import socket
from packet import *
from util import *


class Client:
    def __init__(self):
        self.__socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

    def start(self):
        # Connect to bootstrap
        self.__socket.connect(('localhost', 65427))
        self.__push()

    def __push(self):
        packet = Packet()
        packet.type = 0
        by = packet.to_bytes()
        send(self.__socket, by)
        res = receive(self.__socket, 4096)
        if not res:
            print("Something bad happend: ", res)
            return
        p = Packet(res)
        print(p.type)


if __name__ == "__main__":
    client = Client()
    client.start()