import datetime
import logging
import sys
import time

from keystoneclient import client as keystoneclient
from keystoneauth1.identity import v3
from keystoneauth1 import session
from multiprocessing import Pipe, Process
from time import sleep

class ApiUptime():
    def __init__(self, version, username, password, tenant, auth_url):
	auth = v3.Password(auth_url=auth_url, username=username,
                           project_name=tenant, password=password,
			   user_domain_id="default", project_domain_id="default")
	self.keystone = session.Session(auth=auth)
        self.keystone_client = keystoneclient.Client(session=self.keystone)
	
    def write_status(self, service, status, build_start):
	    status = str({"service": service, "status": status, "timestamp": build_start})
            f = open('../output/keystone_status.txt','a')
            f.write(status + "\n")
            f.close()

    def report(self, conn, service, success, total, start_time, end_time, down_time):
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

    def test_create_validate_token(self, conn, service, times):
	print "Running Keystone during upgrade tests."
	output = []
        start_time = datetime.datetime.now()
        down_time = None
	start_time = 0
        total_time = 0
        total_down_time = 0

        if times is True:
            times = xrange(sys.maxint)
        else:
            times = xrange(times)
        pipes = []

	open('../output/keystone_status.txt','w')
        
	for _ in times:
            if conn.poll() and conn.recv() == "STOP":
                break
            
	    build_start = str(datetime.datetime.now())
	    start_time = time.time()

	    try:
		#Get token
		token = self.keystone.get_auth_headers()['X-Auth-Token']
		
		#Validate token
		self.keystone_client.tokens.validate(token)
		
		#Send success
	     	output.append(True)

	        #Write to logfile
		self.write_status(service, 1, build_start)
		sleep(1)
	    except Exception as e:
		print e
		down_time = time.time()
		total_down_time += int(down_time - start_time)
	        self.write_status(service, 0, build_start)

		#Send Fail
		output.append(False)
		sleep(1)

        self.report(conn, service, sum(output),
                    len(output), str(build_start), 
		    str(datetime.datetime.now()), total_down_time)

