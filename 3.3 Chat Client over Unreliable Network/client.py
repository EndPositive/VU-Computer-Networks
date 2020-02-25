import socket
import threading
import time
from rc5 import *


def send(conn, msg):
    if type(msg) == str:
        msg += '\n'
        msg = msg.encode('utf8')
    try:
        conn.sendto(msg, ('18.195.107.195', 5382))
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
            return data
    except socket.error:
        return False


def msg_to_bits(msg):
    bits = 0
    for i in range(len(msg) - 1, -1, -1):
        bits += msg[i] << (i * 8)
    return bits


def get_crc(m, p=0xb):
    r = msg_to_bits(m) << (len(bin(p)) - 3)
    while len(bin(r)) >= len(bin(p)):
        d = p << len(bin(r)) - len(bin(p))
        r = d ^ r
    return r


def set_header(data, msg_id, ack=False):
    header = msg_id.to_bytes(1, 'big') + (ack << 7).to_bytes(1, 'big')
    return get_crc(header + data).to_bytes(1, 'big') + header + data


def get_header(packet):
    crc_check = packet[0] == get_crc(packet[1:])
    msg_id = packet[1]
    ack = (packet[2] & 0b10000000) > 0
    data = packet[3:]
    return crc_check, msg_id, ack, data


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
        # ACK maps username to boolean values meaning if they sent us an ack after we sent them a message
        self.ACK = {}
        self.OK = False

    def start(self):
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

        if res.startswith(b"IN-USE"):
            print("Username already in use.")
            return self.__connect()
        elif res.startswith(b"BUSY"):
            print("Server is busy.")
            return self.__connect()
        elif res.startswith(b"HELLO"):
            self.name = name
            print("Connected.")
            return True
        return False

    def __push(self):
        while True and not self.Quit:
            if self.__Wait != 0:
                continue

            inp = input("\n$ ")
            if not inp:
                continue

            spl = inp.split(' ', 1)
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
                self.ACK[user] = False
                if not self.send_msg(user, msg):
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

            if res.startswith(b"WHO-OK"):
                print("Online users: ", res[7:-1].decode('utf8'))
            elif res.startswith(b"SEND-OK"):
                self.OK = True
            elif res.startswith(b"UNKNOWN"):
                print("User is not online.")
            elif res.startswith(b"DELIVERY"):
                spl = res.split(b' ', 2)

                from_user = spl[1].decode('utf8')
                crc_check, msg_id, ack_flag, data = get_header(spl[2])

                if not crc_check:
                    print("INCORRECT CRC")
                    continue

                # check if the ack is set in the header
                if ack_flag:
                    self.ACK[from_user] = True
                    print("RECEIVED ACK")
                    continue

                rc = rc5([0x91, 0x5F, 0x46, 0x19, 0xBE, 0x41, 0xB2, 0x51, 0x63, 0x55, 0xA5, 0x01, 0x10, 0xA9, 0xCE, 0x91])
                print("Received msg from " + from_user + ": ", rc.decrypt_msg(data[:-1]))

                self.OK = False
                t = threading.Thread(target=self.send_ack, args=(from_user,))
                t.start()
            elif res.startswith(b"BAD-RQST-HDR"):
                print("Unknown command.")
            elif res.startswith(b"BAD-RQST-BODY"):
                print("Bad parameters")
            else:
                print("Unknown error")

            self.__Wait -= 1

        self.close()

    def send_msg(self, user, msg, ack=False):
        rc = rc5([0x91, 0x5F, 0x46, 0x19, 0xBE, 0x41, 0xB2, 0x51, 0x63, 0x55, 0xA5, 0x01, 0x10, 0xA9, 0xCE, 0x91])
        data = rc.encrypt_msg(msg)
        data += b"\n"
        packet = set_header(data, 0, ack=ack)
        while not self.ACK[user]:
            send(self.__socket, b"SEND " + user.encode('utf8') + b" " + packet)
            print("SENT MSG")
            time.sleep(.5)
        return True

    def send_ack(self, user):
        if type(user) == str:
            user = user.encode('utf8')

        msg = set_header(b'\n', 0, ack=True)
        while not self.OK:
            send(self.__socket, b"SEND " + user + b" " + msg)
            print("SENT ACK")
            time.sleep(0.5)
        return True

    def close(self, code=0):
        self.__socket.close()
        exit(code)


if __name__ == '__main__':
    chatClient = ChatClient()
    chatClient.start()
    while True and not chatClient.Quit:
        pass
