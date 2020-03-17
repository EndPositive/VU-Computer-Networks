import copy
import threading
import time
from packet import *
from util import *


class Bootstrap:
    def __init__(self):
        self.__socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

        # maps torrent hash to list of seeders
        self.connections = {}

    def start(self):
        self.__socket.bind(('192.168.0.2', 65400))

        print("Listening for client on 192.168.0.2")
        pingt = threading.Thread(target=self.__ping)
        pingt.setDaemon(True)
        pingt.start()
        self.__listen(self.__socket)

    def __listen(self, sock):
        while True:
            res, conn = receive(sock, 4096)
            if not res:
                break
            packet = Packet(res)

            # SIGN IN
            if packet.type == 0:
                self.h_start_seeding(packet, conn)
            # SIGN OUT
            elif packet.type == 1:
                self.h_stop_seeding(packet, conn)
            # PING
            elif packet.type == 2:
                self.h_start_seeding(packet, conn, False)
            # LIST SEEDERS
            elif packet.type == 3:
                self.h_request_seeders(packet, conn)
            # CREATE HASH/TORRENT
            elif packet.type == 4:
                self.h_create(packet, conn)
            # REQUEST HOLE PUNCH
            elif packet.type == 8:
                self.h_punch(packet, conn)
        conn.close()

    def __ping(self):
        packet = Packet()
        packet.type = 2
        while True:
            connections = copy.deepcopy(self.connections)
            for hash in connections:
                for conn in connections[hash]:
                    packet.hash = hash
                    self.connections[packet.hash].remove(conn)
                    send(self.__socket, packet.to_bytes(), conn)
            # Ping every 15 seconds. NAT's remove entries after
            # about 60sec but it varies....
            time.sleep(15)

    def h_start_seeding(self, packet, conn, needs_response=True):
        if packet.hash in self.connections:
            if conn not in self.connections[packet.hash]:
                self.connections[packet.hash].append(conn)
            else:
                self.h_error(packet, conn, 2)
                return
            if needs_response:
                send(self.__socket, packet.to_bytes(), conn)
        else:
            self.h_error(packet, conn, 0)

    def h_stop_seeding(self, packet, conn):
        if packet.hash in self.connections:
            self.connections[packet.hash].remove(conn)
            send(self.__socket, packet.to_bytes(), conn)
        else:
            self.h_error(packet, conn, 0)

    def h_request_seeders(self, packet, conn):
        if packet.hash in self.connections:
            packet.seeders = self.connections[packet.hash]
            send(self.__socket, packet.to_bytes(), conn)
        else:
            self.h_error(packet, conn, 0)

    def h_create(self, packet, conn):
        if packet.hash not in self.connections:
            self.connections[packet.hash] = []
            send(self.__socket, packet.to_bytes(), conn)
        else:
            self.h_error(packet, conn, 1)

    def h_punch(self, packet, to_be_punched):
        to_punch = packet.seeders[0]
        packet.seeders[0] = to_be_punched
        send(self.__socket, packet.to_bytes(), to_punch)

    def h_error(self, packet, conn, num):
        packet.type = 5
        packet.err = num
        send(self.__socket, packet.to_bytes(), conn)


if __name__ == "__main__":
    boot = Bootstrap()
    boot.start()
