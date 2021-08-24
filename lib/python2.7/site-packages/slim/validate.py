#!/usr/bin/env python
# coding=utf-8
#
# Copyright © Splunk, Inc. All Rights Reserved.

from __future__ import absolute_import, division, print_function, unicode_literals

import sys

from slim.utils import *
from slim.app import *
from slim.command import *


# Argument parser definition

parser = SlimArgumentParser(
    description='verify an app and its dependencies',
    epilog='This command assumes the app.manifest file is located within the app source directory.'
)

parser.add_app_source()
parser.add_argument_help()
parser.add_repository()
parser.add_unreferenced_input_groups()


def main(args):
    validate(args.source, args.repository, args.unreferenced_input_groups)


def validate(source, repository=None, unreferenced_input_groups='note', app_only=False):

    SlimLogger.step('Validating app at ' + encode_filename(source) + '...')

    # Default repository is set on slim_configuration
    if repository is None:
        repository = slim_configuration.repository_path

    # Load the app source form either a directory or tarball
    app_source = AppSource(source)
    SlimLogger.exit_on_error()

    # Only validate the AppSource, not the dependencies
    if not app_only:

        # Create/validate the dependency graph and validate it
        app_dependency_graph = AppDependencyGraph(app_source, repository)
        SlimLogger.exit_on_error()

        # Report/validate input forwarder groups
        app_dependency_graph.report_unreferenced_input_groups(unreferenced_input_groups)
        SlimLogger.exit_on_error()

    SlimLogger.information('App validation complete')


if __name__ == '__main__':
    # noinspection PyBroadException
    try:
        main(parser.parse_args(sys.argv[1:]))
    except SystemExit:
        raise
    except:
        SlimLogger.fatal(exception_info=sys.exc_info())
