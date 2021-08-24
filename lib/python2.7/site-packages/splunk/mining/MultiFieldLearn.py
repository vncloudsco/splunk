from __future__ import absolute_import
from __future__ import print_function
from __future__ import division
from functools import cmp_to_key

# This work contains trade
#secrets and confidential material of Splunk Inc., and its use or disclosure in
#whole or in part without the express written permission of Splunk Inc. is prohibited.

from past.utils import old_div
from builtins import object
from splunk.util import cmp
from builtins import object

import logging
import re

import splunk.mining.FieldLearning as fieldLearning

logger = logging.getLogger('splunk.mining.MFieldLearning')

# before we do the very expensive validation of every rule against
# every event, only consider the 20 best scoring rules
MAX_RULES_TO_CONSIDER_BEFORE_VALIDATION = 20
MAX_PATTERNS_BEFORE_BARF = 400000

## def isLearningField(fromField, fieldname):
##     return fieldname != fromField and not fieldname.startswith("#")
##
## def makeMarkedEvents(events, examples):
##     markedExamples = []
##     added = set()
##     for example in examples:
##         if example[0] == example[-1] and example.count(example[0]) > 2:
##             values = [v for v in s.split(s[0]) if v!='']
##         for event in events:
##             for val in values:
##                 if val not in event:
##                     break
##             else:
##                 added.add(event)
##                 markedExamples.append({'raw': event, 'values': values})
##     for event in events:
##         if event not in added:
##             markedExamples.append({'raw': event})
##     return markedExamples


def learn(fromField, markedEvents, counterExamples):
    rules = _generateRules(fromField, markedEvents)
    _validateRules(markedEvents, rules, counterExamples)
    return rules


def _validateRules(markedEvents, rules, counterExamples):


    # cutting off of bad rules with prelim stats before validation
    rules.sort(key=cmp_to_key(fieldLearning.ruleCMP))
    _keepTopRulesPerFieldSet(rules, MAX_RULES_TO_CONSIDER_BEFORE_VALIDATION)
    # reset the preliminary rule scores to be calc'd again after validation
    for r in rules:
        r._score = None

    badrules = set()
    # remove bad rules -- ambiguous patterns and those that give counter examples
    for markedEvent in markedEvents.values():
        for rule in rules:
            if rule in badrules:
                continue
            pattern = rule._pattern

            # if the rule is ambiguous, remove it. for example: [a-z]+([a-z]+) which can get any arbitrary split
            if re.search("(.+)\(\\1\)", pattern) != None:
                badrules.add(rule)
                continue
            extractions = rule.findExtractions(markedEvent)
            if len(extractions) > 0:

                # if value extracted is in counterexamples, mark as bad
                for k, v in extractions.items():
                    if v in counterExamples.get(k, []):
                        badrules.add(rule)
                        logger.debug("Removing rule that learned counter example: %s for field: %s" % (rule._pattern, k))
                        break
                rule.addExtractions(extractions)

    # remove bad rules
    for br in badrules:
        if br in  rules:
            rules.remove(br)
    # re-sort now that we have new extractions
    rules.sort(key=cmp_to_key(fieldLearning.ruleCMP))
    # for each rule, keep the best scoring of each set of fields.
    # we don't need 5 rules that extract the same thing.
    # assumes same fields won't be required to be extracted from different regex. not perfect,
    # but will reduce the regex to a minimum needed to retrieve different sets of values.
    _keepTopRulesPerFieldSet(rules, 1)

def _keepTopRulesPerFieldSet(rules, max):

    keepers = []
    seenFieldsCount = {}

    # for each rule
    for rule in rules:
        # get fields it extracts
        fields = str(list(rule.getMarkedEvent().keys()))
        if fields in seenFieldsCount:
            seenFieldsCount[fields] += 1
        else:
            seenFieldsCount[fields] = 1
        # if we've seen too many rules with this count, remove
        if seenFieldsCount[fields] <= max:
            keepers.append(rule)

    del rules[:]
    rules.extend(keepers)


def _generateRules(fromField, markedEvents):
    rules = {}
    for markedEvent in markedEvents.values():
        fieldsToLearn = list(markedEvent.keys())
        fieldsToLearn.remove("_event")
        if len(fieldsToLearn) == 0:
            continue
        myrules = makeRules(fromField, markedEvent)
        for rule in myrules:
            rulestr = str(rule)
            if rulestr in rules:
                markedEvent = rule.getMarkedEvent()
                rule = rules[rulestr]
                rule.addExtractions(markedEvent)
            else:
                rules[rulestr] = rule
            rule.incMatchCount()
    return list(rules.values())


def makeRules(fromField, markedEvent):

    patterns = generatePatterns(fromField, markedEvent)

    rules = []
    for pattern, bias in patterns:
        rule = MPositionalRule(pattern, markedEvent, fromField, bias)
        rules.append(rule)
    return rules


def fieldOrder(fromField, markedEvent):

    # if fieldnames indicate order, use that order

    fields = list(markedEvent.keys())
    if "_event" in fields:
        fields.remove("_event")
    for field in fields:
        if not field.startswith("FIELDNAME") or len(field)<= 9 or not field[9:].isdigit():
            break
    else: # all fields starts with FIELDNAME<number>, use numeric sort
        orderedFields = sorted(fields)
        return orderedFields

    positions = {}
    raw = markedEvent["_event"][fromField]

    # sort fields from largest value to smallest to discourage overlap
    orderedFields = list(markedEvent.items())
    orderedFields.sort(key=lambda x: len(str(x[1])))
    for fieldname, findval in markedEvent.items():
        findval = str(findval)
        if fieldname == "_event" or findval == "":
            continue
        pos = raw.find(findval)
        #print("ORDERING: %s %s %s" % (pos, fieldname, findval))
        if pos < 0:
            #print("Unable to find '%s' on event '%s'.  Ignoring event." % (findval, raw))
            return []
        positions[fieldname] = (pos, pos+len(findval))

    orderedFields = list(positions.items())
    orderedFields.sort(key=lambda x: x[1][0])
    #print("ORDERED: %s" % orderedFields)
    return [field for field, stats in orderedFields]


# return best pos in text, after start, for finding 'val'.
# tries to find the pos that's as close to the nextval to find.
# this prevents 200 from being found at the very start of this line,
# when the next value to find is 711.  instead it prefers the later 200.
#
#        2008/10/22 14:19 PDT [-] 10.1.6.141 .... 200 711 ....
#        ^^^ NO                                YES^^^ ^^^ BECAUSE
def bestPos(text, start, val, nextval):
    pos = text.find(val, start)
    if pos >= 0 and nextval != None:
        nextpos = text.find(nextval, pos)
        betterpos = text.rfind(val, pos, nextpos)
        if betterpos >= 0:
            return betterpos
    return pos


def generatePatterns(fromField, markedEvent):

    patterns = set([('', 1.0)])
    lastend = 0
    start = 0
    raw = markedEvent["_event"][fromField]
    #print("RAW: %s" % raw)

    findval = None
    orderedFields = fieldOrder(fromField, markedEvent)
    # print("ORDERED: %s" % orderedFields)
    for i, fieldname in enumerate(orderedFields):
        if fieldname == "_event":
            continue

        findval = markedEvent[fieldname]
        nextval = None
        if i < len(orderedFields)-1:
            nextval = markedEvent[orderedFields[i+1]]
        pos = bestPos(raw, start, findval, nextval)

        #print("FINDING: %s %s %s start: %s" % (pos, fieldname, findval, start))
        if pos < 0:
            #print("FAILED TO FIND: %s" % findval)
            return []

        prefix = ''
        if pos > 0:
            prefix = raw[lastend:pos]
        lastend = pos + len(findval)
        suffixChar = ''
        if lastend < len(raw):
            suffixChar = raw[lastend]

        #print("PREFIX: '%s' %s %s %s" % (prefix, lastend, pos, findval))
        #print("{%s}$%s$" % (prefix, findval))
        start = lastend
        newpatterns = set()

        prefixPatterns = getPrefixPatterns(prefix)
        valuePatterns = getValuePatterns(findval, suffixChar)

        # for each existing pattern so far
        for pastPattern, pastBias in patterns:
            for prefixPattern, prefixBias in prefixPatterns:
                for valPattern, valBias in valuePatterns:
                    newpattern = pastPattern + prefixPattern + "(?P<%s>%s)" % (fieldname, valPattern)
                    newbias = pastBias * prefixBias * valBias
                    newpatterns.add( (newpattern, newbias) )
        patterns = newpatterns
        nextcount = len(patterns) * len(prefixPatterns) * len(valuePatterns)
        # PREVENT ABUSE
        if nextcount > MAX_PATTERNS_BEFORE_BARF:
            break


    if findval == None:
        return []

    # add suffix pattern
    suffix = raw[lastend+1:]
    newpatterns = []    
    for pastPattern, pastBias in patterns:
        for suffixPattern, suffixBias in getSuffixPatterns(suffix, findval):  
            newpattern = pastPattern + suffixPattern
            newbias    = pastBias * suffixBias
            newpatterns.append( (newpattern, newbias) )
    return newpatterns

def getPrefixPatterns(prefix):

    patterns = set()

    # if first
    if prefix == '':
        patterns.add(('^', 1.0))
        return patterns

    multiline = '\n' in prefix
    # !!! maybe need to add (?is) to p
    for p in fieldLearning.getLiteralPrefixRegexes(prefix, multiline):
        patterns.add((p, 1.0))
    for p in fieldLearning.generateSimpleRegexes(prefix, True, multiline):
        patterns.add((p, 1.0))
    for p in fieldLearning.getPrefixRegexes(prefix, multiline):
        patterns.add((p, 1.0))
    patterns.add( (fieldLearning.safeRegexLiteral(prefix[-1]).replace('\^', ''), 0.8) )
    return patterns


def getSuffixPatterns(suffix, extraction):

    suffixes = []
    suffixes.append(("",  0.5))
    return suffixes
    if suffix == "" or suffix == "\n":
        suffixes.append(("$", 1.0))
    else:
        oppositeChar = suffix[0]
        if oppositeChar in fieldLearning.VALUEPOST_CHARACTERS and not oppositeChar in extraction:
            suffixes.append( ("(?=%s)" % fieldLearning.safeRegexLiteral(oppositeChar).replace("\$", ''), 1.0) )

    return suffixes


def getValuePatterns(value, suffixChar):
    return [(fieldLearning.getValueRegex(value, True, suffixChar)[0], 1.0)]



####################################################

class MPositionalRule(object):

    def __init__(self, pattern, markedEvent, fromField, bias):
        self._examplesCount = {}
        self._regex = None
        self._learnedExtractionsCount = {}
        self._fromField = fromField

        self._pattern = pattern
        self._initialMarkedEvent = markedEvent
        self.addExtractions(markedEvent, True)

        self._score = None
        self._matchCount = 0
        self._bias = bias

    def __str__(self):
        #return "regex: %s    Examples: %s" % (str("".join(self._pattern)), self._examplesCount)
        return "regex: %s" % (str("".join(self._pattern)))
    def __hash__(self):
        return hash(str(self))
    def incMatchCount(self):
        self._matchCount += 1
    def getMatchCount(self):
        return self._matchCount
    def getMarkedEvent(self):
        return self._initialMarkedEvent

    def getScore(self):
        if self._score == None:
            self._score = self.calcScore()
        return self._score


    def extractionExpectedness(self):
        '''measure of how off the avg length of the learned extractions are from the example extractions'''
        learned = self.getLearnedCount()
        examples = self.getExamplesCount()
        if len(learned) == 0 or len(examples) == 0:
            return 1
        avgExampleLen = float(sum([ len(k) for k in examples]))  / len(examples)
        avgLearnedLen = float(sum([ len(k) for k in learned]))   / len(learned)

        minExampleLen = min([ len(k) for k in examples])
        minLearnedLen = min([ len(k) for k in learned])
        maxExampleLen = max([ len(k) for k in examples])
        maxLearnedLen = max([ len(k) for k in learned])
        expectedness = 1 + abs(minExampleLen-minLearnedLen) / float(minExampleLen) + abs(maxExampleLen-maxLearnedLen) / float(maxExampleLen) + old_div(abs(avgLearnedLen - avgExampleLen), avgExampleLen)
        return expectedness

    def valType(self, vals):
        seenNum = False
        seenShortText = False
        seenLongText = False

        for v in vals:
            try:
                float(v)
                seenNum = True
            except:
                if len(v)>20:
                    seenLongText = True
                else:
                    seenShortText = True
            if seenNum and (seenShortText or seenLongText):
                return "mixed"
        if seenNum:
            return "num"
        if seenShortText and seenLongText:
            return "mixedtext"
        if seenShortText:
            return "shorttext"
        if seenLongText:
            return "longtext"
        return "unknown"

    def learnedConsistent(self):
        exType = self.valType(self.getExamplesCount())
        lrnType = self.valType(self.getLearnedCount())
        return lrnType == "unknown" or exType == lrnType


    def calcScore(self):
        exampleCount = sum(self.getExamplesCount().values())      # number of examples matched
        exampleVarietyPerc = float(sum([ 1 for v in self.getExamplesCount().values() if v > 0]))  / len(self.getExamplesCount())# number of examples this rule extracts
        learnedCount       = len(self.getLearnedCount())                # learned more terms
        regexSize          = len(self.getPattern())                   # approximate measure of regex complexity
        center = 20
        goodCount = float(max(0, center - abs(learnedCount-center)))
        if goodCount == 0 and learnedCount > 0:
            goodCount = 1

        score = (10000.0*exampleVarietyPerc) + (100.0*goodCount) + (200.0/regexSize)  + 10*exampleCount
        score *= self._bias
        if self.learnedConsistent():
            score += 500

        return score


    def getPattern(self):
        return self._pattern

    def getRE(self):
        if self._regex == None:
            self._regex = re.compile(self._pattern)
        return self._regex


    def getExamples(self):
        return list(self._examplesCount.keys())

    def getExamplesCount(self):
        return self._examplesCount

    def getLearnedCount(self):
        return self._learnedExtractionsCount

    def getFieldValues(self):
        return self._fieldValues

    def addExtractions(self, markedEvent, init=False):
        if init:
            self._examplesCount = {}
            self._fieldValues = {}

        for field, extraction in markedEvent.items():
            if field == "_event":
                continue
            # keep set of all values extracted
            if field not in self._fieldValues:
                self._fieldValues[field] = set()
            self._fieldValues[field].add(extraction)


            # keep track of counts of example and learned extractions, ignoring fields for simplicity
            if init:
                self._examplesCount[extraction] = 1
            elif extraction in self._examplesCount:
                self._examplesCount[extraction] += 1
            elif extraction in self._learnedExtractionsCount:
                self._learnedExtractionsCount[extraction] += 1
            else:
                self._learnedExtractionsCount[extraction] = 1


    def findExtractions(self, markedEvent):
        raw = markedEvent["_event"][self._fromField]
        match = self.getRE().match(raw)
        if match == None:
            return {}
        return match.groupdict()


if __name__ == '__main__':

    counterExamples = {}
    markedEvents = {
        1:
        {
        '_event': {'raw': '15.151.182.2 - - [15/May/2005:04:05:34 -0700] "POST /rs-soap/services/RSPortal HTTP/1.0" 200 384 "-" "Axis/1.1"'},
        'ip': '15.151.182.2',
        'date':'15/May/2005',
        'time':'04:05:34',
        'zone':'-0700',
        'method':'POST',
        'file':'/rs-soap/services/RSPortal',
        'version':'HTTP/1.0',
        'status':'200',
        'bytes':'384'
        },

        2: {
        '_event': {'raw': '15.151.182.2 - - [15/May/2006:04:05:34 -0800] "POST /elvis/was-here.html HTTP/1.0" 300 385 "-" "Axis/1.1"'},
        'ip': '15.151.182.2',
        'date':'15/May/2006',
        'time':'04:05:34',
        'zone':'-0700',
        'method':'POST',
        'file':'/elvis/was-here.html',
        'version':'HTTP/1.0',
        'status':'300',
        'bytes':'385'
        },
        3:
        {
        '_event': {'raw': '15.151.182.2 - - [15/May/2007:04:06:34 -0800] "POST /carasso/was-here.html HTTP/1.0" 300 385 "-" "Axis/1.1"'},
        'ip': '15.151.182.2',
        'date':'15/May/2007',
        'time':'04:06:34',
        'zone':'-0800',
        'method':'POST',
        'file':'/carasso/was-here.html',
        'version':'HTTP/1.0',
        'status':'300',
        'bytes':'385'
         },
         4:
         {
         '_event': {'raw': 'david,was,here'},
         'name': 'david',
         'verb':'was',
         'location':'here'
         },
        }

    rules = learn("raw", markedEvents, counterExamples)

    print("%s rules found" % len(rules))

    for e in markedEvents.values():
        for rule in rules:
            extractions = rule.findExtractions(e)
            if len(extractions) > 0:
                print("%s\n\t%s\n\t%s" % (e["_event"]['raw'], extractions, rule.getPattern()))
                break
            else:
                print("rule didn't find %s" % e)
        print("")

    rule = rules[0]
