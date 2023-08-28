# espsinks.py

import espdatasink
import espdsnidaq

def makeDataSink(cfg):
    if cfg.hw.adapter[0]=='nidaq':
        return espdsnidaq.ESPDS_Nidaq(cfg)
    elif cfg.hw.adapter[0]=='dummy':
        return espdatasink.ESPDS_Dummy(cfg)
    else:
        raise RuntimeError('Unknown adapter type: ' + cfg.hw.adapter[0])
    
