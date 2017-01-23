import logging
import sys
import time
import json
import requests
import urllib2
import unittest
import os

from datetime import datetime
from multiprocessing import Pipe, Process
from time import sleep

class ApiUptime(unittest.TestCase):
    def __init__(self, version, username, password, tenant, auth_url):
        self.url = auth_url + '/'
	self.data = '{"auth":{"identity":{"methods": ["password"],"password": {"user":{"name": "' + username + '","domain":{"name":"Default"},"password": "' + password + '"}}}}}'


    def get_token(self):
        get_token = None
        headers = {'Content-Type': 'application/json'}
        url = self.url + 'auth/tokens'
        req = requests.post(url, self.data)

        try:
	    f = req.headers
        except Exception as e:
            if ('503' or '404') in str(e):
                return False, False

        token = f['X-Subject-Token']
	header = {'X-Auth-Token': token, 'X-Subject-Token': token}
        return header, token

    def validate_token(self, header, token):
        url = self.url + 'auth/tokens'
        req = requests.get(url,headers=header)

	f = req.headers

        if token == f['X-Subject-Token']:
	    return True
	else:
	    return False

    def write_status(self, service, status, build_start):
	    status = {"service": service, "status": status, "timestamp": build_start}
            f = open('%s/output/keystone_status.json' % os.environ['HOME'],'a')
            f.write(json.dumps(status) + "\n")
            f.close()

    def report(self, conn, service, success, total, start_time, end_time, down_time,duration):
        success_pct = 100 * (float(success)/total)
	
	uptime_pct = 100 - round((float(down_time)/duration * 100), 2)

	print "*** Keystone uptime pct: " + str(uptime_pct) + "% ***"

        conn.send({
            service: {
		"project": service,
                "success_pct": success_pct,
                "total_requests": total,
                "successful_requests": success,
                "failed_requests": total - success,
                "start_time": start_time,
                "end_time": end_time,
		"uptime_pct": uptime_pct,
		"down_time": down_time}})
        conn.close()

    def test_create_validate_token(self, conn, service, times):
	output = []
        start_time = 0
        done_time = 0
	start_time = 0
        total_time = 0
        total_down_time = 0
	duration = 0

        if times is True:
            times = xrange(sys.maxint)
        else:
            times = xrange(times)
        pipes = []

	open('%s/output/keystone_status.json' % os.environ['HOME'],'w')

	build_start = str(datetime.now().strftime("%Y-%m-%dT%H:%M:%S%z"))

	for _ in times:
            if conn.poll() and conn.recv() == "STOP":
                break

	    start_time = time.time()

	    try:

		#Get token
		header, token = self.get_token()
		self.assertNotEqual(header,False)

		#Validate token
		validate = self.validate_token(header, token)
		self.assertNotEqual(validate,False)
	       
	        #Write to logfile
		self.write_status(service, 1, str(datetime.now().strftime("%Y-%m-%dT%H:%M:%S%z")))

                #Send success
                output.append(True)

		sleep(1)
		done_time = time.time()
	    except Exception as e:
		print "Failed Keystone: " + str(e)

		self.write_status(service, 0, str(datetime.now().strftime("%Y-%m-%dT%H:%M:%S%z")))

                #Send Fail
                output.append(False)

		#Record downtime accrual and write status
		sleep(1)
		done_time = time.time()
		total_down_time += (done_time - start_time)

	    #Aggregating run time of test
	    duration += (done_time - start_time)

        self.report(conn, service, sum(output),
                    len(output), str(build_start), 
		    str(datetime.now().strftime("%Y-%m-%dT%H:%M:%S%z")), total_down_time,duration)
