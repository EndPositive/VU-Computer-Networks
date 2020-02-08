import socket
import threading
import time

username = ""


def hello(name):
    global username
    username = name
    s.sendall(('HELLO-FROM ' + name + '\n').encode('utf-8'))


def who():
    s.sendall('WHO\n'.encode('utf-8'))


def send(user, msg):
    s.sendall(("SEND " + user + " " + msg + "\n").encode('utf-8'))


def receive(size):
    data = s.recv(size)
    if not data:
        return "Socket is closed."
    else:
        return data.decode("utf-8")


def connect():
    print("Username:")
    hello(input())
    time.sleep(.1)


def run():
    while True:
        print("\nCommand:")
        inp = input()
        spl = inp.split()
        if spl[0] == "!quit":
            s.close()
            exit(1)
            return
        elif spl[0] == "!who":
            who()
        elif inp[0] == "@":
            user = spl[0][1:]
            msg = " ".join(spl[1:])
            send(user, msg)
        else:
            print("Unknown command")
        time.sleep(.1)


def hear():
    while True:
        res = receive(4096)
        spl = res.split()
        if spl[0] == "WHO-OK":
            print("Online users: ", ",".join(spl[1:]))
        elif spl[0] == "SEND-OK":
            print("Message successfully sent.")
        elif spl[0] == "UNKNOWN":
            print("Unknown")
        elif spl[0] == "DELIVERY":
            print("Received msg: ", " ".join(spl[1:]))
        elif spl[0] == "BAD-RQST-HDR":
            print("Unknown command.")
        elif spl[0] == "BAD-RQST-BODY":
            print("Bad parameters")
        elif spl[0] == "IN-USE":
            print("Username already in use.")
            return connect()
        elif spl[0] == "BUSY":
            print("Server is busy.")
        elif spl[0] == "HELLO":
            print("Connected.")


if __name__ == '__main__':
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.connect(('18.195.107.195', 5378))

    threading.Thread(target=hear).start()

    connect()

    threading.Thread(target=run).start()