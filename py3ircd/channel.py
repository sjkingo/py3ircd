from codes import *
from util import modeline_parser

DEFAULT_CHANNEL_MODE = '+ns'

class Channel:
    clients = set() # clients joined to this channel

    def __init__(self, name, owner, mode=DEFAULT_CHANNEL_MODE):
        self.name = name
        self.owner = owner
        self.modeset = modeline_parser(mode)

    def __str__(self):
        return f'#{self.name}'

    @property
    def mode_as_str(self):
        return '+' + ''.join(self.modeset)

    def chansend_as_user(self, command, msg, user=None):
        """
        Sends the specified message to all users on the channel.
        """
        for c in self.clients:
            c.send_as_user(command, msg, user=user)

    def chansend_as_server(self, command, msg):
        """
        Sends the specified message to all users on the channel.
        """
        for c in self.clients:
            c.send_as_server(command, msg)

    def join(self, client):
        """
        Join the specified client to this channel.
        """

        self.clients.add(client)
        client.joined_channels[self.name] = self
        self.chansend_as_user('JOIN', str(self), user=client)
        self.send_names(client)

        # Newly created channel
        if len(self.clients) == 1:
            self.chansend_as_server('MODE', f'{self} {self.mode_as_str}')

    def send_names(self, client):
        """
        Send the NAMES list to the specified client.
        """
        nick = client.ident.nick
        onchan = ' '.join([c.ident.nick for c in self.clients])
        client.send_as_server(RPL_NAMREPLY, f'{nick} @ {self} :@{onchan}')
        client.send_as_server(RPL_ENDOFNAMES, f'{nick} {self} :End of /NAMES list.')

    def user_quit(self, client, reason):
        """
        Send a QUIT message to all users in the channel when the specified
        client quits, and remove them from the channel.
        """
        for c in self.clients:
            if c == client:
                continue
            c.send_as_user('QUIT', f':{reason}', user=client) # send as client
        self.clients.remove(client)

    def mode(self, client, mode=None):
        """
        Sets or gets the channel mode.
        """

        nick = client.ident.nick

        if mode is None:
            client.send_as_server(RPL_CHANNELMODEIS, f'{nick} {self} {self.mode_as_str}')
            return

        # Return banlist
        if mode == 'b':
            # RPL_BANLIST
            client.send_as_server(RPL_ENDOFBANLIST, f'{nick} {self} :End of channel ban list')
            return

        # Otherwise parse and set mode
        self.modeset = modeline_parser(mode, self.modeset)
        client.send_as_user('MODE', f'{self} {mode}')

    def send_who(self, client):
        """
        #channel ~ownernick ownerhost server <nick> <H|G>[*][@|+] :<hopcount> <real_name>

        WHO #boo
        :orwell.freenode.net 352 sjkingo123 #boo ~f 122-129-143-130.dynamic.ipstaraus.com orwell.freenode.net sjkingo123 H :0 ff
        :orwell.freenode.net 352 sjkingo123 #boo ChanServ services. services. ChanServ H@ :0 Channel Services
        :orwell.freenode.net 315 sjkingo123 #boo :End of /WHO list.
        """

        prefix = f'{client.ident.nick} {self}'
        o = self.owner
        i = o.ident
        client.send_as_server(RPL_WHOREPLY, f'{prefix} {i.prefix}{i.nick} {i.hostname} {o.server.name} {client.ident.nick} H :0 {i.realname}')
        client.send_as_server(RPL_ENDOFWHO, f'{prefix} :End of /WHO list.')
