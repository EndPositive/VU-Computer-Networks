import socket
import threading
import time
from copy import deepcopy as cp
from os import urandom
from cache import Cache
from dns_frame import *


def send(sockfd, data, protocol, addr=None):
    try:
        if protocol == 'UDP':
            if addr is None:
                return False
            else:
                sockfd.sendto(data, addr)
        else:
            sockfd.sendall(len(data).to_bytes(2, 'big') + data)
        return True
    except socket.error:
        return False


class DNSserver:
    def __init__(self, verbose=True, use_multithreading=True):
        if verbose:
            print('[+]Starting server...', flush=True)
        self.udp_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.tcp_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.verbose = verbose
        self.multithreaded = use_multithreading
        self.cache = Cache()

    def start(self, port=53):
        self.udp_socket.bind(('127.0.0.1', port))
        self.tcp_socket.bind(('127.0.0.1', port))

        if self.multithreaded:
            udp_thread = threading.Thread(target=self.udp_listen)
            tcp_thread = threading.Thread(target=self.tcp_listen)
            udp_thread.start()
            tcp_thread.start()
        else:
            self.udp_listen()

    def udp_listen(self):
        if self.verbose:
            print('[+]Started UDP listening thread', flush=True)
        while True:
            data, addr = self.udp_socket.recvfrom(512)
            new_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            if self.multithreaded:
                t = threading.Thread(target=self.handle_conn, args=(new_socket, data, 'UDP', addr))
                t.start()
                time.sleep(0.1)
            else:
                self.handle_conn(new_socket, data, 'UDP', addr)

    def tcp_listen(self):
        if self.verbose:
            print('[+]Started TCP listening thread', flush=True)
        self.tcp_socket.listen()
        while True:
            new_socket, addr = self.tcp_socket.accept()
            if self.multithreaded:
                t = threading.Thread(target=self.handle_conn, args=(new_socket, None, 'TCP', None))
                t.start()
                time.sleep(0.1)
            else:
                self.handle_conn(new_socket, None, 'TCP', addr)

    def handle_conn(self, sockfd, data, protocol, addr=None):
        try:
            # Receive packets with tcp connection
            if protocol == 'TCP':
                data = sockfd.recv(1024)
                data_len = int.from_bytes(data[:2], 'big')
                while len(data) < data_len:
                    data += sockfd.recv(1024)
            query = DNSframe(data)

            if self.verbose:
                print('[+]Received from', addr, flush=True)

            # if it is not a standard query or it is truncated send format err and exit
            if query.qr != 0 or query.opcode != 0 or query.tc != 0:
                if self.verbose:
                    print('[-]Frame is not a query', flush=True)
                response = DNSframe()

                # set id to the one from the request
                response.id = data[:2]

                # set to response
                response.qr = 1

                # set to format error
                response.rcode = 1

                send(sockfd, response.to_bytes(False), protocol, addr)
                return

            # check if the frame contains more than 1 query and remove them if so
            # do this because it makes things simple, and because nobody on the planet implements it
            # WHY IS IT EVEN IN THE SPECIFICATION HONESTLY
            for i in range(1, len(query.queries)):
                del query.queries[i]
            query.qdcount = 1

            # make packet to send from the query
            forward_request = cp(query)

            # set the recursion flags
            forward_request.rd = 1
            forward_request.ra = 1

            # generate random id for the message
            forward_request.id = urandom(2)

            # set answers to [] just in case
            forward_request.ancount = 0
            forward_request.answers = []

            # check for the cached names
            record_cache = self.cache.fetch_record(query.queries[0])
            if record_cache:
                response = DNSframe()
                response.ancount = len(record_cache)
                response.answers = record_cache
            else:
                found_good_server = False

                # try and get the cname of the query if we have it in the cache
                cname = self.cache.get_cname(query.queries[0])
                res = None
                while cname is not None and query.queries[0]['qtype'] != 5:
                    res = cname
                    cname = self.cache.get_cname(cname)
                if res is not None:
                    forward_request.queries[0]['qname'] = res

                if self.verbose:
                    print('[+]Making recursive call', flush=True)
                # for server in self.cache.get_best_servers(15):
                for server in ['8.8.8.8']:
                    try:
                        # open connection to the server and send the request
                        forward_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                        forward_socket.connect((server, 53))
                        forward_socket.sendall(forward_request.to_bytes())

                        if self.verbose:
                            print('[+]Querying ' + server + ' for ' + (b'.'.join(query.queries[0]['qname']).decode('utf8')), flush=True)

                        server_response = forward_socket.recv(1024)
                        server_response_size = int.from_bytes(server_response[:2], 'big')
                        server_response = server_response[2:]
                        while len(server_response) < server_response_size:
                            server_response += forward_socket.recv(1024)
                        forward_socket.close()
                        if self.verbose:
                            print('[+]Recursive response received', flush=True)

                        # parse the response
                        response = DNSframe(server_response)

                        if forward_request.id != response.id:
                            if self.verbose:
                                print('[-]Wrong id received from the name server', flush=True)
                            continue

                        if response.rcode != 0:
                            if self.verbose:
                                print('[-]Received error code from the server: ' + str(response.rcode), flush=True)
                            continue

                        if response.qr != 1:
                            if self.verbose:
                                print('[-]Received query instead of response', flush=True)
                            continue

                        found_good_server = True
                        break
                    except socket.error:
                        print('[-]Failed to reach DNS server', flush=True)
                        forward_socket.close()
                        continue
                    except MalformedFrameError:
                        if self.verbose:
                            print('[-]Uhm...looks like you forgot how to DNS: malformed frame from server', flush=True)
                        continue
                # check if no server was found
                if not found_good_server:
                    if self.verbose:
                        print('[-]No good server found...closing connection', flush=True)
                    response = DNSframe()

                    # set id to the one from the request
                    response.id = query.id

                    # set to response
                    response.qr = 1

                    # set to server failure
                    response.rcode = 2
                    send(sockfd, response.to_bytes(False), protocol, addr)
                    return

                # delete the responses that do not match the type and cache the good ones
                for i in range(len(response.answers) - 1, -1, -1):
                    answer = response.answers[i]
                    if answer['type'] == query.queries[0]['qtype'] or answer['type'] == 5:
                        self.cache.add_record(answer)

                    if answer['type'] != query.queries[0]['qtype']:
                        del response.answers[i]
                        continue

                    # change the name to the one in the query
                    response.answers[i]['name'] = query.queries[0]['qname']

            if self.verbose:
                print('[+]Preparing response', flush=True)

            # set the id to the one that was given in the request
            response.id = query.id

            # set to response just in case
            response.qr = 1

            # set the recursion to true
            response.rd = 1
            response.ra = 1

            # set the number of answers
            response.ancount = len(response.answers)

            if self.verbose:
                print('[+]Sending response', flush=True)
            # send back the response
            send(sockfd, response.to_bytes(False), protocol, addr)

            # close the connection and exit the thread
            if self.verbose:
                print('[+]Connection closed', flush=True)
            return
        except socket.error:
            if self.verbose:
                print('[-]Error while receiving or sending', flush=True)
            return
        except MalformedFrameError:
            if self.verbose:
                print('[-]Frame is malformed. Closing connection...', flush=True, end='')

            response = DNSframe()

            # set id to the one from the request
            response.id = data[:2]

            # set to response
            response.qr = 1

            # set to format error
            response.rcode = 1
            try:
                send(sockfd, response.to_bytes(False), protocol, addr)
            except socket.error:
                if self.verbose:
                    print('[-]Failed to send', flush=True)
            if self.verbose:
                print('done', flush=True)
            return


if __name__ == '__main__':
    dnsserver = DNSserver(verbose=True)
    dnsserver.start(port=53)
