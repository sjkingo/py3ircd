"""
IRC protocol module. This handles client connections using asyncio
and delegates all activity to the `irc.IRCServer` class that is global
here. This exists to be easily swapped out with a different server
if required.
"""

import asyncio
import logging
logging.getLogger('asyncio').setLevel(logging.WARNING)

from irc import Server
server = Server()

class IRCClientProtocol(asyncio.Protocol):
    """
    Client protocol class that delegates to the server instance.
    """

    def connection_made(self, transport):
        self.transport = transport
        server.new_connection(transport)

    def data_received(self, data):
        lines = [l for l in data.decode().split('\r\n') if len(l) > 0]
        for line in lines:
            server.data_received(self.transport, line)

    def connection_lost(self, exc):
        server.connection_lost(self.transport, exc)

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
