<img alt="EScope" src="https://github.com/wagenadl/escope/blob/main/docs/source/banner.svg" width="100%">
EScope is a software oscilloscope and function generator
aimed primarily but not exclusively at electrophysiology.

## Screenshots

EScope running in “demo” mode on Linux without a DAQ card:

<img alt="EScope screenshot" src="https://github.com/wagenadl/escope/blob/main/docs/source/escope.png" width="80%">

The ESpark module running on Windows:

<img alt="ESpark screenshot" src="https://github.com/wagenadl/escope/blob/main/docs/source/espark.png" width="80%">
                              
## Features

EScope can display traces from up to eight analog inputs
simultaneously, optionally using one of them as a trigger input. As on
physical digital storage oscilloscopes, input signals can be DC or AC
coupled. The vertical gain and offset can be adjusted by dragging
corresponding user interface elements.

EScope can continuously stream acquired data to disk. Alternatively,
individually acquired single sweeps can be saved. A Python module is
included to conveniently load saved data for further analyis.

Through its “ESpark module”, EScope can output a variety of pulse
waveforms either singly or in programmable trains. Up to four analog
or digital channels can be driven concurrently. The software displays
previews of the signals to be generated making it particularly easy
for students to design complex stimuli.

## Compatibility

EScope is compatible with the picoDAQ data acquisition system from Pasadena Neurotech and with most National Instruments
multifunction data acquisition boards. EScope  does not require a LabView
license. The software has been tested on both Windows and
Linux. It will likely work on MacOS as well.

*Important caveat:* National Instruments only fully supports a
shockingly small number of their cards on Linux. (Many are supported
only with “software timing”, which is completely useless.) If they do
not properly support yours, the best I can suggest is that you loudly
demand your money back.

## Prerequisites

To use with NI hardware, you first need to install the NIDAQmx
software.

## Installation

Installation is as easy as

    pip install escope
    
This will pull in several dependencies. You may prefer to set up a
[virtual environment](https://docs.python.org/3/library/venv.html).
    
## Running

To run the software, open a terminal and type

    escope

In Windows, after you run the software in this fashion once, you
should be able to run it from the start menu as well. (If you know
of a way to make “pip” create a start menu entry, please contact
me or open an [Issue](https://github.com/wagenadl/escope/issues).)

## Data analysis

EScope includes 
[a jupyter notebook](https://github.com/wagenadl/escope/blob/main/eg-data/egdata.ipynb) 
showing how to load the data it saves. You can also 
[open it in colab](https://colab.research.google.com/github/wagenadl/escope/blob/main/eg-data/egdata.ipynb). 

## Extended documentation

Full documentation is at [readthedocs.io](https://escope.readthedocs.io).

## License

EScope is licensed under the GPL license, version 3 or—at your choice—any later version. See [LICENSE](LICENSE) for more information.

