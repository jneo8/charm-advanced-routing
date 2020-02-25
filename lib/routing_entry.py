"""RoutingEntry Classes.

This module contains the following abstract types and
concrete implementations, that model a routing table

                       RoutingEntryType
            ---------------------------------------
           |                    |                  |
     RoutingEntryTable  RoutingEntryRoute  RoutingEntryRule
"""
import collections
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

    default_table_file = "/etc/iproute2/rt_tables"
    table_name_file = '/etc/iproute2/rt_tables.d/juju-managed.conf'
    table_index_offset = 100  # static
    tables = set()
    tables_all = set()

    def __init__(self, config):
        """Adds unique tables to the tables list."""
        hookenv.log('Created {}'.format(self.__class__.__name__), level=hookenv.INFO)
        super().__init__()
        self.config = config
        RoutingEntryTable.tables_all = self.store_default_tables

        if not self.table_exists:
            RoutingEntryTable.tables.add(self.config["table"])
            RoutingEntryTable.tables_all.add(self.config["table"])

    @property
    def store_default_tables(self):
        """Store the default tables.

        Default tables don't need to be created by the user.
        """
        try:
            with open(self.default_table_file) as fd:
                # ['local', 'main', 'default', 'unspec']
                self.default_tables = set([
                    line.split()[1] for line in fd.readlines()
                    if line.strip() and not line.strip().startswith("#")
                ])
        except FileNotFoundError:
            self.default_tables = set([])

    @property
    def table_exists(self):
        """Verify if the table shared is reserved by iproute2."""
        return any(self.config["table"] in table
                   for table in [self.tables_all, RoutingEntryTable.tables])

    def create_line(self):
        """Not implemented in this base class."""
        pass

    def apply(self):
        """Opens iproute tables and adds the known list of tables into this file."""
        with open(RoutingEntryTable.table_name_file, 'w') as rt_table_file:
            num = RoutingEntryTable.table_index_offset
            for num, tbl in enumerate(RoutingEntryTable.tables):
                rt_table_file.write(
                    "{} {}\n".format(
                        num + RoutingEntryTable.table_index_offset,
                        tbl,
                    )
                )

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
            cmd.extend([
                "default",
                "via",
                self.config["gateway"],
                "table",
                self.config["table"],
            ])
            if 'device' in self.config.keys():
                cmd.extend([
                    "dev",
                    self.config["device"],
                ])
            return cmd

        # route in any given table or none
        cmd.append(self.config['net'])
        opts = collections.OrderedDict({
            "gateway": "via",
            "device": "dev",
            "table": "table",
            "metric": "metric",
        })
        for opt in opts.keys():
            try:
                cmd.extend([
                    opts[opt],
                    str(self.config[opt]),
                ])
            except KeyError:
                pass
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
            cmd.extend([
                "to",
                self.config["to-net"],
                "lookup",
            ])
            try:
                cmd.append(self.config['table'])
            except KeyError:
                cmd.append("main")
            return cmd

        for opt in ["table", "priority"]:
            try:
                cmd.extend([
                    opt,
                    self.config[opt],
                ])
            except KeyError:
                pass
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
