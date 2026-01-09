#!/usr/bin/env python3
"""
Cura to CurviSlicer Adapter - FIXED VERSION (Removes Skirt!)
=============================================================
Properly filters out skirt and brim from the G-code.

Usage:
    python cura_to_curvi_FIXED.py after.stl input_cura.gcode output.gcode
"""

import sys
import re
import struct


def read_stl_bounding_box(stl_file):
    """Read STL minimum coordinates."""
    with open(stl_file, 'rb') as f:
        f.read(80)
        num_triangles = struct.unpack('I', f.read(4))[0]
        
        min_x = min_y = min_z = float('inf')
        
        for _ in range(num_triangles):
            f.read(12)
            for _ in range(3):
                x, y, z = struct.unpack('fff', f.read(12))
                min_x = min(min_x, x)
                min_y = min(min_y, y)
                min_z = min(min_z, z)
            f.read(2)
        
        print(f"[INFO] STL minimum: X={min_x:.6f}, Y={min_y:.6f}, Z={min_z:.6f}")
        return min_x, min_y, min_z


def extract_layer_height(lines):
    """Extract layer height from comments."""
    for line in lines:
        if line.startswith(';Layer height:'):
            match = re.search(r';\s*Layer height:\s*([\d.]+)', line)
            if match:
                return float(match.group(1))
    return 0.2


def find_first_wall_coords(lines):
    """Find the minimum X,Y from the first wall/skin movements."""
    print("[INFO] Finding first wall coordinates...")
    
    in_wall_or_skin = False
    min_x = min_y = float('inf')
    count = 0
    max_to_check = 100
    
    for line in lines:
        line = line.strip()
        
        # Check if we're in wall or skin
        if ';TYPE:WALL' in line or ';TYPE:SKIN' in line:
            in_wall_or_skin = True
            continue
        elif ';TYPE:' in line:
            if count > 0:
                break
            in_wall_or_skin = False
            continue
        
        if not in_wall_or_skin:
            continue
        
        # Extract X and Y from G0/G1 moves
        if line.startswith('G0 ') or line.startswith('G1 '):
            x_match = re.search(r'X([\d.]+)', line)
            y_match = re.search(r'Y([\d.]+)', line)
            
            if x_match and y_match:
                x = float(x_match.group(1))
                y = float(y_match.group(1))
                min_x = min(min_x, x)
                min_y = min(min_y, y)
                count += 1
                
                if count >= max_to_check:
                    break
    
    if min_x == float('inf'):
        print("[ERROR] Could not find wall coordinates!")
        sys.exit(1)
    
    print(f"[INFO] First wall minimum: X={min_x:.2f}, Y={min_y:.2f} (from {count} moves)")
    return min_x, min_y


def filter_gcode(stl_file, input_file, output_file):
    """Main conversion."""
    print("[INFO] Starting conversion...")
    
    # Read STL
    stl_min_x, stl_min_y, stl_min_z = read_stl_bounding_box(stl_file)
    
    # Read G-code
    with open(input_file, 'r') as f:
        lines = f.readlines()
    
    # Extract layer height
    layer_height = extract_layer_height(lines)
    print(f"[INFO] Layer height: {layer_height}")
    
    # Find first wall coordinates
    gcode_min_x, gcode_min_y = find_first_wall_coords(lines)
    
    # Calculate offset
    offset_x = stl_min_x - gcode_min_x
    offset_y = stl_min_y - gcode_min_y
    offset_z = stl_min_z
    
    print(f"[INFO] Calculated offset:")
    print(f"       X = {stl_min_x:.6f} - {gcode_min_x:.6f} = {offset_x:.6f}")
    print(f"       Y = {stl_min_y:.6f} - {gcode_min_y:.6f} = {offset_y:.6f}")
    print(f"       Z = {stl_min_z:.6f}")
    
    # Find where actual print starts
    print_start_line = None
    for i, line in enumerate(lines):
        if ';LAYER:0' in line:
            print_start_line = i
            break
    
    # Filter G-code - KEY CHANGE: Track TYPE and skip SKIRT/BRIM
    filtered_lines = []
    removed_count = 0
    current_type = None  # Track current TYPE
    
    for i, line in enumerate(lines):
        # Before print starts, only keep comments
        if i < print_start_line:
            if line.strip().startswith(';'):
                filtered_lines.append(line)
            else:
                removed_count += 1
            continue
        
        line_stripped = line.strip()
        
        if not line_stripped:
            continue
        
        # Track TYPE changes
        if ';TYPE:' in line_stripped:
            current_type = line_stripped
            # Keep the TYPE comment
            filtered_lines.append(line)
            continue
        
        # Keep other comments
        if line_stripped.startswith(';'):
            filtered_lines.append(line)
            continue
        
        # CRITICAL: Skip movements if we're in SKIRT or BRIM
        if current_type and (';TYPE:SKIRT' in current_type or ';TYPE:BRIM' in current_type):
            if line_stripped.startswith('G'):
                removed_count += 1
                continue
        
        # Remove M-codes and G28
        if line_stripped.startswith('M') or line_stripped.startswith('G28'):
            removed_count += 1
            continue
        
        # Keep all other G-codes (when not in skirt/brim)
        if line_stripped.startswith('G'):
            filtered_lines.append(line)
            continue
        
        removed_count += 1
    
    print(f"[INFO] Removed {removed_count} lines (including skirt/brim)")
    print(f"[INFO] Kept {len(filtered_lines)} lines")
    
    # Write output
    with open(output_file, 'w') as f:
        f.write(f"o X {offset_x:.6f} Y {offset_y:.6f} Z {offset_z:.6f}\n")
        f.write(f"t {layer_height}\n")
        f.write("; Converted from Cura (skirt/brim removed)\n")
        f.write(";\n")
        
        for line in filtered_lines:
            f.write(line)
    
    print(f"[INFO] Done! Output: {output_file}")


def main():
    if len(sys.argv) != 4:
        print(f"Usage: {sys.argv[0]} <after.stl> <cura.gcode> <output.gcode>")
        sys.exit(1)
    
    stl_file = sys.argv[1]
    input_file = sys.argv[2]
    output_file = sys.argv[3]
    
    filter_gcode(stl_file, input_file, output_file)


if __name__ == "__main__":
    main()
