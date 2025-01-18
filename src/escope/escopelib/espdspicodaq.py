# espdspicodaq.py - This file is part of EScope/ESpark
# (C) 2024  Dapicoel A. Wagenaar
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


from .espdsxxdaq import ESPDS_xxdaq
from . import espicodaq
from .espdatasink import ESPDS_Dummy

class ESPDS_Picodaq_StandAlone(ESPDS_xxdaq):
    def __init__(self, cfg):
        super().__init__(cfg)
        self.GenTask = espicodaq.FiniteProdTask
        
class ESPDS_Picodaq_Joint(ESPDS_Dummy):
    def __init__(self, cfg, reccfg):
        super().__init__(cfg)
        self.reccfg = reccfg

    def join(self, acqtask):
        """Join gentask with acqtask
        """
        if self.cfg.hw.adapter == self.reccfg.hw.adapter:
            print("join", self.chans)
            acqtask.feedstimdata(self.dat)
