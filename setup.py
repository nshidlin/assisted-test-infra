from setuptools import setup, find_packages

setup(
    name='assistedtestinfra',
    version='0.1.0',    
    description='Infrastructure for running assisted-installer tests',
    url='https://github.com/openshift/assisted-test-infra',
    packages=find_packages(),
    include_package_data=True,
    entry_points={
        'console_scripts': ['run-assisted-tests=assisted_test_infra.run_assisted_tests:main']
    },
    # scripts=['run-assisted-tests.py'],
    install_requires=[
        'boto3==1.16.25',
        'dnspython==2.0.0',
        'ipython==7.10',
        'ipdb==0.13.4',
        'libvirt-python==6.9.0',
        'pre-commit==2.9.2',
        'pyyaml==5.3.1',
        'python-terraform==0.10.1',
        'kubernetes==12.0.1',
        'munch==2.5.0',
        'requests==2.24.0',
        'retry==0.9.2',
        'tqdm==4.54.0',
        'waiting==1.4.1',
        'netaddr==0.8.0',
        'pytest==6.1.2',
        'python-dateutil==2.8.1',
        'jira==2.0.0',
        'tabulate==0.8.7',
        'paramiko==2.7.2',
        'openshift-client==1.0.9',
        'Jinja2==2.10.1',
        'strato-skipper==1.26.0'
    ],
)