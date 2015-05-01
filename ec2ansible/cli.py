import argparse
import os
from ec2ansible import Ec2InventoryGenerator
from os.path import expanduser

DEFAULT_CONFIG = {
    'default_role': 'default',

    'regions': 'all',
    'regions_exclude': 'us-gov-west-1,cn-north-1',

    'cache_path': '~/.ansible/tmp/ec2ansible.json',
    'cache_max_age': 300,

    'instance_filters': '',
}


def main():
    args = parse_args()

    init_path = expanduser('~') + '/.ec2ansible'

    if not os.path.isfile(init_path):
        init_path = None

    inv = Ec2InventoryGenerator(DEFAULT_CONFIG, init_path).generate()
    print inv.to_json(0)


def parse_args():
    parser = argparse.ArgumentParser(description='Generate EC2 inventory for Ansible')
    parser.add_argument('--list', action='store_true', help='List instances (default behavior)')

    return parser.parse_args()
