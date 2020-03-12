import socket
import time
from packet import *
from util import *


class Client:
    def __init__(self):
        self.__socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

    def start(self):
        # Connect to bootstrap
        self.__socket.connect(('80.112.140.14', 65400))
        self.__push()

    def __push(self):
        while True:
            inp = input("> ")
            packet = Packet()
            if "!seed" in inp:
                packet.type = 1
                # packet.hash = " ".split(inp)[1]
            elif "seed" in inp:
                packet.type = 0
                # packet.hash = " ".split(inp)[1]
            elif "list" in inp:
                packet.type = 3
                # packet.hash = " ".split(inp)[1]
            elif "create" in inp:
                # file = " ".split(inp)[1]
                packet.type = 4
                # packet.hash = md5(file)
            elif "download" in inp:
                packet.type = 6
                # packet.hash = " ".split(inp)[1]
                packet.piece_no = " ".split(inp)[2]
            else:
                print("unknown command")
                return

            by = packet.to_bytes()
            send(self.__socket, by)
            time.sleep(0.3)
            res = receive(self.__socket, 4096)
            if not res:
                print("Something bad happend: ", res)
                return
            p = Packet(res)
            if p.type == packet.type:
                print("Success")
            else:
                print("Something bad happend, type: ", p.type, p.err)



if __name__ == "__main__":
    client = Client()
    client.start()