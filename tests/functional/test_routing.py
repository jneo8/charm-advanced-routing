#!/usr/bin/python3.6
"""Main module for functional testing."""

import os

import pytest

pytestmark = pytest.mark.asyncio
SERIES = ['xenial',
          'bionic',
          pytest.param('cosmic', marks=pytest.mark.xfail(reason='canary')),
          ]

############
# FIXTURES #
############

@pytest.fixture(scope='module',
                params=SERIES)
async def deploy_app(request, model):
    """Deploy the policy-routing charm as a subordinate of ubuntu."""
    release = request.param

    await model.deploy(
        'ubuntu',
        application_name='ubuntu-' + release,
        series=release,
        channel='stable'
    )
    policy_routing = await model.deploy(
        '{}/builds/policy-routing'.format(os.getenv('JUJU_REPOSITORY')),
        application_name='policy-routing-' + release,
        series=release,
        num_units=0,
    )
    await model.add_relation(
        'ubuntu-' + release,
        'policy-routing-' + release
    )

    await model.block_until(lambda: policy_routing.status == 'active')
    yield policy_routing


@pytest.fixture(scope='module')
async def unit(deploy_app):
    """Return the policy-routing unit we've deployed."""
    return deploy_app.units.pop()

#########
# TESTS #
#########


async def test_deploy(deploy_app):
    """Tst the deployment."""
    assert deploy_app.status == 'active'
