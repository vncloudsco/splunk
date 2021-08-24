import os
import re
import json
import splunk.entity as en
#pylint: disable=F0401
import win32api, win32con, pywintypes
import logging as logger
import re


"""
Encodes a currentName into JSON, depending on whether currentName is in
selectedItemNames.  It applies normalizationFunc to every encoded item.

Example output: "{"Tcpip_ICMPv6": 0}"
"""
def createJsonEncodedItem(currentName, selectedItemNames, normalizationFunc = lambda x: x):
    d = None
    l = [normalizationFunc(i).lower() for i in selectedItemNames]
    if normalizationFunc(currentName).lower() in l:
        d = {currentName: 1}
    else:
        d = {currentName: 0}
    return json.JSONEncoder().encode(d)

"""
@param procInputs - list of input processors endpoint paths to be reloaded
@param scriptInputs - list of scripted input endpoint paths to be reloaded

Example endpoint path: admin/win-eventlogs/_reload
"""
def reloadConf(self, procInputs=[], scriptInputs=[]):
    for procInput in procInputs:
        en.getEntities( procInput,
              sessionKey = self.getSessionKey() )

    #TODO: Handle restart of individual cripted
    for scriptInput in scriptInputs:
        en.getEntities( scriptInput,
              sessionKey = self.getSessionKey() )

"""
Given a "disabled" config value as a string, returns True or False
"""
def isDisabled(s):
    s = str(s)
    s = s.lower().strip()
    if s == "true" or s == "1" or s == "yes" or s == "":
        return True
    return False

"""
Returns a string of representing a value disabled config value.  Looks at
the existing value s, and tries to use the same convention.
"""
def setDisabled(s, disabled = 0):
    convTable = (("0", "1"), ("false", "true"), ("no", "yes"))
    ls = s.lower().strip()
    oposite = (disabled + 1) % 2

    for conv in convTable:
        if conv[disabled] == ls:
            # already properly set: just return it in the prefered case
            return ls
        elif conv[oposite] == ls:
            # set to oposite value: return the mathing oposite
            return conv[disabled]

    return convTable[0][disabled]

"""
Deletes a registry a key and all of the subkeys under it in local machine
registry hive, under Software.  Currently used by the cli to delete splunk
registry keys when the user does "clean all"
"""
def DeleteSplunkRegistryKeys(splunkKey):
    hKeyRoot = win32con.HKEY_LOCAL_MACHINE

    RegDeleteKeyRecurse(hKeyRoot, os.path.join("Software", splunkKey))

"""
Deletes a registry key and all the subkeys under it
"""
def RegDeleteKeyRecurse(hKeyRoot, hSubKey):
    hKey = 0
    enumKeys = ""
    rootKeyStr = "HKEY_LOCAL_MACHINE"

    try:
        win32api.RegDeleteKey(hKeyRoot, hSubKey)
        logger.info("\tCleaning registry key %s\%s" % (rootKeyStr, hSubKey))
        return 0
    except pywintypes.error as e:
        pass

    try:
        hKey = win32api.RegOpenKeyEx(hKeyRoot, hSubKey, 0, win32con.KEY_READ)
    except pywintypes.error as e:
        logger.debug("Could not open registry key=%s\%s: %s" % (rootKeyStr, hSubKey, e[2]))
        return 1

    try:
        enumKeys = win32api.RegEnumKeyEx(hKey);
    except pywintypes.error as e:
        logger.debug("Could not enum key=%s\%s: %s" % (rootKeyStr, hSubKey, str(e[2])))
        return 1

    for enumKey in enumKeys:
        RegDeleteKeyRecurse(hKeyRoot, os.path.join(hSubKey, enumKey[0]))

    try:
        logger.info("\tCleaning registry key %s\%s" % (rootKeyStr, hSubKey))
        win32api.RegDeleteKey(hKeyRoot, hSubKey)
    except pywintypes.error as e:
        logger.error("Failed to delete key='%s\%s': %s" % (rootKeyStr, hSubKey, str(e[2])))

    win32api.RegCloseKey(hKey)
