from __future__ import print_function
from __future__ import division
from past.utils import old_div

from builtins import map
from builtins import range
from builtins import zip
from builtins import object

def divide (a, b):
    if b == 0:
        return 0.0;
    return 100.0*(old_div(a,b))

def subtract (a, b):
    return a - b

def tuplify (op):
    """ Convert the function op into a function that acts on tuples """
    return lambda x: op(*x)

# data: a list, mean: a float, k: an int
def autocovariance (data, mean, k):
    """ Compute the k lagged autocovariance of the given data whose mean is passed in"""
    cov = 0.0
    N = len(data)
    if N <= k: return cov
    for i in range(N-k):
        cov += (data[i]-mean)*(data[i+k]-mean)
    return old_div(cov,N)
    # return cov/(N-1) # it's standard pratice in statistics to divide by N-1 instead of N. Also, it's not N-k either (as might be expected).


# data: a list, n: an int
def correlogram (data, n=0):
    """ Compute the correlogram of the given data.
    The returned correlogram consists of autocorrelations of lag up to n only.
    If n isn't specified, the lag is taken up to len(data)-1. """
    N = len(data)
    mean = float(sum(data))/N
    if n == 0 or n >= N: n = N-1
    var = autocovariance(data, mean, 0)
    yield 1.0
    for i in range(1, n+1):
        if var == 0.: yield 0.
        else: yield old_div(autocovariance(data,mean,i),var)


#data: a list of float's
def findPeriod (data):
    cor = correlogram(data)
    prev_item = next(cor)
    curr_item = next(cor)
    # Go through cor and find the indices of all local peaks.
    # Find the smallest index that might be the period.
    # It's not necessarily the max peak, as the peak at the period may be slightly
    # smaller than the max peak. So we'll ignore the differences that are smaller than 0.01.
    peak_idx = 0
    peak_val = 0.0
    for i, next_item in enumerate(cor):
        if curr_item > prev_item and curr_item > next_item and curr_item > peak_val + 0.01:
            peak_val = curr_item
            peak_idx = i+1
        prev_item = curr_item
        curr_item = next_item
    if peak_val <= 0.01: return 0
    return peak_idx

    
class TS(object):
    """Time Series data structure"""

    def __init__ (self, n=0, val=0.0):
        self.startIdx = 0
        self.endIdx = 0
        self.data = [val]*n
        self.period = 0
        self.num_periods = 0

    @classmethod
    def fromlist (cls, datalist):
        """Initialize TS from a list"""
        cls = TS()
        cls.data = datalist
        cls.periodStart = 0
        cls.endIdx = len (datalist)
        return cls

    def __contains__ (self, x):
        return x in self.data

    def __iter__ (self):
        return self.data.__iter__()

    def __append__ (self, val):
        self.data.append (val)

    def __setitem__ (self, i, val):
        self.data[i] = val

    def __getitem__ (self, i):
        return self.data[i]

    def __len__ (self):
        return len(self.data)

    def dataLength (self):
        return self.data_length

    def setPeriod (self, period):
        self.period = period

    def setPeriodStart (self, periodStart):
        self.periodStart = periodStart
        self.first_full_period = 0
        if self.periodStart:
            self.first_full_period = 1

    def setStartIdx (self, startIdx):
        self.startIdx = startIdx

    def resize (self, n, val=0.0):
        self.data = [val]*n

    # Make sure this is called after setStartIdx() and setPeriodStart()  
    def setEndIdx (self, endIdx):
        self.endIdx = endIdx
        self.data_length = self.endIdx - self.startIdx
        if self.period > 0:
            d = self.data_length + self.periodStart
            if d%self.period == 0:
                self.num_periods = int(old_div(d,self.period))
            else:
                self.num_periods = int(old_div(d,self.period) + 1)

            if d%self.period == self.period-1:
                self.last_full_period = self.num_periods - 1
            else:
                self.last_full_period = self.num_periods - 2

            self.periods = list(range(2*self.num_periods))
            self.periods[0] = int(self.startIdx)
            self.periods[1] = int(self.periods[0] + self.period - self.periodStart)
            for i in range(1, self.num_periods-1):
                self.periods[2*i] = self.periods[2*i-1]
                self.periods[2*i+1] = self.periods[2*i] + self.period
            if self.num_periods > 1:
                self.periods[2*(self.num_periods-1)] = self.periods[2*self.num_periods-3]
                self.periods[2*self.num_periods-1] = int(self.endIdx)

    def begin (self, idx):
        return self.periods[2*idx]

    def end (self, idx):
        return self.periods[2*idx+1]
    
    def numPeriods (self):
        return self.num_periods

    def firstFullPeriod (self):
        """ Return index of first full period"""
        return self.first_full_period

    def lastFullPeriod (self):
        """ Return index of last full period"""
        return self.last_full_period

    def remove (self, toRemove, op, sameSizeAsRemoved, result):
        if len(toRemove) < len(self):
            print("Can't remove: incompatible time series: toRemove's len = %d while self's len = %d" % (len(toRemove), len(self)))
            raise ValueError

        result.data = list(map(tuplify(op), zip(self, toRemove)))
        
        if sameSizeAsRemoved:
            result.setPeriod (toRemove.period)
            result.setPeriodStart (toRemove.periodStart)
            result.setStartIdx (toRemove.startIdx)
            result.setEndIdx (toRemove.endIdx)
        else:
            result.setPeriod (self.period)
            result.setPeriodStart (self.periodStart)
            result.setStartIdx (self.startIdx)
            result.setEndIdx (self.endIdx)

    def equals (self, other, numDecimals):
        """ Compare two time series where values are considered up to numDecimals after decimal points"""
        if len(self) != len(other):
            print("self's length = %d other's length = %d \n" % (len(self), len(other)))
            return False

        small = 10.0**(-numDecimals)
        for (a, b) in zip(self, other):
            diff = a - b
            if diff >= small or diff <= -small:
                print("self = %f, other = %f" % (a, b))
                return False
        return True
    

    def read (self, filename):
        self.data = []
        file = open(filename, 'r')
        for line in file:
            self.data.extend([float(x) for x in line.strip().split()])
        file.close()


    def str_monthly (self,start_month,header=True):
        months = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
        pad = 9
        out = []
        if header:
            for m in months:
                out.append (m.center(pad))
            out.append("\n")
        out.append (' '*(pad*(start_month-1)))

        offset = 12 - start_month
        val_width = 7
        for i, x in enumerate(self):
            val_str = "%*.3f" % (val_width, x)
            out.append (val_str.center(pad))
            if i%12 == offset:
                out.append ("\n")

        return ''.join(out)

    def print_monthly(self, start_month):
        print(self.str_monthly(start_month))

    def print_monthly_to (self, file_name, start_month, header=True):
        file = open (file_name, "w")
        file.write (self.str_monthly(start_month, header))
        file.close()

    def print_to (self, file_name):
        file = open (file_name, "w")
        file.write (''.join(["%f\n" %x for x in self]) )
        file.close()
