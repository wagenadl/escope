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
            return super().default()

def decoder(dct):
    if "__type__" in dct:
        typ = dct["__type__"]
        if typ=="Struct":
            return Struct(**dct)
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
        else:
            return dct

def dump(obj, fd):
    json.dump(obj, fd, cls=Encoder, indent=2)

def load(fd):
    return json.load(fd, object_hook=decoder)
