import socket

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