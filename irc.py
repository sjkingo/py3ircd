"""
The main IRC server.
"""

import datetime
import logging
log = logging.getLogger('ircd')
import socket

from codes import *
from channel import Channel
from exc import *
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
        """
        Example: <nick(+i)> or <(unreg)> or <nick>
        """
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

    def closed(self, reason):
        """
        Called when the client has quit or the underlying connection has
        been closed.
        """
        log.debug(f'C {self} Closed connection ({reason})')

    def send_as_user(self, command, msg):
        """
        Sends a message using the client's prefix.
        """
        self._write(f':{self.ident} {command} {msg}')

    def send_as_server(self, command, msg):
        """
        Sends a message using the server's prefix.
        """
        self._write(f':{self.server.name} {command} {msg}')

    def registration_complete(self):
        """
        Sends the registration complete notices to the client.
        https://tools.ietf.org/html/rfc2812#section-5.1
        """
        s = self.server
        nick = self.ident.nick
        log.debug(f'C {self} {self.ident} is now registered to {s}')
        self.send_as_server(RPL_WELCOME, f'{nick} :Welcome to the Internet Relay Network {self.ident}')
        self.send_as_server(RPL_YOURHOST, f'{nick} :Your host is {s}, running version {s.version}')
        self.send_as_server(RPL_CREATED, f'{nick} :This server was created {s.created}')
        user_modes = ''.join(s.supported_user_modeset)
        chan_modes = ''.join(s.supported_chan_modeset)
        self.send_as_server(RPL_MYINFO, f'{nick} :{s} {s.version} {user_modes} {chan_modes}')
        self.send_as_server(RPL_LUSERCLIENT, f'{nick} :There are {len(s.clients)} user(s) on 1 server')
        self.send_as_server(RPL_LUSERCHANNELS, f'{nick} {len(s.channels)} :channels formed')

    def dispatch_mode_for_channel(self, target, mode):
        """
        Called to set/get mode of a channel by this client.
        """
        channel = target[1:]
        assert channel in self.server.channels
        self.server.channels[channel].mode(self, mode)

class Server:
    """
    The main IRC server instance.
    """

    # Some metadata on this server
    name = socket.gethostname()
    version = f'{__name__} {__version__}'
    created = datetime.datetime.now()

    # The supported modes for this server
    supported_user_modeset = frozenset(list('i'))
    supported_chan_modeset = frozenset(list('ns'))

    # Commands that can be received without registering
    allowed_unregistered_cmds = frozenset(['NICK', 'USER', 'QUIT'])

    clients = {} #: {transport: Client}
    channels = {} #: {name: Channel}

    def __str__(self):
        return self.name

    def new_connection(self, transport):
        """
        Handles an incoming connection from a new client.
        """
        assert transport not in self.clients
        self.clients[transport] = Client(transport, self)

    def data_received(self, transport, line):
        """
        Parse line from client and dispatch to appropriate function.
        Catches any errors raised and sends back formatted error responses.
        """

        if transport not in self.clients:
            return

        client = self.clients[transport]
        log.debug(f'< {client} {line!r}')

        func_name, *args = line.split()
        func = getattr(IncomingCommand, func_name, None)

        # Dispatch and handle errors
        try:
            if func is None:
                raise UnknownCommand(func_name)
            if not client.ident.registered and func_name not in self.allowed_unregistered_cmds:
                raise UnregisteredDisallow()
            func(client, *args)

        except UnknownCommand as e:
            log.info(f'! {client} *** Unknown command {e} ***')
            client.send_as_server(ERR_UNKNOWNCOMMAND, f'{client.ident.nick} {e} :Unknown command')

        except TypeError as e:
            # A TypeError calling func() means the arguments were incorrect
            if str(e).startswith(func_name + '()'):
                log.info(f'! {client} {line!r}: {e}')
                client.send_as_server(ERR_NEEDSMOREPARAMS, f'{client.ident.nick} {func_name} :{e}')
            # Or it could be an exception from the function execution itself
            else:
                raise

        except UnregisteredDisallow as e:
            client.send_as_server(ERR_NOTREGISTERED, f':You have not registered')

    def connection_lost(self, transport, exc):
        if transport not in self.clients:
            return
        reason = str(exc) if exc else 'Connection reset by peer'
        self.clients[transport].closed(reason)
        del self.clients[transport]
