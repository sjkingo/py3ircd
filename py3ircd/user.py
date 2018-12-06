import socket

from channel import Channel
from codes import *
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

        if client.server.check_nick_in_use(nick):
            client.send_as_server(ERR_NICKNAMEINUSE, f'* {nick} :Nickname is already in use.')
            return

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
        MODE <nickname>|<#channel> [<mode>]
        https://tools.ietf.org/html/rfc2812#section-3.1.5
        """

        if target[0] == '#':
            client.dispatch_mode_for_channel(target, mode)
            return

        if target != client.ident.nick:
            client.send_as_server(ERR_USERSDONTMATCH,
                    f'{client.ident.nick} :Can\'t view or change mode for other users')
            return

        if mode is None:
            client.send_as_server(RPL_UMODEIS, f'{client.ident.nick} {client.ident.mode}')
        else:
            client.set_mode(mode)

    @classmethod
    def QUIT(cls, client, *msg_parts):
        """
        QUIT [ <Quit Message> ]
        https://tools.ietf.org/html/rfc2812#section-3.1.7
        """
        reason = ' '.join(msg_parts)[1:]
        msg = f'Client quit: ({reason})' if len(reason) > 0 else 'Client quit'
        client.server.client_close(client._transport, msg)

    @classmethod
    def JOIN(cls, client, name):
        """
        Joins the specified channel, creating it if it doesn't exist.
        """

        if name[0] == '#':
            name = name[1:]

        channel = client.server.channels.get(name, None)
        if not channel:
            channel = Channel(name, client)
            client.server.channels[name] = channel

        channel.join(client)

    @classmethod
    def WHOIS(cls, client, target):
        """
        WHOIS <target>
        https://tools.ietf.org/html/rfc2812#section-3.6.2
        """

        prefix = f'{client.ident.nick} {target}'
        s = client.server

        user = client.server.get_client_by_nick(target)
        if user is None:
            client.send_as_server(ERR_NOSUCHNICK, ':No such nick/channel')
        else:
            i = user.ident
            client.send_as_server(RPL_WHOISUSER, f'{prefix} ~{target} {i.hostname} * :{i.realname}')
            client.send_as_server(RPL_WHOISSERVER, f'{prefix} {s.name} :{s.info}')

        client.send_as_server(RPL_ENDOFWHOIS, f'{prefix} :End of /WHOIS list.')

    @classmethod
    def WHO(cls, client, target):
        """
        WHO <target>
        https://tools.ietf.org/html/rfc2812#section-3.6.1
        """
        if target[0] == '#':
            chan = client.server.channels.get(target[1:], None)
            if not chan:
                pass
            chan.send_who(client)

    @classmethod
    def PRIVMSG(cls, client, target, *msg_parts):
        """
        PRIVMSG
        <msgtarget> <text to be sent>
        https://tools.ietf.org/html/rfc2812#section-3.3.1
        """

        msg = ' '.join(msg_parts)[1:]

        if target[0] == '#':
            chan = client.server.channels.get(target[1:], None)
            if not chan:
                pass
            chan.send_to_channel(client, msg)

class Ident:
    """
    Metadata on a client instance.
    """

    # These are populated during registration
    nick = None
    username = None
    realname = None
    prefix = '~'

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
        return '+' + ''.join(self.modeset)
