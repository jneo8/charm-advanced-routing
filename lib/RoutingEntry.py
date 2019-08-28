"""RoutingEntry Classes.

This module contains the following abstract type and
concrete implementations, thta model a routing table

                       RoutingEntryType
            ---------------------------------------
           |                    |                  |
     RoutingEntryTable  RoutingEntryRoute  RoutingEntryRule
"""
import subprocess

from charmhelpers.core import hookenv


class RoutingEntryType(object):
    """Abstract type RoutingEntryType."""

    entries = []  # static <RoutingEntryType>[]
    config = None  # config entry

    def __init__(self):
        """Constructor."""
        hookenv.log('Init {}'.format(self.__class__.__name__), level=hookenv.INFO)
        pass

    def exec_cmd(self, cmd, pipe=False):
        """Runs a subprocess and returns True or False on success."""
        try:
            if pipe:
                hookenv.log('Subprocess check shell: {} {}'.format(self.__class__.__name__, cmd), level=hookenv.INFO)
                command = ' '.join(cmd)
                ps = subprocess.Popen(command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
                ps.communicate()
                return True if ps.returncode == 0 else False
            else:
                hookenv.log('Subprocess check: {} {}'.format(self.__class__.__name__, cmd), level=hookenv.INFO)
                subprocess.check_call(cmd)
                return True
        except subprocess.CalledProcessError as error:
            hookenv.log(error, level=hookenv.ERROR)
            return False

    @staticmethod
    def add_rule(newrule):
        """Due to config-change/install etc hooks etc.

        The validator may be called multiple times
        The static list will get duplicate items added
        """
        for rule in RoutingEntryType.entries:
            if rule.addline == newrule.addline:
                return
        RoutingEntryType.entries.append(newrule)

    def apply(self):
        """Not implemented, should override in strategy."""
        raise NotImplementedError

    def create_line(self):
        """Not implemented, should override in strategy."""
        raise NotImplementedError

    @property
    def addline(self):
        """Not implemented, should override in strategy."""
        raise NotImplementedError

    @property
    def removeline(self):
        """Not implemented, should override in strategy."""
        raise NotImplementedError


class RoutingEntryTable(RoutingEntryType):
    """Concrete RoutingEntryType Strategy."""

    table_name_file = '/etc/iproute2/rt_tables.d/juju-managed.conf'
    table_index_counter = 100  # static
    tables = []

    def __init__(self, config):
        """Adds unique tables to the tables list."""
        hookenv.log('Created {}'.format(self.__class__.__name__), level=hookenv.INFO)
        super().__init__()
        self.config = config

        if self.config['table'] not in RoutingEntryTable.tables:
            RoutingEntryTable.tables.append(self.config['table'])

    def create_line(self):
        """Not implemented in this base class."""
        raise NotImplementedError

    def apply(self):
        """Opens iproute tables and adds the known list of tables into this file."""
        with open(RoutingEntryTable.table_name_file, 'w') as rt_table_file:
            num = RoutingEntryTable.table_index_counter
            for tbl in RoutingEntryTable.tables:
                rt_table_file.write("{} {}\n".format(num, tbl))
                num += 1

    @property
    def addline(self):
        """Returns the add line for the ifup script."""
        return "# Table: name {}\n".format(self.config['table'])

    @property
    def removeline(self):
        """Returns the remove line for the ifdown script."""
        line = "ip route flush table {}\n".format(self.config['table'])
        line += "ip rule del table {}\n".format(self.config['table'])
        return line


class RoutingEntryRoute(RoutingEntryType):
    """Concrete RoutingEntryType Strategy."""

    def __init__(self, config):
        """Nothing special in this constructor."""
        hookenv.log('Created {}'.format(self.__class__.__name__), level=hookenv.INFO)
        super().__init__()
        self.config = config

    def create_line(self):
        """Creates and returns the command line for this rule object."""
        cmd = ["ip", "route", "replace"]

        # default route in table
        if 'default_route' in self.config.keys():
            cmd.append("default")
            cmd.append("via")
            cmd.append(self.config['gateway'])
            cmd.append("table")
            cmd.append(self.config['table'])
            if 'device' in self.config.keys():
                cmd.append("dev")
                cmd.append(self.config['device'])
        # route in any given table or none
        else:
            cmd.append(self.config['net'])
            if 'gateway' in self.config.keys():
                cmd.append("via")
                cmd.append(self.config['gateway'])
            if 'device' in self.config.keys():
                cmd.append("dev")
                cmd.append(self.config['device'])
            if 'table' in self.config.keys():
                cmd.append("table")
                cmd.append(self.config['table'])
            if 'metric' in self.config.keys():
                cmd.append("metric")
                cmd.append(str(self.config['metric']))

        return cmd

    def apply(self):
        """Applies this rule object to the system."""
        super().exec_cmd(self.create_line())

    @property
    def addline(self):
        """Returns the add line for the ifup script."""
        return ' '.join(self.create_line()) + "\n"

    @property
    def removeline(self):
        """Returns the remove line for the ifdown script."""
        return ' '.join(self.create_line()).replace(" replace ", " del ") + "\n"


class RoutingEntryRule(RoutingEntryType):
    """Concrete RoutingEntryType Strategy."""

    def __init__(self, config):
        """Nothing special in this constructor."""
        hookenv.log('Created {}'.format(self.__class__.__name__), level=hookenv.INFO)
        super().__init__()
        self.config = config

    def create_line(self):
        """Creates and returns the command line for this rule object."""
        cmd = ["ip", "rule", "add", "from", self.config['from-net']]

        if 'to-net' in self.config.keys():
            cmd.append("to")
            cmd.append(self.config['to-net'])
            cmd.append("lookup")
            if 'table' in self.config.keys():
                cmd.append(self.config['table'])
            else:
                cmd.append('main')
        else:
            if 'table' in self.config.keys():
                cmd.append(self.config['table'])
            if 'priority' in self.config.keys():
                cmd.append(self.config['priority'])

        return cmd

    def apply(self):
        """Applies this rule object to the system."""
        if self.is_duplicate() is False:
            # ip rule replace not supported, check for duplicates
            super().exec_cmd(self.create_line())

    @property
    def addline(self):
        """Returns the add line for the ifup script."""
        return ' '.join(self.create_line()) + "\n"

    @property
    def removeline(self):
        """Returns the remove line for the ifdown script."""
        return ' '.join(self.create_line()).replace(" add ", " del ") + "\n"

    def is_duplicate(self):
        """Ip rule add does not prevent duplicates in older kernel versions."""
        # https://patchwork.ozlabs.org/patch/624553/
        parts = ' '.join(self.create_line()).split("add ")
        return self.exec_cmd(["ip", "rule", "|", "grep", "\"" + parts[1] + "\""], pipe=True)
