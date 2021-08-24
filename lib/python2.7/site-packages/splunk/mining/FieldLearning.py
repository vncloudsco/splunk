from __future__ import division
# This work contains trade
#secrets and confidential material of Splunk Inc., and its use or disclosure in
#whole or in part without the express written permission of Splunk Inc. is prohibited.

from builtins import object
from builtins import range
from past.utils import old_div

import re
import logging
import itertools
from functools import cmp_to_key
logger = logging.getLogger('splunk.mining.FieldLearning') 

# more interations is good for interactive learning of terms, but in
# ifx we're focusing on learning of ONE rule
MAX_ITERATIONS = 1
# have learning fail if more than 100 rules are generated.   need more unique examples.
MAX_REGEX_BEFORE_FAILURE = 100
# if the regex is longer than N characters, abort
MAX_RULE_LEN = 60
# if we generate a regex with more than 20 elements, give up rule
MAX_REGEX_ELEMENTS = 30
# before we do the very expensive validation of every rule against
# every event, only consider the 20 best scoring rules
MAX_RULES_TO_CONSIDER_BEFORE_VALIDATION = 20
# if regex of actual value is > 15 characters, loose up regex.
# revents overly complicated regex when they get unnecessary complex,
# and also prevents false extractions when regex is simple
MAX_VALUE_REGEX = 15
# don't allow \w+{6}
MAXMATCHCOUNT = 10
# don't allow jump to char if more than 30 chars away.  defeats much of purpose of dist
MAXDIST = 30

# terms that you do not want to use as a prefix in regex
BAD_MEAT = set(["sun", "mon", "tue", "tues", "wed", "thurs", "fri", "sat", "sunday", "monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov", "dec", "january", "february", "march", "april", "may", "june", "july", "august", "september", "october", "november", "december", "2003", "2004", "2005", "2006", "2007", "2008", "2009", "am", "pm", "ut", "utc", "gmt", "cet", "cest", "cetdst", "met", "mest", "metdst", "mez", "mesz", "eet", "eest", "eetdst", "wet", "west", "wetdst", "msk", "msd", "ist", "jst", "kst", "hkt", "ast", "adt", "est", "edt", "cst", "cdt", "mst", "mdt", "pst", "pdt", "cast", "cadt", "east", "eadt", "wast", "wadt"])

# characters used to jump to value (e.g. jump 3 tabs)
GUIDEPOST_CHARACTERS = "\"/\t()[]{}*+^$!-\\?!@#%+=:<>,?;" + "' &.~" + "|"

# same but value AFTER value, so willing to accept more unreliable characters . and space.
# unwilling to rely on spaces to jump to a value (because english text length can arbitrarily vary),
# but are willing to have space end a value (e.g "[blah blah blah] 7.0 blah" -> ] (\d+.\d+) ")
VALUEPOST_CHARACTERS = "&. " + GUIDEPOST_CHARACTERS


def ruleCMP(x, y):
    return int(1000 * (y.getScore() - x.getScore()))

def fastFirstRuleCMP(x, y):
    return y.getMatchCount() - x.getMatchCount() #len(x._wholePattern) - len(y._wholePattern)

def learn(events, examples, counterexamples, justTopRule=True):

    rules = None
    newTerms = None
    newExamples = list(examples)
    # for each learning cycle
    for i in range(0, MAX_ITERATIONS):
        logger.info("GENERATING RULES FROM %s EVENTS" % len(events))
        rules = _generateRules(events, newExamples)
        newTerms = _validateRules(events, newExamples, counterexamples, rules)
        if len(newTerms) == 0:
            break
        newExamples.extend(newTerms)

    terms = set()
    for rule in rules:
        terms.update(rule.getExamplesCount())
        terms.update(rule.getLearnedCount())
        
    logger.debug("%s rules" % len(rules))
    orderedTerms = sorted(terms)
    logger.debug("Terms Learned: %s" % orderedTerms)

    rules = sorted(rules, key = cmp_to_key(ruleCMP))

    if justTopRule:
        rules = rules[:1]
    if len(rules) > MAX_REGEX_BEFORE_FAILURE:
        raise Exception('Too many rules were generated. Try providing values that are more unique to your field.')
    regexes = []
    extractions = {}
    for pos, rule in enumerate(rules):
        regexes.append(rule.getWholePattern())
        knownCounts = rule.getExamplesCount()
        learnedCounts = rule.getLearnedCount()
        terms = itertools.chain(knownCounts, learnedCounts)
        for term in terms:
            myrules = extractions.get(term, [])
            myrules.append(pos)
            extractions[term] = myrules
        
    return regexes, extractions

def removeDoomedRules(rules, doomed):
    for d in doomed:
        for i in range(0, len(rules)):
            if d == rules[i].getWholePattern():
                del rules[i]
                break

def patternComplexity(pattern):
    return pattern.count('(') + pattern.count('[') + pattern.count('\\')
    
def _generateRules(events, extractions):
    rules = {}
    for event in events:
        myrules = _generateEventRules(events, event, extractions)
        for rule in myrules:
            rulestr = str(rule)
            if rulestr in rules:
                extraction = rule.getSourceExtraction() # get prelim stats for fast cutting off of bad rules
                rule = rules[rulestr]
                rule.addExtraction(extraction)          # get prelim stats for fast cutting off of bad rules
            else:
                rules[rulestr] = rule
                rule.addExtraction(rule.getSourceExtraction()) # get prelim stats for fast cutting off of bad rules
            rule.incMatchCount()
    return list(rules.values())

def removeBadRules(rules, badrules):
    for br in badrules:
        if br in  rules:
            rules.remove(br)
    badrules.clear()


# remove rules that have bad patterns, like \d+(\d+)
BADPATTERNS = [] #["\\d\+\(.*?>\\\d\+\)","\\d\(.*?>\\\d\+\)","\(.*?>\\\d\+\)\\d", "\\\d\+\(.*?>\\\d\+\)","\\\d\(.*?>\\\d\+\)","\(.*?>\\\d\+\)\\\d"]

def _validateRules(events, examples, counterexamples, rules):

    totalExtractions = 0
    knownmatches = 0
    newExtractions = set()
    badrules = set()

    # for each rule
    for rule in rules:
        pattern = rule._wholePattern
        for p in BADPATTERNS:
            if re.search(p, pattern) != None:
                badrules.add(rule)
                #print("DIGIT CRAP: %s" % pattern)
                break
        # if the rule is ambiguous, remove it
        # for example: [a-z]+([a-z]+) which can get any arbitrary split
        #print("PATTERN: %s" % pattern)
        if re.search("(.+)\(\\1\)", pattern) != None:
            #print("THROWING OUT BAD RULE: %s" % pattern)
            badrules.add(rule)
            logger.debug("Removing ambiguously rule: %s" % pattern)

    # REMOVE RULES THAT HAD AMBIGUOUS REGEX
    removeBadRules(rules, badrules)

    # cutting off of bad rules with prelim stats before validation
    rules = sorted(rules, key = cmp_to_key(ruleCMP)) # (fastFirstRuleCMP)
    while len(rules) > MAX_RULES_TO_CONSIDER_BEFORE_VALIDATION:
        rules.pop()
        

    # reset the preliminary rule scores to be calc'd again after validation
    for r in rules:
        #print("%s %s %s %s" % (r.getMatchCount(), r.getScore(), r._examplesCount, r))
        r._score = None # reset the prelim score

    matchesSomething = set()
    for event in events:
        for rule in rules:
            if rule in badrules:
                continue
            extractions = rule.findExtractions(event)
            if len(extractions) > 0:
                for extraction in extractions:
                    #print("EXTRACTED: %s RULE: %s" % (extractions, rule))
                    if extraction in counterexamples:
                        badrules.add(rule)
                        logger.debug("Removing rule that learned counter example: %s Counterexample: %s" % (rule._wholePattern, extraction))
                        break
                    rule.addExtraction(extraction)
                    totalExtractions += 1
                    if extraction in examples:
                        knownmatches += 1
                        matchesSomething.add(rule)
                    else:
                        if not extraction in newExtractions:
                            newExtractions.add(extraction)

    # delete rules that don't match anything
    for rule in rules:
        if rule not in matchesSomething:
            badrules.add(rule)


    logger.debug("%s known matches out of %s total matches." % (knownmatches, totalExtractions))
    logger.debug("New values: %s" % list(newExtractions))

    removeBadRules(rules, badrules)

    return newExtractions
    

def _generateEventRules(events, event, extractions):
    rules = []
    for extraction in extractions:
        start = 0
        while True:
            start = event.find(extraction, start)
            if start < 0:
                break
            myrules = makeRules(extraction, start, event, extractions)
            rules.extend(myrules)
            start += 1
    return rules

def needsEsc(ch):
    return ".()[]{}*+^$!-\?|".find(ch) >= 0

def safeRegexLiteral(literal):
    safe = ""
    for ch in literal:
        if needsEsc(ch):
            ch = "\\" + ch
        if ch == '\t':
            ch = "\\t"
            
        safe += ch
    return safe

def getBestSkipPuncs(text, isPrefix):
    punct = GUIDEPOST_CHARACTERS

    scores = []
    l = len(text)
    for p in punct:
        thiscount = text.count(p)
        if thiscount == 0 or thiscount > MAXMATCHCOUNT:
            continue
        if isPrefix:
            thispos = text.rfind(p)
        else:
            thispos = text.find(p)
        if thispos >= 0:
            if isPrefix:
                dist = l - thispos
            else:
                dist = thispos+1
            if dist > MAXDIST:
                continue
            thisscore = dist * dist * thiscount * thiscount
            # spaces are much less reliable
            if p == ' ': thisscore *= 4
            scores.append((thispos, thisscore))
            #print("PUNCT: %s SCORE: %s DIST: %s COUNT %s" % (p, thisscore, dist, text.count(p)))
                
    scores = sorted(scores, key = lambda v: v[1])
    # return top 5 scoring jump chars pos
    return [v[0] for v in scores[:5]]

def generateSearchRegex(text):
    regex = ""
    bestpos = getBestSkipPuncs(text, True)[0]
    if bestpos >= 0:
        ch = text[bestpos]
        count = text.count(ch)
        chStr = ""
        if ch == '\t':
            chStr = "\\t"
        elif needsEsc(ch):
            chStr = "\\" + ch
        else: 
            chStr = ch
        regex = "%s" % chStr
        if count > 1:
            regex = "(?:[^%s]*%s)%s" % (chStr, chStr, "{%s}" % str(count))

        afterregex = splitText(text[bestpos+1:])
        regex = regex + afterregex
    else:
        regex = splitText(text)
    regex = regex.replace(' ', '\\s')
    return regex

def generateSimpleRegexes(text, isPrefix, multiline, loosenCount = False):

    bestpositions = getBestSkipPuncs(text, isPrefix)

    regexes = []
    for bestpos in bestpositions:
        try:
            regex = ""
            ch = text[bestpos]
            count = text.count(ch)
            chStr = ""
            if ch == '\t':
                chStr = "\\t"
            elif needsEsc(ch):
                chStr = "\\" + ch
            else: 
                chStr = ch
            countstr = ""
            if count > 1:
                if loosenCount:
                    countstr = "+"
                else:
                    countstr = "{%s}" % str(count)
            newlineRestriction = ""
            if multiline!="":
                newlineRestriction = "\\n"
            if isPrefix:
                if countstr == "":
                    regex = "[^%s%s]*%s" % (chStr, newlineRestriction, chStr)
                else:
                    regex = "(?:[^%s%s]*%s)%s" % (chStr, newlineRestriction, chStr, countstr)
            else:
                if countstr == "":
                    regex = "%s" % chStr
                else:
                    regex = "(?:%s[^%s%s]*)%s" % (chStr, newlineRestriction, chStr, countstr)
            if isPrefix:
                afterregex = splitText(text[bestpos+1:])
                regex = regex + afterregex
            else:
                beforeregex = splitText(text[:bestpos])
                regex = beforeregex + regex
            regexes.append(regex)
        except Exception as e:
            logE(e)
    else:
        try:
            regex = splitText(text)
            regexes.append(regex)
        except Exception as e:
            logE(e)            
    return regexes


def fixHex(text):
    return re.sub("(?<![0-9a-z])(?:(?:(?:\d+[a-f]+)|(?:[a-f]+\d+))[0-9a-f]*)(?![0-9a-z])", "X", text) # uppercase X (text is already lowercased)


def fixIdentifiers(types):
    oldtypes = None
    while oldtypes != types:
        oldtypes = types
        types = types.replace("[a-z]+\\d+[a-z]+", "[a-z]\\w+")
        types = types.replace("[a-z]+\\d+[a-z]", "[a-z]\\w+")
        types = types.replace("\\d+[a-z]+\\d+", "\\d+\\w+")
        types = types.replace("\\w+\\d+", "\\w+")
        types = types.replace("\\w+[a-z]+", "\\w+")
        types = types.replace("\\w+[a-z]", "\\w+")
        types = types.replace("\\w+\\w+", "\\w+")
        types = types.replace("\\w+\-\\w+", "[a-z_-]+")
        types = types.replace("\\w+_\\w+", "[a-z_-]+")
        types = types.replace("\\w+_", "\\w+")
        types = types.replace("_\\w+", "\\w+")
        types = types.replace("\\s+\-\\d", "\\s+[-+]\\d")        
        types = types.replace("\\s+\+\\d", "\\s+[-+]\\d")        
        #print("types: \n\t%s\n\t%s" % (oldtypes, types))
    return types


CHARMAP = {
'!': ('\\!', False),
'$': ('\\$', False),
'(': ('\\(', False),
')': ('\\)', False),
'*': ('\\*', False),
'+': ('\\+', False),
'-': ('\\-', False),
'.': ('\\.', False),
'0': ('\\d', True),
'1': ('\\d', True),
'2': ('\\d', True),
'3': ('\\d', True),
'4': ('\\d', True),
'5': ('\\d', True),
'6': ('\\d', True),
'7': ('\\d', True),
'8': ('\\d', True),
'9': ('\\d', True),
'?': ('\\?', False),
'X': ('[a-f0-9]', True),
'[': ('\\[', False),
'\\': ('\\\\', False),
' ': ('\\s', True),
'\n': ('\\s', True),
'\r': ('\\s', True),
'\t': ('\\t', False),
']': ('\\]', False),
'^': ('\\^', False),
'a': ('\\w', True),
'b': ('\\w', True),
'c': ('\\w', True),
'd': ('\\w', True),
'e': ('\\w', True),
'f': ('\\w', True),
'g': ('\\w', True),
'h': ('\\w', True),
'i': ('\\w', True),
'j': ('\\w', True),
'k': ('\\w', True),
'l': ('\\w', True),
'm': ('\\w', True),
'n': ('\\w', True),
'o': ('\\w', True),
'p': ('\\w', True),
'q': ('\\w', True),
'r': ('\\w', True),
's': ('\\w', True),
't': ('\\w', True),
'u': ('\\w', True),
'v': ('\\w', True),
'w': ('\\w', True),
'x': ('\\w', True),
'y': ('\\w', True),
'z': ('\\w', True),
'{': ('\\{', False),
'|': ('\\|', False),
'}': ('\\}', False),
}

split_cache = {}
def splitText(text):
    global split_cache
    if text == '': return ''
    if text in split_cache:
        return split_cache[text]
    origtext = text
    types = []
    token = ""
    lastchtype = None
    lastallowplus = False
    text = text.lower()
    text = fixHex(text)
    typelen = 0
    for ch in text:
        chtype, allowplus = CHARMAP.get(ch, (None, None))
        if chtype == None:
            CHARMAP[ch] = (ch, False)
            chtype, allowplus = ch, False
        if lastchtype != None and chtype != lastchtype:
            if lastallowplus:
                lastchtype += "+"
            types.append(lastchtype)
            typelen += 1
            token = ""
        if chtype == lastchtype and not allowplus:
            types.append(lastchtype)
            typelen += 1            
        token += ch
        lastchtype = chtype
        lastallowplus = allowplus

        if typelen > MAX_REGEX_ELEMENTS:
            #print(types)
            raise Exception("REGEX TOO LONG")

    if lastchtype != None:
        types.append(lastchtype)
    if lastallowplus:
        types.append("+")
    types = "".join(types)
    split_cache[origtext] = types
    return types



def logE(e):
    if "TOO LONG" not in str(e):
        import traceback
        logger.debug('Exception %s:\n%s' % (e, traceback.format_stack()))


def generatePatterns(event, extraction, startpos):
        end = startpos + len(extraction)
        prefix = event[0:startpos]
        suffix = event[end:]
        SOL = prefix.rfind('\n')
        EOL = suffix.find('\n')
        if EOL == len(suffix)-1: EOL = -1
        multiline = ""
        if SOL >= 0 or EOL >= 0:
            multiline = "m"
            if SOL >= 0: prefix = prefix[SOL+1:]
            if EOL >= 0: suffix = suffix[:EOL]
        
        patterns = []
        patterns.extend(generateForwardPatterns(event, extraction, multiline, end, prefix, suffix))
        patterns.extend(generateTrivialForwardPatterns(event, extraction, multiline, end, prefix, suffix))
        patterns.extend(generateBackwardPatterns(event, extraction, multiline, end, prefix, suffix))
        patterns.extend(generateForwardLiteralPatterns(event, extraction, multiline, end, prefix, suffix))
        patterns.extend(generateForwardDelimiterPatterns(event, extraction, multiline, end, prefix, suffix))
        #patterns.append(('/.*?\\.(?P<FIELDNAME>[a-z]+)\\s', 'david'))
        #patterns.append(('/.*?\\.(?P<FIELDNAME>(?:gif|html|htm|css))\\s', 'david'))
        # xxx
        return patterns

###################################################
def generateForwardPatterns(event, extraction, multiline, end, prefix, suffix):
    patterns = []
    try:
        oppositeChar = ""
        if suffix != "": oppositeChar = suffix[0]
        valueRegex, oppositeRegex = getValueRegex(extraction, True, suffix)
        if oppositeRegex == "": oppositeRegex = simpleOppositeRegex(oppositeChar, extraction)
        prefixRegexes = getPrefixRegexes(prefix, multiline, False)
        for prefixRegex in prefixRegexes:
            pattern = "(?i%s)^%s(?P<FIELDNAME>%s)%s" % (multiline, prefixRegex, valueRegex, oppositeRegex)
            pattern = fixIdentifiers(pattern)
            patterns.append((pattern, 'forward'))
    except Exception as e:
        logE(e)            
    return patterns

def generateBackwardPatterns(event, extraction, multiline, end, prefix, suffix):
    patterns = []
    try:
        oppositeChar = ""
        if prefix != "": oppositeChar = prefix[-1]        
        valueRegex, oppositeRegex = getValueRegex(extraction, False, suffix)
        suffixRegexes = generateSimpleRegexes(suffix, False, multiline)
        #print("SUFFIX: %s REGEX: %s" % (suffix, suffixRegexes))
        for suffixRegex in suffixRegexes:
            pattern = "(?i)%s(?P<FIELDNAME>%s)%s" % (oppositeRegex, valueRegex, suffixRegex)
            pattern = fixIdentifiers(pattern)        
            patterns.append((pattern, 'backward'))
    except Exception as e:
        logE(e)            
    return patterns

def generateForwardLiteralPatterns(event, extraction, multiline, end, prefix, suffix):
    patterns = []
    try:
        oppositeChar = ""
        if suffix != "": oppositeChar = suffix[0]
        valueRegex, oppositeRegex = getValueRegex(extraction, True, suffix)
        if oppositeRegex == "": oppositeRegex = simpleOppositeRegex(oppositeChar, extraction)        
        prefixRegexes = getPrefixRegexes(prefix, multiline, True)
        for prefixRegex in prefixRegexes:
            pattern = "(?i)%s(?P<FIELDNAME>%s)%s" % (prefixRegex, valueRegex, oppositeRegex)
            pattern = fixIdentifiers(pattern)
            patterns.append((pattern, 'forward-literal'))
    except Exception as e:
        logE(e)            
    return patterns





# copy of generateForwardLiteralPatterns but for much simpler patterns.
# uses GUIDEPOST chars as prefix
def generateTrivialForwardPatterns(event, extraction, multiline, end, prefix, suffix):
    patterns = []
    try:
        oppositeChar = ""
        if suffix != "": oppositeChar = suffix[0]
        valueRegex, oppositeRegex = getValueRegex(extraction, True, suffix)
        # if oppositeChar starts with well known punct/space char and that char is not in extraction use it as the oppositeText pattern
        if oppositeChar in VALUEPOST_CHARACTERS and not oppositeChar in extraction:
            oppositeRegex = "(?=%s)" % safeRegexLiteral(suffix[0])
        prefixRegexes = getPrefixRegexes(prefix, multiline, True)
        seen = set()
        for prefixRegex in prefixRegexes:
            newPrefix = ""
            for c in prefixRegex:
                if c not in GUIDEPOST_CHARACTERS:
                    if not newPrefix.endswith(".*?"):
                        newPrefix += ".*?"
                else:
                    newPrefix += c
            prefixRegex = newPrefix
            if prefixRegex not in seen:
                seen.add(prefixRegex)
                valre1 = splitText(extraction)
                valre2 = valre1.replace('\\w', '[a-z]')
                vals =  set([valre1, valre2])
                for valre in vals:
                    try:
                        pattern = "(?i)%s(?P<FIELDNAME>%s)%s" % (prefixRegex, valre, oppositeRegex)
                        pattern = fixIdentifiers(pattern)
                        re.compile(pattern)
                        patterns.append((pattern, 'forward-literal'))
                    except Exception as e:
                        pass
    except Exception as e:
        logE(e)            
    return patterns


def generateForwardDelimiterPatterns(event, extraction, multiline, end, prefix, suffix):

    patterns = []
    try:
        if suffix == '' or suffix == '\n': suffix = "$" 
        if prefix == '': prefix = '^'
        suffix = suffix[0]
        prefix = prefix[-1]
        if suffix not in extraction and prefix not in extraction:
            suffixVal = safeRegexLiteral(suffix).replace("\$", '')
            prefixVal = safeRegexLiteral(prefix).replace('\^', '')
            valueRegex, oppositeRegex = getValueRegex(extraction, True, suffix)
            pattern = "(?i)%s(?P<FIELDNAME>%s)%s" % (prefixVal, valueRegex, suffixVal)
            patterns.append((pattern, 'forward-delimiter'))
    except Exception as e:
        logE(e)            
    return patterns

def getValueRegex(extraction, forward, suffix, max_value_regex=0): #MAX_VALUE_REGEX):

    # make value extractions
    valueRegex = splitText(extraction)

    oppositeRegex = "" 
    simplifiedValueRegex = False

    # if forward rule, and there is not suffix (we're at the end
    # of the line), the value is just everything (.*)
    if forward and suffix == "":
        valueRegex = ".+"
        simplifiedValueRegex = True                    
    # if we have a suffix and the value regex is too complicated (too long)
    # try to simplify the value regex if it can be via the suffix
    elif suffix != "" and len(valueRegex) > max_value_regex:
        endchar = suffix[0]
        # interesting suffix
        if endchar in VALUEPOST_CHARACTERS:
            # and  not in the extraction or is in extraction, but 
            if not endchar in extraction:
                simplifiedValueRegex = True
                valueRegex = "[^%s]+" % safeRegexLiteral(endchar)                    
                oppositeRegex = ""
                
        # if we haven't yet simplified the value regex and we are making a forward regex
        if not simplifiedValueRegex and forward:
            # see if start of suffix isn't in value regex, do non-greed match
            for suffixTasteLen in range(1, len(suffix)):
                tasteOfSuffix = suffix[0:suffixTasteLen]
                suffixTasteRegex = splitText(tasteOfSuffix)
                # if new 'simple' suffix match more than 50% of
                # the valueregex's complexity, forget it.  it's
                # less effecient in terms of backtracking to not
                # be worth the elegance of a shorter regex, unless
                # it's really short.
                if len(suffixTasteRegex) * 2 > len(valueRegex):
                    break
                if suffixTasteRegex not in valueRegex:
                    oppositeRegex = suffixTasteRegex
                    valueRegex = ".+?"
                    break
                
    return valueRegex, oppositeRegex

def simpleOppositeRegex(oppositeChar, extraction):
    ## if oppositeChar starts with well known punct/space char and that char is not in extraction use it as the oppositeText pattern
    #if oppositeChar in VALUEPOST_CHARACTERS and not oppositeChar in extraction:
    #    return "(?=%s)" % safeRegexLiteral(oppositeChar)
    return ""

def getPrefixRegexes(prefix, multiline, literal=False):
    if literal:
        return getLiteralPrefixRegexes(prefix, multiline)
    else:
        return generateSimpleRegexes(prefix, True, multiline)            

def getLiteralPrefixRegexes(text, multiline):
    # look for meaty term before match
    l = len(text)
    foundmeat = False
    end = -1
    for pos in range(l-1, -1, -1):
        punct = text[pos] in VALUEPOST_CHARACTERS
        if not punct:
            # if prefix meat is a number, we have failed
            if text[pos].isdigit():
                break
            if not foundmeat:
                end = pos
            foundmeat = True
        if foundmeat and punct:
            break
    if foundmeat:
        meatword = text[pos+1:end+1]
        # if known bad word
        if meatword.lower() in BAD_MEAT:
            return []
        else:
            meat = safeRegexLiteral(text[pos:])
            text = "" #text[:pos]
    else:
        return []
    return [ regex + meat for regex in generateSimpleRegexes(text, True, multiline) ]
    


####################################################


def makeRules(extraction, startpos, event, examples):
    patterns = generatePatterns(event, extraction, startpos)
    rules = []
    for pattern, ruletype in patterns:
        rule = PositionalRule(pattern, extraction, examples, ruletype)
        rules.append(rule)
    return rules


class PositionalRule(object):

    def __init__(self, pattern, extraction, examples, ruletype):
        self._examplesCount = {}
        self._regex = None
        self._learnedExtractionsCount = {}

        self._wholePattern = pattern
        self._source_extraction = extraction
        self.setExamples(examples)
        #self.addExtraction(extraction)
        
        self._score = None
        self._matchCount = 0
        self._bias = 1.0
        if ruletype == "forward-literal":
            self._bias = 1.3 # bonus for literal rule
        elif ruletype.startswith('forward-delimiter'):
            self._bias = 0.7 # penalty for less reliable rule
        elif ruletype.startswith('backward'):
            self._bias = 0.7 # penalty for less reliable rule
        
    def __str__(self):
        return "regex: %s" % str("".join(self._wholePattern))

    def __hash__(self):
        return hash(str(self))
    def incMatchCount(self):
        self._matchCount += 1
    def getMatchCount(self):
        return self._matchCount
    def getSourceExtraction(self):
        return self._source_extraction
        
    def getScore(self):
        if self._score == None:
            self._score = self.calcScore()
        return self._score

    
    def extractionExpectedness(self):
        '''measure of how off the avg length of the learned extractions are from the example extractions'''
        learned = self.getLearnedCount().keys()
        examples = self.getExamplesCount().keys()
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
        ex = self.getExamplesCount()
        exampleCount = sum(ex.values())  # number of examples matched
        exampleVarietyPerc = float(sum([ 1 for v in ex.values() if v > 0]))  / len(ex)# number of examples this rule extracts
        learnedCount       = len(self.getLearnedCount())                # learned more terms
        regexSize          = len(self.getWholePattern())                   # approximate measure of regex complexity
        center = 20
        goodCount = float(max(0, center - abs(learnedCount-center)))
        if goodCount == 0 and learnedCount > 0:
            goodCount = 1

        #expectedness = self.extractionExpectedness()

        score = (10000.0*exampleVarietyPerc) + (100.0*goodCount) + (300.0/regexSize)  + 100.*exampleCount
        score *= self._bias
        if self.learnedConsistent():
            score +=500
        return score
    

    def getWholePattern(self):
        return self._wholePattern

    def getRE(self):
        if self._regex == None:
            self._regex = re.compile(self._wholePattern)
        return self._regex
    
    def setExamples(self, examples):
        self._examplesCount = {}
        for ke in examples:
            self._examplesCount[ke] = 0
            
    def getExamples(self):
        return list(self._examplesCount.keys())

    def getExamplesCount(self):
        return self._examplesCount

    def getLearnedCount(self):
        return self._learnedExtractionsCount
    
    def addExtraction(self, extraction):
        if extraction in self._examplesCount:
            self._examplesCount[extraction] += 1
        elif extraction in self._learnedExtractionsCount:
            self._learnedExtractionsCount[extraction] += 1
        else:
            self._learnedExtractionsCount[extraction] = 1

    def findExtractions(self, event):
        #return self.getRE().findall(event)
        m = self.getRE().search(event)
        if m == None:
            return []
        return [ m.group(1) ] 
