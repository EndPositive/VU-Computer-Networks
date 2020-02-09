import socket
import threading
import time

class DNSframe:
    def __init__(self, data):
        if len(data) < 12:
            return

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

            if len(data) <  index:
                return
            # QNAME - a domain name represented as a sequence of labels, where
            # each label consists of a length octet followed by that
            # number of octets.  The domain name terminates with the
            # zero length octet for the null label of the root.  Note
            # that this field may be an odd number of octets; no padding is used.
            cnt = int.from_bytes(data[index], 'big')
            while cnt != 0:
                # copy_index will point to the start of the next label
                copy_index = index + cnt + 1

                # check for message compression
                if cnt & 0b11000000 == 0b11000000:
                    # move the index to the pointer offset
                    index = cnt & 0b00111111
                    # parse the number of bytes there
                    cnt = int.from_bytes(data[index], 'big')

                # parse cnt bytes
                self.queries[i]['qname'].append(data[index: index + cnt])
                index = copy_index
                cnt = int.from_bytes(data[index], 'big')

            # move index over the 0 byte
            index += 1

            if len(data) < index + 4:
                return
            # QTYPE - a two octet code which specifies the type of the query.
            # The values for this field include all codes valid for a
            # TYPE field, together with some more general codes which
            # can match more than one type of RR.
            self.queries[i]['qtype'] = int.from_bytes(data[index:index + 2], 'big')
            index += 2

            if len(data) < index + 4:
                return
            # QCLASS - a two octet code which specifies the type of the query.
            # The values for this field include all codes valid for a
            # TYPE field, together with some more general codes which
            # can match more than one type of RR.
            self.queries[i]['qclass'] = int.from_bytes(data[index: index + 2], 'big')
            index += 2





class DNSserver:
    def __init__(self, verbose=True):
        self.listen_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.verbose = verbose
        self.connections = []

    def start(self, timeout=None):
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
        data = data[:2]
        while len(data) < frame_size:
            data += conn.recv(1024)

        if self.verbose:
            print('[+]Received', frame_size, 'bytes from', addr, flush=True)

        packet = DNSframe(data)

    def close(self, code=0):
        if self.verbose:
            print('[+]Joining threads and exiting...', flush=True)
        for conn in self.connections:
            conn.join(0.2)
        exit(code)


if __name__ == '__main__':
    pass
