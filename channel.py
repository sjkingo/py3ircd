from util import modeline_parser

DEFAULT_CHANNEL_MODE = '+ns'

class Channel:

    users = set()

    def __init__(self, name, mode=DEFAULT_CHANNEL_MODE):
        self.name = name
        self.nameh = '#' + name
        self.modeset = modeline_parser(mode)

    @property
    def mode_as_str(self):
        return '+' + ''.join(self.modeset)

    def join(self, client):
        self.users.add(client)
        client.send('MODE', self.mode_as_str, to=self.nameh, sep='')
        self.send_names([client])

    def send_names(self, users=None):
        if not users:
            users = list(self.users)
        for to in users:
            to.send('353', f'@{to.ident.nick}', suffix=f'@ {self.nameh}')
            to.send('366', 'End of /NAMES list.', suffix=f'{self.nameh}')
