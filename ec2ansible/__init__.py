import ConfigParser
from datetime import time
import json
import os
from boto import ec2


class Ec2Ansible(object):
    def __init__(self, default_config, ini_path=None):
        self.config = default_config
        self.ini_path = ini_path

        self.regions = {}
        self.vars = {}
        self.inventory = {}

        self._load_config()
        self._load_regions()

    def generate(self):
        """
        Generate Ansible inventory
        :rtype: dict
        """
        if self.config['cache_max_age'] > 0 \
                and os.path.isfile(self.config['cache_path']) \
                and time() - os.path.getmtime(self.config['cache_path']) < self.config['cache_max_age']:
            return self._read_cache()

        regional_children = set()

        for key, region in self.regions.iteritems():
            self._add_hosts_from_region_by_role(region, key)
            regional_children.add(key)

        # Top-most group
        self._add_group_children('all', regional_children)

        return self.to_json()

    def to_json(self, indent=4, sort_keys=True):
        """
        Returns JSON data
        :type indent: int
        :type sort_keys: bool
        :rtype: string
        """
        return json.dumps(self.inventory, indent=indent, sort_keys=sort_keys)

    def _add_hosts_from_region_by_role(self, region, region_key, role_tag_key='Role'):
        """
        Add host from an AWS region with it's role tag value as group
        :type region: boto.ec2.regioninfo.RegionInfo
        :type region_key: string
        :type role_tag_key: string
        :rtype: Ec2Inventory
        """
        regional_roles = set()
        role_hierarchy_map = {}
        role_children_map = {}

        region_info = ec2.get_region(region)

        conn = ec2.EC2Connection(region=region_info)
        for r in conn.get_all_instances():
            for i in r.instances:
                if i.state != 'running':
                    continue

                if role_tag_key in i.tags:
                    role = i.tags[role_tag_key]
                else:
                    role = self.config['default_role']

                # The lowest level group that contains hosts
                regional_role = region_key + '_' + role
                regional_roles.add(regional_role)

                # Group by role (web_server -> use1_web_server)
                role_children_map.setdefault(role, set()).add(regional_role)

                # Group by role hierarchy (worker -> worker_gearman -> use1_worker_gearman)
                if '_' in role:
                    prefix = ''
                    underscore = ''
                    for segment in role.split('_')[:-1]:
                        prefix += underscore + segment
                        role_hierarchy_map.setdefault(prefix, set()).add(regional_role)
                        underscore = '_'

                self._add_group_instance(regional_role, i)

        self._add_group_children(region_key, regional_roles) \
            ._add_mapped_children(role_children_map) \
            ._add_mapped_children(role_hierarchy_map)

        return self

    def _get_host(self, instance):
        """
        Get host of instance
        :type instance: Instance
        :rtype: string
        """
        if instance.vpc_id is None:
            return instance.ip_address
        else:
            return instance.private_ip_address

    def _group_by_role_hierarchy(self, region_key, role):
        groups = set()

        prefix = ''
        underscore = ''

        for segment in role.split('_')[:-1]:
            prefix += underscore + segment
            groups.add(region_key + '_' + role)
            underscore = '_'

        return groups

    def _add_mapped_children(self, children_map):
        """
        Add children to a role group
        :type children_map: dict
        """
        for grp, children in children_map.items():
            self._add_group_children(grp, children)

        return self

    def _add_group_instance(self, group_name, instance):
        """
        Add instance to a group
        :type group_name: string
        :type instance: Instance
        :rtype: Ec2Inventory
        """
        host = self._get_host(instance)
        return self._add_group_host(group_name, host)

    def _load_regions(self):
        valid_regions = ec2.regions()

        if self.config['regions'] == 'all':
            for r in valid_regions:
                if r.name not in self.config['regions_exclude']:
                    self.regions[self._get_region_key(r.name)] = r.name
        else:
            for r in valid_regions:
                if r.name in self.config['regions']:
                    self.regions[self._get_region_key(r.name)] = r.name

    def _get_region_key(self, region):
        """
        Convert region name into region key (eg. us-east-1 -> use1)
        :type region: string
        :rtype: string
        """
        segments = region.split('-')

        key = segments[0]

        for direction in ['north', 'south', 'east', 'west']:
            if direction in region:
                key += direction[:1]

        key += segments[2]
        return key

    def _load_config(self):
        if self.ini_path is not None:
            ini = ConfigParser.ConfigParser()
            ini.read(self.ini_path)

            for k, v in self.config.iteritems():
                if ini.has_option('ec2', k):
                    self.config[k] = ini.get('ec2', k)

        self.config['cache_max_age'] = int(self.config['cache_max_age'])

    def _save_cache(self):
        fh = open(self.config['cache_path'], 'w')
        fh.write(self.to_json(indent=0))
        fh.close()

    def _read_cache(self):
        data = ''
        with open(self.config['cache_path'], 'r') as f:
            data += f.read()

        return data

    def _add_group_host(self, group_name, host):
        """
        Add host to a group
        :type group_name: string
        :type host: string
        :rtype: Ec2Inventory
        """
        self._create_group(group_name)
        self.inventory[group_name]['hosts'].append(host)

        return self

    def _add_group_children(self, group_name, children):
        """
        Add children to a group
        :type group_name: string
        :type children: list|set
        :rtype: Ec2Inventory
        """
        return self._add_group_child(group_name, children)

    def _add_group_child(self, group_name, child):
        """
        Add child to a group
        :type group_name: string
        :type child: list|set|str
        :rtype: Ec2Inventory
        """
        self._create_group(group_name)

        if isinstance(child, basestring):
            child = [child]

        for grp in child:
            self.inventory[group_name]['children'].append(grp)

        return self

    def _create_group(self, name):
        """
        Create group if not exists
        :type name: string
        :rtype: Ec2Inventory
        """
        if name in self.inventory:
            return

        if name in self.vars:
            grp_vars = self.vars[name]
        else:
            grp_vars = {}

        self.inventory[name] = {
            'hosts': [],
            'vars': grp_vars,
            'children': []
        }

        return self
