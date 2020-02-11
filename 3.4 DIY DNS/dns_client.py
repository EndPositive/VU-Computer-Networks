import socket
from dns_server import DNSframe
from dns_server import MalformedFrameError

if __name__ == '__main__':
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    malformed = b"\xb1\xed\x01\x00\x00\x01\x00\x00\x00\x00\x00\x00\x06\x64\x69\x73\x71\x75\x73\x03\x63\x6f\x6d\x00\x00"
    query = b"\x01\x00\x00\x01\x00\x00\x00\x00\x00\x00\x06\x64\x69\x73\x71\x75\x73\x03\x63\x6f\x6d\x00\x00\x01\x00\x01"
    msg = query
    s.sendto(int.to_bytes(len(msg), 2, 'big') + msg, ("127.0.0.1", 12341))
    data = s.recv(1024)
    print(data)
    try:
        frame = DNSframe(data)
        print(frame.answers)
    except MalformedFrameError:
        print("Problemo")

