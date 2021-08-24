from builtins import map
from builtins import object
import logging, re
from threading import current_thread


class WarningsCollectionHandler(logging.Handler):
    """
    Logging handler which collects warning messages in-memory for validation reporting
    """

    def __init__(self, level=logging.WARN):
        super(WarningsCollectionHandler, self).__init__(level)
        self.thread = current_thread()
        self.messages = []

    def emit(self, record):
        if self.thread == current_thread():
            self.messages.append(self.format(record).strip())


class WarningsCollector(object):
    """
    The collector is to be used in a with statement and handles attaching and removing the collection handler to
    and from the given logger
    """

    def __init__(self, logger):
        self.logger = logger
        self.handler = WarningsCollectionHandler()

    def __enter__(self):
        if self.logger:
            self.logger.addHandler(self.handler)

    def __exit__(self, type, value, traceback):
        if self.logger:
            if traceback:
                self.handler.messages.append(str(value))

    def getMessages(self):
        return self.handler.messages


MESSAGE_LINE = re.compile(r'^(.+?)\s*\(line (\d+)\)$')


def extractMessageLineNumber(msg):
    line = None
    match = MESSAGE_LINE.search(msg)
    if match:
        msg = match.group(1)
        line = int(match.group(2))
    return dict(message=msg, line=line)


def normalizeMessageInformation(messages):
    return list(map(extractMessageLineNumber, messages))


if __name__ == '__main__':
    import unittest

    class ValidationHelperTests(unittest.TestCase):
        def testExtractLineInformation(self):
            result = extractMessageLineNumber('This is a test message (line 4711)')
            self.assertIsNotNone(result)
            self.assertEquals(result['message'], 'This is a test message')
            self.assertEquals(result['line'], 4711)

            result = extractMessageLineNumber('This is a test message without line info')
            self.assertIsNotNone(result)
            self.assertEquals(result['message'], 'This is a test message without line info')
            self.assertIsNone(result['line'])

    loader = unittest.TestLoader()
    suite = [loader.loadTestsFromTestCase(case) for case in (ValidationHelperTests,)]
    unittest.TextTestRunner(verbosity=2).run(unittest.TestSuite(suite))
