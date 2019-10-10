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


class ValidationError(Exception):
    """Validation error exception."""

    pass


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
                msg = 'JSON format invalid, conf: {}, Error: {}'.format(conf['advanced-routing-config'], err)
                self.report_error(msg)
        else:
            msg = "JSON data empty in charm config option 'advanced-routing-config'."
            self.report_error(msg)
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
                    self.report_error(msg)
                # Lookup appropriate method and run if found
                verifier = dispatch_table.get(conf['type'])
                if verifier is None:
                    msg = "Bad config: unknown type found: {} in routing entry {}".format(conf['type'], conf)
                    self.report_error(msg)
                verifier(conf)

    def verify_table(self, conf):
        """Verify tables."""
        hookenv.log('Verifying table {}'.format(pprint.pformat(conf)), level=hookenv.INFO)
        if 'table' not in conf:
            msg = "Bad network config: 'table' missing in rule at {}".format(conf)
            self.report_error(msg)

        if not self.pattern.match(conf['table']):
            msg = 'Bad network config: table name {} must match [0-9a-zA-Z-].'.format(conf['table'])
            self.report_error(msg)

        if conf['table'] in self.tables:
            msg = 'Bad network config: duplicate table name "{}"'.format(conf['table'])
            self.report_error(msg)

        self.tables.append(conf['table'])
        RoutingEntryType.add_entry(RoutingEntryTable(conf))

    def verify_route(self, conf):
        """Verify routes."""
        hookenv.log('Verifying route {}'.format(pprint.pformat(conf)), level=hookenv.INFO)

        # Verify items in configuration
        self.verify_route_gateway(conf)
        self.verify_route_network(conf)
        self.verify_route_table(conf)
        self.verify_route_default_route(conf)
        self.verify_route_device(conf)
        self.verify_route_metric(conf)

        RoutingEntryType.add_entry(RoutingEntryRoute(conf))

    def verify_route_gateway(self, conf):
        """Verify route gateway in conf."""
        try:
            ipaddress.ip_address(conf['gateway'])
        except ValueError as error:
            msg = 'Bad gateway IP: {} - {}'.format(conf['gateway'], error)
            self.report_error(msg)

    def verify_route_network(self, conf):
        """Verify route network in conf."""
        try:
            ipaddress.ip_network(conf['net'])
        except ValueError as error:
            msg = 'Bad network config: {} - {}'.format(conf['net'], error)
            self.report_error(msg)

    def verify_route_table(self, conf):
        """Verify route table in conf."""
        if 'table' in conf:
            if not self.pattern.match(conf['table']):
                msg = 'Bad network config: table name {} must match [0-9a-zA-Z] in {}'.format(conf['table'], conf)
                self.report_error(msg)
            if conf['table'] not in self.tables:
                msg = 'Bad network config: table {} reference not defined'.format(conf['table'])
                self.report_error(msg)

    def verify_route_default_route(self, conf):
        """Verify route default route."""
        if 'default_route' in conf:
            if not isinstance(conf['default_route'], bool):
                msg = 'Bad network config: default_route should be bool in {}'.format(conf)
                self.report_error(msg)
            if 'table' not in conf:
                msg = "Bad network config: Key 'table' missing in default route {} ".format(conf)
                self.report_error(msg)

    def verify_route_device(self, conf):
        """Verify route device."""
        if 'device' in conf:
            if not self.pattern.match(conf['device']):
                msg = 'Bad network config: device name {} in rule {} must match [0-9a-zA-Z-].'.format(
                      conf['device'], conf)
                self.report_error(msg)
            try:
                subprocess.check_call(["ip", "link", "show", conf['device']])
            except subprocess.CalledProcessError as error:
                msg = 'Device {} does not exist: {}'.format(conf['device'], error)
                self.report_error(msg)

    def verify_route_metric(self, conf):
        """."""
        if 'metric' in conf:
            try:
                int(conf['metric'])
            except ValueError:
                msg = 'Bad network config: metric expected to be integer'
                self.report_error(msg)

    def verify_rule(self, conf):
        """Verify rules."""
        hookenv.log('Verifying rule {}'.format(pprint.pformat(conf)), level=hookenv.INFO)

        # Verify items in configuration
        self.verify_rule_from_net(conf)
        self.verify_rule_to_net(conf)
        self.verify_rule_table(conf)
        self.verify_rule_prirority(conf)

        RoutingEntryType.add_entry(RoutingEntryRule(conf))

    def verify_rule_from_net(self, conf):
        """Verify rule source network."""
        try:
            ipaddress.ip_network(conf['from-net'])
        except ValueError as error:
            msg = 'Bad network config: {} - {}'.format(conf['from-net'], error)
            self.report_error(msg)

    def verify_rule_to_net(self, conf):
        """Verify rule destination network."""
        if 'to-net' in conf:
            try:
                ipaddress.ip_network(conf['to-net'])
            except ValueError as error:
                msg = 'Bad network config: {} - {}'.format(conf['to-net'], error)
                self.report_error(msg)

    def verify_rule_table(self, conf):
        """Verify rule table."""
        if 'table' not in conf:
            msg = "Bad network config: 'table' missing in rule {}".format(conf)
            self.report_error(msg)

        if conf['table'] not in self.tables:
            msg = 'Bad network config: table reference not defined: {}'.format(conf['table'])
            self.report_error(msg)

        if not self.pattern.match(conf['table']):
            msg = 'Bad network config: table name {} in rule must match: [0-9a-zA-Z-]'.format(conf['table'])
            self.report_error(msg)

    def verify_rule_prirority(self, conf):
        """Verify rule priority."""
        if 'priority' in conf:
            try:
                int(conf['priority'])
            except ValueError:
                msg = 'Bad network config: priority expected to be integer at {}'.format(conf)
                self.report_error(msg)

    def report_error(self, msg):
        """Error reporting."""
        hookenv.log(msg, level=hookenv.ERROR)
        hookenv.status_set('blocked', msg)
        raise ValidationError(msg)
