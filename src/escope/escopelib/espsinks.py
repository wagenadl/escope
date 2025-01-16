# espsinks.py - This file is part of EScope/ESpark
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


# espsinks.py

from . import espdatasink
from . import espdsnidaq
from . import espdspicodaq

def makeDataSink(cfg, reccfg=None):
    if cfg.hw.adapter[0]=='nidaq':
        return espdsnidaq.ESPDS_Nidaq(cfg)
    elif cfg.hw.adapter[0]=='picodaq':
        if reccfg and reccfg.hw.adapter == cfg.hw.adapter:
            return espdspicodaq.ESPDS_Picodaq_Joint(cfg, reccfg)
        else:
            return espdspicodaq.ESPDS_Picodaq_StandAlone(cfg)
    elif cfg.hw.adapter[0]=='dummy':
        return espdatasink.ESPDS_Dummy(cfg)
    else:
        raise RuntimeError('Unknown adapter type: ' + cfg.hw.adapter[0])
    
