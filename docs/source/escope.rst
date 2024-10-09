Using EScope
============

EScope starts with a nearly blank screen. To start displaying traces,
click the “Run” button. The “LED” will turn bright green. By default,
data is acquired from the first two channels of your first DAQ card.

To select which DAQ card to use, click the “Hardware” button. This
opens a dialog where you can also set the sampling rate.

To select which channels to display, click the “Channels” button. In
the resulting dialog, you can also change scale factors. This allows
EScope to display physically correct voltage or current scales when
you use, e.g., a 10× probe or are reading from one of the scaled
outputs of an AxoClamp amplifier.

On the main screen, you can change the vertical offset of each channel
by dragging the handles on the left. You can also change the vertical
zoom of each channel by dragging the scale bars on the right. You can
change the horizontal zoom by dragging the scale bar below the trace
display. Scrolling your mouse wheel while hovering over any scale bar
also works.


Triggering
----------

By default, EScope continuously displays the data as they come
in. Often, however, it is useful to make display contingent on an
external event. For instance, you might have one channel teed to a
stimulus marker and another channel record a neuronal response. In
that case, the “Trigger” menu allows you to align subsequent traces on
an upward or downward transition on a chosen channel. In trigger mode,
traces align on the triangle marker below the main screen. This marker
can be dragged left or right. Use the “Auto trigger” mode to make
EScope pretend it sees a trigger when there is a long time between
actual triggers.

Saving acquired data
--------------------

In typical operation, it is most convenient to stream the data to disk
as they are acquired. This is achieved by checking the “Capture”
button. (Nothing happens unless “Run” is also clicked.) Files are
saved in Documents/EScopeData using filenames constructed as
YYYYMMDD-HHMMSS timestamps. For every “Capture” there will be three
files: one with “.escope” extension that contains the metadata for the
recording in json format; one with “.dat” extension that contains the
actual data; and one with “.config” extension that contains the full
configuration of EScope at the time of recording. The “LED” turns red
while actively capturing data.

In addition to recording data continuously, you can also save a single
sweep. This is useful if you did not have “Capture” enabled, but some
interesting event appeared on the screen. Best to click “Stop” first,
to keep a spurious trigger from overwriting the display. Then click
“Save Sweep”. This saves a trio of files in the Documents/EScopeData
with a sweep number appended to the usual timestamp.

You can see the timestamp and sweep number on the top right of the
display, so it is easy to copy these into your notes.


Loading previously saved data
-----------------------------

You can reload previously saved data by pressing the “Load Sweep”
button. This will load either the single sweep saved by “Save Sweep”,
or the final sweep of a longer “Capture”. While this functionality can
be useful to quickly inspect a series of saved sweep, for more
advanced analysis, it is generally preferably to load data into a
separate Python session (or Jupyter notebook) using the
:ref:`escope library <library>`. 
