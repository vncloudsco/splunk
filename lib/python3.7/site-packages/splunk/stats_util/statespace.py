from __future__ import print_function
from __future__ import division
from past.utils import old_div

from builtins import next, range, object
from builtins import range

from splunk.stats_util.dist import (Chisqdist, Fdist)
from splunk.stats_util.optimize import dfpmin
from splunk.stats_util.optimize import vec

from math import log
from math import exp

import unittest


normality_critical_val = Chisqdist(2).invcdf(.95)


def autocovariance0(data, start, end, mean, k):
    ''' Compute the k lagged autocovariance of the given data from start to end.
    The mean of the data (from start to end) is passed in.
    '''
    cov = 0.0
    N = end - start
    if N <= k: return cov
    for i in range(start, end-k):
        cov += (data[i]-mean)*(data[i+k]-mean)
    return old_div(cov,(N-1))

# data: list, k: lag
def autocovariance (data, mean, k):
    return autocovariance0(data, 0, len(data), mean, k)

def correlogram0(data, start, end, n=0):
    ''' Compute the correlogram of the given data from start to end. The returned correlogram consists of autocorrelations of lag up to n only.
    If n isn't specified, the lag is taken up to len(data)-1. '''
    N = end - start
    mean = 0.0
    for i in range(start, end):
        mean += data[i]
    mean = old_div(mean, N)
    if n == 0 or n >= N: n = N-1
    var = autocovariance0(data, start, end, mean, 0)
    if var == 0: raise Exception
    yield 1.0
    for i in range(1, n+1):
        yield old_div(autocovariance0(data, start, end, mean, i),var)


def correlogram(data, n=0):
    return correlogram0(data, 0, len(data), n)


MAX_LAG = 2000 # so period can't be larger than MAX_LAG
MAX_POINTS = 20*MAX_LAG
 

def findPeriod0(data, start, end):
    ''' Find periodicity of given data from start to end. Return -1 of no periodicity is detected.
    '''
    if end <= start + 1: return 1
#    MAX_LAG = 1000 # so period can't be larger than MAX_LAG
#    MAX_POINTS = 30*MAX_LAG
    if end > start + MAX_POINTS: end = start + MAX_POINTS # cut off at the first MAX_POINTS data points.
    cor = correlogram0(data, start, end, MAX_LAG)
    # TODO: futurize next() needs to be done later
    try:
        prev = next(cor)
    except Exception:  # this means either all elements are equal or else some elements aren't numbers.
        return 1
    curr = next(cor)
    # Go through cor and find the indices of all local peaks.
    # Find the smallest index that might be the period.
    # It's not necessarily the max peak, as the peak at the period may be slightly
    # smaller than the max peak. So we'll ignore the differences that are smaller than 0.01
    peak_idx = 0
    peak_val = 0.0
    for i, next_item in enumerate(cor):
        if curr > prev and curr > next_item and curr > peak_val + 0.01:
            peak_val = curr
            peak_idx = i+1
        prev = curr
        curr = next_item
    if peak_val <= 0.01: return -1
    return peak_idx


# data: a list of float's         
# return -1 if no periodicity is found                                                                                                                                                                       
def findPeriod (data, start, end):
    return findPeriod0(data, start, end)


def findLongestContinuousStretch(data, start, end):
    ''' data may have missing values, denoted by None. This function returns the start and end of 
    the longest stretch without missing values.
    '''
    longestStart = longestEnd = start
    currentStart = currentEnd = start
    while currentEnd < end:
        if data[currentEnd] != None:
            currentEnd += 1
        else:
            if currentEnd-currentStart > longestEnd-longestStart:
                longestStart = currentStart
                longestEnd = currentEnd
            currentEnd += 1
            while currentEnd < end and data[currentEnd] == None:
                currentEnd += 1
            currentStart = currentEnd
    if currentStart < end: # last stretch. Need to compare it to the longest one.
        if currentEnd-currentStart > longestEnd-longestStart:
            longestStart = currentStart
            longestEnd = currentEnd
    return [longestStart, longestEnd]


def findPeriod2(data, start, end):
    ''' Find period of data that may have missing values. We find the longest stretch of the data 
    without missing values and call findPeriod0() on it.
    '''
    start, end = findLongestContinuousStretch(data, start, end)
    return findPeriod0(data, start, end)


def fillinMV(data, start, end):
    ''' Fill in missing values in data. If a value is missing (= None ), we use a weighted average of its nearest left
    and right neighbors. Example: suppose the data is [a, None, None, None, b]. The filled-in array will be: 
    [a, (3*a+b)/4, (2*a + 2*b)/4, (a + 3*b)/4, b]. Note that each filled-in value is the average of its two neighbors.
    If the left end is missing, e.g. [None, None. None, b], then the filled-in elements are all equal to the right end: [b,b,b,b].
    Similar scheme applies if the right end is missing.
    '''
    if end > start + MAX_POINTS: end = start + MAX_POINTS # cut off at the first MAX_POINTS data points.

    i = start
    while i < end:
        if data[i] == None:
            j = i+1
            while j < end and data[j] == None:
                j += 1

            denom = j - i + 1
            if i > start: 
                left = old_div(data[i-1],denom)
            else:
                left = old_div(data[j],denom)
            if j < end: 
                right = old_div(data[j],denom)
            else:
                right = old_div(data[i-1],denom)

            w1 = (denom-1)*left
            w2 = right
            for k in range(i, j):
                data[k] = w1 + w2
                w1 -= left
                w2 += right
            i = j 
        else: i += 1


def findPeriod3(data, start, end):
    data_copy = [x for x in data]
    fillinMV(data_copy, start, end)
    return findPeriod0(data_copy, start, end)


class Datafeed(object):
    def __init__(self, data, start, end, step, missingValued=False):
        self.data = data
        self.start = start
        self.end = end
        self.step = step
        self.data_len = old_div((self.end-self.start),self.step)
        self.cur = self.start
        self.missingValued = missingValued

    def __iter__(self):
        return self

    def getVal(self, i):
        return self.data[i]

    def setVal(self, i, val):
        self.data[i] = val

    def __next__(self):
        if self.cur >= self.end:
            raise StopIteration
        else:
            cur = self.cur
            self.cur += self.step
            return self.data[cur]

    def rewind(self):
        self.cur -= self.step

    def reset(self):
        self.cur = self.start

    def setStart(self, start):
        self.start = start

    def getStart(self):
        return self.start

    def setEnd(self, end):
        self.end = end

    def getEnd(self):
        return self.end

    def getCur(self):
        return self.cur

    def getStep(self):
        return self.step

    def clone(self, start=-1, end=-1, step=1):
        ''' Return a Datafeed pointing to the same underlying data but using given start, end, and step.
        If the parameters start and step aren't specified, then use current object's parameters.
        '''
        if start==-1: return Datafeed(self.data, self.start, self.end, self.step)
        return Datafeed(self.data, start, end, step)

    def period(self):
        if self.missingValued:
            return findPeriod3(self.data, self.start, self.end)
        else:
            return findPeriod(self.data, self.start, self.end)

    def __len__(self):
        return (self.end - self.start)//self.step




FORECAST=3
class Univar(object):
    ''' Wrapper around the univariate algorithms.
    '''

    def __init__(self, algorithm, data, data_start, data_end, period=-1, forecast_len=FORECAST, correlate=None, missingValued=False):
        self.data_len = data_end - data_start
        if period > MAX_LAG:
            raise ValueError("period can't be greater than %s" %MAX_LAG)
        self.period = period
        self.forecast_len = forecast_len
        self.correlate = correlate
        self.algos = [None]*len(data)
        try:
            if not algorithm in ALGORITHMS:
                raise AttributeError("Unkown algorithm")
            if algorithm[:3]=='LLP':
                for i in range(len(data)):
                    self.algos[i] = ALGORITHMS[algorithm](Datafeed(data[i], data_start, data_end, 1, missingValued), period=self.period, forecast_len=self.forecast_len)
            else:
                for i in range(len(data)):
                    self.algos[i] = ALGORITHMS[algorithm](Datafeed(data[i], data_start, data_end, 1), forecast_len=self.forecast_len)
        except AttributeError as e:
            raise e


    def state(self, ts_idx, i):
#        if ts_idx < 0 or ts_idx > len(self.algos):
#            print("Invalid time series index: %d" % ts_idx)
#            return 0.0
        return self.algos[ts_idx].fc[i]


    def var(self, ts_idx, i):
#        if ts_idx < 0 or ts_idx > len(self.algos):
#            print("Invalid time series index: %d" % ts_idx)
#            return 0.0
        return self.algos[ts_idx].p[i]


    def datalen(self):
        return self.data_len

    def multivariate(self):
        return False

    def period(self):
        return self.period

    def least_num_data(self):
        return self.algos[0].least_num_data()

    def first_forecast_index(self):
        return self.algos[0].first_forecast_index()


class Multivar(object):
    ''' Wrapper around the multivariate algorithms.
    '''

    def __init__(self, algorithm, data, data_end, period=None, forecast_len=FORECAST, correlate=None, missingValued=False):
        if period is not None and period > MAX_LAG:
            raise ValueError("period can't be greater than %s" %MAX_LAG)
        self.datalength = data_end
        self.period = period
        self.forecast_len = forecast_len
        self.correlate = correlate
        self.algorithm = algorithm
        if missingValued:
            if self.algorithm[-2:] != 'mv':
                self.algorithm += 'mv'
        try:
            if self.algorithm[:3] == 'LLB':
                self.algo = ALGORITHMS[self.algorithm].instance(var1=data[0], var2=correlate, data_len=data_end, forecast_len=forecast_len)
            else:
                self.algo = ALGORITHMS[self.algorithm](data=data, data_len=data_end, forecast_len=forecast_len)
        except AttributeError as e:
            raise e
        

    def predict(self, predict_var, start=30):
        if self.algorithm[:3] == 'LLB':
            self.algo.predict(predict_var, start)


    def state(self, ts_idx, i):
        if self.algorithm[:3] == 'LLB':
            return self.algo.fc[i]
        else:
            return self.algo.state(ts_idx, i)


    def var(self, ts_idx, i):
        if self.algorithm[:3] == 'LLB':
            return self.algo.variance(i)
        else:
            return self.algo.var(ts_idx, i)


    def datalen(self):
        return self.algo.datalen()

    def multivariate(self):
        return True

    def period(self):
        return self.period

    def least_num_data(self):
        return self.algo.least_num_data()

    def first_forecast_index(self):
        return self.algo.first_forecast_index()



class LL0(object):

    def __init__ (self, datafeed, fc=None, fcstart=-1, fcend=-1, fcinitval=None, 
            P=None, Pstart=-1, Pend=-1, Pinitval=None, state_step=1, forecast_len=FORECAST):

        self.fc, self.fcstart, self.fcend, self.fcinitval = fc, fcstart, fcend, fcinitval
        self.p, self.pstart, self.pend, self.pinitval = P, Pstart, Pend, Pinitval
        self.state_step = state_step

        self.setData(datafeed)
        self.setForecastLen(forecast_len)
        self.initStates(fc, fcstart, fcend, fcinitval, P, Pstart, Pend, Pinitval)
        self.computeStates()

        
    def setData(self, datafeed):
        self.data_len = len(datafeed)
        i = self.fcstart
        while next(datafeed)==None and (self.fc==None or self.fc[i]==None):
            i += self.state_step
        datafeed.rewind()
        datafeed.setStart(datafeed.getCur())
        if len(datafeed)==0:
            raise ValueError
        self.datafeed = datafeed


    def setForecastLen(self, forecast_len):
        self.forecast_len = forecast_len


    def initStates(self, fc, fcstart, fend, fcinitval, P, Pstart, Pend, Pinitval):
        if fc == None:
            self.fc = [None]*(self.data_len+self.forecast_len) # filtered states
            self.fcstart = self.datafeed.getStart()
            self.fcend = len(self.fc)

        if self.p == None:
            self.p = [None]*len(self.fc) # variances of predictions (not filtered states)
            self.pstart = self.fcstart
            self.pend = self.fcend


    def computeStates(self):
        self.sigma = 0.
        self.nu = 0.
        psi = vec([1.0])
        dfpmin(lambda x: self.llh(exp(x)), psi)
        q = exp(psi[0])
        self.updateAll(q)
        self.var = self.p[self.cur_state_end-self.state_step] + self.sigma
        # Compute forescast beyond the end of the given data
        # Use equations (2.38) in Durbin-Koopman. Basically, just set v_t = 0 and K_t = 0.
        fcend = self.cur_state_end
        Pend = self.cur_state_end
        fclast = fcend - self.state_step
        Plast = Pend - self.state_step
        for i in range(0, self.forecast_len*self.state_step, self.state_step):
            self.fc[fcend+i] = self.fc[fclast]
            self.p[Pend+i] = self.p[Plast+i] + self.nu

    @classmethod 
    def least_num_data(cls):
        return 1


    def first_forecast_index(self):
        return self.datafeed.getStart()


    def update_kalman (self, y, a, p, q):
        if y==None: return [a, p+q, 0, p+1.] # missing value. See Durbin-Koopmen, page 24.
        f = p + 1.
        k = old_div(p,f)
        p = k + q
        v = y - a
        a = a + k*v
        return [a, p, v, f]


    def llh (self, q): # compute llh using data from start to end
        """ The concentrated diffuse loglikelihood. See 'Time Series Analysis by State Space Methods'
        by Durbin-Koopman, p.32."""

        self.datafeed.reset()
        
        if self.fc[self.fcstart] != None:
            a = self.fc[self.fcstart]
            p = self.p[self.pstart]
            numdatataken = 0
        else:
            a = next(self.datafeed)
            p = 1.0 + q
            numdatataken = 1

        t1, t2 = 0.0, 0.0
        for x in self.datafeed:
            [a, p, v, f] = self.update_kalman(x, a, p, q)
            t1 += old_div(v**2,f)
            t2 += log(f)
        
        if t1 == 0.0: return t2
        return (len(self.datafeed)-numdatataken)*log(t1) + t2


    def updateAll(self, q):
        self.datafeed.reset()
        if self.fc[self.fcstart] != None:
            a = self.fc[self.fcstart]
            p = self.p[self.pstart]
            i = b = 0
        else:
            self.fc[self.fcstart] = a = next(self.datafeed)
            self.p[self.pstart] = p = 1.0 + q
            i = b = self.state_step
        sigma = 0.0
        for x in self.datafeed:
            [a, p, v, f] = self.update_kalman(x, a, p, q)
            sigma += old_div(v*v,f)
            self.fc[self.fcstart+i] = a
            self.p[self.pstart+i] = p
            i += self.state_step
        sigma = old_div(sigma, max(1, old_div((i-b),self.state_step)) )
        self.sigma = sigma
        self.nu = q*sigma
        for j in range(self.pstart, self.pstart+i, self.state_step):
            self.p[j] = (self.p[j] + 1)*sigma # we add one sigma for the measuremant variance.
        self.cur_state_end = self.pstart+i

    def variance(self, i):
        n = self.datafeed.getEnd()
        if i < n:
            return self.p[i] + self.sigma # sigma is the measurement variance.
        else:
            return self.var + (i-n+1)*self.nu
            
    def datalen(self):
        return self.data_len


class LL(LL0):
    def computeStates(self):
        SUBLEN = 2000
        self.divide = max(old_div(len(self.datafeed),SUBLEN), 1)
        start = self.datafeed.getStart()
        end = self.datafeed.getEnd()
        step = self.datafeed.getStep()
        datafeed = self.datafeed.clone() 
        sublen = step*(old_div(len(self.datafeed),self.divide))
        fcstart, fcend, fcinitval = self.fcstart, self.fcend, None
        Pstart, Pend, Pinitval = self.pstart, self.pend, None
        for i in range(self.divide-1):
            datafeed.setEnd(start+sublen)
            model = LL0(datafeed, fc=self.fc, fcstart=fcstart, fcend=fcend, fcinitval=fcinitval,  
                    P=self.p, Pstart=Pstart, Pinitval=Pinitval, state_step=self.state_step, forecast_len=0)
            start += sublen
            fcstart += sublen
            fcend += sublen
            Pstart += sublen
            Pend += sublen
            datafeed.setStart(start)
            fcinitval = self.fc[start-1]
            Pinitval = self.p[start-1]
        datafeed.setEnd(end)
        model = LL0(datafeed, fc=self.fc, fcstart=fcstart, fcend=fcend, fcinitval=fcinitval,  
                    P=self.p, Pstart=Pstart, Pend=Pend, Pinitval=Pinitval, state_step=self.state_step, forecast_len=self.forecast_len)
        self.nu = model.nu

class LLP(object):
    def __init__(self, datafeed, period=-1, forecast_len=FORECAST):
        self.setData(datafeed)
        self.setPeriod(period)
        self.setForecastLen(forecast_len)
        self.initStates()
        self.setModels()
        self.computeStates()

    def setPeriod(self, period):
        if period >= 2:
            self.period = period
        else:
            self.period = self.datafeed.period()
            if self.period < 2:
                raise ValueError("data is not periodic")
        if self.data_len < self.least_num_data():
            raise ValueError("Too few data points: %d. Need at least %d" %(self.data_len, self.least_num_data()))

    def setData(self, datafeed):
        self.datafeed = datafeed
        self.data_len = len(self.datafeed)


    def setForecastLen(self, forecast_len):
        self.forecast_len = max(forecast_len, self.period)


    def initStates(self):
        self.fc = [None]*(self.data_len+self.forecast_len) # filtered states
        self.p = [None]*len(self.fc) # variances of filtered states


    def setModels(self):
        # Fill in missing values in the first period
        for i in range(self.period):
            if self.datafeed.getVal(i) == None:
                j = i+1
                while j < self.data_len and self.datafeed.getVal(j) == None:
                    j += 1
                denom = j - i + 1
                right = old_div(self.datafeed.getVal(j),denom)
                if i > 0: left = old_div(self.datafeed.getVal(i-1),denom)
                else: left = right
                w1 = (denom-1)*left
                w2 = right
                for k in range(i, j):
                    self.datafeed.setVal(k, w1 + w2)
                    w1 -= left
                    w2 += right


        self.models = [None]*self.period
        start, end = self.datafeed.getStart(), self.datafeed.getEnd()
        for i in range(self.period):
            model_start = start + i
            model_end = end - ((end-i)%self.period)
            if model_end < end: model_end += self.period
            datafeed = self.datafeed.clone(model_start, model_end, self.period)
            diff = len(self.fc) - model_end
            model_forecast_len = old_div(diff,self.period)
            if diff%self.period != 0: model_forecast_len += 1

            self.models[i] = LL(datafeed, fc=self.fc, fcstart=model_start, fcend=model_end, fcinitval=None,
                                P=self.p, Pstart=model_start, Pend=model_end, Pinitval=None,
                                state_step=self.period, forecast_len=model_forecast_len)

    def computeStates(self):
        pass


    def least_num_data(self):
        return self.period*LL.least_num_data()


    def first_forecast_index(self):
        return min([i+self.models[i].first_forecast_index() for i in range(self.period)])


    def variance(self, i):
        return self.models[i%self.period].variance(old_div(i,self.period))

    def datalen(self):
        return self.data_len
 


class LLP1(LLP):
    ''' The only difference between LLP1 and LLP is that self.p[i] is set to max(self.p[i-1],m.p[j]) (see below)
    instead of self.p[i] = m.p[j] as in LLP.
    '''

    def computeStates(self):
        for i in range(1, len(self.p)):
            self.p[i] = max(self.p[i-1], self.p[i])


class LLP2(LLP):
    ''' LLP2 combines LL and LLP. The period must be given; LLP2 doesn't compute it. 
    '''
    def setModels(self):
        self.model1 = LL(datafeed=self.datafeed, forecast_len=self.forecast_len)
        try:
            self.model2 = LLP(datafeed=self.datafeed, period=self.period, forecast_len=self.forecast_len)
        except ValueError as e:
            raise e


    def computeStates(self):
        for i in range(len(self.fc)):
            self.combine(i)


    def first_forecast_index(self):
        return min(self.model1.first_forecast_index(), self.model2.first_forecast_index())


    def variance(self, i):
        return self.p[i]


    def combine(self, i):
        if self.model1.p[i]==None or self.model1.fc[i]==None:
            self.p[i] = self.model2.p[i]
            self.fc[i] = self.model2.fc[i]
        elif self.model2.p[i]==None or self.model2.fc[i]==None:
            self.p[i] = self.model1.p[i]
            self.fc[i] = self.model1.fc[i]
        elif self.model1.p[i]==0 and self.model2.p[i]==0:
            self.p[i] = 0
            self.fc[i] = (self.model1.fc[i]+self.model2.fc[i])/2.
        else:
            k = old_div(self.model1.p[i],(self.model1.p[i]+self.model2.p[i]))
            self.fc[i] = self.model1.fc[i] + k*(self.model2.fc[i]-self.model1.fc[i])
            self.p[i] = (1-k)*self.model1.p[i]


class LLP5(LLP):
    ''' LLP5 combines LLT and LLP1. If there's no periodicity, it uses LLT only. Otherwise it uses both LLT and LLP1
    and outputs a weighted average of the two predictions.
    '''

    def setPeriod(self, period):
        try:
            LLP.setPeriod(self, period)
        except ValueError:
            pass # LLP5 combines LLT and LLP1, so if there's no periodicity, it uses LLT only.


    def setModels(self):
        self.model1 = LLT(datafeed=self.datafeed, forecast_len=self.forecast_len) # starts with LLT
        self.model2 = None
        if self.period >= 2 and self.data_len >= self.period*LL.least_num_data(): # the upper bound 100 is arbitrary, but we want an upper bound.
            self.model2 = LLP1(datafeed=self.datafeed, period=self.period, forecast_len=self.forecast_len)


    def computeStates(self):
        model1 = self.model1
        model2 = self.model2
        for i in range(model1.first_forecast_index(), len(self.fc)):
            if model2 == None or model2.p[i] == None or model2.fc[i] == None:
                self.p[i] = model1.p[i]
                self.fc[i] = model1.fc[i]
            elif model1.p[i]==0 and model2 and model2.p[i]==0:
                self.p[i] = 0
                self.fc[i] = old_div((model1.fc[i]+model2.fc[i]),2)
            else:
                K = old_div(model1.p[i],(model1.p[i]+model2.p[i]))
                self.fc[i] = model1.fc[i] + K*(model2.fc[i]-model1.fc[i])
                self.p[i] = (1-K)*model1.p[i]


    def first_forecast_index(self):
        return self.model1.first_forecast_index()


    def variance(self, i):
        if i >= len(self.p): raise ValueError("variance index out of bound")
        return self.p[i]


class LLT2(LL0):
    """ Local linear trend time series model. Difference between this and LLT is that this one has
    nonconstant trend. We add a noise component to the trend."""
 
    def setData(self, datafeed):
        LL0.setData(self, datafeed)
        # If the second data point is missing, fill it using its neighbor averages
        data_start = self.datafeed.getStart()
        step = self.datafeed.getStep()
        i = data_start+step
        if i < self.datafeed.getEnd() and self.datafeed.getVal(i) == None:
            j = i + step
            while j < self.datafeed.getEnd() and self.datafeed.getVal(j) == None:
                j += step
            if j < self.datafeed.getEnd():
                fillval = old_div((self.datafeed.getVal(data_start) + self.datafeed.getVal(j)),2)
            else:
                fillval = self.datafeed.getVal(data_start)
            self.datafeed.setVal(i, fillval)

    def computeStates(self):
        self.Z = [1., 0.]
        self.Q = 0.0
        psi = vec([1.0, 1.0])
        dfpmin(lambda x, y: -self.llh(exp(x), exp(y)), psi)
        self.zeta = exp(psi[0])
        self.eta = exp(psi[1])
        self.trend = [None]*len(self.fc)
        self.updateAll(self.zeta, self.eta)
        # Compute forescast beyond the end of the given data
        # Use equations (2.38) in Durbin-Koopman. Basically, just set v_t = 0 and K_t = 0.
        fcend = self.cur_state_end
        Pend = self.cur_state_end
        fclast = fcend - self.state_step
        Plast = Pend - self.state_step
        self.tr = self.trend[fclast]
        for i in range(0, self.forecast_len*self.state_step, self.state_step):
            self.fc[fcend+i] = self.fc[fclast+i] + self.tr
            self.p[Pend+i] = self.p[Plast+i] + self.var + self.nu


    # Concentrated Kalman filter update
    def update_kalman(self, y, a, P, P2, K, zeta, eta):
        if y==None:
            F = P[0] + 1.
            a[0] = a[0] + a[1] # a[1] remains the same
            P2 = [P[0]+zeta, P[1], P[2], P[3]+eta] 
            return [0, F, log(F)]
 
        x1 = P[0] + P[2]
        x2 = P[1] + P[3]
        F = P[0] + 1.
        K[0] = old_div(x1,F)
        K[1] = old_div(P[2],F)
        v = y - a[0]
        a[0] = a[0]+a[1]+v*K[0]
        a[1] = a[1]+v*K[1]
        L0 = 1 - K[0]
        # This is not a mistake. This is the transpose of the L in the Kalman formula.
        # We compute the transpose here so we don't need to take the transpose when computing P2 below.
        P2[0] = x1*L0 + x2 + zeta
        P2[1] = x2 - x1*K[1] 
        P2[2] = P[2]*L0 + P[3]
        P2[3] = P[3] - P[2]*K[1] + eta
        return [v, F, log(F)]


    # Steady state update
    def steady_update(self, y, a, K):
        if y==None:
            a[0] = a[0] + a[1]
            return 0
        v = y - a[0]
        a[0] = a[0]+a[1]+v*K[0]
        a[1] = a[1]+v*K[1]
        return v


    def llh(self, zeta, eta):
        """ The concentrated diffuse loglikelihood function. """
        self.datafeed.reset()
        pt1 = next(self.datafeed)
        pt2 = next(self.datafeed)
        a = [2*pt2 - pt1, pt2 - pt1] 
        P = [5. + 2.*zeta + eta, 3. + zeta + eta, 3. + zeta + eta, 2. + zeta + 2.*eta]
        P2 = [None]*4
        F = P[0]+1.0
        lF = log(F)
        K = [old_div((P[0]+P[2]),F), old_div(P[2],F)]
        t1, t2 = 0., 0.

        steady = False
        for y in self.datafeed:
            if not steady:
                [v, F, lF] = self.update_kalman(y, a, P, P2, K, zeta, eta)
                norm = 0
                for i in range(4):
                    norm += abs(P2[i]-P[i])
                # this is slower: norm = sum(abs(x-y) for (x,y) in zip(P2,P))
                if norm < 0.001:
                    steady = True
                for i in range(4):
                    P[i] = P2[i]
            else:
                v = self.steady_update(y, a, K)
                
            t1 += old_div(v**2,F)
            t2 += lF

        if t1 == 0.: return -t2
        return -(len(self.datafeed)-2)*log(t1) - t2


    def updateAll(self, zeta, eta):
        self.datafeed.reset()
        pt1 = next(self.datafeed)
        pt2 = next(self.datafeed)
        a = [2*pt2 - pt1, pt2 - pt1]
        Z = [1., 0.]
        P = [5. + 2.*zeta + eta, 3. + zeta + eta, 3. + zeta + eta, 2. + zeta + 2.*eta]
        P2 = [None]*4
        F = P[0]+1.0
        lF = log(F)
        K = [old_div((P[0]+P[2]),F), old_div(P[2],F)]
        
        epsilon = 0.
        steady = False
        fcstart = self.fcstart
        pstart = self.pstart
        i = b = fcstart + 2*self.state_step
        for y in self.datafeed:
            if not steady:
                [v, F, lF] = self.update_kalman(y, a, P, P2, K, zeta, eta)
                norm = 0
                for j in range(4):
                    norm += abs(P2[j]-P[j])
                if norm < 0.001:
                    steady = True
                for j in range(4):
                    P[j] = P2[j]
                self.fc[i] = a[0]
                self.trend[i] = a[1]
            else:
                v = self.steady_update(y, a, K)
                self.fc[i] = a[0]
                self.trend[i] = a[1]
            epsilon += old_div(v*v,F)
            self.p[i] = P[0] + 1  
            i += self.state_step

        self.epsilon = old_div(epsilon,len(self.datafeed))
        self.zeta = zeta*self.epsilon
        self.eta = eta*self.epsilon
        self.var = (P[0] + 1)*self.epsilon
        self.nu = P[3]*self.epsilon
        self.fc[fcstart] = pt1
        self.trend[fcstart] = 0.0
        self.p[pstart] = self.epsilon*(1 + zeta)
        self.fc[fcstart+self.state_step] = pt2
        self.trend[fcstart+self.state_step] = pt2 - pt1
        self.p[pstart+self.state_step] = self.epsilon*(5 + 2*zeta)
        for j in range(b, i, self.state_step):
            self.p[j] = (self.p[j] + 1)*self.epsilon # add one epsilon for the measurement variance
        self.cur_state_end = i


    def variance(self, i):
        n = self.datafeed.getEnd()
        if i < n-2:
            return self.p[i]
        else:
            return self.var + (i-n+3)*self.zeta 


class LLT(LL0):
    """ Local linear trend time series model """
    def setData(self, datafeed):
        if len(datafeed) < LLT.least_num_data():
            raise ValueError("Too few data points: %d. Need at least %d" %(len(datafeed), LLT.least_num_data()))
        LL0.setData(self, datafeed)
        # If the second data point is missing, fill it using an average of its neighbor
        data_start = self.datafeed.getStart()
        step = self.datafeed.getStep()
        i = data_start+step
        if i < self.datafeed.getEnd() and self.datafeed.getVal(i) == None:
            j = i + step
            while j < self.datafeed.getEnd() and self.datafeed.getVal(j) == None:
                j += step
            if j < self.datafeed.getEnd():
                fillval = old_div((self.datafeed.getVal(data_start) + self.datafeed.getVal(j)),2)
            else:
                fillval = self.datafeed.getVal(data_start)
            self.datafeed.setVal(i, fillval)

   
    def computeStates(self):
        self.Z = [1., 0.]
        self.Q = 0.0
        self.var = 10000.
        psi = vec([1.])
        dfpmin(lambda x: -self.llh(exp(x)), psi)
        self.zeta = exp(psi[0]) 
        self.updateAll(self.zeta)

        # Compute forescast beyond the end of the given data
        # Use equations (2.38) in Durbin-Koopman. Basically, just set v_t = 0 and K_t = 0.
        fcend = self.cur_state_end
        Pend = self.cur_state_end
        fclast = fcend - self.state_step
        Plast = Pend - self.state_step
        for i in range(0, self.forecast_len*self.state_step, self.state_step):
            self.fc[fcend+i] = self.fc[fclast+i] + self.trend
            self.p[Pend+i] = self.p[Plast+i] + self.zeta


    @classmethod
    def least_num_data(cls):
        return 2


    @classmethod
    def first_forecast_index(cls):
        return 0


    # Concentrated Kalman filter update
    def update_kalman(self, y, a, P, K, zeta):
        if y==None:
            a[0] = a[0] + a[1] # a[1] remains the same
            P[0] += zeta
            F = P[0] + 1
            return [0, F, log(F)]
        x1 = P[0] + P[2]
        x2 = P[1] + P[3]
        F = P[0] + 1.
        K[0] = old_div(x1,F)
        K[1] = old_div(P[2],F)
#        v = y - a[0]
        v = y - a[0] - a[1]
        a[0] = a[0]+a[1]+v*K[0]
        a[1] = a[1]+v*K[1]
        L0 = 1 - K[0]
        # This is not a mistake. This is the transpose of the L in the Kalman formula.
        # We compute the transpose here so we don't need to take the transpose when updating P below.
        P[0] = x1*L0 + x2 + zeta
        P[1] = x2 - x1*K[1] 
        p2, p3 = P[2], P[3]
        P[2], P[3] = p2*L0 + p3, p3 - p2*K[1]

        return [v, F, log(F)]


    def llh(self, zeta):
        """ The concentrated diffuse loglikelihood function. """
        self.datafeed.reset()
        pt1 = next(self.datafeed)
        pt2 = next(self.datafeed)
#        a = [2*pt2 - pt1, pt2 - pt1]
        a = [pt2, pt2 - pt1]
        P = [5.+2.*zeta, 3.+zeta, 3.+zeta, 2.+zeta]
        F = P[0]+1.0
        lF = log(F)
        K = [old_div((P[0]+P[2]),F), old_div(P[2],F)]
        t1, t2 = 0., 0.

        for x in self.datafeed:
            [v, F, lF] = self.update_kalman(x, a, P, K, zeta)
            t1 += old_div(v**2,F)
            t2 += lF

        if t1 == 0.: return -t2
        return -(len(self.datafeed)-2)*log(t1) - t2


    def updateAll(self, zeta):
        self.datafeed.reset()
        pt1 = next(self.datafeed)
        pt2 = next(self.datafeed)
#        a = [2*pt2 - pt1, pt2 - pt1]
        a = [pt2, pt2 - pt1]
        Z = [1., 0.]
        P = [5.+2.*zeta, 3.+zeta, 3.+zeta, 2.+zeta]
        F = P[0]+1.0
        lF = log(F)
        K = [old_div((P[0]+P[2]),F), old_div(P[2],F)]
        self.epsilon = 1.0
        
        epsilon = 0.
        fcstart = self.fcstart
        pstart = self.pstart
        i = b = fcstart + 2*self.state_step
        for x in self.datafeed:
            [v, F, lF] = self.update_kalman(x, a, P, K, zeta)
            self.fc[i] = a[0]
            epsilon += old_div(v*v,F)
            self.p[i] = P[0] + 1  
            i += self.state_step

        if len(self.datafeed) > 2:
            self.epsilon = old_div(epsilon,(len(self.datafeed) - 2))

        self.zeta = zeta*self.epsilon
        self.trend = a[1]
        self.var = (P[0] + 1)*self.epsilon
        self.fc[fcstart] = pt1
        self.p[pstart] = self.epsilon*(1 + zeta)
        self.fc[fcstart+self.state_step] = pt2
        self.p[pstart+self.state_step] = self.epsilon*(5 + 2*zeta)
        for j in range(b, i, self.state_step):
            self.p[j] = (self.p[j] + 1)*self.epsilon # add one epsilon for the measurement variance
        self.cur_state_end = i

    def variance(self, i):
        n = self.datafeed.getEnd()
        if i < n-2:
            return self.p[i]
        else:
            return self.var + (i-n+3)*self.zeta 



class BiLL(object):
    """ Bivariate Local Level """
        
    eps = 1e-12

    def __init__(self, data, data_len, forecast_len=FORECAST):
        if len(data) == 0: raise ValueError
        self.data = data
        self.datalength = data_len #min(len(data[0]), len(data[1]))
        self.forecast_len = forecast_len
        self.Q = [None]*3
        self.P = [None]*(self.datalength+self.forecast_len) # variances of predictions (not filtered states)
        self.a = [None]*len(self.P) # filter states
        self.a[0] = [data[0][0], data[1][0]]
        self.scale = .1
        psi = vec([1./self.scale, .5/self.scale, 1./self.scale])
        dfpmin(lambda x, y, z: self.llh(x, y, z, self.datalength), psi)
        self.updateAll(psi)
        # Compute forescast beyond the end of the given data
        # Use equations (2.38) in Durbin-Koopman. Basically, just set v_t = 0 and K_t = 0.
        n = self.datalength
        for i in range(self.forecast_len):
            self.a[n+i] = self.a[n-1]
            self.P[n+i] = [None]*3
            for j in range(3):
                self.P[n+i][j] = self.P[n+i-1][j] + self.Q[j]
                if j != 1:
                    self.P[n+i][j] += self.epsilon


    @classmethod
    def instance(cls, var1, var2, forecast_len=FORECAST):
        cls = BiLL((var1, var2), forecast_len)
        return cls

    @classmethod
    def least_num_data(cls):
        return 1

    @classmethod
    def first_forecast_index(cls):
        return 0 
    

    def update_Kalman(self, y, a, v, P, K, Fi):
        detP = P[0]*P[2] - P[1]*P[1]
        trP = P[0] + P[2]
        detF = detP + trP + 1.
        
        Fi[0] = old_div((P[2]+1.),detF)
        Fi[1] = old_div(-P[1],detF)
        Fi[2] = old_div((P[0]+1.),detF)

        K[0] = old_div((P[0]+detP),detF)
        K[1] = -Fi[1] # = P[1]/detF
        K[2] = old_div((P[2]+detP),detF)

        v[0] = y[0] - a[0]
        v[1] = y[1] - a[1]

        a[0] += K[0]*v[0] + K[1]*v[1]
        a[1] += K[1]*v[0] + K[2]*v[1]

        PP1 = K[0] + self.Q[0]
        PP2 = K[1] + self.Q[1]
        PP3 = K[2] + self.Q[2]
        diff = abs(PP1-P[0]) + abs(PP2-P[1]) + abs(PP3-P[2])
        if diff < 1.0e-5: steady = True
        else: steady = False
        P[0], P[1], P[2] = PP1, PP2, PP3

        return detF, steady


    def update_steady(self, y, a, v, K):
        v[0] = y[0] - a[0]
        v[1] = y[1] - a[1]
        a[0] += K[0]*v[0] + K[1]*v[1]
        a[1] += K[1]*v[0] + K[2]*v[1]
        
        
    # start = where to begin in data
    def next_state(self, data, start, end, a, v, P, K, Fi):
        steady = False
        for i in range(start, end):
            if not steady:
                detF, steady = self.update_Kalman((data[0][i], data[1][i]), a, v, P, K, Fi)
            else: self.update_steady((data[0][i], data[1][i]), a, v, K)
            yield detF


    def llh(self, t1,t2,t3, datarange=200):
        eps = BiLL.eps
        self.Q[0] = t1**2+eps 
        self.Q[1] = (abs(t1)+eps)*t2
        self.Q[2] = t3**2+eps+t2**2 

        a = [self.data[0][0], self.data[1][0]]
        P = [self.Q[0]+1., self.Q[1], self.Q[2]+1.]
        K = [0.]*3
        Fi = [1., 0., 1.]
        v = [0.]*2
        T1, T2 = 0., 0.
        
        steady = False
        for detF in self.next_state(self.data, 1, datarange, a, v, P, K, Fi):
            T1 += v[0]*Fi[0]*v[0] + 2*v[0]*Fi[1]*v[1] + v[1]*Fi[2]*v[1]
            T2 += log(detF)

        if T1 == 0: return T2
        return (datarange-1)*log(T1) + T2


    def updateAll(self, psi):
        eps = LLB.eps
        [t1, t2, t3] = psi
        self.Q[0] = t1**2+eps 
        self.Q[1] = (abs(t1)+eps)*t2
        self.Q[2] = t3**2+eps+t2**2 
        data = self.data
        self.a[0] = a = [self.data[0][0], self.data[1][0]]
        self.P[0] = P = [self.Q[0]+1., self.Q[1], self.Q[2]+1.]
        K = [0.]*3
        Fi = [1., 0., 1.]
        v = [0.]*2
        epsilon = 0.
        start = 0
        end = self.datalength
        for i, detF in enumerate(self.next_state(data, start, end, a, v, P, K, Fi)):
            self.a[i+start] = [a[0], a[1]]
            self.P[i+start] = [(P[0]+1), P[1], (P[2]+1)]
            epsilon += v[0]*Fi[0]*v[0] + 2*v[0]*Fi[1]*v[1] +  v[1]*Fi[2]*v[1]
        epsilon /= self.datalength
        self.epsilon = epsilon
        for i in range(len(self.P)):
            if self.P[i]:
                self.P[i] = [u*epsilon for u in self.P[i]]
        for i in range(len(self.Q)):
            self.Q[i] *= epsilon
 

    def state(self, ts_idx, i):
        if ts_idx != 0 and ts_idx != 1:
            print("Invalid time series index: %d" % ts_idx)
            return 0.0
        if i < 0 or i > len(self.a):
            print("Invalid state index: %d" % i)
            return 0.0
        return self.a[i][ts_idx]


    def var(self, ts_idx, i):
        if ts_idx != 0 and ts_idx != 1:
            print("Invalid time series index: %d" % ts_idx)
            return 0.0
        if i < 0 or i > len(self.P):
            print("Invalid state index: %d" % i)
            return 0.0
        if i < self.datalength:
            return self.P[i][ts_idx]+ self.Q[ts_idx]          
        else:
            return self.P[i][ts_idx]


    def datalen(self):
        return self.datalength


class BiLLmv(BiLL):
    """ Bivariate Local Level for data with missing values  """

    def __init__(self, data, data_len, forecast_len=FORECAST):
        BiLL.__init__(self, data, data_len, forecast_len=forecast_len)


    @classmethod
    def instance(cls, var1, var2, forecast_len=FORECAST):
        cls = BiLLmv((var1, var2), forecast_len)
        return cls

    def update_Kalman(self, y, a, v, P, K, Fi):
        detP = P[0]*P[2] - P[1]*P[1]
        trP = P[0] + P[2]
        detF = detP + trP + 1.

        Fi[0] = old_div((P[2]+1.),detF)
        Fi[1] = old_div(-P[1],detF)
        Fi[2] = old_div((P[0]+1.),detF)

        K[0] = old_div((P[0]+detP),detF)
        K[1] = -Fi[1] # = P[1]/detF
        K[2] = old_div((P[2]+detP),detF)

        if y[0] == None: 
            v[0] = 0
            P[0] += self.Q[0]
        else:
            v[0] = y[0] - a[0]
            a[0] += K[0]*v[0] + K[1]*v[1]
            P[0] = K[0] + self.Q[0]
        if y[1] == None: 
            v[1] = 0
            P[2] += self.Q[2]
        else:
            v[1] = y[1] - a[1]
            a[1] += K[1]*v[0] + K[2]*v[1]
            P[2] = K[2] + self.Q[2]
        P[1] = K[1] + self.Q[1]

        return detF

        
    # start = where to begin in data
    def next_state(self, data, start, end, a, v, P, K, Fi):
        steady = False
        for i in range(start, end):
            yield self.update_Kalman((data[0][i], data[1][i]), a, v, P, K, Fi)



class BiLLmv2(object):
    """ Bivariate Local Level for data with missing values  """
        
    eps = 1e-12

    def __init__(self, data, data_len, forecast_len=FORECAST):
        if len(data) == 0: raise ValueError
        self.data = data
        self.datalength = data_len #min(len(data[0]), len(data[1]))
        self.forecast_len = forecast_len
        self.Q = [None]*3
        self.P = [None]*(self.datalength+self.forecast_len) # variances of predictions (not filtered states)
        self.a = [None]*len(self.P) # filter states
        self.a[0] = [data[0][0], data[1][0]]
        self.scale = .1
        psi = vec([1./self.scale, .5/self.scale, 1./self.scale])
        dfpmin(lambda x, y, z: self.llh(x, y, z, self.datalength), psi)
        self.updateAll(psi)
        # Compute forescast beyond the end of the given data
        # Use equations (2.38) in Durbin-Koopman. Basically, just set v_t = 0 and K_t = 0.
        n = self.datalength
        for i in range(self.forecast_len):
            self.a[n+i] = self.a[n-1]
            self.P[n+i] = [None]*3
            for j in range(3):
                self.P[n+i][j] = self.P[n+i-1][j] + self.Q[j]
                if j != 1:
                    self.P[n+i][j] += self.epsilon



    @classmethod
    def instance(cls, var1, var2, forecast_len=FORECAST):
        cls = BiLL((var1, var2), forecast_len)
        return cls

    @classmethod
    def least_num_data(cls):
        return 1

    @classmethod
    def first_forecast_index(cls):
        return 0 
    
    def update_Kalman(self, y, a, v, P, K, Fi):
        detP = P[0]*P[2] - P[1]*P[1]
        trP = P[0] + P[2]
        detF = detP + trP + 1.

        Fi[0] = old_div((P[2]+1.),detF)
        Fi[1] = old_div(-P[1],detF)
        Fi[2] = old_div((P[0]+1.),detF)

        K[0] = old_div((P[0]+detP),detF)
        K[1] = -Fi[1] # = P[1]/detF
        K[2] = old_div((P[2]+detP),detF)

        if y[0] == None: 
            v[0] = 0
            P[0] += self.Q[0]
        else:
            v[0] = y[0] - a[0]
            a[0] += K[0]*v[0] + K[1]*v[1]
            P[0] = K[0] + self.Q[0]
        if y[1] == None: 
            v[1] = 0
            P[2] += self.Q[2]
        else:
            v[1] = y[1] - a[1]
            a[1] += K[1]*v[0] + K[2]*v[1]
            P[2] = K[2] + self.Q[2]
        P[1] = K[1] + self.Q[1]

        return detF

        
    # start = where to begin in data
    def next_state(self, data, start, end, a, v, P, K, Fi):
        steady = False
        for i in range(start, end):
            yield self.update_Kalman((data[0][i], data[1][i]), a, v, P, K, Fi)


    def llh(self, t1,t2,t3, datarange=200):
        eps = BiLL.eps
        self.Q[0] = t1**2+eps 
        self.Q[1] = (abs(t1)+eps)*t2
        self.Q[2] = t3**2+eps+t2**2 

        a = [self.data[0][0], self.data[1][0]]
        P = [self.Q[0]+1., self.Q[1], self.Q[2]+1.]
        K = [0.]*3
        Fi = [1., 0., 1.]
        v = [0.]*2
        T1, T2 = 0., 0.
        
        steady = False
        for detF in self.next_state(self.data, 1, datarange, a, v, P, K, Fi):
            T1 += v[0]*Fi[0]*v[0] + 2*v[0]*Fi[1]*v[1] + v[1]*Fi[2]*v[1]
            T2 += log(detF)

        if T1 == 0: return T2
        return (datarange-1)*log(T1) + T2


    def updateAll(self, psi):
        eps = LLB.eps
        [t1, t2, t3] = psi
        self.Q[0] = t1**2+eps 
        self.Q[1] = (abs(t1)+eps)*t2
        self.Q[2] = t3**2+eps+t2**2 
        data = self.data
        self.a[0] = a = [self.data[0][0], self.data[1][0]]
        self.P[0] = P = [self.Q[0]+1., self.Q[1], self.Q[2]+1.]
        K = [0.]*3
        Fi = [1., 0., 1.]
        v = [0.]*2
        epsilon = 0.
        start = 0
        end = self.datalength
        for i, detF in enumerate(self.next_state(data, start, end, a, v, P, K, Fi)):
            self.a[i+start] = [a[0], a[1]]
            self.P[i+start] = [(P[0]+1), P[1], (P[2]+1)]
            epsilon += v[0]*Fi[0]*v[0] + 2*v[0]*Fi[1]*v[1] +  v[1]*Fi[2]*v[1]
        epsilon /= self.datalength
        self.epsilon = epsilon
        for i in range(len(self.P)):
            if self.P[i]:
                self.P[i] = [u*epsilon for u in self.P[i]]
        for i in range(len(self.Q)):
            self.Q[i] *= epsilon
 


    def state(self, ts_idx, i):
        if ts_idx != 0 and ts_idx != 1:
            print("Invalid time series index: %d" % ts_idx)
            return 0.0
        if i < 0 or i > len(self.a):
            print("Invalid state index: %d" % i)
            return 0.0
        return self.a[i][ts_idx]


    def var(self, ts_idx, i):
        if ts_idx != 0 and ts_idx != 1:
            print("Invalid time series index: %d" % ts_idx)
            return 0.0
        if i < 0 or i > len(self.P):
            print("Invalid state index: %d" % i)
            return 0.0
        if i < self.datalength:
            return self.P[i][ts_idx]+ self.Q[ts_idx]          
        else:
            return self.P[i][ts_idx]


    def datalen(self):
        return self.datalength


class LLB(object):
    """ Multivariate Local Level """
        
    eps = 1e-12

    def __init__(self, data, data_len, forecast_len=FORECAST):
        if len(data)==0 or data_len==0: raise ValueError
        self.data = data
        self.data_len = data_len
        self.forecast_len = forecast_len
        self.Q = [None]*3
        self.P = [None]*(data_len+self.forecast_len) # variances of predictions (not filtered states)
        self.a = [None]*len(self.P) # filter states
        self.a[0] = [data[0][0], data[1][0]]
        self.scale = .1
        psi = vec([1./self.scale, .5/self.scale, 1./self.scale])
        dfpmin(lambda x, y, z: self.llh(x, y, z, len(data)), psi)
        self.updateAll(psi)
    

    @classmethod
    def instance(cls, var1, var2, data_len, forecast_len=FORECAST):
        cls = LLB(data=(var1, var2), data_len=data_len, forecast_len=forecast_len)
        return cls

    @classmethod
    def least_num_data(cls):
        return 2

    @classmethod
    def first_forecast_index(cls):
        return 1 
    

    def update_Kalman(self, y, a, v, P, K, Fi):
        detP = P[0]*P[2] - P[1]*P[1]
        trP = P[0] + P[2]
        detF = detP + trP + 1.
        
        Fi[0] = old_div((P[2]+1.),detF)
        Fi[1] = old_div(-P[1],detF)
        Fi[2] = old_div((P[0]+1.),detF)

        K[0] = old_div((P[0]+detP),detF)
        K[1] = -Fi[1] # = P[1]/detF
        K[2] = old_div((P[2]+detP),detF)

        v[0] = y[0] - a[0]
        v[1] = y[1] - a[1]

        a[0] += K[0]*v[0] + K[1]*v[1]
        a[1] += K[1]*v[0] + K[2]*v[1]

        PP1 = K[0] + self.Q[0]
        PP2 = K[1] + self.Q[1]
        PP3 = K[2] + self.Q[2]
        PP = abs(PP1-P[0]) + abs(PP2-P[1]) + abs(PP3-P[2])
        if PP < 1.0e-5: steady = True
        else: steady = False
        P[0], P[1], P[2] = PP1, PP2, PP3

        return detF, steady


    def update_steady(self, y, a, v, K):
        v[0] = y[0] - a[0]
        v[1] = y[1] - a[1]
        a[0] += K[0]*v[0] + K[1]*v[1]
        a[1] += K[1]*v[0] + K[2]*v[1]
        
        
    # start = where to begin in data
    def next_state(self, data, start, a, v, P, K, Fi):
        steady = False
        for i in range(start, self.data_len):
            if not steady:
                detF, steady = self.update_Kalman((data[0][i], data[1][i]), a, v, P, K, Fi)
            else: self.update_steady((data[0][i], data[1][i]), a, v, K)
            yield detF


    def llh(self, t1,t2,t3, datarange=200):
        eps = LLB.eps
        self.Q[0] = t1**2+eps 
        self.Q[1] = (abs(t1)+eps)*t2
        self.Q[2] = t3**2+eps+t2**2 

        a = [self.data[0][0], self.data[1][0]]
        P = [self.Q[0]+1., self.Q[1], self.Q[2]+1.]
        K = [0.]*3
        Fi = [1., 0., 1.]
        v = [0.]*2
        t1, t2 = 0., 0.
        
        steady = False
        for detF in self.next_state(self.data, 1, a, v, P, K, Fi):
            t1 += v[0]*Fi[0]*v[0] + 2*v[0]*Fi[1]*v[1] + v[1]*Fi[2]*v[1]
            t2 += log(detF)

        if t1 == 0: return old_div(t2,2)
        return (self.data_len-1)*log(t1) + old_div(t2,2)


    def updateAll(self, psi):
        eps = LLB.eps
        [t1, t2, t3] = psi
        self.Q[0] = t1**2+eps 
        self.Q[1] = (abs(t1)+eps)*t2
        self.Q[2] = t3**2+eps+t2**2 
        data = self.data
        self.a[0] = a = [self.data[0][0], self.data[1][0]]
        self.P[0] = P = [self.Q[0]+1., self.Q[1], self.Q[2]+1.]
        K = [0.]*3
        Fi = [1., 0., 1.]
        v = [0.]*2
        epsilon = 0.
        start = 0
        for i, detF in enumerate(self.next_state(data, start, a, v, P, K, Fi)):
            self.a[i+start] = [a[0], a[1]]
            self.P[i+start] = [(P[0]+1), P[1], (P[2]+1)]
            epsilon += v[0]*Fi[0]*v[0] + 2*v[0]*Fi[1]*v[1] +  v[1]*Fi[2]*v[1]
        epsilon /= 2.*self.data_len
        for i in range(len(self.P)):
            if self.P[i]:
                for j in range(len(self.P[i])):
                    self.P[i][j] *= epsilon
 

    def predict(self, var, start=30):
        if var != 0 and var != 1: raise ValueError
        data = self.data
        n = self.data_len 
        corvar = 1-var
        self.fc = [None]*n
        self.VAR = [None]*n
        for i in range(start, n):
            COV = self.P[i] 
            if COV[2*corvar] != 0:
                SIGMA = old_div(COV[1],COV[2*corvar])
                self.VAR[i] = COV[2*var] - old_div(COV[1]*COV[1],COV[2*corvar])
            else:
                SIGMA = 0
                self.VAR[i] = COV[2*var]
            if data[corvar][i] == None:
                self.fc[i] = self.a[i-1][var]
            else:
                self.fc[i] = self.a[i-1][var] + SIGMA*(data[corvar][i] - self.a[i-1][corvar])


    def variance(self, i):
        return self.VAR[i]


    def datalen(self):
        return self.data_len


class LLBmv(LLB):
    """ Multivariate Local Level for data with missing values """

    def __init__(self, data, data_len, forecast_len=FORECAST):
        LLB.__init__(self, data, data_len, forecast_len=FORECAST)


    @classmethod
    def instance(cls, var1, var2, data_len, forecast_len=FORECAST):
        cls = LLBmv(data=(var1, var2), data_len=data_len, forecast_len=forecast_len)
        return cls

    def update_Kalman(self, y, a, v, P, K, Fi):
        detP = P[0]*P[2] - P[1]*P[1]
        trP = P[0] + P[2]
        detF = detP + trP + 1.

        Fi[0] = old_div((P[2]+1.),detF)
        Fi[1] = old_div(-P[1],detF)
        Fi[2] = old_div((P[0]+1.),detF)

        K[0] = old_div((P[0]+detP),detF)
        K[1] = -Fi[1] # = P[1]/detF
        K[2] = old_div((P[2]+detP),detF)

        if y[0] == None: 
            v[0] = 0
            P[0] += self.Q[0]
        else:
            v[0] = y[0] - a[0]
            a[0] += K[0]*v[0] + K[1]*v[1]
            P[0] = K[0] + self.Q[0]
        if y[1] == None: 
            v[1] = 0
            P[2] += self.Q[2]
        else:
            v[1] = y[1] - a[1]
            a[1] += K[1]*v[0] + K[2]*v[1]
            P[2] = K[2] + self.Q[2]
        P[1] = K[1] + self.Q[1]

        return detF

       
    # start = where to begin in data
    def next_state(self, data, start, a, v, P, K, Fi):
        steady = False
        for i in range(start, self.data_len):
            yield self.update_Kalman((data[0][i], data[1][i]), a, v, P, K, Fi)



ALGORITHMS = {'LL': LL,
        'LLP': LLP, 
        'LLP1': LLP1,
        'LLP2': LLP2, 
        'LLP5': LLP5, 
        'LLT': LLT, 
        'LLB': LLB, 
        'LLBmv': LLBmv, 
        'BiLL': BiLL,   
        'BiLLmv': BiLLmv   
        }


#####################  Unit tests ##########################
import csv

class SPTest(unittest.TestCase):
    
    def testLongestStretch(self):
        data = [1, 2, 3, 4, None, 5, 6, 7, None, None, 8, 9, 1, 2, 3, None]
        self.assertEqual(findLongestContinuousStretch(data), [10, 15]) 

    def testPeriod(self):
        data = list(range(7)) + [None,None,None] + list(range(7))*5
        self.assertEqual(findPeriod2(data), 7)


    def testCorrelogram(self):
        data = list(range(10))
        expect = [1.0, 0.7000000000000001, 0.4121212121212121, 0.1484848484848485, -0.0787878787878788, -0.2575757575757576, -0.3757575757575758, -0.42121212121212126, -0.38181818181818183, -0.24545454545454548]
        cor = [x for x in correlogram0(data, 0, len(data))]
        self.assertEqual(cor, expect)




#class LLP3():
#    ''' LLP3 follows LL for a while until it detects a period in the data, then it switches to LLP using that period.
#    '''
#    def __init__(self, data, period=-1, forecast_len=FORECAST,missingValued=False):
#        if len(data) < self.least_num_data():
#            raise ValueError("too few data points: %d" %len(data))
#
#        self.data = data
#        self.forecast_len = forecast_len
#        self.fc = [None]*(len(data)+forecast_len) # filtered states
#        self.p = [None]*len(self.fc) # variances of predictions (not filtered states)

#        self.model = self.model1 = LL(data,forecast_len) # starts with LL
#        self.period = period
#
#        for i in range(self.model1.first_forecast_index(),len(self.fc)):
#            self.update(i)
#
#
#    def first_forecast_index(self):
#        return self.model1.first_forecast_index()
#
#
#    def least_num_data(self):
#        return LL.least_num_data()
#
#    # User needs to ensure k < len(self.fc)
#    def update(self,k):
#        data = self.data
#
#        period = findPeriod(data[:k])
#        if period != -1 and period != self.period and k > period*LL.least_num_data():
#            try:
#                self.model2 = LLP(data,period,self.forecast_len)
#                self.model = self.model2 
#                self.period = self.model2.period
#            except ValueError:
#                pass
#
#        if self.model.fc[k] != None:
#            self.fc[k] = self.model.fc[k]
#            self.p[k] = self.model.p[k]
#        else:
#            self.fc[k] = self.model1.fc[k]
#            self.p[k] = self.model1.p[k]
#
#
#    def variance(self,i):
#        if i >= len(self.p): raise ValueError("variance index out of bound")
#        return self.p[i]
#
#
#    def predict(self,length):
#        if length <= self.forecast_len: return
#        self.model.predict(length)
#        oldlen = len(self.fc)
#        ext = length - self.forecast_len
#        self.fc.extend([None]*ext)
#        self.p.extend([None]*ext)
#        for i in range(ext):
#            self.update(oldlen+i)
#
#        
#    def datalen(self):
#        return self.model.datalen()
#
#
#class LLP4:
#    ''' LLP4 combines LL and LLP. If there's no periodicity, it uses only LL. Otherwise it uses both LL and LLP
#    and outputs the average of the two predictions.
#    '''
#    def __init__(self, data, period=-1, forecast_len=FORECAST,missingValued=False):
#        if len(data) < self.least_num_data():
#            raise ValueError("too few data points: %d" %len(data))
#
#        self.data = data
#        self.forecast_len = forecast_len
#        self.fc = [None]*(len(data)+forecast_len) # filtered states
#        self.p = [None]*len(self.fc) # variances of predictions (not filtered states)
#
#        self.model1 = LL(data,forecast_len) # starts with LL
#        self.period = period
#        self.model2 = None
#
#        for i in range(self.model1.first_forecast_index(),len(self.fc)):
#            self.update(i)
#
#
#    def first_forecast_index(self):
#        return self.model1.first_forecast_index()
#
#
#    def least_num_data(self):
#        return LL.least_num_data()
#
#    # User needs to ensure k < len(self.fc)
#    def update(self,k):
#        data = self.data
#
#        period = findPeriod(data[:k])
#        if period != -1 and period != self.period and k > period*LL.least_num_data():
#            try:
#                self.model2 = LLP(data,period,self.forecast_len)
#                self.period = self.model2.period
#            except ValueError:
#                pass
#
#        if self.model2 == None or self.model2.p[k]==None or self.model2.fc[k]==None:
#            self.p[k] = self.model1.p[k]
#            self.fc[k] = self.model1.fc[k]
#        elif self.model1.p[k]==0 and self.model2 != None and self.model2.p[k]==0:
#            self.p[k] = 0
#            self.fc[k] = (self.model1.fc[k]+self.model2.fc[k])/2.
#        else:
#            K = self.model1.p[k]/(self.model1.p[k]+self.model2.p[k])
#            self.fc[k] = self.model1.fc[k] + K*(self.model2.fc[k]-self.model1.fc[k])
#            self.p[k] = self.model1.p[k]
#
#
#    def variance(self,i):
#        if i >= len(self.p): raise ValueError("variance index out of bound")
#        return self.p[i]
#
#
#    def predict(self,length):
#        if length <= self.forecast_len: return
#        self.model1.predict(length)
#        self.model2.predict(length)
#        oldlen = len(self.fc)
#        ext = length - self.forecast_len
#        self.fc.extend([None]*ext)
#        self.p.extend([None]*ext)
#        for i in range(ext):
#            self.update(oldlen+i)
#
#        
#    def datalen(self):
#        return self.model1.datalen()
#




# def computeStats(model):
#     n = len(model.data)

#     model.r = [None]*n # autocorrelation (Commandeur-Koopman, p.90)
#     model.Q = [None]*n # Box-Ljung statistic (Commandeur-Koopman, p.90)
#     model.H = [None]*n # Homoscedasticity (Commandeur-Koopman, p.92)

#     nf = n - 1.
#     e_mean = sum(model.e)/nf
#     model.var = reduce(lambda x,y: x + (y-e_mean)**2,model.e[1:],0.0) 
    
#     for k in range(1,len(model.r)):
#         model.r[k] = reduce(lambda x,y: x + (y[0]-e_mean)*(y[1]-e_mean), izip(model.e,model.e[k:]), 0.0)/model.var
        
#     for k in range(1,len(model.Q)):
#         model.Q[k] = n*(n+2)*reduce(lambda x,y: x + y[1]**2/(n-y[0]-1.), enumerate(model.r[1:k+1]), 0.0)
#             # explain: n-y[0]-1. we subtract 1 because we start from the index 1 term of model.r while enumerate starts from 0.
            
#     esq = [e**2 for e in model.e]
#     d = 1
#     for h in range(1,len(model.H)):
#         denom = sum(esq[d:d+h])
#         if denom == 0: model.H[h] = 100000.
#         else: model.H[h] = sum(esq[n-h:])/denom
                
#     m2 = model.var/nf
#     m3 = reduce(lambda x,y: x + (y-e_mean)**3, model.e[1:], 0.0)/nf
#     m4 = reduce(lambda x,y: x + (y-e_mean)**4, model.e[1:], 0.0)/nf
#     model.S = m3/m2**(3.0/2)
#     model.K = m4/(m2**2)
#     model.N = nf*(model.S**2/6. + (model.K-3)**2/24.)
                
 
# def independence(model, k):
#     critical_val = Chisqdist(k-model.w+1).invcdf(.95)
#     if model.Q[k] < critical_val: 
#         print("Q = %f, critical = %f" %(model.Q[k],critical_val))
#         return True
#     else:
#         print("independence fails: Q[%d] = %f >= critical_val = %f" %(k,model.Q[k],critical_val))
#     return False

# def homoscedasticity(model):
#     k = int(round((len(model.data) - 1)/3.,0))
#     critical_val = Fdist(k,k).invcdf(.975)
#     if model.H[k] < critical_val: 
#         print("H = %f, critical_val = %f" %(model.H[k],critical_val))
#         return True
#     else:
#         print("homoscedasticity fails: H[%d] = %f >= critical_val = %f" %(k,model.H[k],critical_val))
#     return False
        
# def normality(model):
#     if model.N < normality_critical_val: 
#         print("N = %f, critical_val = %f" %(model.N,normality_critical_val))
#         return True
#     else:
#         print("normality fails: N = %f >= critical_val = %f" %(model.N,normality_critical_val))
#     return False

# def box_ljung (model,k):
#     if k >= len(model.Q):
#         print("Box-Ljung statistic only computed for 1 <= k <= %d" %len(model.Q))
#         raise ValueError
#     return model.Q[k]
