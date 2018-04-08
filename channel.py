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
        client.send_as_user(f'JOIN {self}')
        client.send_as_server(f'MODE {self} {self.mode_as_str}')
        self.send_names(client)

    def send_names(self, client):
        """
        Send the NAMES list to the specified client.
        """
        nick = client.ident.nick
        client.send_as_server(f'353 {nick} @ {self} :@{nick}')
        client.send_as_server(f'366 {nick} {self} :End of /NAMES list.')

    def mode(self, client, mode=None):
        """
        Sets or gets the channel mode.
        """
        if mode is None:
            client.send_as_server(f'324 {client.ident.nick} {self} {self.mode_as_str}')
        else:
            self.modeset = modeline_parser(mode, self.modeset)
            client.send_as_user(f'MODE {self} {mode}')
