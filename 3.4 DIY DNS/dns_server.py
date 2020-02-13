import socket
import threading
import time
from copy import deepcopy as cp
from os import urandom
from cache import Cache


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


class MalformedFrameError(Exception):
    def __init__(self, expression=None, message=None):
        self.expression = expression
        self.message = message

class DNSframe:
    def __init__(self, data=None):
        self.id = b''
        self.qr = 0
        self.opcode = 0
        self.aa = 0
        self.tc = 0
        self.rd = 1
        self.ra = 1
        self.rcode = 0
        self.qdcount = 0
        self.ancount = 0
        self.nscount = 0
        self.arcount = 0
        self.queries = []
        self.answers = []
        self.name_servers = []
        self.additional = []

        if data is None:
            return

        if len(data) < 12:
            raise MalformedFrameError()

        # TRANSACTION ID: 2 BYTES
        self.id = data[:2]

        # QR (query(0) / response(1))
        self.qr = data[2] >> 7

        # Opcode (standard query(0) / inverse query(1) / server status request(2)
        self.opcode = (data[2] & 0x78) >> 3

        # Authoritative answer-this bit is valid in responses,
        # and specifies that the responding name server is an
        # authority for the domain name in question section.
        self.aa = (data[2] & 0x4) >> 2

        # Truncation - specifies that this message was truncated
        # due to length greater than that permitted on the transmission channel.
        self.tc = (data[2] & 0x2) >> 1

        # Recursion Desired - this bit may be set in a query and
        # is copied into the response.  If RD is set, it directs
        # the name server to pursue the query recursively.
        self.rd = (data[2] & 0x1)

        # Recursion Available - this be is set or cleared in a
        # response, and denotes whether recursive query support is
        # available in the name server.
        self.ra = data[3] >> 7

        # Response code
        #                 0               No error condition
        #                 1               Format error - The name server was
        #                                 unable to interpret the query.
        #                 2               Server failure - The name server was
        #                                 unable to process this query due to a
        #                                 problem with the name server.
        #                 3               Name Error - Meaningful only for
        #                                 responses from an authoritative name
        #                                 server, this code signifies that the
        #                                 domain name referenced in the query does
        #                                 not exist.
        #                 4               Not Implemented - The name server does
        #                                 not support the requested kind of query.
        #                 5               Refused - The name server refuses to
        #                                 perform the specified operation for
        #                                 policy reasons.  For example, a name
        #                                 server may not wish to provide the
        #                                 information to the particular requester,
        #                                 or a name server may not wish to perform
        #                                 a particular operation (e.g., zone transfer) for particular data.
        self.rcode = data[3] & 0xf

        # QDCOUNT - an unsigned 16 bit integer specifying the number of
        # entries in the question section.
        self.qdcount = int.from_bytes(data[4:6], 'big')

        # ANCOUNT - an unsigned 16 bit integer specifying the number of
        # resource records in the answer section.
        self.ancount = int.from_bytes(data[6:8], 'big')

        # NSCOUNT - an unsigned 16 bit integer specifying the number of name
        # server resource records in the authority records section.
        self.nscount = int.from_bytes(data[8:10], 'big')

        # ARCOUNT - an unsigned 16 bit integer specifying the number of
        # resource records in the additional records section.
        self.arcount = int.from_bytes(data[10:12], 'big')

        # PARSE QUERIES
        self.queries = []
        index = 12
        for i in range(self.qdcount):
            self.queries.append({})
            self.queries[i]['qname'] = []

            # QNAME - a domain name represented as a sequence of labels, where
            # each label consists of a length octet followed by that
            # number of octets.  The domain name terminates with the
            # zero length octet for the null label of the root.  Note
            # that this field may be an odd number of octets; no padding is used.
            if len(data) <= index:
                raise MalformedFrameError()

            index, self.queries[i]['qname'] = DNSframe.parse_name(data, index)

            # QTYPE - a two octet code which specifies the type of the query.
            # The values for this field include all codes valid for a
            # TYPE field, together with some more general codes which
            # can match more than one type of RR.
            if len(data) < index + 2:
                raise MalformedFrameError()
            self.queries[i]['qtype'] = int.from_bytes(data[index:index + 2], 'big')
            index += 2

            # QCLASS - a two octet code which specifies the type of the query.
            # The values for this field include all codes valid for a
            # TYPE field, together with some more general codes which
            # can match more than one type of RR.
            if len(data) < index + 2:
                raise MalformedFrameError()
            self.queries[i]['qclass'] = int.from_bytes(data[index: index + 2], 'big')
            index += 2

        self.answers = []
        if index >= len(data):
            return
        # parse answer resource record
        for i in range(self.ancount):
            self.answers.append({})
            self.answers[i]['name'] = []

            # NAME - a domain name to which this resource record pertains.
            if len(data) < index:
                raise MalformedFrameError()
            index, self.answers[i]['name'] = DNSframe.parse_name(data, index)

            # TYPE - two octets containing one of the RR type codes.  This
            # field specifies the meaning of the data in the RDATA field.
            if len(data) < index + 2:
                raise MalformedFrameError()
            self.answers[i]['type'] = int.from_bytes(data[index:index + 2], 'big')
            index += 2

            # CLASS - two octets which specify the class of the data in the RDATA field.
            self.answers[i]['class'] = int.from_bytes(data[index: index + 2], 'big')
            if len(data) < index + 2:
                raise MalformedFrameError()
            index += 2

            # TTL - a 32 bit unsigned integer that specifies the time
            # interval (in seconds) that the resource record may be
            # cached before it should be discarded.  Zero values are
            # interpreted to mean that the RR can only be used for the
            # transaction in progress, and should not be cached.
            if len(data) < index + 4:
                raise MalformedFrameError()
            self.answers[i]['ttl'] = int.from_bytes(data[index: index + 4], 'big')
            index += 4

            # RDLENGTH - an unsigned 16 bit integer that specifies the length in octets of the RDATA field.
            if len(data) < index + 2:
                raise MalformedFrameError()
            self.answers[i]['rdlength'] = int.from_bytes(data[index: index + 2], 'big')
            index += 2

            # RDATA - a variable length string of octets that describes the
            # resource.  The format of this information varies
            # according to the TYPE and CLASS of the resource record.
            # For example, the if the TYPE is A and the CLASS is IN,
            # the RDATA field is a 4 octet ARPA Internet address.
            if len(data) < index + self.answers[i]['rdlength']:
                raise MalformedFrameError()
            self.answers[i]['rdata'] = data[index: index + self.answers[i]['rdlength']]
            index += self.answers[i]['rdlength']

        self.name_servers = []
        if index >= len(data):
            return
        # parse answer resource record
        for i in range(self.nscount):
            self.name_servers.append({})
            self.name_servers[i]['name'] = []

            # NAME - a domain name to which this resource record pertains.
            if len(data) < index:
                raise MalformedFrameError()
            index, self.name_servers[i]['name'] = DNSframe.parse_name(data, index)

            # TYPE - two octets containing one of the RR type codes.  This
            # field specifies the meaning of the data in the RDATA field.
            if len(data) < index + 2:
                raise MalformedFrameError()
            self.name_servers[i]['type'] = int.from_bytes(data[index:index + 2], 'big')
            index += 2

            # CLASS - two octets which specify the class of the data in the RDATA field.
            self.name_servers[i]['class'] = int.from_bytes(data[index: index + 2], 'big')
            if len(data) < index + 2:
                raise MalformedFrameError()
            index += 2

            # TTL - a 32 bit unsigned integer that specifies the time
            # interval (in seconds) that the resource record may be
            # cached before it should be discarded.  Zero values are
            # interpreted to mean that the RR can only be used for the
            # transaction in progress, and should not be cached.
            if len(data) < index + 4:
                raise MalformedFrameError()
            self.name_servers[i]['ttl'] = int.from_bytes(data[index: index + 4], 'big')
            index += 4

            # RDLENGTH - an unsigned 16 bit integer that specifies the length in octets of the RDATA field.
            if len(data) < index + 2:
                raise MalformedFrameError()
            self.name_servers[i]['rdlength'] = int.from_bytes(data[index: index + 2], 'big')
            index += 2

            # RDATA - a variable length string of octets that describes the
            # resource.  The format of this information varies
            # according to the TYPE and CLASS of the resource record.
            # For example, the if the TYPE is A and the CLASS is IN,
            # the RDATA field is a 4 octet ARPA Internet address.
            if len(data) < index + self.name_servers[i]['rdlength']:
                raise MalformedFrameError()
            self.name_servers[i]['rdata'] = data[index: index + self.name_servers[i]['rdlength']]
            index += self.name_servers[i]['rdlength']

        self.additional = []
        if index >= len(data):
            return
        # parse answer resource record
        for i in range(self.arcount):
            self.additional.append({})
            self.additional[i]['name'] = []

            # NAME - a domain name to which this resource record pertains.
            if len(data) < index:
                raise MalformedFrameError()
            index, self.additional[i]['name'] = DNSframe.parse_name(data, index)

            # TYPE - two octets containing one of the RR type codes.  This
            # field specifies the meaning of the data in the RDATA field.
            if len(data) < index + 2:
                raise MalformedFrameError()
            self.additional[i]['type'] = int.from_bytes(data[index:index + 2], 'big')
            index += 2

            # CLASS - two octets which specify the class of the data in the RDATA field.
            self.additional[i]['class'] = int.from_bytes(data[index: index + 2], 'big')
            if len(data) < index + 2:
                raise MalformedFrameError()
            index += 2

            # TTL - a 32 bit unsigned integer that specifies the time
            # interval (in seconds) that the resource record may be
            # cached before it should be discarded.  Zero values are
            # interpreted to mean that the RR can only be used for the
            # transaction in progress, and should not be cached.
            if len(data) < index + 4:
                raise MalformedFrameError()
            self.additional[i]['ttl'] = int.from_bytes(data[index: index + 4], 'big')
            index += 4

            # RDLENGTH - an unsigned 16 bit integer that specifies the length in octets of the RDATA field.
            if len(data) < index + 2:
                raise MalformedFrameError()
            self.additional[i]['rdlength'] = int.from_bytes(data[index: index + 2], 'big')
            index += 2

            # RDATA - a variable length string of octets that describes the
            # resource.  The format of this information varies
            # according to the TYPE and CLASS of the resource record.
            # For example, the if the TYPE is A and the CLASS is IN,
            # the RDATA field is a 4 octet ARPA Internet address.
            if len(data) < index + self.additional[i]['rdlength']:
                raise MalformedFrameError()
            self.additional[i]['rdata'] = data[index: index + self.additional[i]['rdlength']]
            index += self.additional[i]['rdlength']

    @staticmethod
    def parse_name(data, index):
        ans = []
        # REDUNDANT CHECK??
        # IS IT THO?
        if index >= len(data):
            raise MalformedFrameError()
        cnt = data[index]
        next_index = index
        while cnt != 0:
            index += 1
            # check for message compression
            if cnt & 0b11000000 == 0b11000000:
                next_index = (cnt & 0b00111111) * 255 + data[index]
                _, partial = DNSframe.parse_name(data, next_index)
                ans.extend(partial)
                return index + 1, ans
            else:
                # next_index will point to the start of the next label
                next_index = index + cnt

                # parse cnt bytes
                if index + cnt >= len(data):
                    raise MalformedFrameError()
                ans.append(data[index: index + cnt])
                index = next_index
                if index >= len(data):
                    raise MalformedFrameError()
                cnt = data[index]

        return next_index + 1, ans

    def to_bytes(self, include_len=True):
        frame = b''

        # HEADER
        frame += self.id
        frame += ((self.qr << 7) | (self.opcode << 3) | (self.aa << 2) | (self.tc << 1) | self.rd).to_bytes(1, 'big')
        frame += ((self.ra << 7) | self.rcode).to_bytes(1, 'big')
        frame += self.qdcount.to_bytes(2, 'big')
        frame += self.ancount.to_bytes(2, 'big')
        frame += self.nscount.to_bytes(2, 'big')
        frame += self.arcount.to_bytes(2, 'big')

        # QUERY
        for query in self.queries:
            for label in query['qname']:
                frame += len(label).to_bytes(1, 'big')
                frame += label
            frame += b'\x00'
            frame += query['qtype'].to_bytes(2, 'big')
            frame += query['qclass'].to_bytes(2, 'big')

        # ANSWER RR
        for answer in self.answers:
            for label in answer['name']:
                frame += len(label).to_bytes(1, 'big')
                frame += label
            frame += b'\x00'
            frame += answer['type'].to_bytes(2, 'big')
            frame += answer['class'].to_bytes(2, 'big')
            # frame += answer['ttl'].to_bytes(4, 'big')
            frame += (0).to_bytes(4, 'big')
            frame += answer['rdlength'].to_bytes(2, 'big')
            frame += answer['rdata']

        # NAMESERVER RR
        for ns in self.name_servers:
            for label in ns['name']:
                frame += len(label).to_bytes(1, 'big')
                frame += label
            frame += b'\x00'
            frame += ns['type'].to_bytes(2, 'big')
            frame += ns['class'].to_bytes(2, 'big')
            frame += ns['ttl'].to_bytes(4, 'big')
            frame += ns['rdlength'].to_bytes(2, 'big')
            frame += ns['rdata']

        # ADDITIONAL RR
        for add in self.additional:
            for label in add['name']:
                frame += len(label).to_bytes(1, 'big')
                frame += label
            frame += b'\x00'
            frame += add['type'].to_bytes(2, 'big')
            frame += add['class'].to_bytes(2, 'big')
            frame += add['ttl'].to_bytes(4, 'big')
            frame += add['rdlength'].to_bytes(2, 'big')
            frame += add['rdata']

        if include_len:
            return len(frame).to_bytes(2, 'big') + frame
        else:
            return frame

class DNSserver:
    def __init__(self, verbose=True):
        if verbose:
            print('[+]Starting server...', flush=True)
        self.udp_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.tcp_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.verbose = verbose
        self.cache = Cache()

    def start(self, port=53):
        self.udp_socket.bind(('127.0.0.1', port))
        self.tcp_socket.bind(('127.0.0.1', port))

        udp_thread = threading.Thread(target=self.udp_listen)
        tcp_thread = threading.Thread(target=self.tcp_listen)
        udp_thread.start()
        tcp_thread.start()

    def udp_listen(self):
        if self.verbose:
            print('[+]Started UDP listening thread')
        while True:
            data, addr = self.udp_socket.recvfrom(512)
            new_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            t = threading.Thread(target=self.handle_conn, args=(new_socket, data, 'UDP', addr))
            t.start()
            time.sleep(0.1)

    def tcp_listen(self):
        if self.verbose:
            print('[+]Started TCP listening thread')
        self.tcp_socket.listen()
        while True:
            new_socket, addr = self.tcp_socket.accept()
            t = threading.Thread(target=self.handle_conn, args=(new_socket, None, 'TCP', None))
            t.start()
            time.sleep(0.1)

    def handle_conn(self, sockfd, data, protocol, addr=None):
        try:
            # Receive packets with tcp connection
            if protocol == 'TCP':
                data = sockfd.recv(1024)
                data_len = int.from_bytes(data[:2], 'big')
                while len(data) < data_len:
                    data += sockfd.recv(1024)
            query = DNSframe(data)
            # TODO: REMOVE LINE BELOW AND SOLVE THE PROBLEM
            # THE PROBLEM IS THAT THE OS SENDS ARCOUNT AS 1
            # query.arcount = 0

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
            for i in range(len(query.queries),1):
                del query.queries[i]
            query.qdcount = 1

            if self.verbose:
                print('[+]Making recursive call', flush=True)

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
            record_cache = self.cache.fetch_record(query.queries[0]['qname'])
            if record_cache:
                response = DNSframe()
                response.ancount = len(record_cache)
                response.answers = record_cache
            else:
                found_good_server = False
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
                        print('[-]Failed to reach DNS server')
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
                for answer in response.answers:
                    if answer['name'] == query.queries[0]['qname']:
                        self.cache.add_record(answer)
                    else:
                        print("WTF")
                        print(answer['name'])
                        print(query.queries[0]['qname'])

            if self.verbose:
                print('[+]Preparing response')

            # set the id to the one that was given in the request
            response.id = query.id

            # set to response just in case
            response.qr = 1

            # set the recursion to true
            response.rd = 1
            response.ra = 1

            if self.verbose:
                print('[+]Sending response')
            # send back the response
            send(sockfd, response.to_bytes(False), protocol, addr)

            # close the connection and exit the thread
            if self.verbose:
                print('[+]Connection closed')
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
