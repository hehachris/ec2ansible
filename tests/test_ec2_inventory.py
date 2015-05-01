import json
from moto import mock_ec2

try:
    import unittest2 as unittest
except ImportError:
    import unittest

import boto.ec2
import logging
import sys
from ec2ansible import Ec2InventoryGenerator


DEFAULT_CONFIG = {
    'default_role': 'default',

    'regions': 'us-east-1',
    'regions_exclude': 'us-gov-west-1,cn-north-1',

    'cache_path': '~/.ansible/tmp/ec2ansible.json',
    'cache_max_age': 300,

    'instance_filters': '',
}

INV_SINGLE_HOST = {
    "all": {
        "children": [
            "use1"
        ],
        "hosts": [],
        "vars": {}
    },
    "use1": {
        "children": [
            "use1_web_apache"
        ],
        "hosts": [],
        "vars": {}
    },
    "use1_web_apache": {
        "children": [],
        "hosts": [
            "10.0.0.1"
        ],
        "vars": {}
    },
    "web": {
        "children": [
            "use1_web_apache"
        ],
        "hosts": [],
        "vars": {}
    },
    "web_apache": {
        "children": [
            "use1_web_apache"
        ],
        "hosts": [],
        "vars": {}
    }
}

INV_HIERARCHICAL = {
    "all": {
        "children": [
            "use1"
        ],
        "hosts": [],
        "vars": {}
    },
    "use1": {
        "children": [
            "use1_web_proxy_haproxy",
            "use1_web_apache",
            "use1_web_proxy_nginx"
        ],
        "hosts": [],
        "vars": {}
    },
    "use1_web_apache": {
        "children": [],
        "hosts": [
            "10.0.0.1"
        ],
        "vars": {}
    },
    "use1_web_proxy_haproxy": {
        "children": [],
        "hosts": [
            "10.0.0.3"
        ],
        "vars": {}
    },
    "use1_web_proxy_nginx": {
        "children": [],
        "hosts": [
            "10.0.0.2"
        ],
        "vars": {}
    },
    "web": {
        "children": [
            "use1_web_proxy_haproxy",
            "use1_web_apache",
            "use1_web_proxy_nginx"
        ],
        "hosts": [],
        "vars": {}
    },
    "web_apache": {
        "children": [
            "use1_web_apache"
        ],
        "hosts": [],
        "vars": {}
    },
    "web_proxy": {
        "children": [
            "use1_web_proxy_haproxy",
            "use1_web_proxy_nginx"
        ],
        "hosts": [],
        "vars": {}
    },
    "web_proxy_haproxy": {
        "children": [
            "use1_web_proxy_haproxy"
        ],
        "hosts": [],
        "vars": {}
    },
    "web_proxy_nginx": {
        "children": [
            "use1_web_proxy_nginx"
        ],
        "hosts": [],
        "vars": {}
    }
}

class TestEc2Inventory(unittest.TestCase):
    def setUp(self):
        super(TestEc2Inventory, self).setUp()

        logging.basicConfig(stream=sys.stdout, level=logging.DEBUG)
        self.log = logging.getLogger("LOG")

    @mock_ec2
    def test_single_host(self):
        self._add_servers('ami-1234abcd', '10.0.0.1', {'Role': 'web_apache'})

        inv = Ec2InventoryGenerator(DEFAULT_CONFIG).generate()

        self.log.debug(inv.to_json(indent=4))
        self.log.debug(INV_SINGLE_HOST)

        self.assertDictEqual(inv, INV_SINGLE_HOST)

    @mock_ec2
    def test_hierarchical_grouping(self):
        self._add_servers('ami-1234abcd', '10.0.0.1', {'Role': 'web_apache'})
        self._add_servers('ami-1234abcd', '10.0.0.2', {'Role': 'web_proxy_nginx'})
        self._add_servers('ami-1234abcd', '10.0.0.3', {'Role': 'web_proxy_haproxy'})

        inv = Ec2InventoryGenerator(DEFAULT_CONFIG).generate()

        self.log.debug(json.dumps(inv, indent=4))
        self.log.debug(json.dumps(INV_HIERARCHICAL, indent=4))

        self.assertDictEqual(inv, INV_HIERARCHICAL)

    def _add_servers(self, ami_id, ip=None, tags={}, count=1, region='us-east-1'):
        conn = boto.ec2.EC2Connection(region=boto.ec2.get_region(region),)

        for i in range(count):
            reservation = conn.run_instances(ami_id, private_ip_address=ip)
            instance = reservation.instances[0]

            for k, v in tags.iteritems():
                instance.add_tag(k, v)
