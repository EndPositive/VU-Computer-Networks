import socket


def send(conn, msg):
    try:
        conn.sendall(msg.encode('utf-8'))
        return True
    except socket.error:
        return False


def receive(conn, size):
    try:
        data = conn.recv(size)
        if not data:
            return False
        else:
            while not data[-1:] == b'\n':
                data += conn.recv(size)
                if not data:
                    break
            return data.decode("utf-8")
    except socket.error:
        return False