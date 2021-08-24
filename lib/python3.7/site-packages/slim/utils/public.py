#!/usr/bin/env python
# coding=utf-8
#
# Copyright © Splunk, Inc. All Rights Reserved.

from __future__ import absolute_import, division, print_function, unicode_literals

from builtins import object
from collections import OrderedDict, namedtuple
from os import environ, path, makedirs
from tempfile import mkdtemp

import atexit
import errno
import shutil

from .. utils.internal import string


__all__ = [
    'SlimConstants',
    'SlimEnum',
    'SlimError',
    'SlimInstallationGraphActions',
    'SlimStatus',
    'SlimUnreferencedInputGroups'
]


class SlimEnum(tuple):
    __getattr__ = tuple.index


class SlimCacheInfo(object):

    def __init__(self, temp_directory_path):

        if not path.isdir(temp_directory_path):
            makedirs(temp_directory_path)

        cache_path = mkdtemp(prefix='slim.cache_', dir=temp_directory_path)
        self._cache_prefix = temp_directory_path
        self._cache_path = cache_path
        self._sources = OrderedDict()

        atexit.register(self.cleanup)

    @property
    def cache_path(self):
        return self._cache_path

    @property
    def cache_prefix(self):
        return self._cache_prefix

    @property
    def get_sources(self):
        return self._sources

    def add_source(self, package, app_source):
        self._sources[package] = app_source

    def reset(self):
        self._sources.clear()

    def cleanup(self):
        cache_path = self._cache_path
        try:
            shutil.rmtree(cache_path)
        except OSError as error:
            if error.errno != errno.ENOENT:
                raise


# Various status codes indicating the type of error
SlimStatus = SlimEnum([
    'STATUS_OK',
    'STATUS_ERROR_GENERAL',
    'STATUS_ERROR_CONFLICT',
    'STATUS_ERROR_RESOLVABLE_CONFLICT',
    'STATUS_ERROR_MISSING_DEPENDENCIES',
    'STATUS_ERROR_DEPENDENCY_REQUIRED'
])


SlimConstants = namedtuple('SlimConstants', ('DEPENDENCIES_DIR',))(
    DEPENDENCIES_DIR='.dependencies'
)


SlimUnreferencedInputGroups = namedtuple('SlimUnreferencedInputGroups', ('note', 'info', 'warn', 'error'))(
    note='note',  # kept for backwards compatibility
    info='info',  # default
    warn='warn',
    error='error'
)


SlimInstallationGraphActions = namedtuple('SlimInstallationGraphActions', ('add', 'set', 'update', 'remove'))(
    add='add',
    set='set',
    update='update',
    remove='remove'
)


SlimTargetOSWildcard = "*"


SlimTargetOS = [
    SlimTargetOSWildcard,
    "_mac",
    "_linux_x86",
    "_linux_x86_64",
    "_windows"
]


class SlimError(Exception):

    def __init__(self, *message):
        Exception.__init__(self, ''.join(message))


class SplunkInfo(object):

    def __init__(self):
        self._home = string(environ['SPLUNK_HOME'])
        self._etc = path.join(self._home, 'etc')
        self._bin = path.join(self._home, 'bin')

    @property
    def home(self):
        return self._home

    @property
    def bin(self):
        return self._bin

    @property
    def etc(self):
        return self._etc
