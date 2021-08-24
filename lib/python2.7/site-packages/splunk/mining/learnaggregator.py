from __future__ import absolute_import
from __future__ import print_function
# This work contains trade
#secrets and confidential material of Splunk Inc., and its use or disclosure in
#whole or in part without the express written permission of Splunk Inc. is prohibited.

import re

import splunk.mining.FieldLearning as learning
import splunk.mining.dcutils as dcu


def classifyLines(events):
    firstlines = set()
    otherlines = set()
    lastlines  = set()
    for event in events:
        if event == '':
            print("empty event?")
            continue
        if '\n' not in event:
            firstlines.add(event)
            lastlines.add(event)
        else:
            firstline, others = event.split('\n', 1)
            firstlines.add(firstline)
            if others != '':
                others = others.split('\n')
                otherlines.update(others)
                lastlines.add(others[-1])
    return firstlines, otherlines, lastlines

#GUIDEPOST_CHARACTERS = "\"/\t()[]{}*+^$!-\\?!@#%+=:<>,?;" + "' &.~"
GUIDEPOST_CHARACTERS = "\"/\t\\(\\)\\[\\]\\{\\}\\*\\+\\^$!\\-\\\\?@#%\\+=:<>,;' &.~\n"
MAX_FORWARD_CHARS   = 10
MAX_BACKWARDS_CHARS = 10

PATTERN = '([%s]+)' % GUIDEPOST_CHARACTERS
REGEX = re.compile(PATTERN)

def getLinePatterns(line):
    line = '\n' + line + '\n'
    return set(REGEX.findall(line))

    
def getLinesPatterns(lines, start, end, commonp):
    common = set()
    for line in lines:
        line = line[start:end]
        patterns = getLinePatterns(line)
        if len(common) == 0:
            common = patterns
        else:
            if commonp:
                common.intersection_update(patterns)
                if len(common) == 0:
                    return common
            else:
                common = common.union(patterns)

    return common

def getStarts(lines, commonp):
    return getLinesPatterns(lines, 0, MAX_FORWARD_CHARS, commonp)
def getEnds(lines, commonp):
    return getLinesPatterns(lines, -MAX_BACKWARDS_CHARS, -1, commonp)



# what char runs does lines1 have that lines2 doesn't
def learnDiff(lines1, lines2):
    starts1 = getStarts(lines1, True)
    starts2 = getStarts(lines2, False)
    ends1 = getEnds(lines1, True)
    ends2 = getEnds(lines2, False)
##     print("STARTS1: %s" % starts1)
##     print("STARTS2: %s" % starts2)
##     print("ENDS1: %s" % ends1)
##     print("ENDS2: %s" % ends2)
    return starts1.difference(starts2), ends1.difference(ends2)

## def makeRegex(pattern, startp):
##     chars = set(pattern)
##     chars = learning.safeRegexLiteral(chars)
##     pattern = learning.safeRegexLiteral(pattern)
##     if startp:
##         return '([\\r\\n]+)[^%s]{0,%s}%s            # BREAK AFTER SEEING "%s" AT THE BEGINNING OF A LINE' % (chars, MAX_FORWARD_CHARS, pattern, pattern)
##     else:
##         return '%s[^%s]{0,%s}([\\r\\n]+)            # BREAK AFTER SEEING "%s" AT THE BEGINNING OF A LINE' % (pattern, MAX_BACKWARDS_CHARS, chars, pattern)        

def _makeRegex(pattern, startp):
    pattern = learning.safeRegexLiteral(pattern)
    if startp:
        if pattern.startswith('\n'):
            pattern = pattern[1:]
            return '([\\r\\n]+)%s            # BREAK BEFORE SEEING "%s" AT THE START OF A LINE' % (pattern, pattern)
        else:
            return '([\\r\\n]+).{0,%s}%s     # BREAK BEFORE SEEING "%s" NEAR THE BEGINNING OF A LINE' % (MAX_FORWARD_CHARS, pattern, pattern)
    else:
        if pattern.endswith('\n'):
            pattern = pattern[:-1]
            return '%s([\\r\\n]+)            # BREAK AFTER SEEING "%s" AT THE END OF A LINE' % (pattern, pattern)
        else:
            return '%s.{0,%s}([\\r\\n]+)     # BREAK AFTER SEEING "%s" NEAR THE END OF A LINE' % (pattern, MAX_BACKWARDS_CHARS, pattern)        
def makeRegex(pattern, startp):
    return _makeRegex(pattern, startp).replace('\n', '')

def learnAggregator(events):
    firstlines, otherlines, lastlines = classifyLines(events)
    beforeStart, beforeEnd = learnDiff(firstlines, otherlines)
    afterStart, afterEnd = learnDiff(lastlines, firstlines)
##     print("beforeStart: %s beforeEnd: %s afterStart: %s afterEnd: %s" % (beforeStart, beforeEnd, afterStart, afterEnd))

    print("SAMPLE EVENT: %s" % events[0])
    
    # best to use pattern at start of line for break-before
    if len(beforeStart) > 0:
        print("LINE_BREAKER = %s" % makeRegex(list(beforeStart)[0], True))
    # next best to use pattern at end of line for break-after
    elif len(afterEnd) > 0:
        print("LINE_BREAKER = %s" % makeRegex(list(afterEnd)[0], False))
    # next best are equally weird.  using pattern at start of line before break or end of line after break
    elif len(beforeEnd) > 0:
        print("LINE_BREAKER = %s" % makeRegex(list(beforeEnd)[0], False))
    elif len(afterStart) > 0:
        print("LINE_BREAKER = %s" % makeRegex(list(afterStart)[0], True))
        

if __name__ == '__main__':
    import sys
    if len(sys.argv) != 2:
        print('Usage:  python %s "file of events"' % sys.argv[0])
        print('        file should break events with "-=X=-" on a separate line')
    else:
        events = []
        filename = sys.argv[1]
        lines = dcu.loadLines(filename)
        if lines == []:
            print("cannot get events")
            exit(1)
        event = ''
        for line in lines:
            line = line.strip()
            if line == '-=X=-':
                if event != '':
                    events.append(event)
                event = ''
            else:
                if event != '':
                    event += '\n'
                event += line

        if event != '':
            events.append(event)
##         for e in events:
##             print(e)
##             print("-"*80)
#        print("%s events" % len(events))
        learnAggregator(events)
