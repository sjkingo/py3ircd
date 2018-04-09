from codes import *
from util import modeline_parser

DEFAULT_CHANNEL_MODE = '+ns'

class Channel:
    clients = set() # clients joined to this channel

    def __init__(self, name, mode=DEFAULT_CHANNEL_MODE):
        self.name = name
        self.modeset = modeline_parser(mode)

    def __str__(self):
        return f'#{self.name}'

    @property
    def mode_as_str(self):
        return '+' + ''.join(self.modeset)

    def join(self, client):
        """
        Join the specified client to this channel.
        """

        self.clients.add(client)
        client.joined_channels[self.name] = self

        for c in self.clients:
            c.send_as_user('JOIN', str(self))

        # Newly created channel
        if len(self.clients) == 1:
            client.send_as_server('MODE', f'{self} {self.mode_as_str}')

        for c in self.clients:
            self.send_names(c)

    def send_names(self, client):
        """
        Send the NAMES list to the specified client.
        """
        nick = client.ident.nick
        others = ' '.join([c.ident.nick for c in self.clients])
        client.send_as_server(RPL_NAMREPLY, f'{nick} @ {self} :@{others}')
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
        if mode is None:
            client.send_as_server(RPL_CHANNELMODEIS, f'{client.ident.nick} {self} {self.mode_as_str}')
        else:
            self.modeset = modeline_parser(mode, self.modeset)
            client.send_as_user('MODE', f'{self} {mode}')
