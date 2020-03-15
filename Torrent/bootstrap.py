import copy
import threading
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
            print(packet.type)
            # SIGN IN
            if packet.type == 0:
                self.pull_sign_in(packet, conn)
            # SIGN OUT
            elif packet.type == 1:
                self.pull_sign_out(packet, conn)
            # PING
            elif packet.type == 2:
                self.pull_sign_in(packet, conn, False)
            # LIST SEEDERS
            elif packet.type == 3:
                self.pull_list(packet, conn)
            # CREATE HASH/TORRENT
            elif packet.type == 4:
                self.pull_create(packet, conn)
            # ERROR MESSAGE
            elif packet.type == 5:
                pass
            # REQUEST FOR DOWNLOAD
            elif packet.type == 6:
                pass
            # DOWNLOAD OF PIECE
            elif packet.type == 7:
                pass
            # REQUEST HOLE PUNCH
            elif packet.type == 8:
                self.pull_punch(packet, conn)
            else:
                print("Unknown type", res)
        conn.close()

    def __ping(self):
        packet = Packet()
        packet.type = 2
        while True:
            connections = copy.deepcopy(self.connections)
            for hash in connections:
                self.connections[hash] = []
                for conn in connections[hash]:
                    send(self.__socket, packet.to_bytes(), conn)
            # Ping every 15 seconds. NAT's remove entries after
            # about 60sec but it varies....
            time.sleep(15)

    def pull_sign_in(self, packet, conn, needs_response=True):
        if packet.hash in self.connections:
            if conn not in self.connections[packet.hash]:
                self.connections[packet.hash].append(conn)
            else:
                self.pull_error(packet, conn, 2)
                return
            if needs_response:
                send(self.__socket, packet.to_bytes(), conn)
        else:
            self.pull_error(packet, conn, 0)

    def pull_sign_out(self, packet, conn):
        if packet.hash in self.connections:
            self.connections[packet.hash].remove(conn)
            send(self.__socket, packet.to_bytes(), conn)
        else:
            self.pull_error(packet, conn, 0)

    def pull_list(self, packet, conn):
        packet.seeders = self.connections[packet.hash]
        send(self.__socket, packet.to_bytes(), conn)

    def pull_create(self, packet, conn):
        if packet.hash not in self.connections:
            self.connections[packet.hash] = []
            send(self.__socket, packet.to_bytes(), conn)
        else:
            self.pull_error(packet, conn, 1)

    def pull_error(self, packet, conn, num):
        packet.type = 5
        packet.err = num
        send(self.__socket, packet.to_bytes(), conn)

    def pull_punch(self, packet, to_be_punched):
        to_punch = packet.seeders[0]
        packet.seeders[0] = to_be_punched
        send(self.__socket, packet.to_bytes(), to_punch)


if __name__ == "__main__":
    boot = Bootstrap()
    boot.start()