# coding=utf-8
#
# Copyright © Splunk, Inc. All Rights Reserved.

from __future__ import absolute_import, division, print_function, unicode_literals
from collections import namedtuple
from ... utils.internal import string


# noinspection PyClassHasNoInit
class FilePosition(namedtuple('FilePosition', ('file', 'line'))):
    __slots__ = ()  # no extra slots required for this derived type

    def __str__(self):
        return self.file + ', line ' + string(self.line)
