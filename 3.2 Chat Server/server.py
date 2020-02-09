import socket
import threading

clients = []


def send(conn, msg):
    try:
        print("OUT: ", msg)
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
            return data.decode("utf-8")
    except socket.error:
        return False


def hear(client):
    while True:
        disconnect = False
        res = receive(client[0], 4096)
        if res:
            print("IN:  ", res[:-1])
            spl = res.split()
            if spl[0] == "HELLO-FROM":
                if len(spl) < 2:
                    if not send(client[0], "BAD-RQST-BODY\n"):
                        disconnect = True
                elif len(clients) >= 64:
                    send(client[0], 'BUSY\n')
                    print('BUSY')
                    disconnect = True
                elif not any(x for x in clients if x[2] == spl[1]):
                    i = clients.index(client)
                    client[2] = spl[1]
                    clients[i] = client
                    if not send(client[0], 'HELLO ' + spl[1] + '\n'):
                        disconnect = True
                else:
                    send(client[0], 'IN-USE\n')
                    print('IN-USE')
                    disconnect = True
            elif spl[0] == "WHO":
                who = []
                for x in clients:
                    who.append(x[2])
                if not send(client[0], "WHO-OK " + ",".join(who) + "\n"):
                    disconnect = True
            elif spl[0] == "SEND":
                if len(spl) < 3:
                    if not send(client[0], "BAD-RQST-BODY\n"):
                        disconnect = True
                elif any(x for x in clients if x[2] == spl[1]):
                    if spl[1] == "echobot":
                        conn = client[0]
                        if send(client[0], "SEND-OK\n"):
                            if not send(conn, "DELIVERY echobot " + " ".join(spl[2:]) + "\n"):
                                disconnect = True
                        else:
                            disconnect = True
                    else:
                        conn = [x for x in clients if x[2] == spl[1]][0][0]
                        if send(conn, "DELIVERY " + client[2] + " " + " ".join(spl[2:]) + "\n"):
                            if not send(client[0], "SEND-OK\n"):
                                disconnect = True
                        else:
                            disconnect = True
                else:
                    if not send(client[0], "UNKNOWN\n"):
                        disconnect = True
            else:
                if not send(client[0], "BAD-RQST-HDR\n"):
                    disconnect = True
        else:
            print("Disconnecting ", client[2], "...\n")
            disconnect = True
        if disconnect:
            clients.remove(client)
            client[0].close()
            break


def connect():
    while True:
        conn, addr = s.accept()
        clients.append([conn, addr, ""])

        print("IN:  ", addr)
        hearT = threading.Thread(target=hear, args=([[conn, addr, ""]]))
        hearT.setDaemon(True)
        hearT.start()


if __name__ == '__main__':
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.bind(('localhost', 65432))
    s.listen()

    clients.append(["", "", "echobot"])

    connectT = threading.Thread(target=connect)
    connectT.setDaemon(True)
    connectT.start()

    while True:
        pass
