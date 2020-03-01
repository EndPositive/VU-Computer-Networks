import socket
import threading
import time
from dh import DH

cts = threading.Lock()


def send(conn, msg):
    global cts
    if type(msg) == str:
        msg += '\n'
        msg = msg.encode()
    try:
        cts.acquire()
        # conn.sendto(msg, ('192.168.0.102', 5382))
        conn.sendto(msg, ('18.195.107.195', 5382))
        cts.release()
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


def escape(msg):
    return msg.replace(b'\x00', b'\x00\x00').replace(b'\n', b'\x00\x01')


def unescape(msg):
    new_msg = b''
    i = 0
    while i < len(msg):
        if msg[i] == 0x00:
            if i < len(msg) - 1:
                if msg[i + 1] == 0x01:
                    new_msg += b'\n'
                elif msg[i + 1] == 0x00:
                    new_msg += b'\x00'
            else:
                return b''
            i += 1
        else:
            new_msg += msg[i: i + 1]
        i += 1

    return new_msg


def to_bits(msg):
    bits = 0
    for i in range(len(msg) - 1, -1, -1):
        bits += msg[i] << (i * 8)
    return bits


def get_crc(m, p=0x973afb51):
    r = to_bits(m) << (len(bin(p)) - 3)
    while len(bin(r)) >= len(bin(p)):
        d = p << len(bin(r)) - len(bin(p))
        r = d ^ r
    return r


def set_header(msg, msg_id, msg_type=0):
    header = (msg_id % 256).to_bytes(1, 'big') + (msg_type << 5).to_bytes(1, 'big')
    return escape(get_crc(header + msg).to_bytes(4, 'big') + header + msg) + b'\n'


def get_header(msg):
    msg = unescape(msg[:-1])
    crc_check = msg[0:4] == get_crc(msg[4:]).to_bytes(4, 'big')
    msg_id = msg[4]
    msg_type = msg[5] >> 5
    return crc_check, msg_id, msg_type, msg[6:]

class ChatClient:
    def __init__(self, verbose=False):
        self.verbose = verbose

        self.__socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

        self.__pushThread = threading.Thread(target=self.__push)
        self.__pushThread.setDaemon(True)

        self.__pullThread = threading.Thread(target=self.__pull)
        self.__pullThread.setDaemon(True)

        self.Quit = False

        self.name = ""

        # maps username to id
        self.id = {}

        # maximum number of id's before self.receive gets reset
        self.MAX_ID = 255

        # maps username to arrays (an array is a queue)
        # each element in the queue is a bytes object
        self.q = {}

        # maps usernames to set of id's (of messages you received)
        self.receive = {}

        # maps usernames to a DH object with crypto information
        self.dh = {}

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
            inp = input()
            if not inp:
                continue

            spl = inp.split(' ', 1)
            if spl[0] == "!quit":
                self.Quit = True
            elif spl[0] == "!who":
                if not send(self.__socket, 'WHO'):
                    print("Something went wrong.\nDisconnecting from host...")
                    self.Quit = True
            elif inp[0] == "@":
                user = spl[0][1:]
                try:
                    msg = spl[1]
                except IndexError:
                    print('WTF ARE YOU DOING?')
                    continue
                self.send_msg(user, msg)
            elif spl[0] == "SET":
                send(self.__socket, inp)
            elif spl[0] == "RESET":
                send(self.__socket, inp)
            elif spl[0] == "GET":
                send(self.__socket, inp)
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
                pass
            elif res.startswith(b"UNKNOWN"):
                print("User is not online.")
            elif res.startswith(b"DELIVERY"):
                if self.verbose:
                    print("RECEIVED")
                spl = res.split(b' ', 2)

                from_user = spl[1].decode('utf8')
                try:
                    crc_check, msg_id, msg_type, msg = get_header(spl[2])
                except IndexError:
                    if self.verbose:
                        print('Incorrect header')
                    continue

                if not crc_check:
                    if self.verbose:
                        print("INCORRECT CRC")
                    continue

                # check if the message is an ack
                if msg_type == 1:
                    for i in range(len(self.q[from_user])):
                        if self.q[from_user][i][1] == msg_id:
                            del self.q[from_user][i]
                            break
                    if self.verbose:
                        print("RECEIVED ACK")
                    continue

                # reset the id set if necessary
                if from_user not in self.receive or len(self.receive[from_user]) > self.MAX_ID:
                    self.receive[from_user] = set()

                # check for duplicates
                if msg_id not in self.receive[from_user]:
                    self.receive[from_user].add(msg_id)
                    if msg_type == 2 or msg_type == 3:
                        if from_user not in self.dh:
                            self.dh[from_user] = DH()
                        self.dh[from_user].set_secret(msg)
                        if msg_type == 3:
                            self.send_msg(from_user, self.dh[from_user].get_public_info(), msg_type=2)
                    elif msg_type == 0:
                        if from_user in self.dh:
                            msg = self.dh[from_user].decrypt(msg)
                        print(from_user + ": ", msg.decode('utf8'))

                self.send_ack(from_user, msg_id)
            elif res.startswith(b"BAD-RQST-HDR"):
                print("Unknown command.")
            elif res.startswith(b"BAD-RQST-BODY"):
                print("Bad parameters")
            elif res.startswith(b"VALUE"):
                if self.verbose:
                    print(res)
            elif res.startswith(b"SET-OK"):
                if self.verbose:
                    print(res)
        self.close()

    def send_msg(self, user, msg, msg_type=0):
        if type(msg) == str:
            msg = msg.encode('utf8')

        if user not in self.id:
            self.id[user] = 0

        msg_id = self.id[user]
        self.id[user] += 1

        if msg_type == 0:
            if user not in self.dh:
                self.dh[user] = DH()

            if self.dh[user].password is None:
                # we need to ask for DH parameters
                self.send_msg(user, self.dh[user].get_public_info(), msg_type=3)

        if user not in self.q:
            self.q[user] = []
        if not self.q[user]:
            self.q[user].append([msg, msg_id, msg_type])
            t = threading.Thread(target=self.queue_send, args=(user,))
            t.daemon = True
            t.start()
        else:
            self.q[user].append([msg, msg_id, msg_type])

    def send_ack(self, user, msg_id):
        if type(user) == str:
            user = user.encode('utf8')

        msg = set_header(b'', msg_id, msg_type=1)
        send(self.__socket, b"SEND " + user + b" " + msg)
        if self.verbose:
            print("SENT ACK")
        return True

    def queue_send(self, user):
        while self.q[user]:
            try:
                msg = self.q[user][0][0]
                msg_id = self.q[user][0][1]
                msg_type = self.q[user][0][2]
            except IndexError:
                continue

            if msg_type == 0:
                if user not in self.dh or self.dh[user].password is None:
                    time.sleep(1)
                    continue
                msg = self.dh[user].encrypt(msg)

            msg = set_header(msg, msg_id, msg_type)

            send(self.__socket, b"SEND " + user.encode('utf8') + b" " + msg)
            if self.verbose:
                print("SENT", msg)
            time.sleep(.5)

    def close(self, code=0):
        self.__socket.close()
        exit(code)


if __name__ == '__main__':
    chatClient = ChatClient(True)
    chatClient.start()
    while True and not chatClient.Quit:
        pass
