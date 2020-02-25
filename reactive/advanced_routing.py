"""Reactive charm hooks."""
import sys

from advanced_routing_helper import AdvancedRoutingHelper, PolicyRoutingExists

from charms.layer import status
from charms.reactive import set_flag, when, when_not

from routing_validator import RoutingConfigValidatorError


try:
    advanced_routing = AdvancedRoutingHelper()
except PolicyRoutingExists as error:
    status.blocked(str(error))
    sys.exit(0)


@when_not('advanced-routing.installed')
def install_routing():
    """Install the charm."""
    if advanced_routing.is_advanced_routing_enabled:
        status.maintenance('Installing routes')
        try:
            advanced_routing.setup()
        except RoutingConfigValidatorError as error:
            status.blocked(str(error))
            return
        advanced_routing.apply_config()
        set_flag('advanced-routing.installed')

    status.active('Unit is ready.')


@when('config.changed')
def reconfigure_routing():
    """Handle routing configuration change."""
    if advanced_routing.is_advanced_routing_enabled:
        status.maintenance('Installing routes')
        advanced_routing.remove_routes()
        advanced_routing.setup()
        advanced_routing.apply_config()
    else:
        status.maintenance('Removing routes')
        advanced_routing.remove_routes()

    status.active('Unit is ready')
