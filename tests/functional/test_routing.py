#!/usr/bin/python3.6
"""Main module for functional testing."""

import os

import pytest

pytestmark = pytest.mark.asyncio
SERIES = ['bionic', 'xenial']

############
# FIXTURES #
############


@pytest.fixture(scope='module', params=SERIES)
async def deploy_app(request, model):
    """Deploy the advanced-routing charm as a subordinate of ubuntu."""
    release = request.param

    await model.deploy(
        'ubuntu',
        application_name='ubuntu-' + release,
        series=release,
        channel='stable'
    )
    advanced_routing = await model.deploy(
        '{}/builds/advanced-routing'.format(os.getenv('JUJU_REPOSITORY')),
        application_name='advanced-routing-' + release,
        series=release,
        num_units=0,
    )
    await model.add_relation(
        'ubuntu-' + release,
        'advanced-routing-' + release
    )

    await model.block_until(lambda: advanced_routing.status == 'active')
    yield advanced_routing


@pytest.fixture(scope='module')
async def unit(deploy_app):
    """Return the advanced-routing unit we've deployed."""
    return deploy_app.units.pop()

#########
# TESTS #
#########


async def test_deploy(deploy_app):
    """Test the deployment."""
    assert deploy_app.status == 'active'
