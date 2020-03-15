import threading
import time
from packet import *
from util import *
from torrent import *


class Client:
    def __init__(self):
        self.__socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.conn_bootstrap = ('80.112.140.14', 65400)
        self.punched = False
        self.punched_other = False
        self.torrents = []

    def start(self):
        self.torrents = load_torrents()
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
            elif "seeders" in inp:
                self.push_list(inp)
            elif "seed" in inp:
                self.push_sign_in(inp)
            elif "list" in inp:
                for torrent in self.torrents:
                    print(torrent.id, torrent.file.path, torrent.hash)
            elif "create" in inp:
                self.push_create(inp)
            elif "download" in inp:
                self.push_download(inp)
            elif "punch" in inp:
                self.push_punch(inp)
                continue
            else:
                print("Unknown command")
            save_torrents(self.torrents)
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
                self.pull_ping(packet)
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
            elif packet.type == 8 or packet.type == 9:
                self.pull_punch(packet, conn)
            else:
                print("Unknown type", res)
            save_torrents(self.torrents)

    def push_sign_in(self, data):
        torrent = self.torrents[int(data.split(" ")[1])]
        packet = Packet()
        packet.type = 0
        packet.hash = torrent.hash
        send(self.__socket, packet.to_bytes(), self.conn_bootstrap)

    def push_sign_out(self, data):
        torrent = self.torrents[int(data.split(" ")[1])]
        packet = Packet()
        packet.type = 1
        packet.hash = torrent.hash
        send(self.__socket, packet.to_bytes(), self.conn_bootstrap)

    def push_list(self, data):
        torrent = self.torrents[int(data.split(" ")[1])]
        packet = Packet()
        packet.type = 3
        packet.hash = torrent.hash
        send(self.__socket, packet.to_bytes(), self.conn_bootstrap)

    def push_create(self, data):
        torrent = Torrent(data.split(" ")[1], 10, len(self.torrents))
        self.torrents.append(torrent)
        packet = Packet()
        packet.type = 4
        packet.hash = torrent.hash
        send(self.__socket, packet.to_bytes(), self.conn_bootstrap)

    def push_download(self, data):
        torrent = Torrent(data.split(" ")[1], 10, len(self.torrents))
        packet = Packet()
        packet.type = 6
        packet.hash = torrent.hash
        packet.piece_no = " ".split(data)[2]
        send(self.__socket, packet.to_bytes(), self.conn_bootstrap)

    def push_punch(self, data):
        data = data.split(" ")
        to_be_punched = (data[1], int(data[2]))

        packet = Packet()
        packet.type = 8
        packet.seeders.append(to_be_punched)
        send(self.__socket, packet.to_bytes(), self.conn_bootstrap)

        punchThread = threading.Thread(target=self.punch, args=(packet, to_be_punched))
        punchThread.setDaemon(True)
        punchThread.start()

    def pull_ping(self, packet):
        send(self.__socket, packet.to_bytes(), self.conn_bootstrap)

    def pull_list(self, packet):
        print(packet.seeders)

    def pull_punch(self, packet, sender):
        # Only respond to pull if it is a request (comes from bootstrap)
        if sender == self.conn_bootstrap:
            print("Received punch request")
            to_be_punched = packet.seeders[0]
            punchThread = threading.Thread(target=self.punch, args=(packet, to_be_punched))
            punchThread.setDaemon(True)
            punchThread.start()
            return

        # Its am actual punch and we have not been punched yet
        if not self.punched:
            self.punched = True
            print("Punched by", sender)

        # If the packet is of type 9, the other client has been punched
        if packet.type == 9:
            self.punched_other = True
            print("Punched", sender)

    def punch(self, packet, conn):
        self.punched = False
        self.punched_other = False
        # We have not been punched yet
        while True and not self.punched:
            send(self.__socket, packet.to_bytes(), conn)
            time.sleep(.5)
        # We have been punched, but the other one not yet
        while True and not self.punched_other:
            packet.type = 9
            send(self.__socket, packet.to_bytes(), conn)
            time.sleep(.5)
        # Final punch
        packet.type = 9
        send(self.__socket, packet.to_bytes(), conn)
        time.sleep(.5)
        print("> ")


if __name__ == "__main__":
    client = Client()
    client.start()
