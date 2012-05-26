#!/usr/bin/python

#config open_inodes
#graph_title Inode table usage
#graph_args --base 1000 -l 0
#graph_vlabel number of open inodes
#graph_category system
#graph_info This graph monitors the Linux open inode table.
#used.label open inodes
#used.info The number of currently open inodes.
#max.label inode table size
#max.info The size of the system inode table. This is dynamically adjusted by the kernel.
#.
#fetch open_inodes
#used.value 26028
#max.value 43491
#.


import socket
import threading
import SocketServer
import re
import sys
import subprocess

def iostat_config(dname, ssh_data):

  output = "graph_title IOStat for %s\n" % (dname)
  output = "%sgraph_args --base 1000 -l 0\n" % (output)
  output = "%sgraph_vlabel activity\n" % (output)
  output = "%sgraph_category iostat\n" % (output)
  output = "%sgraph_info This graph shows IOStat output\n" % (output)
  for cell in ssh_data[0].split(','):
    if cell != "Device:":
      output = "%s%s.label %s\n" % (output, re.sub('[\W_]', '', cell), cell)
  output = "%s.\n" % (output)
  return output
  
def iostat_fetch(dname, ssh_data):
  output = ""
  header = ssh_data[0].split(',')
  header.pop(0)
  for line in ssh_data:
    cells = line.split(',')
    if cells[0] == dname:
      cells.pop(0)
      i=0
      for cell in cells:
        output = "%s%s.value %s\n" % (output, re.sub('[\W_]', '', header[i]), cell)
        i=i+1

  output = "%s.\n" % (output)
  return output

def do_ssh(cmd=""):
    prog = subprocess.Popen(["ssh", "dgtlmoon@localhost", cmd], stdout=subprocess.PIPE,stderr=subprocess.PIPE)
    (stdoutdata, stderrdata) = prog.communicate()
    return stdoutdata.splitlines()
  
class ThreadedTCPRequestHandler(SocketServer.BaseRequestHandler):
    def handle(self):
	self.request.sendall("# munin node at AMIDATAFS01\n")
	# connect via ssh and get the info?
        ssh_data = do_ssh('iostat -x|grep -E "^(Device:|sd[abcde])\s"|sed -r "s/\ +/,/g"')

	while True:
            data = self.request.recv(1024)
            if not data: break
            command = re.match( r'^(cap|list|config|fetch).(.*)', data, re.M|re.I)
            if command is not None:
                cmd = command.group(1).strip()
                grp = command.group(2).strip()
                if cmd == 'cap':
                  self.request.sendall("cap multigraph dirtyconfig\n")

                if cmd == 'list':
                  self.request.sendall("iostat_sda iostat_sdb iostat_sdc iostat_sdd iostat_sde\n")

                if cmd == 'config' and cmd.find("iostat_") is not None:
                  # time to grab all the config details and get em ready
        	  drive = grp.split('_')[1]
                  self.request.sendall(iostat_config(drive, ssh_data))
                if cmd == 'fetch':
        	  drive = grp.split('_')[1]
                  self.request.sendall(iostat_fetch(drive, ssh_data))
	
	self.request.close(  )

class ThreadedTCPServer(SocketServer.ThreadingMixIn, SocketServer.TCPServer):
    pass

if __name__ == "__main__":


    # Port 0 means to select an arbitrary unused port
    server = ThreadedTCPServer(("localhost", 5002), ThreadedTCPRequestHandler)
    ip, port = server.server_address

    # Start a thread with the server -- that thread will then start one
    # more thread for each request
    server_thread = threading.Thread(target=server.serve_forever)
    # Exit the server thread when the main thread terminates
    server_thread.daemon = True
    server_thread.start()
    print "Server loop running in thread:", server_thread.name

    try:
      server.serve_forever()
    except:
      print "got exception"
      server.shutdown()
      sys.exit()
