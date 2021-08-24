#!/usr/bin/env python
# This work contains trade
#secrets and confidential material of Splunk Inc., and its use or disclosure in
#whole or in part without the express written permission of Splunk Inc. is prohibited.

import os, re, random, glob
from splunk.mining.DateParser import _validateDate, _validateTime

# set of values that imply attribute-value
# 'regex' : (attribute [, value]) -- if no value specified the value matched against will be the value
valuesMap = {
    'macintosh' : ['os'],
    'windows' : ['os'],
    'linux' : ['os'],
    'netscape' : ['browser'],
    'mozilla' : ['browser', 'firefox'],
    'firefox'  : ['browser'],
    '\Wie\W  ' : ['browser', 'ie'],
    'php' : ['language'],
    'java' : ['language'],
    'python' : ['language'],
    'c\+\+' : ['language'],
    '\wperl\w' : ['language', 'perl'],
    }

# common regex used
#start = '(?:^|[~`!@#$%&*()\.,?/;:\'\"]\s)\s*'
start = '(?:^|[~`!@#$%&*()\.,?/;:\'\"])\s*'
ending = '(?:$|[ ~`!@#$%&*()\.,?/;:\'\"])'

regexMap = {
    ## ips (63.215.194.99)
    'ip' : '(?P<ip>\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})',
    ## emailaddress
    'email' : '(?:^|\s|\()(?P<email>[\w\-][\w\-\.]+@[\w\-][\w\-\.]+[a-zA-Z]{1,4})',
    ## url
    'url' : '(?P<url>(ftp|http|https|gopher|mailto|news|nntp|telnet|wais|file|prospero|aim|webcal):(([A-Za-z0-9$_.+!*(),;/?:@&~=-])|%[A-Fa-f0-9]{2})+(#([a-zA-Z0-9][a-zA-Z0-9$_.+!*(),;/?:@&~=%-]*))?)',
    'java exception class' : '\sat (?P<class>[\w\.$_-]+)\(',
    ## attr=value (space or ; separated)
    ## attr:value (whitespace)
    #'nv1' : start + '(?P<attr>[a-z]\w+)=(?P<value>(?:\w?[@!:\.+-_]?\w)+)[\s,;.]',    #[^\s=;,>)\]}])*)(?!=)' + '(?:$|[ ~`!@#$%&*()\.,?/;\'\"])',
#    'nv1' : start + '(?P<attr>[a-z]\w+)=(?P<value>(?:\w+))[\s,;.]',    #[^\s=;,>)\]}])*)(?!=)' + '(?:$|[ ~`!@#$%&*()\.,?/;\'\"])',
    'nv2' : start + '(?P<attr>[a-z]\w+):(?P<value>(?:\w[^\s:;,>)\]}])+)(?!:)' + ending,
    #punct|start  words : number words punct|end
    'nv3a' : start + '(?P<attr>[a-z][\w_ -]+)\s*[:]\s*(?P<value>[0-9\.-]*[0-9]\s*[a-z][\w_ ]+)(?!:)', # // + ending, 
    'nv3b' : start + '(?P<attr>[a-z][\w_ -]+)\s*[=]\s*(?P<value>[0-9\.-]*[0-9]\s*[a-z][\w_ ]+)(?!=)', # // + ending, 
    #punct|start  words : number punct|end
    'nv4' : start + '(?P<attr>[a-z][\w_ -]+)\s*:\s*(?P<value>[0-9\.-]*[0-9])(?!:)' + ending,
    'nv5' : start + '(?P<attr>[a-z][\w_ -]+)\s*=\s*(?P<value>[0-9+:\.-]*[0-9])', #(?!=)' + ending,
    #to=<sdfsdfsdfds>
    'nv6a' : start + '(?P<attr>[a-z][\w_ -]+)=\<(?P<value>.+)\>', # + ending
    'nv6b' : start + '(?P<attr>[a-z][\w_ -]+)=\((?P<value>.+)\)', # + ending
    'nv6c' : start + '(?P<attr>[a-z][\w_ -]+)=\[(?P<value>.+)\]', # + ending
    # default.  word=word
    'nv7' : start + '(?P<attr>[a-z][\w_ -]+)=(?P<value>[\w_-]+)', # + ending
    }

#compile
compiledRegexMap = dict()
for thisType in regexMap.keys():
    compiledRegexMap[thisType] = re.compile(regexMap[thisType], re.I) # optimize.  recompiles each time

compiledValuesMap = dict()
for thisRegex in valuesMap.keys():
    compiledValuesMap[thisRegex] = re.compile(thisRegex, re.I)

def extractValues(text):
    result = dict()
    extractKeywords(result, text)
    # print("compiledRegexMap %s" % compiledRegexMap)
    for atype in compiledRegexMap.keys():
        expression = compiledRegexMap[atype] 
        matches = expression.findall(text)
        if matches:
            #print("Matches: %s %s" % (atype, matches))
            if len(matches[0]) == 2: ## attr/value if two values in regex
                for attr, val in matches:
                    #sys.stdout.write("%s = %s ," % (attr, val))
                    #result[attr] = val
                    addToMapSet(result, attr, val)
            else:
                for val in matches:
                    if type(val) != str:
                        val = val[0]
                    #print('MATCHES: %s VAL: %s' % (matches, val))
                    addToMapSet(result, atype, val)
    return result

def extractKeywords(result, text):
    for regex in valuesMap.keys():
        expression = compiledValuesMap[regex] 
        matches = expression.findall(text)
        if matches:
            values = valuesMap[regex]
            for val in matches:
                if len(values) == 1:
                    addToMapSet(result, values[0], val)
                else:
                    addToMapSet(result, values[0], values[1])

def addToMapSet(map, key, value):
    if key in map:
        s = map[key]
    else:
        s = set()
        map[key] = s

    doomed = list()
    for item in s:
        # if existing value is a substring of new value, mark it for deletion
        if item in value:
            doomed.append(item)
        # if value to add is a substring of existing value, ignore
        if value in item:
            return s
    for gone in doomed:
        s.remove(gone)
    s.add(value)
    return s



WATERMARK = "SPLUNK"
SPLUNK_ENTITY = "SPLUNK-COM"
WORD_REGEX = re.compile(r'[^a-zA-Z0-9]+')
WORD_SPLIT = re.compile(r'([^a-zA-Z0-9]+)')

def _generateReplacement(term, nameterms):
    replacement = ""
    if looksLikeWord(term):
        # get list of names with the same length as the term
        names = nameterms.get(len(term), None)
        if names != None:
            nameCount = len(names)
            if nameCount > 0:
                index = random.randint(1, nameCount)
                replacement = names[index-1]
                del names[index-1]
                return replacement
        
    for ch in term:
        if ch.isdigit():
            # return a new number that is randomly less than the given value, so that ip addresses, and codes
            # are not higher than the value given.  otherwise we wil get ip addresses like 554.785.455.545.
            # this assumes that if given a number, a number lower than it will be equally valid
            maxVal = int(ch)
            newch = str(random.randint(0,maxVal))
        elif ch.isalpha():
            if ch.islower():
                newch = chr(random.randint(97,122))
            else:
                newch = chr(random.randint(65,90))
        else:
            newch = ch
        replacement += newch
    return replacement

def allAlpha(token):
    for c in token:
        if not c.isalpha():
            return False
    return True

def lengthLists(terms):
    result = dict()
    for key in terms.keys():
        addToMapList(result, len(key), key)
    return result


def watermark(terms, replacements, mark):
    marklen = len(mark)
    for term in terms:
        if len(term) == marklen and looksLikeWord(term) and term in replacements:
            replacements[term] = mark
            break

def parentDirectory(filename):
    try:
        return filename[ : filename.rindex(os.sep)]
    except:
        return "."

def fileNameNoDirectory(filename):
    try:
        return filename[ filename.rindex(os.sep) + 1 :]
    except:
        return filename

############################# DATEFINDER

def findAllDatesAndTimes(text, timeInfoTuplet):
    global today, _MIN_YEAR, _MAX_YEAR

    timeExpressions = timeInfoTuplet[0]
    dateExpressions = timeInfoTuplet[1]
    matches = getAllMatches(text, dateExpressions, _validateDate)
    matches.extend(getAllMatches(text, timeExpressions, _validateTime))
    return matches


def getAllMatches(text, expressions, validator):
    index = -1
    matches = list()
    for expression in expressions:
        index += 1
        for match in expression.finditer(text):
            values = match.groupdict()
            isvalid = validator(values)
            if isvalid:
                #print("MATCHED: %s" % match.group())
                matches.append(match.span())
                # DOING ALL EXPRESSIONS FOR OPTIMIZATION DOES NOTHING.
                # # DC: WE HAVE A VALID MATCH, AND IT WASN'T THE FIRST EXPRESSION,
                # # MAKE THIS PATTERN THE FIRST ONE TRIED FROM NOW ON
                # if index > 0: # optimize search
                #     expressions.insert(0, expressions.pop(index))
    return matches

# return true if position is between any start-end in list of regions
def inRegions(position, regions):
    for region in regions:
        start = region[0]
        end = region[1]
        if start <= position <= end:
            return True
    return False

def compilePatterns(formats):
    compiledList = list()
    for format in formats:
        #print(str(format))
        compiledList.append(re.compile(format, re.I))
    return compiledList

def getTimeInfoTuplet(timestampconfilename):
    text = readText(timestampconfilename)
    text = text.replace('\\n', '\n').replace('\n\n', '\n')
    exec(text)
    compiledTimePatterns = compilePatterns(timePatterns)
    compiledDatePatterns = compilePatterns(datePatterns)
    timeInfoTuplet = [compiledTimePatterns, compiledDatePatterns, minYear, maxYear]
    return timeInfoTuplet

############################# DATEFINDER
    
################################### BEGIN COPIED FROM DCUTILS.PY

def addToMapList(map, key, value):
    if key in map:
        l = map[key]
    else:
        l = list()
        map[key] = l
    safeAppend(l, value)
    return l
    

def fileWords(filename, lowercase):
    terms = dict()
    try:
        f = open(filename, 'r')
        count = 1
        while (True):
            line = f.readline()
            if (lowercase):
                line = line.lower()
            if len(line) == 0:
                break
            tokenize(line, False, terms)
            if count % 100000 == 0:
                print('\t%u processed...' % count)
            count += 1
        f.close()
    except Exception as e:
        print('*** Error reading file %s and getting terms: %s', (filename, e))
    return terms
        
        
def readText(filename):
    try:
        f = open(filename, 'r')
        text = f.read()
        f.close()
        return text
    except Exception as e:
        print('*** Error reading file %s: %s' % (filename, e))
        return ""

def writeText(filename, text):
    try:
        f = open(filename, 'w')
        f.write(text)
        f.close()
    except Exception as e:
        print('*** Error writing file %s: %s' % (filename, e))

MAX_SEGMENT = 1024

def findBreak(start, segSize, text):
    segEnd = start + segSize - 1
    if segEnd > len(text):
        return len(text)-1
    for end in range(segEnd, max(start+1, segEnd-100), -1):
        if not text[end].isalnum():
            return end
    # failed to find break by going back 100 chars.  give up and break at will.
    return segEnd

# returns maps of terms and phrases to their count
def tokenize(text, wordsOnlyP, vector = dict()):
    segCount = int((len(text) + MAX_SEGMENT-1) / MAX_SEGMENT)
    segStart = 0

    for seg in range(0, segCount):
        segEnd = findBreak(segStart, MAX_SEGMENT, text)
        segText = text[segStart:segEnd+1]
        tokens = WORD_REGEX.split(segText)
        for token in tokens:
            if len(token) == 0:
                continue
            if not wordsOnlyP or looksLikeWord(token):
                incCount(vector, token, 1)
        segStart = segEnd+1
    return vector


def looksLikeWord(token):
    upper = lower = 0
    for c in token:
        if not c.isalpha():
            return False
        if c.isupper():
            upper += 1
        else:
            lower += 1
    return len(token) > 2 and (upper == 0 or lower == 0 or upper == 1)

def incCount(map, val, count):
    if val in map:
        map[val] += count
    else:
        map[val] = count


def safeAppend(list, val):
    if val not in list:
        list.append(val)

################################### END COPIED FROM DCUTILS.PY
        
def suggestOtherPrivateTerms(scrubeefilename, privateTerms, publicTerms):
    import synonyms
    recommendedAlready = set()
    # for each private term
    for term in privateTerms:
        # find synonyms like it
        suggestions = synonyms.learnTerms(scrubeefilename, [term], 100, 100)
        if suggestions != None:
            keepers = set()
            # for each synonym
            for sug in suggestions:
                # if it's a public term, it's dangerous that it might be a private.
                # unpublic terms are not dangerous as they wil automatically be scrubbed
                # ...also check that we haven't already recommended it
                if sug in publicTerms and sug not in recommendedAlready and sug not in privateTerms:
                    keepers.add(sug) # keep it
                    recommendedAlready.add(sug)
                    
        if len(keepers) >= 1:
            prettyKeepers = ', '.join(keepers)
            print('You\'ve specified (%s) as a private term.  You might want to also consider:\n\t%s' % (term, prettyKeepers))


# returns terms that occur between min and max times.
def getBestTerms(terms, minCount=0, maxCount=99999999999):
    tokensAndCounts = terms.items()
    tokensAndCounts.sort( lambda x, y: y[1] - x[1] )
    result = list()
    for i in range(0, len(terms)):
        count = tokensAndCounts[i][1]
        if minCount <= count <= maxCount:
            result.append(tokensAndCounts[i][0])
    return result

def suggestTermsByFreq(terms, privateTerms, publicTerms):
    nonuniqueTerms = getBestTerms(terms, 2)
    privateresult = list()
    publicresult = list()
    for term in nonuniqueTerms:
        if looksLikeWord(term):
            lower = term.lower()
            if lower not in privateTerms and lower in publicTerms and lower not in privateresult:
                privateresult.append(lower)
            if lower not in publicTerms and lower not in privateTerms and lower not in publicresult:
                publicresult.append(lower)
    return privateresult, publicresult

def isInt(token):
    if len(token) > 0 and  token[0].isdigit():
        try:
            int(token)
            return True
        except:
            pass
    return False

def caseSame(caseSource, textSource):
    result = "";
    for i in range(0, len(caseSource)):
        casech = caseSource[i]
        textch = textSource[i]
        if casech.isupper():
            textch = textch.upper()
        elif casech.islower():
            textch = textch.lower()
        result += textch;
    return result;


def getNamedEntities(logfiles):
    print('Getting named entities')
    names = set()
    for logfile in logfiles:
        try:
            f = open(logfile, 'r')
            count = 1
            print('\tProcessing %s' % logfile)
            while (True):
                line = f.readline()
                if len(line) == 0:
                    break
                if count > 100000:
                    print('\tStopping named entity extractor after %u lines.' % count)
                    break
                if '=' in line: # condition speeds things up but potentially loses some namevalue pairs
                    nes = extractValues(line)
                    for n in nes.keys(): 
                        names.add(n)
                count += 1
            f.close()
        except Exception as e:
            print('*** Problem with named entity extraction on file: %s\nSkipping %s ...' % (e, logfile))
    return names

def scrub(logpath, publictermsfilename, privatefilename, nametermsfilename, dictionaryfilename, timestampconfigfilename, corporateEntity):

    try:
        
        replacements = dict()
        # load private terms
        privateTerms = fileWords(privatefilename, True)
        # load default public terms
        publicTerms = fileWords(dictionaryfilename, True)
        # load user specific public terms
        userpublicTerms = fileWords(publictermsfilename, True)
        # load personal name terms
        nameTerms = lengthLists(fileWords(nametermsfilename, True))
        # add user public terms to default publicterms
        for t in userpublicTerms:
            publicTerms[t] = userpublicTerms[t]

        logfiles = glob.glob(logpath)
        if len(logfiles) == 0:
            print('Unable to find any files with specification %s' % logpath)
            return -1
        print('Processing files: %s' % logfiles)

        namedEntities = getNamedEntities(logfiles)
        print('Adding named entities to list of public terms: %s' % namedEntities)
        # add named entities to default publicterms
        for t in namedEntities:
            publicTerms[t] = 10000

        
        allterms = dict()
        # FOR EACH FILE TO PROCESS BUILD UP REPLACEMENT MAPPING
        for logfile in logfiles:
            print('\tProcessing %s for terms.' % logfile)
            terms = fileWords(logfile, False)
            if terms == None:
                continue
            #text = readText(logfile)
            #terms = tokenize(text, False)
            #wordterms = tokenize(text, True)
            print('\tCalculating replacements for %u terms.' % len(terms))
            for term in terms:
                # add term and count to allterms
                incCount(allterms, term, terms[term])
                
                lower = term.lower()
                # if we haven't already made a replacement for this term and it's a private term or not a public term
                if lower not in replacements and (lower in privateTerms or lower not in publicTerms): 
                    replacements[lower] = _generateReplacement(term, nameTerms) # make a replacement term

        if corporateEntity != None:
            corporateLower = corporateEntity.lower()
            publicTerms[corporateLower] = 10000
            publicTerms[WATERMARK] = 10000
            if corporateLower in replacements:
                del replacements[corporateLower]

        watermark(allterms, replacements, WATERMARK)
        timeInfoTuplet = getTimeInfoTuplet(timestampconfigfilename)
        
        directory = parentDirectory(logpath)
        mappingfilename = directory + os.sep + 'INFO-mapping.txt'
        replacetext = "Replacement Mappings\n--------------------\n"
        for item in replacements.items():
            replacetext += item[0] + " --> " + item[1] + "\n"
        writeText(mappingfilename, replacetext)
        print('===================================================')
        print('Wrote dictionary scrubbed terms with replacements to \"' + mappingfilename + '\"')
    
        #print('===================================================')
        #suggestOtherPrivateTerms(scrubeefilename, privateTerms, publicTerms)
        privateSuggestions, publicSuggestions = suggestTermsByFreq(allterms, privateTerms, publicTerms)
        suggestionsfilename = directory + os.sep + 'INFO-suggestions.txt'
        suggestText = "Terms to consider making private (currently not scrubbed):\n\n" + str(privateSuggestions) + "\n\n\nTerms to consider making public (currently scrubbed):\n\n" + str(publicSuggestions) + "\n"
        writeText(suggestionsfilename, str(suggestText))
        print('Wrote suggestions for dictionary to \"' + suggestionsfilename + '\"')
        print('===================================================')
    
        for logfile in logfiles:
            anonfilename = directory + os.sep + "ANON-" + fileNameNoDirectory(logfile)
            print("Writing out %s" % anonfilename)
            count = 1
            try:
                fout = open(anonfilename, 'w')
                fin = open(logfile, 'r')
                while (True):
                    if count % 100000 == 0:
                        print('\t%u processed...' % count)
                    line = fin.readline()
                    if len(line) == 0:
                        break
                    line = line[0:len(line)-1]
    
                    regions = findAllDatesAndTimes(line, timeInfoTuplet)
                    position = 0
                    tokens = re.split(WORD_SPLIT, line)
                    newtokens = list()
                    for token in tokens:
                        lower = token.lower()
                        inDateRegion = inRegions(position, regions) 
                        # IF WE'RE IN A DATE REGION AND IT'S A NUMBER OF PUBLIC WORD, KEEP IT
                        # WE NEED TO DOUBLE CHECK FOR NUMBERS OF PUBLIC TERMS BECAUSE DATE REGIONS SOMETIMES
                        # HAVE EXTRAINEOUS TEXT IF THE REGEX MATCHES CONTAINS A NOISE TERM OR END OF EXPRESSION MATCH
                        if inDateRegion and (isInt(token) or (lower in publicTerms and lower not in privateTerms)):
                            #print('leaving: %s alone as it's part of a date.' % token)
                            newtoken = token
                        else:
                            newtoken = replacements.get(lower, token)
                            newtoken = caseSame(token, newtoken)
                            
                        position += len(token)
                        newtokens.append(newtoken)
                    newline = ''.join(newtokens)
                    if corporateEntity != None:
                        newline = newline.replace(corporateEntity, SPLUNK_ENTITY)
        
                    fout.write(newline)
                    fout.write('\n')
                    count += 1
                fin.close()
                fout.close()
            except Exception as e:
                print('*** Scrubber error: %s\nSkipping %s ...' % (e, logfile))
                #import traceback
                #traceback.print_exc()
        print("Done.")
    except Exception as e:
        print('***Scrubber error: %s' % e)
        import traceback
        traceback.print_exc()

__source            = "-source"
__publicTerms       = "-public-terms"
__privateTerms      = "-private-terms" 
__nameTerms         = "-name-terms"
__timestampConfig   = "-timestamp-config"
__dictionary        = "-dictionary"
__corpEntity        = "-corp-entity"
__fileSpecification = "<file specification>"


if __name__ == '__main__':
    import sys
    argc = len(sys.argv)
    argv = sys.argv

    scrubeefilename = None
    from splunk.clilib.bundle_paths import make_splunkhome_path
    root = make_splunkhome_path(['etc', 'anonymizer'])
    publictermsfilename     = os.path.join(root, "public-terms.txt")
    privatetermsfilename    = os.path.join(root, "private-terms.txt")
    nametermsfilename       = os.path.join(root, "names.txt")
    dictionaryfilename      = os.path.join(root, "dictionary.txt")
    timestampconfigfilename = os.path.join(root, 'anonymizer-time.ini')  
    corporateEntity = None

    i = 1
    while i < argc-1:
        if argv[i] == __source:
            scrubeefilename = argv[i+1]
        elif argv[i] == __publicTerms:
            publictermsfilename = argv[i+1]
        elif argv[i] == __privateTerms:
            privatetermsfilename = argv[i+1]
        elif argv[i] == __nameTerms:
            nametermsfilename = argv[i+1]
        elif argv[i] == __dictionary:
            dictionaryfilename = argv[i+1]
        elif argv[i] == __timestampConfig:
            timestampconfigfilename = argv[i+1]
        elif argv[i] == __corpEntity:
            corporateEntity = argv[i+1]
        else:
            i = i - 1

        i = i + 2
        

    if scrubeefilename:
        scrub(scrubeefilename, publictermsfilename, privatetermsfilename, nametermsfilename, dictionaryfilename, timestampconfigfilename, corporateEntity)
    else:
        print('Simple Usage \n')
        print('\tsplunk anonymize file -source <filespecification> [additional arguments]\n')
        print('\t...for example...\n')
        print('\tsplunk anonymize file -source \'/home/myname/logs/*.log\'\n')

        print('\nAdditional optional arguments:')
        print('\t%s %s' % (__publicTerms, __fileSpecification))
        print('\t%s %s' % (__privateTerms, __fileSpecification))
        print('\t%s %s' % (__nameTerms, __fileSpecification))
        print('\t%s %s' % (__timestampConfig, __fileSpecification))
        print('\t%s %s' % (__dictionary, __fileSpecification))
        print('\t%s %s' % (__corpEntity, "<string>"))
