"""
The main IRC server.
"""

import datetime
import logging
log = logging.getLogger('ircd')
import socket

from util import *

__name__ = 'py3ircd'
__version__ = '0.1'

TERMINATOR = '\r\n'

class IncomingCommand:

    @classmethod
    def CAP(cls, client, subcmd, *args):
        """
        CAP LS | LIST | REQ :<cap> .. | ACK | NAK | END
        https://ircv3.net/specs/core/capability-negotiation-3.1.html#the-cap-command
        ircv3
        """
        pass

    @classmethod
    def NICK(cls, client, nick, *ignore):
        """
        NICK <nickname> [ <hopcount> ]
        https://tools.ietf.org/html/rfc1459#section-4.1.2
        """
        client.ident.nick = nick
        if client.ident.registered:
            client.registration_complete()

    @classmethod
    def USER(cls, client, username, ignore1, ignore2, *realname):
        """
        USER <username> <hostname> <servername> :<realname>
        https://tools.ietf.org/html/rfc1459#section-4.1.3
        """
        client.ident.username = username
        client.ident.realname = ' '.join(realname)[1:]
        if client.ident.registered:
            client.registration_complete()

    @classmethod
    def PING(cls, client, server1, *ignore):
        """
        PING <server1> [<server2>]
        https://tools.ietf.org/html/rfc1459#section-4.6.2
        Here we violate the spec by replying with a PONG to clients.
        """
        if server1 == client.server.name:
            client.PONG()

    @classmethod
    def MODE(cls, client, target, mode):
        """
        MODE <nickname> <mode>
        https://tools.ietf.org/html/rfc2812#section-3.1.5
        """
        client.ident.modeset = modeline_parser(mode, client.ident.modeset)
        client.send('MODE', mode)

    @classmethod
    def QUIT(cls, client, msg):
        pass

class Ident:
    """
    Metadata on a client instance.
    """

    # These are populated during registration
    nick = None
    username = None
    realname = None

    # user mode set
    modeset = set()

    def __init__(self, peername):
        self._peername = peername
        self.hostname = socket.gethostbyaddr(peername[0])[0]

    def __str__(self):
        return f'{self.nick}!{self.username}@{self.hostname}'

    @property
    def registered(self):
        return self.nick and self.username and self.realname

    @property
    def mode(self):
        m = '+' + ''.join(self.modeset)
        return m if len(m) > 1 else ''

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

    def send(self, cmd, msg, origin=None, to=None):
        """
        Formats a correct message and send it to the client.
        """
        to = self.ident.nick if to is None else to
        origin = self.server.name if origin is None else origin
        line = f':{origin} {cmd} {to} :{msg}'
        self._write(line)

    def registration_complete(self):
        """
        Sends the registration complete notices to the client.
        https://tools.ietf.org/html/rfc2812#section-5.1
        """
        s = self.server
        log.debug(f'C {self} {self.ident} is now registered')
        self.send('001', f'Welcome to the Internet Relay Network {self.ident}')
        self.send('002', f'Your host is {s}, running version {s.version}')
        self.send('003', f'This server was created {s.created}')
        self.send('004', f'{s.name} {s.version} <user modes> <channel modes>')

    def PONG(self):
        self.send('PONG', str(self.server), to=str(self.server))

class Server:
    name = socket.gethostname()
    version = f'{__name__} {__version__}'
    created = datetime.datetime.now()

    clients = {} #: {transport: Client}

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
