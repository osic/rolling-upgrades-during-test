import time
import sys
import requests
import urllib2
import unittest
import json
import os

from datetime import datetime
from time import sleep
from multiprocessing import Pipe, Process

class ApiUptime(unittest.TestCase):
    def __init__(self, version, username, password, tenant, auth_url):
	self.url = auth_url + '/'
        self.data = '{"auth":{"passwordCredentials":{"username":"' + username + '","password": "' + password + '"},"tenantName": "' + tenant + '"}}'

    def get_token(self):
        get_token = None
        headers = {'Content-Type': 'application/json'}
        url = self.url + 'tokens'
        req = urllib2.Request(url, self.data, {'Content-Type': 'application/json'})

	try:
            f = urllib2.urlopen(req)
	except Exception as e:
	    if any(c in str(e) for c in ('503','404')):
		return False

        for x in f:
            d = json.loads(x)
            token = d['access']['token']['id']
	f.close()
        header = {'X-Auth-Token': token}
        return header

    def get_swift_url(self):
	swift_url = None
        headers = {'Content-Type': 'application/json'}
        url = self.url + 'tokens'
        req = urllib2.Request(url, self.data, {'Content-Type': 'application/json'})

        try:
            f = urllib2.urlopen(req)
        except Exception as e:
	    print e 
	    if any(c in str(e) for c in ('503','404')):
                return False

	try:
            for x in f:
                d = json.loads(x)
                for j in d['access']['serviceCatalog']:
                    if j['name'] == 'swift':
                        for k in j['endpoints']:
                            swift_url = k['internalURL']
	except Exception as e:
	    print e
	    f.close()
	    return False
        f.close()

	if swift_url == None: return False
	
        return swift_url + '/'

    def create_container(self, url, headers, container_name):
        response = str(requests.put(url + container_name, headers=headers))
	if any(c in response for c in ('201','202')):
	    return True
        return False

    def create_object(self, url, headers, container_name, object_name):
        response = str(requests.put(url + container_name + '/' + object_name, headers=headers))
	if any(c in response for c in ('201','202')):
            return True
        return False

    def delete_object(self, url, headers, container_name, object_name):
	url = url + container_name + '/' + object_name
	response = str(requests.delete(url, headers=headers))

        return response
	    
    def delete_container(self, url, headers, container_name):
	url = url + container_name
	response = str(requests.delete(url, headers=headers))

        return response


    def write_status(self, service, status, build_start):
	    status = {"service": service, "status": status, "timestamp": build_start}
            f = open('%s/output/swift_status.json' % os.environ['HOME'],'a')
            f.write(json.dumps(status) + "\n")
            f.close()

    def report(self, conn, service, success, total, start_time, end_time, down_time, duration):
	success_pct = 100 * (float(success)/total)

        uptime_pct = 100 - round((float(down_time)/duration) * 100, 2)

        print "*** Swift uptime pct: " + str(uptime_pct) + "% ***"

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

    def test_create_delete_container(self, conn, service, times, container_name, object_name):
	output = []
        start_time = 0
        total_time = 0
        total_down_time = 0
	new_container = ''
	new_object = ''
	duration = 0
	object_delete = ''
	container_delete = ''
        container_name = container_name
        object_name = object_name

        if times is True:
            times = xrange(sys.maxint)
        else:
            times = xrange(times)

	open('%s/output/swift_status.json' % os.environ['HOME'],'w')

	headers = self.get_token()
	swift_url = self.get_swift_url()

	build_start = str(datetime.now().strftime("%Y-%m-%dT%H:%M:%S%z"))
        
        for _ in times:
	    #Begin accruing time for down/up time
	    start_time = time.time()

            if conn.poll() and conn.recv() == "STOP":
                break

	    try:
                if headers == False:
                    print "Trouble getting token"
		    self.assertNotEqual(headers,False)
                if swift_url == False:
                    print "Please check if you have Swift installed."
                    self.assertNotEqual(swift_url,False)

		#Create new container
		new_container = self.create_container(swift_url, headers, container_name)
		self.assertTrue(new_container)

		#Create new object
		new_object = self.create_object(swift_url, headers, container_name, object_name)
		self.assertTrue(new_object)

		#Delete Object
	        object_delete = self.delete_object(swift_url, headers, container_name, object_name)
		self.assertIn('204',object_delete)

		#Delete Container
		container_delete = self.delete_container(swift_url, headers, container_name)
		self.assertIn('204',container_delete)

		self.write_status(service, 1, datetime.now().strftime("%Y-%m-%dT%H:%M:%S%z"))

		#Send Success
		output.append(True)
		sleep(1)
                done_time = time.time()
	    except Exception as e:
		#Print error
		print "Failed Swift: " + str(e)

                #Send Fail and write status
                output.append(False)
		self.write_status(service, 0, datetime.now().strftime("%Y-%m-%dT%H:%M:%S%z"))

		#Record downtime accrual and write status
		sleep(1)
                done_time = time.time()
		total_down_time += (done_time - start_time)

		#Get another token if necessary
		if headers == False or new_container or new_object:
		    print "Attempting to retrieve token and Swift Url"
                    headers = self.get_token()
		    swift_url = self.get_swift_url()
		elif '401' in object_delete or '401' in container_delete:
                    print "Attempting to retrieve token and Swift Url"
                    headers = self.get_token()
                    swift_url = self.get_swift_url()

	    #Aggregating total run time of test
            duration += (done_time-start_time)

        self.report(conn, service, sum(output),
                    len(output), str(build_start), str(datetime.now().strftime("%Y-%m-%dT%H:%M:%S%z")), total_down_time,duration)
