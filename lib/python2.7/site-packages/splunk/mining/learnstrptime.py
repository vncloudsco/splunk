from __future__ import absolute_import
from __future__ import print_function
from __future__ import division
from functools import cmp_to_key

# This work contains trade
#secrets and confidential material of Splunk Inc., and its use or disclosure in
#whole or in part without the express written permission of Splunk Inc. is prohibited.

from past.utils import old_div
import re
import time
import splunk.mining.FieldLearning as learning


def sameType(v1, v2):
    if ((v1.isdigit() and v2.isdigit()) or (v1.isalpha() and v2.isalpha())):
        #print("SAME TYPE: %s %s" % (v1, v2))
        return True
    return False

def findAll(line, value):
    if value == '':
        return [-1]
    positions = []
    start = 0
    line = line.lower()
    value = value.lower()
    # linelen = len(line)
    while True:
        pos = line.find(value, start)
        start = pos+1
        if pos < 0:
            break
        #if (pos > 0 and sameType(value, line[pos-1])) or (pos < linelen-len(value) and sameType(value, line[pos+len(value)])):
        #    pass  #continue
        positions.append(pos)
    return positions

def getPositions(line, timevalues):
    flatpositions = []
    positions = []
    for val in timevalues:
        thesePos = findAll(line, val)
        poslen = len(thesePos)
        #print("VAL: %s POS: %s" % (val, thesePos))
        if poslen > 0:
            positions.append(thesePos)
            if poslen == 1:
                flatpositions.append(thesePos[0])
            else:
                #print(thesePos)
                flatpositions.append(thesePos[int(round(poslen/2.))])
    minV = 10000000
    maxV = sumV = 0
    if len(flatpositions) == 0:
        return None
    for pos in flatpositions:
        sumV += pos
        if pos < minV: minV = pos
        if pos > maxV: maxV = pos
    avg = old_div(sumV, len(positions))
    #print("MIN: %s MAX: %s AVG: %s" % (minV, maxV, avg))
    bestpositions = []
    for vlocs in positions:
        bestvloc = vlocs[0]
        # find the location that is closest to the average
        for vloc in vlocs:
            if abs(vloc - avg) < abs(bestvloc - avg):
                bestvloc = vloc
        bestpositions.append(bestvloc)
    return bestpositions


"""
%y The year within century.
%m The month number [01,12]; leading zeros are permitted but not required.
%b The month, using the locale's month names; either the abbreviated or full name may be specified.
%d The day of the month [01,31]; leading zeros are permitted but not required.
%H The hour (24-hour clock) [00,23]; leading zeros are permitted but not required.
%I The hour (12-hour clock) [01,12]; leading zeros are permitted but not required.
%M The minute [00,59]; leading zeros are permitted but not required.
%S The seconds [00,60]; leading zeros are permitted but not required.
%p The locale's equivalent of a.m or p.m.
%n Any white space.
---------
Splunk Exhancements
%N For GNU date-time nanoseconds. Specify any sub-second parsing by providing the width: %3N = milliseconds, %6N = microseconds, %9N = nanoseconds.
%Q,%qFor milliseconds, microseconds for Apache Tomcat. %Q and %q can format any time resolution if the width is specified.
%IFor hours on a 12-hour clock format. If %I appears after %S or %s (like "%H:%M:%S.%l") it takes on the log4cpp meaning of milliseconds.
%+For standard UNIX date format timestamps.
%vFor BSD and OSX standard date format.
%z, %::z, %:::zGNU libc support.
%oFor AIX timestamp support (%o used as an alias for %Y).
%pThe locale's equivalent of AM or PM. (Note: there may be none.)

"""

FIELDNAMES = ["month", "day", "year", "hour", "minute", "second", "ampm", "zone"]
STRPTIME = { 'month':'m', 'litmonth':'b', 'day':'d', 'year':'y', 'hour':'I', '24hour':'H', 'minute':'M', 'second':'S', 'ampm':'p', 'zone':'Z' }

def buildSTRPTime(text, fieldAndPos, valueDict):
    lastpos = 0
    strp = ""
    for field, pos in fieldAndPos:
        if field in FIELDNAMES:
            value = valueDict[field]
            if len(value) == 0 or pos == -1 :
                continue
            
            if field == "month" and not value.isdigit():
                field = "litmonth"
            if field == 'hour' and (int(value) > 12 or valueDict['ampm'] == ''):
                field = '24hour'
            suffix = ""
            if lastpos > 0:
                suffix = text[lastpos:pos]
            # don't treat "Mar  7" as two spaces.
            if suffix == '  ': suffix = ' '
            strp += suffix + "%" + STRPTIME[field]
            lastpos = pos + len(value)
    return strp


def learnSTRPTime(text, timevalues):
    timevalues = timevalues.split(',')
    positions = getPositions(text, timevalues)
    if positions == None:
        return None, None
    if positions[0] == -1 or positions[1] == -1 or positions[3] == -1 or positions[4] == -1:
        print("Warning: month, day, hour, and minute are required.")
        return None, None
                  
    posDict = {}
    valueDict = {}
    count = 0
    first = -1
    last = -1
    for position in positions:
        fieldname = FIELDNAMES[count]
        posDict[fieldname] = position
        value = timevalues[count]
        valueDict[fieldname] = value
        count += 1
        if first < 0 or -1 < position < first:
            first = position
        if position > last:
            last = position + len(value)
    # sort by position
    fieldAndPos = list(posDict.items())
    fieldAndPos.sort(key=cmp_to_key(lambda x, y: x[1] - y[1]))
    #print(fieldAndPos)
    prefix = text[:first]
    suffix = text[last:]
    #print("TEXT: %s" % text)
    #print("PREFIX: %s" % prefix)
    #print("SUFFIX: %s" % suffix)
    #print("VALUES: %s" % valueDict)
    prefixRegex = learning.generateSearchRegex(prefix)

    strpformat = buildSTRPTime(text, fieldAndPos, valueDict)
    print("TIME_PREFIX: '%s'" % prefixRegex)
    print("TIME_FORMAT: %s" % strpformat)
    try:
        verify(text, prefixRegex, strpformat, suffix)
        return (prefixRegex, strpformat, suffix)
    except:
        print("Error determining timeformat")
        return None
    
def verify(text, regex, strp, suffix):
    start = re.search(regex, text).end()
    timetext = text[start:]
    timetext = timetext[:timetext.index(suffix)]
    #print("TIMETEXT: '%s'" % timetext)
    thistime = time.strptime(timetext, strp)
    #print(thistime)
    seq = [x for x in thistime]
    if seq[0] == 1900:
        seq[0] = time.gmtime()[0]
    print(time.asctime(seq))

if __name__ == '__main__':
    import sys
    args = sys.argv
    argcount = len(args)
    if argcount != 3:
        print('Usage:  python %s "eventtext" "%s"' % (args[0], FIELDNAMES))
        print('example:          "blah Mar  7 11:04:21 willLaptop syslogd 1.4.1: restart" "Mar,7,,11,04,21,,"')
    else:
        text = args[1]
        fields = args[2]
        learnSTRPTime(text, fields)
