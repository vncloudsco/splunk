#!/usr/bin/env python
# coding=utf-8
#
# Copyright © Splunk, Inc. All Rights Reserved.

from __future__ import absolute_import, division, print_function, unicode_literals

from os import path
import json
import sys

from slim.utils import *
from slim.app import *
from slim.command import *
from slim.utils import SlimInstallationGraphActions
from slim.app._internal.object_view import ObjectView


# Argument parser definition

parser = SlimArgumentParser(
    description='perform an update action on an installation graph',
    epilog='''Update action can be add, set, update, remove

--actions add --package <path>
--actions set --package <path>
--actions update --package <path>
--actions remove --id <package app id>

Additional add and set parameters:
  --combine-search-head-indexer-workloads <boolean>
  --deployment-packages
  --forwarder-workloads
''')

parser.add_argument_help()
parser.add_installation()
parser.add_output_directory(description='installation graph and deployment packages')
parser.add_repository()
parser.add_combine_search_head_indexer_workloads()
parser.add_forwarder_workloads()
parser.add_deployment_packages()
parser.add_target_os()

# Command-specific arguments

parser.add_argument(
    '-a', '--action', required=True,
    choices=SlimInstallationGraphActions,
    help='apply action to the given installation graph: add, set, update or remove')

parser.add_argument(
    '-p', '--package', type=string, default=None,
    help='location of an app source package',
    metavar='<app-source>')

# this option is intentionally undocumented, it shouldn't be used by the SLIM users
parser.add_argument(
    '--is-external',
    action='store_const', const=True, default=False)

parser.add_argument(
    '--id', type=string, default=None,
    help='package app id')

parser.add_argument(
    '--disable-automatic-resolution',
    action='store_const', const=True, default=False,
    help='do not automatically resolve dependency conflicts by updating installed versions')


def main(args):
    # translate args to action args
    if args.action in [SlimInstallationGraphActions.add,
                       SlimInstallationGraphActions.set,
                       SlimInstallationGraphActions.update]:
        actions_args = ObjectView((
            ('app_package', args.package),
            ('is_external', args.is_external),
            ('combine_search_head_indexer_workloads', args.combine_search_head_indexer_workloads),
            ('workloads', args.forwarder_workloads),
            ('deployment_packages', args.deployment_packages),
            ('target_os', args.target_os),
        ))
    elif args.action == SlimInstallationGraphActions.remove:
        if args.id is None:
            raise SlimArgumentError('The remove action requires and app id, use the --id parameter to set this.')
        actions_args = ObjectView((('app_id', args.id),))
    else:
        assert False  # strange, this should never happen

    # execute the action
    server_collection = _update_installation(
        args.installation,
        args.repository,
        [AppInstallationAction((('action', args.action), ('args', actions_args)))],
        args.target_os,
        args.disable_automatic_resolution
    )

    filename = path.join(args.output_dir, 'installation-update.json')
    server_collection.save(filename)
    SlimLogger.exit_on_error()
    SlimLogger.information('Saved updated installation graph to ', encode_filename(filename))


def update_installation(installation_graph, action_list, target_os, disable_automatic_resolution=False):

    if isinstance(installation_graph, dict):
        installation_graph = json.dumps(installation_graph)

    stream_type = SlimStringIOArgument(name="installation_graph.json")

    with stream_type(value=installation_graph) as istream:
        action_type = SlimInstallationActionArgument()
        actions = []
        for action in action_list:
            action_item = action_type(value=json.dumps(action))
            workloads = action.get('args', {}).get('workloads')
            if workloads:
                # "adjust" args.workloads making it compatible with _update_installation
                # pylint: disable=no-member
                action_item.args.workloads = AppDeploymentSpecification.from_forwarder_workloads(workloads)
                # pylint: enable=no-member
            actions.append(action_item)

        server_collection = _update_installation(
            istream, slim_configuration.repository_path, actions, target_os, disable_automatic_resolution
        )

    # Save the installation graph to the payload only (not file output)
    server_collection.save(None)
    SlimLogger.exit_on_error()


# pylint: disable=redefined-builtin
def _update_installation(file, repository, actions, target_os, disable_automatic_resolution):

    SlimLogger.step('Updating installation graph at ', encode_filename(file.name))

    server_collection = AppServerClassCollection.load(file, repository)
    SlimLogger.exit_on_error()

    # Disable installation graph update validation until all actions have been complete
    server_collection.validate = False

    for action in actions:
        server_collection.update_installation(action, target_os, disable_automatic_resolution)
        SlimLogger.exit_on_error()

    # Enable installation graph validation again, and trigger a reload
    server_collection.validate = True
    server_collection.reload()
    SlimLogger.exit_on_error()

    return server_collection


if __name__ == '__main__':
    # noinspection PyBroadException
    try:
        main(parser.parse_args(sys.argv[1:]))
    except SystemExit:
        raise
    except:
        SlimLogger.fatal(exception_info=sys.exc_info())
