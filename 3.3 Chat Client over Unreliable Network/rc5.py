import math


def rotate_left(a, n, w=16):
    a &= (2 ** w - 1)
    n %= w
    return ((a << n) | (a >> (w - n))) & (2 ** w - 1)


def rotate_right(a, n, w=16):
    n %= w
    a &= (2 ** w - 1)
    return ((a >> n) | (a << (w - n))) & (2 ** w - 1)


def sha1(msg):
    MAX32 = (1 << 32) - 1
    h0 = 0x67452301
    h1 = 0xEFCDAB89
    h2 = 0x98BADCFE
    h3 = 0x10325476
    h4 = 0xC3D2E1F0

    # preprocessing
    l = len(msg)
    msg += b'\x80'
    msg += b'\x00' * (56 - (len(msg) % 56))
    msg += l.to_bytes(8, 'big')

    # for each chunk
    for j in range(0, len(msg), 64):
        chunk = msg[j: j + 64]
        w = [0] * 80
        for i in range(16):
            w[i] = int.from_bytes(chunk[4 * i: 4 * (i + 1)], 'big')

        for i in range(16, 80):
            w[i] = rotate_left(w[i - 3] ^ w[i-8] ^ w[i-14] ^ w[i-16], 1, 32)

        a = h0
        b = h1
        c = h2
        d = h3
        e = h4

        for i in range(80):
            if i < 20:
                f = (b & c) | ((~b) & d)
                k = 0x5A827999
            elif i < 40:
                f = b ^ c ^ d
                k = 0x6ED9EBA1
            elif i < 60:
                f = (b & c) | (b & d) | (c & d)
                k = 0x8F1BBCDC
            else:
                f = b ^ c ^ d
                k = 0xCA62C1D6

            temp = (rotate_left(a, 5, 32) + f + e + k + w[i]) & MAX32
            e = d
            d = c
            c = rotate_left(b, 30, 32)
            b = a
            a = temp

        h0 = (h0 + a) & MAX32
        h1 = (h1 + b) & MAX32
        h2 = (h2 + c) & MAX32
        h3 = (h3 + d) & MAX32
        h4 = (h4 + e) & MAX32

    return h0.to_bytes(4, 'big') + h1.to_bytes(4, 'big') + h2.to_bytes(4, 'big') + h3.to_bytes(4, 'big') + h4.to_bytes(4, 'big')


def sha256(msg):
    MAX32 = (1 << 32) - 1

    h0 = 0x6a09e667
    h1 = 0xbb67ae85
    h2 = 0x3c6ef372
    h3 = 0xa54ff53a
    h4 = 0x510e527f
    h5 = 0x9b05688c
    h6 = 0x1f83d9ab
    h7 = 0x5be0cd19

    k = [0x428a2f98, 0x71374491, 0xb5c0fbcf, 0xe9b5dba5, 0x3956c25b, 0x59f111f1, 0x923f82a4, 0xab1c5ed5,
         0xd807aa98, 0x12835b01, 0x243185be, 0x550c7dc3, 0x72be5d74, 0x80deb1fe, 0x9bdc06a7, 0xc19bf174,
         0xe49b69c1, 0xefbe4786, 0x0fc19dc6, 0x240ca1cc, 0x2de92c6f, 0x4a7484aa, 0x5cb0a9dc, 0x76f988da,
         0x983e5152, 0xa831c66d, 0xb00327c8, 0xbf597fc7, 0xc6e00bf3, 0xd5a79147, 0x06ca6351, 0x14292967,
         0x27b70a85, 0x2e1b2138, 0x4d2c6dfc, 0x53380d13, 0x650a7354, 0x766a0abb, 0x81c2c92e, 0x92722c85,
         0xa2bfe8a1, 0xa81a664b, 0xc24b8b70, 0xc76c51a3, 0xd192e819, 0xd6990624, 0xf40e3585, 0x106aa070,
         0x19a4c116, 0x1e376c08, 0x2748774c, 0x34b0bcb5, 0x391c0cb3, 0x4ed8aa4a, 0x5b9cca4f, 0x682e6ff3,
         0x748f82ee, 0x78a5636f, 0x84c87814, 0x8cc70208, 0x90befffa, 0xa4506ceb, 0xbef9a3f7, 0xc67178f2]

    # preprocessing
    l = len(msg)
    msg += b'\x80'
    msg += b'\x00' * (56 - (len(msg) % 56))
    msg += l.to_bytes(8, 'big')

    # for each chunk
    for j in range(0, len(msg), 64):
        chunk = msg[j: j + 64]

        w = [0] * 80
        for i in range(16):
            w[i] = int.from_bytes(chunk[4 * i: 4 * (i + 1)], 'big')

        for i in range(16, 64):
            s0 = rotate_right(w[i - 15], 7, 32) ^ rotate_right(w[i - 15], 18, 32) ^ (w[i - 15] >> 3)
            s1 = rotate_right(w[i - 2], 17, 32) ^ rotate_right(w[i - 2], 19, 32) ^ (w[i - 2] >> 10)
            w[i] = (w[i - 16] + s0 + w[i - 7] + s1) & MAX32

        a = h0
        b = h1
        c = h2
        d = h3
        e = h4
        f = h5
        g = h6
        h = h7

        for i in range(64):
            S1 = rotate_right(e, 6, 32) ^ rotate_right(e, 11, 32) ^ rotate_right(e, 25, 32)
            ch = (e & f) ^ ((~e) & g)
            temp1 = (h + S1 + ch + k[i] + w[i]) & MAX32
            S0 = rotate_right(a, 2, 32) ^ rotate_right(a, 13, 32) ^ rotate_right(a, 22, 32)
            maj = (a & b) ^ (a & c) ^ (b & c)
            temp2 = (S0 + maj) & MAX32

            h = g
            g = f
            f = e
            e = (d + temp1) & MAX32
            d = c
            c = b
            b = a
            a = (temp1 + temp2) & MAX32

        h0 = (h0 + a) & MAX32
        h1 = (h1 + b) & MAX32
        h2 = (h2 + c) & MAX32
        h3 = (h3 + d) & MAX32
        h4 = (h4 + e) & MAX32
        h5 = (h5 + f) & MAX32
        h6 = (h6 + g) & MAX32
        h7 = (h7 + h) & MAX32

    return h0.to_bytes(4, 'big') + h1.to_bytes(4, 'big') + h2.to_bytes(4, 'big') + h3.to_bytes(4, 'big') + \
           h4.to_bytes(4, 'big') + h5.to_bytes(4, 'big') + h6.to_bytes(4, 'big') + h7.to_bytes(4, 'big')


def xor(a, b):
    if len(a) < len(b):
        a, b = b, a
    res = list(a)
    for i, x in enumerate(b):
        res[i] ^= x

    return bytes(res)


def pbkdf2(func, password, salt=None, n_iterations=256):
    if salt is None:
        salt = b'1' * len(password)
    for _ in range(n_iterations):
        password = func(xor(password, salt))
    return password


class rc5:
    def __init__(self, key, n_rounds=20):
        # The key, considered as an array of bytes
        self.K = key

        # key schedule
        self.S = []

        # The number of rounds to use when encrypting data.
        self.r = n_rounds

        # fill key schedule
        self.get_key()

    def get_key(self):
        # The length of the key in words (or 1, if b=0)
        c = math.ceil(max(len(self.K), 1) / 2)
        # A temporary working array used during key scheduling. initialized to the key in words.
        L = [0] * c
        # The number of round subkeys required.
        t = 2 * (self.r + 1)
        # The round subkey words.
        self.S = [0] * t

        # L key in words
        for i in range(c - 1, -1, -1):
            L[i] = self.K[i * 2] + (self.K[i * 2 - 1] << 8)

        # self.S subkey array
        self.S[0] = 0xB7E1
        for i in range(1, t):
            self.S[i] = self.S[i - 1] + 0x9E37

        i = j = A = B = 0
        for x in range(3 * max(t, c)):
            A = self.S[i] = rotate_left(self.S[i] + A + B, 3)
            B = L[j] = rotate_left(L[j] + A + B, A + B)
            i = (i + 1) % t
            j = (j + 1) % c

    def encrypt(self, A, B, w=16):
        A = (A + self.S[0]) % (1 << w)
        B = (B + self.S[1]) % (1 << w)
        for i in range(1, self.r + 1):
            A = rotate_left(A ^ B, B) + self.S[2 * i]
            B = rotate_left(B ^ A, A) + self.S[2 * i + 1]

        return A % (1 << w), B % (1 << w)

    def decrypt(self, A, B, w=16):
        for i in range(self.r, 0, -1):
            B = rotate_right(B - self.S[2 * i + 1], A) ^ A
            A = rotate_right(A - self.S[2 * i], B) ^ B

        B = (B - self.S[1]) % (1 << w)
        A = (A - self.S[0]) % (1 << w)

        return A, B


    def encrypt_msg(self, msg):
        msg = msg.encode()
        padding = (4 - len(msg) % 4)
        msg += bytes([padding]) * padding

        enc = b''
        for i in range(0, len(msg), 4):
            A = int.from_bytes(msg[i: i + 2], 'big')
            B = int.from_bytes(msg[i + 2: i + 4], 'big')
            A, B = self.encrypt(A, B)
            enc += A.to_bytes(2, 'big')
            enc += B.to_bytes(2, 'big')
        return bytes(enc)


    def decrypt_msg(self, msg):
        enc = []
        for i in range(0, len(msg), 4):
            A = int.from_bytes(msg[i: i + 2], 'big')
            B = int.from_bytes(msg[i + 2: i + 4], 'big')
            A, B = self.decrypt(A, B)
            enc += A.to_bytes(2, 'big')
            enc += B.to_bytes(2, 'big')

        enc = bytes(enc)
        return enc[:-enc[-1]].decode('utf8')


if __name__ == "__main__":
    r = rc5([0x91, 0x5F, 0x46, 0x19, 0xBE, 0x41, 0xB2, 0x51, 0x63, 0x55, 0xA5, 0x01, 0x10, 0xA9, 0xCE, 0x91])
    # A, B = rc5.encrypt("h".encode()[0], 0)
    # print("")
    # A, B = rc5.decrypt(A, B)
    # print(chr(A), chr(B))

