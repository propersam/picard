# -*- coding: utf-8 -*-
#
# Picard, the next-generation MusicBrainz tagger
# Copyright (C) 2007 Lukáš Lalinský
# Copyright (C) 2006 Matthias Friedrich
#
# This program is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License
# as published by the Free Software Foundation; either version 2
# of the License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301, USA.

import ctypes
import sys
from PyQt4 import QtCore
from picard.ui.cdlookup import CDLookupDialog


class DiscError(IOError):
    pass


class Disc(QtCore.QObject):

    def __init__(self):
        QtCore.QObject.__init__(self)
        self.id = None
        self.submission_url = None

    def read(self, device):
        libdiscid = _openLibrary()
        handle = libdiscid.discid_new()
        assert handle != 0, "libdiscid: discid_new() returned NULL"
        res = libdiscid.discid_read(handle, device)
        if res == 0:
            raise DiscError(libdiscid.discid_get_error_msg(handle))
        self.id = libdiscid.discid_get_id(handle)
        self.submission_url = libdiscid.discid_get_submission_url(handle)
        print self.submission_url
        libdiscid.discid_free(handle)

    def lookup(self):
        self.tagger.xmlws.find_releases(self._lookup_finished, discid=self.id)

    def _lookup_finished(self, document, http, error):
        self.tagger.restore_cursor()
        if error:
            self.log.error(unicode(http.errorString()))
            return
        try:
            dialog = CDLookupDialog(document.metadata[0].release_list[0].release, self)
            dialog.exec_()
        except (KeyError, IndexError):
            # FIXME report error
            pass


def _openLibrary():
    """Tries to open libdiscid.

    @return: a C{ctypes.CDLL} object, representing the opened library

    @raise NotImplementedError: if the library can't be opened
    """
    # This only works for ctypes >= 0.9.9.3. Any libdiscid is found,
    # no matter how it's called on this platform.
    try:
        if hasattr(ctypes.cdll, 'find'):
            libDiscId = ctypes.cdll.find('discid')
            _setPrototypes(libDiscId)
            return libDiscId
    except OSError, e:
        raise NotImplementedError(str(e))

    # For compatibility with ctypes < 0.9.9.3 try to figure out the library
    # name without the help of ctypes. We use cdll.LoadLibrary() below,
    # which isn't available for ctypes == 0.9.9.3.
    #
    if sys.platform == 'linux2':
        libName = 'libdiscid.so.0'
    elif sys.platform == 'darwin':
        libName = 'libdiscid.0.dylib'
    elif sys.platform == 'win32':
        libName = 'discid.dll'
    else:
        # This should at least work for Un*x-style operating systems
        libName = 'libdiscid.so.0'

    try:
        libDiscId = ctypes.cdll.LoadLibrary(libName)
        _setPrototypes(libDiscId)
        return libDiscId
    except OSError, e:
        raise NotImplementedError('Error opening library: ' + str(e))

    assert False # not reached


def _setPrototypes(libDiscId):
    ct = ctypes
    libDiscId.discid_new.argtypes = ( )

    libDiscId.discid_free.argtypes = (ct.c_int, )

    libDiscId.discid_read.argtypes = (ct.c_int, ct.c_char_p)

    libDiscId.discid_get_error_msg.argtypes = (ct.c_int, )
    libDiscId.discid_get_error_msg.restype = ct.c_char_p

    libDiscId.discid_get_id.argtypes = (ct.c_int, )
    libDiscId.discid_get_id.restype = ct.c_char_p

    libDiscId.discid_get_submission_url.argtypes = (ct.c_int, )
    libDiscId.discid_get_submission_url.restype = ct.c_char_p
