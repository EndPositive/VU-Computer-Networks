import socket
from packet import *
from util import *


def error(sock, num, conn):
    packet = Packet()
    packet.type = 5
    packet.err = num
    send(sock, packet.to_bytes(), conn)


def list_seeders(sock, connections, conn):
    packet = Packet()
    packet.type = 3
    packet.seeders = connections
    send(sock, packet.to_bytes(), conn)


class Bootstrap:
    def __init__(self):
        self.__socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

        # maps torrent hash to list of seeders
        self.connections = {}

    def start(self):
        self.__socket.bind(('192.168.0.2', 65400))

        print("Listening for client on 192.168.0.2")
        self.__listen(self.__socket)

    def __listen(self, sock):
        while True:
            res, conn = receive(sock, 4096)
            if res:
                packet = Packet(res)
                p = Packet()
                print(packet.type)
                if packet.type == 0:
                    if packet.hash in self.connections:
                        if conn not in self.connections[packet.hash]:
                            self.connections[packet.hash].append(conn)
                        else:
                            error(sock, 2, conn)
                            continue
                        p.type = packet.type
                        p.hash = packet.hash
                        by = p.to_bytes()
                        send(sock, by, conn)
                    else:
                        error(sock, 0, conn)
                        continue
                elif packet.type == 1:
                    if packet.hash in self.connections:
                        self.connections[packet.hash].remove(conn)
                        p.type = packet.type
                        p.hash = packet.hash
                        by = p.to_bytes()
                        send(sock, by, conn)
                    else:
                        error(sock, 0, conn)
                        continue
                elif packet.type == 2:
                    pass
                elif packet.type == 3:
                    list_seeders(sock, self.connections[packet.hash], conn)
                elif packet.type == 4:
                    if packet.hash not in self.connections:
                        self.connections[packet.hash] = []
                        p.type = packet.type
                        p.hash = packet.hash
                        by = p.to_bytes()
                        send(sock, by, conn)
                    else:
                        error(sock, 1, conn)
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