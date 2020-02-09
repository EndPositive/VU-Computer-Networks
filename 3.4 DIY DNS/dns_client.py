import socket

if __name__ == '__main__':
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.connect(('192.168.0.1', 53))
    msg = b"\xb1\xed\x01\x00\x00\x01\x00\x00\x00\x00\x00\x00\x06\x64\x69\x73\x71\x75\x73\x03\x63\x6f\x6d\x00\x00\x01\x00\x01"
    s.sendall(int.to_bytes(len(msg), 2, 'big') + msg)
    data = s.recv(1024)
    print(data)
