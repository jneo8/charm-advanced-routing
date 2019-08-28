"""RoutingValidator Class.

Validates the entire json configuration constructing a model.
"""
import ipaddress
import json
import pprint
import re
import subprocess

from RoutingEntry import (
    RoutingEntryRoute,
    RoutingEntryRule,
    RoutingEntryTable,
    RoutingEntryType,
)

from charmhelpers.core import hookenv


class RoutingConfigValidator:
    """Validates the enitre json configuration constructing model of rules."""

    def __init__(self):
        """Init function."""
        hookenv.log('Init {}'.format(self.__class__.__name__), level=hookenv.INFO)

        self.pattern = re.compile("^([a-zA-Z0-9-]+)$")
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
                hookenv.log('Read json config from juju config', level=hookenv.INFO)
            except ValueError:
                hookenv.status_set('blocked', 'JSON format invalid.')
                raise Exception('JSON format invalid.')
        else:
            hookenv.status_set('blocked', 'JSON invalid or not set in charm config')
            raise Exception('JSON format invalid.')
        return json_decoded

    def verify_config(self):
        """Iterates the entries in the config checking each type for sanity."""
        hookenv.log('Verifying json config', level=hookenv.INFO)
        type_order = ['table', 'route', 'rule']

        for entry_type in type_order:
            # get all the tables together first, so that we can provide strict relations
            for conf in self.config:
                if 'type' not in conf:
                    hookenv.status_set('blocked', 'Bad config: \'type\' not found in routing entry')
                    hookenv.log('type not found in rule', level=hookenv.ERROR)
                    raise Exception('type not found in rule')
                if entry_type == "table" and entry_type == conf['type']:
                    self.verify_table(conf)
                if entry_type == "route" and entry_type == conf['type']:
                    self.verify_route(conf)
                if entry_type == "rule" and entry_type == conf['type']:
                    self.verify_rule(conf)

    def verify_table(self, conf):
        """Verify rules."""
        hookenv.log('Verifying table \n{}'.format(pprint.pformat(conf)), level=hookenv.INFO)
        if 'table' not in conf:
            hookenv.status_set('blocked', 'Bad network config: \'table\' missing in rule')
            raise Exception('Bad network config: \'table\' missing in rule')

        if self.pattern.match(conf['table']) is False:
            hookenv.status_set('blocked', 'Bad network config: garbage table name in table [0-9a-zA-Z-]')
            raise Exception('Bad network config: garbage table name in table [0-9a-zA-Z-]')

        if conf['table'] in self.tables:
            hookenv.status_set('blocked', 'Bad network config: duplicate table name')
            raise Exception('Bad network config: duplicate table name')

        self.tables.append(conf['table'])
        RoutingEntryType.add_rule(RoutingEntryTable(conf))

    def verify_route(self, conf):
        """Verify routes."""
        hookenv.log('Verifying route \n{}'.format(pprint.pformat(conf)), level=hookenv.INFO)
        try:
            ipaddress.ip_address(conf['gateway'])
        except ValueError as error:
            hookenv.log('Bad gateway IP: {} - {}'.format(conf['gateway'], error), level=hookenv.INFO)
            hookenv.status_set('blocked', 'Bad gateway IP: {} - {}'.format(conf['gateway'], error))
            raise Exception('Bad gateway IP: {} - {}'.format(conf['gateway'], error))

        try:
            ipaddress.ip_network(conf['net'])
        except ValueError as error:
            hookenv.log('Bad network config: {} - {}'.format(conf['net'], error), level=hookenv.INFO)
            hookenv.status_set('blocked', 'Bad network config: {} - {}'.format(conf['net'], error))
            raise Exception('Bad network config: {} - {}'.format(conf['net'], error))

        if 'table' in conf:
            if self.pattern.match(conf['table']) is False:
                hookenv.log('Bad network config: garbage table name in rule [0-9a-zA-Z]', level=hookenv.INFO)
                hookenv.status_set('blocked', 'Bad network config')
                raise Exception('Bad network config: garbage table name in rule [0-9a-zA-Z]')
            if conf['table'] not in self.tables:
                hookenv.log('Bad network config: table reference not defined', level=hookenv.INFO)
                hookenv.status_set('blocked', 'Bad network config')
                raise Exception('Bad network config: table reference not defined')

        if 'default_route' in conf:
            if isinstance(conf['default_route'], bool):
                hookenv.log('Bad network config: default_route should be bool', level=hookenv.INFO)
                hookenv.status_set('blocked', 'Bad network config')
                raise Exception('Bad network config: default_route should be bool')
            if 'table' not in conf:
                hookenv.log('Bad network config: replacing the default route in main table blocked', level=hookenv.INFO)
                hookenv.status_set('blocked', 'Bad network config')
                raise Exception('Bad network config: replacing the default route in main table blocked')

        if 'device' in conf:
            if self.pattern.match(conf['device']) is False:
                hookenv.log('Bad network config: garbage device name in rule [0-9a-zA-Z-]', level=hookenv.INFO)
                hookenv.status_set('blocked', 'Bad network config')
                raise Exception('Bad network config: garbage device name in rule [0-9a-zA-Z-]')
            try:
                subprocess.check_call(["ip", "link", "show", conf['device']])
            except subprocess.CalledProcessError as error:
                hookenv.log('Device {} does not exist'.format(conf['device']), level=hookenv.INFO)
                hookenv.status_set('blocked', 'Bad network config')
                raise Exception('Device {} does not exist, {}'.format(conf['device'], error))

        if 'metric' in conf:
            try:
                int(conf['metric'])
            except ValueError:
                hookenv.log('Bad network config: metric expected to be integer', level=hookenv.INFO)
                hookenv.status_set('blocked', 'Bad network config')
                raise Exception('Bad network config: metric expected to be integer')

        RoutingEntryType.add_rule(RoutingEntryRoute(conf))

    def verify_rule(self, conf):
        """Verify rules."""
        hookenv.log('Verifying rule \n{}'.format(pprint.pformat(conf)), level=hookenv.INFO)

        try:
            ipaddress.ip_network(conf['from-net'])
        except ValueError as error:
            hookenv.status_set('blocked', 'Bad network config: {} - {}'.format(conf['from-net'], error))
            raise Exception('Bad network config: {} - {}'.format(conf['from-net'], error))

        if 'to-net' in conf:
            try:
                ipaddress.ip_network(conf['to-net'])
            except ValueError as error:
                hookenv.status_set('blocked', 'Bad network config: {} - {}'.format(conf['to-net'], error))
                raise Exception('Bad network config: {} - {}'.format(conf['to-net'], error))

        if 'table' not in conf:
            hookenv.status_set('blocked', 'Bad network config: \'table\' missing in rule')
            raise Exception('Bad network config: \'table\' missing in rule')

        if conf['table'] not in self.tables:
            hookenv.status_set('blocked', 'Bad network config: table reference not defined')
            raise Exception('Bad network config: table reference not defined')

        if self.pattern.match(conf['table']) is False:
            hookenv.status_set('blocked', 'Bad network config: garbage table name in rule [0-9a-zA-Z-]')
            raise Exception('Bad network config: garbage table name in rule [0-9a-zA-Z-]')

        if 'priority' in conf:
            try:
                int(conf['priority'])
            except ValueError:
                hookenv.status_set('blocked', 'Bad network config: priority expected to be integer')
                raise Exception('Bad network config: priority expected to be integer')

        RoutingEntryType.add_rule(RoutingEntryRule(conf))
