#   Version 4.0
import re,sys,time, splunk.Intersplunk

def getDSTFlag(timestamp):
    tt = time.localtime(timestamp)
    return tt.tm_isdst > 0

def getDSTOffset():
   offset = (60 * 60)
   #override standard DST offset to 30 min for Lord Howe Island timezone
   if time.tzname[0] == "+1030" and time.tzname[1] == "+11":
       offset = (60 * 60) / 2
   return offset

def doDSTAdjustmentIfNeeded(start, end):
   newstart = start
   newend = end

   start_isdst = getDSTFlag(start)
   end_isdst = getDSTFlag(end)

   if start_isdst and not end_isdst:
       dst_offset = getDSTOffset()
       if not getDSTFlag(end-dst_offset):
           newstart += dst_offset
           newend += dst_offset
   elif not start_isdst and end_isdst:
       dst_offset = getDSTOffset()
       if getDSTFlag(end-dst_offset):
           newstart -= dst_offset
           newend -= dst_offset

   return newstart,newend

def midnightToday():
    now = time.localtime()
    midnightlastnight = time.mktime((now[0], now[1], now[2], 0, 0, 0, 0, 0, -1))
    return midnightlastnight

# "5/4/9999:34:33:33"
def getTime(val):
    if not val:
        return None
    match = re.findall("(\d{1,2})/(\d{1,2})(?:/(\d{2,4}))?(?::(\d{1,2}):(\d{2}):(\d{2}))?", val)
    # if timestamp.  default year to current year and time to midnight
    if len(match) > 0:
        now = time.localtime()
        vals = match[0]
        month = int(vals[0])
        day   = int(vals[1])
        if len(vals[2]) > 0:
            year = int(vals[2])
            if year < 100:
                year += 2000
        else:
            year = now[0]
        if len(vals[3]) > 0:
            hour   = int(vals[3])
            minute = int(vals[4])
            sec    = int(vals[5])
        else:
            hour = 0
            minute = sec = 0
        return time.mktime((year, month, day, hour, minute, sec, 0, 0, -1)) 
    else:
        now = int(time.time())
        daysago = int(val)
        midnightlastnight = midnightToday()
        midnightago = midnightlastnight + (24*60*60 * daysago)
        if getDSTFlag(now) and not getDSTFlag(midnightago):
            midnightago += getDSTOffset()
        elif getDSTFlag(midnightago) and not getDSTFlag(now):
            midnightago -= getDSTOffset()
        return midnightago
    return None

def getIncrement(val):
    if not val:
        return None
    match = re.findall("(\d+)([smhd])", val)
    # if timestamp.  default year to current year and time to midnight
    if len(match) > 0:
        val = int(match[0][0])
        units = match[0][1]
        if units == 'm':
            val *= 60
        elif units == 'h':
            val *= 60 * 60
        elif units == 'd':
            val *= 24 * 60 * 60
        return val
    return None

def addResultSample(results, start, end):
    result = {}
    result['starttime'] = str(start)
    result['endtime']   = str(end)

    start_tmz = time.tzname[0]
    end_tmz = time.tzname[0]

    if time.tzname[0] != time.tzname[1]:
        if getDSTFlag(start):
            start_tmz = time.tzname[1]
        if getDSTFlag(end):
            end_tmz = time.tzname[1]

    if -1 != start_tmz.find("+") or -1 != start_tmz.find("-"):
        start_tmz = "GMT" + start_tmz

    if -1 != end_tmz.find("+") or -1 != end_tmz.find("-"):
        end_tmz = "GMT" + end_tmz

    starthuman_str = time.asctime(time.localtime(start)) + ' ' + start_tmz
    endhuman_str = time.asctime(time.localtime(end)) + ' ' + end_tmz
    result['starthuman'] = starthuman_str
    result['endhuman'] = endhuman_str

    results.append(result)
    return

def generateTimestamps(results, settings):

    try:
        keywords, argvals = splunk.Intersplunk.getKeywordsAndOptions()
        startagostr        = argvals.get("start", None)
        endagostr          = argvals.get("end", None)
        incrementstr       = argvals.get("increment", None)

        starttime = getTime(startagostr)
        endtime   = getTime(endagostr)
        increment = getIncrement(incrementstr)

        if not endtime:
            endtime = midnightToday()
        if not increment:
            increment = 24 * 60 * 60 # 1 day
        if not starttime:
            return splunk.Intersplunk.generateErrorResults("generatetimestamps requires start=mm/dd/yyyy:hh:mm:ss and optional takes 'end' and 'increment' values.")

        results = []

        start = int(starttime)
        end = int(starttime)
        while start < int(endtime):
            end = start + increment - 1 # 1 sec less than next range

            #check for any possible DST adjestment
            newstart,newend = doDSTAdjustmentIfNeeded(start, end)

            #adjust the end timestamp as per DST
            if end != newend:
                end = newend

            #generate a result sample
            addResultSample(results, start, end)

            #now adjust the start timestamp as per DST
            if start != newstart:
                start = newstart

            start += increment

    except Exception as e:
        import traceback
        stack =  traceback.format_exc()
        results = splunk.Intersplunk.generateErrorResults(str(e) + ". Traceback: " + str(stack))
    return results
        

results, dummyresults, settings = splunk.Intersplunk.getOrganizedResults()
results = generateTimestamps(results, settings)
splunk.Intersplunk.outputResults(results)
