#!/usr/bin/env python3
"""
Post processing script for PrusaSlicer for Prusa MK4S

This script will randomise the purge line to one of five positions.

The nozzle cleaning and probing near the purge line is also moved.

It will also orient the purge line such that the extruder doesn't cross
it in the Y-axis when moving to the start of the first object.

Usage:
Add to the Post-processing scripts in PrusaSlicer (Print Settings > Output options)
/path/to/script/purgeShift_x_mk4s.py [inclusion mask];

Inclusion mask is an optional five binary digits denoting which purge positions to include.
For example, if you have a build plate that you have only used with default settings,
position 0 may be well worn, so you would specify 01111.

Scott Wannell
2025-07-15
"""

import re
import sys
import random

# Randomly select purge slot from valid slots
def select_purge_slot(inclusion_mask):
    if inclusion_mask is None:
        # No mask provided, randomly select from all slots
        return random.randint(0, 4)
    
    # Build list of valid slots
    valid_slots = [i for i, bit in enumerate(inclusion_mask) if bit == '1']
    
    # Pick randomly from valid slots
    return random.choice(valid_slots)

# Parameter check 
if len(sys.argv) < 2 or len(sys.argv) > 3:
    print("Usage: python purgeShift_x_mk4s.py [inclusion mask] filename.gcode")
    print("       inclusion mask (optional): 5-bit binary string, e.g. 01111")
    print("       filename.gcode: path to the G-code file")
    sys.exit(1)

inclusion_mask = None
gcode_file = None

if len(sys.argv) == 2:
    # Only filename provided
    gcode_file = sys.argv[1]
    inclusion_mask = "11111"
elif len(sys.argv) == 3:
    # Additional argument provided, PrusaSlicer adds the filename to the end of our arguments
    gcode_file = sys.argv[2]
    # Check inclusion mask is sfive binary digits with at least one 1
    inclusion_mask_given = sys.argv[1]
    if re.fullmatch(r'[01]{5}', inclusion_mask_given) and '1' in inclusion_mask_given:
        inclusion_mask = inclusion_mask_given
    else:
        print(f"ERROR: The inclusion mask must be five binary digits and have at least one 1.  You specified '{inclusion_mask_given}.'")
        sys.exit(1)

# Open file
try:
    with open(gcode_file, "r") as f:
        lines = f.readlines()
except FileNotFoundError:
    print(f"ERROR: File '{gcode_file}' not found.")
    sys.exit(1)
except PermissionError:
    print(f"ERROR: Permission denied reading file '{gcode_file}'.")
    sys.exit(1)
except Exception as e:
    print(f"ERROR: Could not read file '{gcode_file}': {e}")
    sys.exit(1)

# Randomly choose from valid purge slots (provided or all)
selected_purge_slot = select_purge_slot(inclusion_mask)
print(f"Purge slot {selected_purge_slot} will be used.")

# Compile regex patterns for X and Y values
# (negative X for adaptation to other printers or purge procedures)
# g0_pattern = re.compile(r'^(G0.*?)$', re.IGNORECASE)
x_pattern = re.compile(r"\bX(-?\d+\.?\d*)", re.IGNORECASE)
y_pattern = re.compile(r"\bY(-?\d+\.?\d*)", re.IGNORECASE)
#w_pattern = re.compile(r"\bW(-?\d+\.?\d*)", re.IGNORECASE)

# Select X offset
# This will be the start or end of the purge, depending on direction
# The purge travels 51mm, but is only on the bed for 36mm,
# so we can use 46mm spacing to fit five purge lines
offset = selected_purge_slot * 46

# Find the start X coordinate of the first object
first_object_start_x = None

# Find the first G1 line with a positive Y value and extract the X coordinate
for line in lines:
    if line.upper().startswith("G1 X"):
        y_match = y_pattern.search(line)
        if y_match:
            y_val = float(y_match.group(1))
            if y_val > 0:
                # I could regex this but we rely on X being first already
                parts = line.split()
                x_val = float(parts[1][1:])
                first_object_start_x = x_val
                print(f"The first object start X coordinate is X{first_object_start_x}")
                break

if first_object_start_x is None:
    print("ERROR: Failed to locate start coordinates of first object.  Syntax may have changed, please raise an issue.")
    sys.exit(1)

# Determine purge direction
# The default purge starts at 0 and ends at 51 and is only on the bed from 15 to 51.
# I want to preserve the on bed positions in either direction, so our full range is 0 to 66 (51 + 15)

purge_lower_x = offset + 0
purge_upper_x = offset + 66

dist_lower = abs(first_object_start_x - purge_lower_x)
dist_upper = abs(first_object_start_x - purge_upper_x)

reverse_purge = dist_upper > dist_lower

# Process the gcode file lines

in_purge_block = False
purge_block_processed = False

output_lines = []

def shift_x(match):
    x_val = float(match.group(1))
    return f"X{round(x_val + offset, 1)}"

def shift_flip_x(match):
    x_val = float(match.group(1))
    if reverse_purge:
        return f"X{round(offset + 66 - x_val, 1)}"
    else:
        return f"X{round(x_val + offset, 1)}"

def shift_w(match):
    w_val = float(match.group(1))
    return f"W{round(x_val + offset, 1)}"

for line in lines:
    stripped = line.strip()
    
    if not purge_block_processed:
        
        if not in_purge_block:
            # Check for start of purge block: first G0 with negative Y (the bed leveling uses G1 with negative Y before this)
            if stripped.upper().startswith("G0"):
                y_match = y_pattern.search(stripped)
                if y_match:
                    y_value = float(y_match.group(1))
                    if y_value < 0:
                        in_purge_block = True
            else:
                # We are in the probe block, offset X and W
                if stripped.upper().startswith(("G1", "G29")):
                    line = x_pattern.sub(shift_x, line)
                    #line = w_pattern.sub(shift_w, line)

        # If we are in the purge block, modify X on G0 lines
        if in_purge_block:
            if stripped.upper().startswith("G0"):
                # Look for X coordinate and shift it
                line = x_pattern.sub(shift_flip_x, line)

            # Look for end: first G1 with positive Y
            if stripped.startswith("G1"):
                y_match = y_pattern.search(stripped)
                if y_match:
                    y_value = float(y_match.group(1))
                    if y_value > 0:
                        in_purge_block = False # Unnecessary, added to avoid future trip up
                        purge_block_processed = True

    output_lines.append(line)

# Write changes
with open(gcode_file, "w") as f:
    f.writelines(output_lines)

print(f"Sucessfully updated purge line position.")
input("Press Enter to continue...")