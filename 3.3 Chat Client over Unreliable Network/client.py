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


def to_bits(msg):
    bits = 0
    for i in range(len(msg) - 1, -1, -1):
        bits += msg[i] << (i * 8)
    return bits


def get_crc(m, p=0xb):
    r = to_bits(m) << (len(bin(p)) - 3)
    while len(bin(r)) >= len(bin(p)):
        d = p << len(bin(r)) - len(bin(p))
        r = d ^ r
    return r


def set_header(msg, msg_id, msg_type=0):
    header = (msg_id % 256).to_bytes(1, 'big') + (msg_type << 6).to_bytes(1, 'big')
    print(get_crc(header + msg).to_bytes(1, 'big'))
    return get_crc(header + msg).to_bytes(1, 'big') + header + msg + b'\n'


def get_header(msg):
    crc_check = msg[0] == get_crc(msg[1:-1])
    msg_id = msg[1]
    msg_type = msg[2] >> 6
    return crc_check, msg_id, msg_type, msg[3:][:-1]


class ChatClient:
    def __init__(self):
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
        self.MAX_ID = 256

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
                spl = res.split(b' ', 2)

                from_user = spl[1].decode('utf8')
                try:
                    crc_check, msg_id, msg_type, msg = get_header(spl[2])
                except IndexError:
                    print('Incorrect header')
                    continue

                if not crc_check:
                    print("INCORRECT CRC")
                    continue

                # check if the message is an ack
                if msg_type == 1:
                    for i in range(len(self.q[from_user])):
                        if self.q[from_user][i][1] == msg_id:
                            del self.q[from_user][i]
                            break
                    print("RECEIVED ACK")
                    continue

                # reset the id set if necessary
                if from_user not in self.receive or len(self.receive[from_user]) > self.MAX_ID:
                    self.receive[from_user] = set()

                # check if the message is DH exchange
                if msg_type == 2 and msg_id not in self.receive[from_user]:
                    if from_user not in self.dh:
                        self.dh[from_user] = DH()
                    self.dh[from_user].set_secret(msg)

                    # reply with a DH of our own
                    self.send_msg(from_user, self.dh[from_user].get_public_info(), msg_type=2)

                # check if the message is a normal message
                if msg_type == 0 and msg_id not in self.receive[from_user]:
                    if from_user in self.dh:
                        msg = self.dh[from_user].decrypt(msg)
                    print("Received msg from " + from_user + ": ", msg.decode('utf8'))

                self.send_ack(from_user, msg_id)
            elif res.startswith(b"BAD-RQST-HDR"):
                print("Unknown command.")
            elif res.startswith(b"BAD-RQST-BODY"):
                print("Bad parameters")
            elif res.startswith(b"VALUE"):
                print(res)
            elif res.startswith(b"SET-OK"):
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
                # we need to make a DH exchange
                self.send_msg(user, self.dh[user].get_public_info(), msg_type=2)

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
        print("SENT ACK")
        return True

    def queue_send(self, user):
        # TODO: SOLVE BUG WHERE \n byte in the message ends the transmission: maybe use byte stuffing
        while self.q[user]:
            try:
                msg = self.q[user][0][0]
                msg_id = self.q[user][0][1]
                msg_type = self.q[user][0][2]
            except IndexError:
                continue

            if msg_type == 0:
                if user not in self.dh or self.dh[user].password is None:
                    time.sleep(0.5)
                    continue
                msg = self.dh[user].encrypt(msg)

            msg = set_header(msg, msg_id, msg_type)

            send(self.__socket, b"SEND " + user.encode('utf8') + b" " + msg)
            print("SENT", msg)
            time.sleep(.5)

    def close(self, code=0):
        self.__socket.close()
        exit(code)


if __name__ == '__main__':
    chatClient = ChatClient()
    chatClient.start()
    while True and not chatClient.Quit:
        pass
