# coding=utf-8
#
# Copyright © Splunk, Inc. All Rights Reserved.

from __future__ import absolute_import, division, print_function, unicode_literals

from builtins import object
from abc import abstractmethod, ABCMeta as AbstractMetaClass
from future.utils import with_metaclass

__all__ = ['PackagingRule', 'DefaultPackagingRule', 'InputsPackagingRule']


class PackagingRule(with_metaclass(AbstractMetaClass, object)):
    """
    This is the extension point for future packaging rules

    """

    @abstractmethod
    def should_include_setting(self, stanza, setting, deployment_specification, app_manifest):
        pass

    @abstractmethod
    def should_include_stanza(self, stanza, settings, deployment_specification, app_manifest):
        pass

    @classmethod
    def instance(cls):
        instance = cls.__dict__.get('_instance')
        if instance is None:
            instance = cls._instance = cls()  # pylint: disable=abstract-class-instantiated
        return instance


class DefaultPackagingRule(PackagingRule):

    # noinspection PyMethodMayBeStatic
    def should_include_setting(self, stanza, setting, deployment_specification, app_manifest):
        return setting.placement.is_overlapping(deployment_specification.workload)

    # noinspection PyMethodMayBeStatic
    def should_include_stanza(self, stanza, settings, deployment_specification, app_manifest):
        if len(settings) > 0:
            return True
        return stanza.placement.is_overlapping(deployment_specification.workload)


class InputsPackagingRule(DefaultPackagingRule):

    def should_include_setting(self, stanza, setting, deployment_specification, app_manifest):
        return self._should_include_stanza(stanza, deployment_specification, app_manifest)

    def should_include_stanza(self, stanza, settings, deployment_specification, app_manifest):
        if len(settings) > 0:
            return True
        if stanza.name == 'default':
            return False
        return self._should_include_stanza(stanza, deployment_specification, app_manifest)

    @staticmethod
    def _should_include_stanza(stanza, deployment_specification, app_manifest):

        tasks = app_manifest.tasks

        if tasks and 'searchHead' in deployment_specification.workload:
            if stanza.name == 'default' or stanza.name in tasks:
                return True

        if 'forwarder' in deployment_specification.workload:

            if stanza.name == 'default':
                return True

            if not (tasks and stanza.name in tasks):
                names = deployment_specification.inputGroups

                if deployment_specification.is_all_input_groups(names):
                    return True

                input_groups = app_manifest.inputGroups

                for name in names:
                    info = getattr(input_groups, name, None)
                    if info is None:
                        continue
                    if stanza.name in info.inputs:
                        return True

        return False
