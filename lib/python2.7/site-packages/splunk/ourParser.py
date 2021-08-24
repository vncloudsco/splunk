from __future__ import print_function
from splunk.search.TransformerUtil import stringToSearchKV, tokenize

def splunkParse(splunk):
    tokens = tokenize(splunk)
    chunks = []
    clauses = []

    # break the splunk out into chunks
    firstToken = True
    for token in tokens:
        if firstToken:
            clause = { 'command': "", 'tokens':[]}
            clause['command'] = token
            firstToken = False
        elif token is not "|":
            clause['tokens'].append(token)
        else:
            chunks.append(clause)
            firstToken = True

    for chunk in chunks:
        termDict = stringToSearchKV(' '.join(chunk['tokens'] ), True )

        clause = {
            'command': chunk['command'],
            'args'    : {
                '_terms'  : termDict['search']
            }
        }

        for k, v in termDict.items():
            if k is not 'search':
                clause['args'][k] = v

        clauses.append(clause)

    return clauses


if __name__ == "__main__":
    import unittest

    class TestParse(unittest.TestCase):
        def testPass(self):
            print(splunkParse("search host=* | fields +punct | timechart avg(widgets)"))

    # Execute test suite.
    parseSuite = unittest.TestLoader().loadTestsFromTestCase(TestParse)
    unittest.TextTestRunner(verbosity=3).run(parseSuite)
