# coding: latin-1
from __future__ import print_function
from builtins import object
from builtins import range
import json
import re
from functools import wraps
from splunk.util import toUnicode, unicode
import splunk.auth
import splunk.search
import splunk.bundle 

WHITESPACE = {
        ' ': 'space',
        '\t': 'tab',
        '\v': 'vertical tab',
        '\n': 'new line',
        '\f': 'form feed character',
        '\r': 'character return'
        }


RULE_POS_MAP = {'start_rules': 0, 'extract_rules': 1, 'stop_rules': 2}


def trace(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        result = func(*args, **kwargs)
        print('%s(%r, %r) -> %r' %(func.__name__, args, kwargs, result))
        return result
    return wrapper


def mycompile(regex):
    return re.compile(regex, re.UNICODE)


IRCHAR = mycompile(r'[^\w ]') # Irregular chars are non-words and not space
ONLY_LETTERS = mycompile(r'^[a-zA-Z]+$')
ONLY_LOWERCASE_LETTERS = mycompile(r'^[a-z]+$')
ONLY_UPPERCASE_LETTERS = mycompile(r'^[A-Z]+$')
ONLY_WORDS = mycompile(r'^[\w]+$')
ONLY_NUMBERS = mycompile(r'^[\d]+$')


def myescape(s):
    return re.escape(s)
    
    
def deduplist(seq):
    ''' Deduplicate given list.
    Why assign seen.add to seen_add instead of just calling seen.add? 
    Python is a dynamic language, and resolving seen.add each iteration is more 
    costly than resolving a local variable. seen.add could have changed between iterations, 
    and the runtime isn't smart enough to rule that out. To play it safe, 
    it has to check the object each time.
    '''
    seen = set()
    seen_add = seen.add
    return [x for x in seq if not (x in seen or seen_add(x))]


class FXData(object):
    def __init__(self, require={}, option={}):
        self._require = require 
        self._option = option 

    @property
    def require(self):
        return self._require

    @require.setter
    def require(self, value):
        self._require = value

    @property
    def option(self):
        return self._option

    @option.setter
    def option(self, value):
        self._option = value

    @staticmethod
    def _check(args, against, required=True):
        ''' Helper function that checks the given args against 'against' dict.
        args will be clobbered.
        '''
        res = {}
        for rarg, (rtype, rvals) in list(against.items()):
            try:
                val = args.pop(rarg)
            except KeyError:
                if required:
                    raise Exception('Missing required argument: %s\n'%rarg)
            else:
                if rtype == 'choice':
                    if val not in rvals:
                        raise Exception("Value for %s must be one of the following: %s\n"%(rarg, rvals))
                    else:
                        res[rarg] = val
                elif rtype == 'int':
                    try:
                        rmin, rmax = rvals
                        val = int(val)
                        if val < rmin or val > rmax: raise Exception
                        res[rarg] = val
                    except:
                        raise Exception("Value for %s must be an integer between %d and %d\n"%(rarg, rmin, rmax))
                elif rtype == 'string':
                    res[rarg] = toUnicode(val)
                elif rtype == 'json':
                    try:
                        res[rarg] = json.loads(val)
                    except Exception as e:
                        raise Exception("bad json for %s: %s\n"% (rarg, args[rarg]))
        return res

    def check(self, args, ignoreOthers=False):
        '''
        Check given args against self._require and self._option. 
        If ignoreOthers is True, ignore keys and values pairs in args that are not in those two dicts.
        Note that args will be clobbered. 
        '''
        res = self._check(args, self.require)
        res.update(self._check(args, self.option, required=False))
        if args and not ignoreOthers:
            raise Exception("Unexpected argument: %r" %args)
        args.update(res)


class TableUI(object):
    def __init__(self, rankResults=True):
        self.fxd = FXData()
        self.setOptional()
        self.computeOtherData()
        self.rankResults = rankResults

    def setSessionKey(self, sessionKey):
        self.sessionKey = sessionKey
        self.setRequired()
        return self

    def setRequired(self):
        pass

    def setOptional(self):
        pass

    def computeOtherData(self):
        pass

    def checkData(self, data):
        self.fxd.check(data)
        self.data = data

    def computeResults(self, data):
        self._result = ''

    def rankRules(self, data, result):
        pass

    def results(self, data):
        self.checkData(data)
        self.computeResults(data)
        if self.rankResults:
            self.rankRules(data, self._result)
        return self._result

    @staticmethod
    def jobResults(sid, field, sessionKey, count=-1):
        try:
            job = splunk.search.getJob(sid=sid, sessionKey=sessionKey)
        except Exception as e:
            print(e.get_message_text())
            raise e
        else:
            i = 0
            for res in job.results:
                if field in res:
                    i += 1
                    yield toUnicode(repr(res[field]))
                if i == count: break


class TableUIRule(TableUI):

    def startingRegexes(self, data):
        ''' Subclass to implement
        '''
        pass

    def extractionRegexes(self, data):
        ''' Subclass to implement
        '''
        pass

    def stoppingRegexes(self, data):
        ''' Subclass to implement
        '''
        pass

    @staticmethod
    def computeRules(regexes):
        seen = set()
        seen_add = seen.add # local cache of seen.add() function, for speed
        for rex in regexes:
            if rex.valid:
                result = rex.result 
                if result['regex'] not in seen:
                    yield result
                    seen_add(result['regex'])
#                else:
#                    print('regex %s is a dup' % result['regex'])

    def computeResults(self, data):
        self._result = {
            'start_rules': list(self.computeRules(self.startingRegexes(data))),
            'extract_rules': list(self.computeRules(self.extractionRegexes(data))),
            'stop_rules': list(self.computeRules(self.stoppingRegexes(data)))
        }

    class MatchResult(object):
        '''
        Extract matched info from a re.MatchObject.
        '''
        def __init__(self, re_match):
            if not re_match:
                raise ValueError('match object is None')
            groupdict = re_match.groupdict()
            self.selectedText = list(groupdict.values())[0]
            self.selectedRange = re_match.span(list(groupdict.keys())[0])
            self.allRanges = [(re_match.start(i), re_match.end(i)) for i in range(1, re_match.lastindex+1)]
            for i in range(len(self.allRanges)-1, -1, -1):
                if self.allRanges[i][0] == self.selectedRange[0]:
                    self.selectedIndex = i
                    break

    @staticmethod
#    @trace
    def userRegex(regex_start, regex_extract, regex_stop):
        ''' Our convention is regex_start and regex_stop should contain the capture groups if any, while regex_extract doesn't.
            This function adds the capture group for regex_extract in the returned value.
        '''
        return mycompile(r'%s(?P<SELECTEDTEXT>%s)%s' %(regex_start, regex_extract, regex_stop))

    def matchResults(self, data, count):
        ''' data = dict with keys 'sid', 'field', 'regex_start', 'regex_extract', and 'regex_stop'
        '''
        user_regex = TableUIRule.userRegex(data['regex_start'], data['regex_extract'], data['regex_stop']) 
        job_results = TableUI.jobResults(data['sid'], data['field'], self.sessionKey, count=count)
        for field_value in job_results:
            mm = user_regex.match(field_value)
            if mm: yield (field_value, TableUIRule.MatchResult(mm))
    

class TableUINewRule(TableUIRule):
    ''' Usage example:
        data = {
                'sid': '123456789.012',
                'selected_text': '172.22.7.4',
                'field_value': 'Jul 24 00:03:24 172.22.7.4 %LINK-I-Up:  e13',
                'start_position': '16',
                'end_position': '26',
                'type': 'rules_new',
                'field': '_raw'
        }
        rule = TableUINewRule()
        rule.setSessionKey(sessionKey)
        results = rule.results(data)

        or just: TableUINewRule().setSessionKey(sessionKey).results(data).

        Note that setSessionKey() is required before executing results().
    '''
    def setRequired(self):
        MAX_EVENT_LENGTH = int(splunk.bundle.getConf('props', sessionKey=self.sessionKey)['default']['TRUNCATE'])
        self.fxd.require  = { \
            'sid': ('string', None),
            'selected_text': ('string', None),
            'field_value': ('string', None),
            'start_position': ('int', (0, MAX_EVENT_LENGTH)),
            'end_position': ('int', (0, MAX_EVENT_LENGTH)),
            'type': ('choice', ('rules_new')),
            'field': ('string', None),
            }

    def startingRegexes(self, data):
        return (
                NthCharacterStartingRegex(data),
                NSpacesAndStartingCharacterStartingRegex(data),
                IrregularCharactersStartingRegex(data),
                NCharactersStartingRegex(data),
                AnyCharactersStartingRegex(data),
                NSpacesAndIrregularCharactersStartingRegex(data),
                NSpacesAndPrecedingStringStartingRegex(data),
                NSpacesAndPrecedingWordStartingRegex(data),
                PrecedingWordStartingRegex(data),
                PrecedingStringStartingRegex(data),
                NCommasAndPrecedingCharacterStartingRegex(data),
                StartOfStringStartingRegex(data),
                FieldNameStartingRegex(data),
                AfterLiteralStartingRegex(data),
            )

    def extractionRegexes(self, data):
        return (
                AnyCharacterButFollowingCharacterExtractionRegex(data),
                NumberOfCharactersExtractionRegex(data),
                WordCharactersAndContainedIrregularCharactersExtractionRegex(data),
                AnyCharacterExtractionRegex(data),
                EndOfStringExtractionRegex(data),
                LettersExtractionRegex(data),
                LowercaseLettersExtractionRegex(data),
                UppercaseLettersExtractionRegex(data),
                WordCharactersExtractionRegex(data),
                NumbersExtractionRegex(data),
            )

    def stoppingRegexes(self, data):
        return (
                FollowingCharacterStoppingRegex(data),
                AnyCharacterStoppingRegex(data),
                BeforeLiteralStoppingRegex(data),
                EndOfStringStoppingRegex(data),
                NthCharacterStoppingRegex(data),
                StoppingCharacterAndNSpacesStoppingRegex(data),
                IrregularCharactersStoppingRegex(data),
                NCharactersStoppingRegex(data),
                NSpacesAndIrregularCharactersStoppingRegex(data),
                FollowStringAndNSpacesStoppingRegex(data),
                FollowWordAndNSpacesStoppingRegex(data),
                FollowWordStoppingRegex(data),
                FollowStringStoppingRegex(data),
                FollowCharacterAndNCommasStoppingRegex(data),
            )
    def rankRules(self, data, result):
        SimpleRanking(data, result, self.sessionKey).rankRules()


class SimpleRanking(object):
    def __init__(self, data, rules, sessionKey):
        self.data = data
        self.rules = rules
        self.sessionKey = sessionKey

    class RankData(object):
        def __init__(self, index):
            self.idx = index

        def indexByPos(self, pos):
            return self.idx[RULE_POS_MAP[pos]]

        @property
        def matched(self):
            return self._match

        @matched.setter
        def matched(self, value):
            self._match = value

        @property
        def matchCount(self):
            return self._matchCount

        @matchCount.setter
        def matchCount(self, value):
            self._matchCount = value

        def __repr__(self):
            return '%s matched:%s match-count=%d' %(str(self.idx), self.matched, self.matchCount)


    def indexList(self, start_rule_idx, extract_rule_idx, stop_rule_idx):
        idx = [None]*3
        idx[RULE_POS_MAP['start_rules']] = start_rule_idx
        idx[RULE_POS_MAP['extract_rules']] = extract_rule_idx
        idx[RULE_POS_MAP['stop_rules']] = stop_rule_idx
        return idx

    def generateRankData(self, numEvents=100):
        data = self.data
        job_results = list(TableUI.jobResults(data['sid'], data['field'], self.sessionKey, numEvents)) # needs to access job_results multiple times below
        for i, startRule in enumerate(self.rules['start_rules']):
            for j, extractRule in enumerate(self.rules['extract_rules']):
                for k, stopRule in enumerate(self.rules['stop_rules']):
                    user_regex = TableUIRule.userRegex(startRule['regex'], extractRule['regex'], stopRule['regex'])
                    rank_data = SimpleRanking.RankData(self.indexList(start_rule_idx=i, extract_rule_idx=j, stop_rule_idx=k))
                    try:
                        match_result = TableUIRule.MatchResult(user_regex.match(data['field_value']))
                    except ValueError:
                        rank_data.matched = False
                    else:
                        rank_data.matched = match_result.selectedText == data['selected_text']
                    match_count = sum([1 for fv in job_results if user_regex.match(fv)])
                    rank_data.matchCount = match_count
                    yield rank_data

    def findMaxRule(self, rankData):
        '''
            rankData is a list of SimpleRanking.RankData objects.
            This function returns the RankData object with matched == True and whose matchCount is max.
            Choose a random one in case there are multiple objects like that,
        '''
        matchCount = 0
        res = None
        for rd in rankData:
            if rd.matched and rd.matchCount > matchCount:
                res = rd
                matchCount = rd.matchCount
        return res

    def sortRules(self, rankData, maxRule, rulePos):
        ruleIdx = RULE_POS_MAP[rulePos]
        idx = list(range(3))
        idx.remove(ruleIdx)
        xx = [x for x in rankData if x and x.idx[idx[0]]==maxRule.idx[idx[0]] and \
                                    x.idx[idx[1]]==maxRule.idx[idx[1]]]
        return sorted(xx, key=lambda x: -x.matchCount)

    def reorgRules(self, rulePos, newOrder):
        oldRuleList = self.rules[rulePos]
        newRuleList = [oldRuleList[rankdata.indexByPos(rulePos)] for rankdata in newOrder]
        self.rules[rulePos] = newRuleList
        
    def rankRules(self):
        rankData = list(self.generateRankData())
        maxRule = self.findMaxRule(rankData)
        if not maxRule:
            return
        for rulePos in RULE_POS_MAP:
            newOrder =  self.sortRules(rankData, maxRule, rulePos)
            self.reorgRules(rulePos, newOrder)

 
class TableUIExistingRule(TableUIRule):
    ''' Usage example:
        data = {
                'sid': '123456789.012',
                'regex_start': '^[^\ ]*?\ [^\ ]*?\ [^\ ]*?\ [^\ ]*?\ [^\%]*?\%.*?',
                'regex_extract': '[^\:]+',
                'regex_stop': '\:',
                'field': '_raw',
                'type': 'rules_existing'
        }
        rule = TableUIExistingRule()
        rule.setSessionKey(sessionKey)
        results = rule.results(data)
    '''

    def setSessionKey(self, sessionKey):
        ''' overiding setSessionKey() in TableUI '''
        self._newRule.setSessionKey(sessionKey)
        self.sessionKey = sessionKey
        self.setRequired()
        return self

    def setOptional(self):
        self._newRule = TableUINewRule()


    def setRequired(self):
        self.fxd.require = {
            'sid': ('string', None),
            'regex_start': ('string', None),
            'regex_extract': ('string', None),
            'regex_stop': ('string', None),
            'type': ('choice', ('rules_existing')),
            'field': ('string', None)
            }

    def originalRule(self, data):
        '''
            Return a dictionary containing a field value together with a substring that the user
            might have selected. A TableUINewRule object will work off this dictionary to give 
            the desired results.
        '''
        for field_value, mr in self.matchResults(data, count=-1): # -1 means look at all events 
            # Use only the first matched result
            return {
                    'sid': self.data['sid'],
                    'selected_text': mr.selectedText,
                    'field_value': field_value,
                    'start_position': mr.selectedRange[0],
                    'end_position': mr.selectedRange[1],
                    'type': 'rules_new',
                    'field': self.data['field']
                    }
       
    def computeResults(self, data):
        originalRule = self.originalRule(data)
        if not originalRule:
            raise Exception('Given rule does not match any previous events\n')
        self._result = self._newRule.results(originalRule)


class TableUIEvents(TableUIRule):
    def setRequired(self):
        self.fxd.require = {
            'sid': ('string', None),
            'regex_start': ('string', None),
            'regex_extract': ('string', None),
            'regex_stop': ('string', None),
            'count': ('int', (1, 50000)),
            'type': ('choice', ('events')),
            'field': ('string', None),
            }

    def computeResults(self, data):
        self._result = []
        for field_value, mr in self.matchResults(data, count=data['count']):
            event = self.computeHighlightRanges(mr)
            event.update({'field_value': field_value})
            self._result.append(event)
        if not self._result: 
            self._result = 'No matched events' 


    def computeHighlightRanges(self, matchResult):
        selected_index = matchResult.selectedIndex
        all_ranges = matchResult.allRanges
        return { 'pre_highlight_ranges': all_ranges[:selected_index],
                 'highlight_range': all_ranges[selected_index],
                 'post_highlight_ranges': all_ranges[selected_index+1:]
                }


class TableUIRegex(object):
    '''
        Base class for Starting, Extraction and Stopping regex classes.
        Each of them needs to implement the setResult() method in order
        to get the desired behavior.
    '''
    def __init__(self, data):
        self.data = data
        self.valid = False
        self.result = {}
        self.setResult()

    @property
    def fullText(self):
        return self.data['field_value']

    @property 
    def selectedText(self):
        return self.data['selected_text']

    @property
    def startPos(self):
        return self.data['start_position']

    @property
    def endPos(self):
        return self.data['end_position']

    def setResult(self):
        ''' Subclasses need to implement this method and set the self.result dict
        '''
        pass 

    def extractIrregularChars(self, s, dedup=False):
        ''' Returns all 'irregular characters' in s - usually punctuation but can be more, e.g. unicode chars.
            Can pass optional parameter shouldDedup=true/false to deduplicate the characters.
        '''
        irregulars = IRCHAR.findall(s)
        if dedup: return ''.join(deduplist(irregulars))
        return ''.join(irregulars)

    @classmethod
    def getRegex(cls, data):
        return cls(data)

    def setLabel(self, label, metadata=None):
        if not metadata: metadata = {}
        self.label = {'label': label, 'metadata': metadata}


class SegmentRegex(TableUIRegex):
    '''
        Base class of all the Starting and Stopping regex classes. Each of them needs to 
        implement the setPatternAndLabel() method and perhaps the setRegExp() method to 
        get the desired behavior.
    '''
    def __init__(self, data, before=True):
        self.before = before
        TableUIRegex.__init__(self, data)

    def setResult(self):
        self._str = self.fullText[:self.startPos] if self.before else self.fullText[self.endPos:]
        if self._str:
            self._char = self._str[-1] if self.before else self._str[0]
        else:
            self._char = ''
        self.initPatternAndLabel()
        self.setPatternAndLabel()
        self.setRegExp() # setRegExp() must not be called before setPatternAndLabel()
        self.result.update({
                'type': self.label,
                'regex': self.regExp,
                })

    def setRegExp(self):
        '''
            Most Starting Regex classes need not overide this method. However, some Regex classes
            set the regExp directly without going through the generateRegExp() method.
            These classes need to implement this method to get the desired behavior.
        '''
        if self.valid:
            self.regExp = self.generateRegExp(self.pattern)

    def setPattern(self, pat, anchorStr=None):
        self.pattern.pat = pat
        self.pattern.anchorStr = anchorStr

    def initPatternAndLabel(self):
        ''' Initialize pattern and type
        '''
        self.pattern = SegmentRegex.Pattern() 
        self.regExp = ''
        self.label = {}

    def setPatternAndLabel(self):
        ''' Set pattern and label fields. To be implemented by subclasses.
        '''
        pass 

    @property
    def segment(self):
        return self._str

    @property
    def anchorChar(self):
        return self._char

    @property
    def anchorCharName(self):
        if self.anchorChar in WHITESPACE:
            return WHITESPACE[self.anchorChar]
        return self.anchorChar

    def countChar(self, c):
        return self.segment.count(c)

    def anchorCharCount(self):
        return self.countChar(self.anchorChar)

    def anchorCharIs(self, c):
        return self.anchorChar ==  c

    def anchorCharIsIrregular(self):
        return IRCHAR.match(self.anchorChar)

    def extractFieldName(self):
        if self.anchorCharIs('=') or self.anchorCharIs(':'):
            s = self.segment[:-1] if self.before else self.segment[1:]
            return self.extractWord(s)
        return ''
    
    def irregularCharsFromChar(self, c, dedup=False):
        '''
            Finds the latest (or first if self.before=False) instance of c in string, 
            then takes all irregular from that character to the end (or start if self.before=False).
        '''
        s = self.segment
        pos = (s.rfind(c) + 1) if self.before else s.find(c)
        if pos == -1:
            pos = None
        res = self.extractIrregularChars(s[pos:], dedup) if self.before else \
                self.extractIrregularChars(s[:pos], dedup)
        return res

    def irregularCharsFromSpace(self):
        if self.countChar(' ') > 0:
            return self.irregularCharsFromChar(' ')
        return ''
        
    def irregularChars(self):
        return self.extractIrregularChars(self.segment)

    def stringFromChar(self, c, skipSpace=False):
        s = self.segment
        if skipSpace:
            s = s.rstrip() if self.before else s.strip()
        pos = (s.rfind(c) + 1) if self.before else s.find(c)
        if pos == -1:
            pos = None
        res = self.segment[pos:] if self.before else self.segment[:pos]
        return res

    def stringFromSpace(self, skipSpace=False):
        return self.stringFromChar(' ', skipSpace)

    def extractWord(self, s, ignoreIrregular=False):
        '''
            Returns the closest word to the anchor char.
            If ignoreIrregular=True, skip the irrgular chars at the start (if self.before=True) 
            or at the end (if self.before=False) until a word is found.
            Otherwise, returns nothing if there are irregular chars at the start (if self.before=True) 
            or at the end (if self.before=False).
        '''
        rex = r'(\w+)\W*?' if ignoreIrregular else r'(\w+)' 
        rex = (rex + '$') if self.before else ('^' + rex)
        result = mycompile(rex).search(s)
        result = result.group(1) if result else ''
        return result

    class Pattern(object):
        def __init__(self, pat='', anchorStr=''):
            self.pat = pat
            self.anchorStr = anchorStr

        def __repr__(self):
            return 'pat = {} anchorStr = {}'.format(repr(self.pat), repr(self.anchorStr)) 

    def generateRegExp1(self, pattern):
        regExp = ['^']
        regExp.extend(['[^%s]*?(%s)'%(ch, ch) for ch in map(myescape, pattern.pat)])
        if pattern.anchorStr:
            if pattern.anchorStr[-1] == ' ':
                anchorStr = pattern.anchorStr.rstrip()
                regExp.append('.*?(%s)\ *?'%myescape(anchorStr) if anchorStr else '.*?\ *?')
            else:
                regExp.append('.*?(%s)'%myescape(pattern.anchorStr))
        return ''.join(regExp)

    def generateRegExp2(self, pattern):
        if pattern.anchorStr:
            if pattern.anchorStr[0] == ' ':
                anchorStr = pattern.anchorStr.lstrip()
                regExp = ['\ *?(%s).*?'%myescape(anchorStr)] if anchorStr else ['\ *?.*?']
            else:
                regExp = [('(%s).*?'%myescape(pattern.anchorStr))]
        else:
            regExp = []
        regExp.extend(['(%s)[^%s]*?'%(ch, ch) for ch in map(myescape, pattern.pat)])
        regExp.append('$')
        return ''.join(regExp)

    def generateRegExp(self, pattern):
        return self.generateRegExp1(pattern) if self.before else self.generateRegExp2(pattern)


class StartRegex(SegmentRegex):
    def __init__(self, data):
        SegmentRegex.__init__(self, data, before=True)
    
    @property
    def precedingCharCount(self):
        return self.anchorCharCount()

    @property
    def precedingChar(self):
        return self.anchorChar

    @property
    def precedingStr(self):
        return self.segment

    @property
    def precedingCharName(self):
        return self.anchorCharName

    @property
    def precedingSpaceCount(self):
        return self.countChar(' ')

    @property
    def precedingCharIsSpace(self):
        return self.anchorCharIs(' ')

    @property
    def precedingCharIsIrregular(self):
        return self.anchorCharIsIrregular()

    @property
    def precedingIrregularChars(self):
        return self.irregularChars()

    @property
    def precedingIrregularCharsAfterSpace(self):
        return self.irregularCharsFromSpace()

    def precedingStringAfterSpace(self, skipSpace=False):
        return self.stringFromSpace(skipSpace)

    @property
    def precedingWord(self):
        return self.extractWord(self.precedingStr)

    def precedingCommaCount(self):
        return self.countChar(',')

    @property
    def precedingCharIsComma(self):
        return self.anchorCharIs(',')

    @property
    def precedingFieldName(self):
        return self.extractFieldName()


class NthCharacterStartingRegex(StartRegex):
    def setPatternAndLabel(self):
        preCharCount = self.precedingCharCount
        self.valid = preCharCount > 1
        if self.valid:
            self.setPattern(self.precedingChar*preCharCount)
            self.setLabel('nth_character', {'preCharCount': preCharCount, 'preCharName': self.precedingCharName})


class NSpacesAndStartingCharacterStartingRegex(StartRegex):
    def setPatternAndLabel(self):
        self.valid = self.precedingSpaceCount and not self.precedingCharIsSpace
        if self.valid:
            self.setPattern(' '*self.precedingSpaceCount + self.precedingChar)
            self.setLabel('n_spaces_and_starting_character', {'preSpaceCount': self.precedingSpaceCount, 'preChar': self.precedingChar})


class IrregularCharactersStartingRegex(StartRegex):
    def setPatternAndLabel(self):
        if not self.precedingCharIsIrregular: 
            return
        preIrregChars = self.precedingIrregularChars
        self.valid = len(preIrregChars) < 10
        if self.valid:
            self.setPattern(preIrregChars)
            self.setLabel('irregular_characters', {'preIrregChars': preIrregChars})


class NCharactersStartingRegex(StartRegex):
    def setPatternAndLabel(self):
        self.valid = self.startPos > 0
        if self.valid:
            self.setLabel('n_characters', {'preStrLength': len(self.precedingStr)})

    def setRegExp(self):
        preStrLen = len(self.precedingStr)
        self.regExp = '^.{%d}'%preStrLen


class AnyCharactersStartingRegex(StartRegex):
    def setPatternAndLabel(self):
        self.valid = self.startPos > 0
        if self.valid:
            self.setLabel('any_characters')

    def setRegExp(self):
        self.regExp = '.*?'

 
class NSpacesAndIrregularCharactersStartingRegex(StartRegex):
    def setPatternAndLabel(self):
        preSpaceCount = self.precedingSpaceCount
        preIrregCharsAfterSpace = self.precedingIrregularCharsAfterSpace
        self.valid = (preSpaceCount > 0) and (len(preIrregCharsAfterSpace) > 1) and (len(preIrregCharsAfterSpace) < 10)
        if self.valid:
            pattern = ' '*preSpaceCount + preIrregCharsAfterSpace
            self.setPattern(pattern)
            self.setLabel('n_spaces_and_irregular_characters', {'preSpaceCount': preSpaceCount, 'preIrregCharsAfterSpace': preIrregCharsAfterSpace})


class NSpacesAndPrecedingStringStartingRegex(StartRegex):
    def setPatternAndLabel(self):
        preSpaceCount = self.precedingSpaceCount
        preStrAfterSpace = self.precedingStringAfterSpace()
        preIrregCharsAfterSpace = self.precedingIrregularCharsAfterSpace
        self.valid = (preSpaceCount > 0) and \
                     (len(preStrAfterSpace) > 1) and \
                     (len(preStrAfterSpace) < 30) and \
                     (preStrAfterSpace != preIrregCharsAfterSpace)
        if self.valid:
            pattern = ' '*preSpaceCount
            self.setPattern(pattern, preStrAfterSpace)
            self.setLabel('n_spaces_and_preceding_string', {'preSpaceCount': preSpaceCount, 'preStrAfterSpace': preStrAfterSpace})


class NSpacesAndPrecedingWordStartingRegex(StartRegex):
    def setPatternAndLabel(self):
        preSpaceCount = self.precedingSpaceCount
        preWord = self.precedingWord
        preIrregCharsAfterSpace = self.precedingIrregularCharsAfterSpace
        self.valid = preSpaceCount and preWord
        if self.valid:
            pattern = ' '*preSpaceCount + preIrregCharsAfterSpace
            self.setPattern(pattern, preWord) 
            self.setLabel('n_spaces_and_preceding_word', {'preSpaceCount': preSpaceCount, 'preWord': preWord})


class PrecedingWordStartingRegex(StartRegex):
    def setPatternAndLabel(self):
        preWord = self.precedingWord
        self.valid = bool(preWord)
        if self.valid:
            self.setPattern('', preWord)
            self.setLabel('preceding_word', {'preWord': preWord})


class PrecedingStringStartingRegex(StartRegex):
    def setPatternAndLabel(self):
        preStrAfterSpace = self.precedingStringAfterSpace()
        preWord = self.precedingWord
        if not preStrAfterSpace or not preWord: return
        self.valid = (not preWord) and (len(preStrAfterSpace) > 1) and (len(preStrAfterSpace) < 30)
        if self.valid:
            self.setPattern('', preStrAfterSpace)
            self.setLabel('preceding_string', {'preStrAfterSpace': preStrAfterSpace})


class NCommasAndPrecedingCharacterStartingRegex(StartRegex):
    def setPatternAndLabel(self):
        preCommaCount = self.precedingCommaCount()
        self.valid = (preCommaCount > 0) and not self.precedingCharIsComma
        if self.valid:
            self.setPattern(','*preCommaCount, self.precedingChar)
            self.setLabel('n_commas_and_preceding_character', {'preCommaCount': preCommaCount, 'preCharName': self.precedingCharName}) 


class StartOfStringStartingRegex(StartRegex):
    def setPatternAndLabel(self):
        self.valid = self.startPos == 0
        if self.valid:
            self.setLabel('start_of_string')

    def setRegExp(self):
        self.regExp = '^'


class FieldNameStartingRegex(StartRegex):
    def setPatternAndLabel(self):
        preFieldName = self.precedingFieldName
        preFieldNamePlusChar = preFieldName + self.precedingChar 
        self.valid = bool(preFieldName)
        if self.valid:
            self.setPattern('', preFieldNamePlusChar)
            self.setLabel('field_name', {'preFieldNameAndChar': preFieldNamePlusChar})


class AfterLiteralStartingRegex(StartRegex):
    def setPatternAndLabel(self):
        preStrAfterSpace = self.precedingStringAfterSpace(skipSpace=True)
        literal = preStrAfterSpace if preStrAfterSpace else self.precedingStr
        self.valid = bool(literal)
        if self.valid:
            self.setPattern('', literal)
            self.setLabel('after_literal', {'literal': literal})


class ExtractionRegex(TableUIRegex):
    '''
        Base class of all Extraction Regex classes. Each of them must implement the setLabelRegex() methods.
    '''
    def setResult(self):
        self.setLabelRegex()
        if self.valid:
            self.result.update({
                    'type': self.label,
                    'regex': self.regExp,
                }) 

    def setLabelRegex(self):
        ''' Subclass to set label, regExp
        '''
        self.regExp = ''

    def containsEnd(self):
        ''' Does selected text reach the end of the full text? 
        '''
        return self.endPos >= len(self.fullText)

    def followingStr(self):
        if self.containsEnd(): return ''
        return self.fullText[self.endPos:]

    def followingStringBeforeSpace(self, skipSpace=False):
        ''' Extract the string that follows the selected text, up to a space. 
        Extract to the end if no space exists.
        '''
        afterStr = self.fullText[self.endPos:]
        if skipSpace:
            afterStr = afterStr.lstrip()
        spacePos = afterStr.find(' ')
        if spacePos == -1:
            return afterStr
        else:
            return afterStr[:spacePos]

    def followingChar(self):
        if self.containsEnd(): return ''
        return self.fullText[self.endPos]

    def followingCharName(self):
        followChar = self.followingChar()
        if followChar in WHITESPACE:
            return WHITESPACE[followChar]
        return followChar

    def containsFollowingChar(self):
        return self.selectedText.find(self.followingChar()) != -1

    @property
    def irregularChars(self):
        return self.extractIrregularChars(self.selectedText)

    @property
    def uniqueIrregularChars(self):
        return self.extractIrregularChars(self.selectedText, dedup=True)

    def containsIrregularChars(self):
        return len(self.irregularChars) > 0
    
    def containsSpace(self):
        return (' ' in self.selectedText)


class AnyCharacterButFollowingCharacterExtractionRegex(ExtractionRegex):
    def setLabelRegex(self):
        follChar = self.followingChar()
        follCharName = self.followingCharName()
        self.valid = (follChar != '') and not self.containsFollowingChar()
        if self.valid:
            self.setLabel('any_character_but_following_character', {'followCharName': follCharName})
            self.regExp = '[^%s]+'%myescape(follChar)


class NumberOfCharactersExtractionRegex(ExtractionRegex):
    def setLabelRegex(self):
        self.valid = True # always return this regex 
        selectLen = len(self.selectedText)
        self.setLabel('number_of_characters', {'selectedTextLength': selectLen})
        self.regExp = '.{%d}'%selectLen


class WordCharactersAndContainedIrregularCharactersExtractionRegex(ExtractionRegex):
    def setLabelRegex(self):
        self.valid = self.containsIrregularChars() and not self.containsFollowingChar() \
                    and not self.containsSpace()
        if self.valid:
            uniqueIrregularChars = self.uniqueIrregularChars
            self.setLabel('word_characters_and_contained_irregular_characters', {'uniqueIrregChars': uniqueIrregularChars})
            self.regExp = '[\\w%s\ ]+'%myescape(uniqueIrregularChars)


class AnyCharacterExtractionRegex(ExtractionRegex):
    def setLabelRegex(self):
        self.valid = self.endPos < len(self.fullText)
        if self.valid:
            self.setLabel('any_character')
            self.regExp = '.+'


class EndOfStringExtractionRegex(ExtractionRegex):
    def setLabelRegex(self):
        self.valid = self.endPos == len(self.fullText)
        if self.valid:
            self.setLabel('end_of_string')
            self.regExp = '.+$'


class LettersExtractionRegex(ExtractionRegex):
    def setLabelRegex(self):
        self.valid = ONLY_LETTERS.match(self.selectedText)
        if self.valid:
            self.setLabel('letters')
            self.regExp = '[a-zA-Z]+'


class LowercaseLettersExtractionRegex(ExtractionRegex):
    def setLabelRegex(self):
        self.valid = ONLY_LOWERCASE_LETTERS.match(self.selectedText)
        if self.valid:
            self.setLabel('lowercase_letters')
            self.regExp = '[a-z]+'


class UppercaseLettersExtractionRegex(ExtractionRegex):
    def setLabelRegex(self):
        self.valid = ONLY_UPPERCASE_LETTERS.match(self.selectedText)
        if self.valid:
            self.setLabel('uppercase_letters')
            self.regExp = '[A-Z]+'


class WordCharactersExtractionRegex(ExtractionRegex):
    def setLabelRegex(self):
        self.valid = ONLY_WORDS.match(self.selectedText)
        if self.valid:
            self.setLabel('word_characters')
            self.regExp = '\\w+'


class NumbersExtractionRegex(ExtractionRegex):
    def setLabelRegex(self):
        self.valid = ONLY_NUMBERS.match(self.selectedText)
        if self.valid:
            self.setLabel('numbers')
            self.regExp = '\\d+'


class StopRegex(SegmentRegex):
    def __init__(self, data):
        SegmentRegex.__init__(self, data, before=False)
    
    @property
    def followCharCount(self):
        return self.anchorCharCount()

    @property
    def followChar(self):
        return self.anchorChar

    @property
    def followStr(self):
        return self.segment

    @property
    def followCharName(self):
        return self.anchorCharName

    @property
    def followSpaceCount(self):
        return self.countChar(' ')

    @property
    def followCharIsSpace(self):
        return self.anchorCharIs(' ')

    @property
    def followCharIsIrregular(self):
        return self.anchorCharIsIrregular()

    @property
    def followIrregularChars(self):
        return self.irregularChars()

    @property
    def followIrregularCharsBeforeSpace(self):
        return self.irregularCharsFromSpace()

    def followStringBeforeSpace(self, skipSpace=False):
        return self.stringFromSpace(skipSpace)

    @property
    def followWord(self):
        return self.extractWord(self.segment)

    def followCommaCount(self):
        return self.countChar(',')

    @property
    def followCharIsComma(self):
        return self.anchorCharIs(',')

    @property
    def followFieldName(self):
        return self.extractFieldName()

    def containsFollowingChar(self):
        return self.selectedText.find(self.followChar) != -1


class NthCharacterStoppingRegex(StopRegex):
    def setPatternAndLabel(self):
        follCharCount = self.followCharCount
        self.valid = follCharCount > 1
        if self.valid:
            self.setPattern(self.followChar*follCharCount)
            self.setLabel('nth_character', {'stopCharCount': follCharCount, 'stopCharName': self.followCharName})


class StoppingCharacterAndNSpacesStoppingRegex(StopRegex):
    def setPatternAndLabel(self):
        self.valid = self.followSpaceCount and not self.followCharIsSpace
        if self.valid:
            self.setPattern(self.followChar + ' '*self.followSpaceCount)
            self.setLabel('stopping_character_and_n_spaces', {'followSpaceCount': self.followSpaceCount, 'stopChar': self.followChar})


class IrregularCharactersStoppingRegex(StopRegex):
    def setPatternAndLabel(self):
        if not self.followCharIsIrregular: 
            return
        follIrregChars = self.followIrregularChars
        self.valid = len(follIrregChars) < 10
        if self.valid:
            self.setPattern(follIrregChars)
            self.setLabel('irregular_characters', {'followIrregChars': follIrregChars})


class NCharactersStoppingRegex(StopRegex):
    def setPatternAndLabel(self):
        self.valid = self.endPos < len(self.fullText)
        if self.valid:
            self.setLabel('n_characters', {'followStrLength': len(self.followStr)})

    def setRegExp(self):
        follStrLen = len(self.followStr)
        self.regExp = '.{%d}$'%follStrLen


class NSpacesAndIrregularCharactersStoppingRegex(StopRegex):
    def setPatternAndLabel(self):
        follSpaceCount = self.followSpaceCount
        follIrregCharsBeforeSpace = self.followIrregularCharsBeforeSpace
        self.valid = (follSpaceCount > 0) and (len(follIrregCharsBeforeSpace) > 1) and (len(follIrregCharsBeforeSpace) < 10)
        if self.valid:
            pattern = follIrregCharsBeforeSpace + ' '*follSpaceCount
            self.setPattern(pattern)
            self.setLabel('irregular_characters_and_n_spaces', {'followSpaceCount': follSpaceCount, 'followIrregCharsAfterSpace': follIrregCharsBeforeSpace})


class FollowStringAndNSpacesStoppingRegex(StopRegex):
    def setPatternAndLabel(self):
        follSpaceCount = self.followSpaceCount
        follStrBeforeSpace = self.followStringBeforeSpace()
        follIrregCharsBeforeSpace = self.followIrregularCharsBeforeSpace
        self.valid = (follSpaceCount > 0) and \
                     (len(follStrBeforeSpace) > 1) and \
                     (len(follStrBeforeSpace) < 30) and \
                     (follStrBeforeSpace != follIrregCharsBeforeSpace)
        if self.valid:
            pattern = ' '*follSpaceCount
            self.setPattern(pattern, follStrBeforeSpace)
            self.setLabel('following_string_and_n_spaces', {'followSpaceCount': follSpaceCount, 'followStrBeforeSpace': follStrBeforeSpace})


class FollowWordAndNSpacesStoppingRegex(StopRegex):
    def setPatternAndLabel(self):
        follSpaceCount = self.followSpaceCount
        follWord = self.followWord
        follIrregCharsBeforeSpace = self.followIrregularCharsBeforeSpace
        self.valid = follSpaceCount and follWord
        if self.valid:
            pattern = ' '*follSpaceCount + follIrregCharsBeforeSpace
            self.setPattern(pattern, follWord) 
            self.setLabel('following_word_and_n_spaces', {'followSpaceCount': follSpaceCount, 'followWord': follWord})


class FollowWordStoppingRegex(StopRegex):
    def setPatternAndLabel(self):
        follWord = self.followWord
        self.valid = bool(follWord)
        if self.valid:
            self.setPattern('', follWord)
            self.setLabel('following_word', {'followWord': follWord})


class FollowStringStoppingRegex(StopRegex):
    def setPatternAndLabel(self):
        follStrBeforeSpace = self.followStringBeforeSpace()
        follWord = self.followWord
        if not follStrBeforeSpace or not follWord: return
        self.valid = (not follWord) and (len(follStrBeforeSpace) > 1) and (len(follStrBeforeSpace) < 30)
        if self.valid:
            self.setPattern('', follStrBeforeSpace)
            self.setLabel('following_string', {'follStrBeforeSpace': follStrBeforeSpace})


class BeforeLiteralStoppingRegex(StopRegex):
    def setPatternAndLabel(self):
        followStrBeforeSpace = self.followStringBeforeSpace(skipSpace=True)
        self.valid = bool(followStrBeforeSpace)
        if self.valid:
            self.setPattern('', followStrBeforeSpace)
            self.setLabel('before_literal', {'literal': followStrBeforeSpace})


class FollowCharacterAndNCommasStoppingRegex(StopRegex):
    def setPatternAndLabel(self):
        follCommaCount = self.followCommaCount()
        self.valid = follCommaCount and not self.followCharIsComma
        if self.valid:
            self.setPattern(','*follCommaCount, self.followChar)
            self.setLabel('following_character_and_n_commas', {'followCommaCount': follCommaCount, 'followCharName': self.followCharName}) 


class EndOfStringStoppingRegex(StopRegex):
    def setPatternAndLabel(self):
        self.valid = self.endPos == len(self.fullText)
        if self.valid:
            self.setLabel('end_of_string')

    def setRegExp(self):
        self.regExp = '$'


class FollowingCharacterStoppingRegex(StopRegex):
    def setPatternAndLabel(self):
        followChar = self.followChar
        self.valid = followChar and not self.containsFollowingChar()
        if self.valid:
            self.setLabel('following_characters', {'followChars': followChar})
            self.setPattern('', followChar)


class AnyCharacterStoppingRegex(StopRegex):
    def setRegExp(self):
        self.regExp = '.*?$'

    def setPatternAndLabel(self):
        self.valid = True
        self.setLabel('any_characters')



import unittest
import pprint
import sys
import timeit
from time import time

def myprint(some_obj, fout=sys.stdout):
    fout.write(json.dumps(some_obj, indent=3, ensure_ascii=False) + "\n")


class Timer(object):
    '''
    Usage: timer = Timer()
           timer.start()
           // code
           timer.stop()
    '''
    def __init__(self):
        self.t0 = None

    def start(self):
        self.t0 = timeit.default_timer()

    def stop(self):
        print('done in %0.3fs.'%(timeit.default_timer() - self.t0))


def timethis(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        start = timeit.default_timer()
        r = func(*args, **kwargs)
        end = timeit.default_timer()
        print("Done in {:0.3f}s".format(end-start))
        return r
    return wrapper


class Test(unittest.TestCase):
#    @timethis
    def __init__(self, *arg, **kwargs):
        self.timer = Timer()
        super(Test, self).__init__(*arg, **kwargs)
        owner = 'admin'
        self.hostPath='https://wimpy.splunk.com:9040'
        self.sessionKey = splunk.auth.getSessionKey('admin', 'changeme', hostPath=self.hostPath)
        query = 'search source="/home/nnguyen/mydata/alcatel.1k.log"'
        job = splunk.search.dispatch(query, hostPath=self.hostPath, sessionKey=self.sessionKey)
        self.sid = job.sid
        self.maxDiff = None
        class NewRule(TableUINewRule):
            '''
                Define this class here so that adding more match rules in the future
                won't break these tests.
            '''
            def startingRegexes(self, data):
                return (
                        NthCharacterStartingRegex(data),
                        NSpacesAndStartingCharacterStartingRegex(data),
                        IrregularCharactersStartingRegex(data),
                        NCharactersStartingRegex(data),
                        AnyCharactersStartingRegex(data),
                        NSpacesAndIrregularCharactersStartingRegex(data),
                        NSpacesAndPrecedingStringStartingRegex(data),
                        NSpacesAndPrecedingWordStartingRegex(data),
                        PrecedingWordStartingRegex(data),
                        PrecedingStringStartingRegex(data),
                        NCommasAndPrecedingCharacterStartingRegex(data),
                        StartOfStringStartingRegex(data),
                        FieldNameStartingRegex(data),
                        AfterLiteralStartingRegex(data),
                    )
            def extractionRegexes(self, data):
                return (
                        AnyCharacterButFollowingCharacterExtractionRegex(data),
                        NumberOfCharactersExtractionRegex(data),
                        WordCharactersAndContainedIrregularCharactersExtractionRegex(data),
                        AnyCharacterExtractionRegex(data),
                        EndOfStringExtractionRegex(data),
                        LettersExtractionRegex(data),
                        LowercaseLettersExtractionRegex(data),
                        UppercaseLettersExtractionRegex(data),
                        WordCharactersExtractionRegex(data),
                        NumbersExtractionRegex(data),
                    )
            def stoppingRegexes(self, data):
                return (
                        FollowingCharacterStoppingRegex(data),
                        AnyCharacterStoppingRegex(data)
                    )

        class ExistingRule(TableUIExistingRule):
            def setOptional(self):
                self._newRule = NewRule()

        self._newRule = NewRule()
        self._newRule.setSessionKey(self.sessionKey)
        self._existingRule = ExistingRule()
        self._existingRule.setSessionKey(self.sessionKey)

    def case1(self):
        required_args = {
            'selected_text': ('string', None),
            'field_value': ('string', None),
            'start_position': ('int', (0, 1000)),
            'end_position': ('int', (0, 1000)),
            }
        fxa = FXData(require=required_args)
        args = {
            'field_value': 'Introduction to Probability',
            'selected_text': 'Probability',
            'start_position': '16',
            'end_position': '27',
            }
        fxa.check(args) 
        correct = {
            'field_value': 'Introduction to Probability',
            'selected_text': 'Probability',
            'start_position': 16,
            'end_position': 27
            }
        self.assertEqual(args, correct)

#    @timethis
    def case2(self):
        data = {
                'sid': self.sid,
                'selected_text': 'STP-W-PORTSTATUS',
                'field_value': 'Jul 24 00:03:05 172.22.98.4 %STP-W-PORTSTATUS: e4: STP status Forwarding',
                'start_position': '29',
                'end_position': '45',
                'type': 'rules_new',
                'field': '_raw'
        }
        results = self._newRule.results(data)
        correct = \
        {
           "start_rules": [
              {
                 "regex": "^[^\\ ]*?(\\ )[^\\ ]*?(\\ )[^\\ ]*?(\\ )[^\\ ]*?(\\ )[^\\%]*?(\\%)", 
                 "type": {
                    "metadata": {
                       "preSpaceCount": 4, 
                       "preChar": "%"
                    }, 
                    "label": "n_spaces_and_starting_character"
                 }
              }, 
              {
                 "regex": "^[^\\:]*?(\\:)[^\\:]*?(\\:)[^\\.]*?(\\.)[^\\.]*?(\\.)[^\\.]*?(\\.)[^\\%]*?(\\%)", 
                 "type": {
                    "metadata": {
                       "preIrregChars": "::...%"
                    }, 
                    "label": "irregular_characters"
                 }
              }, 
              {
                 "regex": "^.{29}", 
                 "type": {
                    "metadata": {
                       "preStrLength": 29
                    }, 
                    "label": "n_characters"
                 }
              }, 
              {
                 "regex": ".*?", 
                 "type": {
                    "metadata": {}, 
                    "label": "any_characters"
                 }
              }, 
              {
                 "regex": "^.*?(\\%)", 
                 "type": {
                    "metadata": {
                       "literal": "%"
                    }, 
                    "label": "after_literal"
                 }
              }
           ], 
           "stop_rules": [
              {
                 "regex": "(\\:).*?$", 
                 "type": {
                    "metadata": {
                       "followChars": ":"
                    }, 
                    "label": "following_characters"
                 }
              }, 
              {
                 "regex": ".*?$", 
                 "type": {
                    "metadata": {}, 
                    "label": "any_characters"
                 }
              }
           ], 
           "extract_rules": [
              {
                 "regex": "[^\\:]+", 
                 "type": {
                    "metadata": {
                       "followCharName": ":"
                    }, 
                    "label": "any_character_but_following_character"
                 }
              }, 
              {
                 "regex": "[\\w\\-\\ ]+", 
                 "type": {
                    "metadata": {
                       "uniqueIrregChars": "-"
                    }, 
                    "label": "word_characters_and_contained_irregular_characters"
                 }
              }, 
              {
                 "regex": ".+", 
                 "type": {
                    "metadata": {}, 
                    "label": "any_character"
                 }
              }, 
              {
                 "regex": ".{16}", 
                 "type": {
                    "metadata": {
                       "selectedTextLength": 16
                    }, 
                    "label": "number_of_characters"
                 }
              }
           ]
        }
        self.assertEqual(results, correct)

    def case3(self):
        data = {
                'sid': self.sid,
                'selected_text': '172.22.7.4',
                'field_value': 'Jul 24 00:03:24 172.22.7.4 %LINK-I-Up:  e13',
                'start_position': '16',
                'end_position': '26',
                'type': 'rules_new',
                'field': '_raw'
        }
        results = self._newRule.results(data)
        correct = \
        {
           "extract_rules": [
              {
                 "type": {
                    "label": "any_character_but_following_character", 
                    "metadata": {
                       "followCharName": "space"
                    }
                 }, 
                 "regex": "[^\\ ]+"
              }, 
              {
                 "type": {
                    "label": "number_of_characters", 
                    "metadata": {
                       "selectedTextLength": 10
                    }
                 }, 
                 "regex": ".{10}"
              }, 
              {
                 "type": {
                    "label": "word_characters_and_contained_irregular_characters", 
                    "metadata": {
                       "uniqueIrregChars": "."
                    }
                 }, 
                 "regex": "[\\w\\.\\ ]+"
              }, 
              {
                 "type": {
                    "label": "any_character", 
                    "metadata": {}
                 }, 
                 "regex": ".+"
              }
            ],
            "stop_rules": [
              {
                 "regex": "\\ *?.*?$", 
                 "type": {
                    "label": "following_characters", 
                    "metadata": {
                       "followChars": " "
                    }
                 }
              }, 
              {
                 "regex": ".*?$", 
                 "type": {
                    "label": "any_characters", 
                    "metadata": {}
                 }
              }
           ], 
           "start_rules": [
              {
                 "regex": "^[^\\ ]*?(\\ )[^\\ ]*?(\\ )[^\\ ]*?(\\ )", 
                 "type": {
                    "label": "nth_character", 
                    "metadata": {
                       "preCharCount": 3, 
                       "preCharName": "space"
                    }
                 }
              }, 
              {
                 "regex": "^.{16}", 
                 "type": {
                    "label": "n_characters", 
                    "metadata": {
                       "preStrLength": 16
                    }
                 }
              }, 
              {
                 "regex": ".*?", 
                 "type": {
                    "label": "any_characters", 
                    "metadata": {}
                 }
              }, 
              {
                 "regex": "^.*?(00\\:03\\:24)\\ *?", 
                 "type": {
                    "label": "after_literal", 
                    "metadata": {
                       "literal": "00:03:24 "
                    }
                 }
              }
           ]
        }
        self.assertEqual(results, correct)

    def testNewRex(self, rexname,  data, correct):
        data.update({'sid': '123456789.012','type': 'rules_new', 'field': '_raw'})
        TableUINewRule().setSessionKey(self.sessionKey).checkData(data)
        rex = getattr(sys.modules[__name__], rexname)(data)
        # these also work but less secured: 
        #   rex = eval(rexname).getRegex(data) 
        #   rex = globals()[rexname](data)
        if correct:
            self.assertEqual(rex.result, correct)
        else:
            myprint(rex.result)
        
    def case4(self):
        data = {
                'selected_text': ' %STP-W-PORTSTATUS',
                'field_value': 'Jul 24 00:03:05 172.22.98.4 %STP-W-PORTSTATUS: e4: STP status Forwarding',
                'start_position': '27',
                'end_position': '45',
            }
        correct = \
        {
           "type": {
              "metadata": {'preIrregCharsAfterSpace': u'...', 'preSpaceCount': 3},
              "label": "n_spaces_and_irregular_characters"
           }, 
           "regex": "^[^\\ ]*?(\\ )[^\\ ]*?(\\ )[^\\ ]*?(\\ )[^\\.]*?(\\.)[^\\.]*?(\\.)[^\\.]*?(\\.)"
        }
        self.testNewRex('NSpacesAndIrregularCharactersStartingRegex', data, correct)
 
    def case5(self):
        data = {
                'selected_text': ' %STP-W-PORTSTATUS',
                'field_value': 'Jul 24 00:03:05 172.22.98.4 %STP-W-PORTSTATUS: e4: STP status Forwarding',
                'start_position': '27',
                'end_position': '45',
            }
        correct = \
        {
           "type": {
              'metadata': {'preSpaceCount': 3, 'preStrAfterSpace': u'172.22.98.4'},
              "label": "n_spaces_and_preceding_string"
           }, 
           "regex": "^[^\\ ]*?(\\ )[^\\ ]*?(\\ )[^\\ ]*?(\\ ).*?(172\\.22\\.98\\.4)"
        }
        self.testNewRex('NSpacesAndPrecedingStringStartingRegex', data, correct)
 
    def case6(self):
        data = {
                'selected_text': ' %STP-W-PORTSTATUS',
                'field_value': 'Jul 24 00:03:05 172.22.98.4 %STP-W-PORTSTATUS: e4: STP status Forwarding',
                'start_position': '27',
                'end_position': '45',
            }
        correct = \
        {
           "regex": "^[^\\ ]*?(\\ )[^\\ ]*?(\\ )[^\\ ]*?(\\ )[^\\.]*?(\\.)[^\\.]*?(\\.)[^\\.]*?(\\.).*?(4)", 
           "type": {
              "label": "n_spaces_and_preceding_word", 
              'metadata': {'preSpaceCount': 3, 'preWord': u'4'}
           }
        }
        self.testNewRex('NSpacesAndPrecedingWordStartingRegex', data, correct)
 
    def case7(self):
        data = {
                'selected_text': ' %STP-W-PORTSTATUS',
                'field_value': 'Jul 24 00:03:05 172.22.98.4 %STP-W-PORTSTATUS: e4: STP status Forwarding',
                'start_position': '27',
                'end_position': '45',
            }
        correct = \
        {
           "regex": "^.*?(4)", 
           "type": {
              "label": "preceding_word", 
              'metadata': {'preWord': u'4'}
           }
        }
        self.testNewRex('PrecedingWordStartingRegex', data, correct)
 
    def case8(self):
        data = {
                'selected_text': ' %STP-W-PORTSTATUS',
                'field_value': 'Jul 24 00:03:05 172.22.98.4 %STP-W-PORTSTATUS: e4: STP status Forwarding',
                'start_position': '27',
                'end_position': '45',
            }
        correct = \
        {
           "regex": "^[^\\ ]*?(\\ )[^\\ ]*?(\\ )[^\\ ]*?(\\ )[^4]*?(4)", 
           "type": {
              'metadata': {'preChar': u'4', 'preSpaceCount': 3},
              "label": "n_spaces_and_starting_character"
           }
        }
        self.testNewRex('NSpacesAndStartingCharacterStartingRegex', data, correct)
 
    def case9(self):
        data = {
                'selected_text': ' %STP-W-PORTSTATUS',
                'field_value': 'Jul 24 00:03:05 172.22.98.4 %STP-W-PORTSTATUS: e4: STP status Forwarding',
                'start_position': '27',
                'end_position': '45',
            }
        correct = \
        {
           "type": {
              "label": "nth_character", 
              'metadata': {'preCharCount': 2, 'preCharName': u'4'},
           }, 
           "regex": "^[^4]*?(4)[^4]*?(4)"
        }
        self.testNewRex('NthCharacterStartingRegex', data, correct)
 
    def case10(self):
        data = {
                'selected_text': ',"AxisBoard-5"',
                'field_value': '"1144644002.000000",27e4df3defe4ce59b891a7230dfd28d2,"AxisBoard-5"',
                'start_position': '52',
                'end_position': '66',
            }
        correct = \
        {
           "type": {
              'metadata': {'preWord': u'27e4df3defe4ce59b891a7230dfd28d2'},
              "label": "preceding_word"
           }, 
           "regex": "^.*?(27e4df3defe4ce59b891a7230dfd28d2)"
        }
        self.testNewRex('PrecedingWordStartingRegex', data, correct)
 
    def case11(self):
        data = {
                'selected_text': ',"AxisBoard-5"',
                'field_value': '"1144644002.000000",27e4df3defe4ce59b891a7230dfd28d2,"AxisBoard-5"',
                'start_position': '52',
                'end_position': '66',
            }
        correct = \
        {
           "type": {
              "label": "n_commas_and_preceding_character", 
              'metadata': {'preCharName': u'2', 'preCommaCount': 1},
           }, 
           "regex": "^[^\\,]*?(\\,).*?(2)"
        }
        self.testNewRex('NCommasAndPrecedingCharacterStartingRegex', data, correct)
 
    def case12(self):
        data = {
                'selected_text': 'Jul',
                'field_value': 'Jul 24 00:03:05 172.22.98.4 %STP-W-PORTSTATUS: e4: STP status Forwarding',
                'start_position': '0',
                'end_position': '2',
            }
        correct = \
        {
           "regex": "^", 
           "type": {
              "metadata": {}, 
              "label": "start_of_string"
           }
        }
        self.testNewRex('StartOfStringStartingRegex', data, correct)
 
    def case13(self):
        data = {
                'selected_text': "'hello world'",
                'field_value': "I greeting='hello world'",
                'start_position': '11',
                'end_position': '24',
            }
        correct = \
        {
           "type": {
              "label": "field_name", 
              'metadata': {'preFieldNameAndChar': u'greeting='},
           }, 
           "regex": "^.*?(greeting\\=)"
        }
        self.testNewRex('FieldNameStartingRegex', data, correct)
 
    def case14(self):
        data = {
                'selected_text': "'hello world'",
                'field_value': "greeting:'hello world'",
                'start_position': '9',
                'end_position': '22',
            }
        correct = \
        {
           "regex": "^.*?(greeting\\:)", 
           "type": {
              "label": "field_name", 
              'metadata': {'preFieldNameAndChar': u'greeting:'},
           }
        }
        self.testNewRex('FieldNameStartingRegex', data, correct)
 
    def case15(self):
        data = {
                'selected_text': '%STP-W-PORTSTATUS',
                'field_value': 'Jul 24 00:03:05 172.22.98.4 %STP-W-PORTSTATUS: e4: STP status Forwarding',
                'start_position': '28',
                'end_position': '45',
            }
        correct = \
        {
           "type": {
              "label": "any_character_but_following_character", 
              'metadata': {'followCharName': u':'},
           }, 
           "regex": "[^\\:]+"
        }
        self.testNewRex('AnyCharacterButFollowingCharacterExtractionRegex', data, correct)

    def case16(self):
        data = {
                'selected_text': '%STP-W-PORTSTATUS',
                'field_value': 'Jul 24 00:03:05 172.22.98.4 %STP-W-PORTSTATUS: e4: STP status Forwarding',
                'start_position': '28',
                'end_position': '45',
            }
        correct = \
        {
           "type": {
              'metadata': {'selectedTextLength': 17},
              "label": "number_of_characters"
           }, 
           "regex": ".{17}"
        }
        self.testNewRex('NumberOfCharactersExtractionRegex', data, correct)

    def case17(self):
        data = {
                'selected_text': '%STP-W-PORTSTATUS',
                'field_value': 'Jul 24 00:03:05 172.22.98.4 %STP-W-PORTSTATUS: e4: STP status Forwarding',
                'start_position': '28',
                'end_position': '45',
            }
        correct = \
        {
           "type": {
              'metadata': {'uniqueIrregChars': u'%-'},
              "label": "word_characters_and_contained_irregular_characters"
           }, 
           "regex": "[\\w\\%\\-\\ ]+"
        }
        self.testNewRex('WordCharactersAndContainedIrregularCharactersExtractionRegex', data, correct)

    def case18(self):
        data = {
                'selected_text': '%STP-W-PORTSTATUS',
                'field_value': 'Jul 24 00:03:05 172.22.98.4 %STP-W-PORTSTATUS: e4: STP status Forwarding',
                'start_position': '28',
                'end_position': '45',
            }
        correct = \
        {
           "type": {
              "metadata": {}, 
              "label": "any_character"
           }, 
           "regex": ".+"
        }
        self.testNewRex('AnyCharacterExtractionRegex', data, correct)

    def case19(self):
        data = {
                'selected_text': '%STP-W-PORTSTATUS: e4: STP status Forwarding',
                'field_value': 'Jul 24 00:03:05 172.22.98.4 %STP-W-PORTSTATUS: e4: STP status Forwarding',
                'start_position': '28',
                'end_position': '72',
            }
        correct = \
        {
           "regex": ".+$", 
           "type": {
              "metadata": {}, 
              "label": "end_of_string"
           }
        }
        self.testNewRex('EndOfStringExtractionRegex', data, correct)

    def case20(self):
        data = {
                'selected_text': 'status',
                'field_value': 'Jul 24 00:03:05 172.22.98.4 %STP-W-PORTSTATUS: e4: STP status Forwarding',
                'start_position': '55',
                'end_position': '61',
            }
        correct = \
        {
           "type": {
              "label": "letters", 
              "metadata": {}
           }, 
           "regex": "[a-zA-Z]+"
        }
        self.testNewRex('LettersExtractionRegex', data, correct)

    def case21(self):
        data = {
                'selected_text': 'status',
                'field_value': 'Jul 24 00:03:05 172.22.98.4 %STP-W-PORTSTATUS: e4: STP status Forwarding',
                'start_position': '55',
                'end_position': '61',
            }
        correct = \
        {
           "type": {
              "metadata": {}, 
              "label": "lowercase_letters"
           }, 
           "regex": "[a-z]+"
        }
        self.testNewRex('LowercaseLettersExtractionRegex', data, correct)

    def case22(self):
        data = {
                'selected_text': 'status',
                'field_value': 'Jul 24 00:03:05 172.22.98.4 %STP-W-PORTSTATUS: e4: STP status Forwarding',
                'start_position': '55',
                'end_position': '61',
            }
        correct = \
        {
           "type": {
              "label": "word_characters", 
              "metadata": {}
           }, 
           "regex": "\\w+"
        }
        self.testNewRex('WordCharactersExtractionRegex', data, correct)

    def case23(self):
        data = {
                'selected_text': 'STP',
                'field_value': 'Jul 24 00:03:05 172.22.98.4 %STP-W-PORTSTATUS: e4: STP status Forwarding',
                'start_position': '51',
                'end_position': '54',
            }
        correct = \
        {
           "type": {
              "label": "uppercase_letters", 
              "metadata": {}
           }, 
           "regex": "[A-Z]+"
        }
        self.testNewRex('UppercaseLettersExtractionRegex', data, correct)

    def case24(self):
        data = {
                'selected_text': '24',
                'field_value': 'Jul 24 00:03:05 172.22.98.4 %STP-W-PORTSTATUS: e4: STP status Forwarding',
                'start_position': '4',
                'end_position': '6',
            }
        correct = \
        {
           "regex": "\\d+", 
           "type": {
              "metadata": {}, 
              "label": "numbers"
           }
        }
        self.testNewRex('NumbersExtractionRegex', data, correct)

    def case25(self):
        data = {
                'selected_text': '%STP-W-PORTSTATUS',
                'field_value': 'Jul 24 00:03:05 172.22.98.4 %STP-W-PORTSTATUS: e4: STP status Forwarding',
                'start_position': '28',
                'end_position': '45',
            }
        correct = \
        {
           "type": {
              "label": "following_characters", 
              'metadata': {'followChars': u':'},
           }, 
           "regex": "(\\:).*?$"
        }
        self.testNewRex('FollowingCharacterStoppingRegex', data, correct)

    def case26(self):
        data = {
                'selected_text': '%STP-W-PORTSTATUS',
                'field_value': 'Jul 24 00:03:05 172.22.98.4 %STP-W-PORTSTATUS: e4: STP status Forwarding',
                'start_position': '28',
                'end_position': '45',
            }
        correct = \
        {
           "type": {
              "label": "any_characters", 
              "metadata": {}
           }, 
           "regex": ".*?$"
        }
        self.testNewRex('AnyCharacterStoppingRegex', data, correct)

    def testExistingRex(self, data, correct):
        data.update({'sid': self.sid, 'type': 'rules_existing', 'field': '_raw'})
        result = self._existingRule.results(data)
        if correct:
            self.assertEqual(result, correct)
        else:
            pprint.pprint(result)

    def case27(self):
#        self.timer.start()
        data = {
                'regex_start': '^[^\ ]*?\ [^\ ]*?\ [^\ ]*?\ [^\ ]*?\ [^\%]*?\%.*?',
                'regex_extract': '[^\:]+',
                'regex_stop': '\:',
            }
        correct = \
        {'extract_rules': [{'regex': u'[^\\:]+',
                            'type': {'label': 'any_character_but_following_character',
                                     'metadata': {'followCharName': u':'}}},
                           {'regex': u'[\\w\\-\\ ]+',
                            'type': {'label': 'word_characters_and_contained_irregular_characters',
                                     'metadata': {'uniqueIrregChars': u'-'}}},
                           {'regex': '.+',
                            'type': {'label': 'any_character', 'metadata': {}}},
                           {'regex': '.{9}',
                            'type': {'label': 'number_of_characters',
                                     'metadata': {'selectedTextLength': 9}}}],
         'start_rules': [{'regex': u'^[^\\ ]*?(\\ )[^\\ ]*?(\\ )[^\\ ]*?(\\ )[^\\ ]*?(\\ )[^\\%]*?(\\%)',
                          'type': {'label': 'n_spaces_and_starting_character',
                                   'metadata': {'preChar': u'%',
                                                'preSpaceCount': 4}}},
                         {'regex': u'^[^\\:]*?(\\:)[^\\:]*?(\\:)[^\\.]*?(\\.)[^\\.]*?(\\.)[^\\.]*?(\\.)[^\\%]*?(\\%)',
                          'type': {'label': 'irregular_characters',
                                   'metadata': {'preIrregChars': u'::...%'}}},
                         {'regex': '^.{28}',
                          'type': {'label': 'n_characters',
                                   'metadata': {'preStrLength': 28}}},
                         {'regex': '.*?',
                          'type': {'label': 'any_characters', 'metadata': {}}},
                         {'regex': u'^.*?(\\%)',
                          'type': {'label': 'after_literal',
                                   'metadata': {'literal': u'%'}}}],
         'stop_rules': [{'regex': u'(\\:).*?$',
                         'type': {'label': 'following_characters',
                                  'metadata': {'followChars': u':'}}},
                        {'regex': '.*?$',
                         'type': {'label': 'any_characters', 'metadata': {}}}]}
        self.testExistingRex(data, correct)
#        self.timer.stop()


    def testEventRetrieval(self, data, correct):
        data.update({'sid': self.sid, 'type': 'events', 'field': '_raw', 'count': 5})
        result  = TableUIEvents().setSessionKey(self.sessionKey).results(data)
        if correct:
            self.assertEqual(result, correct)
        else:
            pprint.pprint(result)

    def case28(self):
        data = {
                'regex_start': '^[^\ ]*?(\ )[^\ ]*?(\ )[^\ ]*?(\ )[^\ ]*?(\ )[^\%]*?(\%).*?',
                'regex_extract': '[^\:]+',
                'regex_stop': '(\:)',
            }
        correct = \
        [{'field_value': u'Jul 24 00:03:24 172.22.7.4 %LINK-I-Up:  e13',
          'highlight_range': (28, 37),
          'post_highlight_ranges': [(37, 38)],
          'pre_highlight_ranges': [(3, 4), (6, 7), (15, 16), (26, 27), (27, 28)]},
         {'field_value': u'Jul 24 00:03:24 172.22.7.4 %LINK-I-Up:  e13',
          'highlight_range': (28, 37),
          'post_highlight_ranges': [(37, 38)],
          'pre_highlight_ranges': [(3, 4), (6, 7), (15, 16), (26, 27), (27, 28)]},
         {'field_value': u'Jul 24 00:03:05 172.22.98.4 %STP-W-PORTSTATUS: e4: STP status Forwarding',
          'highlight_range': (29, 45),
          'post_highlight_ranges': [(45, 46)],
          'pre_highlight_ranges': [(3, 4), (6, 7), (15, 16), (27, 28), (28, 29)]},
         {'field_value': u'Jul 24 00:03:05 172.22.98.4 %STP-W-PORTSTATUS: e4: STP status Forwarding',
          'highlight_range': (29, 45),
          'post_highlight_ranges': [(45, 46)],
          'pre_highlight_ranges': [(3, 4), (6, 7), (15, 16), (27, 28), (28, 29)]},
         {'field_value': u'Jul 24 00:02:57 172.22.68.4 %STP-W-PORTSTATUS: e3: STP status Forwarding',
          'highlight_range': (29, 45),
          'post_highlight_ranges': [(45, 46)],
          'pre_highlight_ranges': [(3, 4), (6, 7), (15, 16), (27, 28), (28, 29)]}]

        self.testEventRetrieval(data, correct)

    def testRegex(self, field_val, selected_text, regex_start, regex_extract, regex_stop):
        '''
        Apply the given rule to field_val and check whether selected_text is extracted.
        '''
        user_regex = TableUIRule.userRegex(regex_start, regex_extract, regex_stop)
        try:
            match_result = TableUIRule.MatchResult(user_regex.match(field_val))
        except ValueError as e:
            print("regex %s doesn't match field value %s" %(user_regex.pattern, field_val))
            return False
        else:
            s = match_result.selectedText 
            if s == selected_text:
                return True
            else:
                print('Regex is NOT correct.\n   extracted text: %s\n   correct text: %s' %(repr(s), repr(selected_text)))
                print('Regex was %s field value was %s' % (user_regex.pattern, field_val))
                return False

    def testRules(self, data):
        data['field_value'] = toUnicode(data['field_value'])
        data['selected_text'] = toUnicode(data['selected_text'])
        results = TableUINewRule().setSessionKey(self.sessionKey).results(data)
        start_rule = results['start_rules'][0]['regex']
        extract_rule = results['extract_rules'][0]['regex']
        stop_rule = results['stop_rules'][0]['regex']
        self.assertTrue(self.testRegex(data['field_value'], data['selected_text'], start_rule, extract_rule, stop_rule))
 
    def case29(self):
        data = {
                'sid': self.sid,
                'selected_text': 'Français', 
                'field_value': 'Français złoty Österreich',
                'start_position': '0',
                'end_position': '8',
                'type': 'rules_new',
                'field': '_raw'
        }
        self.testRules(data)

    def case30(self):
        data = {
                'sid': self.sid,
                'selected_text': 'Français', 
                'field_value': 'user=Français złoty Österreich',
                'start_position': '5',
                'end_position': '13',
                'type': 'rules_new',
                'field': '_raw'
        }
        self.testRules(data)

    def case31(self):
        data = {
                'sid': self.sid,
                'selected_text': 'Français', 
                'field_value': '123  Français złoty Österreich',
                'start_position': '5',
                'end_position': '13',
                'type': 'rules_new',
                'field': '_raw'
        }
        self.testRules(data)

    def case32(self):
        data = {
                'sid': self.sid,
                'selected_text': 'złoty', 
                'field_value': 'Français=złoty Österreich',
                'start_position': '9',
                'end_position': '14',
                'type': 'rules_new',
                'field': '_raw'
        }
        class TestRule(TableUINewRule):
            def startingRegexes(self, data):
                return (
                        NthCharacterStartingRegex(data),
                        NSpacesAndStartingCharacterStartingRegex(data),
                        IrregularCharactersStartingRegex(data),
                        NCharactersStartingRegex(data),
                        AnyCharactersStartingRegex(data),
                        NSpacesAndIrregularCharactersStartingRegex(data),
                        NSpacesAndPrecedingStringStartingRegex(data),
                        NSpacesAndPrecedingWordStartingRegex(data),
                        PrecedingWordStartingRegex(data),
                        PrecedingStringStartingRegex(data),
                        NCommasAndPrecedingCharacterStartingRegex(data),
                        StartOfStringStartingRegex(data),
                        FieldNameStartingRegex(data),
                        AfterLiteralStartingRegex(data),
                    )
            def stoppingRegexes(self, data):
                return (
                        FollowingCharacterStoppingRegex(data),
                        AnyCharacterStoppingRegex(data),
                        BeforeLiteralStoppingRegex(data),
                        EndOfStringStoppingRegex(data),
                        )

        results = TestRule().setSessionKey(self.sessionKey).results(data)
        correct = \
        {
            "extract_rules": \
            [
               {
                  "type": {
                     "label": "any_character_but_following_character", 
                     "metadata": {
                        "followCharName": "space"
                     }
                  }, 
                  "regex": "[^\\ ]+"
               }, 
               {
                  "type": {
                     "label": "number_of_characters", 
                     "metadata": {
                        "selectedTextLength": 5
                     }
                  }, 
                  "regex": ".{5}"
               }, 
               {
                  "type": {
                     "label": "any_character", 
                     "metadata": {}
                  }, 
                  "regex": ".+"
               }, 
               {
                  "type": {
                     "label": "word_characters", 
                     "metadata": {}
                  }, 
                  "regex": "\\w+"
               }
            ],
           "stop_rules": [
              {
                 "regex": "\\ *?.*?$", 
                 "type": {
                    "metadata": {
                       "followChars": " "
                    }, 
                    "label": "following_characters"
                 }
              }, 
              {
                 "regex": ".*?$", 
                 "type": {
                    "metadata": {}, 
                    "label": "any_characters"
                 }
              }, 
              {
                 "regex": "\\ *?(\\Österreich).*?$", 
                 "type": {
                    "metadata": {
                       "literal": " Österreich"
                    }, 
                    "label": "before_literal"
                 }
              }
           ], 
           "start_rules": [
              {
                 "regex": "^.{9}", 
                 "type": {
                    "metadata": {
                       "preStrLength": 9
                    }, 
                    "label": "n_characters"
                 }
              }, 
              {
                 "regex": ".*?", 
                 "type": {
                    "metadata": {}, 
                    "label": "any_characters"
                 }
              }, 
              {
                 "regex": "^[^\\=]*?(\\=)", 
                 "type": {
                    "metadata": {
                       "preIrregChars": "="
                    }, 
                    "label": "irregular_characters"
                 }
              }, 
              {
                 "regex": "^.*?(Fran\\çais\\=)", 
                 "type": {
                    "metadata": {
                       "preFieldNameAndChar": "Français="
                    }, 
                    "label": "field_name"
                 }
              }, 
#              {
#                 "regex": "^.*?(Fran\\çais\\=)", 
#                 "type": {
#                    "metadata": {
#                       "literal": "Français="
#                    }, 
#                    "label": "after_literal"
#                 }
#              }
           ]
        }
        self.assertEqual(results, correct)

    def case34(self):
        data = {
                'selected_text': ' -4.0',
                'field_value': '1407829891424 S_PWR -4.0 S_SPD 0.0',
                'start_position': '19',
                'end_position': '24',
            }
        correct = \
        {
           "type": {
              "label": "after_literal", 
              'metadata': {'literal': u'S_PWR'},
           }, 
           "regex": "^.*?(S\\_PWR)"
        }
        self.testNewRex('AfterLiteralStartingRegex', data, correct)

    def case35(self):
        data = {
                'selected_text': ' -4.0',
                'field_value': '1407829891424 S_PWR -4.0 S_SPD 0.0',
                'start_position': '19',
                'end_position': '25',
            }
        correct = \
        {
           "type": {
              "label": "before_literal", 
              'metadata': {'literal': u'S_SPD'},
           }, 
           "regex": "(S\\_SPD).*?$"
        }
        self.testNewRex('BeforeLiteralStoppingRegex', data, correct)

    def case36(self):
        query = 'search source="/home/nnguyen/mydata/megumi.csv"'
#        query = 'search source="/home/nnguyen/mydata/megumi.csv" | fields client_ip'
        job = splunk.search.dispatch(query, hostPath=self.hostPath, sessionKey=self.sessionKey)

        data = {
                'selected_text': '175',
                'field_value': '205.175.124.217',
                'start_position': '4',
                'end_position': '7',
                'type': 'rules_new',
                'field': 'client_ip',
                'sid': job.sid,
            }
        results = self._newRule.results(data)
        correct = \
        {
           "start_rules": [
              {
                 "type": {
                    "label": "irregular_characters", 
                    "metadata": {
                       "preIrregChars": "."
                    }
                 }, 
                 "regex": "^[^\\.]*?(\\.)"
              }, 
              {
                 "type": {
                    "label": "n_characters", 
                    "metadata": {
                       "preStrLength": 4
                    }
                 }, 
                 "regex": "^.{4}"
              }, 
              {
                 "type": {
                    "label": "any_characters", 
                    "metadata": {}
                 }, 
                 "regex": ".*?"
              }, 
              {
                 "type": {
                    "label": "after_literal", 
                    "metadata": {
                       "literal": "205."
                    }
                 }, 
                 "regex": "^.*?(205\\.)"
              }
           ], 
           "extract_rules": [
              {
                 "type": {
                    "label": "any_character_but_following_character", 
                    "metadata": {
                       "followCharName": "."
                    }
                 }, 
                 "regex": "[^\\.]+"
              }, 
              {
                 "type": {
                    "label": "number_of_characters", 
                    "metadata": {
                       "selectedTextLength": 3
                    }
                 }, 
                 "regex": ".{3}"
              }, 
              {
                 "type": {
                    "label": "any_character", 
                    "metadata": {}
                 }, 
                 "regex": ".+"
              }, 
              {
                 "type": {
                    "label": "word_characters", 
                    "metadata": {}
                 }, 
                 "regex": "\\w+"
              }, 
              {
                 "type": {
                    "label": "numbers", 
                    "metadata": {}
                 }, 
                 "regex": "\\d+"
              }
           ], 
           "stop_rules": [
              {
                 "type": {
                    "label": "following_characters", 
                    "metadata": {
                       "followChars": "."
                    }
                 }, 
                 "regex": "(\\.).*?$"
              }, 
              {
                 "type": {
                    "label": "any_characters", 
                    "metadata": {}
                 }, 
                 "regex": ".*?$"
              }
           ]
        }
        self.assertEqual(correct, results)
            
    def case37(self):
        data = {
                'selected_text': 'STP-W-PORTSTATUS',
                'field_value': 'Jul 24 00:03:05 172.22.98.4 %STP-W-PORTSTATUS: e4: STP status Forwarding',
                'start_position': '29',
                'end_position': '45',
            }
        correct = \
        {
           "type": {
              "label": "nth_character", 
              'metadata': {'stopCharCount': 2, 'stopCharName': u':'},
           }, 
           "regex": "(\\:)[^\\:]*?(\\:)[^\\:]*?$"
        }
        self.testNewRex('NthCharacterStoppingRegex', data, correct)
 
    def case38(self):
        data = {
                'selected_text': ' %STP-W-PORTSTATUS',
                'field_value': 'Jul 24 00:03:05 172.22.98.4 %STP-W-PORTSTATUS: e4: STP status Forwarding',
                'start_position': '27',
                'end_position': '45',
            }
        correct = \
        {
           "regex": "(\\:)[^\\:]*?(\\ )[^\\ ]*?(\\ )[^\\ ]*?(\\ )[^\\ ]*?(\\ )[^\\ ]*?$", 
           "type": {
                'metadata': {'stopChar': u':', 'followSpaceCount': 4},
                "label": "stopping_character_and_n_spaces"
            }
        }
        self.testNewRex('StoppingCharacterAndNSpacesStoppingRegex', data, correct)
 
    def case39(self):
        data = {
                'selected_text': '175',
                'field_value': '205.175.124.217',
                'start_position': '4',
                'end_position': '7',
            }
        correct = \
        {
           "regex": "(\\.)[^\\.]*?(\\.)[^\\.]*?$",
           "type": {
              "metadata": {
                 "followIrregChars": ".."
              }, 
              "label": "irregular_characters"
           }
        }
        self.testNewRex('IrregularCharactersStoppingRegex', data, correct)

    def case40(self):
        data = {
                'selected_text': '175',
                'field_value': '205.175.124.217',
                'start_position': '4',
                'end_position': '7',
            }
        correct = \
        {
           "type": {
              "label": "n_characters", 
              "metadata": {
                 "followStrLength": 8
              }
           }, 
           "regex": ".{8}$"
        }
        self.testNewRex('NCharactersStoppingRegex', data, correct)

    def case41(self):
        data = {
                'selected_text': '205',
                'field_value': '205.175.124.217 ip address',
                'start_position': '0',
                'end_position': '3',
            }
        correct = \
        {
           "type": {
              "label": "irregular_characters_and_n_spaces", 
              "metadata": {
                 "followSpaceCount": 2, 
                 "followIrregCharsAfterSpace": "..."
              }
           }, 
           "regex": "(\\.)[^\\.]*?(\\.)[^\\.]*?(\\.)[^\\.]*?(\\ )[^\\ ]*?(\\ )[^\\ ]*?$", 
        }
        self.testNewRex('NSpacesAndIrregularCharactersStoppingRegex', data, correct)
 
    def case42(self):
        data = {
                'selected_text': '205.175.124.217',
                'field_value': '205.175.124.217ip address',
                'start_position': '0',
                'end_position': '15',
            }
        correct = \
        {
           "type": {
              "label": "following_string_and_n_spaces", 
              "metadata": {
                 "followStrBeforeSpace": "ip", 
                 "followSpaceCount": 1
              }
           }, 
           "regex": "(ip).*?(\\ )[^\\ ]*?$"
        }
        self.testNewRex('FollowStringAndNSpacesStoppingRegex', data, correct)
 
    def case43(self):
        data = {
                'selected_text': '205.175.124.217',
                'field_value': '205.175.124.217ip address',
                'start_position': '0',
                'end_position': '15',
            }
        correct = \
        {
           "type": {
              "label": "following_word_and_n_spaces", 
              "metadata": {
                 "followWord": "ip", 
                 "followSpaceCount": 1
              }
           }, 
           "regex": "(ip).*?(\\ )[^\\ ]*?$"
        }
        self.testNewRex('FollowWordAndNSpacesStoppingRegex', data, correct)

    def case44(self):
        data = {
                'selected_text': 'STP-W-PORTSTATUS',
                'field_value': 'Jul 24 00:03:05 172.22.98.4 %STP-W-PORTSTATUS: e4: STP status Forwarding',
                'start_position': '29',
                'end_position': '51',
            }
        correct = \
        {
           "type": {
              "label": "following_word", 
              "metadata": {
                 "followWord": "STP"
              }
           }, 
           "regex": "(STP).*?$"
        }
        self.testNewRex('FollowWordStoppingRegex', data, correct)

    def case45(self):
        data = {
                'selected_text': 'STP-W-PORTSTATUS: ',
                'field_value': 'Jul 24 00:03:05 172.22.98.4 %STP-W-PORTSTATUS: e4: STP status Forwarding',
                'start_position': '29',
                'end_position': '47',
            }
        correct = \
        {
           "regex": "(e4\\:).*?$", 
           "type": {
              "metadata": {
                 "literal": "e4:"
              }, 
              "label": "before_literal"
           }
        }
        self.testNewRex('BeforeLiteralStoppingRegex', data, correct)

    def case46(self):
        data = {
                'selected_text': 'STP-W-PORTSTATUS',
                'field_value': 'Jul 24 00:03:05 172.22.98.4 %STP-W-PORTSTATUS: e4: STP, status, Forwarding',
                'start_position': '29',
                'end_position': '45',
            }
        correct = \
        {
           "type": {
              "label": "following_character_and_n_commas", 
              "metadata": {
                 "followCharName": ":", 
                 "followCommaCount": 2
              }
           }, 
           "regex": "(\\:).*?(\\,)[^\\,]*?(\\,)[^\\,]*?$"
        }
        self.testNewRex('FollowCharacterAndNCommasStoppingRegex', data, correct)

    def case47(self):
        data = {
                'sid': self.sid,
                'selected_text': 'STP-W-PORTSTATUS',
                'field_value': 'Jul 24 00:03:05 172.22.98.4 %STP-W-PORTSTATUS: e4: STP status Forwarding',
                'start_position': '29',
                'end_position': '45',
                'type': 'rules_new',
                'field': '_raw'
           }
        self.testRules(data)

    def case48(self):
        data = {
                'sid': self.sid,
                'selected_text': '-4.0',
                'field_value': '1407829891424 S_PWR -4.0 S_SPD 0.0',
                'start_position': '20',
                'end_position': '24',
                'type': 'rules_new',
                'field': '_raw'
           }
        self.testRules(data)

    def case49(self):
        data = {
                'sid': self.sid,
                'selected_text': 'STP-W-PORTSTATUS',
                'field_value': 'Jul 24 00:03:05 172.22.98.4 %STP-W-PORTSTATUS: e4: STP status Forwarding',
                'start_position': '29',
                'end_position': '45',
                'type': 'rules_new',
                'field': '_raw'
        }
        class TestRule(TableUINewRule):
            def startingRegexes(self, data):
                return (
                        NthCharacterStartingRegex(data),
                        NSpacesAndStartingCharacterStartingRegex(data),
                        IrregularCharactersStartingRegex(data),
                        NCharactersStartingRegex(data),
                        AnyCharactersStartingRegex(data),
                        NSpacesAndIrregularCharactersStartingRegex(data),
                        NSpacesAndPrecedingStringStartingRegex(data),
                        NSpacesAndPrecedingWordStartingRegex(data),
                        PrecedingWordStartingRegex(data),
                        PrecedingStringStartingRegex(data),
                        NCommasAndPrecedingCharacterStartingRegex(data),
                        StartOfStringStartingRegex(data),
                        FieldNameStartingRegex(data),
                        AfterLiteralStartingRegex(data),
                    )

            def extractionRegexes(self, data):
                return (
                        AnyCharacterButFollowingCharacterExtractionRegex(data),
                        NumberOfCharactersExtractionRegex(data),
                        WordCharactersAndContainedIrregularCharactersExtractionRegex(data),
                        AnyCharacterExtractionRegex(data),
                        EndOfStringExtractionRegex(data),
                        LettersExtractionRegex(data),
                        LowercaseLettersExtractionRegex(data),
                        UppercaseLettersExtractionRegex(data),
                        WordCharactersExtractionRegex(data),
                        NumbersExtractionRegex(data),
                    )

            def stoppingRegexes(self, data):
                return (
                        FollowingCharacterStoppingRegex(data),
                        AnyCharacterStoppingRegex(data),
                        BeforeLiteralStoppingRegex(data),
                        EndOfStringStoppingRegex(data),
                        NthCharacterStoppingRegex(data),
                        StoppingCharacterAndNSpacesStoppingRegex(data),
                        IrregularCharactersStoppingRegex(data),
                        NCharactersStoppingRegex(data),
                        NSpacesAndIrregularCharactersStoppingRegex(data),
                        FollowStringAndNSpacesStoppingRegex(data),
                        FollowWordAndNSpacesStoppingRegex(data),
                        FollowWordStoppingRegex(data),
                        FollowCharacterAndNCommasStoppingRegex(data),
                    )

        results = TestRule().setSessionKey(self.sessionKey).results(data)
        correct = \
        {
           "stop_rules": [
              {
                 "type": {
                    "metadata": {
                       "followChars": ":"
                    }, 
                    "label": "following_characters"
                 }, 
                 "regex": "(\\:).*?$"
              }, 
              {
                 "type": {
                    "metadata": {}, 
                    "label": "any_characters"
                 }, 
                 "regex": ".*?$"
              }, 
#              {
#                 "type": {
#                    "metadata": {
#                       "literal": ":"
#                    }, 
#                    "label": "before_literal"
#                 }, 
#                 "regex": "(\\:).*?$"
#              }, 
              {
                 "type": {
                    "metadata": {
                       "stopCharCount": 2, 
                       "stopCharName": ":"
                    }, 
                    "label": "nth_character"
                 }, 
                 "regex": "(\\:)[^\\:]*?(\\:)[^\\:]*?$"
              }, 
              {
                 "type": {
                    "metadata": {
                       "followSpaceCount": 4, 
                       "stopChar": ":"
                    }, 
                    "label": "stopping_character_and_n_spaces"
                 }, 
                 "regex": "(\\:)[^\\:]*?(\\ )[^\\ ]*?(\\ )[^\\ ]*?(\\ )[^\\ ]*?(\\ )[^\\ ]*?$"
              }, 
#              {
#                 "type": {
#                    "metadata": {
#                       "followIrregChars": "::"
#                    }, 
#                    "label": "irregular_characters"
#                 }, 
#                 "regex": "(\\:)[^\\:]*?(\\:)[^\\:]*?$"
#              }, 
              {
                 "type": {
                    "metadata": {
                       "followStrLength": 27
                    }, 
                    "label": "n_characters"
                 }, 
                 "regex": ".{27}$"
              }
           ], 
           "extract_rules": [
              {
                 "type": {
                    "metadata": {
                       "followCharName": ":"
                    }, 
                    "label": "any_character_but_following_character"
                 }, 
                 "regex": "[^\\:]+"
              }, 
              {
                 "type": {
                    "metadata": {
                       "uniqueIrregChars": "-"
                    }, 
                    "label": "word_characters_and_contained_irregular_characters"
                 }, 
                 "regex": "[\\w\\-\\ ]+"
              }, 
              {
                 "type": {
                    "metadata": {}, 
                    "label": "any_character"
                 }, 
                 "regex": ".+"
              }, 
              {
                 "type": {
                    "metadata": {
                       "selectedTextLength": 16
                    }, 
                    "label": "number_of_characters"
                 }, 
                 "regex": ".{16}"
              }
           ], 
           "start_rules": [
              {
                 "type": {
                    "metadata": {
                       "preChar": "%", 
                       "preSpaceCount": 4
                    }, 
                    "label": "n_spaces_and_starting_character"
                 }, 
                 "regex": "^[^\\ ]*?(\\ )[^\\ ]*?(\\ )[^\\ ]*?(\\ )[^\\ ]*?(\\ )[^\\%]*?(\\%)"
              }, 
              {
                 "type": {
                    "metadata": {
                       "preIrregChars": "::...%"
                    }, 
                    "label": "irregular_characters"
                 }, 
                 "regex": "^[^\\:]*?(\\:)[^\\:]*?(\\:)[^\\.]*?(\\.)[^\\.]*?(\\.)[^\\.]*?(\\.)[^\\%]*?(\\%)"
              }, 
              {
                 "type": {
                    "metadata": {
                       "preStrLength": 29
                    }, 
                    "label": "n_characters"
                 }, 
                 "regex": "^.{29}"
              }, 
              {
                 "type": {
                    "metadata": {}, 
                    "label": "any_characters"
                 }, 
                 "regex": ".*?"
              }, 
              {
                 "type": {
                    "metadata": {
                       "literal": "%"
                    }, 
                    "label": "after_literal"
                 }, 
                 "regex": "^.*?(\\%)"
              }
           ]
        }
        self.assertEqual(results, correct)

    def case50(self):
        query = 'search source="/home/nnguyen/mydata/pooja.csv"'
        job = splunk.search.dispatch(query, hostPath=self.hostPath, sessionKey=self.sessionKey)
        data = {
                'sid': job.sid,
                'selected_text': 'backup from 10.11.36.15 port 38184 ssh2',
                'field_value': 'May 19 22:50:25 acmepayroll sshd[17169]: Failed password for backup from 10.11.36.15 port 38184 ssh2',
                'start_position': '61',
                'end_position': '100',
                'type': 'rules_new',
                'field': '_raw'
        }
        results = TableUINewRule().setSessionKey(self.sessionKey).results(data)
        correct = \
        {
           "stop_rules": [
              {
                 "regex": ".*?$", 
                 "type": {
                    "metadata": {}, 
                    "label": "any_characters"
                 }
              }, 
              {
                 "regex": "$", 
                 "type": {
                    "metadata": {}, 
                    "label": "end_of_string"
                 }
              }
           ], 
           "extract_rules": [
              {
                 "regex": ".{39}", 
                 "type": {
                    "metadata": {
                       "selectedTextLength": 39
                    }, 
                    "label": "number_of_characters"
                 }
              }, 
              {
                 "regex": ".+$", 
                 "type": {
                    "metadata": {}, 
                    "label": "end_of_string"
                 }
              }
           ], 
           "start_rules": [
              {
                 "regex": "^[^\\ ]*?(\\ )[^\\ ]*?(\\ )[^\\ ]*?(\\ )[^\\ ]*?(\\ )[^\\ ]*?(\\ )[^\\ ]*?(\\ )[^\\ ]*?(\\ )[^\\ ]*?(\\ )", 
                 "type": {
                    "metadata": {
                       "preCharCount": 8, 
                       "preCharName": "space"
                    }, 
                    "label": "nth_character"
                 }
              }, 
              {
                 "regex": "^.{61}", 
                 "type": {
                    "metadata": {
                       "preStrLength": 61
                    }, 
                    "label": "n_characters"
                 }
              }, 
              {
                 "regex": ".*?", 
                 "type": {
                    "metadata": {}, 
                    "label": "any_characters"
                 }
              }, 
              {
                 "regex": "^.*?(for)\\ *?", 
                 "type": {
                    "metadata": {
                       "literal": "for "
                    }, 
                    "label": "after_literal"
                 }
              }
           ]
        }
        self.assertEqual(results, correct)

    def case51(self):
        query = 'search source="/home/nnguyen/mydata/pooja.csv"'
        job = splunk.search.dispatch(query, hostPath=self.hostPath, sessionKey=self.sessionKey)
        data = {
                'regex_start': '^[^\\ ]*?(\\ )[^\\ ]*?(\\ )[^\\ ]*?(\\ )[^\\ ]*?(\\ )[^\\ ]*?(\\ )[^\\ ]*?(\\ )[^\\ ]*?(\\ )[^\\ ]*?(\\ )',
                'regex_extract': '.{39}',
                'regex_stop': '.*?$',
                'sid': job.sid,
                'type': 'rules_existing',
                'field': '_raw',
            }
        result = TableUIExistingRule().setSessionKey(self.sessionKey).results(data)
        correct = \
        {
           "start_rules": [
              {
                 "regex": "^[^\\ ]*?(\\ )[^\\ ]*?(\\ )[^\\ ]*?(\\ )[^\\ ]*?(\\ )[^\\ ]*?(\\ )[^\\ ]*?(\\ )[^\\ ]*?(\\ )[^\\ ]*?(\\ )", 
                 "type": {
                    "label": "nth_character", 
                    "metadata": {
                       "preCharCount": 8, 
                       "preCharName": "space"
                    }
                 }
              }, 
              {
                 "regex": "^.{62}", 
                 "type": {
                    "label": "n_characters", 
                    "metadata": {
                       "preStrLength": 62
                    }
                 }
              }, 
              {
                 "regex": ".*?", 
                 "type": {
                    "label": "any_characters", 
                    "metadata": {}
                 }
              }, 
              {
                 "regex": "^.*?(for)\\ *?", 
                 "type": {
                    "label": "after_literal", 
                    "metadata": {
                       "literal": "for "
                    }
                 }
              }
           ], 
           "extract_rules": [
              {
                 "regex": "[^\\\"]+", 
                 "type": {
                    "label": "any_character_but_following_character", 
                    "metadata": {
                       "followCharName": "\""
                    }
                 }
              }, 
              {
                 "regex": ".+", 
                 "type": {
                    "label": "any_character", 
                    "metadata": {}
                 }
              }, 
              {
                 "regex": ".{39}", 
                 "type": {
                    "label": "number_of_characters", 
                    "metadata": {
                       "selectedTextLength": 39
                    }
                 }
              }
           ], 
           "stop_rules": [
              {
                 "regex": "(\\\").*?$", 
                 "type": {
                    "label": "following_characters", 
                    "metadata": {
                       "followChars": "\""
                    }
                 }
              }, 
              {
                 "regex": ".*?$", 
                 "type": {
                    "label": "any_characters", 
                    "metadata": {}
                 }
              }, 
              {
                 "regex": "(\\\")[^\\\"]*?(\\\")[^\\\"]*?(\\\")[^\\\"]*?$", 
                 "type": {
                    "label": "nth_character", 
                    "metadata": {
                       "stopCharName": "\"", 
                       "stopCharCount": 3
                    }
                 }
              }, 
              {
                 "regex": ".{32}$", 
                 "type": {
                    "label": "n_characters", 
                    "metadata": {
                       "followStrLength": 32
                    }
                 }
              }, 
              {
                 "regex": "(\\\").*?(\\,)[^\\,]*?$", 
                 "type": {
                    "label": "following_character_and_n_commas", 
                    "metadata": {
                       "followCommaCount": 1, 
                       "followCharName": "\""
                    }
                 }
              }, 
              {
                 "regex": "(\\\"\\,\\\"2016\\-05\\-19T22\\:50\\:25\\.000\\-0700\\\").*?$", 
                 "type": {
                    "label": "before_literal", 
                    "metadata": {
                       "literal": "\",\"2016-05-19T22:50:25.000-0700\""
                    }
                 }
              }
           ]
        }
        self.assertEqual(result, correct)

    def case52(self):
        query = 'search source="/home/nnguyen/mydata/pooja.csv"'
        job = splunk.search.dispatch(query, hostPath=self.hostPath, sessionKey=self.sessionKey)
        data = {
                'regex_start': '^[^\\ ]*?(\\ )[^\\ ]*?(\\ )[^\\ ]*?(\\ )[^\\ ]*?(\\ )[^\\ ]*?(\\ )[^\\ ]*?(\\ )[^\\ ]*?(\\ )[^\\ ]*?(\\ )',
                'regex_extract': '.{39}',
                'regex_stop': '.*?$',
                'sid': job.sid,
                'type': 'events',
                'field': '_raw',
                'count': 10,
            }
        result = TableUIEvents().setSessionKey(self.sessionKey).results(data)
        correct = \
        [{'field_value': u'"May 19 22:50:25 acmepayroll sshd[17169]: Failed password for backup from 10.11.36.15 port 38184 ssh2","2016-05-19T22:50:25.000-0700"',
          'highlight_range': (62, 101),
          'post_highlight_ranges': [],
          'pre_highlight_ranges': [(4, 5),
                                   (7, 8),
                                   (16, 17),
                                   (28, 29),
                                   (41, 42),
                                   (48, 49),
                                   (57, 58),
                                   (61, 62)]},
         {'field_value': u'"May 19 22:50:24 acmepayroll sshd[15110]: Failed password for invalid user test2 from 10.11.36.43 port 40742 ssh2","2016-05-19T22:50:24.000-0700"',
          'highlight_range': (62, 101),
          'post_highlight_ranges': [],
          'pre_highlight_ranges': [(4, 5),
                                   (7, 8),
                                   (16, 17),
                                   (28, 29),
                                   (41, 42),
                                   (48, 49),
                                   (57, 58),
                                   (61, 62)]},
         {'field_value': u'"May 19 22:50:18 acmepayroll sshd[14307]: Failed password for invalid user pgsql from 10.11.36.50 port 51330 ssh2","2016-05-19T22:50:18.000-0700"',
          'highlight_range': (62, 101),
          'post_highlight_ranges': [],
          'pre_highlight_ranges': [(4, 5),
                                   (7, 8),
                                   (16, 17),
                                   (28, 29),
                                   (41, 42),
                                   (48, 49),
                                   (57, 58),
                                   (61, 62)]},
         {'field_value': u'"May 19 22:49:58 acmepayroll sshd[16495]: Failed password for invalid user smbuser from 10.11.36.25 port 49315 ssh2","2016-05-19T22:49:58.000-0700"',
          'highlight_range': (62, 101),
          'post_highlight_ranges': [],
          'pre_highlight_ranges': [(4, 5),
                                   (7, 8),
                                   (16, 17),
                                   (28, 29),
                                   (41, 42),
                                   (48, 49),
                                   (57, 58),
                                   (61, 62)]},
         {'field_value': u'"May 19 22:49:48 acmepayroll sshd[17085]: Failed password for invalid user amanda from 10.11.36.15 port 54824 ssh2","2016-05-19T22:49:48.000-0700"',
          'highlight_range': (62, 101),
          'post_highlight_ranges': [],
          'pre_highlight_ranges': [(4, 5),
                                   (7, 8),
                                   (16, 17),
                                   (28, 29),
                                   (41, 42),
                                   (48, 49),
                                   (57, 58),
                                   (61, 62)]},
         {'field_value': u'"May 19 22:49:26 acmepayroll sshd[17450]: Failed password for invalid user 1 from 10.11.36.15 port 37831 ssh2","2016-05-19T22:49:26.000-0700"',
          'highlight_range': (62, 101),
          'post_highlight_ranges': [],
          'pre_highlight_ranges': [(4, 5),
                                   (7, 8),
                                   (16, 17),
                                   (28, 29),
                                   (41, 42),
                                   (48, 49),
                                   (57, 58),
                                   (61, 62)]},
         {'field_value': u'"May 19 22:49:24 acmepayroll sshd[14373]: Failed password for invalid user sales from 10.11.36.26 port 52962 ssh2","2016-05-19T22:49:24.000-0700"',
          'highlight_range': (62, 101),
          'post_highlight_ranges': [],
          'pre_highlight_ranges': [(4, 5),
                                   (7, 8),
                                   (16, 17),
                                   (28, 29),
                                   (41, 42),
                                   (48, 49),
                                   (57, 58),
                                   (61, 62)]},
         {'field_value': u'"May 19 22:48:37 acmepayroll sshd[17796]: Failed password for root from 10.11.36.25 port 42113 ssh2","2016-05-19T22:48:37.000-0700"',
          'highlight_range': (62, 101),
          'post_highlight_ranges': [],
          'pre_highlight_ranges': [(4, 5),
                                   (7, 8),
                                   (16, 17),
                                   (28, 29),
                                   (41, 42),
                                   (48, 49),
                                   (57, 58),
                                   (61, 62)]},
         {'field_value': u'"May 19 22:48:13 acmepayroll sshd[17759]: Failed password for invalid user oracle from 10.11.36.39 port 40609 ssh2","2016-05-19T22:48:13.000-0700"',
          'highlight_range': (62, 101),
          'post_highlight_ranges': [],
          'pre_highlight_ranges': [(4, 5),
                                   (7, 8),
                                   (16, 17),
                                   (28, 29),
                                   (41, 42),
                                   (48, 49),
                                   (57, 58),
                                   (61, 62)]},
         {'field_value': u'"May 19 22:48:13 acmepayroll sshd[15460]: Failed password for invalid user ftpuser from 10.11.36.45 port 42977 ssh2","2016-05-19T22:48:13.000-0700"',
          'highlight_range': (62, 101),
          'post_highlight_ranges': [],
          'pre_highlight_ranges': [(4, 5),
                                   (7, 8),
                                   (16, 17),
                                   (28, 29),
                                   (41, 42),
                                   (48, 49),
                                   (57, 58),
                                   (61, 62)]}]
        self.assertEqual(result, correct)

    def case53(self):
        query = 'search source="/home/nnguyen/mydata/pooja3.csv" system-alert'
        job = splunk.search.dispatch(query, hostPath=self.hostPath, sessionKey=self.sessionKey)
        data = {
                'sid': job.sid,
                'selected_text': 'system-alert-00012',
                'field_value': 'May 19 22:42:28 2016 30.40.50.60 ACME-006: NetScreen device_id=ACME-006  [Root]system-alert-00012: UDP flood! From 1.2.3.5:6868 to 1.2.3.7:30111, proto UDP (zone Untrust int  redundant1.3). Occurred 4 times. (2016-05-19 22:42:28)',
                'start_position': '78',
                'end_position': '96',
                'type': 'rules_new',
                'field': '_raw'
        }
        result = TableUINewRule().setSessionKey(self.sessionKey).results(data)
        correct = \
        {
           "extract_rules": [
              {
                 "regex": ".{18}", 
                 "type": {
                    "metadata": {
                       "selectedTextLength": 18
                    }, 
                    "label": "number_of_characters"
                 }
              }, 
              {
                 "regex": ".+", 
                 "type": {
                    "metadata": {}, 
                    "label": "any_character"
                 }
              }
           ], 
           "start_rules": [
              {
                 "regex": "^[^t]*?(t)[^t]*?(t)", 
                 "type": {
                    "metadata": {
                       "preCharName": "t", 
                       "preCharCount": 2
                    }, 
                    "label": "nth_character"
                 }
              }, 
              {
                 "regex": "^[^\\ ]*?(\\ )[^\\ ]*?(\\ )[^\\ ]*?(\\ )[^\\ ]*?(\\ )[^\\ ]*?(\\ )[^\\ ]*?(\\ )[^\\ ]*?(\\ )[^\\ ]*?(\\ )[^\\ ]*?(\\ )[^t]*?(t)", 
                 "type": {
                    "metadata": {
                       "preSpaceCount": 9, 
                       "preChar": "t"
                    }, 
                    "label": "n_spaces_and_starting_character"
                 }
              }, 
              {
                 "regex": "^.{78}", 
                 "type": {
                    "metadata": {
                       "preStrLength": 78
                    }, 
                    "label": "n_characters"
                 }
              }, 
              {
                 "regex": ".*?", 
                 "type": {
                    "metadata": {}, 
                    "label": "any_characters"
                 }
              }, 
              {
                 "regex": "^[^\\ ]*?(\\ )[^\\ ]*?(\\ )[^\\ ]*?(\\ )[^\\ ]*?(\\ )[^\\ ]*?(\\ )[^\\ ]*?(\\ )[^\\ ]*?(\\ )[^\\ ]*?(\\ )[^\\ ]*?(\\ ).*?(\\[Root)", 
                 "type": {
                    "metadata": {
                       "preStrAfterSpace": "[Root", 
                       "preSpaceCount": 9
                    }, 
                    "label": "n_spaces_and_preceding_string"
                 }
              }, 
              {
                 "regex": "^[^\\ ]*?(\\ )[^\\ ]*?(\\ )[^\\ ]*?(\\ )[^\\ ]*?(\\ )[^\\ ]*?(\\ )[^\\ ]*?(\\ )[^\\ ]*?(\\ )[^\\ ]*?(\\ )[^\\ ]*?(\\ )[^\\[]*?(\\[).*?(Root)", 
                 "type": {
                    "metadata": {
                       "preSpaceCount": 9, 
                       "preWord": "Root"
                    }, 
                    "label": "n_spaces_and_preceding_word"
                 }
              }, 
              {
                 "regex": "^.*?(Root)", 
                 "type": {
                    "metadata": {
                       "preWord": "Root"
                    }, 
                    "label": "preceding_word"
                 }
              }, 
              {
                 "regex": "^.*?(\\[Root)", 
                 "type": {
                    "metadata": {
                       "literal": "[Root"
                    }, 
                    "label": "after_literal"
                 }
              }
           ], 
           "stop_rules": [
              {
                 "regex": ".*?$", 
                 "type": {
                    "metadata": {}, 
                    "label": "any_characters"
                 }
              }, 
              {
                 "regex": "(2\\:).*?$", 
                 "type": {
                    "metadata": {
                       "literal": "2:"
                    }, 
                    "label": "before_literal"
                 }
              }, 
              {
                 "regex": "(2)[^2]*?(2)[^2]*?(2)[^2]*?(2)[^2]*?(2)[^2]*?(2)[^2]*?(2)[^2]*?(2)[^2]*?$", 
                 "type": {
                    "metadata": {
                       "stopCharName": "2", 
                       "stopCharCount": 8
                    }, 
                    "label": "nth_character"
                 }
              }, 
              {
                 "regex": "(2)[^2]*?(\\ )[^\\ ]*?(\\ )[^\\ ]*?(\\ )[^\\ ]*?(\\ )[^\\ ]*?(\\ )[^\\ ]*?(\\ )[^\\ ]*?(\\ )[^\\ ]*?(\\ )[^\\ ]*?(\\ )[^\\ ]*?(\\ )[^\\ ]*?(\\ )[^\\ ]*?(\\ )[^\\ ]*?(\\ )[^\\ ]*?(\\ )[^\\ ]*?(\\ )[^\\ ]*?(\\ )[^\\ ]*?(\\ )[^\\ ]*?(\\ )[^\\ ]*?$", 
                 "type": {
                    "metadata": {
                       "stopChar": "2", 
                       "followSpaceCount": 18
                    }, 
                    "label": "stopping_character_and_n_spaces"
                 }
              }, 
              {
                 "regex": ".{133}$", 
                 "type": {
                    "metadata": {
                       "followStrLength": 133
                    }, 
                    "label": "n_characters"
                 }
              }, 
              {
                 "regex": "(2\\:).*?(\\ )[^\\ ]*?(\\ )[^\\ ]*?(\\ )[^\\ ]*?(\\ )[^\\ ]*?(\\ )[^\\ ]*?(\\ )[^\\ ]*?(\\ )[^\\ ]*?(\\ )[^\\ ]*?(\\ )[^\\ ]*?(\\ )[^\\ ]*?(\\ )[^\\ ]*?(\\ )[^\\ ]*?(\\ )[^\\ ]*?(\\ )[^\\ ]*?(\\ )[^\\ ]*?(\\ )[^\\ ]*?(\\ )[^\\ ]*?(\\ )[^\\ ]*?$", 
                 "type": {
                    "metadata": {
                       "followStrBeforeSpace": "2:", 
                       "followSpaceCount": 18
                    }, 
                    "label": "following_string_and_n_spaces"
                 }
              }, 
              {
                 "regex": "(2).*?(\\ )[^\\ ]*?(\\ )[^\\ ]*?(\\ )[^\\ ]*?(\\ )[^\\ ]*?(\\ )[^\\ ]*?(\\ )[^\\ ]*?(\\ )[^\\ ]*?(\\ )[^\\ ]*?(\\ )[^\\ ]*?(\\ )[^\\ ]*?(\\ )[^\\ ]*?(\\ )[^\\ ]*?(\\ )[^\\ ]*?(\\ )[^\\ ]*?(\\ )[^\\ ]*?(\\ )[^\\ ]*?(\\ )[^\\ ]*?(\\ )[^\\ ]*?(\\:)[^\\:]*?$", 
                 "type": {
                    "metadata": {
                       "followWord": "2", 
                       "followSpaceCount": 18
                    }, 
                    "label": "following_word_and_n_spaces"
                 }
              }, 
              {
                 "regex": "(2).*?$", 
                 "type": {
                    "metadata": {
                       "followWord": "2"
                    }, 
                    "label": "following_word"
                 }
              }, 
              {
                 "regex": "(2).*?(\\,)[^\\,]*?$", 
                 "type": {
                    "metadata": {
                       "followCommaCount": 1, 
                       "followCharName": "2"
                    }, 
                    "label": "following_character_and_n_commas"
                 }
              }
           ]
        }
        self.assertEqual(result, correct)

    def case54(self):
        query = 'search source="/home/nnguyen/mydata/pooja3.csv" system-alert'
        job = splunk.search.dispatch(query, hostPath=self.hostPath, sessionKey=self.sessionKey)
        data = {
                'regex_start': '^[^t]*?(t)[^t]*?(t)',
                'regex_extract': '.{18}',
                'regex_stop': '.*?$',
                'sid': job.sid,
                'type': 'rules_existing',
                'field': '_raw',
            }
        result = TableUIExistingRule().setSessionKey(self.sessionKey).results(data)
        correct = \
        {
           "stop_rules": [
              {
                 "type": {
                    "label": "following_characters", 
                    "metadata": {
                       "followChars": "7"
                    }
                 }, 
                 "regex": "(7).*?$"
              }, 
              {
                 "type": {
                    "label": "any_characters", 
                    "metadata": {}
                 }, 
                 "regex": ".*?$"
              }, 
              {
                 "type": {
                    "label": "before_literal", 
                    "metadata": {
                       "literal": "7:"
                    }
                 }, 
                 "regex": "(7\\:).*?$"
              }, 
              {
                 "type": {
                    "label": "n_characters", 
                    "metadata": {
                       "followStrLength": 136
                    }
                 }, 
                 "regex": ".{136}$"
              }, 
#              {
#                 "type": {
#                    "label": "following_word", 
#                    "metadata": {
#                       "followWord": "7"
#                    }
#                 }, 
#                 "regex": "(7).*?$"
#              }, 
              {
                 "type": {
                    "label": "following_character_and_n_commas", 
                    "metadata": {
                       "followCommaCount": 1, 
                       "followCharName": "7"
                    }
                 }, 
                 "regex": "(7).*?(\\,)[^\\,]*?$"
              }, 
              {
                 "type": {
                    "label": "nth_character", 
                    "metadata": {
                       "stopCharName": "7", 
                       "stopCharCount": 2
                    }
                 }, 
                 "regex": "(7)[^7]*?(7)[^7]*?$"
              }, 
              {
                 "type": {
                    "label": "stopping_character_and_n_spaces", 
                    "metadata": {
                       "followSpaceCount": 16, 
                       "stopChar": "7"
                    }
                 }, 
                 "regex": "(7)[^7]*?(\\ )[^\\ ]*?(\\ )[^\\ ]*?(\\ )[^\\ ]*?(\\ )[^\\ ]*?(\\ )[^\\ ]*?(\\ )[^\\ ]*?(\\ )[^\\ ]*?(\\ )[^\\ ]*?(\\ )[^\\ ]*?(\\ )[^\\ ]*?(\\ )[^\\ ]*?(\\ )[^\\ ]*?(\\ )[^\\ ]*?(\\ )[^\\ ]*?(\\ )[^\\ ]*?(\\ )[^\\ ]*?$"
              }, 
              {
                 "type": {
                    "label": "following_string_and_n_spaces", 
                    "metadata": {
                       "followStrBeforeSpace": "7:", 
                       "followSpaceCount": 16
                    }
                 }, 
                 "regex": "(7\\:).*?(\\ )[^\\ ]*?(\\ )[^\\ ]*?(\\ )[^\\ ]*?(\\ )[^\\ ]*?(\\ )[^\\ ]*?(\\ )[^\\ ]*?(\\ )[^\\ ]*?(\\ )[^\\ ]*?(\\ )[^\\ ]*?(\\ )[^\\ ]*?(\\ )[^\\ ]*?(\\ )[^\\ ]*?(\\ )[^\\ ]*?(\\ )[^\\ ]*?(\\ )[^\\ ]*?(\\ )[^\\ ]*?$"
              }, 
              {
                 "type": {
                    "label": "following_word_and_n_spaces", 
                    "metadata": {
                       "followSpaceCount": 16, 
                       "followWord": "7"
                    }
                 }, 
                 "regex": "(7).*?(\\ )[^\\ ]*?(\\ )[^\\ ]*?(\\ )[^\\ ]*?(\\ )[^\\ ]*?(\\ )[^\\ ]*?(\\ )[^\\ ]*?(\\ )[^\\ ]*?(\\ )[^\\ ]*?(\\ )[^\\ ]*?(\\ )[^\\ ]*?(\\ )[^\\ ]*?(\\ )[^\\ ]*?(\\ )[^\\ ]*?(\\ )[^\\ ]*?(\\ )[^\\ ]*?(\\ )[^\\ ]*?(\\:)[^\\:]*?$"
              }
           ], 
           "start_rules": [
              {
                 "type": {
                    "label": "nth_character", 
                    "metadata": {
                       "preCharName": "t", 
                       "preCharCount": 2
                    }
                 }, 
                 "regex": "^[^t]*?(t)[^t]*?(t)"
              }, 
              {
                 "type": {
                    "label": "n_spaces_and_starting_character", 
                    "metadata": {
                       "preSpaceCount": 9, 
                       "preChar": "t"
                    }
                 }, 
                 "regex": "^[^\\ ]*?(\\ )[^\\ ]*?(\\ )[^\\ ]*?(\\ )[^\\ ]*?(\\ )[^\\ ]*?(\\ )[^\\ ]*?(\\ )[^\\ ]*?(\\ )[^\\ ]*?(\\ )[^\\ ]*?(\\ )[^t]*?(t)"
              }, 
              {
                 "type": {
                    "label": "n_characters", 
                    "metadata": {
                       "preStrLength": 87
                    }
                 }, 
                 "regex": "^.{87}"
              }, 
              {
                 "type": {
                    "label": "any_characters", 
                    "metadata": {}
                 }, 
                 "regex": ".*?"
              }, 
              {
                 "type": {
                    "label": "n_spaces_and_preceding_string", 
                    "metadata": {
                       "preSpaceCount": 9, 
                       "preStrAfterSpace": "[Root"
                    }
                 }, 
                 "regex": "^[^\\ ]*?(\\ )[^\\ ]*?(\\ )[^\\ ]*?(\\ )[^\\ ]*?(\\ )[^\\ ]*?(\\ )[^\\ ]*?(\\ )[^\\ ]*?(\\ )[^\\ ]*?(\\ )[^\\ ]*?(\\ ).*?(\\[Root)"
              }, 
              {
                 "type": {
                    "label": "n_spaces_and_preceding_word", 
                    "metadata": {
                       "preSpaceCount": 9, 
                       "preWord": "Root"
                    }
                 }, 
                 "regex": "^[^\\ ]*?(\\ )[^\\ ]*?(\\ )[^\\ ]*?(\\ )[^\\ ]*?(\\ )[^\\ ]*?(\\ )[^\\ ]*?(\\ )[^\\ ]*?(\\ )[^\\ ]*?(\\ )[^\\ ]*?(\\ )[^\\[]*?(\\[).*?(Root)"
              }, 
              {
                 "type": {
                    "label": "preceding_word", 
                    "metadata": {
                       "preWord": "Root"
                    }
                 }, 
                 "regex": "^.*?(Root)"
              }, 
              {
                 "type": {
                    "label": "after_literal", 
                    "metadata": {
                       "literal": "[Root"
                    }
                 }, 
                 "regex": "^.*?(\\[Root)"
              }
           ], 
           "extract_rules": [
              {
                 "type": {
                    "label": "any_character_but_following_character", 
                    "metadata": {
                       "followCharName": "7"
                    }
                 }, 
                 "regex": "[^7]+"
              }, 
              {
                 "type": {
                    "label": "any_character", 
                    "metadata": {}
                 }, 
                 "regex": ".+"
              }, 
              {
                 "type": {
                    "label": "number_of_characters", 
                    "metadata": {
                       "selectedTextLength": 18
                    }
                 }, 
                 "regex": ".{18}"
              }, 
              {
                 "type": {
                    "label": "word_characters_and_contained_irregular_characters", 
                    "metadata": {
                       "uniqueIrregChars": "]-"
                    }
                 }, 
                 "regex": "[\\w\\]\\-\\ ]+"
              }
           ]
        }
        self.assertEqual(result, correct)

    def case55(self):
        query = 'search source="/home/nnguyen/mydata/pooja3.csv" system-alert'
        job = splunk.search.dispatch(query, hostPath=self.hostPath, sessionKey=self.sessionKey)
        data = {
                'regex_start': '^[^t]*?(t)[^t]*?(t)',
                'regex_extract': '.{18}',
                'regex_stop': '.*?$',
                'sid': job.sid,
                'type': 'events',
                'count': 5,
                'field': '_raw',
            }
        result = TableUIEvents().setSessionKey(self.sessionKey).results(data)
        correct = \
        [{'field_value': u'"May 19 22:42:28 2016 30.40.50.60 PROD-MFS-005: NetScreen device_id=PROD-MFS-005  [Root]system-alert-00027: Login attempt by admin root from 10.1.0.11 is refused as this account is locked (2016-05-19 22:42:28)","2016-05-19T22:42:28.000-0700"',
          'highlight_range': (87, 105),
          'post_highlight_ranges': [],
          'pre_highlight_ranges': [(50, 51), (86, 87)]},
         {'field_value': u'"May 19 22:42:28 2016 30.40.50.60 COREDEV-003: NetScreen device_id=COREDEV-003  [Root]system-alert-00012: UDP flood! From 1.2.3.5:6868 to 1.2.3.7:30111, proto UDP (zone Untrust int  redundant1.3). Occurred 2 times. (2016-05-19 22:42:28)","2016-05-19T22:42:28.000-0700"',
          'highlight_range': (85, 103),
          'post_highlight_ranges': [],
          'pre_highlight_ranges': [(49, 50), (84, 85)]},
         {'field_value': u'"May 19 22:42:28 2016 30.40.50.60 PROD-POS-004: NetScreen device_id=PROD-POS-004  [Root]system-alert-00012: UDP flood! From 1.2.3.5:6868 to 1.2.3.7:30111, proto UDP (zone Untrust int  redundant1.3). Occurred 37 times. (2016-05-19 22:42:28)","2016-05-19T22:42:28.000-0700"',
          'highlight_range': (87, 105),
          'post_highlight_ranges': [],
          'pre_highlight_ranges': [(50, 51), (86, 87)]},
         {'field_value': u'"May 19 22:42:28 2016 30.40.50.60 ACME-006: NetScreen device_id=ACME-006  [Root]system-alert-00012: UDP flood! From 1.2.3.5:6868 to 1.2.3.7:30111, proto UDP (zone Untrust int  redundant1.3). Occurred 4 times. (2016-05-19 22:42:28)","2016-05-19T22:42:28.000-0700"',
          'highlight_range': (79, 97),
          'post_highlight_ranges': [],
          'pre_highlight_ranges': [(46, 47), (78, 79)]}]
        self.assertEqual(result, correct)

    def case56(self):
        query = 'search source="/home/nnguyen/mydata/pooja3.csv" system-alert'
        job = splunk.search.dispatch(query, hostPath=self.hostPath, sessionKey=self.sessionKey)
        data = {
                'regex_start': '^[^t]*?(t)[^t]*?(t)',
                'regex_extract': '[^7]+',
                'regex_stop': '(7).*?$',
                'sid': job.sid,
                'type': 'events',
                'count': 5,
                'field': '_raw',
            }
        result = TableUIEvents().setSessionKey(self.sessionKey).results(data)
        correct = \
        [{'field_value': u'"May 19 22:42:28 2016 30.40.50.60 PROD-MFS-005: NetScreen device_id=PROD-MFS-005  [Root]system-alert-00027: Login attempt by admin root from 10.1.0.11 is refused as this account is locked (2016-05-19 22:42:28)","2016-05-19T22:42:28.000-0700"',
          'highlight_range': (87, 105),
          'post_highlight_ranges': [(105, 106)],
          'pre_highlight_ranges': [(50, 51), (86, 87)]},
         {'field_value': u'"May 19 22:42:28 2016 30.40.50.60 COREDEV-003: NetScreen device_id=COREDEV-003  [Root]system-alert-00012: UDP flood! From 1.2.3.5:6868 to 1.2.3.7:30111, proto UDP (zone Untrust int  redundant1.3). Occurred 2 times. (2016-05-19 22:42:28)","2016-05-19T22:42:28.000-0700"',
          'highlight_range': (85, 144),
          'post_highlight_ranges': [(144, 145)],
          'pre_highlight_ranges': [(49, 50), (84, 85)]},
         {'field_value': u'"May 19 22:42:28 2016 30.40.50.60 PROD-POS-004: NetScreen device_id=PROD-POS-004  [Root]system-alert-00012: UDP flood! From 1.2.3.5:6868 to 1.2.3.7:30111, proto UDP (zone Untrust int  redundant1.3). Occurred 37 times. (2016-05-19 22:42:28)","2016-05-19T22:42:28.000-0700"',
          'highlight_range': (87, 146),
          'post_highlight_ranges': [(146, 147)],
          'pre_highlight_ranges': [(50, 51), (86, 87)]},
         {'field_value': u'"May 19 22:42:28 2016 30.40.50.60 ACME-006: NetScreen device_id=ACME-006  [Root]system-alert-00012: UDP flood! From 1.2.3.5:6868 to 1.2.3.7:30111, proto UDP (zone Untrust int  redundant1.3). Occurred 4 times. (2016-05-19 22:42:28)","2016-05-19T22:42:28.000-0700"',
          'highlight_range': (79, 138),
          'post_highlight_ranges': [(138, 139)],
          'pre_highlight_ranges': [(46, 47), (78, 79)]}]
        self.assertEqual(result, correct)
         

    def case57(self):
        '''
        This shows that SPL-123833 is resolved.
        '''
        query = 'search source="/home/nnguyen/mydata/pooja3.csv" system-alert-00012'
        job = splunk.search.dispatch(query, hostPath=self.hostPath, sessionKey=self.sessionKey)
        data = {
                'regex_start': '^[^\\ ]*?(\\ )[^\\ ]*?(\\ )[^\\ ]*?(\\ )[^\\ ]*?(\\ )[^\\ ]*?(\\ )[^\\ ]*?(\\ )[^\\ ]*?(\\ )[^\\ ]*?(\\ )[^\\ ]*?(\\ )[^t]*?(t)',
                'regex_extract': '[^\\:]+',
                'regex_stop': '(\\:)',
                'sid': job.sid,
                'type': 'rules_existing',
                'field': '_raw',
            }
        result = TableUIExistingRule().setSessionKey(self.sessionKey).results(data)
        correct = \
        {
           "stop_rules": [
              {
                 "regex": "(\\:).*?$", 
                 "type": {
                    "metadata": {
                       "followChars": ":"
                    }, 
                    "label": "following_characters"
                 }
              }, 
              {
                 "regex": ".*?$", 
                 "type": {
                    "metadata": {}, 
                    "label": "any_characters"
                 }
              }, 
              {
                 "regex": "(\\:)[^\\:]*?(\\:)[^\\:]*?(\\:)[^\\:]*?(\\:)[^\\:]*?(\\:)[^\\:]*?(\\:)[^\\:]*?(\\:)[^\\:]*?$", 
                 "type": {
                    "metadata": {
                       "stopCharCount": 7, 
                       "stopCharName": ":"
                    }, 
                    "label": "nth_character"
                 }
              }, 
              {
                 "regex": "(\\:)[^\\:]*?(\\ )[^\\ ]*?(\\ )[^\\ ]*?(\\ )[^\\ ]*?(\\ )[^\\ ]*?(\\ )[^\\ ]*?(\\ )[^\\ ]*?(\\ )[^\\ ]*?(\\ )[^\\ ]*?(\\ )[^\\ ]*?(\\ )[^\\ ]*?(\\ )[^\\ ]*?(\\ )[^\\ ]*?(\\ )[^\\ ]*?(\\ )[^\\ ]*?(\\ )[^\\ ]*?(\\ )[^\\ ]*?(\\ )[^\\ ]*?(\\ )[^\\ ]*?$", 
                 "type": {
                    "metadata": {
                       "stopChar": ":", 
                       "followSpaceCount": 18
                    }, 
                    "label": "stopping_character_and_n_spaces"
                 }
              }, 
              {
                 "regex": "(\\:).*?(\\,)[^\\,]*?(\\,)[^\\,]*?$", 
                 "type": {
                    "metadata": {
                       "followCharName": ":", 
                       "followCommaCount": 2
                    }, 
                    "label": "following_character_and_n_commas"
                 }
              }, 
              {
                 "regex": ".{164}$", 
                 "type": {
                    "metadata": {
                       "followStrLength": 164
                    }, 
                    "label": "n_characters"
                 }
              }
           ], 
           "extract_rules": [
              {
                 "regex": "[^\\:]+", 
                 "type": {
                    "metadata": {
                       "followCharName": ":"
                    }, 
                    "label": "any_character_but_following_character"
                 }
              }, 
              {
                 "regex": ".{19}", 
                 "type": {
                    "metadata": {
                       "selectedTextLength": 19
                    }, 
                    "label": "number_of_characters"
                 }
              }, 
              {
                 "regex": "[\\w\\]\\-\\ ]+", 
                 "type": {
                    "metadata": {
                       "uniqueIrregChars": "]-"
                    }, 
                    "label": "word_characters_and_contained_irregular_characters"
                 }
              }, 
              {
                 "regex": ".+", 
                 "type": {
                    "metadata": {}, 
                    "label": "any_character"
                 }
              }
           ], 
           "start_rules": [
              {
                 "regex": "^[^t]*?(t)[^t]*?(t)", 
                 "type": {
                    "metadata": {
                       "preCharCount": 2, 
                       "preCharName": "t"
                    }, 
                    "label": "nth_character"
                 }
              }, 
              {
                 "regex": "^[^\\ ]*?(\\ )[^\\ ]*?(\\ )[^\\ ]*?(\\ )[^\\ ]*?(\\ )[^\\ ]*?(\\ )[^\\ ]*?(\\ )[^\\ ]*?(\\ )[^\\ ]*?(\\ )[^\\ ]*?(\\ )[^t]*?(t)", 
                 "type": {
                    "metadata": {
                       "preChar": "t", 
                       "preSpaceCount": 9
                    }, 
                    "label": "n_spaces_and_starting_character"
                 }
              }, 
              {
                 "regex": "^.{85}", 
                 "type": {
                    "metadata": {
                       "preStrLength": 85
                    }, 
                    "label": "n_characters"
                 }
              }, 
              {
                 "regex": ".*?", 
                 "type": {
                    "metadata": {}, 
                    "label": "any_characters"
                 }
              }, 
              {
                 "regex": "^[^\\ ]*?(\\ )[^\\ ]*?(\\ )[^\\ ]*?(\\ )[^\\ ]*?(\\ )[^\\ ]*?(\\ )[^\\ ]*?(\\ )[^\\ ]*?(\\ )[^\\ ]*?(\\ )[^\\ ]*?(\\ ).*?(\\[Root)", 
                 "type": {
                    "metadata": {
                       "preStrAfterSpace": "[Root", 
                       "preSpaceCount": 9
                    }, 
                    "label": "n_spaces_and_preceding_string"
                 }
              }, 
              {
                 "regex": "^[^\\ ]*?(\\ )[^\\ ]*?(\\ )[^\\ ]*?(\\ )[^\\ ]*?(\\ )[^\\ ]*?(\\ )[^\\ ]*?(\\ )[^\\ ]*?(\\ )[^\\ ]*?(\\ )[^\\ ]*?(\\ )[^\\[]*?(\\[).*?(Root)", 
                 "type": {
                    "metadata": {
                       "preWord": "Root", 
                       "preSpaceCount": 9
                    }, 
                    "label": "n_spaces_and_preceding_word"
                 }
              }, 
              {
                 "regex": "^.*?(Root)", 
                 "type": {
                    "metadata": {
                       "preWord": "Root"
                    }, 
                    "label": "preceding_word"
                 }
              }, 
              {
                 "regex": "^.*?(\\[Root)", 
                 "type": {
                    "metadata": {
                       "literal": "[Root"
                    }, 
                    "label": "after_literal"
                 }
              }
           ]
        }
        self.assertEqual(result, correct)        


    def all(self):
#        [getattr(self, 'case%d'%i)() for i in range(1,50)]
        for i in range(1, 58):
            test_case = 'case%d'%i
            print('testing ' + test_case)
            getattr(self, test_case)()


class Test2(unittest.TestCase):
    def __init__(self, *arg, **kwargs):
        super(Test2, self).__init__(*arg, **kwargs)
        owner = 'admin'
        hostPath='https://wimpy.splunk.com:9040'
        self.sessionKey = splunk.auth.getSessionKey('admin', 'changeme', hostPath=hostPath)
        query = 'search source="/home/nnguyen/mydata/product_downloads_scrubbed.log"'
        job = splunk.search.dispatch(query, hostPath=hostPath, sessionKey=self.sessionKey)
        self.sid = job.sid
        self.maxDiff = None
 
    def testEventRetrieval(self, data, correct):
        data.update({'sid': self.sid, 'type': 'events', 'field': '_raw', 'count': 2})
        result  = TableUIEvents().setSessionKey(self.sessionKey).results(data)
        if correct:
            self.assertEqual(result, correct)
        else:
            myprint(result)

    def case1(self):
        data = {
                'regex_start': '^(.{25})',
                'regex_extract': '[^\*]+',
                'regex_stop': '(\*)',
            }
        correct = \
        [{'field_value': u'20.04.2015 17:59:12.553 *INFO* [10.209.8.111 [1429567151809] GET /bin/splunk/DownloadActivityServlet HTTP/1.1] com.splunk.servlet.DownloadActivityServlet [track_download] salesforce_id="0034000001dhuC2AAI" last_download_date="" crm_type="Contact" country="" postal="" splunk_version_downloaded="6.2.2" splunk_file_downloaded="splunk-6.2.2-255606-linux-2.6-amd64.deb" url="https://www.splunk.com/bin/splunk/DownloadActivityServlet?architecture=x86_64&description=splunk-6.2.2-255606-linux-2.6-amd64.deb&Platform=Linux&version=6.2.2&formID=%20239&product=splunk&crmId=0034000001dhuC2AAI&eloquaGUID=undefined&client_ip=undefined&state=3&co_code=undefined&_=1429567150483" activity="Download" geo_countryCode="" geo_countryName="" geo_region="" geo_city="" geo_postalCode="" geo_latitude="" geo_longitude="" geo_areaCode="" geo_dmaCode="" geo_countryCode3="" ip_address="undefined" cookie="10.209.0.75.1428283352340639" ac=""',
          'highlight_range': (25, 29),
          'post_highlight_ranges': [(29, 30)],
          'pre_highlight_ranges': [(0, 25)]},
         {'field_value': u'20.04.2015 17:56:59.774 *INFO* [10.209.8.184 [1429567018845] GET /bin/splunk/DownloadActivityServlet HTTP/1.1] com.splunk.servlet.DownloadActivityServlet [track_download] salesforce_id="00Q40000016DoPEEA0" last_download_date="" crm_type="Lead" phone="2066166119" country="United States" postal="98101" splunk_version_downloaded="6.2.2" splunk_file_downloaded="splunk-6.2.2-255606-linux-2.6-x86_64.rpm" url="http://www.splunk.com/bin/splunk/DownloadActivityServlet?architecture=x86_64&description=splunk-6.2.2-255606-linux-2.6-x86_64.rpm&Platform=Linux&version=6.2.2&formID=239&product=splunk&affiliateCode=ga0508_s_splunk&crmId=00Q40000016DoPEEA0&eloquaGUID=8c9e7df6-9eb9-44c7-9116-ad5894ed6fc1&client_ip=205.175.124.217&state=3&co_code=US&_=1429567020101" activity="Download" geo_countryCode="US" geo_countryName="United States" geo_region="WA" geo_city="Seattle" geo_postalCode="98105" geo_latitude="47.6606" geo_longitude="-122.2919" geo_areaCode="206" geo_dmaCode="819" geo_countryCode3="USA" ip_address="205.175.124.217" cookie="205.175.116.217.1415400274741227" ac="ga0508_s_splunk"',
          'highlight_range': (25, 29),
          'post_highlight_ranges': [(29, 30)],
          'pre_highlight_ranges': [(0, 25)]}]
        self.testEventRetrieval(data, correct)

    def case2(self):
        data = {
                'sid': self.sid,
                'selected_text': 'INFO',
                'field_value': '20.04.2015 17:59:12.553 *INFO* [10.209.8.111 [1429567151809] GET /bin/splunk/DownloadActivityServlet HTTP/1.1] com.splunk.servlet.DownloadActivityServlet [track_download] salesforce_id="0034000001dhuC2AAI" last_download_date="" crm_type="Contact" country="" postal="" splunk_version_downloaded="6.2.2" splunk_file_downloaded="splunk-6.2.2-255606-linux-2.6-amd64.deb" url="https://www.splunk.com/bin/splunk/DownloadActivityServlet?architecture=x86_64&description=splunk...',
                'start_position': '25',
                'end_position': '29',
                'type': 'rules_new',
                'field': '_raw'
            }
        class TestRule(TableUINewRule):
            def startingRegexes(self, data):
                return (
                        NthCharacterStartingRegex(data),
                        NSpacesAndStartingCharacterStartingRegex(data),
                        IrregularCharactersStartingRegex(data),
                        NCharactersStartingRegex(data),
                        AnyCharactersStartingRegex(data),
                        NSpacesAndIrregularCharactersStartingRegex(data),
                        NSpacesAndPrecedingStringStartingRegex(data),
                        NSpacesAndPrecedingWordStartingRegex(data),
                        PrecedingWordStartingRegex(data),
                        PrecedingStringStartingRegex(data),
                        NCommasAndPrecedingCharacterStartingRegex(data),
                        StartOfStringStartingRegex(data),
                        FieldNameStartingRegex(data),
                        AfterLiteralStartingRegex(data),
                    )
            def extractionRegexes(self, data):
                return (
                        AnyCharacterButFollowingCharacterExtractionRegex(data),
                        NumberOfCharactersExtractionRegex(data),
                        WordCharactersAndContainedIrregularCharactersExtractionRegex(data),
                        AnyCharacterExtractionRegex(data),
                        EndOfStringExtractionRegex(data),
                        LettersExtractionRegex(data),
                        LowercaseLettersExtractionRegex(data),
                        UppercaseLettersExtractionRegex(data),
                        WordCharactersExtractionRegex(data),
                        NumbersExtractionRegex(data),
                    )

            def stoppingRegexes(self, data):
                return (
                        FollowingCharacterStoppingRegex(data),
                        AnyCharacterStoppingRegex(data),
                        BeforeLiteralStoppingRegex(data),
                    )

        results = TestRule().setSessionKey(self.sessionKey).results(data)
        correct = \
        {
           "stop_rules": [
              {
                 "regex": "(\\*).*?$", 
                 "type": {
                    "metadata": {
                       "followChars": "*"
                    }, 
                    "label": "following_characters"
                 }
              }, 
              {
                 "regex": ".*?$", 
                 "type": {
                    "metadata": {}, 
                    "label": "any_characters"
                 }
              }, 
#              {
#                 "regex": "(\\*).*?$", 
#                 "type": {
#                    "metadata": {
#                       "literal": "*"
#                    }, 
#                    "label": "before_literal"
#                 }
#              }
           ], 
           "extract_rules": [
              {
                 "regex": "[^\\*]+", 
                 "type": {
                    "metadata": {
                       "followCharName": "*"
                    }, 
                    "label": "any_character_but_following_character"
                 }
              }, 
              {
                 "regex": ".{4}", 
                 "type": {
                    "metadata": {
                       "selectedTextLength": 4
                    }, 
                    "label": "number_of_characters"
                 }
              }, 
              {
                 "regex": ".+", 
                 "type": {
                    "metadata": {}, 
                    "label": "any_character"
                 }
              }, 
              {
                 "regex": "[a-zA-Z]+", 
                 "type": {
                    "metadata": {}, 
                    "label": "letters"
                 }
              }, 
              {
                 "regex": "[A-Z]+", 
                 "type": {
                    "metadata": {}, 
                    "label": "uppercase_letters"
                 }
              }, 
              {
                 "regex": "\\w+", 
                 "type": {
                    "metadata": {}, 
                    "label": "word_characters"
                 }
              }
           ], 
           "start_rules": [
              {
                 "regex": "^[^\\ ]*?(\\ )[^\\ ]*?(\\ )[^\\*]*?(\\*)", 
                 "type": {
                    "metadata": {
                       "preChar": "*", 
                       "preSpaceCount": 2
                    }, 
                    "label": "n_spaces_and_starting_character"
                 }
              }, 
              {
                 "regex": "^[^\\.]*?(\\.)[^\\.]*?(\\.)[^\\:]*?(\\:)[^\\:]*?(\\:)[^\\.]*?(\\.)[^\\*]*?(\\*)", 
                 "type": {
                    "metadata": {
                       "preIrregChars": "..::.*"
                    }, 
                    "label": "irregular_characters"
                 }
              }, 
              {
                 "regex": "^.{25}", 
                 "type": {
                    "metadata": {
                       "preStrLength": 25
                    }, 
                    "label": "n_characters"
                 }
              }, 
              {
                 "regex": ".*?", 
                 "type": {
                    "metadata": {}, 
                    "label": "any_characters"
                 }
              }, 
              {
                 "regex": "^.*?(\\*)", 
                 "type": {
                    "metadata": {
                       "literal": "*"
                    }, 
                    "label": "after_literal"
                 }
              }
           ]
        }
        self.assertEqual(results, correct) 

    def all(self):
        for i in range(1, 3):
            test_case = 'case%d'%i
            print('testing ' + test_case)
            getattr(self, test_case)()



class RemoteTest(unittest.TestCase):
    '''
        Test the REST endpoint /services/field_extractor/generate_regex
    '''
    def __init__(self, *args, **kwargs):
        super(RemoteTest, self).__init__(*args, **kwargs)
        owner = 'admin'
        password = 'changeme'
        self.hostPath='https://wimpy.splunk.com:9040'
        restEndPoint = "/services/field_extractor/generate_regex"
        self.url = self.hostPath + restEndPoint
        self.sessionKey = splunk.auth.getSessionKey('admin', 'changeme', hostPath=self.hostPath)
        query = 'search source="/home/nnguyen/mydata/alcatel.1k.log" '
        job = splunk.search.dispatch(query, hostPath=self.hostPath, sessionKey=self.sessionKey)
        self.sid = job.sid
        import httplib2
        self.http = httplib2.Http(".cache", disable_ssl_certificate_validation=True)
        self.http.add_credentials(owner, password)
        self.maxDiff = None

    def httprequest(self, data, method='GET'):
        from future.moves.urllib import parse as urllib_parse

        try:
            if isinstance(data, str):
                response, content = self.http.request(self.url + '?' + data, method=method)
            else:
                response, content = self.http.request(self.url + '?' + urllib_parse.urlencode(data), method=method)
            if (response['status'] >= '200' and response['status'] <= '204'):
                return content
            else:
                print('Http Status: ' + str(response['status']))
                return content 
        except Exception as e:
            print("Exception: '%s'" % e)

    def ifx0(self, examples):
        ''' examples is a string
        '''
        query = {'output_mode': 'json',
                'field': '_raw',
                'sid': self.sid,
                'examples': examples
                }
        return self.httprequest(query)

    def ifx(self, examples):
        ''' examples is a list of dicts
        '''
        return self.ifx0(json.dumps(examples))

    def case1(self):
        query = 'output_mode=json&field=_raw&sid='+self.sid+\
        '&examples=[{"_rawtext":"Jul%2024%2000:03:24%20172.22.7.4%20LINK-I-Up:%20%20e13","ip":[16,26]}]'
        result = json.loads(self.httprequest(query))
        correct = \
        {
           "examples": [
              {
                 "ip": [
                    16, 
                    26
                 ], 
                 "_rawtext": "Jul 24 00:03:24 172.22.7.4 LINK-I-Up:  e13"
              }
           ], 
           "field": "_raw", 
           "sid": self.sid,
           "rules": [
              "^(?:[^ \\n]* ){3}(?P<ip>[^ ]+)"
           ]
        }
        self.assertEqual(result, correct)

    def case2(self):
        result = self.ifx0('[{"_rawtext":"Jul 24 00:03:24 172.22.7.4 %LINK-I-Up:  e13","ip":[16,26]}]')
        result = json.loads(result)
        correct = \
        {
           "rules": [
              "^(?:[^ \\n]* ){3}(?P<ip>[^ ]+)"
           ], 
           "sid": self.sid, 
           "examples": [
              {
                 "ip": [
                    16, 
                    26
                 ], 
                 "_rawtext": "Jul 24 00:03:24 172.22.7.4 %LINK-I-Up:  e13"
              }
           ], 
           "field": "_raw"
        }
        self.assertEqual(result, correct)

    def case3(self):
        examples = '[{"_rawtext":"Change 58859 on 2009/05/07 11:53:13 by gerad@win-install integrate 3.2-gerad -> 3.2",\
                    "p4user": [39, 44],\
                    "change_list": [7, 12],\
                    "time_stamp": [16, 35]},\
                    {"workspace": [45, 58],\
                    "_rawtext": "Change 58845 on 2009/05/07 10:09:30 by inder@inder-windoze current -> dm-current",\
                    "p4user":[39, 44],"change_list":[7, 12],"time_stamp":[16, 35]}]'
        result = json.loads(self.ifx0(examples))
        self.assertTrue(len(result['rules']) > 0)

    def case4(self):
        result = self.ifx([{"_rawtext":"Jul 24 00:03:24 172.22.7.4 %LINK-I-Up:  e13","ip":[16, 26]}])
        result = json.loads(result)
        correct = \
        {
           "sid": self.sid,
           "rules": [
              "^(?:[^ \\n]* ){3}(?P<ip>[^ ]+)"
           ], 
           "examples": [
              {
                 "_rawtext": "Jul 24 00:03:24 172.22.7.4 %LINK-I-Up:  e13", 
                 "ip": [
                    16, 
                    26
                 ]
              }
           ], 
           "field": "_raw"
        }
        self.assertEqual(result, correct)

    def case5(self):
        ex1 = {"_rawtext": "Change 58859 on 2009/05/07 11:53:13 by gerad@win-install integrate 3.2-gerad -> 3.2",
                "p4user": [39, 44],
                "change_list": [7, 12],
                "time_stamp": [16, 35]}

        ex2 = {"_rawtext": "Change 58845 on 2009/05/07 10:09:30 by inder@inder-windoze current -> dm-current",
                "workspace": [45, 58],
                "p4user":[39, 44],
                "change_list":[7, 12],
                "time_stamp":[16, 35]}

        result = json.loads(self.ifx([ex1, ex2]))
        self.assertTrue(len(result['rules']) > 0)

    def case6(self):
        ''' Make sure the data file /home/nnguyen/mydata/alcatel.1k.log is imported to splunk before running this test
        '''
        data = {
                'sid': self.sid,
                'selected_text': 'STP-W-PORTSTATUS',
                'field_value': 'Jul 24 00:03:05 172.22.98.4 %STP-W-PORTSTATUS: e4: STP status Forwarding',
                'start_position': '29',
                'end_position': '45',
                'type': 'rules_new',
                'field': '_raw'
        }

        result = json.loads(self.httprequest(data, 'POST'))
        correct = \
        {
           "stop_rules": [
              {
                 "regex": "(\\:).*?$", 
                 "type": {
                    "metadata": {
                       "followChars": ":"
                    }, 
                    "label": "following_characters"
                 }
              }, 
              {
                 "regex": ".*?$", 
                 "type": {
                    "metadata": {}, 
                    "label": "any_characters"
                 }
              }, 
              {
                 "regex": "(\\:)[^\\:]*?(\\:)[^\\:]*?$", 
                 "type": {
                    "metadata": {
                       "stopCharName": ":", 
                       "stopCharCount": 2
                    }, 
                    "label": "nth_character"
                 }
              }, 
              {
                 "regex": "(\\:)[^\\:]*?(\\ )[^\\ ]*?(\\ )[^\\ ]*?(\\ )[^\\ ]*?(\\ )[^\\ ]*?$", 
                 "type": {
                    "metadata": {
                       "followSpaceCount": 4, 
                       "stopChar": ":"
                    }, 
                    "label": "stopping_character_and_n_spaces"
                 }
              }, 
              {
                 "regex": ".{27}$", 
                 "type": {
                    "metadata": {
                       "followStrLength": 27
                    }, 
                    "label": "n_characters"
                 }
              }
           ], 
           "extract_rules": [
              {
                 "regex": "[^\\:]+", 
                 "type": {
                    "metadata": {
                       "followCharName": ":"
                    }, 
                    "label": "any_character_but_following_character"
                 }
              }, 
              {
                 "regex": "[\\w\\-\\ ]+", 
                 "type": {
                    "metadata": {
                       "uniqueIrregChars": "-"
                    }, 
                    "label": "word_characters_and_contained_irregular_characters"
                 }
              }, 
              {
                 "regex": ".+", 
                 "type": {
                    "metadata": {}, 
                    "label": "any_character"
                 }
              }, 
              {
                 "regex": ".{16}", 
                 "type": {
                    "metadata": {
                       "selectedTextLength": 16
                    }, 
                    "label": "number_of_characters"
                 }
              }
           ], 
           "start_rules": [
              {
                 "regex": "^[^\\ ]*?(\\ )[^\\ ]*?(\\ )[^\\ ]*?(\\ )[^\\ ]*?(\\ )[^\\%]*?(\\%)", 
                 "type": {
                    "metadata": {
                       "preSpaceCount": 4, 
                       "preChar": "%"
                    }, 
                    "label": "n_spaces_and_starting_character"
                 }
              }, 
              {
                 "regex": "^[^\\:]*?(\\:)[^\\:]*?(\\:)[^\\.]*?(\\.)[^\\.]*?(\\.)[^\\.]*?(\\.)[^\\%]*?(\\%)", 
                 "type": {
                    "metadata": {
                       "preIrregChars": "::...%"
                    }, 
                    "label": "irregular_characters"
                 }
              }, 
              {
                 "regex": "^.{29}", 
                 "type": {
                    "metadata": {
                       "preStrLength": 29
                    }, 
                    "label": "n_characters"
                 }
              }, 
              {
                 "regex": ".*?", 
                 "type": {
                    "metadata": {}, 
                    "label": "any_characters"
                 }
              }, 
              {
                 "regex": "^.*?(\\%)", 
                 "type": {
                    "metadata": {
                       "literal": "%"
                    }, 
                    "label": "after_literal"
                 }
              }
           ]
        }
 
        self.assertEqual(result, correct)
                
    def case7(self):
        ''' Make sure the data file /home/nnguyen/mydata/alcatel.1k.log is imported to splunk before running this test
        '''
        data = {
                'sid': self.sid,
                'selected_text': 'admin',
                'field_value': 'Audit:[id=, timestamp=02-22-2016 15:33:25.485, user=admin, action=search, info=granted REST: /search/timeparser/tz][n/a]',
                'start_position': '52',
                'end_position': '57',
                'type': 'rules_new',
                'field': '_raw',
        }
        result = json.loads(self.httprequest(data, 'POST'))
        correct = \
        {
           "start_rules": [
              {
                 "regex": ".*?", 
                 "type": {
                    "label": "any_characters", 
                    "metadata": {}
                 }
              }, 
              {
                 "regex": "^.{52}", 
                 "type": {
                    "label": "n_characters", 
                    "metadata": {
                       "preStrLength": 52
                    }
                 }
              }, 
              {
                 "regex": "^[^\\=]*?(\\=)[^\\=]*?(\\=)[^\\=]*?(\\=)", 
                 "type": {
                    "label": "nth_character", 
                    "metadata": {
                       "preCharCount": 3, 
                       "preCharName": "="
                    }
                 }
              }, 
              {
                 "regex": "^[^\\ ]*?(\\ )[^\\ ]*?(\\ )[^\\ ]*?(\\ )[^\\=]*?(\\=)", 
                 "type": {
                    "label": "n_spaces_and_starting_character", 
                    "metadata": {
                       "preSpaceCount": 3, 
                       "preChar": "="
                    }
                 }
              }, 
              {
                 "regex": "^[^\\ ]*?(\\ )[^\\ ]*?(\\ )[^\\ ]*?(\\ ).*?(user\\=)", 
                 "type": {
                    "label": "n_spaces_and_preceding_string", 
                    "metadata": {
                       "preStrAfterSpace": "user=", 
                       "preSpaceCount": 3
                    }
                 }
              }, 
              {
                 "regex": "^[^\\,]*?(\\,)[^\\,]*?(\\,).*?(\\=)", 
                 "type": {
                    "label": "n_commas_and_preceding_character", 
                    "metadata": {
                       "preCharName": "=", 
                       "preCommaCount": 2
                    }
                 }
              }, 
              {
                 "regex": "^.*?(user\\=)", 
                 "type": {
                    "label": "field_name", 
                    "metadata": {
                       "preFieldNameAndChar": "user="
                    }
                 }
              }, 
           ], 
           "extract_rules": [
              {
                 "regex": "[^\\,]+", 
                 "type": {
                    "label": "any_character_but_following_character", 
                    "metadata": {
                       "followCharName": ","
                    }
                 }
              }, 
              {
                 "regex": ".{5}", 
                 "type": {
                    "label": "number_of_characters", 
                    "metadata": {
                       "selectedTextLength": 5
                    }
                 }
              }, 
              {
                 "regex": ".+", 
                 "type": {
                    "label": "any_character", 
                    "metadata": {}
                 }
              }, 
              {
                 "regex": "[a-zA-Z]+", 
                 "type": {
                    "label": "letters", 
                    "metadata": {}
                 }
              }, 
              {
                 "regex": "\\w+", 
                 "type": {
                    "label": "word_characters", 
                    "metadata": {}
                 }
              }, 
              {
                 "regex": "[a-z]+", 
                 "type": {
                    "label": "lowercase_letters", 
                    "metadata": {}
                 }
              }
           ], 
           "stop_rules": [
              {
                 "regex": ".*?$", 
                 "type": {
                    "label": "any_characters", 
                    "metadata": {}
                 }
              }, 
              {
                 "regex": "(\\,).*?$", 
                 "type": {
                    "label": "following_characters", 
                    "metadata": {
                       "followChars": ","
                    }
                 }
              }, 
              {
                 "regex": "(\\,)[^\\,]*?(\\,)[^\\,]*?$", 
                 "type": {
                    "label": "nth_character", 
                    "metadata": {
                       "stopCharName": ",", 
                       "stopCharCount": 2
                    }
                 }
              }, 
              {
                 "regex": "(\\,)[^\\,]*?(\\ )[^\\ ]*?(\\ )[^\\ ]*?(\\ )[^\\ ]*?(\\ )[^\\ ]*?$", 
                 "type": {
                    "label": "stopping_character_and_n_spaces", 
                    "metadata": {
                       "stopChar": ",", 
                       "followSpaceCount": 4
                    }
                 }
              }, 
              {
                 "regex": ".{63}$", 
                 "type": {
                    "label": "n_characters", 
                    "metadata": {
                       "followStrLength": 63
                    }
                 }
              }
           ]
        } 
        self.assertEqual(result, correct)

    def all(self):
        for i in range(1, 8):
            test_case = 'case%d'%i
            print('testing ' + test_case)
            getattr(self, test_case)()
