from __future__ import division
from past.utils import old_div
from builtins import range
from builtins import object

from math import log
from math import exp
from math import sqrt
from math import pow

### The implementations below are based on those in "Numerical Recipes, 3rd ed" hence forth abreviated as NR.


EPS = 2.22045e-16 # numeric_limits<double>::episilon() in C++
MIN = 2.22507e-308 # numeric_limits<double>::min() in C++
FPMIN = MIN / EPS


class Gauleg18(object):
    """ NR, p.262 """
    ngau = 18
    y = [0.0021695375159141994,
         0.011413521097787704, 0.027972308950302116, 0.051727015600492421,
         0.082502225484340941, 0.12007019910960293, 0.16415283300752470,
         0.21442376986779355, 0.27051082840644336, 0.33199876341447887,
         0.39843234186401943, 0.46931971407375483, 0.54413605556657973,
         0.62232745288031077, 0.70331500465597174, 0.78649910768313447,
         0.87126389619061517, 0.95698180152629142]
    w = [0.0055657196642445571,
         0.012915947284065419, 0.020181515297735382, 0.027298621498568734,
         0.034213810770299537, 0.040875750923643261, 0.047235083490265582,
         0.053244713977759692, 0.058860144245324798, 0.064039797355015485,
         0.068745323835736408, 0.072941885005653087, 0.076598410645870640,
         0.079687828912071670, 0.082187266704339706, 0.084078218979661945,
         0.085346685739338721, 0.085983275670394821]

class Gamma(Gauleg18):
    ASWITCH = 100

    cof = [57.1562356658629235, -59.5979603554754912,
           14.1360979747417471, -0.491913816097620199, .339946499848118887e-4,
           .465236289270485756e-4, -.983744753048795646e-4, .158088703224912494e-3,
           -.210264441724104883e-3, .217439618115212643e-3, -.164318106536763890e-3,
           .844182239838527433e-4, -.261908384015814087e-4, .368991826595316234e-5]


    @classmethod
    def gammln(cls, xx):
        """ Returns the value of ln(Gamma(xx)) for xx > 0. NR, page 257. """
        cls = Gamma()
        if xx <= 0: raise ValueError
        y, x = xx, xx
        tmp = x + 5.24218750000000000 # Rational 671/128
        tmp = (x+0.5)*log(tmp)-tmp
        ser = 0.999999999999997092
        for j in range(14):
            y += 1
            ser += old_div(Gamma.cof[j],y)
        return tmp + log(2.5066282746310005*ser/x)

    def gammpapprox(self, a, x, psig):
        """ NR. p.262 """
        a1 = a-1.0
        lna1 = log(a1)
        sqrta1 = sqrt(a1)
        gln = self.gammln(a)
        if x > a1: xu = max(a1 + 11.5*sqrta1, x + 6.0*sqrta1)
        else: xu = max(0.0, min(a1 - 7.5*sqrta1, x - 5.0*sqrta1))
        sum = 0
        for j in range(self.ngau):
            t = x + (xu-x)*Gauleg18.y[j]
            sum += Gauleg18.w[j]*exp(-(t-a1)+a1*(log(t)-lna1))
        ans = sum*(xu-x)*exp(a1*(lna1-1.)-gln)
        if psig == 1:
            if ans > 0.0:return 1.0-ans
            else: return -ans
        else:
            if ans >= 0.0: return ans
            else: return 1.0+ans

    def gcf(self, a, x):
        """ NR, p.261 """
        gln = self.gammln(a)
        b = x+1.0-a
        c = 1.0/FPMIN
        d = 1.0/b
        h = d
        i = 1
        while True:
            an = -i*(i-a)
            b += 2.0
            d = an*d+b
            if abs(d) < FPMIN: d = FPMIN
            c = b+old_div(an,c)
            if abs(c) < FPMIN: c = FPMIN
            d = 1.0/d
            delta = d*c
            h *= delta
            if abs(delta-1.0) <= EPS: break
        return exp(-x+a*log(x)-gln)*h


    def gammp(self, a, x):
        if x < 0.0 or a <= 0.0:
            raise ValueError
        if x == 0.0: return 0.0
        elif a >= Gamma.ASWITCH: return self.gammpapprox(a, x, 1)
        elif x < a+1.0: return self.gser(a, x)
        else: return 1.0-self.gcf(a, x)


    def gammq(self, a, x):
        if x < 0.0 or a <= 0.0: 
            raise ValueError
        if x == 0: return 1.0
        elif a >= Gamma.ASWITCH: return self.gammpapprox(a, x, 0)
        elif x < a+1.0: return 1.0-self.gser(a, x)
        else: return self.gcf(a, x)


    def gser(self, a, x):
        gln = self.gammln(a)
        ap = a
        delta = 1.0/a 
        sum = delta
        while True:
            ap += 1
            delta *= old_div(x,ap)
            sum += delta
            if abs(delta) < abs(sum)*EPS:
                return sum*exp(-x+a*log(x)-gln)

    def invgammp(self, p, a):
        """ NR, p.263 """
        a1 = a-1
        EPS = 1.e-8
        gln = self.gammln(a)
        if a <= 0.0: raise ValueError
        if p >= 1.0: return max(100.0, a + 100.0*sqrt(a))
        if p <= 0.0: return 0.0
        if a > 1.0:
            lna1 = log(a1)
            afac = exp(a1*(lna1-1.)-gln)
            if p < 0.5: pp = p
            else: pp = 1.0 - p
            t = sqrt(-2.*log(pp))
            x = old_div((2.30753+t*0.27061),(1.+t*(0.99229+t*0.04481))) - t
            if p < 0.5: x = -x
            x = max(1.e-3,a*pow(1.-1./(9.*a)-old_div(x,(3.*sqrt(a))),3))
        else:
            t = 1.0 - a*(0.253+a*0.12)
            if p < t: x = pow(old_div(p,t),1./a)
            else: x = 1.-log(1.-old_div((p-t),(1.-t)))
        
        for j in range(12):
            if x <= 0.0: return 0.0
            err = self.gammp(a, x) - p
            if a > 1.: t = afac*exp(-(x-a1)+a1*(log(x)-lna1))
            else: t = exp(-x+a1*log(x)-gln)
            u = old_div(err,t)
            t = old_div(u,(1.-0.5*min(1.,u*(old_div((a-1.),x) - 1))))
            x -= t
            if x <= 0.0: x = 0.5*(x + t)
            if abs(t) < EPS*x: break
        
        return x

class Chisqdist(Gamma):
    """ Chi-squared distribution. NR. p.330 """
    def __init__(self, nnu):
#        Gamma.__init__(self)
        self.nu = nnu
        if self.nu <= 0.0: 
            raise ValueError
        self.fac = 0.693147180559945309*(0.5*self.nu)+self.gammln(0.5*self.nu)

    # Return probability density function
    def p(self, x2):
        if x2 <= 0.0: raise ValueError
        return exp(-0.5*(x2-(self.nu-2.0)*log(x2))-self.fac)

    # Return cumulative distribution function
    def cdf(self, x2):
        if x2 < 0.0: raise ValueError
        return self.gammp(0.5*self.nu, 0.5*x2)

    # Return inverse cumulative distribution function
    def invcdf(self, p):
        if p < 0.0 or p >= 1.0:
            raise ValueError
        return 2.0*self.invgammp(p, 0.5*self.nu)


# NR p. 272
class Beta(Gauleg18):
    
    @classmethod
    def betai(cls, a, b, x):
        if a <= 0.0 or b <= 0.0: raise ValueError
        if x < 0.0 or x > 1.0: raise ValueError
        if x == 0.0 or x == 1.0: return x
        SWITCH = 3000
        if a > SWITCH and b > SWITCH: return cls.betaiapprox(a, b, x)
        bt = exp(Gamma.gammln(a+b)-Gamma.gammln(a)-Gamma.gammln(b)+a*log(x)+b*log(1.0-x))
        if x < old_div((a+1.0),(a+b+2.0)): return old_div(bt*cls.betacf(a,b,x),a)
        else: return 1.0 - old_div(bt*cls.betacf(b,a,1.0-x),b)

    @classmethod
    def betacf(cls, a, b, x):
        qab = a+b
        qap = a+1.0
        qam = a-1.0
        c = 1.0
        d = 1.0 - old_div(qab*x,qap)
        if abs(d) < FPMIN: d = FPMIN
        d = 1.0/d
        h = d
        for m in range(1, 10000):
            m2 = 2*m
            aa = old_div(m*(b-m)*x,((qam+m2)*(a+m2)))
            d = 1.0+aa*d
            if abs(d) < FPMIN: d = FPMIN
            c = 1.0+old_div(aa,c)
            if abs(c) < FPMIN: c = FPMIN
            d = 1.0/d
            h *= d*c
            aa = old_div(-(a+m)*(qab+m)*x,((a+m2)*(qap+m2)))
            d = 1.0+aa*d
            if abs(d) < FPMIN: d = FPMIN
            c = 1.0+old_div(aa,c)
            if abs(c) < FPMIN: c = FPMIN
            d = 1.0/d
            delta = d*c
            h *= delta
            if abs(delta-1.0) <= EPS: break
        return h


    @classmethod
    def betaiapprox(cls, a, b, x):
        a1 = a-1.0
        b1 = b-1.0
        mu = old_div(a,(a+b))
        lnmu = log(mu)
        lnmuc = log(1.- mu)
        t = sqrt(old_div(a*b,(((a+b)**2)*(a+b+1.0))))
        if x > old_div(a,(a+b)):
            if x >= 1.0: return 1.0
            xu = min(1., max(mu + 10.*t, x + 5.0*t))
        else:
            if x <= 0.0: return 0.0
            xu = max(0., min(mu - 10.*t, x - 5.0*t))

        sum = 0
        for j in range(0, 18):
            t = x + (xu-x)*Gauleg18.y[j]
            sum += Gauleg18.w[j]*exp(a1*(log(t)-lnmu)+b1*(log(1-t)-lnmuc))
        ans = sum*(xu-x)*exp(a1*lnmu-Gamma.gammln(a)+b1*lnmuc-Gamma.gammln(b)+Gamma.gammln(a+b))
        if ans > 0.0: return 1.0-ans
        else: return -ans

    @classmethod
    def invbetai(cls, p, a, b):
        a1 = a-1
        b1 = b-1
        if p <= 0.: return 0.
        elif p >= 1.: return 1.
        elif a >= 1. and b >= 1.:
            if p < 0.5: pp = p
            else: pp = 1. - p
            t = sqrt(-2.*log(pp))
            x = old_div((2.30753+t*0.27061),(1.+t*(0.99229+t*0.04481))) - t
            if p < 0.5: x = -x
            al = (x**2 - 3.)/6.
            h = 2./(1./(2.*a-1.)+1./(2.*b-1.))
            w = (old_div(x*sqrt(al+h),h))-(1./(2.*b-1)-1./(2.*a-1.))*(al+5./6.-2./(3.*h))
            x = old_div(a,(a+b*exp(2.*w)))
        else:
            lna = log(old_div(a,(a+b)))
            lnb = log(old_div(b,(a+b)))
            t = old_div(exp(a*lna),a)
            u = old_div(exp(b*lnb),b)
            w = t + u
            if p < old_div(t,w): x = pow(a*w*p,1./a)
            else: x = 1. - pow(b*w*(1.-p), 1./b)
        
        afac = -Gamma.gammln(a)-Gamma.gammln(b)+Gamma.gammln(a+b)
        for j in range(10):
            if x == 0. or x == 1.: return x
            err = cls.betai(a, b, x) - p
            t = exp(a1*log(x)+b1*log(1.-x) + afac)
            u = old_div(err,t)
            t = old_div(u,(1.-0.5*min(1.,u*(old_div(a1,x) - old_div(b1,(1.-x))))))
            x -= t
            if x <= 0.: x = 0.5*(x + t)
            if x >= 1.: x = 0.5*(x + t + 1.)
            if abs(t) < EPS*x and j > 0: break
        
        return x


class Fdist(Beta):

    def __init__(self, nnu1, nnu2):
        if nnu1 <= 0. or nnu2 <= 0.: raise ValueError
        self.nu1, self.nu2 = nnu1, nnu2
        nu1, nu2 = self.nu1, self.nu2
        gammln = Gamma.gammln
        self.fac = 0.5*(nu1*log(nu1)+nu2*log(nu2))+gammln(0.5*(nu1+nu2)) - gammln(0.5*nu1)-gammln(0.5*nu2)
        

    def p(self, f):
        if f <= 0.: raise ValueError
        nu1, nu2 = self.nu1, self.nu2
        return exp((0.5*nu1-1.)*log(f)-0.5*(nu1+nu2)*log(nu2+nu1*f)+self.fac)
        
    def cdf(self, f):
        if f < 0.: raise ValueError
        nu1, nu2 = self.nu1, self.nu2
        return self.betai(0.5*nu1,0.5*nu2,old_div(nu1*f,(nu2+nu1*f)))
        

    def invcdf(self, p):
        if p <= 0. or p >= 1.: raise ValueError
        nu1, nu2 = self.nu1, self.nu2
        x = self.invbetai(p, 0.5*nu1, 0.5*nu2)
        return old_div(nu2*x,(nu1*(1.-x)))


class Erf(object):
    """ NR, p.264 """
    ncof = 28
    cof = [-1.3026537197817094, 6.4196979235649026e-1,
            1.9476473204185836e-2, -9.561514786808631e-3, -9.46595344482036e-4,
            3.66839497852761e-4, 4.2523324806907e-5, -2.0278578112534e-5,
            -1.624290004647e-6, 1.303655835580e-6, 1.5626441722e-8, -8.5238095915e-8,
            6.529054439e-9, 5.059343495e-9, -9.91364156e-10, -2.27365122e-10,
            9.6467911e-11, 2.394038e-12, -6.886027e-12, 8.94487e-13, 3.13092e-13,
            -1.12708e-13, 3.81e-16, 7.106e-15, -1.523e-15, -9.4e-17, 1.21e-16, -2.8e-17]
    
    def erf(self, x):
        if x >= 0.: return 1. - self.erfccheb(x)
        else: return self.erfccheb(-x) - 1.

    
    def erfc(self, x):
        if x >= 0. : return self.erfccheb(x)
        else: return 2. - self.erfccheb(-x)

    def erfccheb(self, z):
        d, dd = 0., 0.
        if z < 0.: raise ValueError
        t = 2./(2.+z)
        ty = 4.*t - 2.
        for j in range(Erf.ncof-1, 0, -1):
            tmp = d
            d = ty*d - dd + Erf.cof[j]
            dd = tmp
        return t*exp(-z*z + 0.5*(Erf.cof[0] + ty*d) - dd)

    def inverfc(self, p):
        if p >= 2.: return -100.
        if p <= 0.: return 100.
        if p < 1.: pp = p
        else: pp = 2. - p
        t = sqrt(-2.*log(pp/2.))
        x = -0.70711*(old_div((2.30753+t*0.27061),(1.+t*(0.99229+t*0.04481))) - t)

        for j in range(0, 2):
            err = self.erfc(x) - pp
            x += old_div(err,(1.12837916709551257*exp(-x**2)-x*err))
            
        if p < 1.: return x
        else: return -x

    def inverf(self, p):
        return self.inverfc(1.-p)

    def erfcc(self, x):
        z = abs(x)
        t = 2./(2.+z)
        ans = t*exp(-z*z-1.26551223+t*(1.00002368+t*(0.37409196+t*(0.09678418+
                                                                   t*(-0.18628806+t*(0.27886807+t*(-1.13520398+t*(1.48851587+
                                                                                                                  t*(-0.82215223+t*0.17087277)))))))))
        if x >= 0.: return ans
        else: return 2. - ans


class Normaldist(Erf):
    """ NR, p.321 """
    def __init__(self, mmu=0., ssig=1.):
        self.mu, self.sig = mmu, ssig
        if ssig <= 0.: raise ValueError
        

    def p(self, x):
        mu = self.mu
        sig = self.sig
        return (0.398942280401432678/sig)*exp(-0.5*(old_div((x-mu),sig))**2)

    def cdf(self, x):
        mu = self.mu
        sig = self.sig
        return 0.5*self.erfc(old_div(-0.707106781186547524*(x-mu),sig))

    def invcdf(self, p):
        if p <= 0. or p >= 1.: raise ValueError
        mu = self.mu
        sig = self.sig
        return -1.41421356237309505*sig*self.inverfc(2.*p)+mu
