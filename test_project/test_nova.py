import time
import sys
import unittest
<<<<<<< HEAD
import requests
import urllib2
=======
>>>>>>> ac4c619a98409559f9e556aa229c30dea508783c
import json

from datetime import datetime
from time import sleep
from multiprocessing import Pipe, Process

class ApiUptime(unittest.TestCase):
    def __init__(self, version, username, password, tenant, auth_url):
	self.server_id = None
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

    def get_nova_url(self):
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
                    if j['name'] == 'nova':
                        for k in j['endpoints']:
                            nova_url = k['internalURL']
	except Exception as e:
	    print e
	    f.close()
	    return False
        f.close()

	if nova_url == None: return False

        return nova_url + '/'

    def _wait_until(self, url, headers):
	get = None
	start_time = time.time()

	while get  <> 'ACTIVE':
	    #Sending requests to OS
	    response = requests.get(url, headers=headers)

	    #Analyzing response
            if '200' in str(response):
                get = response.json()['server']['status']
                build_time = int(time.time() - start_time)
                if build_time > 15 or get == 'ERROR':
                    return get
	    else:
		return get
	return get

    def write_status(self, service, status, build_start):
            status = {"service": service, "status": status, "timestamp": build_start}
<<<<<<< HEAD
            f = open('../output/nova_status.json','a')
=======
            f = open('/root/output/nova_status.txt','a')
>>>>>>> ac4c619a98409559f9e556aa229c30dea508783c
            f.write(json.dumps(status) + "\n")
            f.close()

    def create_server(self,url,headers,tenant_id,name, image, flavor, data):
	url = url + tenant_id + '/servers'
	response = requests.post(url, data=data,headers=headers)

	if any(c in str(response) for c in ('201','202')):
            pass
	elif '401' in str(response):
	    return str(response)
	else:
            return False

	#Wait until active
	response = response.json()
	self.server_id = response['server']['id']
        status = self._wait_until(url + '/' + self.server_id, headers)
	return status

    def delete_server(self, url, headers, tenant_id):
	url = url + tenant_id + '/servers/' + self.server_id
	response = str(requests.delete(url, headers=headers))

	return response

    def report(self, conn, service, success, total, start_time, end_time, down_time, duration):
        success_pct = 100 * (float(success)/total)

	uptime_pct = 100 - round((float(down_time)/duration * 100), 2)

	print "*** Nova uptime pct: " + str(uptime_pct) + "% ***"

        conn.send({
            service: {
		"project": service,
                "success_pct": success_pct,
                "total_requests": total,
                "successful_requests": success,
                "failed_requests": total - success,
                "start_time": start_time,
                "end_time": end_time,
		"down_time": down_time,
		"uptime_pct": uptime_pct}})
        conn.close()

    def test_create_delete_server(self, conn, service, times, tenant_id=None, flavor=None, name=None, image=None):
        output = []
        start_time = 0
        status = None
        down_time = None
        server = ''
	total_down_time = 0
	server_delete = ''
	test_finish_time = None
	duration = 0

	server_data = '{"server":{"name": "' + name + '", "imageRef": "' + image + '", "flavorRef": "' + flavor + '"}}'

	if times is True:
            times = xrange(sys.maxint)
        else:
            times = xrange(times)

<<<<<<< HEAD
        open('../output/nova_status.json','w')

	headers = self.get_token()
        nova_url = self.get_nova_url()

	build_start = str(datetime.now().strftime("%Y-%m-%dT%H:%M:%S%z"))
=======
        open('/root/output/nova_status.txt','w')
>>>>>>> ac4c619a98409559f9e556aa229c30dea508783c

        for _ in times:

            if conn.poll() and conn.recv() == "STOP":
                break

	    start_time = time.time()

	    try:
                if headers == False:
                    print "Trouble getting token"
		    self.assertNotEqual(headers,False)
                if nova_url == False:
                    print "Please check if you have Nova installed."
                    self.assertNotEqual(swift_url,False)

                #Create server
                server = self.create_server(nova_url,headers,tenant_id,name,image,flavor,server_data)

<<<<<<< HEAD
		#If status is active send true else send false
                self.assertTrue(server == 'ACTIVE')
=======
                #Record timestamp for status
                status_timestamp = str(datetime.datetime.now().strftime("%Y-%m-%dT%H:%M:%S%z"))
>>>>>>> ac4c619a98409559f9e556aa229c30dea508783c

		#Delete server
                server_delete = self.delete_server(nova_url, headers,tenant_id)
		self.assertIn('204',server_delete)

                #Write to status log
                self.write_status(service, 1, str(datetime.now().strftime("%Y-%m-%dT%H:%M:%S%z")))
                output.append(True)

		#Done for aggregating total test duration
		done_time = time.time()
            except Exception as e:
	   	print e

		if '401' in server or '401' in server_delete:
		    headers = False
                elif server:
                    #Delete server
		    server_delete = self.delete_server(nova_url, headers,tenant_id)

		    #If server doesn't delete we need to try until it does
		    while '204' not in server_delete:
                        #Write to status log
                        self.write_status(service, 0, str(datetime.now().strftime("%Y-%m-%dT%H:%M:%S%z")))
                        output.append(False)

                        if conn.poll() and conn.recv() == "STOP":
                            break

                        if '401' in server_delete:
                            print "Attempting to retrieve token and url"
                            headers = self.get_token()
                            nova_url = self.get_nova_url()

		        print "Server delete failed.  Attempting to delete server"
			sleep(10)
                        server_delete = self.delete_server(nova_url, headers,tenant_id)

                #Record down time
                status_timestamp = str(datetime.now().strftime("%Y-%m-%dT%H:%M:%S%z"))

                #Write to status log
                self.write_status(service, 0, status_timestamp)
		output.append(False)

		if headers == False:
		    print "Attempting to retrieve token and url"
		    headers = self.get_token()
		    nova_url = self.get_nova_url()

                done_time = time.time()
                total_down_time += (float(done_time) - start_time)

	    #Aggregating total run time of test
	    duration += (float(done_time)-start_time)

        self.report(conn, service, sum(output),
                    len(output), str(build_start), str(datetime.now().strftime("%Y-%m-%dT%H:%M:%S%z")), total_down_time, duration)

