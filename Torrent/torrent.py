import pickle
from file_manager import File
from hashlib import md5
from threading import Lock

mutex = Lock()

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

    def close(self):
        self.file.close()

    def open(self):
        self.file.open()


def save_torrents(torrent_list, file_name='config'):
    mutex.acquire()
    for t in torrent_list:
        t.close()
    with open(file_name, 'wb') as f:
        pickle.dump(torrent_list, f)
    for t in torrent_list:
        t.open()
    mutex.release()


def load_torrents(file_name='config'):
    mutex.acquire()
    try:
        with open(file_name, 'rb') as f:
            torrents = pickle.load(f)

        for t in torrents:
            t.open()

        mutex.release()
        return torrents
    except FileNotFoundError:
        mutex.release()
        return []
