# coding=utf-8
#
# Copyright © Splunk, Inc. All Rights Reserved.

from __future__ import absolute_import, division, print_function, unicode_literals

from builtins import object
from os import path
from weakref import WeakValueDictionary

import errno

from . _configuration_spec import AppConfigurationPlacement, AppConfigurationSpec
from . _internal import OrderedSet
from .. utils import SlimLogger, encode_filename, slim_configuration


class AppConfigurationValidator(object):
    """ Constructs a context object for setting validation

        :param configuration: Configuration name (eg., 'app', 'inputs', 'etc')
        :type configuration: string

        :param app_root:
        :type app_root: string

    """
    # pylint: disable=protected-access
    # noinspection PyProtectedMember
    def __init__(self, configuration, app_root):
        cls = self.__class__
        try:
            configuration_spec = cls._configuration_specs[configuration]
        except KeyError:
            # Load spec from the filesystem, looking first on the configuration_spec_path, then on <app_root>/README
            configuration_spec_dirs = (slim_configuration.configuration_spec_path, path.join(app_root, 'README'))
            configuration_spec = AppConfigurationSpec(configuration, app_root)
            basename = configuration + '.conf.spec'
            count = 0

            for configuration_spec_dir in configuration_spec_dirs:
                filename = path.join(configuration_spec_dir, basename)
                try:
                    configuration_spec.load(filename)
                except (IOError, OSError) as error:
                    if error.errno not in (errno.ENOENT, errno.ENOTDIR):
                        SlimLogger.fatal('Could not load spec file ', encode_filename(filename), ': ', error.strerror)
                else:
                    count += 1

            if count == 0:
                SlimLogger.warning(
                    'Could not find ', basename, ' on configuration_spec_path:\n  ',
                    '\n  '.join(configuration_spec_dirs)
                )
                cls._configuration_specs[configuration] = configuration_spec = cls._NoConfigurationSpec
            else:
                cls._configuration_specs[configuration] = configuration_spec

        self._configuration_spec = configuration_spec

    # region Special methods

    def __enter__(self):
        return self

    # noinspection PyUnusedLocal
    def __exit__(self, exception_type, exception_value, traceback):
        self._configuration_spec = None
        return False

    # endregion

    # region Methods

    # pylint: disable=protected-access
    # noinspection PyProtectedMember
    def get(self, stanza):
        """ Gets a setting validation function for the named configuration stanza

        :param stanza:  App configuration stanza object.
        :type stanza: AppConfigurationStanza

        :return: A function for validating settings in the context of the given app configuration stanza.
        :rtype: function

        """
        cls = self.__class__

        if self._configuration_spec is cls._NoConfigurationSpec:
            return cls._validate

        if stanza.name == 'default':
            return self._default_stanza_validator()

        return self._non_default_stanza_validator(stanza)

    def get_placement(self, stanza):
        """ Gets the placement of the named configuration stanza

        :param stanza: Stanza name.
        :type stanza: string

        :return: Placement of the named configuration stanza
        :rtype: AppConfigurationPlacement

        """
        configuration_spec = self._configuration_spec
        cls = self.__class__

        if configuration_spec is not cls._NoConfigurationSpec:
            declarations = configuration_spec.match(stanza)
            if declarations is not None:
                placement = None
                for declaration in declarations:
                    placement = declaration.placement.union(placement)
                return placement

        return AppConfigurationPlacement.all_workloads

    # endregion

    # region Protected

    _configuration_specs = WeakValueDictionary()
    _NoConfigurationSpec = type(str('NoConfigurationSpec'), (), {})

    # TODO: Extract functions from common code segments in the following validation functions

    def _default_stanza_validator(self):
        """ Returns a validation function for the `[default]` stanza in the current configuration file.

        :return: A validation function for the `[default]` stanza in the current configuration file.
        :rtype: function

        """
        configuration_spec = self._configuration_spec

        def validate(setting):

            for stanza_declaration in configuration_spec.stanza_declarations():
                setting_declaration = stanza_declaration.match(setting)
                if setting_declaration is not None:
                    setting._placement = setting_declaration.placement
                    return True

            SlimLogger.warning(setting.position, ': Undefined setting in stanza [default]: ', setting.name)
            setting._placement = AppConfigurationPlacement.all_workloads
            return False

        return validate

    def _non_default_stanza_validator(self, stanza):
        """ Returns a validation function for the named configuration `stanza` in the current configuration file.

        :param stanza: App configuration stanza object
        :type stanza: AppConfigurationStanza

        :return: A validation function for the named `stanza` in the current configuration file.
        :rtype: function

        """
        configuration_spec = self._configuration_spec
        stanza_declarations = configuration_spec.match(stanza.name)

        if stanza_declarations is None:
            SlimLogger.warning(
                stanza.position, ': Setting validation is disabled for [', stanza.name.replace('\n', '\\n'), '] '
                'because there is no matching configuration spec')
            return AppConfigurationValidator._validate

        stanza_declarations = OrderedSet(stanza_declarations + configuration_spec.match('default'))

        def validate(setting):

            for stanza_declaration in stanza_declarations:
                setting_declaration = stanza_declaration.match(setting)
                if setting_declaration is not None:
                    setting._placement = setting_declaration.placement
                    return True

            SlimLogger.warning(
                setting.position, ': Undefined setting in ', configuration_spec.name, '.conf, stanza [',
                stanza.name.replace('\n', '\\n'), ']: ', setting.name)

            setting._placement = AppConfigurationPlacement.all_workloads
            return False

        return validate

    # pylint: disable=protected-access
    @staticmethod
    def _validate(setting):
        """ Validation function for configurations without spec files

        :return: const:`True`

        """
        setting._placement = AppConfigurationPlacement.all_workloads
        return True

    # endregion
