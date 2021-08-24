#!/usr/bin/env python
# coding=utf-8
#
# Copyright © Splunk, Inc. All Rights Reserved.

from __future__ import absolute_import, division, print_function, unicode_literals

from os import path
import sys

from slim.utils import SlimLogger, encode_filename, SlimUnreferencedInputGroups, slim_configuration
from slim.app import AppSource, AppDependencyGraph
from slim.command import SlimArgumentParser

# Argument parser definition

parser = SlimArgumentParser(
    description='make an app source package for distribution',
    epilog='This command assumes the app.manifest file is located at the root of the app source directory.'
)

parser.add_app_directory()
parser.add_argument_help()
parser.add_output_directory(description='app source package')
parser.add_repository()
parser.add_unreferenced_input_groups()


def main(args):
    package(args.source, args.output_dir, args.repository, args.unreferenced_input_groups)


def package(source, output_dir, repository=None, unreferenced_input_groups=SlimUnreferencedInputGroups.note):

    SlimLogger.step('Packaging app at ' + encode_filename(source))

    # Default repository is set on slim_configuration
    if repository is None:
        repository = slim_configuration.repository_path

    if path.commonprefix([output_dir, source]) == source:
        SlimLogger.error(
            'Output directory cannot be under the source directory because this contaminates the source package')
        SlimLogger.exit_on_error()

    # Create the AppSource for this app directory
    app_source = AppSource(source)
    SlimLogger.exit_on_error()

    # Create the dependency graph and validate it
    app_dependency_graph = AppDependencyGraph(app_source, repository)
    SlimLogger.exit_on_error()

    # Report unreferenced input groups (and exit on error)
    app_dependency_graph.report_unreferenced_input_groups(unreferenced_input_groups)
    SlimLogger.exit_on_error()

    # Package the app source
    source_package = app_dependency_graph.export_source_package(output_dir)
    SlimLogger.exit_on_error()

    SlimLogger.information('Source package exported to ', encode_filename(source_package))


if __name__ == '__main__':
    # noinspection PyBroadException
    try:
        main(parser.parse_args(sys.argv[1:]))
    except SystemExit:
        raise
    except:
        SlimLogger.fatal(exception_info=sys.exc_info())
