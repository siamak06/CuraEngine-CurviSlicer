#!/bin/bash
################################################################################
# CuraEngine-CurviSlicer Fully Automated Pipeline
# 
# This script automates the entire curved slicing process using CuraEngine:
# 1. Runs curvislice_osqp to create curved after.stl
# 2. Runs CuraEngine to slice the curved model (command-line, no GUI!)
# 3. Converts CuraEngine G-code to CurviSlicer format
# 4. Runs uncurve to apply curves
# 5. Outputs final curved G-code ready to print
#
# Usage: ./automated_curved_slicer.sh <input.stl> [layer_height]
#
# Example: 
#   ./automated_curved_slicer.sh models/Calib_Cube.stl 0.2
#   ./automated_curved_slicer.sh models/wing.stl 0.3
#
################################################################################

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Script directory
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

# Default values
LAYER_HEIGHT=0.2

################################################################################
# Configuration - EDIT THESE PATHS FOR YOUR SYSTEM
################################################################################

CURAENGINE_WRAPPER="${SCRIPT_DIR}/curaengine_wrapper.sh"
CURA_DEFINITIONS_PATH="${HOME}/squashfs-root/share/cura/resources/definitions"
CURVI_DEFINITION="${SCRIPT_DIR}/curvi.def.json"
PYTHON_CONVERTER="${SCRIPT_DIR}/cura_to_curvi_FINAL.py"
TETWILD_EXE="${SCRIPT_DIR}/tools/tetwild/TetWild.exe"
CURVISLICE_BIN="${SCRIPT_DIR}/bin/curvislice_osqp"
UNCURVE_BIN="${SCRIPT_DIR}/bin/uncurve"
LIBOSQP_PATH="${SCRIPT_DIR}/bin"

################################################################################
# Functions
################################################################################

print_header() {
    echo -e "${CYAN}╔════════════════════════════════════════════════════════════════╗${NC}"
    echo -e "${CYAN}║${NC} ${BLUE}$1${NC}"
    echo -e "${CYAN}╚════════════════════════════════════════════════════════════════╝${NC}"
}

print_success() {
    echo -e "${GREEN}✓ $1${NC}"
}

print_error() {
    echo -e "${RED}✗ ERROR: $1${NC}"
}

print_info() {
    echo -e "${YELLOW}→ $1${NC}"
}

print_step() {
    echo -e "${CYAN}═══ $1 ═══${NC}"
}

check_file_exists() {
    if [ ! -f "$1" ]; then
        print_error "File not found: $1"
        exit 1
    fi
}

check_dependencies() {
    print_step "Checking Dependencies"
    
    local missing_deps=0
    
    if [ ! -f "$CURAENGINE_WRAPPER" ]; then
        print_error "CuraEngine wrapper not found: $CURAENGINE_WRAPPER"
        missing_deps=1
    else
        print_success "CuraEngine wrapper found"
    fi
    
    if [ ! -d "$CURA_DEFINITIONS_PATH" ]; then
        print_error "Cura definitions not found: $CURA_DEFINITIONS_PATH"
        missing_deps=1
    else
        print_success "Cura definitions found"
    fi
    
    if [ ! -f "$CURVI_DEFINITION" ]; then
        print_error "Curvi definition not found: $CURVI_DEFINITION"
        missing_deps=1
    else
        print_success "Curvi printer definition found"
    fi
    
    if [ ! -f "$PYTHON_CONVERTER" ]; then
        print_error "Python converter not found: $PYTHON_CONVERTER"
        missing_deps=1
    else
        print_success "Python converter found"
    fi
    
    if [ ! -f "$TETWILD_EXE" ]; then
        print_error "TetWild not found: $TETWILD_EXE"
        missing_deps=1
    else
        print_success "TetWild found"
    fi
    
    if ! command -v wine &> /dev/null; then
        print_error "Wine not found (required to run TetWild)"
        missing_deps=1
    else
        print_success "Wine found"
    fi
    
    if [ ! -f "$CURVISLICE_BIN" ]; then
        print_error "curvislice_osqp not found: $CURVISLICE_BIN"
        missing_deps=1
    else
        print_success "curvislice_osqp found"
    fi
    
    if [ ! -f "$UNCURVE_BIN" ]; then
        print_error "uncurve not found: $UNCURVE_BIN"
        missing_deps=1
    else
        print_success "uncurve found"
    fi
    
    if ! command -v python3 &> /dev/null; then
        print_error "python3 not found"
        missing_deps=1
    else
        print_success "python3 found"
    fi
    
    if [ $missing_deps -ne 0 ]; then
        echo ""
        print_error "Missing dependencies. Please check the paths in the script configuration."
        exit 1
    fi
    
    echo ""
}

################################################################################
# Parse arguments
################################################################################

if [ $# -lt 1 ]; then
    echo "Usage: $0 <input.stl> [layer_height]"
    echo ""
    echo "Arguments:"
    echo "  input.stl     - Input STL file to process"
    echo "  layer_height  - Layer height in mm (default: 0.2)"
    echo ""
    echo "Example:"
    echo "  $0 models/Calib_Cube.stl 0.2"
    echo "  $0 models/wing.stl 0.3"
    exit 1
fi

INPUT_STL="$1"
check_file_exists "$INPUT_STL"

if [ $# -ge 2 ]; then
    LAYER_HEIGHT="$2"
fi

# Get base name without extension
BASE_NAME=$(basename "$INPUT_STL" .stl)
MODEL_DIR=$(dirname "$INPUT_STL")
AFTER_STL="${MODEL_DIR}/${BASE_NAME}/after.stl"
FINAL_OUTPUT="${MODEL_DIR}/${BASE_NAME}_CURVED.gcode"

print_header "CuraEngine-CurviSlicer Automated Pipeline"
echo "Input STL: $INPUT_STL"
echo "Layer height: ${LAYER_HEIGHT}mm"
echo "Output: $FINAL_OUTPUT"
echo ""

# Check dependencies
check_dependencies

################################################################################
# Step 1: Run CurviSlicer Optimizer
################################################################################

print_header "Step 1/6: Tetrahedral Mesh Generation"

MSH_FILE="${MODEL_DIR}/${BASE_NAME}.msh"

if [ -f "$MSH_FILE" ]; then
    print_info "Tetrahedral mesh already exists: $MSH_FILE"
    read -p "Regenerate? (y/N) " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        rm -f "$MSH_FILE"
        REGENERATE_MSH=1
    fi
fi

if [ ! -f "$MSH_FILE" ] || [ -n "$REGENERATE_MSH" ]; then
    print_info "Running TetWild to generate tetrahedral mesh..."
    
    cd "$MODEL_DIR"
    wine "$TETWILD_EXE" --save-mid-result 2 "${BASE_NAME}.stl" -e 0.025 --targeted-num-v 1000 --is-laplacian || {
        print_error "TetWild failed"
        cd "$SCRIPT_DIR"
        exit 1
    }
    
    # TetWild creates a file with __mid2.000000.msh suffix
    if [ -f "${BASE_NAME}__mid2.000000.msh" ]; then
        mv "${BASE_NAME}__mid2.000000.msh" "${BASE_NAME}.msh"
        print_success "Created tetrahedral mesh: $MSH_FILE"
    else
        print_error "TetWild did not create expected output"
        cd "$SCRIPT_DIR"
        exit 1
    fi
    
    cd "$SCRIPT_DIR"
else
    print_success "Using existing tetrahedral mesh"
fi

echo ""

################################################################################
# Step 2: Run CurviSlicer Optimization
################################################################################

print_header "Step 2/6: CurviSlicer Optimization"

if [ -f "$AFTER_STL" ]; then
    print_info "Curved model already exists: $AFTER_STL"
    read -p "Regenerate? (y/N) " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        rm -rf "${MODEL_DIR}/${BASE_NAME}"
        REGENERATE=1
    fi
fi

if [ ! -f "$AFTER_STL" ] || [ -n "$REGENERATE" ]; then
    print_info "Running curvislice_osqp on tetrahedral mesh..."
    
    export LD_LIBRARY_PATH="${LIBOSQP_PATH}:$LD_LIBRARY_PATH"
    
    "$CURVISLICE_BIN" "$MSH_FILE" -l "$LAYER_HEIGHT" || {
        print_error "curvislice_osqp failed"
        exit 1
    }
    
    if [ ! -f "$AFTER_STL" ]; then
        print_error "curvislice_osqp did not create after.stl"
        exit 1
    fi
    
    print_success "Created curved model: $AFTER_STL"
else
    print_success "Using existing curved model"
fi

echo ""

################################################################################
# Step 2: Slice with CuraEngine
################################################################################

print_header "Step 3/6: CuraEngine Slicing"

CURA_GCODE="${MODEL_DIR}/${BASE_NAME}_curaengine.gcode"

print_info "Slicing with CuraEngine..."

"$CURAENGINE_WRAPPER" slice \
    -d "$CURA_DEFINITIONS_PATH" \
    -j "$CURVI_DEFINITION" \
    -s layer_height=$LAYER_HEIGHT \
    -s roofing_layer_count=0 \
    -s flooring_layer_count=0 \
    -s skirt_line_count=0 \
    -s adhesion_type=none \
    -l "$AFTER_STL" \
    -o "$CURA_GCODE" 2>&1 | grep -E "(info|error|warning)" || true

if [ ! -f "$CURA_GCODE" ] || [ ! -s "$CURA_GCODE" ]; then
    print_error "CuraEngine failed to create G-code"
    exit 1
fi

print_success "Sliced with CuraEngine: $CURA_GCODE"
print_info "Size: $(du -h "$CURA_GCODE" | cut -f1)"

echo ""

################################################################################
# Step 3: Convert to CurviSlicer Format
################################################################################

print_header "Step 4/6: Format Conversion"

CONVERTED_GCODE="${MODEL_DIR}/${BASE_NAME}_converted.gcode"

print_info "Converting CuraEngine G-code to CurviSlicer format..."

python3 "$PYTHON_CONVERTER" \
    "$AFTER_STL" \
    "$CURA_GCODE" \
    "$CONVERTED_GCODE" || {
    print_error "Conversion failed"
    exit 1
}

if [ ! -f "$CONVERTED_GCODE" ] || [ ! -s "$CONVERTED_GCODE" ]; then
    print_error "Conversion produced empty file"
    exit 1
fi

print_success "Converted: $CONVERTED_GCODE"
print_info "Size: $(du -h "$CONVERTED_GCODE" | cut -f1)"

echo ""

################################################################################
# Step 4: Prepare Files for Uncurve
################################################################################

print_header "Step 5/6: Preparing for Uncurve"

CONVERTED_DIR="${MODEL_DIR}/${BASE_NAME}_converted"

print_info "Preparing mesh and displacement files..."

# Create directory
mkdir -p "$CONVERTED_DIR"

# Copy mesh file
cp "${MODEL_DIR}/${BASE_NAME}.msh" "${MODEL_DIR}/${BASE_NAME}_converted.msh" || {
    print_error "Failed to copy .msh file"
    exit 1
}

# Copy displacement files
cp "${MODEL_DIR}/${BASE_NAME}/displacements" "${CONVERTED_DIR}/" || {
    print_error "Failed to copy displacements file"
    exit 1
}

# Copy tetmats
cp "${MODEL_DIR}/${BASE_NAME}/tetmats" "${CONVERTED_DIR}/" || {
    print_error "Failed to copy tetmats file"
    exit 1
}

# Copy displacement variants if they exist
cp "${MODEL_DIR}/${BASE_NAME}/displacements_"* "${CONVERTED_DIR}/" 2>/dev/null || true

print_success "Files prepared for uncurve"

echo ""

################################################################################
# Step 5: Apply Curves with Uncurve
################################################################################

print_header "Step 6/6: Applying Curves"

print_info "Running uncurve to generate curved G-code..."

export LD_LIBRARY_PATH="${LIBOSQP_PATH}:$LD_LIBRARY_PATH"

"$UNCURVE_BIN" \
    -l "$LAYER_HEIGHT" \
    --gcode \
    "$CONVERTED_GCODE" || {
    print_error "uncurve failed"
    exit 1
}

# uncurve overwrites the input file with the curved version
if [ ! -f "$CONVERTED_GCODE" ] || [ ! -s "$CONVERTED_GCODE" ]; then
    print_error "uncurve did not produce output"
    exit 1
fi

# Move to final output location
mv "$CONVERTED_GCODE" "$FINAL_OUTPUT"

print_success "Generated curved G-code!"

echo ""

################################################################################
# Cleanup
################################################################################

print_header "Cleanup"

read -p "Remove intermediate files? (y/N) " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    rm -f "$CURA_GCODE"
    rm -f "${MODEL_DIR}/${BASE_NAME}_converted.msh"
    rm -rf "${CONVERTED_DIR}"
    print_success "Intermediate files removed"
else
    print_info "Intermediate files kept:"
    echo "  - CuraEngine output: $CURA_GCODE"
    echo "  - Mesh file: ${MODEL_DIR}/${BASE_NAME}_converted.msh"
    echo "  - Directory: ${CONVERTED_DIR}"
fi

echo ""

################################################################################
# Summary
################################################################################

print_header "Pipeline Complete!"

echo ""
echo -e "${GREEN}╔════════════════════════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║${NC}  ${CYAN}Final Curved G-code:${NC} ${GREEN}$FINAL_OUTPUT${NC}"
echo -e "${GREEN}╚════════════════════════════════════════════════════════════════╝${NC}"
echo ""
echo "File size: $(du -h "$FINAL_OUTPUT" | cut -f1)"
echo "Lines: $(wc -l < "$FINAL_OUTPUT")"
echo ""
echo "Next steps:"
echo "1. Add your printer's start G-code (heating, homing, etc.)"
echo "2. Add your printer's end G-code (cooling, parking, etc.)"
echo "3. Load in a G-code viewer to preview the curved toolpath"
echo "4. Print and enjoy curved slicing! 🎉"
echo ""
print_success "Automated pipeline completed successfully!"
echo ""
