import socket
from hashlib import md5


def send(sock, data, conn):
    try:
        # print("OUT: ", data, conn)
        sock.sendto(data, conn)
        return True
    except socket.error as e:
        print(e)
        return False


def receive(sock, size):
    try:
        data, conn = sock.recvfrom(size)
        # print("IN:   ", data, conn)
        if not data:
            return False, False
        else:
            return data, conn
    except socket.error as e:
        print(e)
        return False, False


def addr_to_bytes(addr):
    ip = addr[0]
    port = addr[1]

    new_ip = bytes([int(x) for x in ip.split('.')])
    new_port = port.to_bytes(2, 'big')
    return new_ip + new_port


def addr_from_bytes(addr):
    ip = addr[:4]
    port = addr[4:]

    new_ip = '.'.join([str(x) for x in list(ip)])
    new_port = int.from_bytes(port, 'big')
    return new_ip, new_port


def hash_data(data, function=md5):
    h = function()
    h.update(data)
    return h.digest()
