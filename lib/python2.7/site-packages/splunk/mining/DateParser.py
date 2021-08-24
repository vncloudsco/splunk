from __future__ import print_function
# This work contains trade
#secrets and confidential material of Splunk Inc., and its use or disclosure in
#whole or in part without the express written permission of Splunk Inc. is prohibited.

from builtins import range
import re, time

_debug = False

HOUR_SECS = 60 * 60
_MIN_YEAR = 2000
_MAX_YEAR = 2010
now = time.localtime()
nowYear = now[0]
nowMonth = now[1]
nowDate = now[2]
oneMinute = 1/60.0
oneHour = 1

# FOR FAST DATETIME PARSING, ASSING DIFF BETWEEN LAST TIME AND THIS
# TIME, IF LESS THAN 5 MINUTES FORWARD, ARE THE SAME DATE
MAX_MINUTE_DIFF_FOR_FAST_ASSUMPTIONS = 5.0

litmonthtable = { 'jan':1, 'feb':2, 'mar':3, 'apr':4, 'may':5,
                  'jun':6, 'jul':7, 'aug':8, 'sep':9, 'oct':10, 'nov':11, 'dec':12 }
# time zone parsing
isozone = ('(?P<zone>[+-]\d\d:?(?:\d\d)?|Z)')
zoneoffset = '(?:(?P<zonesign>[+-])?(?P<hours>\d\d?):?(?P<minutes>\d\d)?)'
zoneoffsetRE = re.compile(zoneoffset)
# The offset given here represent the difference between UTC and the given time zone.
zonetable = { 'UT':0, 'UTC':0, 'GMT':0, 'CET':1, 'CEST':2, 'CETDST':2,
              'MET':1, 'MEST':2, 'METDST':2, 'MEZ':1, 'MESZ':2,
              'EET':2, 'EEST':3, 'EETDST':3, 'WET':0, 'WEST':1,
              'WETDST':1, 'MSK':3, 'MSD':4, 'IST':5.5, 'JST':9,
              'KST':9, 'HKT':8, 'AST':-4, 'ADT':-3, 'EST':-5,
              'EDT':-4, 'CST':-6, 'CDT':-5, 'MST':-7, 'MDT':-6,
              'PST':-8, 'PDT':-7, 'CAST':9.5, 'CADT':10.5, 'EAST':10,
              'EADT':11, 'WAST':8, 'WADT':9, 'D': 4, 'E': 5, 'F': 6,
              'G': 7, 'H': 8, 'I': 9, 'K': 10, 'L': 11, 'M': 12,
              'N':-1, 'O':-2, 'P':-3, 'Q':-4, 'R':-5, 'S':-6, 'T':-7,
              'U':-8, 'V':-9, 'W':-10, 'X':-11, 'Y':-12 }

def utc_offset(zone):
    """ utc_offset(zonestring) Return the UTC time zone offset in
        hours zone must be string and can either be given as +-HH:MM,
        +-HHMM, +-HH numeric offset or as time zone
        abbreviation. Daylight saving time must be encoded into the
        zone offset.  Timezone abbreviations are treated
        case-insensitive.  """
    
    if not zone:
        return 0
    uzone = zone.upper()
    # IF UNKNONW TIMEZONE
    if uzone not in zonetable:
        # LOOK FOR NUMBER OFFSET
        offset = zoneoffsetRE.match(zone)
        if not offset: # NO OFFSET, USE CURRENT TIMEZONE IF NONE
            uzone = time.tzname[0]  
        else: # USE OFFSET
            zonesign, hours, minutes = offset.groups()
            offset = int(hours or 0) * 60 + int(minutes or 0)
            if zonesign == '-':
                offset = -offset
            return offset*oneMinute

    # machine, e.g. windows, is giving us an unknown timezone.  fallback to utc
    if uzone not in zonetable:
        uzone = 'UTC'
    return zonetable[uzone]*oneHour

def secondsOffSetInCurrentTimeZone():
    uzone = time.tzname[0]
    hoursOff = zonetable[uzone]
    if time.daylight:
        hoursOff -= 1
    return hoursOff * HOUR_SECS
         
def parseDate(text, currenttime, lastDate, timeInfoTuplet):
    timetuple = None
    try:
        timetuple = FastDateTimeFromString(text, timeInfoTuplet, lastDate)
        if timetuple != None and compareTimeTuple(timetuple, currenttime, 3) > 0: ## see if later year OR month
           timetuple = (timetuple[0]-1, timetuple[1], timetuple[2], timetuple[3], timetuple[4], timetuple[5], timetuple[6], timetuple[7], timetuple[8])
        # the year is not between the minYear and maxYear (inclusive)
        if timetuple != None and not (timeInfoTuplet[2] <= timetuple[0] <= timeInfoTuplet[3]):
            timetuple = None
       
    except Exception as e:
        print('Exception cause: %s' % e)
        raise Exception(e)
    return timetuple

def compareTimeTuple(dateTuple1, dateTuple2, accuracy=6):
   if dateTuple1 == None or dateTuple2 == None:
      if dateTuple1 == None and dateTuple2 == None:
         return 0
      return -1
   # loop through year, month, day, hour, minute, seconds to see if the first tuple is larger
   for i in range(0, accuracy):
      diff = int(dateTuple1[i]) - int(dateTuple2[i])
      if diff > 0:
         return 1
      elif diff < 0:
         return -1
   return 0
   
def hasTime(text, timeInfoTuplet):
    return getFastTime(text, timeInfoTuplet) != None

def getFastTime(text, timeInfoTuplet):
    expressions = timeInfoTuplet[0]
    for expression in expressions:
        match = expression.search(text)
        if match:
            return match
    return None


def fixOffset(timetuple, offset):
    if offset != None:
        hour = timetuple[3]
        #if time.daylight:
        #    offset += 1
        newHour = hour - offset 
        # if we don't have a simple integer offset that doesn't change the day, minutes, etc. then call the date functions
        if offset != int(offset) or newHour < 0 or newHour >= 24:
            result =  time.localtime(time.mktime(timetuple) - ((offset) * HOUR_SECS))
            #print('BEFORE FIXING: %s %s AFTER: %s' % (timetuple, offset, result))
            return result
        # otherwise just update the hour field
        else:
            return (timetuple[0], timetuple[1], timetuple[2], newHour, timetuple[4], timetuple[5], timetuple[6], timetuple[7], timetuple[8])

def FastDateTimeFromString(text, timeInfoTuplet, lastDateTime):
    if lastDateTime != None:
        match = getFastTime(text, timeInfoTuplet)
        if match == None:
            return None
        timevalues = match.groupdict()
        timeExtractions = _validateTime(timevalues)
        if timeExtractions:
            hour   = timeExtractions[0]
            minute = timeExtractions[1]
            second = timeExtractions[2]
            offset = timeExtractions[3]
            dayMin = 60 * hour + minute
            lastDayMin = 60 * lastDateTime[3] + lastDateTime[4]
            # if this time is after the last time and not more than a few minutes after it, we can assume it's the date and
            # not bother with the expensive date parsing
            if dayMin >= lastDayMin and dayMin - lastDayMin <= MAX_MINUTE_DIFF_FOR_FAST_ASSUMPTIONS:
                try:
                    if lastDateTime == None:
                        day   = nowDate
                        month = nowMonth
                        year  = nowYear
                    else:
                        year  = lastDateTime[0]
                        month = lastDateTime[1]
                        day   = lastDateTime[2]
                    result = (year, month, day, hour, minute, second, 0, 0, 0)
                    if offset != None:
                        result = fixOffset(result, offset)
                    return result
                    # return time.mktime((year, month, day, hour, minute, second, 0, 0, 0))
                    #return DateTime.DateTime(year,month,day,hour,minute,second) - offset
                except Exception as why:
                    if _debug:        
                        print(why)
                    raise Exception('Failed to parse "%s": %s' % (text, why))

    # no lastdatetime or time is off by enough that we have to check the date
    return DateTimeFromString(text, timeInfoTuplet)

    
def DateTimeFromString(text, timeInfoTuplet):
    global _MIN_YEAR, _MAX_YEAR
    timeExpressions = timeInfoTuplet[0]
    dateExpressions = timeInfoTuplet[1]
    _MIN_YEAR       = timeInfoTuplet[2]
    _MAX_YEAR       = timeInfoTuplet[3]

    timevalues = getMatch(text, timeExpressions, _validateTime)
    if not timevalues:
        return None
    datevalues = getMatch(text, dateExpressions, _validateDate)
    if not datevalues:
        day   = nowDate
        month = nowMonth
        year  = nowYear
    else:
        day   = datevalues[0]
        month = datevalues[1]
        year  = datevalues[2]
    hour   = timevalues[0]
    minute = timevalues[1]
    second = timevalues[2]
    offset = timevalues[3]
    try:
        result = (year, month, day, hour, minute, second, 0, 0, 0)
        if offset != None:
            result = fixOffset(result, offset)
        return result
        #return time.mktime((year, month, day, hour, minute, second, 0, 0, 0))        
        #return DateTime.DateTime(year,month,day,hour,minute,second) - offset
    except Exception as why:
        if _debug:        
            print(why)
        raise Exception('Failed to parse "%s": %s' % (text, why))


def getMatch(text, expressions, validator):
    index = -1
    for expression in expressions:
        index += 1
        match = expression.search(text)
        if match:
            values = match.groupdict()
            extractions = validator(values)
            if extractions:
                # DC: WE HAVE A VALID MATCH, AND IT WASN'T THE FIRST EXPRESSION,
                # MAKE THIS PATTERN THE FIRST ONE TRIED FROM NOW ON
                if index > 0:
                    expressions.insert(0, expressions.pop(index))
                return extractions
    return None

    
#litday,day,litmonth,month,year,epoch = match.groups()
# =>
# returns day, month, year
def _validateDate(values):
    error = None
    year = nowYear
    month = 1
    day = 1
    if _debug:
        print(str(values))

    yvalue = values.get('year')
    dvalue = values.get('day')
    mvalue = values.get('month')
    lvalue = values.get('litmonth')
    
    if yvalue:
        year = yvalue
        if len(year) == 2:
            year = add_century(int(year))
        else:
            year = int(year)
        if not (_MIN_YEAR <= int(year) <= _MAX_YEAR):
            error = "bad year: " + str(yvalue)
    if dvalue:
        day = dvalue
        day = int(day)
        if day < 1 or day > 31:
            error = "bad day: " + str(dvalue)
    if mvalue:
        month = mvalue
        month = int(month)
        if month > 12 or month == 0:
            error = "bad month: " + str(mvalue)
    if lvalue:
        litmonth = lvalue.lower()
        try:
            month = litmonthtable[litmonth]
        except KeyError:
            raise ValueError('wrong month name: "%s"' % litmonth)

    if error:
        if _debug:
            print("Error: " + error)
        return None

    if day == None:
        day = nowDate
    if month == None:
        month = nowMonth
    if year == None:
        year = nowYear
    return [day, month, year]


# text,hour,minute,second,offset,style]
# =>
# returns hour, minute, second, offset
def _validateTime(values):

    error = ""
    hour, minute, second, ampm, offset = 0, 0, 0, 'a', 0

    zvalue = values.get('zone')
    hvalue = values.get('hour')
    mvalue = values.get('minute')
    svalue = values.get('second')
    ampmvalue = values.get('ampm')

    if zvalue:
        zone = zvalue
        # Convert to UTC offset
        offset = utc_offset(zone)
    else:
        # USE CURRENT TIMEZONE
        offset = utc_offset(time.tzname[0])

    if hvalue:
        hour = int(hvalue)
        if ampmvalue:
            ampm = ampmvalue
            if ampm[0] in ('p', 'P'):
                hour = hour + 12
        if hour < 0 or hour > 23:
            error = "bad hour:", str(hour)
    if mvalue:
        minute = int(mvalue)
        if minute < 0 or minute > 59:
            error = "bad minute:", str(minute)
    if svalue:
        second = int(float(svalue) + 0.5)
        if second < 0 or second > 59:
            error = "bad second:", str(second)

    if error:
        if _debug:
            print("Error: " + error)
        return None
    return [hour, minute, second, offset]

def add_century(year):
    if year > 99:
        return year
    current_year = nowYear
    current_century = (current_year // 100) * 100
    year = year + current_century
    diff = year - current_year
    if diff >= -70 and diff <= 30:
        return year
    elif diff < -70:
        return year + 100
    else:
        return year - 100
