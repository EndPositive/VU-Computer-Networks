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
        self.__socket.bind(('localhost', 65427))
        self.__socket.listen()

        self.__listen()

    def __listen(self):
        while True:
            conn, addr = self.__socket.accept()
            res = receive(conn, 4096)
            if res:
                packet = Packet(res)
                print(packet.type)
                if packet.type == 0:
                    if packet.hash in self.connections:
                        self.connections[packet.hash].append(conn)
                        by = packet.to_bytes()
                        send(conn, by)
                    else:
                        error(conn, 0)
                elif packet.type == 1:
                    if packet.hash in self.connections:
                        self.connections[packet.hash].remove(conn)
                        by = packet.to_bytes()
                        send(conn, by)
                    else:
                        error(conn, 0)
                elif packet.type == 2:
                    pass
                elif packet.type == 3:
                    list_seeders(conn, self.connections[packet.hash])
                elif packet.type == 4:
                    if packet.hash not in self.connections:
                        self.connections[packet.hash] = []
                        by = packet.to_bytes()
                        send(conn, by)
                    else:
                        error(conn, 1)
                elif packet.type == 5:
                    pass
                elif packet.type == 6:
                    pass
                elif packet.type == 7:
                    pass
                else:
                    print("Unknown type", res)
            conn.close()


if __name__ == "__main__":
    boot = Bootstrap()
    boot.start()