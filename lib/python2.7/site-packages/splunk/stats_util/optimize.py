from __future__ import print_function
from __future__ import division
from past.utils import old_div
from builtins import range
import math

from functools import reduce


#EPS = 2.22045e-16 # numeric_limits<double>::episilon() in C++#\
EPS = 1.0e-10

# class MatrixIndex:

#     matrix_index = {}

#     def __init__(self,nrow,ncol):
#         self.index = [None]*nrow
#         for r in range(nrow):
#             self.index[r] = [None]*ncol
#             for c in range(ncol):
#                 self.index[r][c] = r*ncol + c

#     def __getitem__(self,pair):
#         return self.index[pair[0]][pair[1]]


#     @classmethod
#     def get_idx(cls,nrow,ncol):
#         if (nrow,ncol) not in MatrixIndex.matrix_index:
#             MatrixIndex.matrix_index[nrow,ncol] = MatrixIndex(nrow,ncol)
#         return MatrixIndex.matrix_index[nrow,ncol]




class mat(list):

    def __init__(self, a, nrow, ncol=1):
        if nrow <= 0 or ncol <= 0:
            raise ValueError
        if len(a) < nrow*ncol:
            a.extend([None]*(nrow*ncol-len(a)))

        self.nrow = nrow
        self.ncol = ncol

        self.cols = [None]*self.ncol
        for i in range(self.ncol):
            self.cols[i] = [a[j] for j in range(i, len(a), self.ncol)]        
        

    @classmethod
    def fromarray(cls, ar):
        """ Construct a matrix from a 2d list """
        if len(ar) == 0 or len(ar[0]) == 0:
            raise ValueError
        cls = mat([0], 1, 1)        
        cls.ncol = len(ar)
        cls.nrow = len(ar[0])
        cls.cols = ar
        return cls


    @classmethod
    def id(cls, n):
        if n < 1: raise ValueError
        I = [0.0]*(n**2)
        for i in range(n): I[i*n+i] = 1.0
        return mat(I, n, n)


    @classmethod
    def zero(cls, nrow, ncol):
        if nrow < 1 or ncol < 1: raise ValueError
        return mat([0.0]*(nrow*ncol), nrow, ncol)


    def __str__(self):
        pad = 11
        valw = 7
        rep = ["     "]
        for j in range(self.ncol):
            header = "[,%d]" %j
            rep.append(header.center(pad))
        rep.append("\n")
        for i in range(self.nrow):
            rep.append("[%d,] " %i)
            for j in range(self.ncol):
                s = "%*.3f" %(valw, self[i, j])
                rep.append(s.center(pad))
            rep.append("\n")
        return ''.join(rep)


    def __getitem__(self, arg):
        if isinstance(arg, int):
            return self.cols[arg]
        elif isinstance(arg, tuple):
            return self.cols[arg[1]][arg[0]]
        
    def __contains__(self, arg):
        return arg in self.cols

    def __iter__(self):
        return iter(self.cols)

    def __setitem__(self, arg, v):
        if isinstance(arg, int):
            for i in range(self.nrow):
                self.cols[arg][i] = v[i]
        elif isinstance(arg, tuple):
            self.cols[arg[1]][arg[0]] = v


    def row(self, i):
        return [c[i] for c in self.cols]


    def col(self, i):
        return self.cols[i]


    def __add__(self, other):
        if self.nrow != other.nrow or self.ncol != other.ncol:
            raise ValueError
        a = [None]*self.ncol
        for i in range(self.ncol):
            a[i] = [x+y for (x, y) in zip(self.cols[i], other.cols[i])]
        return mat.fromarray(a)


    def __iadd__(self, other):
        if other.nrow != self.nrow or other.ncol != self.ncol: raise ValueError
        for i in range(self.ncol):
            for j in range(self.nrow):
                self.cols[i][j] += other.cols[i][j]
        return self

    
    def __sub__(self, other):
        if self.nrow != other.nrow or self.ncol != other.ncol:
            raise ValueError
        a = [None]*self.ncol
        for i in range(self.ncol):
            a[i] = [x-y for (x, y) in zip(self.cols[i], other.cols[i])]
        return mat.fromarray(a)


    def __isub__(self, other):
        if other.nrow != self.nrow or other.ncol != self.ncol: raise ValueError
        for i in range(self.ncol):
            for j in range(self.nrow):
                self.cols[i][j] -= other.cols[i][j]
        return self


    def __rmul__(self, scalar):
        a = [None]*self.ncol
        for i in range(self.ncol):
            a[i] = [scalar*x for x in self.cols[i]]
        return mat.fromarray(a)


    def __imul__(self, other):
        if not isinstance(other, type(mat.id(1))):
            for i in range(self.ncol):
                for j in range(self.nrow):
                    self.cols[i][j] *= other
        else: self = self*other
        return self


    def __mul__(self, other):
        if self.ncol != other.nrow:
            raise ValueError

        m = mat([0.]*(self.nrow*other.ncol), self.nrow, other.ncol)
        for i in range(m.nrow):
            for j in range(m.ncol):
                for k in range(self.ncol):
                    m[i, j] += self[i, k]*other[k, j]
        return m


    def __div__(self, scalar):
        a = [None]*self.ncol
        for i in range(self.ncol):
            a[i] = [old_div(x,scalar) for x in self.cols[i]]
        return mat.fromarray(a)


    def __idiv__(self, scalar):
        for i in range(self.ncol):
            for j in range(self.nrow):
                self[i, j] /= scalar
        return self

    def __eq__(self, other):
        ret = self.ncol == other.ncol
        for i in range(self.ncol):
            ret = ret and self.cols[i] == other.cols[i]
        return ret

    def __neg__(self):
        return -1*self

    # trace
    def tr(self):
        return reduce(lambda x,i: x + self[i,i], list(range(self.nrow)), 0.0)


    # transpose
    def t(self):
        m = mat([None]*(self.nrow*self.ncol), self.ncol, self.nrow)
        for i in range(m.nrow):
            for j in range(m.ncol):
                m[i, j] = self[j, i]
        return m


    # p-th norm
    def norm(self,p=2):
        s = 0.
        for i in range(self.ncol):
            s += sum((abs(x)**p for x in self.cols[i]))
        if p > 1:
            return pow(s, 1./p)
        else:
            return s

    def size(self):
        return [self.nrow, self.ncol]


    # Return a submatrix made of the rows and columns specified by the rowlist and collist parameters. 
    def submatrix(self, rowlist, collist):
        ar = [None]*len(collist)
        for i in range(len(ar)):
            col = self.cols[collist[i]]
            ar[i] = [col[j] for j in rowlist]
        return mat.fromarray(ar)

        

class vec(list):
    
    @classmethod
    def zero(cls, n):
        if n < 1: raise ValueError
        return vec([0.0]*n)


    def __add__(self, other):
        return vec([a+b for (a, b) in zip(self, other)])

    def __sub__(self, other):
        return vec([a-b for (a, b) in zip(self, other)])

    def __iadd__(self, other):
        return vec([a+b for (a, b) in zip(self, other)])

    def __isub__(self, other):
        return vec([a-b for (a, b) in zip(self, other)])


    def T(self, other):
        """ Multiply (column) vector self with vector other, viewed as a row vector 
        Return a matrix (of course)."""
        m = [None]*(len(self)*len(other))
        for i in range(len(self)):
            k = i*len(other)
            m[k:k+len(other)] = [self[i]*x for x in other]

        return mat(m, len(self), len(other))    

    def __rmul__(self, scalar):
        return vec([scalar*x for x in self])

    def __mul__(self, other):
        return reduce(lambda x, y: x + y[0]*y[1], zip(self, other), 0.0)

    def __imul__(self, scalar):
        return vec([scalar*x for x in self])        

    def __div__(self, scalar):
        return vec([old_div(x,scalar) for x in self])

    def __idiv__(self, scalar):
        return vec([old_div(x,scalar) for x in self])

    def __neg__(self):
        return -1*self


    # transpose
    def t(self):
        return mat(self, 1, len(self))
        
    # Return the p-th norm
    def norm(self,p=2):
        s =  sum((abs(x)**p for x in self))
        if p > 1:
            return pow(s, 1./p)
        else:
            return s

def apply(m, v):
    """ multiply matrix m  with vector v """
    if m.ncol != len(v): raise ValueError
    u = [None]*m.nrow
    for i in range(m.nrow):
        u[i] = 0.
        for j in range(m.ncol):
            u[i] += m[i, j]*v[j]
    return vec(u)
    


# a is vec or a mat
def t(a):
    return a.t()

# a is vec or mat
def norm(a):
    return a.norm()

# m is a mat 
def tr(m):
    return m.tr()

# m is a 2x2 matrix
def det(m):
    return m[0, 0]*m[1, 1] - m[0, 1]*m[1, 0]    

# m is a 2x2 matrix
# det is determinant of m and must be non-zero
def inv(m, det):
    return mat([old_div(m[1,1],det), old_div(-m[0,1],det), old_div(-m[1,0],det), old_div(m[0,0],det)], 2,2)
    


TAB = 10
der_a = [[None]*TAB for i in range(TAB)]

# Return the derivative of the given function 'fn' at the point 'x'
def der (fn, x, h=0.001):
    """ The dfridr algorithm listed on page 188 of 'Numerical Recipes in C, 2nd ed' or page 231 in 3rd ed. """

    CON = 1.4
    CON2 = CON*CON
    BIG = 10.0**10
    SAFE = 2.0

    hh = h
    ans = der_a[0][0] = old_div((fn(x+hh) - fn(x-hh)),(2.0*hh))
    err = BIG
    for i in range(1, TAB):
        hh /= CON
        der_a[0][i] = old_div((fn(x+hh) - fn(x-hh)),(2.0*hh))
        fac = CON2
        for j in range(1, i+1):
            der_a[j][i] = old_div((der_a[j-1][i]*fac - der_a[j-1][i-1]),(fac-1.0))
            fac = CON2*fac
            errt = max(abs(der_a[j][i]-der_a[j-1][i]), abs(der_a[j][i]-der_a[j-1][i-1]))
            if errt <= err:
                err = errt
                ans = der_a[j][i]
        if abs(der_a[i][i] - der_a[i-1][i-1]) >= SAFE*err: break

    return ans



# Given a multivariable function 'fn', a given vec p, and a direction vec u.
# Return the one-variable function g(t) = fn(p + tu).
def direct (fn, p, u):
    return  lambda t: fn(*(p + t*u))  

# Return the partial derivative of fn at the point p in the direction u
def pder (fn, p, u, h=0.001):
    return der(direct(fn, p, u), 0.0, h)


# Return the gradient of given function fn at p
def grad (fn, p, h=0.001):
    n = len(p)
    e = vec.zero(n)
    gr = vec([None]*n)
    for i in range(n):
        e[i] = 1.0
        gr[i] = pder(fn, p, e, h)
        e[i] = 0.0
    return gr



# Compute the gradient of func.
# NR, 3rd, p.525: p = x, g = df, fold = Funcd.f
def df (func, p, fold, g):
    ph = p
    for j in range(len(p)):
        temp = p[j]
        h = EPS*abs(temp)
        if h < EPS: h = EPS
        ph[j] = temp + h
        h = ph[j] - temp
        fh = func(*ph)
        ph[j] = temp
        g[j] = old_div((fh - fold),h)



def ip (a1, fa1, da1, a2, fa2, da2):
    d = a2 - a1
    if d > 0: sgn = 1
    else: sgn = -1
    
    d1 = da1 + da2 - old_div(3*(fa1-fa2),(a1-a2))
    d2 = sgn*math.sqrt(abs(d1**2 - da1*da2))
    a = a2 - old_div(d*(da2 + d2 - d1),(da2 - da1 + 2.0*d2))
    small = 0.00001
    if abs(a-a1) < small or abs(a-a2) < small:
        a = (a1 + a2)/2.0
    return a

def zoom (fn, f0, df0, a_lo, a_hi, c1, c2):
    small = 0.00001
    df_lo = der(fn, a_lo)
    if abs(df_lo) < small: return a_lo
    df_hi = der(fn, a_hi)
    if abs(df_hi) < small: return a_hi
    f_lo = fn(a_lo)
    f_hi = fn(a_hi)

    iter = 1
    while (True):
        a = ip(a_lo, f_lo, df_lo, a_hi, f_hi, df_hi)
        fa = fn(a)
        dfa = der(fn, a)
        if fa >= f_lo or fa > f0 + c1*a*df0:
            a_hi = a
            f_hi = fa
            df_hi = dfa
        else:
            if abs(dfa) <= -c2*df0:
                return a
            if (dfa >= 0 and a_hi >= a_lo) or (dfa <= 0 and a_hi <= a_lo):
                a_hi = a_lo
                f_hi = f_lo
                df_hi = df_lo
            a_lo = a
            f_lo = fa
            df_lo = dfa
        iter += 1
        if iter > 10: return a

# amax must be > 1
def line_search (fn, c1, c2, amax):
    if amax <= 1: raise ValueError
    f0 = fn(0.0)
    df0 = der(fn, 0.0)
    famax = fn(amax)
    dfamax = der(fn, amax)
    a0 = 0.0
    fa0 = f0
    a1 = 1.0
    i = 1
    while (True):
        fa1 = fn(a1)
        if (fa1 >= fa0 and i > 1) or fa1 > f0 + c1*a1*df0:
            return zoom(fn, f0, df0, a0, a1, c1, c2)
        dfa1 = der(fn, a1)
        if abs(dfa1) <= -c2*df0:
            return a1
        if dfa1 >= 0:
            return zoom(fn, f0, df0, a0, a1, c1, c2)
        a0 = a1
        fa0 = fa1
        a1 = ip(a1, fa1, dfa1, amax, famax, dfamax)
        i += 1
    
# fn = function
# x0 = initial position (a list)
# er = convergence tolerance error
# return a list x where fn(*x) is minimal
def BFGS (fn, x0, er=0.0001):
    n = len(x0)
    I = mat.id(n)
    H = I
    x1 = vec(x0)
    grad1 = grad(fn, x1)
    iter = 0
    ct = 0
    while norm(grad1) > er:
        p = apply(-H,grad1)
        alpha = line_search(lambda t:fn(*(x1+t*p)), er, 0.9, 1.1)
        s = alpha*p
        x2 = x1 + s
        grad2 = grad(fn, x2)
        y = grad2 - grad1
        mu = y*s
        if abs(mu) < 0.000001:
            x1 = x2
            break
        rho = 1.0/mu
        
        U = I - rho*s.T(y)
        H = U*H*t(U) + rho*s.T(s)
        x1 = x2
        grad1 = grad2
        iter += 1
        if norm(y) < er:
            if ct >= 3: break
            else: ct += 1
        else: ct = 0
        if iter > 25: break
    return x1



# The lnsrch function in NR 3ed p.479. 
# The parameter func is moved to front. The parameters f and check are not included as we will return them.
# xold,g,p are vec's of the same len
def lnsrch (func, xold, fold, g, p, x, stpmax):
    """ The lnsrch function in NR 3ed p.479. """
    ALF = 1.0e-4
    TOLX = 2.22045e-16 # numeric_limits<double>::episilon() in C++ 

    alam2, f2 = 0.0, 0.0
    n = len(xold)
    SUM = math.sqrt(p*p)

    if SUM > stpmax:
        for i in range(n):
            p[i] *= (old_div(stpmax,SUM)) # Scale if attempted step is too big.
    
    slope = p*g
    if slope >= 0.0: 
       print("Roundoff problem in lnsrch: slope = %f" % slope)
       print("p = %s g = %s" % (str(p), str(g)))
       raise ValueError
    
    test = 0.0
    for i in range(n):
        temp = old_div(abs(p[i]),max(abs(xold[i]),1.0))
        if temp > test: test = temp
        
    alamin = old_div(TOLX,test)
    alam = 1.0
    while True:
        for i in range(n):
            x[i] = xold[i] + alam*p[i]

        f = func(*x)

        if alam < alamin:
            for i in range(n): x[i] = xold[i]
            return f
        elif f <= fold+ALF*alam*slope:
            return f
        else:
            if alam == 1.0:
                tmplam = old_div(-slope,(2.0*(f-fold-slope)))
            else:
                rhs1 = f-fold-alam*slope
                rhs2 = f2-fold-alam2*slope
                a = old_div((old_div(rhs1,(alam*alam))-old_div(rhs2,(alam2*alam2))),(alam-alam2))
                b = old_div((old_div(-alam2*rhs1,(alam*alam))+old_div(alam*rhs2,(alam2*alam2))),(alam-alam2))
                if a == 0.0: 
                    tmplam = old_div(-slope,(2.0*b))
                else:
                    disc = b*b-3.0*a*slope
                    if disc < 0.0: tmplam = 0.5*alam
                    elif b <= 0.0: tmplam = old_div((-b+math.sqrt(disc)),(3.0*a))
                    else: tmplam = old_div(-slope,(b+math.sqrt(disc)))
                if tmplam > 0.5*alam:
                    tmplam = 0.5*alam
            
        alam2 = alam
        f2 = f
        alam = max(tmplam, 0.1*alam)


# The dfpmin in NR 3rd p.523
# The parameter func is moved to front. The parameters iter and fret are dropped since we return them.
# p is a vec
def dfpmin (func, p, gtol=1.0e-3):
    """ The dfpmin in NR 3rd p.523 """
    ITMAX = 200

    TOLX = 4*EPS
    STPMX = 100.0
    
    n = len(p)
    g = vec.zero(n)
    dg = vec.zero(n)
    hdg = vec.zero(n)
    pnew = vec.zero(n)
    hessin = mat.id(n)
    fp = func(*p)
    df(func, p, fp, g)
    if norm(g) == 0:
        return fp, 0
    xi = -g
    SUM = 0.
    for i in range(n):
        SUM += p[i]*p[i]
    stpmax = STPMX*max(math.sqrt(SUM), float(n))

    for its in range(ITMAX):
        iter = its
        fret = lnsrch(func, p, fp, g, xi, pnew, stpmax)
        fp = fret
        for i in range(n):
            xi[i] = pnew[i]-p[i]
            p[i] = pnew[i]
        
        test=0.0
        for i in range(n):
            temp = old_div(abs(xi[i]),max(abs(p[i]),1.0))
            if temp > test: test = temp
            
        if test < TOLX:
            return fret, iter
        
        for i in range(n):
            dg[i] = g[i]
            
        df(func, p, func(*p), g)
        test = 0.0
        den = max(fret, 1.0)
        for i in range(n):
            temp = old_div(abs(g[i])*max(abs(p[i]),1.0),den)
            if temp > test: test = temp

        if test < gtol:
            return fret, iter
        
        for i in range(n):
            dg[i] = g[i] - dg[i]
            
        for i in range(n):
            hdg[i] = 0.0
            for j in range(n):
                hdg[i] += hessin[i, j]*dg[j]

        fac = dg*xi
        fae = dg*hdg
        sumdg = dg*dg
        sumxi = xi*xi

        if fac > math.sqrt(EPS*sumdg*sumxi):
            fac = 1./fac
            fad = 1./fae
            for i in range(n):
                dg[i] = fac*xi[i] - fad*hdg[i]

            for i in range(n):
                for j in range(i, n):
                    hessin[i, j] += fac*xi[i]*xi[j] - fad*hdg[i]*hdg[j] + fae*dg[i]*dg[j]
                    hessin[j, i] = hessin[i, j]
                    
        for i in range(n):
            xi[i] = 0.
            for j in range(n):
                xi[i] -= hessin[i, j]*g[j]

    return fret, iter
