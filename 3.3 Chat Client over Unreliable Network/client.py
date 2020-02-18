import socket
import threading
import time


def send(conn, msg):
    try:
        conn.sendto((msg + "\n").encode('utf-8'), ('18.195.107.195', 5382))
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


def to_bits(msg):
    msg = msg.encode()
    bits = 0
    for i in range(len(msg) - 1, -1, -1):
        bits += msg[i] << (i * 8)
    return bits


def get_crc(m, p=0xb):
    r = to_bits(m) << len(bin(p)) - 3
    while True:
        if len(bin(r)) < len(bin(p)):
            break
        d = p << len(bin(r)) - len(bin(p))
        r = d ^ r
    return r


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
        self.ACK = False
        self.OK = False

    def start(self):
        self.__socket.bind(("localhost", 54321))
        if self.__connect():
            self.__pushThread.start()
            self.__pullThread.start()
        else:
            print("Disconnecting from host...")
            self.close()

    def __connect(self):
        name = input("Username: ")
        if not name:
            return self.__connect()

        if not send(self.__socket, 'HELLO-FROM ' + name):
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
            return self.__connect()
        elif spl[0] == "HELLO":
            self.name = name
            print("Connected.")
            return True
        return False

    def __push(self):
        while True and not self.Quit:
            if not self.__Wait == 0:
                continue

            inp = input("\n$ ")
            if not inp:
                continue

            spl = inp.split()
            if spl[0] == "!quit":
                self.Quit = True
            elif spl[0] == "!who":
                self.__Wait = 1
                if not send(self.__socket, 'WHO'):
                    print("Something went wrong.\nDisconnecting from host...")
                    self.Quit = True
            elif inp[0] == "@":
                user = spl[0][1:]
                msg = " ".join(spl[1:])
                if user == "echobot" or user == self.name:
                    self.__Wait = 2
                else:
                    self.__Wait = 1
                self.ACK = False
                if not self.send_msg("SEND " + user + " " + msg):
                    print("Something went wrong.\nDisconnecting from host...")
                    self.Quit = True
            else:
                print("Unknown command")
        self.close()

    def __pull(self):
        while True and not self.Quit:
            res = receive(self.__socket, 4096)
            if not res:
                print("Something went wrong, disconnected from host.")
                self.Quit = True
                continue

            spl = res.split()
            if spl[0] == "WHO-OK":
                print("Online users: ", ",".join(spl[1:]))
            elif spl[0] == "SEND-OK":
                self.OK = True
            elif spl[0] == "UNKNOWN":
                print("User is not online.")
                self.ACK = True
            elif spl[0] == "DELIVERY":
                if "ACK" in res:
                    self.ACK = True
                    print("RECEIVED ACK")
                    continue

                if not spl[-1] == get_crc(spl[2:-1]):
                    print("INCORRECT CRC")
                    continue

                print("Received msg from " + spl[1] + ": ", " ".join(spl[2:-1]))

                self.OK = False
                t = threading.Thread(target=self.send_ack, args=(spl[1],))
                t.start()
            elif spl[0] == "BAD-RQST-HDR":
                print("Unknown command.")
            elif spl[0] == "BAD-RQST-BODY":
                print("Bad parameters")
            else:
                print("Unknown error")

            self.__Wait -= 1

        self.close()

    def send_msg(self, msg):
        data = " ".join(msg.split()[2:])
        while not self.ACK:
            send(self.__socket, msg + " " + get_crc(data))
            print("SENT MSG")
            time.sleep(.2)
        return True

    def send_ack(self, user):
        while not self.OK:
            send(self.__socket, "SEND " + user + " ACK")
            print("SENT ACK")
            time.sleep(0.2)
        return True

    def close(self, code=0):
        self.__socket.close()
        exit(code)


if __name__ == '__main__':
    chatClient = ChatClient()
    chatClient.start()
    while True and not chatClient.Quit:
        pass
