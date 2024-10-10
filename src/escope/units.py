# units.py - This file is part of EScope/ESpark
# (C) 2024  Daniel A. Wagenaar
#
# EScope and ESpark are free software: you can redistribute it
# and/or modify it under the terms of the GNU General Public License
# as published by the Free Software Foundation, either version 3 of
# the License, or (at your option) any later version.
#
# EScope and ESpark are distributed in the hope that it will be
# useful, but WITHOUT ANY WARRANTY; without even the implied warranty
# of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this software. If not, see <http://www.gnu.org/licenses/>.


import re
import numpy as np
from typing import Optional

#%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
#% Prepare unit database
def _mkunitcode():
    units = 'mol A g m s'.split(' ')
    uc = {}
    U = len(units)
    for u in range(U):
        vec = np.zeros(U)
        vec[u] = 1
        uc[units[u]] = vec
    uc[1] = np.zeros(U)
    return uc

_unitcode = _mkunitcode()


def _decodeunit(u):
    return _unitcode[u].copy()


def _mkprefix():
    prefix = {'d': -1, 'c': -2,
              'm': -3, 'u': -6, 'n': -9, 'p': -12, 'f': -15,
              'k': 3, 'M': 6, 'G': 9, 'T': 12, 'P': 15}
    altprefix = ['deci=d',
                  'centi=c',
                  'milli=m',
                  'micro=μ=u',
                  'nano=n',
                  'pico=p',
                  'femto=f',
                  'kilo=k',
                  'mega=M',
                  'giga=G',
                  'tera=T',
                  'peta=P']
    for ap in altprefix:
        bits = ap.split('=')
        val = bits.pop()
        for b in bits:
            prefix[b] = prefix[val]
    return prefix

_prefix = _mkprefix()


def _mkunitmap():
    altunits = ['meter=meters=m', 
                 'second=seconds=sec=secs=s', 
                 'gram=grams=gm=g',
                 'lb=lbs=pound=453.59237 g',
                 'amp=amps=ampere=amperes=Amp=Ampere=Amperes=A',
                 'min=minute=60 s',
                 'h=hour=60 min',
                 'day=24 hour',
                 'in=inch=2.54 cm',
                 'l=L=liter=liters=1e-3 m^3',
                 'Hz=Hertz=hertz=cyc=cycles=s^-1',
                 'C=Coulomb=coulomb=Coulombs=coulombs=A s',
                 'N=newton=Newton=newtons=Newtons=kg m s^-2',
                 'lbf=4.4482216 kg m / s^2',
                 'J=joule=joules=Joule=Joules=N m',
                 'W=watt=Watt=watts=Watts=J s^-1',
                 'V=Volt=volt=Volts=volts=W A^-1',
                 'Pa=pascal=Pascal=N m^-2',
                 'bar=1e5 Pa',
                 'atm=101325 Pa',
                 'torr=133.32239 Pa',
                 'psi=6894.7573 kg / m s^2',
                 'Ohm=Ohms=ohm=ohms=V A^-1',
                 'mho=Mho=Ohm^-1',
                 'barn=1e-28 m^2',
                 'M=molar=mol l^-1']
    unitmap = {}
    for au in altunits:
        bits = au.split('=')
        val = bits.pop()
        for b in bits:
            unitmap[b] = val
    return unitmap

_unitmap = _mkunitmap()


def _fracdecode(s):
    #return [mul,code]
    idx = s.find('/')
    if idx<0:
        numer = s
        denom = ''
    else:
        numer = s[:idx]
        denom = s[idx+1:].replace('/', ' ')

    multis = [ numer, denom ]
    mul = []
    code = []
    for q in range(2):
        mul.append(1)
        code.append(_decodeunit(1))
        factors = multis[q].split(' ')
        for fac in factors:
            mu, co = _factordecode(fac)
            mul[q] *= mu
            code[q] += co
    mul = mul[0]/mul[1]
    code = code[0] - code[1]
    return mul, code


_numre = re.compile('^[-0-9+.]')
def _factordecode(fac):
    if _numre.search(fac):
        # It's a number
        return float(fac), _decodeunit(1)

    idx = fac.find('^')
    if idx>=0:
        base = fac[:idx]
        powfrac = fac[idx+1:]
        if powfrac.find('^')>0:
            raise ValueError('Double exponentiation')
        idx = powfrac.find('|')
        if idx>=0:
            pw = float(powfrac[:idx]) / float(powfrac[idx+1:])
        else:
            pw = float(powfrac)
    else:
        base=fac
        pw = 1

    # Let's decode the UNIT
    if base=='':
        return 1., _decodeunit(1)
    elif base in _unitcode:
        # It's a base unit without a prefix
        mu = 1
        co = _decodeunit(base)*pw
        return mu, co
    elif base in _unitmap:
        mu, co = _fracdecode(_unitmap[base])
        mu = mu**pw
        co = co*pw
        return mu, co
    else:
        # So we must have a prefix
        for pf in reversed(_prefix):
            if base.startswith(pf):
                L = len(pf)
                mu, co = _fracdecode(base[L:])
                mu *= 10**_prefix[pf]
                mu = mu**pw
                co = co*pw
                return mu, co
    raise ValueError(f'I do not know any unit named “{fac}”')


class Units:
    '''Class for unit conversion
    
    Examples
    --------
    
      Units("4 lbs").asunits("kg") → 1.814
    
      Units("3 V / 200 mA").asunits("Ohm") → 15.0

      Units("psi").definition() → "6894.7573 kg m^-1 s^-2"

    Syntax
    ------
    
    The full syntax for unit specification is:
    
    BASEUNIT
        m | s | g | A | mol
    
    PREFIX
        m | u | n | p | f | k | M | G | T
    
    ALTUNIT
        meter | meters | second | seconds | sec | secs |
        gram | grams | gm | amp | amps | ampere | amperes | 
        Amp | Ampere | Amperes
    
    ALTPREFIX
        milli | micro | μ | nano | pico | femto | kilo |
        mega | Mega | giga | Giga | tera | Tera
    
    DERIVEDUNIT
        in | inch | Hz | Hertz | hertz | cyc | cycles |
        V | volt | Volt | volts | Volts |
        N | newton | Newton | newtons | Newtons |
        Pa | pascal | bar | atm | torr |
        J | joule | joules | Joule | Joules |
        barn |
        Ohm | Ohms | ohm | ohms | mho | Mho
    
    UNIT
        (PREFIX | ALTPREFIX)? (BASEUNIT | ALTUNIT | DERIVEDUNIT)

    DIGITS
        [0-9]

    INTEGER
        ('-' | '+')? DIGIT+

    NUMBER
        ('-' | '+')? DIGIT* ('.' DIGIT*)? ('e' ('+' | '-') DIGIT*)?

    POWFRAC
        INTEGER ('|' INTEGER)?

    POWERED
        UNIT ('^' POWFRAC)?

    FACTOR
        POWERED | NUMBER

    MULTI
        FACTOR (' ' MULTI)?

    FRACTION
        MULTI ('/' MULTI)?
    
    Thus, the following would be understood:
    
      'kg m / s^2'
          That's a newton
    
      'J / Hz^1|2'
          Joules per root-Hertz
    
    Notes
    -----
    
    Multiplication is implicit; do not attempt to write '*'.
    
    Fractions in exponents must be written with '|' rather than '/',
    as '|' binds more tightly than '^'.
    
    Division marked by '/' binds most loosely, e.g,
    
       'kg / m s' – kilogram per meter per second
    
    Syntax checking is not overly rigorous. Some invalid expressions may
    return meaningless values without a reported error.
    
    '''

    def __init__(self, value: float | np.ndarray | str,
                 unit: Optional[str] = None):
        '''Store a value with associated units
        
        UNITS(value, units), where VALUE is a number and UNITS a string,
        stores the given quantity. For instance, UNITS(9.81, 'm / s^2').
        For convenience, UNITS('9.81 m/s^2') also works.
        
        '''
        
        if unit is None:
            unit = value
            value = 1
        self.value = value
        self.mul, self.code = _fracdecode(unit)

        
    def definition(self, withoutvalue=False):
        '''Definition of stored value in SI units

        Parameters
        ----------

        withoutvalue
           If given as True, only the base unit is returned, not the
           value-with-units

        Returns
        --------
        The definition of the stored unit in terms of SI base units.

        Examples
        --------

        Units("2 lb").definition() → “0.907 kg”
        
        Units("psi").definition(True) → “kg m^-1 s^-2”
        
        '''
        val = self.value * self.mul
        ss = []
        for un, co in zip(_unitcode.keys(), self.code):
            if un=='g':
                val /= 1000**co
                un = 'kg'
            if co==0:
                pass
            elif co==1:
                ss.append(un)
            elif co==int(co):
                ss.append(f'{un}^{int(co)}')
            else:
                ss.append(f'{un}^{co}')
        if not withoutvalue:
            ss.insert(0, f'{val}')
        return ' '.join(ss)

                
    def asunits(self, newunit: str, warn=False) -> float | np.ndarray:
        '''Convert to different units

        Parameters
        ----------

        newunit
            string representation of unit to convert to

        Returns
        -------

        The conversion result. The shape and data type of the result
        will match the original *value* passed into the *Units*
        constructor.

        Notes
        ------
        
        An exception is raised if the units are incompatible.

        Optional argument WARN, if True, turns that into a warning.

        See the class documentation for unit syntax and note that
        addition or subtraction is not supported.
        '''
        newmul, newcode = _fracdecode(newunit)
        if np.any(self.code != newcode):
            if warn:
                print(f'WARNING: Units {newunit} do not match {self.definition(True)}')
            else:
                raise ValueError(f'Units {newunit} do not match {self.definition(True)}')
        return self.value * self.mul / newmul

