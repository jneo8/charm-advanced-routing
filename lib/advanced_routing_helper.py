"""Routing module."""
import errno
import os
import pathlib
import subprocess

from charmhelpers.core import hookenv
from charmhelpers.core.host import CompareHostReleases, lsb_release

from routing_entry import RoutingEntryType

from routing_validator import RoutingConfigValidator


class PolicyRoutingExists(Exception):
    """Old charm-policy-routing configuration is in place."""

    pass


class AdvancedRoutingHelper:
    """Helper class for routing."""

    if_script = '95-juju_routing'
    common_location = pathlib.Path('/usr/local/lib/juju-charm-advanced-routing')
    net_tools_up_path = pathlib.Path('/etc/network/if-up.d')
    net_tools_down_path = pathlib.Path('/etc/network/if-down.d')
    netplan_up_path = pathlib.Path('/etc/networkd-dispatcher/routable.d')
    netplan_down_path = pathlib.Path('/etc/networkd-dispatcher/off.d')
    policy_routing_service_path = pathlib.Path('/etc/systemd/system')
    table_name_file = pathlib.Path('/etc/iproute2/rt_tables.d/juju-managed.conf')
    ifup_path = common_location / "if-up" / if_script
    ifdown_path = common_location / "if-down" / if_script

    def __init__(self):
        """Init function."""
        hookenv.log('Init {}'.format(self.__class__.__name__), level=hookenv.INFO)
        self.charm_config = hookenv.config()
        self.pre_setup()

    @property
    def is_advanced_routing_enabled(self):
        """Returns boolean according to Juju config input."""
        return self.charm_config["enable-advanced-routing"]

    def pre_setup(self):
        """Create folder path for the ifup/down scripts."""
        for ifpath in ["if-up", "if-down"]:
            ifpath_full = self.common_location / ifpath
            if not ifpath_full.exists():
                ifpath_full.mkdir(parents=True)
                hookenv.log('Created {}'.format(ifpath_full), level=hookenv.INFO)

        # check for service file of charm-policy-routing, and block if its present
        policy_routing_svcname = 'charm-pre-install-policy-routing.service'
        policy_routing_file = self.policy_routing_service_path / policy_routing_svcname
        if policy_routing_file.exists():
            hookenv.log(
                'It looks like charm-policy-routing is enabled.'
                ' charm-pre-install-policy-routing.service',
                hookenv.ERROR,
            )
            raise PolicyRoutingExists("Please disable charm-policy-routing")

    def post_setup(self):
        """Symlinks the up/down scripts from the if.up/down or netplan scripts location."""
        hookenv.log('Symlinking into distro specific network manager', level=hookenv.INFO)
        ifup_script, ifdown_script = self.if_scripts
        self.symlink_force(str(self.ifup_path), str(ifup_script))
        self.symlink_force(str(self.ifdown_path), str(ifdown_script))

    def setup(self):
        """Modify the interfaces configurations."""
        # Validate configuration options first
        routing_validator = RoutingConfigValidator()
        routing_validator.read_configurations(self.charm_config["advanced-routing-config"])
        routing_validator.verify_config()

        hookenv.log('Writing {}'.format(self.ifup_path), level=hookenv.INFO)
        # Modify if-up.d
        with open(str(self.ifup_path), 'w') as ifup:
            ifup.write("# This file is managed by Juju.\nip route flush cache\n")
            for entry in RoutingEntryType.entries:
                ifup.write(entry.addline)
        os.chmod(str(self.ifup_path), 0o755)

        hookenv.log('Writing {}'.format(self.ifdown_path), level=hookenv.INFO)
        # Modify if-down.d
        with open(str(self.ifdown_path), 'w') as ifdown:
            ifdown.write("# This file is managed by Juju.\n")
            for entry in list(reversed(RoutingEntryType.entries)):
                ifdown.write(entry.removeline)
            ifdown.write("ip route flush cache\n")
        os.chmod(str(self.ifdown_path), 0o755)

        self.post_setup()

    def apply_config(self):
        """Apply the new routes to the system."""
        hookenv.log('Applying routing rules', level=hookenv.INFO)
        for entry in RoutingEntryType.entries:
            entry.apply()

    def remove_routes(self):
        """Cleanup job."""
        hookenv.log('Removing routing rules', level=hookenv.INFO)
        if self.ifdown_path.is_file():
            try:
                subprocess.check_call(["sh", "-c", str(self.ifdown_path)])
            except subprocess.CalledProcessError as err:
                # Either rules are removed or not valid
                hookenv.log(
                    'ifdown script {} failed. Maybe rules are already gone? Error: {}'.format(
                        self.ifdown_path,
                        err,
                    ),
                    hookenv.WARNING,
                )

        # remove start/stop scripts and table name from iproute2
        filelist = [self.ifup_path, self.ifdown_path, self.table_name_file]
        # remove symlinks
        filelist.extend(self.if_scripts)
        for filename in filelist:
            try:
                filename.unlink()
            except FileNotFoundError as err:
                hookenv.log('Nothing to clean up: {}'.format(err), hookenv.DEBUG)

    def symlink_force(self, target, link_name):
        """Ensures accurate symlink by removing any existing links."""
        try:
            os.symlink(target, link_name)
        except OSError as e:
            if e.errno == errno.EEXIST:
                os.remove(link_name)
                os.symlink(target, link_name)
            else:
                raise e

    @property
    def if_scripts(self):
        """Returns path to folders by series."""
        release = lsb_release()['DISTRIB_CODENAME'].lower()
        if_path = (self.net_tools_up_path
                   if CompareHostReleases(release) < "bionic" else self.netplan_up_path)
        ifup_script = if_path / self.if_script
        ifdown_script = if_path / self.if_script
        return [ifup_script, ifdown_script]
