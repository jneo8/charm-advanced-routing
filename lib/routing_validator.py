"""RoutingValidator Class.

Validates the entire json configuration constructing a model.
"""
import ipaddress
import json
import pprint
import re
import subprocess


from charmhelpers.core import hookenv


from routing_entry import (
    RoutingEntryRoute,
    RoutingEntryRule,
    RoutingEntryTable,
    RoutingEntryType,
)


class RoutingConfigValidator:
    """Validates the entire json configuration constructing model of rules."""

    def __init__(self):
        """Init function."""
        hookenv.log('Init {}'.format(self.__class__.__name__), level=hookenv.INFO)

        self.pattern = re.compile("^([a-zA-Z0-9-]+)$")
        self.tables = []
        self.config = []

    def read_configurations(self, conf):
        """Read and parse the JSON configuration file."""
        json_decoded = []

        if conf['advanced-routing-config']:
            try:
                json_decoded = json.loads(conf['advanced-routing-config'])
                hookenv.log('Read json config from juju config', level=hookenv.INFO)
            except ValueError as err:
                raise Exception('JSON format invalid, conf: {}, Error: {}'.format(conf['advanced-routing-config'], err))
        else:
            raise Exception("JSON data empty in charm config option 'advanced-routing-config'.")
        self.config = json_decoded

    def verify_config(self):
        """Iterates the entries in the config checking each type for sanity."""
        hookenv.log('Verifying json config', level=hookenv.INFO)
        type_order = ['table', 'route', 'rule']

        dispatch_table = {
            'table': self.verify_table,
            'route': self.verify_route,
            'rule': self.verify_rule,
        }

        for entry_type in type_order:
            # get all the tables together first, so that we can provide strict relations
            for conf in self.config:
                if entry_type != conf['type']:
                    continue
                if 'type' not in conf:
                    msg = "Bad config: Key 'type' not found in routing entry {}.".format(conf)
                    hookenv.log(msg, level=hookenv.ERROR)
                    hookenv.status_set('blocked', msg)
                    raise Exception(msg)
                # Lookup appropriate method and run if found
                verifier = dispatch_table.get(conf['type'])
                if verifier is None:
                    msg = "Bad config: unknown type found: {} in routing entry {}".format(conf['type'], conf)
                    hookenv.status_set('blocked', msg)
                    raise Exception(msg)
                verifier(conf)

    def verify_table(self, conf):
        """Verify tables."""
        hookenv.log('Verifying table {}'.format(pprint.pformat(conf)), level=hookenv.INFO)
        if 'table' not in conf:
            raise Exception("Bad network config: 'table' missing in rule")

        if not self.pattern.match(conf['table']):
            raise Exception('Bad network config: garbage table name in table [0-9a-zA-Z-]')

        if conf['table'] in self.tables:
            raise Exception('Bad network config: duplicate table name "{}"'.format(conf['table']))

        self.tables.append(conf['table'])
        RoutingEntryType.add_entry(RoutingEntryTable(conf))

    def verify_route(self, conf):
        """Verify routes."""
        hookenv.log('Verifying route {}'.format(pprint.pformat(conf)), level=hookenv.INFO)
        try:
            ipaddress.ip_address(conf['gateway'])
        except ValueError as error:
            hookenv.log('Bad gateway IP: {} - {}'.format(conf['gateway'], error), level=hookenv.INFO)
            raise Exception('Bad gateway IP: {} - {}'.format(conf['gateway'], error))

        try:
            ipaddress.ip_network(conf['net'])
        except ValueError as error:
            hookenv.log('Bad network config: {} - {}'.format(conf['net'], error), level=hookenv.INFO)
            raise Exception('Bad network config: {} - {}'.format(conf['net'], error))

        if 'table' in conf:
            if not self.pattern.match(conf['table']):
                hookenv.log('Bad network config: garbage table name in rule [0-9a-zA-Z]', level=hookenv.INFO)
                raise Exception('Bad network config: garbage table name in rule [0-9a-zA-Z]')
            if conf['table'] not in self.tables:
                hookenv.log('Bad network config: table reference not defined', level=hookenv.INFO)
                raise Exception('Bad network config: table reference not defined')

        if 'default_route' in conf:
            if not isinstance(conf['default_route'], bool):
                hookenv.log('Bad network config: default_route should be bool', level=hookenv.INFO)
                raise Exception('Bad network config: default_route should be bool')
            if 'table' not in conf:
                hookenv.log('Bad network config: replacing the default route in main table blocked', level=hookenv.INFO)
                raise Exception('Bad network config: replacing the default route in main table blocked')

        if 'device' in conf:
            if not self.pattern.match(conf['device']):
                hookenv.log('Bad network config: garbage device name in rule [0-9a-zA-Z-]', level=hookenv.INFO)
                raise Exception('Bad network config: garbage device name in rule [0-9a-zA-Z-]')
            try:
                subprocess.check_call(["ip", "link", "show", conf['device']])
            except subprocess.CalledProcessError as error:
                hookenv.log('Device {} does not exist'.format(conf['device']), level=hookenv.INFO)
                raise Exception('Device {} does not exist, {}'.format(conf['device'], error))

        if 'metric' in conf:
            try:
                int(conf['metric'])
            except ValueError:
                hookenv.log('Bad network config: metric expected to be integer', level=hookenv.INFO)
                raise Exception('Bad network config: metric expected to be integer')

        RoutingEntryType.add_entry(RoutingEntryRoute(conf))

    def verify_rule(self, conf):
        """Verify rules."""
        hookenv.log('Verifying rule {}'.format(pprint.pformat(conf)), level=hookenv.INFO)

        try:
            ipaddress.ip_network(conf['from-net'])
        except ValueError as error:
            raise Exception('Bad network config: {} - {}'.format(conf['from-net'], error))

        if 'to-net' in conf:
            try:
                ipaddress.ip_network(conf['to-net'])
            except ValueError as error:
                raise Exception('Bad network config: {} - {}'.format(conf['to-net'], error))

        if 'table' not in conf:
            raise Exception("Bad network config: 'table' missing in rule")

        if conf['table'] not in self.tables:
            raise Exception('Bad network config: table reference not defined')

        if not self.pattern.match(conf['table']):
            raise Exception('Bad network config: garbage table name in rule [0-9a-zA-Z-]')

        if 'priority' in conf:
            try:
                int(conf['priority'])
            except ValueError:
                raise Exception('Bad network config: priority expected to be integer')

        RoutingEntryType.add_entry(RoutingEntryRule(conf))
