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


class ChatServer:
    def __init__(self):
        self.__socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

        self.connections = []

    def start(self):
        self.__socket.bind(('localhost', 65432))
        self.__socket.listen()

        self.connections.append(["", "", "echobot"])

        while True:
            conn, addr = self.__socket.accept()
            self.connections.append([conn, addr, ""])
            pullThread = threading.Thread(target=self.__pull, args=(conn, addr, ""))
            pullThread.setDaemon(True)
            pullThread.start()

    def online(self, user):
        conn = [x for x in self.connections if x[2] == user]
        if len(conn):
            return conn[0]
        return False

    def getNames(self):
        names = []
        for x in self.connections:
            names.append(x[2])
        return names

    def __pull(self, conn, addr, name):
        print(conn, addr, name)
        disconnect = False
        while True and not disconnect:
            res = receive(conn, 4096)
            if res:
                print("IN:  ", res[:-1])
                spl = res.split()
                if spl[0] == "HELLO-FROM":
                    if len(spl) < 2:
                        msg = "BAD-RQST-BODY\n"
                    elif len(self.connections) >= 64:
                        msg = "BUSY\n"
                        disconnect = True
                    elif not any(x for x in self.connections if x[2] == spl[1]):
                        i = self.connections.index([conn, addr, name])
                        name = spl[1]
                        self.connections[i] = [conn, addr, name]
                        msg = "HELLO " + spl[1] + "\n"
                    else:
                        msg = "IN-USE"
                        disconnect = True
                elif spl[0] == "WHO":

                    msg = "WHO-OK " + ",".join(self.getNames()) + "\n"
                elif spl[0] == "SEND":
                    if len(spl) < 3:
                        msg = "BAD-RQST-BODY\n"
                    elif self.online(spl[1]):
                        if spl[1] == "echobot":
                            if send(conn, "SEND-OK\n"):
                                msg = "DELIVERY echobot " + " ".join(spl[2:]) + "\n"
                            else:
                                disconnect = True
                        else:
                            to = self.online(spl[1])[0]
                            if send(to, "DELIVERY " + name + " " + " ".join(spl[2:]) + "\n"):
                                msg = "SEND-OK\n"
                            else:
                                disconnect = True
                    else:
                        msg = "UNKNOWN\n"
                else:
                    msg = "BAD-RQST-HDR\n"
                print("OUT: ", msg)
                if not send(conn, msg):
                    disconnect = True
            else:
                print("Disconnecting ", name, "...\n")
                disconnect = True
        self.connections.remove([conn, addr, name])
        conn.close()


if __name__ == '__main__':

    chatServer = ChatServer()
    chatServer.start()

    while True:
        pass
