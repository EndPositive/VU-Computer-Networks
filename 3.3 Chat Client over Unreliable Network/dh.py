import random
from hashing import pbkdf2
from rc5 import rc5

class DH:
    def __init__(self):
        self.p = 32317006071311007300338913926423828248817941241140239112842009751400741706634354222619689417363569347117901737909704191754605873209195028853758986185622153212175412514901774520270235796078236248884246189477587641105928646099411723245426622522193230540919037680524235519125679715870117001058055877651038861847280257976054903569732561526167081339361799541336476559160368317896729073178384589680639671900977202194168647225871031411336429319536193471636533209717077448227988588565369208645296636077250268955505928362751121174096972998068410554359584866583291642136218231078990999448652468262416972035911852507045361090559
        self.g = 2
        self.l = 256  # exponent bit size

        self.__exponent = self.__get_new_exponent()
        self.__public_info = self.__compute_public_info()
        self.__secret = None
        self.__salt = None
        self.__rc5 = None
        self.password = None


    def __compute_public_info(self):
        return pow(self.g, self.__exponent, self.p)

    def __get_new_exponent(self):
        return random.randrange(2 ** (self.l - 1), 2 ** self.l)

    def __get_password(self):
        self.password = pbkdf2(self.__secret, self.__salt)
        self.__rc5 = rc5(self.password)

    def new_parameters(self):
        self.__exponent = self.__get_new_exponent()
        self.__public_info = self.__compute_public_info()
        self.__get_password()

    def set_secret(self, received):
        if type(received) == bytes:
            received = int.from_bytes(received, 'big')

        self.__secret = pow(received, self.__exponent, self.p)
        self.__get_password()

    def set_salt(self, received):
        self.__salt = received

    def get_public_info(self):
        return self.__public_info.to_bytes(256, 'big')

    def encrypt(self, msg):
        if self.password is None:
            return msg
        return self.__rc5.encrypt_msg(msg)

    def decrypt(self, msg):
        if self.password is None:
            print('wtf')
            return msg
        return self.__rc5.decrypt_msg(msg)

