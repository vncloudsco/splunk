from builtins import object
class MockMethod(object):
    def __init__(self, module, name, result=None, exception=None):
        self.module = module
        self.name = name
        self.method = getattr(module, name)
        self.result = result
        self.exception = exception
        self.args = None
        self.kwargs = None
        self.called = False

    def call(self, *args, **kwargs):
        self.called = True
        self.args = args
        self.kwargs = kwargs
        if self.exception is not None:
            raise self.exception
        return self.result

    def install(self):
        setattr(self.module, self.name, self.call)

    def restore(self):
        setattr(self.module, self.name, self.method)

    def __enter__(self):
        self.install()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.restore()


class MockClass(object):
    def __init__(self, module, name, replacement):
        self.module = module
        self.name = name
        self.replacement = replacement
        self.orig = getattr(module, name)

    def install(self):
        setattr(self.module, self.name, self.replacement)

    def restore(self):
        setattr(self.module, self.name, self.orig)

    def __enter__(self):
        self.install()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.restore()


class mock(object):
    def __init__(self, **mocks):
        self.mocks = mocks
        self.__dict__.update(mocks)

    def install(self):
        for m in self.mocks.values():
            m.install()

    def restore(self):
        for m in self.mocks.values():
            m.restore()

    def __enter__(self):
        self.install()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.restore()


class Expando(object):
    def __init__(self, **props):
        self.__dict__.update(props)

    def __str__(self):
        return repr(self.__dict__)


def ExpandoClass(**props):
    instances = []

    class AnonMock(object):
        def __init__(self, *args, **kwargs):
            self._args = args
            self._kwargs = kwargs
            self.__dict__.update(props)
            instances.append(self)

        @classmethod
        def instances(cls):
            return instances

    return AnonMock


class MockJob(Expando):
    def __init__(self, *_, **kwargs):
        self.id = 'fake'
        self.hostPath = 'localhost:0'
        self.sessionKey = '...'
        self.namespace = 'ns'
        self.owner = 'admin'
        self.message_level = None
        self.dispatchArgs = dict()
        self._status_fetch_timeout = 1
        self.waitForRunning = True
        self.request = dict(search="...", earliest_time="-1h", latest_time="now")
        Expando.__init__(self, **kwargs)

    def isExpired(self):
        return False

    def isRealtime(self):
        return False
