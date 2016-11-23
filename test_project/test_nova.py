import datetime
import time
import sys
import unittest
import json

from novaclient import client as novaclient
from time import sleep
from multiprocessing import Pipe, Process

class ApiUptime(unittest.TestCase):
    def __init__(self, version, username, password, tenant, auth_url):
	self.nova = novaclient.Client(version, username, password, tenant, auth_url)

    def _wait_until(self, function, resource_id, server=None):
	get = None
	start_time = time.time()
	while get  <> 'ACTIVE':
            get = function(resource_id).status	
	    build_time = int(time.time() - start_time)
	    if build_time > 15 or get == 'ERROR':
		break

    def write_status(self, service, status, build_start):
            status = {"service": service, "status": status, "timestamp": build_start}
            f = open('/root/output/nova_status.txt','a')
            f.write(json.dumps(status) + "\n")
            f.close()

    def create_server(self,name, image, flavor):
	server = self.nova.servers.create(name=name,
                         image=image,flavor=flavor)
	self._wait_until(self.nova.servers.get, server.id, server)
	return server
	
    def delete_server(self, server_id, status):
	try:
	    self.nova.servers.delete(server=server_id)
        except Exception as e:
	    print e
	    return False

	#Verify delete
	try:
	    self._wait_until(self.nova.servers.get, server_id)
	except Exception as e:
	    self.assertIn('404', str(e))
	return True

    def report(self, conn, service, success, total, avg_build, start_time, end_time, down_time):
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
		"average_build_time": avg_build,
		"down_time": down_time}})
        conn.close()

    def test_create_delete_server(self, conn, service, times, flavor=None, name=None, image=None):
        output = []
        start_time = datetime.datetime.now()
        count = 0
        duration = 0
        status = None
        down_time = None
        total_build_time = 0
        total_down_time = 0
        server = None
	average_build_time = 0
	total_down_time = 0

        if times is True:
            times = xrange(sys.maxint)
        else:
            times = xrange(times)

        open('/root/output/nova_status.txt','w')

        for _ in times:
            if conn.poll() and conn.recv() == "STOP":
                break
          
	    try:
                #Create server
                build_start = time.time()
                server = self.create_server(name,image,flavor)
                build_finish = time.time()

                #If status is active send true else send false
                self.assertTrue(server.status == 'ACTIVE')
                
		#Delete server
                server_delete = self.delete_server(server.id, server.status)
                if server_delete <> True:
                        break

                #Record timestamp for status
                status_timestamp = str(datetime.datetime.now().strftime("%Y-%m-%dT%H:%M:%S%z"))

                #Accrue for stats
                count += 1
                total_build_time += int(build_finish - build_start)
                average_build_time = int(total_build_time/count)

                #Write to status log
                self.write_status(service, 1, status_timestamp)
		output.append(True)
            except Exception as e:
	   	print e
                if server:
                    #Delete server
                    self.delete_server(server.id, server.status)

                #Record down time
                status_timestamp = str(datetime.datetime.now())
                build_finish = time.time()
                total_down_time += (float(build_finish) - build_start)

                #Write to status log
                self.write_status(service, 0, status_timestamp)
		output.append(False)

        self.report(conn, service, sum(output),
                    len(output), average_build_time, str(start_time), str(datetime.datetime.now()), total_down_time)

