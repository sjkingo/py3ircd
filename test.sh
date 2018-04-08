#!/bin/bash

py3ircd/main.py &
server=$!
sleep 1

echo -n -e 'NICK test1\r\nUSER test1 test1 localhost :Test 1\r\nJOIN #foo\r\n' | nc localhost 6667 >/dev/null &

sleep 1
pkill nc
kill $server
