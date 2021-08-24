#!/usr/bin/env python
# coding=utf-8
#
# Copyright © Splunk, Inc. All Rights Reserved.

from __future__ import absolute_import, division, print_function, unicode_literals

from contextlib import contextmanager

from . public import SlimStatus
from . logger import SlimLogger
from . payload import SlimPayloadLoggingHandler
from . _configuration import slim_configuration

__all__ = ['slim_transaction']


@contextmanager
def slim_transaction():
    """
    Reset the SLIM context before we start a new transaction
    """
    payload_logging_handler = None

    try:
        # Update the SLIM logger for this transaction
        SlimLogger.reset_counts()

        # Add the SLIM payload object as a logging handler
        payload_logging_handler = SlimPayloadLoggingHandler(slim_configuration.payload)
        payload_logging_handler.sanitize_messages(paths=slim_configuration.sanitized_paths)
        payload_logging_handler.payload.reset()

        SlimLogger.add_handler(payload_logging_handler)

        yield  # execute code within the "with" statement

    except SystemExit:
        pass   # expected exception to known errors

    finally:
        # Set the status bit to failed if we logged any errors
        if SlimLogger.error_count() and not slim_configuration.payload.status:
            slim_configuration.payload.status = SlimStatus.STATUS_ERROR_GENERAL

        # Remove the payload logging handler (if added)
        if payload_logging_handler is not None:
            SlimLogger.remove_handler(payload_logging_handler)
