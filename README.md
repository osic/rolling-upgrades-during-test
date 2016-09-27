A python script that runs api scenarios on an OpenStack environment in-parallel using python-novaclient, python-swiftclient, & python-keystoneclient.  The goal is to test all services of Nova, Swift, and Keystone.

To get started:

1. Pull the repository (git clone https://github.com/lamarwhitej/test_rolling_upgrades_during.git)
2. cd test_rolling_upgrades_during
2. pip install -r requirements.txt
3. Setup os.cnf file

Setup Config
=============
To set up the config the required parameters are below:

  * version=2.1
  * user= __(required)__
  * password= __(required)__
  * tenant= __(required)__
  * auth_url=http://XX.XX.XXX.XXX:5000/v2.0
  * keystone_auth_url=http://xx.xx.xxx.xxx:5000/v3
  * services_list=nova, swift, keystone
  * image_id= __(required)__
  * instance_name=Test_DeleteInstance
  * container_name=CONTAINER
  * object_name=test_Object
  * flavor_size=42
  * daemon_file=
  * output_file=output.txt

Running the script
=================

This script will parse the following arguments from the command-line and pulls additional data from os.cnf

[-s/--services] [-t/--time] || [-d/--daemon]} [-o/--output-file]

--services is a comma-delimited list of services, defaults to the value in os.cnf

--time is the total amount of interations that the script will check the api's of the given services. Defaults to 60.

--daemon mode will run until the file api.uptime.stop is created

Example to run swift during test in Daemon mode (recommended):

    python call_test.py -d -s swift

Time Mode
===========

This script can also be run in time mode, where it will continuously run for the specified number of seconds (or iterations).

To run the script in time mode, simply run:

    python call_test.py -t 5 -s swift

Where 5 is the number of seconds (or iterations).

Output File
===========

A location for the output file can be specified in os.cnf or specified via the command-line via the -o/--output-file option.

If no output file is given the output will be printed to stdout.  This file contains a json summary containing results of the run.

Status Files
============

There are also 3 files nova_status, swift_status, keystone_status.  These files are populated after each iteration of the test and provide a status of - 0 or 1 - denoting whether the service is up or down.
