""" 
Container for the logging module default-created log output handlers.
This exists solely as a workaround for the cli's main module being far too
large.

In order to conditionally switch off logging writing to stdout later, we need to
remember the handler objects (a requirement of the logging module).  However, we
can't store them within cli.py, since it's operating as the main module.

If another module imports cli.py (during the import of that module by cli.py!)
it will get a different instantiation of the module object, and won't get a copy
of any stored values there.

As a workaround we just use this module as a common point of access for these
items.
"""
log_handlers = {}

def add(name, handler):
    log_handlers[name] = handler

def get(name):
    return log_handlers.get(name)

def remove(name):
    del log_handlers[name]
