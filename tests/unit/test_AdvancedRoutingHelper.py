import os
import pytest
import shutil
import subprocess

from unittest import mock

import RoutingValidator

class TestAdvancedRoutingHelper():
    """Main test class."""

    test_dir = '/tmp/test/charm-advanced-routing/'  # trailing slash
    test_ifup_path = test_dir + 'symlink_test/ifup/'
    test_ifdown_path = test_dir + 'symlink_test/ifdown/'
    test_netplanup_path = test_dir + 'symlink_test/netplanup/'
    test_netplandown_path = test_dir + 'symlink_test/netplandown/'
    test_script = 'test-script'

    def setup_class(self):
        try:
            shutil.rmtree(self.test_dir)
        except:
            pass

        os.makedirs(self.test_dir)
        os.makedirs(self.test_ifdown_path)
        os.makedirs(self.test_ifup_path)
        os.makedirs(self.test_netplandown_path)
        os.makedirs(self.test_netplanup_path)

    def test_pytest(self, advanced_routing_helper):
        """Simple pytest sanity test."""
        assert True

    def test_constructor(self, advanced_routing_helper):
        """No test required"""
        pass

    def test_pre_setup(self, advanced_routing_helper):
        """Test pre_setup"""

        test_obj = advanced_routing_helper

        test_obj.common_location = self.test_dir
        test_obj.if_script = self.test_script
        test_obj.policy_routing_service_path = self.test_dir

        try:
            os.remove(test_obj.policy_routing_service_path + 'charm-pre-install-policy-routing.service')
        except:
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
        except:
            pass  # dont care

        with pytest.raises(Exception):
            test_obj.pre_setup(test_obj)

    def test_post_setup(self, advanced_routing_helper):
        """Test post_setup"""
        #test_obj = advanced_routing_helper
        assert True

    def test_setup(self, advanced_routing_helper):
        """Test setup"""

        def noop():
            pass

        test_obj = advanced_routing_helper
        test_obj.common_location = self.test_dir
        test_obj.if_script = self.test_script
        test_obj.ifup_path = '{}if-up/{}'.format(self.test_dir, self.test_script)
        test_obj.ifdown_path = '{}if-down/{}'.format(self.test_dir, self.test_script)

        test_obj.post_setup = noop
        RoutingValidator.RoutingConfigValidator.__init__ = mock.Mock(return_value=None)
        test_obj.setup(test_obj)

        assert os.path.exists(test_obj.ifup_path)
        assert os.path.exists(test_obj.ifdown_path)
        
        assert True

    def test_apply_routes(self, advanced_routing_helper):
        """Test post_setup"""
        #test_obj = advanced_routing_helper
        assert True

    def test_remove_routes(self, advanced_routing_helper, mock_check_call):
        """Test post_setup"""
        test_obj = advanced_routing_helper

        with mock.patch('charmhelpers.core.host.lsb_release') as lsbrelBionic:
            test_obj.netplan_up_path = self.test_netplanup_path
            test_obj.netplan_down_path = self.test_netplandown_path
            lsbrelBionic.return_value = "bionic"
            test_obj.remove_routes(test_obj)

        with mock.patch('charmhelpers.core.host.lsb_release') as lsbrelArtful:
            test_obj.net_tools_up_path = self.test_ifup_path
            test_obj.net_tools_down_path = self.test_ifdown_path
            lsbrelArtful.return_value = "artful"
            test_obj.remove_routes(test_obj)
            
        assert os.path.exists(test_obj.ifup_path) == False
        assert os.path.exists(test_obj.ifdown_path) == False

        assert True

    def test_symlink_force(self, advanced_routing_helper):
        """Test symlink_force"""
        test_obj = advanced_routing_helper

        target = self.test_dir + 'testfile'
        link = self.test_dir + 'testlink'

        try:
            os.remove(target)
        except:
            pass  # dont care

        # touch target file to link to
        try:
            with open(target, "w+") as f:
                f.write('dont care\n')
        except:
            pass  # dont care

        assert os.path.exists(target)

        # link it
        test_obj.symlink_force(test_obj, target, link)
        assert os.path.exists(link)

        # link it again
        test_obj.symlink_force(test_obj, target, link)
        assert os.path.exists(link)
