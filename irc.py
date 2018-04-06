"""
The main IRC server.
"""

import logging
log = logging.getLogger('ircd')
import socket

import commands

TERMINATOR = '\r\n'

class Client:
    """
    Representation of a connected IRC client.
    """

    nick = None
    username = None
    realname = None

    code = 1

    def __init__(self, transport):
        self.transport = transport
        log.debug('C {} New connection'.format(self))

    def __str__(self):
        return self.peername

    @property
    def peername(self):
        """ip:port<nick>"""
        ip, port = self.transport.get_extra_info('peername')
        nick = '<{}>'.format(self.nick if self.nick else '(unset)')
        return '{}:{}{}'.format(ip, port, nick)

    def _write(self, line):
        """
        Low-level method to send a line back to the client.
        """
        data = (line + TERMINATOR).encode()
        self.transport.write(data)
        log.debug('> {} {!r}'.format(self, line))

    def send(self, line, code=None):
        """
        Format a correct server->client line and send it.
        """
        msg = ':{server} {code:03} {nick} :{line}'.format(
                server=Server.server_name,
                code=code if code is not None else self.code,
                nick=self.nick,
                line=line)
        self._write(msg)
        self.code += 1

    def dispatch(self, line):
        """
        Parses the line given as an IRC command and dispatches it to
        a corresponding function.
        """
        log.debug('< {} {!r}'.format(self, line))
        func_name, *args = line.split()

        try:
            func = getattr(commands, func_name)
        except AttributeError:
            log.warn('! {} Unknown command {!r}'.format(self, line))
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

    @property
    def registered(self):
        return self.nick and self.username and self.realname

    def send_notices(self):
        log.debug('C {} {} ({}) is now registered'.format(self, self.username, self.realname))
        self.send('hello')

class Server:
    server_name = socket.gethostname()

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
