A python script that pings an OpenStack environment in-parallel using NovaClient.

To get started:

1. Pull the repository
2. pip install -r requirements.txt
3. Setup os.cnf file

Setup Config
=============
To set up the config the required parameters are below:

  * version=2.1
  * user=
  * password=
  * tenant=
  * auth_url=http://XX.XX.XXX.XXX:5000/v2.0
  * services_list=cinder, nova, glance, neutron, swift
  * daemon_file=
  * output_file=

__Note:__ If you are pinging Swift you must have a container name specified.

Running the script
=================

This script will parse the following arguments from the command-line and pulls additional data from os.cnf

[-s/--services] [-t/--time] || [-d/--daemon]} [-o/--output-file]

--services is a comma-delimited list of services, defaults to the value in os.cnf

--time is the total amount of time in seconds that the script will check the api's of the given services. Defaults to 60.

To test against glance & nova:

    python call_test.py -s glance, nova

Daemon Mode
===========

This script can also be run in daemon mode, where it will continuously run until a given file (specified in os.cnf) is detected (the default is sys.prefix/api.uptime.stop).

To run the script in daemon mode, simply run:

    python call_test.py -d

To end daemon mode, create the file at the specified location.

Time Mode
===========

This script can also be run in time mode, where it will continuously run for the specified number of seconds.

To run the script in time mode, simply run:

    python call_test.py -t 5

Where 5 is the number of seconds.

Output File
===========

A location for the output file can be specified in os.cnf or specified via the command-line via the -o/--output-file option.

If no output file is given the output will be printed to stdout.
