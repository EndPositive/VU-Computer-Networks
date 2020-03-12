import socket
from packet import *
from util import *


def error(conn, num):
    packet = Packet()
    packet.type = 5
    packet.err = num
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
        self.__socket.bind(('192.168.0.2', 65400))
        self.__socket.listen()

        while True:
            conn, addr = self.__socket.accept()
            print(conn, addr)
            self.__listen(conn)

    def __listen(self, conn):
        while True:
            res = receive(conn, 4096)
            if res:
                packet = Packet(res)
                print(packet.type)
                if packet.type == 0:
                    if packet.hash in self.connections:
                        if conn not in self.connections[packet.hash]:
                            self.connections[packet.hash].append(conn)
                        else:
                            error(conn, 2)
                            continue
                        by = packet.to_bytes()
                        send(conn, by)
                    else:
                        error(conn, 0)
                        continue
                elif packet.type == 1:
                    if packet.hash in self.connections:
                        self.connections[packet.hash].remove(conn)
                        by = packet.to_bytes()
                        send(conn, by)
                    else:
                        error(conn, 0)
                        continue
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
                        continue
                elif packet.type == 5:
                    pass
                elif packet.type == 6:
                    pass
                elif packet.type == 7:
                    pass
                else:
                    print("Unknown type", res)
            else:
                break
        conn.close()


if __name__ == "__main__":
    boot = Bootstrap()
    boot.start()