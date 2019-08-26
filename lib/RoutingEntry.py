import subprocess
from charmhelpers.core import hookenv

#                        RoutingEntryType
#             ---------------------------------------
#            |                    |                  |
#     RoutingEntryTable  RoutingEntryRoute  RoutingEntryRule


class RoutingEntryType(object):
    """Abstract type RoutingEntryType"""
    entries = []  # static <RoutingEntryType>[]
    config = None  # config entry

    def __init__(self):
        hookenv.log('Init %s' % self.__class__.__name__, level=hookenv.INFO)
        pass

    def apply_cmd(self, cmd, pipe=False):
        """Runs a command"""
        try:
            hookenv.log('Subprocess check: {} {}'.format(self.__class__.__name__, cmd), level=hookenv.INFO)
            if pipe:
                command = ' '.join(cmd)
                ps = subprocess.Popen(command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
                ps.communicate()[0]
                return True if ps.returncode == 0 else False
            else:
                subprocess.check_call(cmd)
                return True
        except subprocess.CalledProcessError as error:
            hookenv.log(error, "ERROR")
            return False

    def apply(self):
        """not implemented, should override in strategy"""
        raise NotImplementedError

    def create_line(self):
        """not implemented, should override in strategy"""
        raise NotImplementedError

    @property
    def addLine(self):
        """not implemented, should override in strategy"""
        raise NotImplementedError

    @property
    def removeLine(self):
        """not implemented, should override in strategy"""
        raise NotImplementedError


class RoutingEntryTable(RoutingEntryType):
    """Concrete RoutingEntryType Strategy"""
    table_name_file = '/etc/iproute2/rt_tables.d/juju-managed.conf'
    table_index_counter = 100  # static
    tables = []

    def __init__(self, config):
        hookenv.log('Created %s' % self.__class__.__name__, level=hookenv.INFO)
        super().__init__()
        self.config = config

        if self.config['table'] not in RoutingEntryTable.tables:
            RoutingEntryTable.tables.append(self.config['table'])

    def create_line(self):
        pass

    def apply(self):
        with open(RoutingEntryTable.table_name_file, 'w') as rt_table_file:
            num = RoutingEntryTable.table_index_counter
            for tbl in RoutingEntryTable.tables:
                rt_table_file.write("{} {}\n".format(num, tbl))
                num += 1

    @property
    def addLine(self):
        return "# Table: name {}\n".format(self.config['table'])

    @property
    def removeLine(self):
        line = "sudo ip route flush table {}\n".format(self.config['table'])
        line += "sudo ip rule del table {}\n".format(self.config['table'])
        return line


class RoutingEntryRoute(RoutingEntryType):
    """Concrete RoutingEntryType Strategy"""

    def __init__(self, config):
        hookenv.log('Created %s' % self.__class__.__name__, level=hookenv.INFO)
        super().__init__()
        self.config = config

    def create_line(self):
        cmd = ["sudo", "ip", "route", "replace"]

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
        super().apply_cmd(self.create_line())

    @property
    def addLine(self):
        return ' '.join(self.create_line()) + "\n"

    @property
    def removeLine(self):
        return ' '.join(self.create_line()).replace(" replace ", " del ") + "\n"


class RoutingEntryRule(RoutingEntryType):
    """Concrete RoutingEntryType Strategy"""

    def __init__(self, config):
        hookenv.log('Created %s' % self.__class__.__name__, level=hookenv.INFO)
        super().__init__()
        self.config = config

    def create_line(self):
        cmd = ["sudo", "ip", "rule", "add", "from", self.config['from-net']]

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
        if self.is_duplicate() == False:
            # ip rule replace not supported, check for duplicates
            super().apply_cmd(self.create_line())

    @property
    def addLine(self):
        return ' '.join(self.create_line()) + "\n"

    @property
    def removeLine(self):
        return ' '.join(self.create_line()).replace(" add ", " del ") + "\n"

    def is_duplicate(self):
        """Ip rule add does not prevent duplicates in older kernel versions"""
        # https://patchwork.ozlabs.org/patch/624553/
        parts = ' '.join(self.create_line()).split("add ")
        return self.apply_cmd(["ip", "rule", "|", "grep", "\"" + parts[1] + "\""], True)
