# coding=utf-8
#
# Copyright © Splunk, Inc. All Rights Reserved.

from __future__ import absolute_import, division, print_function, unicode_literals
from collections import MutableSet


class OrderedSet(MutableSet):

    def __init__(self, iterable=None):
        self._end = end = []
        end += [None, end, end]  # Sentinel node for doubly linked list
        self._map = {}           # key -> [key, prev, next]
        if iterable is None:
            return
        for item in iterable:
            if item in self._map:
                continue
            end = self._end
            curr = end[1]
            curr[2] = end[1] = self._map[item] = [item, curr, end]

    # region Special methods

    def __len__(self):
        return len(self._map)

    def __contains__(self, key):
        return key in self._map

    def __eq__(self, other):
        if isinstance(other, OrderedSet):
            return len(self) == len(other) and list(self) == list(other)
        return set(self) == set(other)

    def __getitem__(self, value):
        item = self._map[value]
        return item[0]

    def __iter__(self):
        end = self._end
        current = end[2]
        while current is not end:
            yield current[0]
            current = current[2]

    def __repr__(self):
        name = self.__class__.__name__
        return name + '()' if len(self._map) == 0 else name + '([' + ', '.join((repr(item) for item in self)) + '])'

    def __reversed__(self):
        end = self._end
        current = end[1]
        while current is not end:
            yield current[0]
            current = current[1]

    # endregion

    # region Methods

    def add(self, value):
        if value in self._map:
            return
        end = self._end
        current = end[1]
        current[2] = end[1] = self._map[value] = [value, current, end]

    def discard(self, value):
        try:
            value, previous_item, next_item = self._map[value]
        except KeyError:
            return
        previous_item[2] = next_item
        next_item[1] = previous_item
        del self._map[value]

    def get(self, key, default=None):
        try:
            return self[key]
        except KeyError:
            return default

    # endregion
