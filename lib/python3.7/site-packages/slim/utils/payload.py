#!/usr/bin/env python
# coding=utf-8
#
# Copyright © Splunk, Inc. All Rights Reserved.

from __future__ import absolute_import, division, print_function, unicode_literals

from builtins import object
from collections import OrderedDict

import logging

__all__ = ['SlimPayload', 'SlimPayloadLoggingHandler']


# pylint: disable=too-many-public-methods

class SlimPayload(object):

    def __init__(self):

        self._status = None
        self._messages = None
        self._specific_payload = None

        self.reset()

    # TODO: This is an odd property name in that it causes code like this to be written: ordered_dict = payload.payload
    # Track down the use cases for this and devise something better.

    @property
    def payload(self):
        final_payload = OrderedDict((
            ('status', self._status),
            ('messages', self._messages)
        ))
        final_payload.update(self._specific_payload)
        return final_payload

    def set_info(self, info):
        if 'manifest' not in self._specific_payload:
            self._specific_payload['manifest'] = OrderedDict()
        self._specific_payload['manifest']['info'] = info

    def set_dependencies(self, dependencies):
        if 'manifest' not in self._specific_payload:
            self._specific_payload['manifest'] = OrderedDict()
        self._specific_payload['manifest']['dependencies'] = dependencies

    def set_input_groups(self, input_groups):
        if 'manifest' not in self._specific_payload:
            self._specific_payload['manifest'] = OrderedDict()
        self._specific_payload['manifest']['input_groups'] = input_groups

    def set_dependency_graph(self, dependency_graph):
        self._specific_payload['dependency_graph'] = dependency_graph

    def set_supported_deployments(self, supported_deployments):
        self._specific_payload.setdefault('manifest', OrderedDict())['supported_deployments'] = supported_deployments

    def set_schema_version(self, schema_version):
        self._specific_payload.setdefault('manifest', OrderedDict())['schema_version'] = schema_version

    def set_generated(self, generated):
        self._specific_payload.setdefault('manifest', OrderedDict())['generated'] = generated

    def add_message(self, level, text):
        if text is None:
            return
        if level not in self._messages:
            self._messages[level] = []
        self._messages[level].append(text)

    def set_source_package(self, filename):
        self._specific_payload['source_package'] = filename

    @property
    def status(self):
        return self._status

    @status.setter
    def status(self, value):
        self._status = value

    def add_missing_dependency(self, app_id):
        if 'missing_dependencies' not in self._specific_payload:
            self._specific_payload['missing_dependencies'] = []
        self._specific_payload['missing_dependencies'].append(app_id)

    def add_missing_optional_dependency(self, app_id):
        if 'missing_optional_dependencies' not in self._specific_payload:
            self._specific_payload['missing_optional_dependencies'] = []
        self._specific_payload['missing_optional_dependencies'].append(app_id)

    def set_dependency_requirements(self, app_ids):
        self._specific_payload['required_apps'] = app_ids

    def add_installation_action(self, step):
        if 'installation_actions' not in self._specific_payload:
            self._specific_payload['installation_actions'] = []
        self._specific_payload['installation_actions'].append(step)

    @property
    def installation_actions(self):
        if 'installation_actions' not in self._specific_payload:
            return None
        return self._specific_payload['installation_actions']

    def set_installation_graph(self, graph):
        self._specific_payload['installation_graph'] = graph

    @property
    def installation_graph(self):
        if 'installation_graph' not in self._specific_payload:
            return None
        return self._specific_payload['installation_graph']

    def add_graph_update(self, server_class, updates):
        if 'installation_graph_updates' not in self._specific_payload:
            self._specific_payload['installation_graph_updates'] = OrderedDict()
        self._specific_payload['installation_graph_updates'][server_class] = updates

    @property
    def graph_updates(self):
        if 'installation_graph_updates' not in self._specific_payload:
            return None
        return self._specific_payload['installation_graph_updates']

    def reset(self):
        self._status = 0
        self._messages = OrderedDict()
        self._specific_payload = OrderedDict()


class SlimPayloadLoggingHandler(logging.Handler):

    def __init__(self, payload=None):
        logging.Handler.__init__(self)
        if payload is None:
            payload = SlimPayload()
        if not isinstance(payload, SlimPayload):
            raise TypeError('Expected payload of type SlimPayload, not ' + type(payload).__name__)
        self._payload = payload
        self._paths = []

    @property
    def payload(self):
        return self._payload

    @payload.setter
    def payload(self, value):
        if not isinstance(value, SlimPayload):
            raise TypeError('Expected payload of type SlimPayload, not ' + type(value).__name__)
        self.acquire()
        try:
            self._payload = value
        finally:
            self.release()

    def sanitize_messages(self, paths):
        self._paths = paths

    def emit(self, record):
        if record.message is None:
            return
        record.message = record.message.replace('"', '')
        for old, new in self._paths:
            record.message = record.message.replace(old, new)
        self._payload.add_message(logging.getLevelName(record.levelno), record.message)
