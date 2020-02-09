import socket
import threading
import time

Quit = False


def send(msg):
    try:
        s.sendall(msg.encode('utf-8'))
        return True
    except socket.error:
        return False


def receive(size):
    try:
        data = s.recv(size)
        if not data:
            return False
        else:
            return data.decode("utf-8")
    except socket.error:
        return False


def connect():
    print("Username:")
    name = input()
    if name:
        if send('HELLO-FROM ' + name + '\n'):
            res = receive(4096)
            if res:
                spl = res.split()
                if spl[0] == "IN-USE":
                    print("Username already in use.")
                    return connect()
                elif spl[0] == "BUSY":
                    print("Server is busy.")
                elif spl[0] == "HELLO":
                    print("Connected.")
                    return True
            else:
                print("Something went wrong.")
    else:
        return connect()
    print("Disconnecting from host...")
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
                if not send('WHO\n'):
                    print("Something went wrong.\nDisconnecting from host...")
                    Quit = True
            elif inp[0] == "@":
                user = spl[0][1:]
                msg = " ".join(spl[1:])
                if not send("SEND " + user + " " + msg + "\n"):
                    print("Something went wrong.\nDisconnecting from host...")
                    Quit = True
            else:
                print("Unknown command")
            time.sleep(.2)


def hear():
    global Quit
    while True:
        res = receive(4096)
        if res:
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
        else:
            print("Something went wrong, disconnected from host.")
            Quit = True


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
    s.close()
