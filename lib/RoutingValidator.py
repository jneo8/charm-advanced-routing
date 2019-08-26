
import ipaddress
import json
import sys
import re
import pprint

from charmhelpers.core import hookenv
from RoutingEntry import (
    RoutingEntryType,
    RoutingEntryTable,
    RoutingEntryRoute,
    RoutingEntryRule,
)


class RoutingConfigValidator:

    def __init__(self):
        """Init function."""
        hookenv.log('Init %s' % self.__class__.__name__, level=hookenv.INFO)

        self.pattern = re.compile("^([a-zA-Z0-9]+)$")
        self.tables = []
        self.config = self.read_configurations()
        self.verify_config()

    def read_configurations(self):
        """Read and parse the JSON configuration file."""
        json_decoded = []
        conf = hookenv.config()

        if conf['advanced-routing-config']:
            try:
                json_decoded = json.loads(conf['advanced-routing-config'])
                hookenv.log('Read json config from juju resource', level=hookenv.INFO)
            except ValueError:
                hookenv.status_set('blocked', 'JSON file format invalid.')
                sys.exit(1)
        else:
            hookenv.status_set('blocked', 'JSON file not attached in charm.')
            sys.exit(1)
        return json_decoded

    def verify_config(self):
        """Iterates the entries in the config checking each type for sanity."""
        hookenv.log('Verifying json config', level=hookenv.INFO)
        ruleorder = ['table', 'route', 'rule']

        for rule in ruleorder:
            # get all the tables together first, so that we can provide strict relations
            for conf in self.config:
                if 'type' not in conf:
                    hookenv.status_set('blocked', 'Bad config: \'type\' not found in routing entry')
                    hookenv.log('type not found in rule', level=hookenv.ERROR)
                    sys.exit(1)
                if rule == "table" and rule == conf['type']:
                    self.verify_table(conf)
                if rule == "route" and rule == conf['type']:
                    self.verify_route(conf)
                if rule == "rule" and rule == conf['type']:
                    self.verify_rule(conf)

    def verify_table(self, conf):
        """Verify rules."""
        hookenv.log('Verifying table \n%s' % pprint.pformat(conf), level=hookenv.INFO)
        if 'table' not in conf:
            hookenv.status_set('blocked', 'Bad network config: \'table\' missing in rule')
            sys.exit(1)

        if self.pattern.match(conf['table']) == False:
            hookenv.status_set('blocked', 'Bad network config: garbage table name in table [0-9a-zA-Z]')
            sys.exit(1)

        if conf['table'] in self.tables:
            hookenv.status_set('blocked', 'Bad network config: duplicate table name')
            sys.exit(1)

        self.tables.append(conf['table'])
        RoutingEntryType.entries.append(RoutingEntryTable(conf))

    def verify_route(self, conf):
        """Verify routes."""
        hookenv.log('Verifying route \n%s' % pprint.pformat(conf), level=hookenv.INFO)
        try:
            ipaddress.ip_address(conf['gateway'])
        except ValueError as error:
            hookenv.log('Bad gateway IP: {} - {}'.format(conf['gateway'], error), level=hookenv.INFO)
            hookenv.status_set('blocked', 'Bad gateway IP: {} - {}'.format(conf['gateway'], error))
            sys.exit(1)

        try:
            ipaddress.ip_network(conf['net'])
        except ValueError as error:
            hookenv.log('Bad network config: {} - {}'.format(conf['net'], error), level=hookenv.INFO)
            hookenv.status_set('blocked', 'Bad network config: {} - {}'.format(conf['net'], error))
            sys.exit(1)

        if 'table' in conf:
            if self.pattern.match(conf['table']) == False:
                hookenv.log('Bad network config: garbage table name in rule [0-9a-zA-Z]', level=hookenv.INFO)
                hookenv.status_set('blocked', 'Bad network config')
                sys.exit(1)
            if conf['table'] not in self.tables:
                hookenv.log('Bad network config: table reference not defined', level=hookenv.INFO)
                hookenv.status_set('blocked', 'Bad network config')
                sys.exit(1)

        if 'default_route' in conf:
            if type(conf['default_route']) != type(True):
                hookenv.log('Bad network config: default_route should be bool', level=hookenv.INFO)
                hookenv.status_set('blocked', 'Bad network config')
                sys.exit(1)
            if 'table' not in conf:
                hookenv.log('Bad network config: replacing the default route in main table blocked', level=hookenv.INFO)
                hookenv.status_set('blocked', 'Bad network config')
                sys.exit(1)

        if 'device' in conf:
            if self.pattern.match(conf['device']) == False:
                hookenv.log('Bad network config: garbage device name in rule [0-9a-zA-Z]', level=hookenv.INFO)
                hookenv.status_set('blocked', 'Bad network config')
                sys.exit(1)

        if 'metric' in conf:
            try:
                int(conf['metric'])
            except ValueError:
                hookenv.log('Bad network config: metric expected to be integer', level=hookenv.INFO)
                hookenv.status_set('blocked', 'Bad network config')
                sys.exit(1)

        RoutingEntryType.entries.append(RoutingEntryRoute(conf))

    def verify_rule(self, conf):
        """Verify rules."""
        hookenv.log('Verifying rule \n%s' % pprint.pformat(conf), level=hookenv.INFO)

        try:
            ipaddress.ip_network(conf['from-net'])
        except ValueError as error:
            hookenv.status_set('blocked', 'Bad network config: {} - {}'.format(conf['from-net'], error))
            sys.exit(1)

        if 'to-net' in conf:
            try:
                ipaddress.ip_network(conf['to-net'])
            except ValueError as error:
                hookenv.status_set('blocked', 'Bad network config: {} - {}'.format(conf['to-net'], error))
                sys.exit(1)

        if 'table' not in conf:
            hookenv.status_set('blocked', 'Bad network config: \'table\' missing in rule')
            sys.exit(1)
            if conf['table'] not in self.tables:
                hookenv.status_set('blocked', 'Bad network config: table reference not defined')
                sys.exit(1)

        if self.pattern.match(conf['table']) == False:
            hookenv.status_set('blocked', 'Bad network config: garbage table name in rule [0-9a-zA-Z]')
            sys.exit(1)

        if 'priority' in conf:
            try:
                int(conf['priority'])
            except ValueError:
                hookenv.status_set('blocked', 'Bad network config: priority expected to be integer')
                sys.exit(1)

        RoutingEntryType.entries.append(RoutingEntryRule(conf))
