import socket


def send(conn, data):
    try:
        conn.sendall(data)
        return True
    except socket.error:
        return False


def receive(conn, size):
    try:
        data = conn.recv(size)
        if not data:
            return False
        else:
            return data
    except socket.error:
        return False