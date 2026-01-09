# CuraEngine-CurviSlicer: Automated Non-Planar 3D Printing Pipeline

🎨 **Generate beautiful curved, non-planar G-code using CuraEngine and CurviSlicer!**

This project provides a complete automated pipeline that replaces IceSL with CuraEngine in the CurviSlicer workflow, enabling curved/non-planar 3D printing with zero manual intervention.

---

## ✨ Features

- 🤖 **Fully Automated** - One command from STL to curved G-code
- 🔧 **CuraEngine Integration** - Uses command-line CuraEngine (no GUI required)
- 🐧 **Linux Support** - Tested on Ubuntu 24.04
- 🍷 **Wine Integration** - Seamlessly runs Windows TetWild on Linux
- 📊 **Professional Output** - High-quality curved toolpaths
- 🎯 **Zero Manual Steps** - Complete automation of the entire pipeline
- 🚀 **Ready to Use** - Pre-compiled binaries included

---

## 🎬 What is Non-Planar Printing?

Traditional 3D printing creates flat, horizontal layers:
```
━━━━━━━━  (flat layer at Z=0.2)
━━━━━━━━  (flat layer at Z=0.4)
━━━━━━━━  (flat layer at Z=0.6)
```

**Non-planar (curved) slicing** creates layers that follow your model's surface curvature:
```
∿∿∿∿∿∿∿∿  (curved layer)
∿∿∿∿∿∿∿∿  (curved layer)
∿∿∿∿∿∿∿∿  (curved layer)
```

### Benefits:
- ✅ **Smoother surfaces** - No visible layer lines
- ✅ **Stronger parts** - Better layer adhesion following stress lines
- ✅ **Better overhangs** - Layers follow the surface angle
- ✅ **Unique aesthetics** - Beautiful curved layer patterns
- ✅ **Works on standard printers** - No special hardware needed!

---

## 🚀 Quick Start

### Prerequisites

- **Ubuntu 24.04** (or similar Linux distribution)
- **Wine** (for TetWild)
- **Python 3**
- **Cura 5.x AppImage** (for CuraEngine)

### Installation (5 minutes)

```bash
# 1. Clone the repository
git clone https://github.com/siamak06/CuraEngine-CurviSlicer.git
cd CuraEngine-CurviSlicer

# 2. Install dependencies
sudo apt update
sudo apt install wine64 python3

# 3. Download and extract Cura AppImage
wget https://github.com/Ultimaker/Cura/releases/download/5.11.0/UltiMaker-Cura-5.11.0-linux-X64.AppImage
chmod +x UltiMaker-Cura-5.11.0-linux-X64.AppImage
./UltiMaker-Cura-5.11.0-linux-X64.AppImage --appimage-extract

# 4. Set library path
echo 'export LD_LIBRARY_PATH=$HOME/CuraEngine-CurviSlicer/bin:$LD_LIBRARY_PATH' >> ~/.bashrc
source ~/.bashrc

# 5. Make scripts executable
chmod +x *.sh *.py
```

### Usage (One Command!)

```bash
# Basic usage
./automated_curved_slicer.sh path/to/model.stl

# With custom layer height
./automated_curved_slicer.sh path/to/model.stl 0.3

# Example with included calibration cube
./automated_curved_slicer.sh examples/Calib_Cube.stl 0.2
```

**Output:** `path/to/model_CURVED.gcode` ready to print!

---

## 📊 Example Results

**Input:** 20mm calibration cube  
**Output:** 111,854 lines of curved G-code (4.6MB)

```gcode
G1 X130 Y130 Z0.0903917 E0 F1800
G1 X130 Y129.19 Z0.098735 E0.004783626 F1271.4
G1 X130 Y128.38 Z0.098735 E0.009788052 F1215.3
G1 X130 Y127.57 Z0.098736 E0.01479254 F1215.3
```

**Notice the continuously varying Z coordinates** - that's the curved magic! 🌊

---

## 🔧 How It Works

### 6-Step Automated Pipeline:

```
Input STL
    ↓
1. TetWild → Creates volumetric mesh (.msh)
    ↓
2. curvislice_osqp → Optimizes curved layer positions
    ↓
3. CuraEngine → Slices the curved model (flat layers)
    ↓
4. Python Converter → Converts to CurviSlicer format
    ↓
5. File Preparation → Organizes displacement data
    ↓
6. uncurve → Applies curves to create final G-code
    ↓
Curved G-code ready to print!
```

**All automated - you just run ONE command!** 🎯

---

## 📁 What's Included

```
CuraEngine-CurviSlicer/
├── automated_curved_slicer.sh    # Main automation script
├── curaengine_wrapper.sh          # CuraEngine helper
├── cura_to_curvi_FINAL.py        # Format converter
├── curvi.def.json                 # Printer configuration
├── bin/                           # Pre-compiled binaries
│   ├── curvislice_osqp           # Layer optimizer
│   ├── uncurve                    # Curve applicator
│   └── libosqp.so                # Required library
├── tools/                         # TetWild mesher
│   └── tetwild/
│       └── TetWild.exe
└── examples/                      # Sample models
    └── Calib_Cube.stl
```

---

## ⚙️ Configuration

### Adjust Printer Settings

Edit `curvi.def.json` to match your printer:

```json
{
  "machine_width": 220,
  "machine_depth": 220,
  "machine_height": 240,
  "machine_nozzle_size": 0.4,
  "material_diameter": 1.75,
  "layer_height": 0.2
}
```

### Change Default Layer Height

Edit `automated_curved_slicer.sh`:

```bash
LAYER_HEIGHT=0.2  # Change this value
```

---

## 🎯 Tested On

- ✅ Ubuntu 24.04 LTS
- ✅ Wine 10.0
- ✅ Python 3.12
- ✅ Cura 5.11.0

Should work on other Linux distributions with minor adjustments.

---

## 🐛 Troubleshooting

### "nothing to do..." from uncurve

**Problem:** Missing or misnamed files  
**Solution:** Ensure `.msh` file exists and matches G-code filename

```bash
# Should have:
model.msh
model_converted.gcode
model_converted/ (directory with displacements)
```

### TetWild fails

**Problem:** Wine not installed  
**Solution:**

```bash
sudo apt install wine64
wine --version  # Verify installation
```

### CuraEngine errors

**Problem:** Cura AppImage not extracted  
**Solution:**

```bash
./UltiMaker-Cura-5.11.0-linux-X64.AppImage --appimage-extract
# Creates ~/squashfs-root/
```

### More help?

Check the [Issues](https://github.com/siamak06/CuraEngine-CurviSlicer/issues) or create a new one!

---

## 🤝 Contributing

Contributions welcome! Please:

1. Fork the repository
2. Create a feature branch
3. Test your changes
4. Submit a pull request

**Ideas for contributions:**
- macOS support
- Windows native support (no Wine)
- GUI wrapper
- Additional printer profiles
- Performance optimizations

---

## ⚠️ Important Notes

- **Printer Clearance:** Ensure your printer has adequate nozzle clearance (45° cone, 5cm minimum)
- **Test First:** Start with small test prints to verify clearance
- **Add Start/End Code:** Final G-code needs your printer's heating and homing commands
- **Inspect Output:** Always preview G-code before printing

---

## 📜 License

MIT License - See [LICENSE](LICENSE) for details.

---

## 🙏 Credits

### Original Research

**CurviSlicer** - Curved slicing algorithm
- **Paper:** [CurviSlicer: Slightly Curved Slicing for 3-Axis Printers](https://inria.hal.science/hal-02177164)
- **Authors:** Myriam Claux, Samuel Hornus, Sylvain Lefebvre (INRIA)
- **Original Repository:** [github.com/mfx-inria/curvislicer](https://github.com/mfx-inria/curvislicer)

### This Automation Project

**CuraEngine Integration & Automation**
- **Developers:** Siamak & Claude (2026)
- **Contribution:** Replaced IceSL with CuraEngine, complete automation, comprehensive documentation

### Special Thanks

- **Ultimaker** - CuraEngine
- **INRIA** - CurviSlicer research team
- **3D Printing Community** - Testing and feedback

---

## 📧 Contact & Support

- **Issues:** [GitHub Issues](https://github.com/siamak06/CuraEngine-CurviSlicer/issues)
- **Discussions:** [GitHub Discussions](https://github.com/siamak06/CuraEngine-CurviSlicer/discussions)
- **Star the repo** if you find it useful! ⭐

---

## ⭐ Show Your Support

If this project helps you create amazing curved prints:
- ⭐ **Star this repository**
- 🐛 **Report bugs** you find
- 💡 **Suggest features**
- 🔄 **Share with others**
- 📸 **Show us your prints!**

---

**Made with ❤️ for the 3D printing community**

*Bringing non-planar printing to everyone, one curved layer at a time!* 🌊🎨🚀
