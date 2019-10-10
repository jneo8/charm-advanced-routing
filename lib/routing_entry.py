"""RoutingEntry Classes.

This module contains the following abstract types and
concrete implementations, that model a routing table

                       RoutingEntryType
            ---------------------------------------
           |                    |                  |
     RoutingEntryTable  RoutingEntryRoute  RoutingEntryRule
"""
import subprocess
from abc import ABCMeta, abstractmethod, abstractproperty

from charmhelpers.core import hookenv


class RoutingEntryType(metaclass=ABCMeta):
    """Abstract type RoutingEntryType."""

    entries = []  # static <RoutingEntryType>[]
    config = None  # config entry

    def __init__(self):
        """Constructor."""
        hookenv.log('Init {}'.format(self.__class__.__name__), level=hookenv.INFO)

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
    def add_entry(entry):
        """Add routing entry type.

        The validator may be called multiple times
        The static list will get duplicate items added

        :param entry: routing entry
        """
        for rule in RoutingEntryType.entries:
            if rule.addline == entry.addline:
                return
        RoutingEntryType.entries.append(entry)

    @abstractmethod
    def apply(self):
        """Applies a rule object to the system.

        Not implemented, should override in strategy.
        """
        pass

    @abstractmethod
    def create_line(self):
        """Creates and returns the command line for this rule object.

        Not implemented, should override in strategy.
        """
        pass

    @abstractproperty
    def addline(self):
        """Returns the add line for the ifup script.

        Not implemented, should override in strategy.
        """
        pass

    @abstractproperty
    def removeline(self):
        """Returns the remove line for the ifdown script.

        Not implemented, should override in strategy.
        """
        pass


class RoutingEntryTable(RoutingEntryType):
    """RoutingEntryType used for routing tables."""

    table_name_file = '/etc/iproute2/rt_tables.d/juju-managed.conf'
    table_index_counter = 100  # static
    tables = set()

    def __init__(self, config):
        """Adds unique tables to the tables list."""
        hookenv.log('Created {}'.format(self.__class__.__name__), level=hookenv.INFO)
        super().__init__()
        self.config = config

        if self.config['table'] not in RoutingEntryTable.tables:
            RoutingEntryTable.tables.add(self.config['table'])

    def create_line(self):
        """Not implemented in this base class."""
        raise NotImplementedError

    def apply(self):
        """Opens iproute tables and adds the known list of tables into this file."""
        with open(RoutingEntryTable.table_name_file, 'w') as rt_table_file:
            num = RoutingEntryTable.table_index_counter
            for num, tbl in enumerate(RoutingEntryTable.tables):
                rt_table_file.write("{} {}\n".format(num + RoutingEntryTable.table_index_counter, tbl))

    @property
    def addline(self):
        """Returns the add line for the ifup script."""
        return "# Table: name {}\n".format(self.config['table'])

    @property
    def removeline(self):
        """Returns the remove line for the ifdown script."""
        return ("ip route flush table {table}\n"
                "ip rule del table {table}\n").format(table=self.config['table'])


class RoutingEntryRoute(RoutingEntryType):
    """RoutingEntryType used for routes."""

    def __init__(self, config):
        """Object init function."""
        hookenv.log('Created {}'.format(self.__class__.__name__), level=hookenv.INFO)
        super().__init__()
        self.config = config

    def create_line(self):
        """Creates and returns the command line for this route object."""
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
    """RoutingEntryType used for rules."""

    def __init__(self, config):
        """Object init function."""
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
