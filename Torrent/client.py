import threading
import time
import copy
from packet import *
from util import *
from torrent import *
from random import randint
from platform import system


class Client:
    def __init__(self):
        self.__socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

        # Ip and port of the bootstrap server
        self.conn_bootstrap = ('80.112.140.14', 65400)

        # Variable to know between threads whether we are punched
        self.punched = {}
        # Variable to know between threads whether the other is punched
        self.punched_other = {}

        # List of torrents
        self.torrents = []

        # Dict of seeders, punched seeders and active seeders by torrent hash
        self.seeders = {}
        self.punched_seeders = []
        self.requests = {}
        self.max_requests_per_torrent = 3
        self.max_requests_per_seeder = 3

        # Counter for how many pieces we are receiving
        self.counter = {}
        self.speed = {}
        self.total_speed = 0

    def start(self):
        if system() == "Windows":
            host_name = socket.gethostname()
            host_ip = socket.gethostbyname(host_name)
            while True:
                try:
                    self.__socket.bind((host_ip, randint(49152, 65535)))
                    break
                except:
                    pass
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
        speed_thread = threading.Thread(target=self.__speed)
        speed_thread.setDaemon(True)
        speed_thread.start()
        while True:
            pass

    def __push(self):
        while True:
            inp = input("> ")
            spl = inp.split(" ")

            if len(spl) == 0:
                continue

            # Torrent
            if spl[0] == "load":
                self.load_torrent(inp)
            elif spl[0] == "generate":
                self.generate_torrent(inp)
            elif spl[0] == "list":
                if not len(self.torrents):
                    print("No torrents available.\nUse load or generate to add new torrents.")
                for torrent in self.torrents:
                    print(torrent.id, torrent.file.path, torrent.hash)
            elif spl[0] == "remove":
                self.remove_torrent(inp)
            # Seeding
            elif spl[0] == "seed":
                self.start_seeding(inp)
            elif spl[0] == "!seed":
                self.stop_seeding(inp)
            # Download
            elif "download" in inp:
                self.start_download(inp)

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

            # PING
            if packet.type == 2:
                self.receive_ping(packet, conn)
            # LIST SEEDERS
            elif packet.type == 3:
                self.receive_seeders(packet)
            # REQUEST FOR DOWNLOAD
            elif packet.type == 6:
                self.send_piece(packet, conn)
            # DOWNLOAD OF PIECE
            elif packet.type == 7:
                self.receive_piece(packet, conn)
            # PUNCHING
            elif packet.type == 8 or packet.type == 9:
                self.receive_punch(packet, conn)
            save_torrents(self.torrents)

    def load_torrent(self, data):
        try:
            path = data.split(' ', 1)[1]
            torrent = TorrentFile.load(path)
            if torrent is None:
                print('File already exists. Overwrite? Y/[N]: ', end='')
                to_overwrite = input()
                if to_overwrite.upper().startswith('Y'):
                    torrent = TorrentFile.load(path, overwrite=True)
                else:
                    return

            if torrent.hash not in [t.hash for t in self.torrents]:
                self.torrents.append(torrent)
            else:
                print("Torrent is already added")
        except IndexError:
            print("Usage: load /path/to/file\nLoad a torrent from a torrent file")
        except FileNotFoundError:
            print("The file does not exists")

    def generate_torrent(self, data):
        try:
            path = data.split(" ")[1]
            torrent = Torrent(path, 1000, len(self.torrents))
            path = TorrentFile.dump(torrent, path)
            print("Saved torrent file:", path)
            self.torrents.append(torrent)
        except (IndexError, TypeError, ValueError):
            print("Usage: generate id /path/to/file\nGenerate a torrent file for a given torrent")

    def remove_torrent(self, data):
        try:
            self.torrents = [t for t in self.torrents if t.id != int(data.split(" ")[1])]
        except IndexError:
            print("Usage: remove torrent_id\nRemove a torrent from local cache (does not delete downloaded file).")

    def start_seeding(self, data):
        try:
            torrent = self.torrents[int(data.split(" ")[1])]
            packet = Packet()
            packet.type = 0
            packet.hash = torrent.hash
            send(self.__socket, packet.to_bytes(), self.conn_bootstrap)
        except IndexError:
            print("Usage: seed torrent_id\nStart seeding a torrent.")

    def stop_seeding(self, data):
        try:
            torrent = self.torrents[int(data.split(" ")[1])]
            packet = Packet()
            packet.type = 1
            packet.hash = torrent.hash
            send(self.__socket, packet.to_bytes(), self.conn_bootstrap)
        except IndexError:
            print("Usage: !seed torrent_id\nStop seeding a torrent.")

    def start_download(self, data):
        try:
            packet = Packet()
            torrent = self.torrents[int(data.split(" ")[1])]
            packet.hash = torrent.hash

            # Get seeders list
            self.request_seeders(data)
            time.sleep(1)

            if torrent.hash not in self.seeders:
                print("Received no response from the bootstrap. Please check if its online.")
                return

            if len(self.seeders[torrent.hash]) == 0:
                raise ModuleNotFoundError

            # Main download loop
            while True:
                # Try to download from more seeders if limit isn't reached
                if len(self.requests[torrent.hash]) < self.max_requests_per_torrent:
                    # Find an available piece number
                    packet.piece_no = torrent.get_piece_no()
                    if packet.piece_no == -1:
                        break

                    # Get seeders list
                    self.request_seeders(data)
                    time.sleep(1)

                    # Find users which are not being requested yet
                    idle_seeders = [s for s in self.seeders[torrent.hash] if s not in self.requests[torrent.hash]]

                    # If there are no idle seeders, find a seeder who is not very busy
                    if len(idle_seeders) == 0:
                        # Find fewest used active seeder
                        requests = {}
                        for conn in self.requests[torrent.hash]:
                            num = self.requests[torrent.hash].count(conn)
                            requests[conn] = num

                        seeder = min(requests, key=requests.get)

                        # If the fewest used active seeder is already used a lot
                        if requests[seeder] > self.max_requests_per_seeder:
                            time.sleep(1)
                            break
                    else:
                        seeder = idle_seeders[0]

                    if seeder not in self.punched_seeders:
                        # Tell the bootstrap you want to start punching someone
                        packet.type = 8
                        packet.seeders.append(seeder)
                        send(self.__socket, packet.to_bytes(), self.conn_bootstrap)

                        # Punch an idle seeder
                        self.send_punch(packet, seeder)

                    # Mark the seeders as active
                    self.requests[torrent.hash].append(seeder)

                    # Request a download
                    packet.type = 6
                    send(self.__socket, packet.to_bytes(), seeder)
                else:
                    # Wait a bit before trying again
                    time.sleep(1)
        except IndexError:
            print("Usage: download torrent_id\nGet list of seeders of a torrent.")
        except ModuleNotFoundError:
            print("No seeders where found at this time, please try again later.")

    def send_piece(self, packet, conn):
        try:
            torrent = [t for t in self.torrents if t.hash == packet.hash][0]
            packet.type = 7
            packet.data = torrent.get_piece(packet.piece_no)
            send(self.__socket, packet.to_bytes(), conn)
            print("Sending a piece for torrent", torrent.id)
        except IndexError:
            print("Received a request for an unknown torrent", packet.hash, packet)

    def receive_piece(self, packet, conn):
        try:
            torrent = [t for t in self.torrents if t.hash == packet.hash][0]
            torrent.add_piece(packet.piece_no, data=packet.data)

            # Clear seeder from request list
            if conn in self.requests[torrent.hash]:
                self.requests[torrent.hash].remove(conn)

            # Count how many pieces we receive
            if torrent.hash not in self.counter:
                self.counter[torrent.hash] = 0
            self.counter[torrent.hash] += 1
            print("Succesfully received a piece for torrent", torrent.id)
        except IndexError:
            print("Received a piece of an unknown torrent", packet.hash, packet)

    def request_seeders(self, data):
        try:
            torrent = self.torrents[int(data.split(" ")[1])]
            packet = Packet()
            packet.type = 3
            packet.hash = torrent.hash
            send(self.__socket, packet.to_bytes(), self.conn_bootstrap)
        except IndexError:
            print("Usage: seeders torrent_id\nGet list of seeders of a torrent.")

    def receive_seeders(self, packet):
        # Refresh the seeder list
        self.seeders[packet.hash] = packet.seeders

        # Create a list for this hash if it doesn't exist
        if packet.hash not in self.requests:
            self.requests[packet.hash] = []

    def receive_punch(self, packet, sender):
        # Only respond to pull if it is a request (comes from bootstrap)
        if sender == self.conn_bootstrap:
            print("Received punch request")
            to_be_punched = packet.seeders[0]
            punch_thread = threading.Thread(target=self.send_punch, args=(packet, to_be_punched))
            punch_thread.setDaemon(True)
            punch_thread.start()
            return

        # Its am actual punch and we have not been punched yet
        if not self.punched[sender]:
            self.punched = True
            print("Punched by", sender)

        # If the packet is of type 9, the other client has been punched
        if packet.type == 9:
            self.punched_other[sender] = True
            print("Punched", sender)

    def send_punch(self, packet, conn):
        self.punched[conn] = False
        self.punched_other[conn] = False
        # We have not been punched yet
        while True and not self.punched[conn]:
            send(self.__socket, packet.to_bytes(), conn)
            time.sleep(.5)
        # We have been punched, but the other one not yet
        while True and not self.punched_other[conn]:
            packet.type = 9
            send(self.__socket, packet.to_bytes(), conn)
            time.sleep(.5)
        # Final punch
        packet.type = 9
        send(self.__socket, packet.to_bytes(), conn)

    def __speed(self):
        while True:
            total_speed = 0
            for hash in self.counter:
                self.speed[hash] = self.counter[hash]
                self.counter[hash] = 0
                total_speed += self.speed[hash]
            self.total_speed = total_speed
            time.sleep(1)

    def __ping(self):
        packet = Packet()
        packet.type = 2
        while True:
            connections = copy.deepcopy(self.punched_seeders)
            for conn in connections:
                packet.hash = hash
                if conn in self.punched_seeders:
                    self.punched_seeders.remove(conn)
                send(self.__socket, packet.to_bytes(), conn)
            # Ping every 15 seconds. NAT's remove entries after
            # about 60sec but it varies....
            time.sleep(15)

    def receive_ping(self, packet, conn):
        if conn == self.conn_bootstrap:
            send(self.__socket, packet.to_bytes(), self.conn_bootstrap)
        else:
            if packet.hash not in self.punched_seeders:
                self.punched_seeders = []
            self.punched_seeders.append(conn)


if __name__ == "__main__":
    client = Client()
    client.start()
