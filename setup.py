from setuptools import setup, find_packages
import sys, os

version = '0.1.1'

install_requires = ['boto']

if sys.version_info < (2, 7, 0):
    install_requires.append('argparse')

setup(name='ec2ansible',
      version=version,
      description="AWS EC2 inventory generator for Ansible",
      long_description="""\
""",
      classifiers=[], # Get strings from http://pypi.python.org/pypi?%3Aaction=list_classifiers
      keywords='ansible ec2 aws devops',
      author='Chris Lam',
      author_email='chris@knetgb.com',
      url='https://github.com/hehachris/ec2ansible',
      license='MIT License',
      packages=find_packages(exclude=['ez_setup', 'examples', 'tests']),
      include_package_data=True,
      zip_safe=True,
      install_requires=install_requires,
      entry_points=dict(console_scripts=['ec2ansible=ec2ansible.cli:main']),
      )
