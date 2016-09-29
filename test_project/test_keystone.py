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
            f = open('output_json/keystone_status.txt','a')
            f.write(status + "\n")
            f.close()

    def report(self, conn, service, success, total, start_time, end_time, down_time):
        uptime_pct = 100 * (float(success)/total)
        conn.send({
            service: {
                "uptime_pct": uptime_pct,
                "total_requests": total,
                "successful_requests": success,
                "failed_requests": total - success,
                "start_time": start_time,
                "end_time": end_time,
		"down_time": down_time}})
        conn.close()

    def test_create_validate_token(self, conn, service, times):
        pipes = []
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

	open('output_json/keystone_status.txt','w')
        
	for _ in times:
            if conn.poll() and conn.recv() == "STOP":
                break
            p, c = Pipe()
            build_start = str(datetime.datetime.now())
	    start_time = time.time()

	    try:
		#Get token
		token = self.keystone.get_auth_headers()['X-Auth-Token']
		
		#Validate token
		self.keystone_client.tokens.validate(token)

		c.send(True)	
		c.close()
		
	        #Write to logfile
		self.write_status(service, 1, build_start)
		sleep(1)
	    except Exception as e:
		down_time = time.time()
		total_down_time += int(down_time - start_time)
	        self.write_status(service, 0, build_start)
                c.send(False)
                c.close()
		sleep(1)
            pipes.append(p)

        output = [pipe.recv() for pipe in pipes]
        self.report(conn, service, sum(output),
                    len(output), str(build_start), 
		    str(datetime.datetime.now()), total_down_time)

