import socket


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