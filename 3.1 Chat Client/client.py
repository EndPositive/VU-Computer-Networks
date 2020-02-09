import socket
import threading

class ChatClient:
    def __init__(self):
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

        self.pushThread = threading.Thread(target=self.push)
        self.pushThread.setDaemon(True)

        self.pullThread = threading.Thread(target=self.pull)
        self.pullThread.setDaemon(True)

        self.Quit = False
        self.Received = False

    def start(self):
        self.socket.connect(('18.195.107.195', 5378))
        if self.connect():
            self.pushThread.start()
            self.pullThread.start()
        else:
            self.close()

    def send(self, msg):
        try:
            self.socket.sendall(msg.encode('utf-8'))
            return True
        except socket.error:
            return False

    def receive(self, size):
        try:
            data = self.socket.recv(size)
            if not data:
                return False
            else:
                return data.decode("utf-8")
        except socket.error:
            return False

    def connect(self):
        print("Username:")
        name = input()
        if name:
            if self.send('HELLO-FROM ' + name + '\n'):
                res = self.receive(4096)
                if res:
                    spl = res.split()
                    if spl[0] == "IN-USE":
                        print("Username already in use.")
                        return self.connect()
                    elif spl[0] == "BUSY":
                        print("Server is busy.")
                    elif spl[0] == "HELLO":
                        print("Connected.")
                        return True
                else:
                    print("Something went wrong.")
        else:
            return self.connect()
        print("Disconnecting from host...")
        return False

    def push(self):
        while True:
            print("\nCommand:")
            inp = input()
            if inp:
                spl = inp.split()
                if spl[0] == "!quit":
                    self.Quit = True
                elif spl[0] == "!who":
                    if not self.send('WHO\n'):
                        print("Something went wrong.\nDisconnecting from host...")
                        self.Quit = True
                elif inp[0] == "@":
                    user = spl[0][1:]
                    msg = " ".join(spl[1:])
                    if not self.send("SEND " + user + " " + msg + "\n"):
                        print("Something went wrong.\nDisconnecting from host...")
                        self.Quit = True
                else:
                    self.Received = True
                    print("Unknown command")

                if self.Quit:
                    break

                while True and not self.Received:
                    pass
                self.Received = False

    def pull(self):
        while True:
            res = self.receive(4096)
            if res:
                spl = res.split()
                if spl[0] == "WHO-OK":
                    print("Online users: ", ",".join(spl[1:]))
                elif spl[0] == "SEND-OK":
                    print("Message successfully sent.")
                elif spl[0] == "UNKNOWN":
                    print("User is not online.")
                elif spl[0] == "DELIVERY":
                    print('\x1b[1A' + '\x1b[2K' + '\x1b[1A')
                    print("Received msg from " + spl[1] + ": ", " ".join(spl[2:]))
                elif spl[0] == "BAD-RQST-HDR":
                    print("Unknown command.")
                elif spl[0] == "BAD-RQST-BODY":
                    print("Bad parameters")
                else:
                    print("Unknown error")

                if not spl[0] == "DELIVERY":
                    self.Received = True
            else:
                print("Something went wrong, disconnected from host.")
                self.Quit = True

            if self.Quit:
                break

    def close(self, code=0):
        self.socket.close()
        exit(code)

if __name__ == '__main__':
    chatClient = ChatClient()
    chatClient.start()
    while True and not chatClient.Quit:
        pass
