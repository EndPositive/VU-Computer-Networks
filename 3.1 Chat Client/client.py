import socket
import threading
import time
import sys

Quit = False


def receive(size):
    data = s.recv(size)
    if not data:
        return "Socket is closed."
    else:
        return data.decode("utf-8")


def connect():
    print("Username:")
    name = input()
    if name:
        s.sendall(('HELLO-FROM ' + name + '\n').encode('utf-8'))
        res = receive(4096)
        spl = res.split()
        if spl[0] == "IN-USE":
            print("Username already in use.")
        elif spl[0] == "BUSY":
            print("Server is busy.")
        elif spl[0] == "HELLO":
            print("Connected.")
            return True
    else:
        return connect()
    print("Bad name.")
    return False


def run():
    global Quit
    while True:
        print("\nCommand:")
        inp = input()
        if inp:
            spl = inp.split()
            if spl[0] == "!quit":
                Quit = True
            elif spl[0] == "!who":
                s.sendall('WHO\n'.encode('utf-8'))
            elif inp[0] == "@":
                user = spl[0][1:]
                msg = " ".join(spl[1:])
                s.sendall(("SEND " + user + " " + msg + "\n").encode('utf-8'))
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
            print("User is not online.")
        elif spl[0] == "DELIVERY":
            print("Received msg from " + spl[1] + ": ", " ".join(spl[2:]))
        elif spl[0] == "BAD-RQST-HDR":
            print("Unknown command.")
        elif spl[0] == "BAD-RQST-BODY":
            print("Bad parameters")
        else:
            print("Unknown error")


if __name__ == '__main__':
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.connect(('18.195.107.195', 5378))

    if connect():
        hearT = threading.Thread(target=hear)
        hearT.setDaemon(True)
        hearT.start()
        runT = threading.Thread(target=run)
        runT.setDaemon(True)
        runT.start()

        while True and not Quit:
            pass
    else:
        s.close()