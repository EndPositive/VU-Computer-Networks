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
    except socket.error:
        return False


class ChatClient:
    def __init__(self):
        self.__socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

        self.__pushThread = threading.Thread(target=self.__push)
        self.__pushThread.setDaemon(True)

        self.__pullThread = threading.Thread(target=self.__pull)
        self.__pullThread.setDaemon(True)

        self.Quit = False
        self.__Wait = 0

        self.name = ""

    def start(self):
        self.__socket.connect(('18.195.107.195', 5382))
        if self.__connect():
            self.__pushThread.start()
            self.__pullThread.start()
        else:
            self.close()

    def __connect(self):
        print("Username: ", end="", flush=True)
        name = input()
        if not name:
            return self.__connect()

        if not send(self.__socket, 'HELLO-FROM ' + name + '\n'):
            return False

        res = receive(self.__socket, 4096)
        if not res:
            return False

        spl = res.split()
        if spl[0] == "IN-USE":
            print("Username already in use.")
            return self.__connect()
        elif spl[0] == "BUSY":
            print("Server is busy.")
            return False
        elif spl[0] == "HELLO":
            self.name = name
            print("Connected.")
            return True
        else:
            return False

    def __push(self):
        while True and not self.Quit:
            if not self.__Wait == 0:
                continue

            print("\n<" + self.name + ">: ", end="", flush=True)
            inp = input()
            if not inp:
                continue

            spl = inp.split()
            if spl[0] == "!quit":
                break
            elif spl[0] == "!who":
                self.__Wait = 1
                if not send(self.__socket, 'WHO\n'):
                    break
            elif inp[0] == "@":
                user = spl[0][1:]
                msg = " ".join(spl[1:])
                if user == self.name:
                    self.__Wait = 2
                else:
                    self.__Wait = 1
                if not send(self.__socket, "SEND " + user + " " + msg + "\n"):
                    break
            else:
                self.__Wait = 1
                send(self.__socket, inp + "\n")
        self.close()

    def __pull(self):
        while True and not self.Quit:
            res = receive(self.__socket, 4096)
            if not res:
                break

            spl = res.split()
            print('\x1b[1A' + '\x1b[2K' + '\x1b[1A')
            if spl[0] == "WHO-OK":
                print("Online users: ", ",".join(spl[1:]))
            elif spl[0] == "SEND-OK":
                print("Message successfully sent.")
                self.__Wait -= 1
                continue
            elif spl[0] == "UNKNOWN":
                print("User is not online.")
            elif spl[0] == "DELIVERY":
                print("<" + spl[1] + ">:", " ".join(spl[2:]))
                self.__Wait -= 1
                continue
            elif spl[0] == "BAD-RQST-HDR":
                print("Bad parameters")
            elif spl[0] == "BAD-RQST-BODY":
                print("Bad parameters")
            else:
                print(res)
            self.__Wait = 0
        self.close()

    def close(self, code=0):
        self.Quit = True
        self.__socket.close()
        exit(code)


if __name__ == '__main__':
    chatClient = ChatClient()
    chatClient.start()
    while True and not chatClient.Quit:
        pass
