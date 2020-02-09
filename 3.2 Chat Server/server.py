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
        res = receive(client[0], 4096)
        if res:
            print("IN:  ", res[:-1])
            spl = res.split()
            if spl[0] == "HELLO-FROM":
                if len(spl) < 2:
                    if not send(client[0], "BAD-RQST-BODY\n"):
                        clients.remove(client)
                        client[0].close()
                        break
                elif len(clients) >= 64:
                    send(client[0], 'BUSY\n')
                    print('BUSY')
                    clients.remove(client)
                    client[0].close()
                    break
                elif not any(x for x in clients if x[2] == spl[1]):
                    i = clients.index(client)
                    client[2] = spl[1]
                    clients[i] = client
                    if not send(client[0], 'HELLO ' + spl[1] + '\n'):
                        clients.remove(client)
                        client[0].close()
                        break
                else:
                    send(client[0], 'IN-USE\n')
                    print('IN-USE')
                    clients.remove(client)
                    client[0].close()
                    break
            elif spl[0] == "WHO":
                who = []
                for x in clients:
                    who.append(x[2])
                if not send(client[0], "WHO-OK " + ",".join(who) + "\n"):
                    clients.remove(client)
                    client[0].close()
                    break
            elif spl[0] == "SEND":
                if len(spl) < 3:
                    if not send(client[0], "BAD-RQST-BODY\n"):
                        clients.remove(client)
                        client[0].close()
                        break
                elif any(x for x in clients if x[2] == spl[1]):
                    conn = [x for x in clients if x[2] == spl[1]][0][0]
                    if send(conn, "DELIVERY " + client[2] + " " + " ".join(spl[2:]) + "\n"):
                        if not send(client[0], "SEND-OK\n"):
                            clients.remove(client)
                            client[0].close()
                            break
                    else:
                        clients.remove(client)
                        client[0].close()
                        break
                else:
                    if not send(client[0], "UNKNOWN\n"):
                        clients.remove(client)
                        client[0].close()
                        break
            else:
                if not send(client[0], "BAD-RQST-HDR\n"):
                    clients.remove(client)
                    client[0].close()
                    break
        else:
            print("Disconnecting ", client[2], "...\n")
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
    s.bind(('192.168.2.13', 65432))
    s.listen()

    connectT = threading.Thread(target=connect)
    connectT.setDaemon(True)
    connectT.start()

    while True:
        pass
