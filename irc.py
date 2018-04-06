"""
The main IRC server.
"""

import logging
log = logging.getLogger('ircd')

TERMINATOR = '\r\n'

class Client:
    """
    Representation of a connected IRC client.
    """

    def __init__(self, transport):
        self.transport = transport
        log.debug('C {} New connection'.format(self))
        self.send('SERV')

    def __str__(self):
        return self.peername

    @property
    def peername(self):
        """ip:port"""
        return ':'.join(map(str, self.transport.get_extra_info('peername')))

    def send(self, line):
        data = (line + TERMINATOR).encode()
        self.transport.write(data)
        log.debug('> {} {!r}'.format(self, line))

    def recv(self, line):
        log.debug('< {} {!r}'.format(self, line))

class Server:
    clients = {} #: {transport: Client}

    def new_connection(self, transport):
        assert transport not in self.clients
        client = Client(transport)
        self.clients[transport] = client

    def parse_incoming_line(self, transport, line):
        assert transport in self.clients
        client = self.clients[transport]
        client.recv(line)
