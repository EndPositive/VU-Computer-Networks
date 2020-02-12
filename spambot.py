import socket
import threading


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
    except socket.error as e:
        print(e)
        return False


class ChatClient:
    def __init__(self):
        self.__socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

        self.Quit = False
        self.__Wait = 0

        self.name = ""

    def start(self):
        self.__socket.connect(('18.195.107.195', 5378))
        if self.__connect():
            while True:
                if send(self.__socket, "WHO\n"):
                    print("WHO")
                    rev = receive(self.__socket, 4096)
                    if rev:
                        print("WHO-OK")
                        spl = rev.split()
                        who = " ".join(spl[1:]).split(",")
                        for i in range(len(who)):
                            if not who[i] == "echobot" and not who[i] == "spambot":
                                print("SEND")
                                if send(self.__socket, "SEND " + who[i] + " SPAM\n"):
                                    res = receive(self.__socket, 4096)
                                    print(res)
                                    if res and "SEND-OK" in res:
                                        print("SEND-OK")
                                        continue
                                    print("ERROR SENDING TO " + who[i])
                        continue
                break
            self.close()
        else:
            self.close()

    def __connect(self):
        name = "spambot"
        if send(self.__socket, 'HELLO-FROM ' + name + '\n'):
            res = receive(self.__socket, 4096)
            if res:
                spl = res.split()
                if spl[0] == "IN-USE":
                    print("Username already in use.")
                    return self.__connect()
                elif spl[0] == "BUSY":
                    print("Server is busy." + name)
                elif spl[0] == "HELLO":
                    self.name = name
                    print("Connected " + self.name)
                    return True
            else:
                print("Something went wrong.")
        return False

    def close(self, code=0):
        print("CLOSED " + self.name)
        self.__socket.close()


if __name__ == '__main__':
    chatClient = ChatClient()
    thread = threading.Thread(target=chatClient.start)
    thread.daemon = True
    thread.start()

    thread.join()
