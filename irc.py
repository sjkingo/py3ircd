"""
The main IRC server.
"""

import logging
log = logging.getLogger('ircd')

import commands

TERMINATOR = '\r\n'

class Client:
    """
    Representation of a connected IRC client.
    """

    nick = None

    def __init__(self, transport):
        self.transport = transport
        log.debug('C {} New connection'.format(self))

    def __str__(self):
        return self.peername

    @property
    def peername(self):
        """ip:port"""
        ip, port = self.transport.get_extra_info('peername')
        nick = '<{}>'.format(self.nick if self.nick else '(unset)')
        return '{}:{}{}'.format(ip, port, nick)

    def send(self, line):
        data = (line + TERMINATOR).encode()
        self.transport.write(data)
        log.debug('> {} {!r}'.format(self, line))

    def dispatch(self, line):
        """
        Parses the line given as an IRC command and dispatches it to
        a corresponding function.
        """
        log.debug('< {} {!r}'.format(self, line))
        cmd, *args = line.split()
        func_name = cmd.lower()

        try:
            func = getattr(commands, func_name)
        except AttributeError:
            log.warn('! {} Unknown command {} in {!r}'.format(self, cmd, line))
            return

        try:
            r = func(self, *args)
        except TypeError as e:
            func_str = func_name + '()'
            if str(e).startswith(func_str):
                log.warn('! {} Error in command {!r}: {}'.format(self, line, e))
                return
            else:
                raise

        if r:
            self.send(r)

class Server:
    clients = {} #: {transport: Client}

    def new_connection(self, transport):
        assert transport not in self.clients
        client = Client(transport)
        self.clients[transport] = client

    def data_received(self, transport, line):
        """
        Dispatches to the correct client.
        """
        assert transport in self.clients
        self.clients[transport].dispatch(line)
