#!/usr/bin/env python
# coding=utf-8
#
# Copyright © Splunk, Inc. All Rights Reserved.

from __future__ import absolute_import, division, print_function, unicode_literals
import sys

from slim.command import SlimArgumentParser
from slim.utils import SlimLogger
from slim import program, version


def main(argv=None):

    if argv is None:
        argv = sys.argv

    if len(argv) < 2:
        argument_parser.print_help()
        return

    args = argument_parser.parse_args(argv[1:])

    SlimLogger.set_command_name(args.command_name)
    args.invoke_command(args)


def new_argument_parser():

    from argparse import RawDescriptionHelpFormatter

    parser = SlimArgumentParser(
        prog=program, description='execute a packaging toolkit command',
        formatter_class=RawDescriptionHelpFormatter
    )

    parser.add_argument('-v', '--version', action='version', version=version)
    parser.add_argument_help()
    parser.add_argument('--debug', action='set_debug', help='save debugging information')
    parser.add_argument('--quiet', action='set_quiet', help='suppress all messages except error messages')

    command_parsers = parser.add_subparsers(title=program + ' commands')
    command_parsers.required = False

    for name, command_module in (
            ('config', __import__('slim.config', fromlist=['main', 'parser'])),
            ('describe', __import__('slim.describe', fromlist=['main', 'parser'])),
            ('generate-manifest', __import__('slim.generate_manifest', fromlist=['main', 'parser'])),
            ('package', __import__('slim.package', fromlist=['main', 'parser'])),
            ('partition', __import__('slim.partition', fromlist=['main', 'parser'])),
            ('validate', __import__('slim.validate', fromlist=['main', 'parser'])),
            ('update-installation', __import__('slim.update_installation', fromlist=['main', 'parser']))
    ):
        parent = command_module.parser
        prog = parser.prog + ' ' + name

        command_parser = command_parsers.add_parser(
            name, prog=prog, usage=parser.usage, conflict_handler=parser.conflict_handler,
            formatter_class=parser.formatter_class, fromfile_prefix_chars=parser.fromfile_prefix_chars,
            prefix_chars=parser.prefix_chars, parents=[parent], description=parent.description, epilog=parent.epilog,
            argument_default=parent.argument_default, help=parent.description, add_help=False
        )
        command_parser.set_defaults(command_name=command_parser.prog, invoke_command=command_module.main)

    return parser


argument_parser = new_argument_parser()

if __name__ == '__main__':
    main(sys.argv)
