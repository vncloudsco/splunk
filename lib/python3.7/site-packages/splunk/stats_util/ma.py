from __future__ import print_function
from __future__ import division
from past.utils import old_div
from builtins import range
from builtins import map
from builtins import object

import math

class MA(object):
    """ Moving Average base class """
    def __init__ (self):
        self.center = 0

    def __len__ (self):
        return len(self.weights)

    def __iter__ (self):
        return self.weights.__iter__()

    def __setitem__ (self, i, val):
        self.weights[i] = val

    def __getitem__ (self, i):
        return self.weights[i]

    def __contains__ (self, i):
        return i in self.weights

    # def weight (self, asym_pos, pos):
    #     """ Get the weight at position pos in the asymmetric MA at position asym_pos """
    #     return self.asyms[asym_pos][pos]
        
    def resize (self, n):
        self.weights = list(range(n))

    def apply (self, original, result):
        """ Apply this moving average to the original TS and obtain the result TS """
        if len(result) < len(original):
            print("Warning: result TS's length is too short")
            print("original's length = %d, result's length = %d" % (len(original), len(result)))
            print("resizing result's length ...")
            result.resize(len(original))

        for i, v in enumerate(original):
            idx = i - self.center
            if idx < 0 or idx+len(self) > len(original):
                result[i] = 0.0
                continue

            val = 0.0
            for j, w in enumerate(self):
                val += w * original[int(idx+j)]
            result[i] = val

        result.setPeriod (original.period)
        result.setPeriodStart ( (original.periodStart+self.center)%original.period)
        result.setStartIdx (original.startIdx+self.center)
        result.setEndIdx (original.endIdx-self.center)

    def compose (self, other, result):
        """ Compose this MA with other MA to obtain result MA """
        compose_order = len(self) + len(other) - 1
        if len(result) < compose_order:
            result.resize (compose_order)

        result.center = self.center + other.center

        for i, res in enumerate(result):
            w = 0.0
            for j in range(max(0, i-len(self)), min(i, len(other))):
                w += self[i-j] * other[j]
            result[i] = w

    def __str__ (self):
            s1 =  "Moving average: center = %d [" %self.center
            s2 =  ' '.join(map(str, self))
            s3 = "]"
            return s1+s2+s3
            
class Simple (MA):
    """ Simple Moving Average """
    def __init__ (self, order, forward=True):
        self.weights = [1.0/order]*order
        if order%2:
            self.center = (order - 1)/2.0
        elif forward:
            self.center = (order/2.0) - 1
        else:
            self.center = order/2.0
            
        #print("constructing Simple MA: center = %d, order = %d" % (self.center, order))

class TwoByN (MA):
    """ 2xN Moving Average """
    def __init__ (self, order):
        if order%2:
            print("ERROR: Can't create TwoByN MA with odd order")
            raise ValueError

        self.weights = [1.0/order]*(order+1)
        self.weights[0] = self.weights[order] = 1.0/(2.0*order)
        self.center = order/2.0
        #print("constructing TwoByN MA: order = %d" % order)

class ThreeByN (MA):
    """ 3xN Moving Average """
    def __init__ (self, order):
        if not order%2 or order < 3:
            print("ERROR: Incorrect paramater for TwoByN moving average: order must be odd and >= 3\n")
            raise ValueError
        
        self.weights = [1.0/order]*(order+2)
        self.weights[0] = self.weights[order+1] = 1.0/(3.0*order)
        self.weights[1] = self.weights[order] = 2.0*self.weights[0]
        self.center = (order + 1.0)/2.0

class Henderson (MA):
    def __init__ (self, order):
        self.resize(order)
        p = old_div((order-1),2)
        n = p+2
        n2 = n**2
        denom = 8*n*(n2-1)*((4*n2)-1)*((4*n2)-9)*((4*n2)-25)
        for i in range(order):
            j2 = (i-p)**2
            a1 = (n-1)**2 - j2
            a2 = n2 - j2
            a3 = (n+1)**2 - j2
            a4 = (3*n2) - 16 - (11*j2)
            numer = 315.0*a1*a2*a3*a4

            self[i] = old_div(numer,denom)
            self.center = old_div((order-1),2)
        #print("constructing Henderson MA: order = %d, self.center = %d" % (order, self.center))

class Weighted (MA):
    """ Moving Average created from a sequence """
    def __init__ (self, weights, center):
        self.weights = [val for val in weights]
        self.center = center        
        #print("constructing Weighted MA: center = %d" % self.center)

class Musgrave (MA):
    """ Musgrave Moving Average """
    def __init__ (self, order, ICratio):
        self.ICratio = ICratio
        self.symmetric = Henderson (order)
        self.order = old_div(order,2)
        self.asyms = [[]]*self.order


        D = 4.0/(math.pi*(ICratio**2))

        for i in range(self.order):
            M = self.order+i+1
            self.asyms[i] = list(range(M))
            sum1 = 0.0
            sum2 = 0.0
            u = (M+1)/2.0
            for j in range(M, len(self.symmetric)):
                sum1 += self.symmetric[j]
                sum2 += (j+1-u)*self.symmetric[j]
            sum1 /= M
        
            denom = 1.0 + ((M**3-M)*D)/12.0
            S = old_div((D*sum2),denom)
            R = (M+1.0)/2.0

            for j in range(M):
                self.asyms[i][j] = self.symmetric[j] + sum1 + (j+1-R)*S

    def __len__ (self):
        return self.order

    def weight (self, asym_pos, pos):
        """ Get the weight at position pos in the asymmetric MA at position asym_pos """
        return self.asyms[asym_pos][pos]
        

    def apply (self, original, result):
        """ Apply this MA to the original TS and obtain the result TS """
        self.symmetric.apply (original, result)
        
        # These were set by _symmetric, but they aren't right for Musgrave
        result.setPeriodStart (original.periodStart);
        result.setStartIdx (original.startIdx);
        result.setEndIdx (original.endIdx);
        
        # Compute the begining values using the asymmetric weights
        for pos, val in enumerate(self.asyms):
            idx = result.startIdx + pos
            result[idx] = 0.0
            u = result.startIdx + len(val) - 1
            for i in range(len(val)):
                result[idx] += val[i] * original[u-i]
                
        # Compute the end values using the asymmetric weights
        for pos, val in enumerate(self.asyms):
            idx = result.endIdx - 1 - pos
            result[idx] = 0.0
            u = result.endIdx - len(val)
            for i in range(len(val)):
                result[idx] += val[i] * original[u+i]
                
                    
    def __str__ (self):
        s1 = "order = %d\n" % self.order
        s2 = []
        for i in range(self.order-1, -1, -1):
            s2.extend(["0.00000  "]*(self.order-i))
            s2.extend(["%6.5f  " % x for x in self.asyms[i]])
            s2.append("\n")
        return s1 + ''.join(s2) + str(self.symmetric)
        
        
def test_Musgrave (henderson_size, R, filename):
    mus = Musgrave (henderson_size, R)
    file = open(filename, "r")
    v = []
    for line in file:
        v.append([float(x) for x in line.strip().split()])
    file.close()
    
    if len(mus) != len(v):
        print("Test failed! Different orders. Expect %d, got %d" % (len(v), len(mus)))
        return -1

    for i, u in enumerate(v):
        for j in range(i+1, len(u)):
            diff = u[j] - mus.weight (len(mus)-i-1, j-i-1)
            if diff >= 0.0001 or diff <= -0.0001:
                print("expect %f, got %f" % (u[i][j], mus.weight (len(mus)-i-1, j-i-1)))
                return -1
    print("test_Musgrave for file %s PASSED" %filename)
    return 0


# test_Musgrave (13, 3.5, "Musgrave_13_3_dot_5.txt")
# test_Musgrave (7, 4.5, "Musgrave_7_4_dot_5.txt")
# test_Musgrave (9, 1.0, "Musgrave_9_1.txt")
