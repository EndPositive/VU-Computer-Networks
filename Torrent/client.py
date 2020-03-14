import threading
from packet import *
from util import *


class Client:
    def __init__(self):
        self.__socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.conn = ('80.112.140.14', 65400)

    def start(self):
        # Connect to bootstrap
        pullThread = threading.Thread(target=self.__pull)
        pullThread.setDaemon(True)
        pullThread.start()
        pushThread = threading.Thread(target=self.__push)
        pushThread.setDaemon(True)
        pushThread.start()
        while True:
            pass

    def __push(self):
        while True:
            inp = input("> ")
            if "!seed" in inp:
                self.push_sign_out(inp)
            elif "seed" in inp:
                self.push_sign_in(inp)
            elif "list" in inp:
                self.push_list(inp)
            elif "create" in inp:
                self.push_create(inp)
            elif "download" in inp:
                self.push_download(inp)
            elif "punch" in inp:
                punch(self.__socket, (inp.split(" ")[1], int(inp.split(" ")[2])))
                continue
            else:
                print("unknown command")
                return

            time.sleep(0.2)

    def __pull(self):
        while True:
            res, conn = receive(self.__socket, 4096)
            if not res:
                print("Something bad happend: ", res)
                return
            packet = Packet(res)

            if packet.type == 0:
                pass
            # SIGN OUT
            elif packet.type == 1:
                pass
            # PING
            elif packet.type == 2:
                self.pull_ping()
            # LIST SEEDERS
            elif packet.type == 3:
                self.pull_list(packet)
            # CREATE HASH/TORRENT
            elif packet.type == 4:
                pass
            # ERROR MESSAGE
            elif packet.type == 5:
                pass
            # REQUEST FOR DOWNLOAD
            elif packet.type == 6:
                pass
            # DOWNLOAD OF PIECE
            elif packet.type == 7:
                pass
            else:
                print("Unknown type", res)
            print(packet.type)

    def push_sign_in(self, data):
        packet = Packet()
        packet.type = 0
        # packet.hash = b"0x00" * 16
        send(self.__socket, packet.to_bytes(), self.conn)

    def push_sign_out(self, data):
        packet = Packet()
        packet.type = 1
        # packet.hash = b"0x00" * 16
        send(self.__socket, packet.to_bytes(), self.conn)

    def push_list(self, data):
        packet = Packet()
        packet.type = 3
        # packet.hash = b"0x00" * 16
        send(self.__socket, packet.to_bytes(), self.conn)

    def push_create(self, data):
        packet = Packet()
        packet.type = 4
        # file = " ".split(data)[1]
        # packet.hash = md5(file)
        send(self.__socket, packet.to_bytes(), self.conn)

    def push_download(self, data):
        packet = Packet()
        packet.type = 6
        # packet.hash = " ".split(data)[1]
        packet.piece_no = " ".split(data)[2]
        send(self.__socket, packet.to_bytes(), self.conn)

    def pull_ping(self):
        packet = Packet()
        packet.type = 2
        send(self.__socket, packet.to_bytes(), self.conn)

    def pull_list(self, packet):
        print(packet.seeders)


if __name__ == "__main__":
    client = Client()
    client.start()
