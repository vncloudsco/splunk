from __future__ import division
from __future__ import absolute_import
from __future__ import print_function
#Copyright (C) 2005-2015 Splunk Inc. All Rights Reserved. This work contains trade
#secrets and confidential material of Splunk Inc., and its use or disclosure in
#whole or in part without the express written permission of Splunk Inc. is prohibited.

from builtins import object
from past.utils import old_div
from splunk.util import cmp
import functools
import logging
import re
import sys
from builtins import range

from splunk.field_extractor.FieldLearning import getLiteralPrefixRegexes, generateSimpleRegexes, getPrefixRegexes
from splunk.field_extractor.FieldLearning import safeRegexLiteral, getValueRegex, splitText
from splunk.field_extractor.FieldLearning import fixIdentifiers, VALUEPOST_CHARACTERS

logger = logging.getLogger('dmfx')

# before we do the very expensive validation of every rule against
# every event, only consider the 20 best scoring rules
MAX_RULES_TO_CONSIDER_BEFORE_VALIDATION = 20

# During the generation of patterns, the number could get very large quickly,
# especially if there are more than 4 extractions, say. We need to prune them
# to MAX_PATTERNS at every step of this generation.
MAX_PATTERNS = 1000

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


#fout = open("NGHITEST.txt","w")

def learn(fromField, markedEvents, events, counterExamples, filterstring):
    rules = _generateRules(fromField, markedEvents, filterstring)
#    fout.write("number of rules before validation = %u\n" % len(rules))
#    for r in rules:
#        fout.write(r.getPattern() + "\n")
    _validateRules(events, rules, markedEvents, counterExamples)
    return rules


def ruleCMP(x, y):
    return int(1000 * (y.getScore() - x.getScore()))



def _validateRules(events, rules, markedEvents, counterExamples):
    foundrules = False
    batch = 10
    rules.sort(key=functools.cmp_to_key(ruleCMP))
    numRulesToCheck = min(len(rules), 100) # only look at numRulesToCheck rules. If we keep all rules and none of them matches,
    # we will go through them all and that may take a long time if there are many rules
    for i in range(0, numRulesToCheck, batch):
        subset = rules[i:i+batch]
        _validateRules_1(events, subset, markedEvents, counterExamples)
        if len(subset) > 0:
            del rules[:]
            rules.append(subset[0])
            foundrules = True
            break
    if not foundrules:
        del rules[:]


def _validateRules_1(events, rules, markedEvents, counterExamples):
    # cutting off of bad rules with prelim stats before validation
#    rules.sort(ruleCMP)
#    _keepTopRulesPerFieldSet(rules, MAX_RULES_TO_CONSIDER_BEFORE_VALIDATION)

    # reset the preliminary rule scores to be calc'd again after validation
    for r in rules:
        r._score = None

    badrules = set()
    # remove bad rules -- ambiguous patterns and those that give counter examples
    # for id, markedEvent in markedEvents.items():
    for event in events:
        for rule in rules:
            if rule in badrules:
                continue
            pattern = rule._pattern

            # if the rule is ambiguous, remove it. for example: [a-z]+([a-z]+) which can get any arbitrary split
            u = re.search("(.+)\(\\1\)", pattern)
            if u != None and u.group() != r'\(\)':
#                fout.write("removing pattern %s because it's ambiguous, due to this segment: %s\n" % (pattern, u.group()))
                badrules.add(rule)
                continue

   # FOR EACH RULE,
    for rule in rules:
        if rule in badrules:
            continue
        isBad = False
        # DELETE THE RULE IF IT MATCHES ANY COUNTER EXAMPLES
        for counterEvent in counterExamples:
            extractions = rule.findExtractions(counterEvent)
            for k, v in extractions.items():
                if k == "_event":
                    continue
                if k in counterEvent:
                    cv = counterEvent[k]
                    if cv[0] == v[0] and cv[1] == v[1]:
                        badrules.add(rule)
                        #print("REMOVING RULE: FOR MATCHING " + k)
                        isBad = True
  #                      fout.write("removing pattern %s because it matches counter-example\n" % rule.getPattern())
                        logger.debug("Removing rule that learned counter example: %s for field: %s" % (rule._pattern, k))
                        break
            if isBad:
                break
        # DELETE THE RULE IF IT DOESN'T MATCH ALL EXAMPLES
        # FOR EACH EXAMPLE
        for markedEvent in markedEvents:
            # MATCH RULE AGAINST EXAMPLE
            extractions = rule.findExtractions(markedEvent)
            # FOR EACH VALUE FROM EXAMPLE EVENT
            for k, v in markedEvent.items():
                if k == "_event":
                    continue
                # IF RULE DIDN'T EXTRACT A VALUE OR IT EXTRACTED THE WRONG VALUE
                if k not in extractions or (v[0] != extractions[k][0] or v[1] != extractions[k][1]):
                        badrules.add(rule)
                        #print("REMOVING RULE: FOR NOT MATCHING %s %s %s" % (str(k), str(v), str(extractions)))
                        isBad = True
#                        fout.write("removing pattern " + rule.getPattern() + " because it failed to match example\n")
                        logger.debug("Removing rule that didn't learn example: %s for field: %s" % (rule._pattern, k))
                        break
            if isBad:
                break

    # remove bad rules
    for br in badrules:
        if br in  rules:
            rules.remove(br)
            #print(br.getPattern())
    if len(rules) == 0:
        return

    # add extraction data to each surviving rule
    for event in events:
        for rule in rules:
            extractions = rule.findExtractions(event)
            rule.addExtractions(extractions)

    # re-sort now that we have new extractions
    rules.sort(key=functools.cmp_to_key(ruleCMP))
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


def _generateRules(fromField, markedEvents, filterstring):
    rules = {}
    for markedEvent in markedEvents:
        #myId = markedEvent['id']
        #print("%s %s\n" % (str( markedEvent), type(markedEvent)))
        if len(markedEvent) == 0:
            continue
        # add temp filter field
        if filterstring != '':
            markedEvent['_filter'] = filterstring
        myrules = makeRules(fromField, markedEvent)
        # remove temp filter field
        if '_filter' in markedEvent:
            del markedEvent['_filter']
        for rule in myrules:
            rulestr = str(rule)
            if rulestr in rules:
                markedEvent = rule.getMarkedEvent()
                rule = rules[rulestr]
                rule.addExtractions(markedEvent, True)
            else:
                rules[rulestr] = rule
            rule.incMatchCount()
    return list(rules.values())


def makeRules(fromField, markedEvent):
    patterns = generatePatterns2(fromField, markedEvent)
    rules = []
    for pattern, bias in patterns:
        rule = MPositionalRule(pattern, markedEvent, fromField, bias)
        rules.append(rule)
    return rules


def fieldOrder(markedEvent):
    positions = {}
    for k, v in markedEvent.items():
        if isinstance(v, list): #xxx
            positions[k] = v

    orderedFields = list(positions.items())
    # SORT BY START POSITION
    orderedFields.sort(key=lambda x: x[1][0])
    return [field for field, stats in orderedFields]

def fieldOrder2(fromField, markedEvent):
    fields = list(markedEvent.keys())
    if "_event" in fields:
        raw = markedEvent['_event'][fromField]
        fields.remove("_event")
    positions = {}
    for k, v in markedEvent.items():
        if k == "_filter":
            startpos = raw.find(markedEvent[k])
            if startpos >= 0:
                positions[k] = [startpos, startpos+len(markedEvent[k])]
        elif k != "_event" and isinstance(v, list): #xxx
            positions[k] = v

    orderedFields = list(positions.items())
    # SORT BY START POSITION
    orderedFields.sort(key=lambda x: x[1][0])



def generatePatterns(fromField, markedEvent):

    patterns = set([('', 1.0)])
    lastend = 0
    raw = markedEvent["_event"][fromField]

    findval = None
    orderedFields = fieldOrder(markedEvent)
    for i, fieldname in enumerate(orderedFields):
        if fieldname == "_event":
            continue

        #### CHANGE IN API.  NO LONGER PASS IN VALUE FOR FIELD, BUT AN ARRA OF START AND ENDPOS
        if  fieldname == "_filter":
            findval = markedEvent[fieldname]
            startpos = raw.find(findval)
            if startpos >= 0:
                endpos = startpos + len(findval)
            else:
                return []
        else:
            startpos, endpos = markedEvent[fieldname]

        findval = raw[startpos:endpos]
        prefix = raw[lastend:startpos]
        lastend = endpos
        suffixChar = ''
        if lastend < len(raw):
            suffixChar = raw[lastend]

        newpatterns = set()

        prefixPatterns = getPrefixPatterns(prefix)
        valuePatterns = getValuePatterns2(findval, suffixChar)

        # for each existing pattern so far
        for pastPattern, pastBias in patterns:
            for prefixPattern, prefixBias in prefixPatterns:
                for valPattern, valBias in valuePatterns:
                    if fieldname == '_filter':
                        newpattern = pastPattern + prefixPattern + findval
                    else:
                        newpattern = pastPattern + prefixPattern + "(?P<%s>%s)" % (fieldname, valPattern)

                    newbias = pastBias * prefixBias * valBias
                    newpatterns.add( (newpattern, newbias) )

        patterns = newpatterns

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

# added by NGHI
def generatePatterns2(fromField, markedEvent):
    lastend = 0
    raw = markedEvent["_event"][fromField]

#    print("extractions:")
#    for k,v in markedEvent.items():
#        if type(v) is list:
#            val = raw[v[0]:v[1]]
#            print("\t" + val)

    patterns = set([('', 1.0)])

    findval = None
    orderedFields = fieldOrder(markedEvent)
    for i, fieldname in enumerate(orderedFields):
        if fieldname == "_event":
            continue

        startpos, endpos = markedEvent[fieldname]
        findval = raw[startpos:endpos]
        prefix = raw[lastend:startpos]
        lastend = endpos
        suffixChar = ''
        if lastend < len(raw):
            suffixChar = raw[lastend]

        prefixPatterns = getPrefixPatterns(prefix)
        valuePatterns = getValuePatterns2(findval, suffixChar)
        newpatterns = set()

        # for each existing pattern so far
        for pastPattern, pastBias in patterns:
            for prefixPattern, prefixBias in prefixPatterns:
                for valPattern, valBias in valuePatterns:
                    newpatterns.add((pastPattern + prefixPattern + "(?P<%s>%s)" % (fieldname, valPattern),
                                    pastBias*prefixBias*valBias))

        # if the number of patterns are too large, we need to prune them
        if len(newpatterns) > MAX_PATTERNS:
            patterns = sorted(newpatterns, key=lambda p: -int(1000*p[1]))[:MAX_PATTERNS]
        else: patterns = newpatterns

    if findval == None:
        return []

    filter = ''
    if '_filter' in markedEvent:
#        filter = '(?=.*?' + markedEvent['_filter'] + ')' # lookahead
        ft = markedEvent['_filter']
        char1 = ft[0] # the filter is nonempty as checked above
        filter = '(?=[^' + char1 + ']*' + \
                 '(?:' + ft + '|' + \
                 char1 + '.*' + ft + '))'


    # add suffix pattern and filter
    suffix = raw[lastend+1:]
    newpatterns = []
    for pastPattern, pastBias in patterns:
        if len(pastPattern) > 0 and pastPattern[0] == '^':
            first_part = filter + pastPattern
        else:
            first_part = filter + '^' + pastPattern
        for suffixPattern, suffixBias in getSuffixPatterns(suffix, findval):
            newpatterns.append((first_part+suffixPattern, pastBias*suffixBias))

    return newpatterns


def getPrefixPatterns(prefix):

    patterns = set()

    # if first
    if prefix == '':
        patterns.add(('^', 1.0))
        return patterns

    multiline = '\n' in prefix
    # !!! maybe need to add (?is) to p
    for p in getLiteralPrefixRegexes(prefix, multiline):
        patterns.add((p, 1.0))
    for p in generateSimpleRegexes(prefix, True, multiline):
        patterns.add((p, 1.0))
    for p in getPrefixRegexes(prefix, multiline):
        patterns.add((p, 1.0))
    patterns.add( (safeRegexLiteral(prefix[-1]).replace('\^', ''), 0.8) )
    return patterns


def getSuffixPatterns(suffix, extraction):

    suffixes = []
    suffixes.append(("",  0.5))
    return suffixes
    if suffix == "" or suffix == "\n":
        suffixes.append(("$", 1.0))
    else:
        oppositeChar = suffix[0]
        if oppositeChar in VALUEPOST_CHARACTERS and not oppositeChar in extraction:
            suffixes.append( ("(?=%s)" % safeRegexLiteral(oppositeChar).replace("\$", ''), 1.0) )

    return suffixes



def getValuePatterns(value, suffixChar):
    return [(getValueRegex(value, True, suffixChar)[0], 1.0)]

# Added by NGHI
def getValuePatterns2(value, suffixChar):
#    patterns = getValueRegex2(value, True, suffixChar,10)
    patterns = [(getValueRegex(value, True, suffixChar)[0], 1.0)]
    valres = [splitText(value)]
    valre = valres[0].replace('\\w', '[a-z]')
    if valre != valres[0]: valres.append(valre)
    for r in valres:
        try:
            pattern = fixIdentifiers(r)
            re.compile(pattern)
            patterns.append((pattern, 1.0))
        except Exception as e:
            pass
    return patterns


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
    def getFromField(self):
        return self._fromField
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
        exType = self.valType(self.getExamplesCount().keys())
        lrnType = self.valType(self.getLearnedCount().keys())
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

        for field in markedEvent:
            if field == "_event" or field == "_filter":
                continue
            # keep set of all values extracted
            if field not in self._fieldValues:
                self._fieldValues[field] = set()

            ###
            startpos, endpos = markedEvent[field]
            raw = markedEvent["_event"][self._fromField]
            extraction = raw[startpos:endpos]
            ###

            self._fieldValues[field].add(extraction)


            # keep track of counts of example and learned extractions, ignoring fields for simplicity
            if init:
                self._examplesCount[extraction] = 1 + self._examplesCount.get(extraction, 0)
            else:
                self._learnedExtractionsCount[extraction] = 1 + self._learnedExtractionsCount.get(extraction, 0)


    def findExtractions(self, markedEvent):
        if "_event" in markedEvent:
            markedEvent = markedEvent["_event"]
        raw = markedEvent[self._fromField]
        match = self.getRE().match(raw)
        if match == None:
            return {}

        ##return match.groupdict()
        matches = {}
        for field in match.groupdict():
            matches[field] = match.span(field)

        matches["_event"] = { self._fromField: raw }

        return matches

#=============================================================================================================================
# Unit tests

def check_test_results(expect, receive):
    if len(expect) != len(receive):
        print("len(expect) = %d, len(receive) = %d" %(len(expect), len(receive)))
        return False
    for i, v in enumerate(expect):
        if expect[i] != receive[i]:
            print(("results %u are different:\nexpect\n%s\nreceived\n%s", (i, str(expect[i]), str(receive[i]))))
            return False
    return True


def test_filter():
    print("Running test_filter ...")
    MarkedEvents = [
        {
            '_event': {'_raw':"10.1.1.43 - webdev [07/Aug/2005:23:58:08 -0700] \"GET / HTTP/1.0\" 200 1163 \"-\" \"check_http/1.10 (nagios-plugins 1.4)\""},
            'nghi': [49, 52]
        }
    ] #  'nghi' = 'GET'
    expect = ["(?=[^H]*(?:HTTP|H.*HTTP))[^\"\\n]*\"(?P<nghi>\w+)"]
    receive = [x.getPattern() for x in learn("_raw", MarkedEvents, [], [], "HTTP")] # filter is HTTP
    MarkedEvents[0]['nghi'] = [55, 59] # HTTP
    expect.append("(?=[^G]*(?:GET|G.*GET))(?:[^ \\n]* ){7}(?P<nghi>\w+)")
    receive.extend([x.getPattern() for x in learn("_raw", MarkedEvents, [], [], "GET")]) # filter is GET
#    if not check_test_results(expect,receive):
    if len(receive) == 0:
        print("test_filter failed: no rules")
    else:
        print("test_filter passed: rule = %s" % receive[0])

def test_multiple_extractions():
    print("Running test_multiple_extractions ...")
    MarkedEvents = [
            {
                '_event': {'_raw': '183.60.213.53 - - [04/Jun/2014:04:21:56 -0700] "GET /wp-trackback.php?p=39 HTTP/1.1" 302 - "-" "Mozilla/5.0 (compatible; EasouSpider; +http://www.easou.com/search/spider.html)"'},
                'm1': [48, 51],
                'm2': [75, 79],
                'm3': [96, 103],
                'm4': [109, 119],
                'm5': [163, 169]
            }
        ] # m1 = GET, m2 = HTTP, m3 = Mozilla, m4 = compatible, m5 = spider
    expect = ['[^\]\n]*\]\s+"(?P<m1>\w+)(?:[^ \\n]* ){2}(?P<m2>[^/]+)(?:[^ \\n]* ){4}"(?P<m3>\w+)[^\(\\n]*\((?P<m4>[a-z]+)(?:[^/\\n]*/){4}(?P<m5>\w+)']
    receive = [x.getPattern() for x in learn("_raw", MarkedEvents, [], [], "")]
    if len(receive)>0 and re.match(receive[0], MarkedEvents[0]['_event']['_raw']):
        print("test_multiple_extractions passed")
    elif len(receive) == 0:
        print("test_multiple_extractions failed: no rules generated")
    else:
        print("test_multiple_extractions failed: regex %s doesn't match the event " %receive[0])

def test_filename_extraction():
    print("Running test_filename_extraction ...")
    MarkedEvents = [
            {
                '_event': {'_raw': '[Wed May 11 16:56:12 2014] [error] [client 10.1.1.140] File does not exist: /usr/local/apache/htdocs/favicon.ico'},
                'myfield': [101, 112]
            }
        ] # myfield = favicon.ico
    events = [
            {
                '_raw': '[Wed May 11 16:56:11 2014] [error] [client 10.1.1.140] File does not exist: /usr/local/apache/htdocs/themes/ComBeta/images/page_bg.gi'
            }
        ]
    expect = ['(?:[^/\\n]*/){5}(?P<myfield>\w+\.\w+)']
    receive = [x.getPattern() for x in learn("_raw", MarkedEvents, events, [], "")]
#    if not check_test_results(expect,receive):
    if len(receive) == 0:
        print("test_filename_extraction failed: no rules")
    else:
        print("test_filename_extraction passed")

def test_SPL_90631():
        MarkedEvents = [
                {'_event': {'_raw': "Fri Sep  5 18:56:16 2014system_network_sent_bps: 42557 system_cpu_logical_count: 24 system_network_recv_errors_ps: 0 system_cpu_pct_system: 0.0 system_mem_total_b: 17143455744 system_cpu_pct_user: 0.1 system_mem_pct: 22.3 system_cpu_pct_idle: 99.9 system_swap_sin_b: 0 system_cpu_physical_count: 12 system_swap_free: 30343819264 system_network_sent_packets_ps: 63 system_swap_sout_b: 0 system_network_recv_bps: 21559 system_network_recv_packets_ps: 111 system_swap_used_b: 3941203968 system_swap_total_b: 34285023232 system_swap_pct: 11.5 system_mem_avail_b: 13322375168 system_network_sent_dropped_ps: 0 system_network_sent_errors_ps: 0 system_network_recv_dropped_ps: 0 system_mem_used_b: 3821080576 system_mem_free_b: 13322375168 splunkd_read_ops: 18 splunkd_ppid: 632 splunkd_mem_nonpaged_pool_b: 632928 splunkd_write_ops: 66 splunkd_mem_peak_wset_b: 2173239296 splunkd_connections: 611 splunkd_tcp_connections: 611 splunkd_mem_peak_pagefile_b: 2886307840 splunkd_write_bps: 21221 splunkd_mem_pagefile_b: 1996668928 splunkd_mem_virtual_b: 1996668928 splunkd_cpu_pct: 2.7 splunkd_mem_peak_paged_pool_b: 1125480 splunkd_mem_private_b: 1996668928 splunkd_open_fd: 42060 splunkd_threads: 61 splunkd_mem_resident_b: 1866801152 splunkd_status: running splunkd_mem_num_page_faults: 445681402 splunkd_read_bps: 2649 splunkd_pid: 3740 splunkd_child_procs: 3 splunkd_running: True splunkd_mem_wset_b: 1866801152 splunkd_mem_paged_pool_b: 986920 splunkd_mem_peak_nonpaged_pool_b: 2630164 "},
                'm1': [1215, 1225]
            }]
        receive = [x.getPattern() for x in learn("_raw", MarkedEvents, [], [], "")]
        if len(receive) == 0:
            print("test_SPL_90631 failed: no rules generated")
        else:
            print("test_SPL_90631 passed. rule = %s" %receive[0])


def test_multiple_examples():
    print("Running test_multiple_examples ...")
    res = True
    MarkedEvents = {}
    MarkedEvents['access_combined.log'] = [
            {
                '_event': {'_raw': '220.181.108.99 - - [22/Jul/2014:05:22:49 -0700] "GET / HTTP/1.1" 200 21453 "-" "Mozilla/5.0 (compatible; Baiduspider/2.0; +http://www.baidu.com/search/spider.html)"'},
                'm1': [0, 14],
                'm2': [49, 53],
                'm3': [65, 68],
                'm4': [69, 75],
                'm5': [80, 87],
                'm6': [88, 91],
            } # m1 = 220.181.108.99, m2 = GET, m3 = 200, m4 = 21453, m5 = Mozilla, m6 = 5.0
            , {
                '_event': {'_raw': '93.174.93.204 - - [22/Jul/2014:05:22:26 -0700] "POST /xmlrpc.php HTTP/1.0" 200 370 "-" "Mozilla/4.0 (compatible: MSIE 7.0; Windows NT 6.0)"'},
                'm1': [0, 13],
                'm2': [48, 53],
                'm3': [75, 78],
                'm4': [79, 83],
                'm5': [88, 95],
                'm6': [96, 99],
            }
        ] # m1 = 93.174.93.204, m2 = POST, m3 = 200, m4 = 370, m5 = Mozilla, m6 = 4.0

    MarkedEvents['alcatel.log'] = [
            {
                '_event': {'_raw': 'Jul 16 10:09:24 172.22.76.4 %LINK-W-Down:  e3'},
                'm1': [16, 27],
                'm2': [29, 40],
                'm3': [43, 45],
            } # m1 = 172.22.76.4, m2 = LINK-W-Down, m3 = e3
            , {
                '_event': {'_raw': 'Jul 16 10:09:17 172.22.98.4 %LINK-I-Up:  e4'},
                'm1': [16, 27],
                'm2': [29, 38],
                'm3': [41, 43],
            } # m1 = 172.22.98.4, m2 = LINK-I-Up, m3 = e4
        ]

    MarkedEvents['dhcpd.log'] = [
            {
                '_event': {'_raw': 'Jul 24 00:09:29 dhcp-sac-1s.acmetech.com dhcpd: DHCPREQUEST for 10.11.36.43 (140.192.141.242) from 23:15:be:bc:d1:7f (iPod-touch-2) via 10.99.56.1'},
                'm1': [48, 59],
                'm2': [64, 75],
                'm3': [77, 92],
                'm4': [99, 116],
                'm5': [118, 130],
                'm6': [136, 146],
            } # m1 = DHCPREQUEST, m2 = 10.11.36.43, m3 = 140.192.141.242, m4 = 23:15:be:bc:d1:7f, m5 = iPod-touch-2, m6 = 10.99.56.1
            , { '_event': {'_raw': 'Jul 24 00:09:29 dhcp-sac-1s.acmetech.com dhcpd: DHCPREQUEST for 10.11.36.11 (140.192.141.242) from 8b:66:79:4a:bf:c5 (SEP001BD4587CFF) via 10.99.0.1'},
                'm1': [48, 59],
                'm2': [64, 75],
                'm3': [77, 92],
                'm4': [99, 116],
                'm5': [118, 133],
                'm6': [139, 148],
            } # m1 = DHCPREQUEST, m2 = 10.11.36.11, m3 = 140.192.141.242, m4 = 8b:66:79:4a:bf:c5, m5 = SEP001BD4587CFF, m6 = 10.99.0.1
        ]

    MarkedEvents['alcatel.log.2'] =[
            {
                '_event': {'_raw': 'Jul 24 00:03:05 172.22.98.4 %STP-W-PORTSTATUS: e4: STP status Forwarding'},
                'm1': [16, 27],
                'm2': [29, 45],
                'm3': [47, 49],
           }
           , {
                '_event': {'_raw': 'Jul 24 00:03:24 172.22.7.4 %LINK-I-Up: e13'},
#                'm1': [16,26],
           }
        ]


#    MarkedEvents[] = [
#            {
#                '_event': {},
#                'm1': [,],
#                'm2': [,],
#                'm3': [,],
#                'm4': [,],
#                'm5': [,],
#                'm6': [,],
#            }
#            {
#                '_event': {},
#                'm1': [,],
#                'm2': [,],
#                'm3': [,],
#                'm4': [,],
#                'm5': [,],
#                'm6': [,],
#            }
#        ]

    for k, events  in MarkedEvents.items():
        print("Examples from %s" % k)
        receive = [x.getPattern() for x in learn("_raw", events, [], [], "")]
        if len(receive) == 0:
            print("test_multiple_examples failed for marked events %s: no rules generated" %k)
            res = False
        else:
            print("events %s: rule = %s" %(k, receive[0]))

    if res:
        print("test_multiple_examples pased")



def test_SPL_88441():
    MarkedEvents = [
           {'_event': {"_raw":"127.0.0.1 - admin [06/Aug/2014:09:48:59.631 -0700] \"GET /en-US/api/shelper?snippet=true&snippetEmbedJS=false&namespace=search&search=search+index%3D_internal&useTypeahead=true&useAssistant=true&showCommandHelp=true&showCommandHistory=true&showFieldInfo=false&_=1407343333845 HTTP/1.1\" 200 703 \"http://wimpy:8010/en-US/app/search/search?q=search%20index%3D_internal%20%2210.160.255.36%22&earliest=0&latest=&sid=1407343735.141\" \"Mozilla/5.0 (Macintosh; Intel Mac OS X 10_9_2) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/36.0.1985.125 Safari/537.36\" - 53e25c7ba17fe5783c7b10 32ms"},
           "m1":[427, 547]}
           ]
    receive = [x.getPattern() for x in learn("_raw", MarkedEvents, [], [], "")]
    if len(receive) == 0:
        print("test_SPL_88441 failed: no rules generated")
    else:
        print("test_SPL_88441 passed. rule = %s" %receive[0])

def test_SPL_tbd():
    MarkedEvents = [
            {'_event': {'_raw': "127.0.0.1 - admin [08/Aug/2014:08:22:39.835 -0700] \"GET /en-US/config?autoload=1 HTTP/1.1\" 200 7040 \"http://wimpy:8010/en-US/app/search/search?q=search%20index%3D_internal&earliest=0&latest=&sid=1407448529.55\" \"Mozilla/5.0 (Macintosh; Intel Mac OS X 10_9_2) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/36.0.1985.125 Safari/537.36\" - 53e4eb3fd57fbdc0344750 14ms"},
                'm1': [290, 295],
                'm2': [297, 303]
}]
    receive = [x.getPattern() for x in learn("_raw", MarkedEvents, [], [], "")]
    if len(receive) == 0:
        print("test_SPL_tbd failed: no rules generated")
    else:
        print("test_SPL_tbd passed. rule = %s" %receive[0])


def test_SPL_91728():
    MarkedEvents = [
            {'_event': {"_raw": "Mon Oct 06 2014 07:35:15 mailsv1 sshd[5427]: Failed password for invalid user operator from 199.15.234.66 port 3957 ssh2"},
                'ip':[92, 105]
            },
            {'_event': {"_raw": "Mon Oct 06 2014 07:35:00 mailsv1 sshd[5038]: Failed password for nagios from 199.15.234.66 port 2281 ssh2"},
                'ip': [77, 90]
            }
        ]
    receive = [x.getPattern() for x in learn("_raw", MarkedEvents, [], [], "")]
    if len(receive) == 0:
        print("test_SPL_91728 failed: no rules generated")
    else:
        print("test_SPL_91728 passed. rule = %s" %receive[0])

def test_small():
    MarkedEvents = [
            {'_event': {"_raw": "2014-10-29 11:30:50,917 - [INFO] - from application in play-akka.actor.actions-dispatcher-21 LitleBatchRequest->processReceived() line 738 : Billing successful for order id 1871234"},
                "id":[173, 180]
            }
        ]
    receive = [x.getPattern() for x in learn("_raw", MarkedEvents, [MarkedEvents[0]['_event']], [], "")]
    if len(receive) == 0:
        print("test_small failed: no rules generated")
    else:
        print("test_small passed. rule = %s" %receive[0])


# Carasso's old test
def test_old():
    markedEvents = {
        1:
        {
        '_event': {'_raw': '15.151.182.2 - - [15/May/2005:04:05:34 -0700] "POST /rs-soap/services/RSPortal HTTP/1.0" 200 384 "-" "Axis/1.1"'},
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
        '_event': {'_raw': '15.151.182.2 - - [15/May/2006:04:05:34 -0800] "POST /elvis/was-here.html HTTP/1.0" 300 385 "-" "Axis/1.1"'},
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
        '_event': {'_raw': '15.151.182.2 - - [15/May/2007:04:06:34 -0800] "POST /carasso/was-here.html HTTP/1.0" 300 385 "-" "Axis/1.1"'},
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
         '_event': {'_raw': 'david,was,here'},
         'name': 'david',
         'verb':'was',
         'location':'here'
         },
        }

    markedEvents = [
        {
        '_event': {'_raw': '15.151.182.2 - - [15/May/2005:04:05:34 -0700] "POST /rs-soap/services/RSPortal HTTP/1.0" 200 384 "-" "Axis/1.1"'},
        'ip': [0, 12],
        'date':[18, 29]
        }
    ]

    counterExamples = [
        {
        '_event': {'_raw': '15.151.182.2 - - [15/May/2005:04:05:34 -0700] "POST /rs-soap/services/RSPortal HTTP/1.0" 200 384 "-" "Axis/1.1"'},
        'xip': [0, 12],
        'xdate':[18, 29]
        }
    ]

    events = [
        {
            "source": "/var/log/cron",
            "_raw": '15.151.182.9999 - - [198/May/2005:05:06:77 -0700] "POST /rs-soap/services/RSPortal HTTP/1.0" 200 384 "-" "Axis/1.1"',
            "_sourcetype": "cron"
        }
    ]

    rules = learn("_raw", markedEvents, events, counterExamples, "")
    print("%u rules found" % len(rules))
    for rule in rules:
        print(rule.getPattern())

    for e in markedEvents:
        for rule in rules:
            extractions = rule.findExtractions(e)
            if len(extractions) > 0:
                print("M:%s\n\t%s\n\t%s\n\t%s" % (str(e["_event"]['_raw']), str(extractions), str(rule.getPattern()), str(rule.getLearnedCount())))
                break
            else:
                print("rule didn't find " + str(e))
        print("")


if __name__ == '__main__':

    test_filter()
    test_multiple_extractions()
    test_filename_extraction()
    test_multiple_examples()
    test_SPL_88441()
    test_SPL_tbd()
    test_SPL_90631()
    test_SPL_91728()
    test_small()
#    test_old()
