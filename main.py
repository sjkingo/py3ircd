#!/usr/bin/env python3

import logging
logging.basicConfig(level=logging.DEBUG)

from server import run_server

def main():
    run_server()


if __name__ == '__main__':
    main()
