"""Config options used in test_routing.py.

Listing of advanced-routing-config options to be tested in test_juju_routing
"""

JSON_CONFIGS = [
    {
        "input": [
            {"type": "table", "table": "SF1"},
            {
                "type": "route",
                "default_route": True,
                "net": "192.170.1.0/24",
                "gateway": "10.191.86.2",
                "table": "SF1",
                "metric": 101,
                "device": "eth0",
            },
            {"type": "route", "net": "6.6.6.0/24", "gateway": "10.191.86.2"},
            {
                "type": "rule",
                "from-net": "192.170.2.0/24",
                "to-net": "192.170.2.0/24",
                "table": "SF1",
                "priority": 101,
            },
        ],
        "expected_ifup": (
            "# This file is managed by Juju.\n"
            "ip route flush cache\n"
            "# Table: name SF1\n"
            "ip route replace default via 10.191.86.2 table SF1 dev eth0 metric 101\n"
            "ip route replace 6.6.6.0/24 via 10.191.86.2\n"
            "ip rule add from 192.170.2.0/24 to 192.170.2.0/24 table SF1 priority 101\n"
        ),
        "expected_ifdown": (
            "# This file is managed by Juju.\n"
            "ip rule del from 192.170.2.0/24 to 192.170.2.0/24 table SF1 priority 101\n"
            "ip route del 6.6.6.0/24 via 10.191.86.2\n"
            "ip route del default via 10.191.86.2 table SF1 dev eth0 metric 101\n"
            "ip route flush table SF1\n"
            "ip rule del table SF1\n"
            "ip route flush cache\n"
        ),
    },
    {
        "input": [
            {"type": "table", "table": "mytable"},
            {
                "type": "route",
                "default_route": True,
                "gateway": "10.205.6.1",
                "table": "mytable",
            },
            {
                "type": "rule",
                "from-net": "10.205.6.0/24",
                "to-net": "1.1.1.1/32",
                "priority": 100,
            },
            {
                "type": "rule",
                "from-net": "10.205.6.0/24",
                "table": "mytable",
                "priority": 101,
            },
        ],
        "expected_ifup": (
            "# This file is managed by Juju.\n"
            "ip route flush cache\n"
            "# Table: name mytable\n"
            "ip route replace default via 10.205.6.1 table mytable\n"
            "ip rule add from 10.205.6.0/24 to 1.1.1.1/32 priority 100\n"
            "ip rule add from 10.205.6.0/24 table mytable priority 101\n"
        ),
        "expected_ifdown": (
            "# This file is managed by Juju.\n"
            "ip rule del from 10.205.6.0/24 table mytable priority 101\n"
            "ip rule del from 10.205.6.0/24 to 1.1.1.1/32 priority 100\n"
            "ip route del default via 10.205.6.1 table mytable\n"
            "ip route flush table mytable\n"
            "ip rule del table mytable\n"
            "ip route flush cache\n"
        ),
    },
]
