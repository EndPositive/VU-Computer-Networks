import pickle
from file_manager import File
from hashlib import md5
from threading import Lock
from os.path import basename, splitext, getsize, exists


class Torrent:
    def __init__(self, _path, _piece_size=1000, _id=0, _hash=None, _pieces=None, _server=('80.112.140.14', 65400), _file_size=None):
        self.file = File(_path, _piece_size)
        self.piece_size = _piece_size

        if _hash is None:
            self.hash = self.file.hash_file()
        else:
            self.hash = _hash

        self.id = _id

        if _pieces is None:
            self.pieces = set()
        else:
            self.pieces = _pieces

        self.server = _server
        self.file_size = _file_size
        if self.file_size is None:
            self.file_size = getsize(self.file.path)

        self.__curr_piece = 0

    def allocate_space(self, byte_cnt):
        self.file_size = byte_cnt
        self.file.allocate_space(byte_cnt)

    def add_piece(self, piece_number, data=None):
        if piece_number not in self.pieces and data is not None and len(data):
            self.pieces.add(piece_number)
            self.file.write_piece(piece_number, data)

    def get_piece(self, piece_number):
        if piece_number in self.pieces:
            x = self.file.read_piece(piece_number)
            return x
        return b''

    def get_piece_no(self):
        if len(self.pieces) >= self.get_n_pieces():
            return -1
        n_pieces = self.get_n_pieces()
        if n_pieces is not None:
            while self.__curr_piece in self.pieces:
                self.__curr_piece = (self.__curr_piece + 1) % n_pieces
            to_ret = self.__curr_piece
            self.__curr_piece = (self.__curr_piece + 1) % n_pieces
            return to_ret

        # here, n_pieces is None which means file size not set
        # this can happen when the torrent isn't loaded from a file
        # and there hasn't been space allocated for the file that's being seeded either
        # this should not happen though
        # for the sake of it, we will return the first piece that isn't in the set (not safe)
        i = 0
        while i not in self.pieces:
            i += 1
        return i

    def get_n_pieces(self):
        if self.file_size % self.piece_size == 0:
            return self.file_size // self.piece_size
        else:
            return self.file_size // self.piece_size + 1

    def hash_piece(self, piece_number, function=md5):
        return self.file.hash_piece(piece_number, function)

    def close(self):
        self.file.close()

    def open(self):
        self.file.open()

class TorrentFile:
    @staticmethod
    def load(path=None, obj=None, overwrite=False):
        if path is None and obj is None:
            return

        if path is not None:
            with open(path, 'rb') as fp:
                obj = pickle.load(fp)

        file_name = obj['file_name']
        server = obj['server']
        piece_size = obj['piece_size']
        file_size = obj['file_size']
        hash_val = obj['hash']

        t = None
        if exists(file_name):
            f = File(file_name)
            # if a file with the same hash as the torrent exists, it means that we already have it downloaded
            if f.hash_file() == hash_val:
                t = Torrent(
                    _path=file_name,
                    _piece_size=piece_size,
                    _hash=hash_val,
                    _server=server,
                    _file_size=file_size
                )
                # since we have the file, mark all pieces as already existing
                t.pieces = {i for i in range(t.get_n_pieces())}
                f.close()
            elif not overwrite:
                f.close()
                return None

        if t is None:
            return Torrent(
                _path=file_name,
                _piece_size=piece_size,
                _hash=hash_val,
                _server=server,
                _file_size=file_size
            )

        return t

    @staticmethod
    def dump(obj, path=None):
        obj = {
            'file_name': basename(obj.file.path),
            'server': obj.server,
            'piece_size': obj.piece_size,
            'file_size': obj.file_size,
            'hash': obj.hash
        }

        if path is None:
            return obj

        path = splitext(path)[0] + ".torr"

        with open(path, 'wb') as fp:
            pickle.dump(obj, fp)

        return path


def save_torrents(torrent_list, file_name='config'):
    to_dump = []
    for t in torrent_list:
        to_dump.append(TorrentFile.dump(t))
    with open(file_name, 'wb') as f:
        pickle.dump(to_dump, f)


def load_torrents(file_name='config'):
    try:
        with open(file_name, 'rb') as f:
            torrents = pickle.load(f)

        loaded = []
        for t in torrents:
            loaded.append(TorrentFile.load(obj=t, overwrite=True))
        return loaded
    except FileNotFoundError:
        return []
