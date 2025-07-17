# PrusaSlicer-scripts

**purgeShift_x_mk4s.py**

My build plates are getting worn in the purge area, so I made a script to randomise the position.  It might work already for the MK4S predecessors and the Core One, I’ll look at the profiles of those and may also look at the XL later.

Rather than absolute random placement, I'm using five slots here so that I wear the plate in the same manner as someone not using this script, just in five times the number of positions.

The purge line probing, nozzle cleaning and purge line itself are all moved.

The script also determines the starting X coordinate of the first object and orients the purge line to avoid crossing it when moving to the first object’s starting point.


Usage

See here: https://help.prusa3d.com/article/post-processing-scripts_283913

You will also need to uncheck "Use binary G-code when the printer supports it" in Configuration > Preferences > Other
There is an issue open for this: https://github.com/prusa3d/PrusaSlicer/issues/13736

You can optionally add a five-bit position mask to exclude positions.  For example, to exclude position 0 - as I have with my well-worn plates - use 01111
