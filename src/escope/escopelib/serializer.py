# serializer.py - This file is part of EScope/ESpark
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


import json
from .Struct import Struct
from .espconfig import Monovalue, Bivalue, Trivalue, Pulsetype
import numpy as np


class Encoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, Struct):
            dct = {"__type__": "Struct"}
            for k, v in obj.__dict__.items():
                dct[k] = v
            return dct
        elif isinstance(obj, Monovalue):
            return {"__type__": "Mono", "base": obj.base}
        elif isinstance(obj, Bivalue):
            return {"__type__": "Bi", "base": obj.base, "delta": obj.delta}
        elif isinstance(obj, Trivalue):
            return {"__type__": "Tri", "base": obj.base, "delta": obj.delta, "delti": obj.delti}
        elif isinstance(obj, Pulsetype):
            return {"__type__": "Pulse", "value": obj.value}
        elif isinstance(obj, np.ndarray):
            return {"__type__": "array", "shape": list(obj.shape), "data": list(obj.flatten())}
        else:
            return super().default(obj)

        
def decode(dct):
    if "__type__" in dct:
        typ = dct["__type__"]
        if typ=="Struct":
            return Struct(**{k: decode(v) if type(v)==dict else v
                             for k, v in dct.items()})
        elif typ == "Mono":
            return Monovalue(dct["base"])
        elif typ == "Bi":
            return Bivalue(dct["base"], dct["delta"])
        elif typ == "Tri":
            return Trivalue(dct["base"], dct["delta"], dct["delti"])
        elif typ == "Pulse":
            return Pulsetype(dct["value"])
        elif typ == "array":
            return np.array(dct["data"]).reshape(dct["shape"])
    return dct

        
def dump(obj, fd):
    json.dump(obj, fd, cls=Encoder, indent=2)

    
def load(fd):
    return json.load(fd, object_hook=decode)
