"""Main unit testing module."""
import os
import shutil
from unittest import mock


import pytest


import routing_validator


class TestAdvancedRoutingHelper():
    """Main test class."""

    test_dir = '/tmp/test/charm-advanced-routing/'  # trailing slash
    test_ifup_path = test_dir + 'symlink_test/ifup/'
    test_ifdown_path = test_dir + 'symlink_test/ifdown/'
    test_netplanup_path = test_dir + 'symlink_test/netplanup/'
    test_netplandown_path = test_dir + 'symlink_test/netplandown/'
    test_script = 'test-script'

    @classmethod
    def setUp(cls):
        """Setup."""
        os.makedirs(cls.test_dir)
        os.makedirs(cls.test_ifdown_path)
        os.makedirs(cls.test_ifup_path)
        os.makedirs(cls.test_netplandown_path)
        os.makedirs(cls.test_netplanup_path)

    @classmethod
    def tearDown(cls):
        """Teardown method."""
        try:
            shutil.rmtree(cls.test_dir)
        except OSError:
            pass

    def test_pytest(self, advanced_routing_helper):
        """Simple pytest sanity test."""
        assert True

    def test_pre_setup(self, advanced_routing_helper):
        """Test pre_setup."""
        test_obj = advanced_routing_helper

        test_obj.common_location = self.test_dir
        test_obj.if_script = self.test_script
        test_obj.policy_routing_service_path = self.test_dir

        try:
            os.remove(test_obj.policy_routing_service_path + 'charm-pre-install-policy-routing.service')
        except OSError:
            pass

        test_obj.pre_setup(test_obj)

        uppath = test_obj.common_location + 'if-up/'
        downpath = test_obj.common_location + 'if-down/'

        assert os.path.exists(uppath)
        assert os.path.exists(downpath)

        assert test_obj.ifup_path == uppath + test_obj.if_script
        assert test_obj.ifdown_path == downpath + test_obj.if_script

        # touch file to cause the exception
        try:
            with open(test_obj.policy_routing_service_path + 'charm-pre-install-policy-routing.service', "w+") as f:
                f.write('dont care\n')
        except IOError:
            pass  # dont care

        with pytest.raises(Exception):
            test_obj.pre_setup(test_obj)

    def test_setup(self, advanced_routing_helper):
        """Test setup."""
        def noop():
            pass

        test_obj = advanced_routing_helper
        test_obj.common_location = self.test_dir
        test_obj.if_script = self.test_script
        test_obj.ifup_path = '{}if-up/{}'.format(self.test_dir, self.test_script)
        test_obj.ifdown_path = '{}if-down/{}'.format(self.test_dir, self.test_script)

        test_obj.post_setup = noop
        routing_validator.RoutingConfigValidator.__init__ = mock.Mock(return_value=None)
        test_obj.setup(test_obj)

        assert os.path.exists(test_obj.ifup_path)
        assert os.path.exists(test_obj.ifdown_path)

    def test_remove_routes(self, advanced_routing_helper, mock_check_call):
        """Test post_setup."""
        test_obj = advanced_routing_helper

        with mock.patch('charmhelpers.core.host.lsb_release') as lsbrelbionic:
            test_obj.netplan_up_path = self.test_netplanup_path
            test_obj.netplan_down_path = self.test_netplandown_path
            lsbrelbionic.return_value = "bionic"
            test_obj.remove_routes(test_obj)

        with mock.patch('charmhelpers.core.host.lsb_release') as lsbrelartful:
            test_obj.net_tools_up_path = self.test_ifup_path
            test_obj.net_tools_down_path = self.test_ifdown_path
            lsbrelartful.return_value = "artful"
            test_obj.remove_routes(test_obj)

        assert not os.path.exists(test_obj.ifup_path)
        assert not os.path.exists(test_obj.ifdown_path)

    def test_symlink_force(self, advanced_routing_helper):
        """Test symlink_force."""
        test_obj = advanced_routing_helper

        target = self.test_dir + 'testfile'
        link = self.test_dir + 'testlink'

        try:
            os.remove(target)
        except OSError:
            pass  # dont care

        # touch target file to link to
        try:
            with open(target, "w+") as f:
                f.write('dont care\n')
        except IOError:
            pass  # dont care

        assert os.path.exists(target)

        # link it
        test_obj.symlink_force(test_obj, target, link)
        assert os.path.exists(link)

        # link it again
        test_obj.symlink_force(test_obj, target, link)
        assert os.path.exists(link)
