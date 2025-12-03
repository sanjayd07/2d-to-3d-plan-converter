# 2D Blueprint to 3D Model Converter - GUI Application

A simple Windows offline GUI application built with PySide6 that connects to the existing 2D Blueprint to 3D Model Converter backend.

## Features

✅ **File Input** - Drag & drop or browse for .jpg/.png images  
✅ **Image Preview** - See your floorplan before conversion  
✅ **One-Click Conversion** - Background processing with progress updates  
✅ **Blender Integration** - Auto-detect Blender and open generated models  
✅ **Modern Interface** - Clean, responsive UI with error handling  

## Quick Start

1. **Install Dependencies**
   ```bash
   pip install -r gui_requirements.txt
   ```

2. **Run the GUI**
   ```bash
   python gui_app.py
   ```

3. **Use the Application**
   - Drag & drop or browse for a floorplan image
   - Click "Convert to 3D Model"
   - Wait for processing (runs in background)
   - Click "Open in Blender" to view your 3D model

## Requirements

- Windows 10/11
- Python 3.8+
- Blender (auto-detected or manually configured)
- All dependencies from `gui_requirements.txt`

## Troubleshooting

**"Blender not found"** → Install Blender from https://www.blender.org/download/  
**"Module not found"** → Run `pip install -r gui_requirements.txt`  
**Conversion fails** → Check that your image is a valid floorplan  

## Files

- `gui_app.py` - Main GUI application
- `gui_requirements.txt` - Dependencies
- `Target/` - Output directory for .blend files