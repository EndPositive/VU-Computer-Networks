import socket
import random
import string
import threading
import time


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
            while b'\n' not in data[-1:]:
                data += conn.recv(size)
                if not data:
                    break
            return data.decode("utf-8")
    except socket.error:
        return False


class ChatClient:
    def __init__(self):
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.name = ""

    def start(self):
        self.socket.connect(('127.0.0.1', 65432))
        if not self.__connect():
            self.close()

    def __connect(self):
        name = randomString()
        print("Connection ", name)
        if send(self.socket, 'HELLO-FROM ' + name + '\n'):
            res = receive(self.socket, 4096)
            if res:
                spl = res.split()
                if spl[0] == "HELLO":
                    self.name = name
                    return True
        print("Something went wrong.\nDisconnecting from host...")
        return False

    def close(self):
        self.socket.close()


def spam(client, msg):
    while True:
        if not send(client.socket, msg):
            break
        time.sleep(0.5)
    print("BIG PROBLEM")


if __name__ == '__main__':
    clients = []
    n_clients = 62
    for i in range(n_clients):
        print(str(i) + ": ", end="", flush=True)
        chatClient = ChatClient()
        chatClient.start()
        clients.append(chatClient)

    for i in range(n_clients):
        t = threading.Thread(target=spam, args=(clients[i], 'SEND echobot Hi, its me: ' + clients[i].name + '\n'))
        t.daemon = True
        t.start()

    while True:
        pass
