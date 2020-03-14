class File:
    def __init__(self, path, piece_size=1000000):
        self.path = path
        self.piece_size = piece_size

        # try to open the file and create it if it doesn't exist
        try:
            self.f = open(self.path, 'r+b')
        except FileNotFoundError:
            f = open(self.path, 'w')
            f.close()
            self.f = open(self.path, 'r+b')

    def allocate_space(self, byte_cnt):
        self.f.seek(byte_cnt - 1)
        self.f.write(b'\x00')

    def read_piece(self, piece_number):
        self.f.seek(piece_number * self.piece_size)
        return self.f.read(self.piece_size)

    def write_piece(self, piece_number, data):
        self.f.seek(piece_number * self.piece_size)
        return self.f.write(data)

    def close(self):
        self.f.close()
