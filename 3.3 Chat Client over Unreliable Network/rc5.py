import math


def rotate_left(a, n, w=16):
    a &= (2 ** w - 1)
    n %= w
    return ((a << n) | (a >> (w - n))) & (2 ** w - 1)


def rotate_right(a, n, w=16):
    n %= w
    a &= (2 ** w - 1)
    return ((a >> n) | (a << (w - n))) & (2 ** w - 1)


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
        print(A, B)
        A = (A + self.S[0]) % (1 << w)
        B = (B + self.S[1]) % (1 << w)
        for i in range(1, self.r + 1):
            A = rotate_left(A ^ B, B) + self.S[2 * i]
            B = rotate_left(B ^ A, A) + self.S[2 * i + 1]
            print(A, B)

        return A, B

    def decrypt(self, A, B, w=16):
        print(A, B)
        for i in range(self.r, 0, -1):
            B = rotate_right(B - self.S[2 * i + 1], A) ^ A
            A = rotate_right(A - self.S[2 * i], B) ^ B
            print(A, B)

        B = (B - self.S[1]) % (1 << w)
        A = (A - self.S[0]) % (1 << w)
        print(A, B)

        return A, B


if __name__ == "__main__":
    rc5 = rc5([0x91, 0x5F, 0x46, 0x19, 0xBE, 0x41, 0xB2, 0x51, 0x63, 0x55, 0xA5, 0x01, 0x10, 0xA9, 0xCE, 0x91])
    A, B = rc5.encrypt("h".encode()[0], "e".encode()[0])
    print("")
    A, B = rc5.decrypt(A, B)
    print(chr(A), chr(B))

