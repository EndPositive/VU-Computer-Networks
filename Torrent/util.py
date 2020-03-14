import socket
import time
import threading

def send(conn, data):
    try:
        print("OUT: ", data)
        conn.sendall(data)
        return True
    except socket.error as e:
        print(e)
        return False


def receive(conn, size):
    try:
        data = conn.recv(size)
        print("IN:   ", data)
        if not data:
            return False
        else:
            return data
    except socket.error as e:
        print(e)
        return False


def punch(ip, port):
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    punchl = threading.Thread(target=punchlisten, args=(sock, ))
    punchl.setDaemon(True)
    punchl.start()
    while True:
        sock.sendto(b"PUNCH", (ip, int(port)))
        time.sleep(.5)


def punchlisten(sock):
    while True:
        res = receive(sock, 4096)