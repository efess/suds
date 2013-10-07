###
# This file is part of Soap.
#
# Soap is free software; you can redistribute it and/or modify it under the
# terms of the GNU General Public License as published by the Free Software
# Foundation, version 2.
#
# Soap is distributed in the hope that it will be useful, but WITHOUT ANY
# WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR
# A PARTICULAR PURPOSE.
#
# See the GNU General Public License for more details. You should have received
# a copy of the GNU General Public License along with Soap. If not, see
# <http://www.gnu.org/licenses/>.
###

import supybot.conf as conf
import supybot.ircdb as ircdb
import supybot.ircmsgs as ircmsgs
import supybot.ircutils as ircutils

import logging
import logging.handlers
import os.path
import re
import urllib2

from enums import *

def checkPermission(irc, msg, channel, allowOps):
    capable = ircdb.checkCapability(msg.prefix, 'trusted')
    if capable:
        return True
    else:
        opped = msg.nick in irc.state.channels[channel].ops
        if opped and allowOps:
            return True
        else:
            return False

def disconnect(conn, forced):
    if forced:
        conn.force_disconnect()
    else:
        conn.disconnect()

def generateDownloadUrl(irc, version, osType = None):
    stable = '\d\.\d\.\d'
    trunk = 'r\d{5}'

    if osType == None:
        actionChar = conf.get(conf.supybot.reply.whenAddressedBy.chars)
        irc.reply('%sdownload autostart|autottd|lin|lin64|osx|ottdau|source|win32|win64|win9x'
            % actionChar)
        url = 'http://www.openttd.org/en/'
        if re.match(stable, version):
            url += 'download-stable/%s' % version
        elif re.match(trunk, version):
            url += 'download-trunk/%s' % version
        else:
            url = None
    else:
        url = 'http://binaries.openttd.org/'
        if re.match(stable, version):
            url += 'releases/%s/openttd-%s-' % (version, version)
        elif re.match(trunk, version):
            url += 'nightlies/trunk/%s/openttd-trunk-%s-' % (version, version)
        else:
            url = None
        if not url == None:
            if osType.startswith('lin'):
                url += 'linux-generic-'
                if osType == 'lin':
                    url += 'i686.tar.xz'
                elif osType == 'lin64':
                    url += 'amd64.tar.xz'
                else:
                    url = None
            elif osType == 'osx':
                url += 'macosx-universal.zip'
            elif osType == 'source':
                url += 'source.tar.xz'
            elif osType.startswith('win'):
                url += 'windows-%s.zip' % osType
            else:
                url = None
    return url

def getConnection(connections, channels, source, serverID = None):
    conn = None

    if serverID == None:
        if ircutils.isChannel(source) and source in channels:
            conn = connections.get(source)
    else:
        if ircutils.isChannel(serverID):
            conn = connections.get(serverID)
        else:
            for c in connections.itervalues():
                if c.ID.lower() == serverID.lower():
                    conn = c
    return conn

def initLogger(conn, logdir):
    if os.path.isdir(logdir):
        if not len(conn.logger.handlers):
            logfile = os.path.join(logdir, '%s.log' % conn.channel)
            logformat = logging.Formatter('%(asctime)s %(message)s')
            handler = logging.handlers.RotatingFileHandler(logfile, backupCount = 2)
            handler.setFormatter(logformat)
            conn.logger.addHandler(handler)

def logEvent(logger, message):
    try:
        logger.info(message)
    except AttributeError:
        pass

def msgChannel(irc, channel, msg):
    if channel in irc.state.channels or irc.isNick(channel):
        irc.queueMsg(ircmsgs.privmsg(channel, msg))

def moveToSpectators(irc, conn, client):
    text = '%s: Please change your name before joining/starting a company' % client.name
    command = 'move %s 255' % client.id

    conn.send_packet(AdminRcon, command = command)
    conn.send_packet(AdminChat,
        action = Action.CHAT,
        destType = DestType.BROADCAST,
        clientID = ClientID.SERVER,
        message = text)
    msgChannel(irc, conn.channel, text)

def refreshConnection(connections, registeredConnections, conn):
    try:
        del registeredConnections[conn.filenumber]
    except KeyError:
        pass
    newconn = conn.copy()
    connections[conn.channel] = newconn
    return newconn