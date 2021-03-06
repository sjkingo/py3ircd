"""
The main IRC server.
"""

import datetime
import logging
log = logging.getLogger('ircd')
import socket
from util import *

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

    awaiting_pong_since = None
    joined_channels = {} #: {name: Channel}

    def __init__(self, transport, server):
        self._transport = transport
        self.server = server
        self.ident = Ident(transport.get_extra_info('peername'))
        self.connected_at = datetime.datetime.now()
        ip, port = self.ident._peername
        log.info(f'{self} ## New connection from {ip}:{port}')

    def __str__(self):
        return self.ident.nick or '(unreg)'

    def _write(self, line):
        """
        Low-level method to send a line back to the client.
        """
        data = (line + TERMINATOR).encode()
        self._transport.write(data)
        log.debug(f'{self} >> {line!r}')

    def send_as_user(self, command, msg, user=None):
        """
        Sends a message using the client's prefix.
        """
        user = self if user is None else user
        self._write(f':{user.ident} {command} {msg}')

    def send_as_server(self, command, msg):
        """
        Sends a message using the server's prefix.
        """
        self._write(f':{self.server.name} {command} {msg}')

    def send_as_nick(self, command, msg):
        """
        Sends a message as the nick (rarely used).
        """
        self._write(f':{self.ident.nick} {command} {msg}')

    def set_mode(self, modeline):
        """
        Sets the user's mode.
        """

        # Verify the modeline has valid modes
        for m in modeline:
            if m.isalpha() and m not in self.server.supported_user_modeset:
                self.send_as_server(ERR_UMODEUNKNOWNFLAG,
                        f'{self.ident.nick} :Unknown MODE flag')
                return

        old_modeset = self.ident.modeset
        self.ident.modeset = modeline_parser(modeline, old_modeset)

        # Only send MODE message if modes have changed
        if old_modeset != self.ident.modeset:
            self.send_as_nick('MODE', f'{self.ident.nick} :{modeline}')

    def registration_complete(self):
        """
        Sends the registration complete notices to the client.
        https://tools.ietf.org/html/rfc2812#section-5.1
        """
        s = self.server
        nick = self.ident.nick
        log.debug(f'{self} ## {self.ident} is now registered to {s}')
        self.send_as_server(RPL_WELCOME, f'{nick} :Welcome to the Internet Relay Network {self.ident}')
        self.send_as_server(RPL_YOURHOST, f'{nick} :Your host is {s}, running version {s.version}')
        self.send_as_server(RPL_CREATED, f'{nick} :This server was created {s.created}')
        user_modes = ''.join(s.supported_user_modeset)
        chan_modes = ''.join(s.supported_chan_modeset)
        self.send_as_server(RPL_MYINFO, f'{nick} :{s} {s.version} {user_modes} {chan_modes}')
        self.send_as_server(RPL_LUSERCLIENT, f'{nick} :There are {len(s.clients)} user(s) on 1 server')
        self.send_as_server(RPL_LUSERCHANNELS, f'{nick} {len(s.channels)} :channels formed')
        self.set_mode('+i')

    def dispatch_mode_for_channel(self, target, mode):
        """
        Called to set/get mode of a channel by this client.
        """
        channel = target[1:]
        assert channel in self.server.channels
        self.server.channels[channel].mode(self, mode)

    def ping(self):
        """
        Send a ping request to the client.
        """
        self._write(f'PING :{self.server.name}')
        self.awaiting_pong_since = datetime.datetime.now()

class Server:
    """
    The main IRC server instance.
    """

    # Some metadata on this server
    name = socket.gethostname()
    version = f'{__name__} {__version__}'
    created = datetime.datetime.now()
    info = version

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
        log.debug(f'{client} << {line!r}')

        try:
            func_name, *args = line.split()
        except ValueError:
            return
        func = getattr(IncomingCommand, func_name, None)

        # Dispatch and handle errors
        try:
            if func is None:
                raise UnknownCommand(func_name)
            if not client.ident.registered and func_name not in self.allowed_unregistered_cmds:
                raise UnregisteredDisallow()
            func(client, *args)

        except UnknownCommand as e:
            log.info(f'{client} *** Unknown command {e} ***')
            client.send_as_server(ERR_UNKNOWNCOMMAND, f'{client.ident.nick} {e} :Unknown command')

        except TypeError as e:
            # A TypeError calling func() means the arguments were incorrect
            if str(e).startswith(func_name + '()'):
                client.send_as_server(ERR_NEEDSMOREPARAMS, f'{client.ident.nick} {func_name} :{e}')
            # Or it could be an exception from the function execution itself
            else:
                raise

        except UnregisteredDisallow as e:
            client.send_as_server(ERR_NOTREGISTERED, f'* :You have not registered')

    def client_close(self, transport, reason):
        """
        Called the close a client's connection.
        """

        client = self.clients[transport]

        if client.ident.registered:
            client.send_as_user('QUIT', f':{reason}')
        for chan in client.joined_channels.values():
            chan.user_quit(client, reason)

        client._write(f'ERROR :Closing Link: {client.ident.hostname} ({reason})')

        del self.clients[transport]
        transport.close()
        log.info(f'{client} ## Closed connection ({reason})')

    def connection_lost(self, transport, exc):
        """
        Called when a client connection is lost (peer closed, reset, etc).
        """
        if transport not in self.clients:
            return
        reason = str(exc) if exc else 'Connection reset by peer'
        self.client_close(transport, reason)

    def check_timeout(self, transport, earlier_time, interval, error_msg):
        """
        Check for a timeout and close connection if so.
        """
        now = datetime.datetime.now()
        secs = int((now - earlier_time).total_seconds())
        if secs >= interval:
            self.connection_lost(transport, f'{error_msg}: {secs} seconds')

    def send_pings(self, interval):
        """
        Send PING requests to all clients and check any pending PONGs.
        """
        for client in list(self.clients.values()):
            t = client._transport
            if client.ident.registered:
                since = client.awaiting_pong_since
                if not since:
                    client.ping()
                else:
                    self.check_timeout(t, since, interval, 'Ping timeout')
            else:
                self.check_timeout(t, client.connected_at, interval, 'Connection timed out')

    def get_client_by_nick(self, nick):
        """
        Returns a Client instance by nickname.
        """
        for client in self.clients.values():
            if client.ident.nick == nick:
                return client
        return None

    def check_nick_in_use(self, nick):
        """
        Checks if the specified nickname is in use already.
        """
        return self.get_client_by_nick(nick) is not None
