import time
import sys
import unittest
import requests
import urllib2
import json
import os

from datetime import datetime
from time import sleep
from multiprocessing import Pipe, Process

class ApiUptime(unittest.TestCase):
    def __init__(self, version, username, password, tenant, auth_url):
	self.server_id = None
	self.url = auth_url + '/'
        self.data = '{"auth":{"passwordCredentials":{"username":"' + username + '","password": "' + password + '"},"tenantName": "' + tenant + '"}}'
	self.error_output = None

    def get_token(self):
        get_token = None
        headers = {'Content-Type': 'application/json'}
        url = self.url + 'tokens'
        req = urllib2.Request(url, self.data, {'Content-Type': 'application/json'})

	try:
            f = urllib2.urlopen(req)
	except Exception as e:
	    if any(c in str(e) for c in ('503','404')):
		self.error_output = str(e) + " line 30"
		return False
	    else:
		self.error_output = str(e) + " line 33"
		return False		

        for x in f:
            d = json.loads(x)
            token = d['access']['token']['id']
	f.close()
        header = {'X-Auth-Token': token}
        return header

    def get_nova_url(self):
	nova_url = None
        headers = {'Content-Type': 'application/json'}
        url = self.url + 'tokens'
        req = urllib2.Request(url, self.data, {'Content-Type': 'application/json'})

        try:
            f = urllib2.urlopen(req)
        except Exception as e:
	    if any(c in str(e) for c in ('503','404')):
		self.error_output = str(e) + " line 53"
                return False
	    else:
		self.error_output = str(e) + " line 56"
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
	build_time = 0
	avg_build_time = 0

	while get  <> 'ACTIVE':
	    #Sending requests to OS
	    response = requests.get(url, headers=headers)

	    #Analyzing response
            if '200' in str(response):
                get = response.json()['server']['status']
                build_time = int(time.time() - start_time)
                if build_time > 29 or get == 'ERROR':
                    return str(get), 0
	    else:
		get = 'ERROR'
		return get, 0

	#Get average build time
	avg_build_time = build_time

	#Creating VM every 30 seconds so wait
	while build_time <= 29:
	    build_time = int(time.time() - start_time)

	return get, avg_build_time

    def write_status(self, service, status, build_start, error, total_down, duration, test_start ):
            status = {"service": service, "status": status, "timestamp": build_start, "error": error, "total_down": total_down, "duration": duration, "time_run_started": test_start}
            f = open('../output/nova_status.json','a')
            f.write(json.dumps(status) + "\n")
            f.close()


    def _delete_server_list(self, nova_url, headers, name=None):
        response = requests.get(nova_url + 'servers', headers=headers)

	while any(c in str(response) for c in ('201','200','202')):

	    response = response.json()

	    for i in response['servers']:
	        if i['name'] == name:
	            server_delete = self.delete_server(nova_url, headers, i['id'])

            if '401' in str(response):
                print "Getting token, it may have expired."
                self.headers = self._get_token()
                return True
            return False


    def create_server(self,url,headers,name, image, flavor, data):
	avg_build_time = 0
	url = url + '/servers'
	response = requests.post(url, data=data,headers=headers)

	if any(c in str(response) for c in ('201','202')):
            pass
        elif any(c in str(response) for c in ('401','403','400')):
            self.error_output = str(response) + " creating server on line 118"
            return str(response), avg_build_time
        elif '500' in str(response):
            self.error_output = str(response) + " creating server on line 122 (500)"
	    try:
                response = response.json()
                self.server_id = response['server']['id']
            except Exception as e:
	        pass
            return 'ERROR', avg_build_time
	else:
            self.error_output = str(response) + " creating server on line 126"
            try:
                response = response.json()
                self.server_id = response['server']['id']
            except Exception as e:
                pass
            return str(response), avg_build_time

	#Wait until active
	response = response.json()
	self.server_id = response['server']['id']
        status, avg_build_time = self._wait_until(url + '/' + self.server_id, headers)
	return status, avg_build_time

    def delete_server(self, url, headers, server_id=None):

	if server_id:
	    pass
	else:
	    server_id = self.server_id

	if server_id == None:
	    return '204'
	else:
	    url = url + '/servers/' + str(server_id)
	    response = str(requests.delete(url, headers=headers))
	
	    if '204' not in response:
	        self.error_output = "Error deleting server: " + str(server_id) + " on line 146"
	return response

    def report(self, conn, service, success, total, start_time, end_time, down_time, duration, avg_build_time):
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
		"avg_build_time": avg_build_time,
		"uptime_pct": uptime_pct}})
        conn.close()

    def test_create_delete_server(self, conn, service, times, flavor=None, name=None, image=None):
        output = []
        start_time = 0
        status = None
        down_time = None
        server = ''
	total_down_time = 0
	avg_build_time = 0
	server_delete = ''
	test_finish_time = None
	duration = 0

	server_data = '{"server":{"name": "' + name + '", "imageRef": "' + image + '", "flavorRef": "' + flavor + '"}}'

	if times is True:
            times = xrange(sys.maxint)
        else:
            times = xrange(times)

        open('../output/nova_status.json','w')

	headers  = self.get_token()
        nova_url = self.get_nova_url()

	build_start = str(datetime.now().strftime("%Y-%m-%dT%H:%M:%S%z"))

        for _ in times:

            if conn.poll() and conn.recv() == "STOP":
		print "Ending Nova during testing."
                break
	    elif os.path.isfile('/usr/during.uptime.stop'):
		print "Ending Nova during testing."
                break

	    start_time = time.time()

	    try:
                if headers == False:
                    print "Trouble getting token"
		    self.assertNotEqual(headers,False)
                if nova_url == False:
                    print "Please check if you have Nova installed."
                    self.assertNotEqual(nova_url,False)

                #Create server
                server, build_time = self.create_server(nova_url,headers,name,image,flavor,server_data)
                print "server create: " + str(server)

		#If status is active send true else send false
                self.assertTrue(server == 'ACTIVE')

		avg_build_time += build_time

		#Delete server
                server_delete = self.delete_server(nova_url, headers)
	        print "server delete: " + str(server_delete)
		self.assertIn('204',server_delete)

                #Write to status log
		status_timestamp = str(datetime.now().strftime("%Y-%m-%dT%H:%M:%S%z"))
                #self.write_status(service, 1, str(datetime.now().strftime("%Y-%m-%dT%H:%M:%S%z")))
                output.append(True)

		#Done for aggregating total test duration
		done_time = time.time()
		error = None
		status = 1
            except Exception as e:
	   	#print "Failed Nova: " + str(e)
		status = 0
		
		if self.error_output != None:
		    print self.error_output + ", " + str(e)
		    self.error_output = self.error_output + ", " + str(e) + " line 245"
		else:
		    self.error_output = str(e) + " line 247"
		
		if server == None:
		    pass
		elif '401' in server or '401' in server_delete:
		    headers = False
	        elif '403' in server:
		    #If it is getting forbidden, there may be a limits issue
		    self._delete_server_list(nova_url, headers, name)
                elif any(c in str(server) for c in ('ACTIVE','ERROR','BUILD')) or self.server_id:
                    #Delete server
		    server_delete = self.delete_server(nova_url, headers)

		    #If server doesn't delete we need to try until it does
		    while '204' not in server_delete:
			#Gathering for logs
			status_timestamp = str(datetime.now().strftime("%Y-%m-%dT%H:%M:%S%z"))
			done_time = time.time()
                        total_down_time += (done_time - start_time)
			duration += (done_time-start_time)
			self.error_output = str(server_delete) + " trying to delete server on fail"

                        #Write to status log
                        self.write_status(service,status,status_timestamp,self.error_output,total_down_time,duration,str(build_start))
                        output.append(False)

                        if conn.poll() and conn.recv() == "STOP":
                            break
	                elif os.path.isfile('/usr/during.uptime.stop'):
		            print "Ending Nova during testing."
                            break

                        if '401' in server_delete:
                            print "Attempting to retrieve token and url"
                            headers = self.get_token()
                            nova_url = self.get_nova_url()

		        print "Server delete failed.  Attempting to delete server"
			sleep(5)
                        server_delete = self.delete_server(nova_url, headers)

                #Record down time
                status_timestamp = str(datetime.now().strftime("%Y-%m-%dT%H:%M:%S%z"))

                #Write to status log
                #self.write_status(service, 0, status_timestamp, "Failed Nova: " + str(e))
		output.append(False)

		if headers == False:
		    print "Attempting to retrieve token and url"
		    headers = self.get_token()
		    nova_url = self.get_nova_url()

                done_time = time.time()
                total_down_time += (done_time - start_time)

	    #Aggregating total run time of test
	    duration += (done_time-start_time)
	    self.write_status(service,status,status_timestamp,self.error_output,total_down_time,duration,str(build_start))
            self.error_output = None
	    self.server_id = None

	avg_build_time = avg_build_time/1

        self.report(conn, service, sum(output),
                    len(output), str(build_start), str(datetime.now().strftime("%Y-%m-%dT%H:%M:%S%z")), total_down_time, duration, avg_build_time)
