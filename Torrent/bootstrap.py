import socket
from packet import *
from util import *


def error(conn, num):
    if num == 0:
        packet = Packet()
        packet.type = 5
        packet.err = 0  # not found
    elif num == 1:
        packet = Packet()
        packet.type = 5
        packet.err = 0  # not found
    else:
        return
    bytes = packet.to_bytes()
    send(conn, bytes)


def list_seeders(conn, connections):
    packet = Packet()
    packet.type = 3
    packet.seeders = connections
    bytes = packet.to_bytes()
    send(conn, bytes)


class Bootstrap:
    def __init__(self):
        self.__socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

        self.connections = {}

    def start(self):
        self.__socket.bind(('localhost', 65432))
        self.__socket.listen()

        self.__listen()

    def __listen(self):
        while True:
            conn, addr = self.__socket.accept()
            res = receive(conn, 4096)
            if res:
                try:
                    packet = Packet(res)
                    if packet.type == 0:
                        if packet.hash in self.connections:
                            self.connections[packet.hash].append(conn)
                        else:
                            error(conn, 0)
                    elif packet.type == 1:
                        if packet.hash in self.connections:
                            self.connections[packet.hash].remove(conn)
                        else:
                            error(conn, 0)
                    elif packet.type == 2:
                        pass
                    elif packet.type == 3:
                        list_seeders(conn, self.connections[packet.hash])
                    elif packet.type == 4:
                        if packet.hash not in self.connections:
                            self.connections[packet.hash] = []
                        else:
                            error(conn, 1)
                    elif packet.type == 5:
                        pass
                    elif packet.type == 6:
                        pass
                    elif packet.type == 7:
                        pass
                    else:
                        print("Unknown type")
                except:
                    pass
            conn.close()
