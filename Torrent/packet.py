class MalformedFrameError(Exception):
    def __init__(self, expression=None, message=None):
        self.expression = expression
        self.message = message


class Packet:
    def __init__(self, data=None):
        self.type = None
        self.hash = b'\x00' * 16
        self.seeders = []
        self.err = None
        self.piece_no = None
        self.data = None

        if data is None:
            return

        if len(data) < 17:
            print("Incorrect length", len(data), data)
            raise MalformedFrameError()

        self.type = data[0]
        self.hash = data[1:17]

        index = 17
        # parse request list of seeders
        if self.type == 3:
            self.seeders = []
            while len(data) >= index + 6:
                self.seeders.append((data[index: index + 4], data[index + 4: index + 6]))
                index += 6
        elif self.type == 5:
            self.err = int.from_bytes(data[index:], 'big')
        elif self.type == 6:
            if len(data) < index + 4:
                print("Something with req download")
                raise MalformedFrameError()
            self.piece_no = int.from_bytes(data[index: index + 4], 'big')
        elif self.type == 7:
            if len(data) < index + 4:
                print("Something with recv download")
                raise MalformedFrameError()
            self.piece_no = int.from_bytes(data[index: index + 4], 'big')
            if len(self.data) == 0:
                print("Something with no data in download")
                raise MalformedFrameError()
            self.data = data[index + 4:]

    def to_bytes(self):
        data = b''
        data += self.type.to_bytes(1, 'big')
        data += self.hash

        if self.type == 3:
            for seeder in self.seeders:
                data += seeder[0]
                data += seeder[1]
        elif self.type == 5:
            data += self.err.to_bytes(1, 'big')
        elif self.type == 6:
            data += self.piece_no.to_bytes(4, 'big')
        elif self.type == 7:
            data += self.piece_no.to_bytes(4, 'big')
            data += self.data

        return data
