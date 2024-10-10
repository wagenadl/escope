# Struct.py - This file is part of EScope/ESpark
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


class Struct(object):
    def __init__(self, **kwargs):
        for k, v in kwargs.items():
            self.__dict__[k] = v
            
    def __repr__(self):
        kk=list(self.__dict__.keys())
        kk.sort()
        bits = [k + '=' + repr(self.__dict__[k]) for k in kk]
        return 'Struct(' + ', '.join(bits) + ')'
    
    def __str__(self):
        kk=list(self.__dict__.keys())
        kk.sort()
        bits = [k + '=' + repr(self.__dict__[k]) for k in kk]
        return 'Struct( ' + ',\n  '.join(bits) + ' )'
