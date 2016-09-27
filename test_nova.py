import datetime
import time
from time import sleep
from multiprocessing import Pipe, Process
import sys
import unittest

from novaclient import client as novaclient

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
            status = str({"service": service, "status": status, "timestamp": build_start})
            f = open('nova_status.txt','a')
            f.write(status + "\n")
            f.close()

    def create_server(self,name, image, flavor):
	server = self.nova.servers.create(name=name,
                         image=image,flavor=flavor)
	self._wait_until(self.nova.servers.get, server.id, server)
	return server
	
    def delete_server(self, c, conn, server_id, status):
	try:
	    self.nova.servers.delete(server=server_id)
        except Exception as e:
	    c.send(False)
	    c.close()
	    conn.send('STOP')
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
        pipes = []
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

        open('nova_status.txt','w')

        for _ in times:
            if conn.poll() and conn.recv() == "STOP":
                break
            p, c = Pipe()
            try:
                #Create server
                build_start = time.time()
                server = self.create_server(name,image,flavor)
                build_finish = time.time()

                #If status is active send true else send false
                self.assertTrue(server.status == 'ACTIVE')
                
		#Delete server
                server_delete = self.delete_server(c, conn, server.id, server.status)
                if server_delete <> True:
                        break

                #Record timestamp for status
                status_timestamp = str(datetime.datetime.now())

                #Accrue for stats
                count += 1
                total_build_time += int(build_finish - build_start)
                average_build_time = int(total_build_time/count)

                #Write to status log
                self.write_status(service, True, status_timestamp)
	        c.send(True)
                c.close()
            except Exception as e:
                if server:
                    #Delete server
                    self.delete_server(c, conn, server.id, server.status)

                #Record down time
                status_timestamp = str(datetime.datetime.now())
                build_finish = time.time()
                total_down_time += (float(build_finish) - build_start)

                #Write to status log
                self.write_status(service, False, status_timestamp)
                c.send(False)
                c.close()
            pipes.append(p)

        output = [pipe.recv() for pipe in pipes]
        self.report(conn, service, sum(output),
                    len(output), average_build_time, str(start_time), str(datetime.datetime.now()), total_down_time)

