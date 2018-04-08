import socket

from channel import Channel
from util import *

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
        PING <server1> [ <server2> ]
        https://tools.ietf.org/html/rfc2812#section-3.7.2
        """
        if server1[0] == ':':
            server1 = server1[1:]
        if server1 == client.server.name:
            client.send_as_server('PONG', f'{server1} :{server1}')

    @classmethod
    def PONG(cls, client, server1, *ignore):
        """
        PONG <server> [ <server2> ]
        https://tools.ietf.org/html/rfc2812#section-3.7.3
        """
        if server1[0] == ':':
            server1 = server1[1:]
        if server1 == client.server.name:
            if client.awaiting_pong_since:
                client.awaiting_pong_since = None

    @classmethod
    def MODE(cls, client, target, mode=None):
        """
        MODE <@nickname>|<#channel> [<mode>]
        https://tools.ietf.org/html/rfc2812#section-3.1.5
        """

        if target[0] == '#':
            client.dispatch_mode_for_channel(target, mode)
            return

        if target[0] == '@':
            target = target[1:]

        if mode is None:
            # return client's mode
            pass
        else:
            client.ident.modeset = modeline_parser(mode, client.ident.modeset)
            client.send_as_user('MODE', f'{client.ident.nick} :{mode}')

    @classmethod
    def QUIT(cls, client, msg=None):
        """
        QUIT [ <Quit Message> ]
        https://tools.ietf.org/html/rfc2812#section-3.1.7
        """
        msg = f'Client quit: {msg[1:]}' if msg and len(msg) > 0 else 'Client quit'
        client.server.client_close(client._transport, msg)

    @classmethod
    def JOIN(cls, client, name):
        assert name[0] == '#'
        name = name[1:]
        channel = client.server.channels.get(name, None)
        if not channel:
            channel = Channel(name)
            client.server.channels[name] = channel
        channel.join(client)

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
