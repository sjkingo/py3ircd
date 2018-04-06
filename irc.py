"""
The main IRC server.
"""

import logging
log = logging.getLogger('ircd')
import socket

import commands

TERMINATOR = '\r\n'

class Ident:
    nick = None
    username = None
    realname = None

    def __str__(self):
        return f'{self.username}/{self.nick} ({self.realname})'

    @property
    def registered(self):
        return self.nick and self.username and self.realname

class Client:
    """
    Representation of a connected IRC client.
    """

    ident = Ident()
    code = 1

    def __init__(self, transport):
        self.transport = transport
        log.debug(f'C {self} New connection')

    def __str__(self):
        return self.peername

    @property
    def peername(self):
        """ip:port<nick>"""
        ip, port = self.transport.get_extra_info('peername')
        nick = '<{}>'.format(self.ident.nick if self.ident.nick else '(unset)')
        return f'{ip}:{port}{nick}'

    def _write(self, line):
        """
        Low-level method to send a line back to the client.
        """
        data = (line + TERMINATOR).encode()
        self.transport.write(data)
        log.debug(f'> {self} {line!r}')

    def send(self, line, code=None):
        """
        Format a correct server->client line and send it.
        """
        msg = ':{server} {code:03} {nick} :{line}'.format(
                server=Server.server_name,
                code=code if code is not None else self.code,
                nick=self.ident.nick,
                line=line)
        self._write(msg)
        self.code += 1

    def dispatch(self, line):
        """
        Parses the line given as an IRC command and dispatches it to
        a corresponding function.
        """
        log.debug(f'< {self} {line!r}')
        func_name, *args = line.split()

        try:
            func = getattr(commands, func_name)
        except AttributeError:
            log.warn(f'! {self} Unknown command {line!r}')
            return

        try:
            r = func(self, *args)
        except TypeError as e:
            func_str = func_name + '()'
            if str(e).startswith(func_str):
                log.warn(f'! {self} Error in command {line!r}: {e}')
                return
            else:
                raise

    def send_notices(self):
        log.debug(f'C {self} {self.ident} is now registered')
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
