"""
This module stores the numeric reply and error codes.

Reference: https://www.alien.net.au/irc/irc2numerics.html
"""

# Numeric reply codes
RPL_WELCOME =               '001'
RPL_YOURHOST =              '002'
RPL_CREATED =               '003'
RPL_MYINFO =                '004'
RPL_LUSERCLIENT =           '251'
RPL_LUSERCHANNELS =         '254'
RPL_CHANNELMODEIS =         '324'
RPL_NAMREPLY =              '353'
RPL_ENDOFNAMES =            '366'

# Error codes
ERR_UNKNOWNCOMMAND =        '421'
ERR_NEEDSMOREPARAMS =       '461'
