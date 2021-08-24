from __future__ import division
from __future__ import absolute_import
from __future__ import print_function
from functools import cmp_to_key
# This work contains trade
#secrets and confidential material of Splunk Inc., and its use or disclosure in
#whole or in part without the express written permission of Splunk Inc. is prohibited.

# runs shell that allows user to teach the system to extract dates interactively

from builtins import range
from past.utils import old_div

import re
import os
import time
from splunk.mining.interactiveutils import printQuestion, prompt, askMultipleChoiceQuestion


import splunk.mining.dcutils as dcutils

MAXPREFIX = 7  # PREFIX REGEX WITH AT MOST 7 CHARS BACK

litmonthtable = { 'jan':1, 'feb':2, 'mar':3, 'apr':4, 'may':5, 'jun':6, 'jul':7, 'aug':8, 'sep':9, 'oct':10, 'nov':11, 'dec':12 }


def guessTimestamp(regexes, line):
    for regex in regexes:
        matches = re.search(regex, line)
        if matches != None:
            try:
                matches = matches.groupdict()
                year   = int(matches.get("year", 0))
                day    = int(matches.get("day", 0))
                hour   = int(matches.get("hour", 0))
                minute = int(matches.get("minute", 0))
                second = int(matches.get("second", 0))
                ampm   = matches.get("ampm", "am")
                tzone  = matches.get("zone", None)
                if ampm.lower == "pm" and hour < 12:         
                    hour += 12
                    
                monval = matches.get("month", None)
                litmonval = matches.get("litmonth", None)
                if monval != None:
                    month = int(monval)
                elif litmonval != None:
                    month = litmonthtable[litmonval.lower()]
                timetuple = (year, month, day, hour, minute, second, 0, 0, 0)
                text = time.asctime(timetuple) + " zone=" + str(tzone)
                return text
            except:
                pass
    return None


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
    linelen = len(line)
    while True:
        pos = line.find(value, start)
        start = pos+1
        if pos < 0:
            break
        if (pos > 0 and sameType(value, line[pos-1])) or (pos < linelen-len(value) and sameType(value, line[pos+len(value)])):
            #print("SKIPPING: %s %s %s %s" % (pos, value, line[pos-1], line[pos+len(value)]))
            continue
        positions.append(pos)
    return positions

def makeregex(text):
    regex = ""
    addedPlus = False
    lastchtype = None
    for ch in text:
        if ch.isalpha():
            chtype = "\w"
        elif ch.isdigit():
            chtype = "\d+"
            addedPlus = True
        elif ch.isspace():
            chtype = "\s"
        else:
            if ch in "[](){}?*.^+<>":
                chtype = "\\" + ch
            else:
                chtype = ch
        if lastchtype == chtype:
            if not addedPlus:
                regex += "+"
                addedPlus = True
        else:
            regex += chtype
            addedPlus = False
        lastchtype = chtype
    return regex
    
    
def buildPythonRegex(fieldAndPos, valueDict, line):
    lastpos = 0
    count = 0
    extractions = ""
    regex = ""
    for field, pos in fieldAndPos:
        value = valueDict[field]
        if field == "month" and not value.isdigit():
            field = "litmonth"
        start = pos
        if lastpos == 0 and start - lastpos > MAXPREFIX:
            lastpos = start - MAXPREFIX
        prefix = line[lastpos:start]
        prefixregex = makeregex(prefix)
        valueregex = makeregex(value)
        regex += str(prefixregex) + "(?P<" + str(field) + ">" + str(valueregex) + ")"
        extractions += field + ","
        lastpos = start + len(value)
    return regex

def buildRegex(fieldAndPos, valueDict, fieldSet, line, regexname):
    lastpos = 0
    count = 0
    extractions = ""
    regex = ""
    for field, pos in fieldAndPos:
        if field in fieldSet:
            value = valueDict[field]
            if field == "month" and not value.isdigit():
                field = "litmonth"
            if len(value) == 0:
                continue
            start = pos
            if lastpos == 0 and start - lastpos > MAXPREFIX:
                lastpos = start - MAXPREFIX
            prefix = line[lastpos:start]
            prefixregex = makeregex(prefix)
            valueregex = makeregex(value)
            regex += str(prefixregex) + "(" + str(valueregex) + ")"
            extractions += field + ","
            lastpos = start + len(value)
    if len(regex) == 0:
        return ""
    html = "<define name=\"" + regexname + "\" extract=\"" + extractions + "\">\n\t<text><![CDATA[" + regex + "]]></text>\n</define>\n"
    return html

def learnrobRegex(regexname, line, timevalues):
    positions = getPositions(line, timevalues)
    if positions == None:
        return None, None
    if positions[0] == -1 or positions[1] == -1 or positions[3] == -1 or positions[4] == -1:
        print("Warning: month, day, hour, and minute are required.")
        return None, None
    fieldnames = ["month", "day", "year", "hour", "minute", "second", "ampm", "zone"]
    datefields = set(["month", "day", "year"])
    timefields = set(["hour", "minute", "second", "ampm", "zone"])
                  
    posDict = {}
    valueDict = {}
    count = 0
    for position in positions:
        fieldname = fieldnames[count]
        posDict[fieldname] = position
        value = timevalues[count]
        valueDict[fieldname] = value
        count += 1

    # sort by position
    fieldAndPos = list(posDict.items())
    fieldAndPos.sort(key=cmp_to_key(lambda x, y: x[1] - y[1]))
    datehtml = buildRegex(fieldAndPos, valueDict, datefields, line, regexname + "_date")
    timehtml = buildRegex(fieldAndPos, valueDict, timefields, line, regexname + "_time")

    if datehtml == "":
        print("Unable to generate date regex.")
    if timehtml == "":
        print("Unable to generate time regex.")
        
    pythonregex = buildPythonRegex(fieldAndPos, valueDict, line)
    
    return datehtml + timehtml, pythonregex

    
def getPositions(line, timevalues):
    flatpositions = []
    positions = []
    for val in timevalues:
        thesePos = findAll(line, val)
        poslen = len(thesePos)
        # print("VAL: %s POS: %s" % (val, thesePos))
        if poslen > 0:
            positions.append(thesePos)
            if poslen == 1:
                flatpositions.append(thesePos[0])
            else:
                #print(thesePos)
                flatpositions.append(thesePos[(poslen + 1) // 2])
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

def genformatname(filename, count):
    last = filename.rfind("/")
    if last >= 0:
        filename = filename[last+1:]
    filename = filename.lower()
    last = filename.find(".")
    if last >= 0:
        filename = filename[:last]
    return filename + "_" + str(count)
    
#simple heuristic to show lines with time
def possiblyHasTimeStamp(line):
    nums = 0
    colons = 0
    for ch in line:
        if ch.isdigit():
            nums+=1
        elif ch == ':':
            colons+=1
    score = colons * nums
    #print("Score: %s\t%s" % (score, line))
    return score > 15

Instruction = """INSTRUCTIONS: If a sample line does not have a timestamp, hit Enter.
If it does have a timestamp, enter the timestamp separated by commas
in this order: month, day, year, hour, minute, second, ampm, timezone.
Use a comma as a placeholder for missing values.  For example, for a
sample line like this "[Jan/1/08 11:56:45 GMT] login", the input 
should be: "Jan, 1, 08, 11, 56, 45, , GMT" (note missing AM/PM).
Spaces are optional."""  

def getDateInfo(filename):

    regexes = []
    totalhtml = ""
    count = 1
    linenum = 0
    lines = dcutils.loadLines(filename)
    try:
        printQuestion("Interactively Learning Date Formats.")
        printedInstructions = False
        for line in lines:
            line = line.strip()
            linenum += 1
            prettyLine = formatLine(line, 100, "\t")
            if not possiblyHasTimeStamp(line):
                print("Skipping unpromissing line " + str(linenum) + ".")
            else:
                timestamp = guessTimestamp(regexes, line)
                if timestamp != None:
                    print("Parsed Date on line " + str(linenum) + ".")  #    Time = ", timestamp, "\n", prettyLine
                    continue
                if not printedInstructions:
                    printedInstructions = True
                    print(Instruction)
    
                #print("\n" + "\nUnable to get time on this line:\n" + "-"*80 + "\n" + prettyLine + "\n" + "-"*80)
                print("\nSAMPLE LINE " + str(linenum) + ":\n" + prettyLine + "\n" + "-"*80)
                    #if askYesNoQuestion("Did we parse this correctly?"): continue
                while (True):
                    timeformat = prompt("timestamp values as: month, day, year, hour, minute, second, ampm, timezone.\n\t")
                    if timeformat == "":
                        break  # user says there is no timestamp on this line
                    else:
                        timevalues = [v.lower().strip() for v in timeformat.split(",")]
                        formatname = genformatname(filename, count)
                        html, regex = learnrobRegex(formatname, line, timevalues)
                        if html != None:
                            print("Learned pattern.")
                            #print(html)
                            #print(regex)
                            if not regex in regexes:
                                totalhtml += html
                                count += 1
                                regexes.append(regex)
                            break
                        else:
                            print("Unable to learn pattern.  Enter the timestamp values again.  If there is no timestamp on this line, just hit Enter.")
                printQuestion("If you are satisfied that the timestamps formats have been learned, hit Control-C.")
                        
    except KeyboardInterrupt:
        pass
    except Exception:
        import traceback
        traceback.print_exc()
    return regexes, totalhtml

def formatLine(line, maxlen, prefix):
    result = list(prefix + str(line))
    for i in range(maxlen, len(line), maxlen):
        result.insert(i, "\n" + prefix)
    return ''.join(result)
    
    

    
def learnDatesShell():
    print("")
    filename = prompt("full filename from which to learn dates", False).strip()
    if not dcutils.fileExists(filename):
        print("File does not exist.")
        return
    info, html = getDateInfo(filename)
    splunkhome = os.environ["SPLUNK_HOME"]
    if splunkhome == None or splunkhome == "":
        dtfile = "datetime.xml"
    else:
        from splunk.clilib.bundle_paths import make_splunkhome_path
        dtfile = make_splunkhome_path(['etc', 'datetime.xml'])

    print("\n\nPatterns Learned. \n\nIt is highly recommended that you make changes to a copy of the default datetime.xml file.")
    print("For example, copy \"" + dtfile + "\" to \"" + splunkhome + "/etc/system/local/datetime.xml\", and work with that file.\n")
    print("In that custom file, add the below timestamp definitions, and add the pattern names ")
    print("to timePatterns and datePatterns list.\n\nFor more details, see http://www.splunk.com/doc/latest/admin/TrainTimestampRecognition\n")
    print("-"*80)
    print(html)

def testShell():
    import os
    logfile = prompt("full logfile name", False).strip()
    parsetestexe = os.path.join(os.environ["SPLUNK_HOME"], 'bin', 'parsetest')
    os.system('"%s" file %s' % (parsetestexe, logfile))
        
def shell():
    while True:
        try:
            operation = askMultipleChoiceQuestion("What operation do you want to perform? (default=learn)", ['learn', 'test', 'quit'], 'learn')
            if operation == 'learn':
                learnDatesShell()
            elif operation == 'test':
                testShell()
            elif operation == 'quit':
                break
        except KeyboardInterrupt:
            print("\n\nReturning to main menu...\n")
            pass

if __name__ == '__main__':
    #learnDatesShell()
    #regex,html = getDateInfo("../logs/weblogic.stdout.log")
    #print("\n\n %s" % html)
    shell()
