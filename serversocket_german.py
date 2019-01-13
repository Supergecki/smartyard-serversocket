# Programm, um die gemessenen Werte vom Sensor Client zu empfangen und sie in die Datenbank zu schreiben.
# Gibt außerdem Anweisungen für Display und Actor Clients.

# Importiert alle benötigten Module.
from socket import socket, AF_INET, SOCK_STREAM, gethostbyname, gethostname # für Socket-Verbindungen
from threading import Thread                                                # für Multithreading (sodass mit mehreren Clients gleichzeitig kommuniziert werden kann)
import atexit                                                               # um den Server am Ende des Programms zu beenden
import sqlite3                                                              # für den Zugriff auf die Datenbank
from time import strftime, sleep                                            # für aktuelle Zeitabfrage und Wartezeiten
import sys                                                                  # um das Programm zu beenden

# Definiert einige Konstanten.
HOST = gethostbyname(gethostname()) # eigene IP Adresse
PORT = 33000                        # Port, auf dem der Server gestartet wird
BUFSIZ = 1024                       # maximale Datenmenge, die auf einmal empfangen werden kann
ADDR = ('', PORT)                   # Adresse, auf der der Server gestartet wird ('' steht dafür, dass mehrere Geräte auf den Server zugreifen können)
AIRVALUE   = 870                    # minimaler Feuchtigkeitswert -->   0%
WATERVALUE = 450                    # maximaler Feuchtigkeitswert --> 100%

# Erstellt das IP Dictionary (spezieller Datentyp in Python).
# Übersetzt eine IP Adresse in einen Gerätenamen. 
ip_dict = {
'192.168.188.111':'Sensor 1',
'192.168.188.112':'Sensor 2',
'192.168.188.113':'Actor 1',
'192.168.188.115':'Display'
}
	
last_msg_s1 = '' # speichert den letzten Wert von Sensor Client 1
last_msg_s2 = '' # speichert den letzten Wert von Sensor Client 2
new_data = False # speichert, ob die Daten bereits an den Display Client gesendet wurden
new_data2 = False # speichert, ob die Daten bereits an die Actor Clients gesendet wurden

humidity_standard = 50 # Standardfeuchtigkeitswert (in %), die Actor Clients werden Wasser zuführen, wenn der echte Wert niedriger ist
# Dies ist nur ein Beispielwert. Der richtige Wert muss je nach Erd- und Pflanzentyp angepasst werden.

# Dieser Thread baut die Verbindungen zu allen Clients auf, die versuchen, sich mit dem Server zu verbinden.
# Für jeden dieser wird ein Thread gestartet, über den Server und Client miteinander interagieren.
def accept_incoming_connections():
	while True:
		client, client_address = SERVER.accept()
		HANDLE_THREAD = Thread(target=handle_client, args=(client, client_address))
		HANDLE_THREAD.start()

# Dieser Thread steuert die Interaktion zwischen Server und Client.	
def handle_client(client, client_address):
	global last_msg_s1, last_msg_s2, new_data, new_data2
	try:
		if ip_dict[client_address[0]].startswith('Sensor'): # überprüft, ob das Gerät ein Sensor Client ist
			conn = sqlite3.connect('/var/www/html/database/sensordata.db') # öffnet die Datenbank für den Schreibzugriff
			c = conn.cursor()                                              # und ermöglicht SQLite-Befehle
			while True:
				raw_msg = client.recv(BUFSIZ)                              # empfängt unformatierte Messwerte vom Sensor Client
				if raw_msg:
					raw_msg = raw_msg.decode("utf8")                       # decodiert die Messwerte in eine Zeichenkette
					parts = [raw_msg[i:i+3] for i in range(0, len(raw_msg), 3)] # stellt sicher, dass nur Messwerte aus drei Zeichen gesendet werden
					for msg1 in parts:
						msg = msg1
						msg = round((AIRVALUE - int(msg)) / (AIRVALUE - WATERVALUE) * 100, 2) # rechnet den unformatierten Wert in eine Prozentzahl um
						print(msg)
						if ip_dict[client_address[0]] == 'Sensor 1':
							last_msg_s1 = str(msg)
						else:
							last_msg_s2 = str(msg)
						new_data = True
						new_data2 = True
						c.execute("INSERT INTO sensorreadings(humidity, date, time, device) values(%s, date('now'), time('now'), \"%s\")" % (msg, ip_dict[client_address[0]])) # schreibt Daten in die Datenbank
						conn.commit() # und bestätigt
		elif ip_dict[client_address[0]] == 'Display': # überprüft, ob das Gerät der Display Client ist
			while True:
				client.send(b'%s;%s' % (bytes(last_msg_s1, "utf8"), bytes(last_msg_s2, 'utf8'))) # sendet Werte an den Display Client
				new_data = False
				while not new_data: # wartet darauf, dass neue Daten empfangen werden
					sleep(1)
		elif ip_dict[client_address[0]].startswith('Actor'): # überprüft, ob das Gerät ein Actor Client ist
			while True:
				while not new_data2: # wartet darauf, dass neue Daten empfangen werden
					sleep(1)
				if last_msg_s1:
					client.send(b'%s(1)' % (b'open_gate' if float(last_msg_s1) < humidity_standard else b'close_gate')) # sendet Befehl an Actor Client 1
				if last_msg_s2:
					client.send(b'%s(2)' % (b'open_gate' if float(last_msg_s2) < humidity_standard else b'close_gate')) # sendet Befehl an Actor Client 2
				new_data2 = False
	except (ConnectionResetError, OSError) as e:
		pass

# Beendet den Server, damit der Port neu benutzt werden kann.		
def cleanserver():
	SERVER.close()

# Startet den Server auf der angegebenen Adresse.
SERVER = socket(AF_INET, SOCK_STREAM)
SERVER.bind(ADDR)

# Ruft die cleanserver()-Funktion am Ende des Programms auf, damit der Server beendet wird.
atexit.register(cleanserver)

# Öffnet den Server, sodass die Clients darauf zugreifen können.
try:
	SERVER.listen(5)
	ACCEPT_THREAD = Thread(target=accept_incoming_connections)
	ACCEPT_THREAD.start()
	ACCEPT_THREAD.join()
	
# Wenn das Programm manuell oder unerwartet beendet wird, soll der Server beendet werden.
except KeyboardInterrupt:
	cleanserver()
	sys.exit()
