#!/usr/bin/env python
# coding=utf-8
#
# Copyright © Splunk, Inc. All Rights Reserved.

from __future__ import absolute_import, division, print_function, unicode_literals
import sys

from slim.app import AppDependencyGraph, AppSource
from slim.command import SlimArgumentParser
from slim.utils import SlimLogger, encode_filename, slim_configuration, typing

if typing is not None:
    # pylint: disable=unused-import
    from slim.utils import string
    import argparse


def argument_parser():
    # type: () -> SlimArgumentParser

    _parser = SlimArgumentParser(
        description='describe an app and its dependencies',
        epilog='This command assumes the app.manifest file is located at the root of the app source directory.'
    )

    _parser.add_app_source()
    _parser.add_argument_help()
    _parser.add_repository()
    _parser.add_output_file(description='output of this command')

    return _parser


# Suppresses JetBrains warnings about argparse.Namespace having no attributes
# noinspection PyUnresolvedReferences
def main(args):
    # type: (argparse.Namespace) -> None

    source = args.source

    with args.output as output:
        SlimLogger.step('Describing ' + encode_filename(source) + '...')
        app_source = AppSource(source)
        SlimLogger.exit_on_error()
        app_source.print_description(output)
        app_dependency_graph = AppDependencyGraph(app_source, args.repository)
        SlimLogger.exit_on_error()
        app_dependency_graph.print_description(output)


# pylint: disable=redefined-outer-name
def describe(source, app_only):
    # type: (string, string, bool) -> dict

    app_source = AppSource(source)
    SlimLogger.exit_on_error()

    payload = slim_configuration.payload
    description = app_source.description
    SlimLogger.exit_on_error()

    value = description['info']
    if value:
        payload.set_info(value)

    value = description['dependencies']
    if value:
        payload.set_dependencies(value)

    value = description['input_groups']
    if value:
        payload.set_input_groups(value)

    value = description['supported_deployments']
    if value:
        payload.set_supported_deployments(value)

    value = description['schema_version']
    if value:
        payload.set_schema_version(value)

    value = description['generated']
    if value:
        payload.set_generated(value)

    if not app_only:
        # TODO: Dnoble: SPL-130764: measure the cost of constructing the dependency graph and then look at caching it
        # like AppSource
        # Possibility: Add AppSource.dependency_graph property and compute the property on demand
        # We could then also cache the AppDependencyGraph.description
        app_dependency_graph = AppDependencyGraph(app_source, slim_configuration.repository_path)
        SlimLogger.exit_on_error()
        slim_configuration.payload.set_dependency_graph(app_dependency_graph.description)

    return description


parser = argument_parser()

if __name__ == '__main__':
    # noinspection PyBroadException
    try:
        main(parser.parse_args(sys.argv[1:]))
    except SystemExit:
        raise
    except:
        SlimLogger.fatal(exception_info=sys.exc_info())
