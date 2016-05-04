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
import shutil
import tempfile
import zipfile
import base64

import blockstack_client
import blockstack_file

from blockstack_client import CONFIG_PATH
from .config import APP_CONFIG_PATH, CACHE_DIRNAME

log = blockstack_client.get_logger()

APP_NAME = "app"

def app_fq_data_name( data_name ):
    """
    Make a fully-qualified data name
    """
    return "%s:%s" % (APP_NAME, data_name)


def app_is_fq_data_name( data_name ):
    """
    Is this a fully-qualified data name?
    """
    return data_name.startswith("%s:" % APP_NAME)


def app_data_name( fq_data_name ):
    """
    Get the relative name of this data from its fully-qualified name
    """
    assert app_is_fq_data_name( fq_data_name )
    return data_name[len("%s:" % APP_NAME):]


def app_list( blockchain_id, config_path=CONFIG_PATH, wallet_keys=None ):
    """
    List the set of applications served by this blockchain ID
    Return {'status': True, 'listing': listing} on success
    Return {'error': ...} on error
    """

    config_dir = os.path.dirname(config_path)
    client_config_path = os.path.join(config_dir, blockstack_client.CONFIG_FILENAME )
    proxy = blockstack_client.get_default_proxy( config_path=client_config_path )

    res = blockstack_client.data_list( blockchain_id, proxy=proxy, wallet_keys=wallet_keys )
    if 'error' in res:
        log.error("Failed to list data: %s" % res['error'])
        return {'error': 'Failed to list data'}

    listing = []

    # find the ones that this app put there 
    for rec in res['listing']:
        if not app_is_fq_data_name( rec['data_id'] ):
            continue
        
        listing.append( rec )

    return {'status': True, 'listing': listing}


def app_upload( sender_blockchain_id, hostname, app_name, app_dir, config_path=CONFIG_PATH, wallet_keys=None, version=None, passphrase=None ):
    """
    Publish an application.
    Return {'status': True, 'sender_key_id': ..., 'sig': ...} on success
    Return {'error': ...} on error
    """

    config_dir = os.path.dirname(config_path)
    cache_dir = os.path.join( config_dir, CACHE_DIRNAME )
    client_config_path = os.path.join(config_dir, blockstack_client.CONFIG_FILENAME )
    file_config_path = os.path.join(config_dir, blockstack_file.CONFIG_PATH )

    fd, path = tempfile.mkstemp( prefix="blockstack-app-upload-", dir=cache_dir )
    log.debug("Compress to %s" % path)

    old_dir = os.getcwd()

    # compress 
    try:
        ziph = zipfile.ZipFile( path, 'w', zipfile.ZIP_DEFLATED )
        
        os.chdir(app_dir)
        for root, dirs, files in os.walk("."):
            for f in files:
                ziph.write( os.path.join(root, f) )

        ziph.close()
    except Exception, e:
        log.exception(e)
        os.chdir(old_dir)
        return {'error': 'Failed to compress'}

    else:
        os.chdir(old_dir)
        
    # sign 
    res = blockstack_file.file_sign( sender_blockchain_id, hostname, path, config_path=client_config_path, passphrase=passphrase, wallet_keys=wallet_keys )
    if 'error' in res:
        log.error("Failed to sign %s: %s" % (path, res['error']))
        try:
            os.unlink(path)
        except:
            pass

        return {'error': 'Failed to sign'}
   
    # replicate 
    app_bin = None
    with open(path, "r") as f:
        app_bin = f.read()

    data = {
        'sender_key_id': res['sender_key_id'],
        'sig': res['sig'],
        'app': base64.b64encode( app_bin )
    }

    fq_data_name = app_fq_data_name( app_name )
    proxy = blockstack_client.get_default_proxy( config_path=client_config_path )
    res = blockstack_client.data_put( blockstack_client.make_mutable_data_url( sender_blockchain_id, fq_data_name, version ), data, wallet_keys=wallet_keys, proxy=proxy )
    if 'error' in res:
        log.error("Failed to upload app '%s': %s" % (fq_data_name, res['error']))
        return {'error': 'Failed to upload data'}

    return {'status': True, 'sender_key_id': data['sender_key_id'], 'sig': data['sig']}



def app_download( sender_blockchain_id, appname, config_path=CONFIG_PATH, wallet_keys=None, version=None, appdir=None ):
    """
    Fetch the application to a temporary location on disk.
    Verify that it was signed by its creator.
    Decompress the contents.
    Return {'status': True, 'root': path, 'tag': version or hash} on success
    Return {'error': ...} on error
    """
     
    config_dir = os.path.dirname(config_path)
    cache_dir = os.path.join( config_dir, CACHE_DIRNAME )
    client_config_path = os.path.join(config_dir, blockstack_client.CONFIG_FILENAME )
    file_config_path = os.path.join(config_dir, blockstack_file.CONFIG_PATH )

    proxy = blockstack_client.get_default_proxy( config_path=client_config_path )

    if appdir is None:
        appdir = tempfile.mkdtemp(dir=cache_dir)

    # get the app data
    fq_data_name = app_fq_data_name( appname ) 
    res = blockstack_client.data_get( blockstack_client.make_mutable_data_url( sender_blockchain_id, fq_data_name, version ), wallet_keys=wallet_keys, proxy=proxy )
    if 'error' in res:
        log.error("Failed to get data for %s: %s" % (fq_data_name, res['error']))
        return {'error': 'Failed to get app data'}

    tag = res.get('version', None)
    if tag is None:
        tag = res.get('hash', None)
        if tag is None:
            log.error("Missing version or hash")
            return {'error': "Missing version or hash"}
    
    # stash
    fd, path = tempfile.mkstemp( prefix="blockstack-app-download-", dir=cache_dir )
    log.debug("Stash app data to %s" % path)
    f = os.fdopen(fd, "w")
    f.write( base64.b64decode(res['data']['app']) )
    f.flush()
    os.fsync(f.fileno())
    f.close()

    sender_key_id = res['data']['sender_key_id']
    sig = res['data']['sig']

    # verify it
    res = blockstack_file.file_verify( sender_blockchain_id, sender_key_id, path, sig, config_path=client_config_path, wallet_keys=wallet_keys )
    if 'error' in res:
        log.error("Failed to verify: %s" % res['error'])
        return {'error': 'Failed to verify app data'}

    # decompress it 
    try:
        ziph = zipfile.ZipFile( path, 'r', zipfile.ZIP_DEFLATED )
        ziph.extractall( path=appdir )
        ziph.close()

        log.debug("Extracted app to '%s'" % appdir)

    except zipfile.BadZipfile:
        log.error("Bad zipfile")
        return {'error': 'Bad zipfile'}
    except Exception, e:
        log.exception(e)
        return {'error': 'Failed to extract'}

    try:
        os.unlink(path)
    except:
        pass

    return {'status': True, 'root': path, 'tag': tag}
     

def app_load( config, sender_blockchain_id, appname, wallet_keys=None, tag=None, appdir=None ):
    """
    Load up an application.
    Re-download it if we don't know or have the version.
    Return {'status': True, 'root': ...} on success
    Return {'error': ...} on error
    """

    # check if available offline
    if appdir is not None:
        blockstack_dir = os.path.join( appdir, ".blockstack-app-%s-%s" % (sender_blockchain_id, appname) )
        if os.path.exists( blockstack_dir ):
            tag_path = os.path.join(blockstack_dir, 'tag')
            if os.path.exists(tag_path):
                local_tag = None
                try:
                    with open(tag_path, "r") as f:
                        tag_str = f.read().strip()
                        local_tag = int(tag_str)

                except:
                    pass

                if local_tag is not None and local_tag == tag:
                    # already have it!
                    log.debug("App '%s' tag %s is already loaded at %s" % (appname, tag, appdir))
                    return {'status': True, 'root': appdir}


    # not available offline.  Go get it.
    config_path = config['path']
    config_dir = os.path.dirname(config_path)
    cache_dir = os.path.join( config_dir, CACHE_DIRNAME )

    log.debug("App '%s' is not cached, downloading..." % appname)
    if appdir is None:
        offline_dir = os.path.join( cache_dir, "%s/%s" % (sender_blockchain_id, appname) )
        if os.path.exists(offline_dir):
            shutil.rmtree(offline_dir)

        os.makedirs( offline_dir )
        appdir = offline_dir

    appdata = app_download( sender_blockchain_id, appname, config_path=config['path'], wallet_keys=wallet_keys, version=tag, appdir=appdir )
    if 'error' in appdata:
        log.error("Failed to download '%s' from %s" % (appname, sender_blockchain_id))
        if tempdir:
            shutil.rmtree(appdir)

        return {'error': 'Failed to download data'}

    # store some metadata 
    metadata_dir = os.path.join( appdir, ".blockstack-app-%s-%s" % (sender_blockchain_id, appname))
    os.makedirs( metadata_dir )

    tag = appdata['tag']
    tagpath = os.path.join(metadata_dir, "tag")
    with open( tagpath, "w" ) as f:
        f.write(str(tag))
        f.flush()
        os.fsync(f.fileno())

    return {'status': True, 'root': appdir}


def app_publish( config, appname, appdir, wallet_keys=None, version=None, key_passphrase=None ):
    """
    Publish an application for others to use
    Return {'status': True} on success
    Return {'error': ...} on error
    """

    config_path = config['path']
    blockchain_id = config['blockchain_id']
    hostname = config['hostname']

    res = app_upload( blockchain_id, hostname, appname, appdir, config_path=config_path, wallet_keys=wallet_keys, version=version, passphrase=key_passphrase )
    if 'error' in res:
        log.error("Failed to upload app '%s': %s" % (appname, res['error']))
        return {'error': 'Failed to upload app'}

    return {'status': True}



