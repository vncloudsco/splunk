from __future__ import absolute_import
from __future__ import print_function
# This work contains trade
#secrets and confidential material of Splunk Inc., and its use or disclosure in
#whole or in part without the express written permission of Splunk Inc. is prohibited.

from builtins import object
from builtins import range
import sys
import time

import splunk.mining.dcutils as dcutils
import splunk.clilib.bundle_paths as bundle_paths


_debug = 0


def interactivelyLearn(filename, fieldname, goodTerms, badTerms, maxIterations, maxLines=-1):
    rules = None
    newTerms = None
    for i in range(0, maxIterations):
        if _debug > 0: print("Iteration: %u" % i)
        rules, newTerms = learnFieldRulesFromFile(filename, fieldname, goodTerms, badTerms, maxLines, i==0)
        #print("New Terms: %s" % newTerms)
        if len(newTerms) == 0:
            if _debug > 0: print("No more learned in iteration: %u" % i)
            break
        goodTerms.extend(newTerms)
    return rules, goodTerms
        

def learnFieldRulesFromFile(filename, fieldname, goodTerms, badTerms, maxLines, first):
    filetype = getFileType(filename)
    _printTiming("Got filetype: " + filetype)
    lines = dcutils.loadLines(filename)
    if len(lines) > maxLines:
        lines = lines[:maxLines]
        if first:
            print("Large training file.  Limiting learning to first %s lines of %s" % (maxLines, filename))
    print("Learning...")
    _printTiming("Loaded lines")
    # strictRules = _generateRules(filetype, fieldname, lines, goodTerms, None)
    looseRules = _generateRules(filetype, fieldname, lines, goodTerms, "Loose")
    #rules = strictRules + looseRules
    rules = looseRules
    _printTiming("Generated lines")
    if _debug > 0: print("Rules Generated: %u" % len(rules))
    newTerms = _validateRules(lines, goodTerms, badTerms, rules)
    _printTiming("Validated lines")
    if _debug > 0: print("Rules Approved: %u" % len(rules))
    #if rulesdict != None and len(rulesfile) > 0:
    #  saveRules(rulesfile, rules)
    return rules, newTerms

def addRulesToDict(rulesdict, rules):
    for rule in rules:
        filetype = rule.getFileType()
        pattern = rule.getWholePattern()
        key = _twoKey(filetype, pattern)
        existingRules = rulesdict.get(key, None)
        if existingRules == None:
            existingRules = rulesdict[key] = list()
        existingRules.append(rule)

def getRulesListFromDict(rulesdict):
    rules = []
    for patternrules in list(rulesdict.values()):
        for rule in patternrules:
            rules.append(rule)
    return rules

# strip punctuation from head and tails of each extraction, so that input values could be specified with punctuation to make it less ambiguous, but that the output does not display them
def getExtractions(rulesdict, filetype, line):
    "Return dictionary mapping fieldnames to values extracted"
    pattern, types = splitText(line)
    key = _twoKey(filetype, types)
    matchingRules = rulesdict.get(key, None)
    #print("%s %s" % (key, matchingRules))
    if matchingRules == None:
        return None
    resultDict = dict()
    for rule in matchingRules:
        extraction = rule.findExtraction(types, pattern)
        if extraction != None:
            fieldname = rule.getFieldName()
            resultDict[fieldname] = extraction
    return resultDict
    
        
def getFileType(filename):
    import splunk.mining.findutils as findutils
    return findutils.getFileType(filename)
##     import splunk.fileclassifier
##     returnDict = splunk.fileclassifier.TypeSettings(None)
##     splunk.fileclassifier.getFileType(returnDict, filename)
##     filetype = returnDict.get("file_type")
##     return filetype


def _twoKey(key1, key2):
    return str(key1) + "~" + str(key2)

def xmlescape(text):
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace("\"", "&quot;")

def getrulename(fieldname):
    return fieldname + "-" + time.asctime().replace(" ", "_")

def saveRules(rulesfile, propsfile, learnedRules):
    
    output = ""
    for rule in learnedRules:
        if rule._wholePattern[-1] == "\n":
            rule._wholePattern = rule._wholePattern[:-1]
        pattern = rule._wholePattern # xmlescape(rule._wholePattern)

        ke = list(rule._knownExtractionsCount.keys())
        if len(ke) > 7:
            ke = ke[0:7]
        output += "\n"
        if len(ke) > 0:
            output += "# extraction examples: " + str(ke) +  "\n"
        fieldname = getrulename(rule._fieldname)
        output += "[" + fieldname + "]\nREGEX = " + pattern + "\nFORMAT = " + rule._fieldname + "::$1\n"
    if len(output) > 0:
        existingconf = dcutils.readText(rulesfile)
        newconf = existingconf + output
        dcutils.writeText(rulesfile, newconf)

        existingprops = dcutils.readText(propsfile)
        newprops = existingprops + "\n[default]\nREPORT-%s = %s\n" % (fieldname, fieldname)
        dcutils.writeText(propsfile, newprops)

        _printTiming("Saved Rules")
        print("Rules saved.")
    else:
        print("Nothing to save.")
    
_lastPrintTime = None
def _printTiming(msg):
    global _lastPrintTime

    if _debug == 0:
        return
    now = time.time()
    if _lastPrintTime == None:
        print(msg)
    else:
        secs = int(100*(now-_lastPrintTime)) / 100.0
        print("%s ( Time: %s )" % (msg, secs))
    _lastPrintTime = now

def _generateRules(filetype, fieldname, lines, extractions, generateLooseRule):
    rules = {}
    linecount = 0
    for line in lines:
        linecount += 1
        rule = _generateRule(filetype, fieldname, line, extractions, generateLooseRule)
        if rule != None:
            rulestr = str(rule)
            if rulestr in rules:
                rule = rules[rulestr]
            else:
                #print("%u\t%s" % (linecount, line))
                rules[rulestr] = rule
            rule.incMatchCount()
                
##     for rule in rules.values():
##         print("RULE: %s\t%s" % (rule.getMatchCount(), rule))
    return list(rules.values())

def _validateRules(lines, knownextractions, badextractions, rules):
    # ?? NEED TO ADD CODE TO REMOVE TUPLES THAT DON'T PULL OUT ALL KNOWN VALUES
    # ?? IF USER AGREES WITH TUPLES, RERUN BY ADDING NEWVALUES TO VALUES AND LEARNING NEW NEWVALUES
    # ?? MAYBE IGNORE SPACES BETWEEN MULTIPLE ALPHA?
    # ?? COLLAPSE MULTIPLE WHITESPACE TO ONE?
    
    totalExtractions = 0
    knownmatches = 0
    newExtractions = set()
    lineCount = 0
    badrules = set()
    for line in lines:
        lineCount += 1
        #print("%u %s" % (lineCount, line))
        thispattern, thistypes = splitText(line)
        for rule in rules:
            if rule in badrules:
                #print("skipping badrule")
                continue

            extraction = rule.findExtraction(thistypes, thispattern)
            if extraction != None:
                rule.addExtraction(extraction)
                #print("EXTRACTION: %s\t%s" % (extraction, line))
                if extraction in badextractions:
                    badrules.add(rule)
                    continue
                totalExtractions += 1
                #print("Extraction: %s" % extraction)
                if extraction in knownextractions:
                    #print("%s\t%s" % (extraction, line))
                    knownmatches += 1
                else:
                    if not extraction in newExtractions:
                        #print("NEW EXTRACTION: %s\t%s" % (extraction, line))
                        newExtractions.add(extraction)
            
    if _debug > 0:
        print("%s known matches out of %s total matches." % (knownmatches, totalExtractions))
        print("New values: %s" % list(newExtractions))
    #print("Bad Rules:")
    for br in badrules:
        rules.remove(br)
        #print(str(br))
    return newExtractions

def _parseExtractionOptions(extraction):
    suffixmatches = prefixmatches = False
    if extraction.startswith("*"):
        suffixmatches = True
        extraction = extraction[1:]
    if extraction.endswith("*"):
        prefixmatches = True
        extraction = extraction[0:-1]
    return extraction, prefixmatches, suffixmatches

def _generateRule(filetype, fieldname, line, extractions, generateLooseRule):
    for extraction in extractions:
        extraction, matchPrefix, matchSuffix = _parseExtractionOptions(extraction)
        if extraction in line:
            #print("%s\t%s" % (extraction, line))
            return PositionalRule(filetype, fieldname, extraction, line, matchPrefix, matchSuffix, extractions, generateLooseRule)
    return None
    
def splitText(text):
    tokens = []
    types = []
    token = ""
    lastchtype = None
    lastallowplus = False
    for ch in text:
        chtype = ch
        allowplus = False
        if ch.isalpha():
            chtype = "\w" #not accurate as "[a-zA-Z]" but a lot shorter
            allowplus = True
        elif ch.isdigit():
            chtype = "\d"
            allowplus = True
        elif ch == "\t": #.isspace():
            chtype = "\s"
            allowplus = True          
        elif ch in "()[]{}*+^$!-\?":
            chtype = "\\" + chtype # + "+"
        if lastchtype != None and chtype != lastchtype:
            if lastallowplus:
                lastchtype += "+"
            tokens.append(token)
            types.append(lastchtype)
            token = ""
        if chtype == lastchtype and not allowplus:
            tokens.append(token)
            types.append(lastchtype)
            #chtype = chtype + "+"
            
        token += ch
        lastchtype = chtype
        lastallowplus = allowplus

    if len(token) > 0:
        tokens.append(token)
    if lastchtype != None:
        types.append(lastchtype)
        
    if lastallowplus:
        types.append("+")


    types = "".join(types)
    #print(types)
    return tokens, types

class PositionalRule(object):
    _NOTCALCED = -99.0

    #def __init__(self, pp, vp, sp, knownExtractions):
    def __init__(self, filetype, fieldname, extraction, line, matchPrefix, matchSuffix, knownExtractions, generateLooseRule):

        self._knownExtractionsCount = {}
        self._filetype = filetype
        self._fieldname = fieldname
        self._looseRule = generateLooseRule
        self.generatePattern(line, extraction, matchPrefix, matchSuffix)
        #self.setPattern(ptypes, vtypes, stypes)
        self.setKnownExtractions(knownExtractions)
        self._learnedExtractionsCount = {}
        self._score = None
        self._matchCount = 0

    def clearStats(self):
        safeDelAttr(self, '_knownExtractionsCount')
        safeDelAttr(self, '_learnedExtractionsCount')
        safeDelAttr(self, '_score')
        safeDelAttr(self, '_matchCount')
                        
    def __str__(self):
        return str("".join(self._wholePattern))
    
    def __hash__(self):
        return hash(str(self))

    def incMatchCount(self):
        self._matchCount += 1

    def getMatchCount(self):
        return self._matchCount

    def getFileType(self):
        return self._filetype

    def getFieldName(self):
        return self._fieldname

    
    def getScore(self):
        return self._score

    def generatePattern(self, line, extraction, matchPrefix, matchSuffix):
        start = line.index(extraction)
        end = start + len(extraction)
        prefix = line[0:start]
        suffix = line[end:]
        pvals, ptypes = splitText(prefix)
        svals, stypes = splitText(suffix)            
        vvals, vtypes = splitText(extraction)
        self._prefixPatternLen = len(pvals)
        self._valuePatternLen  = len(vvals)
        self._suffixPatternLen = len(svals)

        if self._looseRule != None:
            stypes = ""
        
        #ALL SUBSTRINGS TO MATCH
        if matchPrefix and stypes[0] == vtypes[-1]:
            stypes = stypes[1:]
        if matchSuffix and len(ptypes) > 0 and  ptypes[-1] == vtypes[0]:
            ptypes = ptypes[0:-1]
        self._wholePattern = ptypes + "(" + vtypes + ")" + stypes
        

    def getWholePattern(self):
        return self._wholePattern

    def setKnownExtractions(self, knownExtractions):
        self._knownExtractionsCount = {}
        for ke in knownExtractions:
            self._knownExtractionsCount[ke] = 0
            
    def getKnownExtractions(self):
        return list(self._knownExtractionsCount.keys())

    def getKnownExtractionsCount(self):
        return self._knownExtractionsCount

    def addExtraction(self, extraction):
        if extraction in self._knownExtractionsCount:
            self._knownExtractionsCount[extraction] += 1
        elif extraction in self._learnedExtractionsCount:
            self._learnedExtractionsCount[extraction] += 1
        else:
            self._learnedExtractionsCount[extraction] = 1

    def findExtraction(self, thistypes, thisvalues):
        wholepattern = self.getWholePattern().replace("\(", "XXX").replace("(", "").replace("XXX", "\(").replace("\)", "XXX").replace(")", "").replace("XXX", "\)")
##         print("LOOSE: %s" % self._looseRule)
##         print("THISTYPES:    %s wholepattern: %s" % (thistypes, wholepattern))
##         print("thisvalues: %s prefixlen: %s" % (thisvalues, self._prefixPatternLen))
        if ( (self._looseRule and thistypes.startswith(wholepattern)) or (self.getWholePattern() == thistypes) ):
            start = self._prefixPatternLen
            end = start + self._valuePatternLen
            extraction = "".join(thisvalues[start: end])
            #print("EXTRACTION: %s" % extraction)
            return extraction
        return None

def safeDelAttr(obj, attr):
    if getattr(obj, attr, False):
        delattr(obj, attr)

def defaultRulesFile():
    return bundle_paths.make_path("regexes.conf")

def defaultPropsFile():
    return bundle_paths.make_path("props.conf")

if __name__ == '__main__':
    argc = len(sys.argv)
    argv = sys.argv
    rulesfile = "rules.xml"
    if argc == 6:
        filename = argv[1]
        fieldname = argv[2]
        rulesfile = argv[3]
        goodstr = argv[4]
        badstr = argv[5]
        goodterms = set([v.strip() for v in goodstr.split(",")])
        badterms = set([v.strip() for v in badstr.split(",")])
        #rules, newterms = learnFieldRulesFromFile(rulesfile, filename,  fieldname, goodterms, badterms)
        rules, newterms = interactivelyLearn(filename,  fieldname, goodterms, badterms, 5, 10000)
        print("%u rules" % len(rules))
        print("Terms: %s" % newterms)
    elif argc == 3:
        filename = argv[1]
        rulesfile = argv[2]
        filetype = getFileType(filename)
        rulesdict = {}
        lines = dcutils.loadLines(filename)
        for line in lines:
            extractions = getExtractions(rulesdict, filetype, line)
            if extractions != None:
                print(line)
                print("\t%s" % extractions)
        
    else:
        print('Usage \n')
        print('\tTo Train: \t' + argv[0] + ' <file> <fieldname> <rulesfile. empty "" to not save> "<good terms comma separated>" "<bad terms comma separated>"')
        print('\tTo Run: \t' + argv[0] + ' <file> <rulesfile>')
