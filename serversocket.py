# Program to receive values from client and write it into database.

# Imports all modules needed.
from socket import socket, AF_INET, SOCK_STREAM, gethostbyname, gethostname # used for socketing
from threading import Thread                                                # used for multithreaded application
import atexit                                                               # used to clean server at the end
import sqlite3                                                              # used for database access
from time import strftime, sleep                                            # used to paste time into database
import sys                                                                  # used to end program

# Sets some constants.
HOST = gethostbyname(gethostname()) # own IP address
PORT = 33000                        # port to set up serversocket
BUFSIZ = 1024                       # maximum amount of data to be received once
ADDR = ('', PORT)                   # address to set up serversocket
AIRVALUE   = 870                    # minimum humidity value -->   0%
WATERVALUE = 450                    # maximum humidity value --> 100%

# Creates the IP and client dictionaries.
# IP dict: translates IP address to device name
ip_dict = {
'192.168.188.111':'Sensor 1',
'192.168.188.112':'Sensor 2',
'192.168.188.113':'Actor 1',
'192.168.188.115':'Display'
}

# Client dict: translates device name to IP address
client_dict = {}
for key in ip_dict:
	client_dict[ip_dict[key]] = key
	
last_msg_s1 = '' # stores the last message received (Sensor 1)
last_msg_s2 = '' # stores the last message received (Sensor 2)
new_data = False # stores if the values were sent to the display
new_data2 = False # stores if the values were sent to the actors

humidity_standard = 50 # the standard humidity value, actors will put water on it if it's below

# Connection accepting thread, accepts all incoming connections (starts a handle_client thread).
def accept_incoming_connections():
	while True:
		client, client_address = SERVER.accept()
		HANDLE_THREAD = Thread(target=handle_client, args=(client, client_address))
		HANDLE_THREAD.start()

# Handles the connection to a single client.	
def handle_client(client, client_address):
	global last_msg_s1, last_msg_s2, new_data, new_data2
	try:
		if ip_dict[client_address[0]].startswith('Sensor'): # check if device is a sensor client
			conn = sqlite3.connect('/var/www/html/database/sensordata.db') # connects to database
			c = conn.cursor()                                              # and enables sqlite commands
			while True:
				raw_msg = client.recv(BUFSIZ)                              # receive message from client
				if raw_msg:
					raw_msg = raw_msg.decode("utf8")                       # decode message from bytes to string
					parts = [raw_msg[i:i+3] for i in range(0, len(raw_msg), 3)]
					for msg1 in parts:
						msg = msg1
						msg = round((AIRVALUE - int(msg)) / (AIRVALUE - WATERVALUE) * 100, 2)
						print(msg)
						if ip_dict[client_address[0]] == 'Sensor 1':
							last_msg_s1 = str(msg)
						else:
							last_msg_s2 = str(msg)
						new_data = True
						new_data2 = True
						c.execute("INSERT INTO sensorreadings(humidity, date, time, device) values(%s, date('now'), time('now'), \"%s\")" % (msg, ip_dict[client_address[0]])) # inserts data into database
						conn.commit() # and commits
		elif ip_dict[client_address[0]] == 'Display': # check if device is the display
			while True:
				client.send(b'%s;%s' % (bytes(last_msg_s1, "utf8"), bytes(last_msg_s2, 'utf8'))) # send values to display
				new_data = False
				while not new_data: # idling while no new data is received
					sleep(1)
		elif ip_dict[client_address[0]].startswith('Actor'): # check if device is an actor client
			while True:
				while not new_data2: # idling while no new data is received
					sleep(1)
				if last_msg_s1:
					client.send(b'%s(1)' % (b'open_gate' if float(last_msg_s1) < humidity_standard else b'close_gate'))
				if last_msg_s2:
					client.send(b'%s(2)' % (b'open_gate' if float(last_msg_s2) < humidity_standard else b'close_gate'))
				new_data2 = False
	except (ConnectionResetError, OSError) as e:
		pass

# Cleans the server port for a new program start.		
def cleanserver():
	SERVER.close()

# Sets up the server at the given address.
SERVER = socket(AF_INET, SOCK_STREAM)
SERVER.bind(ADDR)

# Calls cleanserver() at the end of the program.
atexit.register(cleanserver)

# Opens the server for incoming connections.
try:
	SERVER.listen(5)
	ACCEPT_THREAD = Thread(target=accept_incoming_connections)
	ACCEPT_THREAD.start()
	ACCEPT_THREAD.join()
	
# Program is stopped manually, so clean the server.
except KeyboardInterrupt:
	cleanserver()
	sys.exit()
