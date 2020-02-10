import socket
import threading
import time
from copy import deepcopy as cp
from os import urandom

class MalformedFrameError(Exception):
    def __init__(self, expression=None, message=None):
        self.expression = expression
        self.message = message

class DNSframe:
    def __init__(self, data=None):
        if data is None:
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
            return

        if len(data) < 12:
            raise MalformedFrameError()

        self.queries = []
        self.answers = []

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

        if index >= len(data):
            return
        # parse resource record AKA answer
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

    @staticmethod
    def parse_name(data, index):
        ans = []
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

        # RESOURCE RECORDS
        for answer in self.answers:
            for label in answer['name']:
                frame += len(label).to_bytes(1, 'big')
                frame += label
            frame += b'\x00'
            frame += answer['type'].to_bytes(2, 'big')
            frame += answer['class'].to_bytes(2, 'big')
            frame += answer['ttl'].to_bytes(4, 'big')
            frame += answer['rdlength'].to_bytes(2, 'big')
            frame += answer['rdata']

        if include_len:
            return len(frame).to_bytes(2, 'big') + frame
        else:
            return frame

class DNSserver:
    def __init__(self, verbose=True):
        if verbose:
            print('[+]Starting server...', flush=True)
        self.listen_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.verbose = verbose
        self.connections = []

    def start(self, timeout=None):
        self.listen_socket.bind(('192.168.0.173', 53))
        self.listen_socket.listen()
        if self.verbose:
            print('[+]Listening for connections', flush=True)

        start_time = time.time()
        while (timeout is None) or (time.time() - start_time < timeout):
            conn, addr = self.listen_socket.accept()
            if self.verbose:
                print('[+]Connection received from', addr, flush=True)
            self.connections.append(threading.Thread(target=self.handle_connection, args=(conn, addr)))
            self.connections[-1].daemon = True
            self.connections[-1].start()
            time.sleep(0.1)

        self.close()

    def handle_connection(self, conn, addr):
        if self.verbose:
            print('[+]Thread spawned', flush=True)

        # first 2 bytes indicate the message size
        data = conn.recv(1024)
        frame_size = int.from_bytes(data[:2], 'big')
        data = data[2:]
        while len(data) < frame_size:
            data += conn.recv(1024)

        if self.verbose:
            print('[+]Received', frame_size, 'bytes from', addr, flush=True)

        try:
            query = DNSframe(data)
        except MalformedFrameError:
            if self.verbose:
                print('[-]Frame is malformed. Closing connection...', flush=True, end='')
            if len(data) >= 2:
                response = DNSframe()

                # set id to the one from the request
                response.id = data[:2]

                # set to response
                response.qr = 1

                # set to format error
                response.rcode = 1

                conn.sendall(response.to_bytes())
            conn.close()
            print('done', flush=True)
            return

        # if it is not a query send format err and exit
        if query.qr != 0:
            if self.verbose:
                print('[-]Frame is not a query', flush=True)
            response = DNSframe()

            # set id to the one from the request
            response.id = data[:2]

            # set to response
            response.qr = 1

            # set to format error
            response.rcode = 1

            conn.sendall(response.to_bytes())
            conn.close()
            return

        if self.verbose:
            print('[+]Making recursive call...', end='', flush=True)
        # we will just forward the query to google's 8.8.8.8 and do it recursively regardless
        forward_request = cp(query)

        # set the recursion flags
        forward_request.rd = 1
        forward_request.ra = 1

        # generate random id for the message
        forward_request.id = urandom(2)

        # set answers to [] just in case
        forward_request.ancount = 0
        forward_request.answers = []

        # open connection to 8.8.8.8 and send the request
        forward_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        forward_socket.connect(('8.8.8.8', 53))
        forward_socket.sendall(forward_request.to_bytes())

        # get the response
        server_response = forward_socket.recv(1024)
        server_response_size = int.from_bytes(server_response[:2], 'big')
        server_response = server_response[2:]
        while len(server_response) < server_response_size:
            server_response += forward_socket.recv(1024)
        forward_socket.close()
        if self.verbose:
            print('done', flush=True)

        # parse the response and send it back
        try:
            response = DNSframe(server_response)
        except MalformedFrameError:
            print('[-]Uhm...looks like google forgot how to DNS')
            response = DNSframe()

            # set id to the one from the request
            response.id = query.id

            # set to response
            response.qr = 1

            # set to server failure
            response.rcode = 2

            conn.sendall(response.to_bytes())
            conn.close()
            return

        if forward_request.id != response.id:
            print('[-]Wrong id received from the name server...closing connection')
            response = DNSframe()

            # set id to the one from the request
            response.id = query.id

            # set to response
            response.qr = 1

            # set to server failure
            response.rcode = 2

            conn.sendall(response.to_bytes())
            conn.close()
            return

        # TODO: CACHE IF THERE IS NO ERR
        # TODO: ERR HANDLE SEND() AND RECV()

        # set the id to the one that was given in the request
        response.id = query.id

        # set to response just in case
        response.qr = 1

        # set the Authoritative answer to 0 because we are not that
        response.aa = 0

        # set the recursion to true
        response.rd = 1
        response.ra = 1

        # send back the response
        conn.sendall(response.to_bytes())

        # close the connection and exit the thread
        conn.close()
        return


    def close(self, code=0):
        if self.verbose:
            print('[+]Joining threads and exiting...', flush=True)
        for conn in self.connections:
            conn.join(0.2)
        exit(code)


if __name__ == '__main__':
    server = DNSserver()
    server.start()
