"""
IRC protocol module. This handles client connections using asyncio
and delegates all activity to the `irc.IRCServer` class that is global
here.
"""

import asyncio
import logging
logging.getLogger('asyncio').setLevel(logging.WARNING)

from irc import Server, TERMINATOR
server = Server()

class IRCClientProtocol(asyncio.Protocol):
    """
    Client protocol class that delegates to the server instance.
    """

    def connection_made(self, transport):
        self.transport = transport
        self.client = server.new_connection(transport)

    def data_received(self, data):
        message = data.decode().rstrip(TERMINATOR)
        server.parse_incoming_line(self.transport, message)

def run_server(host='0.0.0.0', port=6667):
    """
    The main loop for the server.
    """

    loop = asyncio.get_event_loop()
    c = loop.create_server(IRCClientProtocol, host, port)
    net = loop.run_until_complete(c)

    try:
        loop.run_forever()
    except KeyboardInterrupt:
        pass

    net.close()
    loop.run_until_complete(net.wait_closed())
    loop.close()
