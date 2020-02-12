import socket
import random
import string

def randomString(stringLength=10):
    letters = string.ascii_lowercase
    return ''.join(random.choice(letters) for i in range(stringLength))


def send(conn, msg):
    try:
        conn.sendall(msg.encode('utf-8'))
        return True
    except socket.error:
        return False


def receive(conn, size):
    try:
        data = conn.recv(size)
        if not data:
            return False
        else:
            while not data[-1:] == b'\n':
                data += conn.recv(size)
                if not data:
                    break
            return data.decode("utf-8")
    except socket.error:
        return False


class ChatClient:
    def __init__(self):
        self.__socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

        self.Quit = False
        self.__Wait = 0

        self.name = ""

    def start(self):
        self.__socket.connect(('127.0.0.1', 65432))
        if self.__connect():
            print("CONNECTED")
        else:
            print("ABORT")
            self.close()

    def __connect(self):
        name = randomString(10)
        print("Connection ", name)
        if send(self.__socket, 'HELLO-FROM ' + name + '\n'):
            res = receive(self.__socket, 4096)
            if res:
                spl = res.split()
                if spl[0] == "IN-USE":
                    print("Username already in use.")
                    return self.__connect()
                elif spl[0] == "BUSY":
                    print("Server is busy.")
                elif spl[0] == "HELLO":
                    self.name = name
                    print("Connected.")
                    return True
            else:
                print("Something went wrong.")
        print("Disconnecting from host...")
        return False

    def close(self, code=0):
        self.__socket.close()


if __name__ == '__main__':
    clients = []
    for i in range(0, 100):
        chatClient = ChatClient()
        chatClient.start()
        clients.append(chatClient)
        print(i)
    while True:
        pass
