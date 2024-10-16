.. image:: banner.svg
           :width: 900
           :align: center
           :class: no-scaled-link

Introduction
============

EScope and ESpark are a software oscilloscope and function generator
aimed primarily but not exclusively at electrophysiology.



Screenshots
-----------


.. figure:: escope.png
    :width: 600
    :align: center
    :class: no-scaled-link

    EScope running in “demo” mode on Linux without a DAQ card
                   
                   
.. figure:: espark.png
    :width: 600
    :align: center
    :class: no-scaled-link

    ESpark running on Windows
              
Features
--------

EScope can display traces from up to eight analog inputs
simultaneously, optionally using one of them as a trigger input. As on
physical digital storage oscilloscopes, input signals can be DC or AC
coupled. The vertical gain and offset can be adjusted by dragging
corresponding user interface elements.

EScope can continuously stream acquired data to disk. Alternatively,
individually acquired single sweeps can be saved. A Python module is
included to conveniently load saved data for further analysis.

ESpark can output a variety of pulse waveforms either singly or in
programmable trains. Up to four analog or digital channels can be
driven concurrently. The software displays previews of the signals to
be generated making it particularly easy for students to design
complex stimuli.

Actual installation
===================

Compatibility
-------------

EScope and ESpark are compatible with most National Instruments
multifunction data acquisition boards and does not require a LabView
license. ESpark will *not* work with boards that do not support
“hardware-timed” analog output.

The software has been tested on both Windows and
Linux. It will likely work on MacOS as well.

*Important caveat:* National Instruments only fully supports a
shockingly small number of their cards on Linux. (Many are supported
only with “software timing”, which is completely useless.) If they do
not properly support yours, the best I can suggest is that you
(politely but firmly) demand your money back.

Prerequisites
-------------

To use with NI hardware, you first need to install the NIDAQmx
software. This is not necessary on computers where you only wish to
analyze data you acquired on another computer.

Installation
------------

Installation is as easy as::

    pip install escope
    
Using the software
==================

Running from the command prompt
-------------------------------

.. container:: compound

    To run the software, open a terminal and type either::
    
        escope
    
    or::
    
        espark

In Windows, after you run the software in this fashion once, you
should be able to run it from the start menu as well. (If you know of
a way to make “pip” create a start menu entry, please contact me or
open an `Issue on github <https://github.com/wagenadl/escope/issues>`_.)


EScope includes `a jupyter notebook <https://github.com/wagenadl/escope/blob/main/eg-data/egdata.ipynb>`_
showing how to load the data it saves. You can also `open it in colab <https://colab.research.google.com/github/wagenadl/escope/blob/main/eg-data/egdata.ipynb>`_.

User guides
-----------

For more details on how to use the software, read these chapters:

.. toctree::
   :maxdepth: 1

   escope-bin
   espark-bin
   library

Development
===========

Development occurs on `github <https://github.com/wagenadl/escope>`_.

License information
===================

EScope and ESpark are free software. Read what that means here:
 
.. toctree::
   :maxdepth: 1

   license
