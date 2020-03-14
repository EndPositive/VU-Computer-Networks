import pickle
from file_manager import File


class Torrent:
    def __init__(self, _path, piece_size=1000, _hash=None, _id=0, _pieces=None):
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

    def add_piece(self, piece_number):
        self.pieces.add(piece_number)

def save_torrents(torrent_list, file_name='config'):
    with open(file_name, 'wb') as f:
        pickle.dump(torrent_list, f)

def load_torrents(file_name='config'):
    with open(file_name, 'rb') as f:
        torrents = pickle.load(f)

    return torrents
