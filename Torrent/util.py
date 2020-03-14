import socket
import time
import threading


def send(sock, data, conn):
    try:
        print("OUT: ", data, conn)
        sock.sendto(data, conn)
        return True
    except socket.error as e:
        print(e)
        return False


def receive(sock, size):
    try:
        data, conn = sock.recvfrom(size)
        print("IN:   ", data, conn)
        if not data:
            return False
        else:
            return data, conn
    except socket.error as e:
        print(e)
        return False


def punch(sock, conn):
    while True:
        send(sock, b"PUNCH", conn)
        time.sleep(.5)