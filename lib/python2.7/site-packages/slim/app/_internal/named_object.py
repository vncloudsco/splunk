# coding=utf-8
#
# Copyright © Splunk, Inc. All Rights Reserved.

from __future__ import absolute_import, division, print_function, unicode_literals

from functools import total_ordering

from builtins import object


@total_ordering
class NamedObject(object):
    __slots__ = ('_name',)

    def __init__(self, name):
        self._name = name

    def __eq__(self, other):
        return self._name == other.name()

    def __lt__(self, other):
        return self._name < other.name()

    def __hash__(self):
        return self._name.__hash__()

    @property
    def name(self):
        return self._name
