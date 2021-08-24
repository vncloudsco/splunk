from __future__ import division
from builtins import range
import math


# Increment an integer in mirrored order.
# For example, if one starts with x = 0 and uses m = 4, applying the function 8
# times will produce the sequence 0, 4, 2, 6, 1, 5, 3, 7 (ie, incre_rev(0,4) = 4, incre_rev(4,4) = 2, and so on).
# That is the sequence obtained by applying the mirror transformation to each term of  0, 1, 2, 3, 4, 5, 6, 7
# where each term is viewed as a 3-bit sequence. The number m specifies the number of bits with which each term should be viewed.
# So m = 4 specifies 3 bits, as 4 = 100 in binary. Another example: m = 8 = 1000 specifies 4 bits. In particular, the parameter m must be a power of 2.
# The mirror transformation of 1 = 001 is 100 = 4, of 2 = 010 is 010 = 2, of 3 = 011 is 110 = 6, etc.
# This algorithm is taken from "Hacker's Delight" by Henry Warren, Chapter 7, section "Incrementing
# a Reversed Integer"
def incre_rev (x, m):
    y = x ^ m
    if y >= 0:
        while y < m:
            m = m >> 1
            y = y ^ m
    return y

# Permute a given sequence according to mirror order.
# For example, if a = [a0,a1,a2,a3,a4,a5,a6,a7] then A = [a0,a4,a2,a6,a1,a5,a3,a7].
# len(a) must be a power of 2
def bit_reverse (a, A):
    m = len(a) // 2 
    rev_idx = 0
    for t in a:
        A[rev_idx] = t
        rev_idx = incre_rev(rev_idx, m)


# Cooley-Tukey Fast Fourier Transform as described in
# "Introduction to Algorithms, 3rd edition" by Cormen-Leiserson-Rivest-Stein, page 917.
def fft (a):
    n = len(a) # n must be a power of 2
    e = int(math.log(n, 2))
    A = list(range(n))
    bit_reverse(a, A)
    
    for s in range(1, e+1):
        m = int(math.pow(2, s))
        phi = 2*math.pi/m
        w_m = complex(math.cos(phi), math.sin(phi))
        # w_m = cmath.rect(1, 2*cmath.pi/m) (if cmath is available) 
        for k in range(0, n, m):
            w = 1
            for j in range(0, m // 2):
                t = w*A[k+j+ m // 2]
                u = A[k+j]
                A[k+j] = u + t
                A[k+j+ m // 2] = u - t
                w = w*w_m
    return A
                
