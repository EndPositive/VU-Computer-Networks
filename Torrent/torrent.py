import pickle
from file_manager import File
from hashlib import md5


class Torrent:
    def __init__(self, _path, piece_size=1000, _id=0, _hash=None, _pieces=None):
        self.file = File(_path, piece_size)

        if _hash is None:
            self.hash = self.file.hash_file()
        else:
            self.hash = _hash

        self.id = _id

        if _pieces is None:
            self.pieces = set()
        else:
            self.pieces = _pieces

    def allocate_space(self, byte_cnt):
        self.file.allocate_space(byte_cnt)

    def add_piece(self, piece_number, data=None):
        self.pieces.add(piece_number)
        if data is not None:
            self.file.write_piece(piece_number, data)

    def get_piece(self, piece_number):
        return self.file.read_piece(piece_number)

    def hash_piece(self, piece_number, function=md5):
        return self.file.hash_piece(piece_number, function)


def save_torrents(torrent_list, file_name='config'):
    with open(file_name, 'wb') as f:
        pickle.dump(torrent_list, f)


def load_torrents(file_name='config'):
    try:
        with open(file_name, 'rb') as f:
            torrents = pickle.load(f)

        return torrents
    except FileNotFoundError:
        return []
