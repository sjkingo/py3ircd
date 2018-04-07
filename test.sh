#!/bin/bash

./main.py &
server=$!
sleep 1

echo -n -e 'CAP LS\r\nNICK test1\r\nUSER test1 test1 localhost :Test 1\r\nPING wren.sjkwi.com.au\r\nJOIN #foo\r\n' | nc localhost 6667 >/dev/null &

sleep 1
pkill nc
kill $server
