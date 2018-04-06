#!/bin/bash

./main.py &
server=$!
sleep 1

echo -n -e 'testing1\r\n' | nc localhost 6667 >/dev/null &
echo -n -e 'testing2\r\n' | nc localhost 6667 >/dev/null &

sleep 1
pkill nc
kill $server
