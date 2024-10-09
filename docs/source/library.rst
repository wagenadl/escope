Python library
==============

The Python library consists primarily of the “escope” package. Typical
use would be something like::

    import matplotlib.pyplot as plt
    import escope
    
    rec = escope.Recording("/some/path/EScopeData/20241007-123412.escope")
    rec.plot()

followed by::
    
    vv1 = rec.data(0, "mV")
    tt = rec.time()
    plt.plot(tt, vv1)


escope package
--------------

.. autoclass:: escope.Recording
    :members:
       
.. autofunction:: escope.rmsnoise
   
.. autofunction:: escope.detectspikes
                  
                  
Submodules
----------

.. toctree::
   :maxdepth: 1
   :caption: Details on the following submodules are available:

   units
   peakx
   spikex

