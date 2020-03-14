from util import addr_to_bytes, addr_from_bytes

class MalformedFrameError(Exception):
    def __init__(self, expression=None, message=None):
        self.expression = expression
        self.message = message


class Packet:
    def __init__(self, data=None, verbose=False):
        self.verbose = verbose

        self.type = None
        self.hash = b'\x00' * 16
        self.seeders = []
        self.err = None
        self.piece_no = None
        self.data = None

        if data is None:
            return

        if len(data) < 17:
            if self.verbose:
                print("Incorrect length", len(data), data)
            raise MalformedFrameError()

        self.type = data[0]
        self.hash = data[1:17]

        index = 17
        # parse request list of seeders
        if self.type == 3:
            self.seeders = []
            while len(data) >= index + 6:
                self.seeders.append(addr_from_bytes(data[index: index + 6]))
                index += 6
        elif self.type == 5:
            self.err = int.from_bytes(data[index:], 'big')
        elif self.type == 6:
            if len(data) < index + 4:
                if self.verbose:
                    print("Something with req download")
                raise MalformedFrameError()
            self.piece_no = int.from_bytes(data[index: index + 4], 'big')
        elif self.type == 7:
            if len(data) < index + 4:
                if self.verbose:
                    print("Something with recv download")
                raise MalformedFrameError()
            self.piece_no = int.from_bytes(data[index: index + 4], 'big')
            self.data = data[index + 4:]
            if len(self.data) == 0:
                if self.verbose:
                    print("Something with no data in download")
                raise MalformedFrameError()
        elif self.type == 8 or self.type == 9:
            if len(data) < index + 6:
                if self.verbose:
                    print("No data in the punch packet")
                raise MalformedFrameError
            self.seeders.append(addr_from_bytes(data[index: index + 6]))

    def to_bytes(self):
        data = b''
        data += self.type.to_bytes(1, 'big')
        data += self.hash

        if self.type == 3:
            for seeder in self.seeders:
                data += addr_to_bytes(seeder)
        elif self.type == 5:
            data += self.err.to_bytes(1, 'big')
        elif self.type == 6:
            data += self.piece_no.to_bytes(4, 'big')
        elif self.type == 7:
            data += self.piece_no.to_bytes(4, 'big')
            data += self.data
        elif self.type == 8 or self.type == 9:
            data += addr_to_bytes(self.seeders[0])

        return data
