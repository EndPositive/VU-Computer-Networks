from hashlib import md5


class File:
    def __init__(self, path, piece_size=1000):
        self.path = path
        self.piece_size = piece_size

        # try to open the file and create it if it doesn't exist
        self.f = None
        try:
            self.open()
        except FileNotFoundError:
            f = open(self.path, 'w')
            f.close()
            self.open()

    def open(self):
        self.f = open(self.path, 'r+b')

    def close(self):
        if self.f:
            self.f.close()
        self.f = None

    def allocate_space(self, byte_cnt):
        self.f.seek(byte_cnt - 1)
        self.f.write(b'\x00')

    def read_piece(self, piece_number):
        self.f.seek(piece_number * self.piece_size)
        return self.f.read(self.piece_size)

    def write_piece(self, piece_number, data):
        self.f.seek(piece_number * self.piece_size)
        return self.f.write(data)

    def hash_file(self, max_read_size=1000000, function=md5):
        h = function()
        self.f.seek(0)
        text = self.f.read(max_read_size)
        while text:
            h.update(text)
            text = self.f.read(max_read_size)
        return h.digest()

    def hash_piece(self, piece_number, function=md5):
        h = function()
        self.f.seek(piece_number * self.piece_size)
        h.update(self.f.read(self.piece_size))
        return h.digest()
