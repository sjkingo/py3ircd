
def cap(client, subcmd, *args):
    """
    CAP LS | LIST | REQ :<cap> .. | ACK | NAK | END
    https://ircv3.net/specs/core/capability-negotiation-3.1.html#the-cap-command
    ircv3
    """
    pass

def nick(client, nick, *ignore):
    """
    NICK <nickname> [ <hopcount> ]
    https://tools.ietf.org/html/rfc1459#section-4.1.2
    """
    client.nick = nick

def user(client, username, ignore1, ignore2, realname):
    """
    USER <username> <hostname> <servername> <realname>
    https://tools.ietf.org/html/rfc1459#section-4.1.3
    """
    pass
