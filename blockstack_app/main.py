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
import socket
import mimetypes
import argparse

from .loader import app_load, app_publish
from .version import __version__
from .config import PORT

import SimpleHTTPServer
import SocketServer

import blockstack_client
import blockstack_file

log = blockstack_client.get_logger()

# globals set from config 
appdir = None
client_port = None

class AppRequestHandler( SimpleHTTPServer.SimpleHTTPRequestHandler ):

    def send_response_ram( self, msg, mimetype ):
        self.send_header("Content-length", str(len(msg)))
        self.send_header('Content-type', mimetype)
        self.end_headers()
        self.wfile.write(msg)


    def do_404(self):
        msg = "No such file or directory"
        self.send_response(404)
        self.send_response_ram( msg, "text/plain")
        return

        
    def do_GET(self):
        """
        Handle a GET request on the app
        """
        global client_port
        global appdir

        if self.path == '/blockstack_port':
            self.send_response(200)
            self.send_response_ram( str(client_port), "text/plain" )
            return 

        if self.path.strip("/") == "":
            # this is a request for index.html
            self.path = "/index.html"

        fp = os.path.realpath( os.path.join(appdir, self.path.strip("/")) )
        if not fp.startswith(appdir) or not os.path.exists(fp):
            self.do_404()
            return

        sb = os.stat(fp)
        size = sb.st_size
        mimetype, _ = mimetypes.guess_type( fp )
        if mimetype is None:
            self.do_404()
            return

        # serve data 
        self.send_response(200)
        self.send_header("Content-length", str(size))
        self.send_header("Content-type", mimetype)
        self.end_headers()

        with open(fp, "r") as f:
            while True:
                buf = f.read(65536)
                if len(buf) == 0:
                    break

                self.wfile.write(buf)

        return


def main(conf, function, args):
    """
    Fetch and serve the application
    """

    global appdir
    global client_port 

    wallet_keys = None
    client_config_path = os.path.join( os.path.dirname(conf['path']), blockstack_client.CONFIG_FILENAME )

    if function in ["run", "publish", "setup"]:
        # need wallet 
        wallet = blockstack_client.get_wallet( config_path=client_config_path )
        if wallet is None or 'error' in wallet:
            print >> sys.stderr, "Failed to get wallet"
            sys.exit(1)

        wallet_keys = wallet
    
    if function == "run":
        # run the app
        try:
            blockchain_id = args[0]
            appname = args[1]
        except:
            print >> sys.stderr, "Usage: %s-%s [opts] blockchain_id appname [tag [appdir]]" % (sys.argv[0], function)
            sys.exit(1)

        # optional arguments 
        tag = None
        appdir = None
        try:
            tag = int(args[2])
            appdir = args[3]
        except:
            pass

        # load the app 
        res = app_load(conf, blockchain_id, appname, wallet_keys=wallet_keys, tag=tag, appdir=appdir)
        if 'error' in res:
            print >> sys.stderr, "Failed to load app: %s" % res['error']
            sys.exit(1)

        client_conf = blockstack_client.get_config( client_config_path )
        client_port = client_conf.get('api_endpoint_port', None)
        if client_port is None:
            print >> sys.stderr, "Could not determine client RPC port"
            sys.exit(1)

        if appdir is None:
            appdir = res['root']

        httpd = SocketServer.TCPServer( ("localhost", conf['port']), AppRequestHandler)
        httpd.serve_forever()

        return {'status': True}

    elif function == "publish":
        # publish an app
        try:
            appname = args[0]
            appdir = args[1]
        except:
            print >> sys.stderr, "Usage: %s-%s [opts] appname appdir [tag [key_passphrase]]" % (sys.argv[0], function)
            sys.exit(1)

        # optional args
        tag = None
        key_passphrase = None
        try:
            tag = int(args[2])
            key_passphrase = args[3]
        except:
            pass
           
        # TODO: mutable vs immutable
        res = app_publish( conf, appname, appdir, wallet_keys=wallet_keys, version=tag, key_passphrase=key_passphrase )
        if 'error' in res:
            print >> sys.stderr, "Failed to publish app: %s" % res['error']
            sys.exit(1)

        return res

    elif function == 'setup':
        # set up app-publishing
        client_config_path = os.path.join( os.path.dirname(conf['path']), blockstack_client.CONFIG_FILENAME )
        res = blockstack_file.file_key_regenerate( conf['blockchain_id'], conf['hostname'], config_path=client_config_path, wallet_keys=wallet_keys ) 
        if 'error' in res:
            print >> sys.stderr, "Failed to publish app: %s" % res['error']
            sys.exit(1)

        return res

    else:
        print >> sys.stderr, "Unrecognized directive '%s'" % function
        sys.exit(1)

