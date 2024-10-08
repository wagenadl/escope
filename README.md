<img alt="EScope and ESpark" src="https://github.com/wagenadl/escope/blob/main/docs/source/banner.svg" width="100%">
EScope and ESpark are a software oscilloscope and function generator
aimed primarily but not exclusively at electrophysiology.

## Screenshots

EScope running in “demo” mode on Linux without a DAQ card:
<img alt="EScope screenshot" src="https://github.com/wagenadl/escope/blob/main/docs/source/escope.png" width="80%">

ESpark running on Windows:
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

ESpark can output a variety of pulse waveforms either singly or in
programmable trains. Up to four analog or digital channels can be
driven concurrently. The software displays previews of the signals to
be generated making it particularly easy for students to design
complex stimuli.

## Compatibility

EScope and ESpark are compatible with most National Instruments
multifunction data acquisition boards and does not require a LabView
license. The software has been tested on both Windows and
Linux. It will likely work on MacOS as well.

*Important caveat:* National Instruments only fully supports a
shockingly small number of their cards on Linux. (Many are supported
only with “software timing”, which is completely useless.) If they do
not properly support yours, the best I can suggest is that you loudly
demand your money back.

## Prerequisites

To use with NI hardware, you first need to install the NIDAQmx
software. This is not necessary on computers where you only wish to
analyze data you acquired on another computer.

## Installation

Installation is as easy as

    pip install escope
    
## Running

To run the software, open a terminal and type either

    escope

or

    espark
    
