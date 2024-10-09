Using ESpark
============

The ESpark window comprises up to four vertically stacked sections,
each used to configure pulses and pulse trains to be sent to one
analog or digital output. When you click “Run”, all the configured
pulse trains are sent to their respective outputs, with
synchronization between channels. At the end of the longest train, the
run automatically ends, unless you have checked “Repeat”, in which
case output continues indefinitely.


Hardware
--------

Use the “Hardware” button to choose which DAQ board will be used and
the sample rate of the generated signals.


Channels
--------

Use the “Channels” button to configure which outputs are used. If your
output is connected to a device like an AxoClamp, you may like to set
scale factors here. That way, the graphs and configuration buttons on the main screen will display physical units.


Configuring pulses
------------------

ESpark currently supports four pulse types: “Monophasic”, “Biphasic”,
“Ramp”, and “Sine”.

A “Monophasic” pulse is defined simply by its amplitude and duration.

A “Biphasic” pulse is defined by the amplitudes and durations of its
first and second phase, which may be different.

For a “Ramp” pulse, the “Amplitude” defines the starting
voltage of the ramp (which may usefully be set to zero), whereas the
“2nd amp.” defines the final voltage.

For a “Sine” pulse, the “Amplitude” is measured center-to-peak, the
“Duration” is the full period of the wave. The “2nd amp.” is used as
an offset (which may usefully be set to zero), whereas the “2nd. dur.”
is used as a phase shift.

In all cases, the graph above the settings automatically updates to
reflect a preview of the pulse you are about to send out.

Configuring trains
------------------

The right half of the configuration panel is used to define pulse
trains. A full stimulus may comprise any number of trains, each
consisting of any number of pulses. The “Pulse period” and “Train
period” are always measured start-to-start. The “Delay” is mainly
useful when multiple channels are in use. Unless your stimulus
comprises only a single pulse in a single train, the graph
above the train settings reflects the full stimulus.

If there are are multiple pulses in your train(s), the main pulse
parameters define the first pulse within each train, and the
“Chg./pulse” column may be used to modify the subsequent pulses. For
instance, you could create a train in which each subsequent pulse is a
little stronger than the previous by setting the “Chg./pulse” for
“Amplitude” to a positive number. The waveform display is updated to
show all of the pulses, using a lighter shade of blue for all but the
first.

Likewise, if there are multiple trains, the “Chg./train” column may be
used to modify the second and later trains. You can even change the
number of pulses between trains. The waveform display is updated to
show all of the pulses, with pulses from all but the first train
plotted in gray.




Loading and saving configurations
---------------------------------

The “Load” and “Save” buttons may be used to save configured pulses
for later use.
