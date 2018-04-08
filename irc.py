"""
The main IRC server.
"""

import datetime
import logging
log = logging.getLogger('ircd')
import socket

from channel import Channel
from user import Ident, IncomingCommand

__name__ = 'py3ircd'
__version__ = '0.1'

TERMINATOR = '\r\n'

class Client:
    """
    A connected IRC client connection.
    Metadata on the client is stored in `self.ident`.
    """

    def __init__(self, transport, server):
        self._transport = transport
        self.server = server
        self.ident = Ident(transport.get_extra_info('peername'))
        log.debug(f'C {self} New connection')

    def __str__(self):
        ip, port = self.ident._peername
        nick = self.ident.nick or '(unreg)'
        mode = f'({self.ident.mode})' if self.ident.mode else ''
        return f'{ip}:{port} <{nick}{mode}>'

    def _write(self, line):
        """
        Low-level method to send a line back to the client.
        """
        data = (line + TERMINATOR).encode()
        self._transport.write(data)
        log.debug(f'> {self} {line!r}')

    def send_as_user(self, msg):
        """
        Sends a message using the client's prefix.
        """
        self._write(f':{self.ident} {msg}')

    def send_as_server(self, msg):
        """
        Sends a message using the server's prefix.
        """
        self._write(f':{self.server.name} {msg}')

    def registration_complete(self):
        """
        Sends the registration complete notices to the client.
        https://tools.ietf.org/html/rfc2812#section-5.1
        """
        s = self.server
        nick = self.ident.nick
        log.debug(f'C {self} {self.ident} is now registered to {s}')
        self.send_as_server(f'001 {nick} :Welcome to the Internet Relay Network {self.ident}')
        self.send_as_server(f'002 {nick} :Your host is {s}, running version {s.version}')
        self.send_as_server(f'003 {nick} :This server was created {s.created}')
        user_modes = ''.join(s.supported_user_modeset)
        chan_modes = ''.join(s.supported_chan_modeset)
        self.send_as_server(f'004 {nick} :{s} {s.version} {user_modes} {chan_modes}')
        self.send_as_server(f'251 {nick} :There are {len(s.clients)} user(s) on 1 server')
        self.send_as_server(f'254 {nick} {len(s.channels)} :channels formed')

    def dispatch_mode_for_channel(self, target, mode):
        """
        Called to set/get mode of a channel by this client.
        """
        channel = target[1:]
        assert channel in self.server.channels
        self.server.channels[channel].mode(self, mode)

class Server:
    name = socket.gethostname()
    version = f'{__name__} {__version__}'
    created = datetime.datetime.now()

    supported_user_modeset = set(list('i'))
    supported_chan_modeset = set(list('ns'))

    clients = {} #: {transport: Client}
    channels = {} #: {name: Channel}

    def __str__(self):
        return self.name

    def new_connection(self, transport):
        assert transport not in self.clients
        self.clients[transport] = Client(transport, self)

    def data_received(self, transport, line):
        assert transport in self.clients
        client = self.clients[transport]
        log.debug(f'< {client} {line!r}')

        func_name, *args = line.split()
        try:
            func = getattr(IncomingCommand, func_name)
        except AttributeError:
            log.info(f'! {client} *** Unknown command {line!r}')
            return

        try:
            r = func(client, *args)
        except TypeError as e:
            if str(e).startswith(func_name + '()'):
                log.info(f'! {client} {line!r}: {e}')
                return
            else:
                raise
