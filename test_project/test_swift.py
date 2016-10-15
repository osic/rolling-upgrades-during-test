import datetime
import time
import sys
import requests
import urllib2
import unittest
import json

from time import sleep
from multiprocessing import Pipe, Process
from swiftclient import client as swiftclient

class ApiUptime(unittest.TestCase):
    def __init__(self, version, username, password, tenant, auth_url):
        self.swift = swiftclient.Connection(authurl=auth_url, user=username, tenant_name=tenant, key=password, auth_version='2')
	self.url = auth_url + '/'
        self.data = '{"auth":{"passwordCredentials":{"username":"' + username + '","password": "' + password + '"},"tenantName": "' + tenant + '"}}'

    def get_token(self):
        get_token = None
        headers = {'Content-Type': 'application/json'}
        url = self.url + 'tokens'
        req = urllib2.Request(url, self.data, {'Content-Type': 'application/json'})
        f = urllib2.urlopen(req)

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
        f = urllib2.urlopen(req)
	
	try:
            for x in f:
                d = json.loads(x)
                for j in d['access']['serviceCatalog']:
                    if j['name'] == 'swift':
                        for k in j['endpoints']:
                            swift_url = k['internalURL']
	except:
	    f.close()
	    return False
        f.close()
        return swift_url + '/'

    def create_container(self, url, headers, container_name):
        response = str(requests.put(url + container_name, headers=headers))
        if '503' in response:
            return False
        elif '404' in response:
            return False
        return True

    def create_object(self, url, headers, container_name, object_name):
        response = str(requests.put(url + container_name + '/' + object_name, headers=headers))
        if '503' in response:
            return False
        return True

    def delete_object(self, container_name, object_name):
        try:
            self.swift.delete_object(container=container_name,obj=object_name)
        except Exception as e:
	    print e
	    return True
	return False
	    
    def delete_container(self, container_name):
	try:
	    self.swift.delete_container(container=container_name)
        except Exception as e:
	    print e
	    return True
	return False

    def write_status(self, service, status, build_start):
	    status = str({"service": service, "status": status, "timestamp": build_start})
            f = open('output_json/swift_status.txt','a')
            f.write(status + "\n")
            f.close()

    def report(self, conn, service, success, total, start_time, end_time, down_time):
	#Avoiding division by 0
        if total < 1: 
	    total = 1

	uptime_pct = 100 * (float(success)/total)
        conn.send({
            service: {
		"project": service,
                "uptime_pct": uptime_pct,
                "total_requests": total,
                "successful_requests": success,
                "failed_requests": total - success,
                "start_time": start_time,
                "end_time": end_time,
		"down_time": down_time}})
        conn.close()

    def test_create_delete_container(self, conn, service, times, container_name, object_name):
	output = []
        start_time = datetime.datetime.now()
        down_time = None
        total_time = 0
        total_down_time = 0
	new_container = None
	new_object = None
        container_name = container_name
        object_name = object_name

        if times is True:
            times = xrange(sys.maxint)
        else:
            times = xrange(times)

	open('output_json/swift_status.txt','w')

	headers = self.get_token()
	swift_url = self.get_swift_url()
        
        for _ in times:
	    if swift_url == False:
		print "Please check if you have Swift installed."
		break
            if conn.poll() and conn.recv() == "STOP":
                break
            
	    build_start = str(datetime.datetime.now())
	    try:

		#Create new container
		new_container = self.create_container(swift_url, headers, container_name)
		self.assertTrue(new_container)

		#Create new object
		new_object = self.create_object(swift_url, headers, container_name, object_name)
		self.assertTrue(new_object)
		
		#Delete Object
	        failed_delete = self.delete_object(container_name, object_name)
		self.assertFalse(failed_delete)

		#Delete Container
		failed_delete = self.delete_container(container_name)
		self.assertFalse(failed_delete)
		
		self.write_status(service, 1, build_start)

		#Send Success
		output.append(True)
		sleep(1)
	    except Exception as e:
		print e
		#Send Fail
		output.append(False)
		self.write_status(service, 0, build_start)
		sleep(1)

        self.report(conn, service, sum(output),
                    len(output), str(start_time), str(datetime.datetime.now()), total_down_time)
