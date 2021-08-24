from __future__ import absolute_import
from __future__ import print_function
# This work contains trade
#secrets and confidential material of Splunk Inc., and its use or disclosure in
#whole or in part without the express written permission of Splunk Inc. is prohibited.

# runs shell that allows user to teach the system to extract fields interactively

import sys
import splunk.mining.dcutils as dcutils
from builtins import range
import getpass

INPUT_PROMPT = ">"

def prompt(msg, allowEmpty=True):
    text = "Enter " +  msg + " " + INPUT_PROMPT
    text = text.rjust(60)        
    while True:
        sys.stdout.write(text)
        value = input().strip()
        if allowEmpty or len(value) > 0:
            return value
        print("Empty " + msg + " is not allowed.")

def promptWithDefault(msg, defaultval):
    text = "Enter " + msg + " (defaults to [" + defaultval + "]) " + INPUT_PROMPT
    text = text.rjust(60)
    sys.stdout.write(text)
    value = input().strip()
    if len(value) == 0:
        value = defaultval
    return value
    
def promptPassWithDefault(msg, defaultval):
    text = "Enter " + msg + " (defaults to [" + defaultval + "]) " + INPUT_PROMPT
    text = text.rjust(60)
    value = getpass.getpass(text + " ")
    if len(value) == 0:
        value = defaultval
    return value
 
def printQuestion(question):
    border = "\n" + "-"*len(question) #+ "\n"
    print(border + "\n" + question.capitalize() + border)

def addListItems(title, itemname, listvalues, validator=None):
    printQuestion(title)
    if len(listvalues) > 0:
        print("\tItems will be added to the list of current values: %s" % listvalues)
    print("\n\tEnter new values on separate lines. Prefix values with '--' to remove an existing value.\n\tEnter a blank line when done.  Enter '??' for more options.")
    print("")
    while True:
        value = prompt(itemname)
        if len(value) == 0:
            print("")
            return
        if value == '??':
            print("\tTo remove a current value, prefix it with '--'.")
            print("\tTo remove all values, enter '[]'.")
            print("\tTo show current values, enter '='.")
        elif value == '[]':
            for i in range(0, len(listvalues)):
                listvalues.pop()
            print("Removed all values.")
        elif value == '=':
            print("Current values: %s" % listvalues)
        elif value.startswith("--"):
            value = value[2:]
            if value in listvalues:
                listvalues.remove(value)
            else:
                print("Could not find '" + value + "' to remove from current values.")
        else:
            if validator == None or validator(*[value]):
                listvalues.append(value)
            else:
                print("Ignoring bad " + itemname)

def validateElements(listname, listvalues):
    if len(listvalues) == 0:
        return listvalues
    print("Here are the current " + listname + ":" + str(listvalues))
    action = askMultipleChoiceQuestion("How would you like to approve this list?", ["some", "all", "none"], "some")
    if action == "all":
        return listvalues
    elif action == "none":
        return []
    else:
        doomed = []
        for item in listvalues:
            itemaction = askYesNoQuestion("Keep " + str(item) + "?", allowCancel=True)
            if itemaction == None:
                break
            elif itemaction == False:
                doomed.append(item)
        for item in doomed:
            listvalues.remove(item)
        if len(doomed) > 0:
            print("Reduced list:" + str(listvalues))
    return listvalues
    
def askYesNoQuestion(question, allowCancel=False):
    promptstr = "[Y]es or [N]o"
    if allowCancel:
        promptstr = "[Y]es, [N]o, or [C]ancel"
    printQuestion(question)
    while True:
        answer = prompt(promptstr)
        if len(answer) > 0:
            ch = answer[0].lower()
            if ch == 'y':
                return True
            if ch  == 'n':
                return False
            if ch == 'c':
                return None

def expandUniquePrefix(givenAnswer, answers):
    match = None
    lowerGivenAnswer = givenAnswer.lower()
    for answer in answers:
        # if prefix match
        if answer.startswith(lowerGivenAnswer):
            if match != None: # already had a prefix match, not unique!
                return givenAnswer # return original answer
            match = answer
    return match

def askMultipleChoiceQuestion(question, answers, defaultanswer=None):
    printQuestion(question)
    allowNoAnswer = (defaultanswer != None)
    capAnswers = ""
    for ans in answers:
        ans = ans.capitalize()
        if defaultanswer != None and ans.lower()==defaultanswer.lower():
            ans = "[" + ans + "]"
        if len(capAnswers) > 0:
            capAnswers += "/"
        capAnswers += ans
    while True:
        #capanswers = [x.capitalize() for x in answers]
        #choicestring = "/".join(capanswers)
        answer = prompt("choice: " + capAnswers, True).lower()
        if allowNoAnswer and len(answer) == 0:
            return defaultanswer
        else:
            answer = expandUniquePrefix(answer, answers)
            if answer in answers:
                return answer
            print("\tInvalid choice. Please enter one of the choices.")


def sameFileTypes(filenames):
    import splunk.mining.positionalsynonyms as positionalsynonyms
    oldtype = None
    bad = []
    for filename in filenames:
        thisType = positionalsynonyms.getFileType(filename)
        if thisType == "unknown":
            bad.append(filename)
        if oldtype != None and oldtype != thisType:
            print("Different file types: %s != %s" % (oldtype, thisType))
            return False
        oldtype = thisType
    for bf in bad:
        print("Ignoring bad filename: '" + str(bf) + "'")
        filenames.remove(bf)
    return True

def printLineSamplings(filenames, maxPerFile = 10, searchKey = None):
    import random
    for fn in filenames:
        lines = dcutils.loadLines(fn)
        print("\nSample lines from %s\n------------------------------------------------------------------------" % fn)
        count = 1
        for line in lines:
            line = line.strip()
            if random.randint(1, 10) == 1 and len(line) > 20 and (searchKey == None or searchKey in line):
                print("\t" + line)
                count += 1
                if count > maxPerFile:
                    break
    print('')

def looseFileExists(filename):
    return dcutils.fileExists(filename.strip())

def getFileNames():
    while True:
        filenames = []
        addListItems("Please specify the full names of the files from which to learn.", "filename", filenames, looseFileExists)
        filenames = [filename.strip() for filename in filenames]
        if len(filenames) == 0:
            print("No files specified.")
        else:
            return filenames
