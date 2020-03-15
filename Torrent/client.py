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
        self.connections = {}

    def start(self):
        self.torrents = load_torrents()
        # Connect to bootstrap
        pull_thread = threading.Thread(target=self.__pull)
        pull_thread.setDaemon(True)
        pull_thread.start()
        push_thread = threading.Thread(target=self.__push)
        push_thread.setDaemon(True)
        push_thread.start()
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
                if not len(self.torrents):
                    print("No torrents available.\nUse create to add new torrents.")
                for torrent in self.torrents:
                    print(torrent.id, torrent.file.path, torrent.hash)
            elif "create" in inp:
                self.push_create(inp)
            elif "remove" in inp:
                self.pull_remove_torrent(inp)
            elif "download" in inp:
                self.request_download(inp)
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
                self.send_download(packet)
            # DOWNLOAD OF PIECE
            elif packet.type == 7:
                self.receive_download(packet)
            elif packet.type == 8 or packet.type == 9:
                self.pull_punch(packet, conn)
            else:
                print("Unknown type", res)
            save_torrents(self.torrents)

    def push_sign_in(self, data):
        try:
            torrent = self.torrents[int(data.split(" ")[1])]
            packet = Packet()
            packet.type = 0
            packet.hash = torrent.hash
            send(self.__socket, packet.to_bytes(), self.conn_bootstrap)
        except IndexError:
            print("Usage: seed torrent_id\nStart seeding a torrent.")

    def push_sign_out(self, data):
        try:
            torrent = self.torrents[int(data.split(" ")[1])]
            packet = Packet()
            packet.type = 1
            packet.hash = torrent.hash
            send(self.__socket, packet.to_bytes(), self.conn_bootstrap)
        except IndexError:
            print("Usage: !seed torrent_id\nStop seeding a torrent.")

    def push_list(self, data):
        try:
            torrent = self.torrents[int(data.split(" ")[1])]
            packet = Packet()
            packet.type = 3
            packet.hash = torrent.hash
            send(self.__socket, packet.to_bytes(), self.conn_bootstrap)
        except IndexError:
            print("Usage: seeders torrent_id\nGet list of seeders of a torrent.")

    def push_create(self, data):
        try:
            torrent = Torrent(data.split(" ")[1], 10, len(self.torrents))
            self.torrents.append(torrent)
            packet = Packet()
            packet.type = 4
            packet.hash = torrent.hash
            send(self.__socket, packet.to_bytes(), self.conn_bootstrap)
        except IndexError:
            print("Usage: create /path/to/file\nAnnounce a torrent at the bootstrap.")
        except FileNotFoundError:
            print("File not found, try again.")

    def pull_ping(self, packet):
        send(self.__socket, packet.to_bytes(), self.conn_bootstrap)

    def pull_list(self, packet):
        self.connections[packet.hash] = packet.seeders
        print(packet.seeders)

    def pull_punch(self, packet, sender):
        # Only respond to pull if it is a request (comes from bootstrap)
        if sender == self.conn_bootstrap:
            print("Received punch request")
            to_be_punched = packet.seeders[0]
            punch_thread = threading.Thread(target=self.punch, args=(packet, to_be_punched))
            punch_thread.setDaemon(True)
            punch_thread.start()
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

    def request_download(self, data):
        try:
            torrent = self.torrents[int(data.split(" ")[1])]

            # Get seeders list
            self.push_list(data)
            time.sleep(1)

            # # Start punching everyone in that list
            # for to_be_punched in self.connections[torrent.hash]:

            to_be_punched = self.connections[torrent.hash][0]

            # Tell the bootstrap you want to start punching someone
            packet = Packet()
            packet.type = 8
            packet.seeders.append(to_be_punched)
            send(self.__socket, packet.to_bytes(), self.conn_bootstrap)

            # Start punching that someone
            self.punch(packet, to_be_punched)

            # Request a download
            packet = Packet()
            packet.type = 6
            packet.hash = torrent.hash
            packet.piece_no = 1
            send(self.__socket, packet.to_bytes(), to_be_punched)
        except IndexError:
            print("Usage: download torrent_id\nGet list of seeders of a torrent.")

    def send_download(self, packet):
        try:
            torrent = [t for t in self.torrents if t.hash == packet.hash][0]
            packet.type = 7
            packet.data = torrent.get_piece(packet.piece_no)
            print("Sending a piece for torrent", torrent.id)
        except IndexError:
            print("Received a request for an unknown torrent", packet.hash, packet)

    def receive_download(self, packet):
        try:
            torrent = [t for t in self.torrents if t.hash == packet.hash][0]
            piece = torrent.get_piece(packet.piece_no)
            print("Succesfully received a piece for torrent", torrent.id)
        except IndexError:
            print("Received a piece of an unknown torrent", packet.hash, packet)

    def pull_remove_torrent(self, data):
        try:
            self.torrents = [t for t in self.torrents if t.id != int(data.split(" ")[1])]
        except IndexError:
            print("Usage: remove torrent_id\nRemove a torrent from local cache (does not delete downloaded file).")


if __name__ == "__main__":
    client = Client()
    client.start()
