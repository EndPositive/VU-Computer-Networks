import pickle
import time
import socket
import threading
import os
from copy import deepcopy as cp

'''
self.rr['google.com'] = [list of answers]
self.rtt['google.com'] = time to google.com
'''
class Cache:
    def __init__(self, server_file='nl.txt'):
        with open(server_file, 'r') as f:
            self.servers = f.read().split('\n')

        self.rtt = {}
        self.rr = {}
        self.cache_file = 'cache.pickle'

        with open(self.cache_file, 'w+'):
            pass

        # variables for rtt_thread
        self.done = {}
        self.threads = []

        # start the update threads
        rr_thread = threading.Thread(target=self.update_rr_thread)
        rr_thread.daemon = True
        rr_thread.start()

        rtt_thread = threading.Thread(target=self.update_rtt_thread)
        rtt_thread.daemon = True
        rtt_thread.start()

        # sleep to allow the threads to make some requests to the servers
        time.sleep(0.5)


    def update_rr(self):
        to_delete = []
        for record in self.rr:
            if self.rr[record][0] < time.time():
                to_delete.append(record)

        for record in to_delete:
            del self.rr[record]

        with open(self.cache_file, 'wb') as f:
            pickle.dump(self.rr, f)

    def update_rr_thread(self, timeout=60):
        while True:
            self.update_rr()
            time.sleep(timeout)

    def update_rtt(self):
        for ip in self.servers:
            if ip not in self.done:
                self.done[ip] = True
            if self.done[ip]:
                self.done[ip] = False
                t = threading.Thread(target=self.ping, args=(ip,))
                t.daemon = True
                t.start()
                self.threads.append([t, ip])

        alive = []
        for t in self.threads:
            t[0].join(0.1)
            if not t[0].is_alive():
                self.done[t[1]] = True
            else:
                alive.append(t)
        self.threads = alive

    def update_rtt_thread(self, timeout=10):
        while True:
            self.update_rtt()
            time.sleep(timeout)

    def get_best_servers(self, n=1):
        if n < 1:
            return []
        if n == 1:
            minimum = 100000000
            ans = ''
            for ip in self.rtt:
                if self.rtt[ip] < minimum:
                    minimum = self.rtt[ip]
                    ans = ip
            return [ans]

        l = list(zip(self.rtt.keys(), self.rtt.values()))
        l.sort(key=lambda x: x[1])
        return [x[0] for x in l[:min(n, len(l))]]

    def ping(self, ip):
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            start_time = time.time()
            s.connect((ip, 53))
            # send random query
            msg = b"\xb1\xed\x01\x00\x00\x01\x00\x00\x00\x00\x00\x00\x06\x64\x69\x73\x71\x75\x73\x03\x63\x6f\x6d\x00\x00\x01\x00\x01"
            s.sendall(int.to_bytes(len(msg), 2, 'big') + msg)
            data = s.recv(1024)
            frame_size = int.from_bytes(data[:2], 'big')
            data = data[2:]
            while len(data) < frame_size:
                data += s.recv(1024)
            self.rtt[ip] = time.time() - start_time
        except:
            self.rtt[ip] = 100000000

    def fetch_record(self, name):
        if tuple(name) not in self.rr:
            return
        to_ret = []
        to_del = []
        # iterate over records
        for i, record in enumerate(self.rr[tuple(name)]):
            # check ttl
            ttl = record['ttl'] - time.time()
            if ttl < 0:
                to_del.append(i)
                continue
            # copy and set the new ttl
            curr_record = cp(record)
            curr_record['ttl'] = ttl
            to_ret.append(curr_record)

        # delete expired records
        for i in reversed(to_del):
            del self.rr[tuple(name)][i]
        return to_ret

    def add_record(self, addr):
        addr['ttl'] += time.time()
        record = tuple(addr['name'])
        if record not in self.rr:
            self.rr[record] = []
        self.rr[record].append(addr)

if __name__ == '__main__':
    c = Cache()
