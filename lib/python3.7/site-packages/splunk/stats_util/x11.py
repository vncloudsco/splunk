from __future__ import absolute_import
from __future__ import division
from past.utils import old_div
from builtins import zip
from builtins import range
from builtins import object

import math
import operator

from splunk.stats_util.ma import *
from splunk.stats_util.ts import *
# this should not use * but do not have bandwidth to fix this
#from splunk.stats_util.ma import Weighted, Musgrave, Simple, Henderson, TwoByN
#from splunk.stats_util.ts import TS, subtract, divide


def neighborhood(iterable):
    iterator = iter(iterable)
    prev = None
    item = next(iterator)  # throws StopIteration if empty.
    for item_item in iterator:
        yield (prev,item,item_item)
        prev = item
        item = item_item
        yield (prev, item, None)

def group(lst, n):
    """group([0,3,4,10,2,3], 2) => [(0,3), (4,10), (2,3)]

    Group a list into consecutive n-tuples. Incomplete tuples are
    discarded e.g.

    >>> group(range(10), 3)
    [(0, 1, 2), (3, 4, 5), (6, 7, 8)]
    """
    return zip(*[lst[i::n] for i in range(n)])

class X11(object):
    def __init__ (self, original, type):
        """ original = original TS object, type = ADD or MULT """
        self.original = original
        self.type = type
        self.lambda_L = 1.5
        self.lambda_U = 2.5

        self.std1 = []
        self.std2 = []
        self.std3 = []
        self.std4 = []

        self.steps = [TS(len(self.original)) for i in range(29)]

        [self.step1, self.step2, self.step3a, self.step3b, self.step3c, self.step3d,
        self.step3e, self.step3f, self.step4a, self.step4b, self.step4c, self.step5,
        self.step6a, self.step6b, self.step6c, self.step6d, self.step6e, self.step7,
        self.step8a, self.step8b, self.step8c, self.step8d, self.step8e, self.step8f,
        self.step9a, self.step9b, self.step9c, self.step10, self.step11] = self.steps

        self.stepnames = ["step1", "step2", "step3a", "step3b", "step3c", "step3d",
                          "step3e", "step3f", "step4a", "step4b", "step4c", "step5",
                          "step6a", "step6b", "step6c", "step6d", "step6e", "step7",
                          "step8a", "step8b", "step8c", "step8d", "step8e", "step8f",
                          "step9a", "step9b", "step9c", "step10", "step11"]

        self.std1 = []
        self.std2 = []

        if type == "ADD":
            self.op = subtract
            self.mean = 0.0
        elif type == "MULT":
            self.op = divide
            self.mean = 100.0
        else:
            raise ValueError

        self.period = original.period
        if self.period%2:
            self.step1MA = Simple(self.period)
            self.step6MA = Henderson(self.period)
        else:
            self.step1MA = TwoByN(self.period)
            self.step6MA = Henderson(self.period+1)

        v3 = [0]*(4*self.period+1)
        v3[0] = v3[4*self.period] = 1.0/9
        v3[self.period] = v3[3*self.period] = 2.0/9
        v3[2*self.period] = 3.0/9
        self.step3MA = Weighted(v3, 2*self.period)

        v5 = [0]*(6*self.period+1)
        v5[0] = v5[6*self.period] = 1.0/15
        v5[self.period] = v5[5*self.period] = 2.0/15
        v5[2*self.period] = v5[3*self.period] = v5[4*self.period] = 3.0/15
        self.step7MA = Weighted(v5, 3*self.period)

    def do_step1 (self):
        self.step1MA.apply(self.original, self.step1)

    def do_step2 (self):
        self.original.remove(self.step1, self.op, True, self.step2)

    def do_step3a (self):
        self.step3MA.apply(self.step2, self.step3a)

        # Compute beginning values
        for i in range(self.period):
            if i < old_div(self.period,2):
                self.step3a[i] = 0.0
                self.step3a[i+self.period] = \
                (self.step2[i+self.period]*11.0 + self.step2[i+(2*self.period)]*11.0 + self.step2[i+(3*self.period)]*5.0)/27.0
                self.step3a[i+(2*self.period)] = (self.step2[i+self.period]*7.0 + self.step2[i+(2*self.period)]*10.0 + \
                                          self.step2[i+(3*self.period)]*7.0 + self.step2[i+(4*self.period)]*3.0)/27.0
            else:
                self.step3a[i] = (self.step2[i]*11.0 + self.step2[i+self.period]*11.0 + self.step2[i+(2*self.period)]*5.0)/27.0
                self.step3a[i+self.period] = \
                (self.step2[i]*7.0 + self.step2[i+self.period]*10.0 + self.step2[i+(2*self.period)]*7.0 + self.step2[i+(3*self.period)]*3.0)/27.0

        # Compute ending values
        for i in range(len(self.step2)-1, len(self.step2)-self.period-1, -1):
            if i >= len(self.step2) - old_div(self.period,2):
                self.step3a[i] = 0.0
                self.step3a[i-self.period] = (self.step2[i-self.period]*11.0 + self.step2[i-(2*self.period)]*11.0 + self.step2[i-(3*self.period)]*5.0)/27.0
                self.step3a[i-(2*self.period)] = (self.step2[i-self.period]*7.0 + self.step2[i-(2*self.period)]*10.0 + \
                                                  self.step2[i-(3*self.period)]*7.0 + self.step2[i-(4*self.period)]*3.0)/27.0
            else:
                self.step3a[i] = (self.step2[i]*11.0 + self.step2[i-self.period]*11.0 + self.step2[i-(2*self.period)]*5.0)/27.0;
                self.step3a[i-self.period] = \
                (self.step2[i]*7.0 + self.step2[i-self.period]*10.0 + self.step2[i-(2*self.period)]*7.0 + self.step2[i-(3*self.period)]*3.0)/27.0;

    def do_step3b (self):
        self.step1MA.apply(self.step3a, self.step3b)
        # Compute beginning and ending values
        half_period = old_div(self.period,2)
        begin_val = self.step3b[self.period]
        end_val = self.step3b[-self.period-1]

        self.step3b[half_period:self.period] = [begin_val]*(self.period-half_period)
        self.step3b[-self.period:-half_period+1] = [end_val]*(self.period-half_period+1)
        # Note: if self.period is odd, it's not true that  self.period-half_period = half_period

    def do_step3c (self):
        self.step3a.remove (self.step3b, self.op, True, self.step3c)

    def do_step3d (self):
        self.step2.remove (self.step3c, self.op, False, self.step3d)

    def computeStd1 (self, ts, std_lst):
        """ ts is a TS object. result is a list of float's """
        first_full_period = ts.firstFullPeriod()
        last_full_period = ts.lastFullPeriod()

        std_lst.extend ([0.0]*ts.num_periods)

        if first_full_period+4 <= last_full_period:
            m_period = first_full_period
            num_terms = 5*self.period
            range_start = max(int(ts.startIdx + (self.period-ts.periodStart) + (m_period-1)*self.period), 0)
            range_end = min(int(range_start + 5*self.period), ts.endIdx)

            while m_period+4 <= last_full_period:
                std = 0.0
                std += sum ([(val-self.mean)**2 for val in ts[int(range_start):int(range_end)]], 0.0)
                std_lst[m_period+2] = math.sqrt (old_div(std,num_terms))
                m_period += 1
                range_start += self.period
                if range_start >= ts.endIdx: break
                range_end += self.period
                if range_end > ts.endIdx:
                    range_end = ts.endIdx

        # compute std for the first 2 or 3 periods
        std = 0.0
        num_terms = (5*self.period) + ((self.period-ts.periodStart)%self.period)
        std += sum ([(val-self.mean)**2 for val in ts[int(ts.startIdx) : int(ts.startIdx+num_terms)]], 0.0)
        std = math.sqrt(old_div(std,num_terms))

        std_lst[:(first_full_period+2)] = [std]*(first_full_period+2)

        # compute std for the last 2 or 3 periods
        std = 0.0
        num_terms = (5*self.period) + ((len(ts) + ts.periodStart)%self.period)
        std += sum ([(val-self.mean)**2 for val in ts[int(ts.endIdx-num_terms) : int(ts.endIdx)]], 0.0)
        std = math.sqrt (old_div(std,num_terms))
        std_lst[-ts.num_periods+last_full_period-1:] = [std]*(ts.num_periods-last_full_period+1)

    def computeStd2 (self, ts, std_lst1, std_lst2):
        first_full_period = ts.firstFullPeriod()
        last_full_period = ts.lastFullPeriod()

        std_lst2.extend ([0.0]*ts.num_periods)

        if first_full_period+4 <= last_full_period:
            m_period = first_full_period
            range_start = max(int(ts.startIdx + self.period - ts.periodStart + (m_period-1)*self.period), 0)
            range_end = min(int(range_start + 5*self.period), ts.endIdx)

            while m_period+4 <= last_full_period:
                std = 0.0
                num_terms = 0
                sigma = self.lambda_U * std_lst1[m_period+2]
                for i in range (int(range_start), int(range_end)):
                    dev = ts[i] - self.mean
                    if dev >= sigma or dev <= -sigma:
                        continue
                    std += dev**2
                    num_terms += 1
                if num_terms == 0: std_lst2[m_period+2] = 0
                else: std_lst2[m_period+2] = math.sqrt (old_div(std,num_terms))
                m_period += 1
                range_start += self.period
                range_end += self.period
                if range_end > ts.endIdx:
                    range_end = ts.endIdx

        # compute std for the first 2 or 3 periods
        std = 0.0
        sigma = self.lambda_U * std_lst1[0]
        num_terms = 0
        max_num_terms = (5*self.period) + (self.period-ts.periodStart)%self.period
        for i in range (int(ts.startIdx), int(ts.startIdx+max_num_terms)):
            dev = ts[i] - self.mean
            if dev >= sigma or dev <= -sigma:
                continue
            std += dev**2
            num_terms += 1
        if num_terms==0: std_lst2[:first_full_period+2] = [0.0]*(first_full_period+2)
        else:
            std = math.sqrt (old_div(std,num_terms))
            std_lst2[:first_full_period+2] = [std]*(first_full_period+2)

        # compute std for the last 2 or 3 periods
        std = 0.0
        sigma = self.lambda_U * std_lst1[len(self.std1)-1]
        num_terms = 0
        max_num_terms = (5*self.period) + (len(ts)+ts.periodStart)%self.period
        for i in range (int(ts.endIdx-max_num_terms), int(ts.endIdx)):
            dev = ts[i] - self.mean
            if dev >= sigma or dev <= -sigma:
                continue
            std += dev**2
            num_terms += 1
        if num_terms==0: std_lst2[-ts.num_periods+last_full_period-1:] = [0.0]*int(ts.num_periods-last_full_period+1)
        else:
            std = math.sqrt (old_div(std,num_terms))
            std_lst2[-ts.num_periods+last_full_period-1:] = [std]*int(ts.num_periods-last_full_period+1)

    def do_step3e (self):
        self.computeStd1 (self.step3d, self.std1)
        self.computeStd2 (self.step3d, self.std1, self.std2)

        self.step3e.resize (len(self.step3d), self.mean)
        self.step3e.setPeriod (self.step3d.period)
        self.step3e.setPeriodStart (self.step3d.periodStart)
        self.step3e.setStartIdx (self.step3d.startIdx)
        self.step3e.setEndIdx (self.step3d.endIdx)

        self.step3e[:int(self.step3e.startIdx)] = [0.0]*int(self.step3e.startIdx)
        self.step3e[int(self.step3e.endIdx):] = [0.0]*int(len(self.step3e)-self.step3e.endIdx)

        for i in range (self.step3e.num_periods):
            sigma_l = self.lambda_L * self.std2[i]
            sigma_u = self.lambda_U * self.std2[i]
            sigma_d = sigma_u - sigma_l

            for j in range (int(self.step3d.begin(i)), int(self.step3d.end(i))):
                dev = abs(self.step3d[j] - self.mean)
                if dev > sigma_l and dev < sigma_u:
                    self.step3e[j] = 100.0*(old_div((sigma_u-dev),sigma_d))
                else:
                    self.step3e[j] = 100.0

    def do_step3f (self):
        self.step3f.resize (len(self.step2), self.mean)
        self.step3f.setPeriod (self.step2.period)
        self.step3f.setPeriodStart (self.step2.periodStart)
        self.step3f.setStartIdx (self.step2.startIdx)
        self.step3f.setEndIdx (self.step2.endIdx)

        past_nonextremes = []
        future_nonextremes = []
        for i in range (self.step2.num_periods):
            for j in range (self.step3e.begin(i), self.step3e.end(i)):
                if self.step3e[j] == 100.0:
                    self.step3f[j] = self.step2[j]
                    continue

                past_count = 0
                future_count = 0
                # search for 4 nearest non-extreme values
                for k in range (self.step3e.num_periods):
                    if k <= i:
                        u = j - (k*self.period)
                        if u >= self.step3e.begin(i-k) and self.step3e[u] == 100.0:
                            past_nonextremes.append (self.step2[j-(k*self.period)])

                    if i+k < self.step2.num_periods:
                        u = j + (k*self.period)
                        if u < self.step3e.end(i+k) and self.step3e[u] == 100.0:
                            future_nonextremes.append (self.step2[j+(k*self.period)])

                    if len(past_nonextremes) >= 2 and len(future_nonextremes) >= 2:
                        break

                # modify extreme values
                weight = self.step3e[j]/100.0
                new_val = self.step2[j]*weight

                if len(past_nonextremes) < 2:
                    if len(future_nonextremes) + len(past_nonextremes) >= 4:
                        future_num = 4 - len(past_nonextremes)
                        num_terms = 4
                    else:
                        future_num = len(future_nonextremes)
                        num_terms = len(past_nonextremes) + len(future_nonextremes)

                    new_val += sum (past_nonextremes, 0.0)
                    new_val += sum (future_nonextremes[:future_num], 0.0)

                elif len(future_nonextremes) < 2:
                    if len(future_nonextremes) + len(past_nonextremes) >= 4:
                        past_num = 4 - len(future_nonextremes)
                        num_terms = 4
                    else:
                        past_num = len(past_nonextremes)
                        num_terms = len(future_nonextremes) + len(past_nonextremes)

                    new_val += sum (past_nonextremes[:past_num], 0.0)
                    new_val += sum (future_nonextremes, 0.0)

                else:
                    num_terms = 4
                    new_val += sum (past_nonextremes[:2], 0.0)
                    new_val += sum (future_nonextremes[:2], 0.0)

                new_val /= (num_terms+weight)
                self.step3f[j] = new_val
                past_nonextremes = []
                future_nonextremes = []

    def do_step4a (self):
        # typing shortcuts
        step4a = self.step4a
        step3f = self.step3f
        period = self.period

        self.step3MA.apply (step3f, step4a)

        # compute beginning values
        for i in range (period):
            if i < old_div(period,2):
                step4a[i] = 0.0
                step4a[i+period] = (step3f[i+period]*11.0 + step3f[i+2*period]*11.0 + step3f[i+3*period]*5.0)/27.0
                step4a[i+2*period] = (step3f[i+period]*7.0 + step3f[i+2*period]*10.0 + \
                                      step3f[i+3*period]*7.0 + step3f[i+4*period]*3.0)/27.0
            else:
                step4a[i] = (step3f[i]*11.0 + step3f[i+period]*11.0 + step3f[i+2*period]*5.0)/27.0
                step4a[i+period] = (step3f[i]*7.0 + step3f[i+period]*10.0 + step3f[i+2*period]*7.0 + step3f[i+3*period]*3.0)/27.0

        # compute ending values
        for i in range (len(step3f)-1, len(step3f)-period-1, -1):
            if i >= len(step3f) - old_div(period,2):
                step4a[i] = 0.0
                step4a[i-period] = (step3f[i-period]*11.0 + step3f[i-2*period]*11.0 + step3f[i-3*period]*5.0)/27.0
                step4a[i-(2*period)] = (step3f[i-period]*7.0 + step3f[i-2*period]*10.0 + \
                                         step3f[i-3*period]*7.0 + step3f[i-4*period]*3.0)/27.0
            else:
                step4a[i] = (step3f[i]*11.0 + step3f[i-period]*11.0 + step3f[i-2*period]*5.0)/27.0
                step4a[i-period] = (step3f[i]*7.0 + step3f[i-period]*10.0 + step3f[i-2*period]*7.0 + step3f[i-3*period]*3.0)/27.0

    def do_step4b (self):
        step4a = self.step4a
        step4b = self.step4b
        period = self.period

        self.step1MA.apply (step4a, step4b)

        # compute beginning and ending values
        half_period = old_div(period,2)
        begin_val = step4b[period]
        end_val = step4b[-period-1]

        step4b[half_period:period] = [begin_val]*(period-half_period)
        step4b[-period:-half_period+1] = [end_val]*(period-half_period+1)

    def do_step4c (self):
        step4a = self.step4a
        step4b = self.step4b
        step4c = self.step4c
        period = self.period
        half_period = old_div(period,2)
        original = self.original

        step4a.remove (step4b, self.op, True, step4c)

        step4c.setPeriodStart (original.periodStart)
        step4c.setStartIdx (original.startIdx)
        step4c.setEndIdx (original.endIdx)

        # set period/2 beginning values
        step4c[:half_period] = step4c[period:half_period+period]
        # set period/2 ending values
        step4c[-half_period:] = step4c[-half_period-period:-period]

    def do_step5 (self):
        self.original.remove (self.step4c, self.op, True, self.step5)

    def do_step6a (self):
        self.step6MA.apply (self.step5, self.step6a)

    def do_step6b (self):
        self.step5.remove (self.step6a, self.op, True, self.step6b)

    def do_step6c (self):
        step6a = self.step6a
        step6c = self.step6c

        step6c.setPeriod (step6a.period)
        step6c.setPeriodStart (step6a.periodStart)
        step6c.setStartIdx (step6a.startIdx+1)
        step6c.setEndIdx (step6a.endIdx)

        for [a, c] in zip (range(step6a.begin(0), step6a.end(step6a.num_periods-1)),\
                      range(step6c.begin(0), step6c.end(step6c.num_periods-1))):
            step6c[c] = abs(self.op (step6a[a+1], step6a[a]) - 100.0)

    def do_step6d (self):
        step6b = self.step6b
        step6c = self.step6c
        step6d = self.step6d

        step6d.setPeriod (step6b.period)
        step6d.setPeriodStart (step6b.periodStart)
        step6d.setStartIdx (step6b.startIdx+1)
        step6d.setEndIdx (step6b.endIdx)

        for [b, d] in zip(range(step6b.begin(0), step6b.end(step6b.num_periods-1)), \
                     range(step6d.begin(0), step6d.end(step6d.num_periods-1))):
            step6d[d] = abs(self.op (step6b[b+1], step6b[b]) - 100.0)

        # calculate I/C ratio
        C = sum (step6c[step6c.begin(0):step6c.end(step6c.num_periods-1)], 0.0)
        I = sum (step6d[step6d.begin(0):step6d.end(step6d.num_periods-1)], 0.0)

        if I == 0:
#            print("ERROR (step6d): I = 0")
            self.IC_ratio = 0
        else: self.IC_ratio = old_div(I,C)

    def do_step6e (self):
        # set asymmetric moving average
        if self.IC_ratio <= 1:
            if self.period > 3:
                self.step6Asym = Musgrave (self.period-3, 1.0)
            else:
                self.step6Asym = Musgrave (self.period, 1.0)
        else:
            self.step6Asym = Musgrave (len(self.step6MA), 3.5)

        self.step6Asym.apply (self.step5, self.step6e)

    def do_step7 (self):
        self.original.remove (self.step6e, self.op, True, self.step7)

    def do_step8a (self):
        step7 = self.step7
        step8a = self.step8a
        period = self.period

        self.step7MA.apply (step7, step8a)

        # compute beginning values
        for i in range(period):
            step8a[i] = (step7[i]*17.0 + step7[i+period]*17.0 + step7[i+(2*period)]*17.0 + \
                          step7[i+(3*period)]*9.0)/60.0
            step8a[i+period] = (step7[i]*15.0 + step7[i+period]*15.0 + step7[i+(2*period)]*15.0 + \
                                 step7[i+(3*period)]*11.0 + step7[i+(4*period)]*4.0)/60.0
            step8a[i+(2*period)] = (step7[i]*9.0 + step7[i+period]*13.0 + step7[i+(2*period)]*13.0 + \
                                     step7[i+(3*period)]*13.0 + step7[i+(4*period)]*8.0 + step7[i+(5*period)]*4.0)/60.0

        # compute ending values
        for i in range(len(step7)-1, len(step7)-period-1, -1):
            step8a[i] = (step7[i]*17.0 + step7[i-period]*17.0 + step7[i-(2*period)]*17.0 + \
                         step7[i-(3*period)]*9.0)/60.0
            step8a[i-period] = (step7[i]*15.0 + step7[i-period]*15.0 + step7[i-(2*period)]*15.0 + \
                                 step7[i-(3*period)]*11.0 + step7[i-(4*period)]*4.0)/60.0
            step8a[i-(2*period)] = (step7[i]*9.0 + step7[i-period]*13.0 + step7[i-(2*period)]*13.0 + \
                                     step7[i-(3*period)]*13.0 + step7[i-(4*period)]*8.0 + step7[i-(5*period)]*4.0)/60.0

    def do_step8b (self):
        step8b = self.step8b
        self.step1MA.apply (self.step8a, step8b)
        # compute beginning and ending values
        half_period = old_div(self.period,2)
        step8b[:half_period] = [step8b[half_period]]*half_period
        step8b[-half_period:] = [step8b[-half_period-1]]*half_period


    def do_step8c (self):
        self.step8a.remove (self.step8b, self.op, True, self.step8c)

    def do_step8d (self):
        self.step7.remove (self.step8c, self.op, False, self.step8d)

    def do_step8e (self):
        step8d = self.step8d
        step8e = self.step8e

        self.computeStd1 (step8d, self.std3)
        self.computeStd2 (step8d, self.std3, self.std4)

        step8e.resize (len(step8d), self.mean)
        step8e.setPeriod (step8d.period)
        step8e.setPeriodStart (step8d.periodStart)
        step8e.setStartIdx (step8d.startIdx)
        step8e.setEndIdx (step8d.endIdx)

        for i in range (step8e.num_periods):
            sigma_l = self.lambda_L * self.std4[i]
            sigma_u = self.lambda_U * self.std4[i]
            sigma_d = sigma_u - sigma_l

            for [d, e] in zip (range(step8d.begin(i), step8d.end(i)), range(step8e.begin(i), step8e.end(i))):
                dev = abs(step8d[d] - self.mean)
                if dev > sigma_l and dev < sigma_u:
                    step8e[e] = 100.0 * (old_div((sigma_u-dev),sigma_d))
                else:
                    step8e[e] = 100.0

    def do_step8f (self):
        step7 = self.step7
        step8e = self.step8e
        step8f = self.step8f
        period = self.period

        step8f.resize (len(step7), self.mean)
        step8f.setPeriod (step7.period)
        step8f.setPeriodStart (step7.periodStart)
        step8f.setStartIdx (step7.startIdx)
        step8f.setEndIdx (step7.endIdx)

        past_nonextremes = []
        future_nonextremes = []

        for i in range(step7.num_periods):
            for [a, b, c] in zip (range(step8e.begin(i), step8e.end(i)),\
                          range(step7.begin(i), step7.end(i)),\
                          range(step8f.begin(i), step8f.end(i))):
                if step8e[a] == 100.0:
                    step8f[c] = step7[b]
                    continue

                past_count = 0
                future_count = 0
                # search for 4 nearest non-extreme values
                for k in range(step8e.num_periods):
                    if k <= i:
                        u = a - k*period
                        if u >= step8e.begin(i-k) and step8e[u] == 100.0:
                            past_nonextremes.append (step7[b-k*period])

                    if i+k < step7.num_periods:
                        u = a + k*period
                        if u < step8e.end(i+k) and step8e[u] == 100.0:
                            future_nonextremes.append (step7[b+k*period])

                    if len(past_nonextremes) >= 2 and len(future_nonextremes) >= 2:
                        break

                # modify extreme values
                weight = step8e[a]/100.0
                new_val = step7[b]*weight

                p_len = len(past_nonextremes)
                f_len = len(future_nonextremes)

                if p_len < 2:
                    if f_len+p_len >= 4:
                        future_num = 4 - p_len
                        num_terms = 4
                    else:
                        future_num = f_len
                        num_terms = f_len+p_len

                    new_val += sum (past_nonextremes, 0.0)
                    new_val += sum (future_nonextremes[:future_num], 0.0)

                elif f_len < 2:
                    if f_len+p_len >= 4:
                        past_num = 4 - f_len
                        num_terms = 4
                    else:
                        past_num = p_len
                        num_terms = f_len+p_len

                    new_val += sum (past_nonextremes[:past_num], 0.0)
                    new_val += sum (future_nonextremes, 0.0)

                else:
                    num_terms = 4
                    new_val += sum (past_nonextremes[:2], 0.0)
                    new_val += sum (future_nonextremes[:2], 0.0)

                new_val /= (num_terms + weight)
                step8f[c] = new_val
                past_nonextremes = []
                future_nonextremes = []

    def do_step9a (self):
        step8f = self.step8f
        step9a = self.step9a
        period = self.period

        self.step7MA.apply (step8f, step9a)

        # compute beginning values
        for i in range(period):
            step9a[i] = (step8f[i]*17.0 + step8f[i+period]*17.0 + step8f[i+2*period]*17.0 + step8f[i+3*period]*9.0)/60.0
            step9a[i+period] = (step8f[i]*15.0 + step8f[i+period]*15.0 + step8f[i+2*period]*15.0 + \
                                 step8f[i+3*period]*11.0 + step8f[i+4*period]*4.0)/60.0
            step9a[i+(2*period)] = (step8f[i]*9.0 + step8f[i+period]*13.0 + step8f[i+2*period]*13.0 + \
                                     step8f[i+3*period]*13.0 + step8f[i+4*period]*8.0 + step8f[i+5*period]*4.0)/60.0

        # compute ending values
        for i in range(len(step8f)-1, len(step8f)-period-1, -1):
            step9a[i] = (step8f[i]*17.0 + step8f[i-period]*17.0 + step8f[i-2*period]*17.0 + \
                         step8f[i-3*period]*9.0)/60.0
            step9a[i-period] = (step8f[i]*15.0 + step8f[i-period]*15.0 + step8f[i-2*period]*15.0 + \
                                 step8f[i-3*period]*11.0 + step8f[i-4*period]*4.0)/60.0
            step9a[i-(2*period)] = (step8f[i]*9.0 + step8f[i-period]*13.0 + step8f[i-2*period]*13.0 + \
                                     step8f[i-3*period]*13.0 + step8f[i-4*period]*8.0 + step8f[i-5*period]*4.0)/60.0


    def do_step9b (self):
        step9b = self.step9b
        self.step1MA.apply (self.step9a, step9b)
        # compute beginning and ending values
        half_period = old_div(self.period,2)
        step9b[:half_period] = [step9b[half_period]]*half_period
        step9b[-half_period:] = [step9b[-half_period-1]]*half_period

    def do_step9c (self):
        self.step9a.remove (self.step9b, self.op, True, self.step9c)

    def do_step10 (self):
        self.original.remove (self.step9c, self.op, True, self.step10)

    def do_step11 (self):
        self.step10.remove (self.step6e, self.op, True, self.step11)

    def seasonal_adjust (self):
        steps = [self.do_step1, self.do_step2, self.do_step3a, self.do_step3b, self.do_step3c, self.do_step3d, self.do_step3e, self.do_step3f, self.do_step4a, self.do_step4b, self.do_step4c, self.do_step5,
                 self.do_step6a, self.do_step6b, self.do_step6c, self.do_step6d,  self.do_step6e, self.do_step7, self.do_step8a, self.do_step8b, self.do_step8c, self.do_step8d, self.do_step8e, self.do_step8f,
                 self.do_step9a, self.do_step9b, self.do_step9c, self.do_step10, self.do_step11]
        for s in steps: s()
        return self.step10

    def irregular (self):
        return self.step11
