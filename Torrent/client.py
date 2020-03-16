import threading
import time
import copy
from packet import *
from util import *
from torrent import *


class Client:
    def __init__(self):
        self.__socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

        # Ip and port of the bootstrap server
        self.conn_bootstrap = ('80.112.140.14', 65400)

        # Variable to know between threads whether we are punched
        self.punched = False
        # Variable to know between threads whether the other is punched
        self.punched_other = False

        # List of torrents
        self.torrents = []

        # Dict of seeders, punched seeders and active seeders by torrent hash
        self.seeders = {}
        self.active_seeders = {}
        self.max_active_seeders = 3

        # Counter for how many pieces we are receiving
        self.counter = {}
        self.speed = {}
        self.total_speed = 0;

    def start(self):
        self.torrents = load_torrents()
        # Connect to bootstrap
        pull_thread = threading.Thread(target=self.__pull)
        pull_thread.setDaemon(True)
        pull_thread.start()
        push_thread = threading.Thread(target=self.__push)
        push_thread.setDaemon(True)
        push_thread.start()
        ping_thread = threading.Thread(target=self.__ping)
        ping_thread.setDaemon(True)
        ping_thread.start()
        speed_thread = threading.Thread(target=self.__ping)
        speed_thread.setDaemon(True)
        speed_thread.start()
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
                self.pull_ping(packet, conn)
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
                self.send_download(packet, conn)
            # DOWNLOAD OF PIECE
            elif packet.type == 7:
                self.receive_download(packet, conn)
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

    def pull_ping(self, packet, conn):
        if conn == self.conn_bootstrap:
            send(self.__socket, packet.to_bytes(), self.conn_bootstrap)
        else:
            torrent = [t for t in self.torrents if t.hash == packet.hash][0]
            self.push_sign_in("seed " + str(torrent.id))

    def pull_list(self, packet):
        self.seeders[packet.hash] = packet.seeders
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

    def punch(self, conn):
        packet = Packet()

        # Tell the bootstrap you want to start punching someone
        packet.type = 8
        packet.seeders.append(conn)
        send(self.__socket, packet.to_bytes(), self.conn_bootstrap)

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

    def __ping(self):
        packet = Packet()
        packet.type = 2
        while True:
            connections = copy.deepcopy(self.active_seeders)
            for hash in connections:
                for conn in connections[hash]:
                    packet.hash = hash
                    self.active_seeders[hash].remove(conn)
                    send(self.__socket, packet.to_bytes(), conn)
            # Ping every 15 seconds. NAT's remove entries after
            # about 60sec but it varies....
            time.sleep(15)

    def __download_speed(self):
        time.sleep(1)
        total_speed = 0
        for hash in self.counter:
            self.speed[hash] = self.counter[hash]
            self.counter[hash] = 0
            total_speed += self.speed[hash]
        self.total_speed = total_speed

    def request_download(self, data):
        try:
            packet = Packet()
            torrent = self.torrents[int(data.split(" ")[1])]
            packet.hash = torrent.hash

            # Main download loop
            while True:
                # Try to download from more seeders if limit isn't reached
                if len(self.active_seeders[torrent.hash]) < self.max_active_seeders:
                    # Get seeders list
                    self.push_list(data)
                    time.sleep(1)

                    # Find punched seeders who are not seeding yet
                    idle_seeders = [s for s in self.seeders[torrent.hash] if s not in self.active_seeders]

                    if len(idle_seeders) == 0:
                        # Wait a bit before trying again
                        time.sleep(1)

                    # Punch an idle seeder
                    self.punch(idle_seeders[0])

                    # Request a download
                    packet.type = 6
                    packet.piece_no = torrent.get_piece_no()
                    send(self.__socket, packet.to_bytes(), idle_seeders[0])

                    # Mark the seeders as active
                    self.active_seeders[torrent.hash].append(idle_seeders[0])
                else:
                    # Wait a bit before trying again
                    time.sleep(1)
        except IndexError:
            print("Usage: download torrent_id\nGet list of seeders of a torrent.")

    def send_download(self, packet, conn):
        try:
            torrent = [t for t in self.torrents if t.hash == packet.hash][0]
            packet.type = 7
            packet.data = torrent.get_piece(packet.piece_no)
            send(self.__socket, packet.to_bytes(), conn)
            print("Sending a piece for torrent", torrent.id)
        except IndexError:
            print("Received a request for an unknown torrent", packet.hash, packet)

    def receive_download(self, packet, conn):
        try:
            torrent = [t for t in self.torrents if t.hash == packet.hash][0]
            torrent.add_piece(packet.piece_no, data=packet.data)
            self.active_seeders[torrent.hash].remove(conn)
            self.counter[torrent.hash] += 1
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
