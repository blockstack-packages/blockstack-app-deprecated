#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
    Blockstack-app
    ~~~~~
    copyright: (c) 2014-2015 by Halfmoon Labs, Inc.
    copyright: (c) 2016 by Blockstack.org

    This file is part of Blockstack-app.

    Blockstack-app is free software: you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation, either version 3 of the License, or
    (at your option) any later version.

    Blockstack-app is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU General Public License for more details.
    You should have received a copy of the GNU General Public License
    along with Blockstack-app. If not, see <http://www.gnu.org/licenses/>.
"""

import os
import sys
import tempfile
import argparse
import socket
import json
import traceback

from ConfigParser import SafeConfigParser
from .version import __version__

import blockstack_client

log = blockstack_client.get_logger()

if os.environ.get("BLOCKSTACK_TEST", "") == "1":
    # testing!
    APP_CONFIG_PATH = os.environ.get("BLOCKSTACK_APP_CONFIG", None)
    assert APP_CONFIG_PATH is not None

    APP_CONFIG_DIR = os.path.dirname( APP_CONFIG_PATH )

else:
    APP_CONFIG_DIR = os.path.expanduser("~/.blockstack-app")
    APP_CONFIG_PATH = os.path.join( APP_CONFIG_DIR, "blockstack-app.ini" )

CACHE_DIRNAME = "blockstack-app-cache"

CONFIG_FIELDS = [
    'wallet',
    'blockchain_id',
    'hostname',
    'port',
    'rpc_port'
]

PORT = 6328

def get_config( config_path=APP_CONFIG_PATH ):
    """
    Get the config
    """
   
    parser = SafeConfigParser()
    parser.read( config_path )

    config_dir = os.path.dirname(config_path)

    wallet = None
    blockchain_id = None
    port = PORT
    hostname = socket.gethostname()
 
    if parser.has_section('blockstack-app'):

        if parser.has_option('blockstack-app', 'wallet'):
            wallet = parser.get('blockstack-app', 'wallet')

        if parser.has_option('blockstack-app', 'blockchain_id'):
            blockchain_id = parser.get('blockstack-app', 'blockchain_id')

        if parser.has_option('blockstack-app', 'hostname'):
            hostname = parser.get('blockstack-app', 'hostname')
            
        if parser.has_option('blockstack-app', 'port'):
            port = int(parser.get('blockstack-app', 'port'))
        
    config = {
        'wallet': wallet,
        'blockchain_id': blockchain_id,
        'hostname': hostname,
        'port': port,
        'path': config_path,
        'cache': os.path.join( config_dir, CACHE_DIRNAME )
    }

    if not os.path.exists( config['cache'] ):
        os.makedirs(config['cache'], 0700)

    return config

