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
                return ps.returncode == 0
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
    tables = set([])
    tables_all = set([])

    def __init__(self, config):
        """Adds unique tables to the tables list."""
        hookenv.log('Created {}'.format(self.__class__.__name__), level=hookenv.INFO)
        super().__init__()
        self.config = config
        RoutingEntryTable.tables_all.update(self.store_default_tables)

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
                return set([
                    line.split()[1] for line in fd.readlines()
                    if line.strip() and not line.strip().startswith("#")
                ])
        except FileNotFoundError:
            return set([])

    @property
    def table_exists(self):
        """Verify if the table shared is reserved by iproute2."""
        return self.config["table"] in RoutingEntryTable.tables_all

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
        """Creates and returns the command line for this route object.

        "default_route" and "net" are mutually exclusive. One of them is required
        "default_route" requires "table"
        "gateway" is mandatory

        Optional keywords: device, table and metric

        """
        opts = collections.OrderedDict({
            "device": "dev",
            "table": "table",
            "metric": "metric",
        })
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
            # already enforced
            del opts["table"]
        else:
            # route in any given table or none
            cmd.extend([
                self.config['net'],
                "via",
                self.config["gateway"],
            ])

        # The "default_route" flow forces "table", so it is later removed
        for opt, keyword in opts.items():
            try:
                cmd.extend([
                    keyword,
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
        """Creates and returns the command line for this rule object.

        Variations:
        # any dst, table main, default prio
        ip rule add from X.X.X.X/XX
        # table main, default prio
        ip rule add from X.X.X.X/XX to Y.Y.Y.Y/YY
        # default prio
        ip rule add from X.X.X.X/XX to Y.Y.Y.Y/YY table mytable
        # table main
        ip rule add from X.X.X.X/XX to Y.Y.Y.Y/YY priority NNN
        # all is specified
        ip rule add from X.X.X.X/XX to Y.Y.Y.Y/YY table mytable priority NNN
        # any dst, default prio
        ip rule add from X.X.X.X/XX table mytable
        # any dst
        ip rule add from X.X.X.X/XX table mytable priority NNN
        # any dst, table main
        ip rule add from X.X.X.X/XX priority NNN
        """
        cmd = ["ip", "rule", "add", "from", self.config['from-net']]
        opts = collections.OrderedDict({
            "to-net": "to",
            "table": "table",
            "priority": "priority",
        })
        for opt, keyword in opts.items():
            try:
                cmd.extend([
                    keyword,
                    str(self.config[opt]),
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
        matchparams = ["from", self.config['from-net']]
        to = self.config.get("to-net")
        if to and to != "all":  # ip rule omits to=all as it's implied
            matchparams.extend(("to", to))
        matchparams.extend(("lookup", self.config.get("table", "main")))
        matchline = " ".join(matchparams)
        prio = str(self.config.get("priority", ""))
        existing_rules = subprocess.check_output(["ip", "rule"]).decode("utf8").splitlines()
        for rule in existing_rules:
            rule = rule.strip()
            if rule.startswith(prio) and rule.endswith(matchline):
                hookenv.log("Found dup rule: {}".format(matchline), level=hookenv.DEBUG)
                return True
        return False
