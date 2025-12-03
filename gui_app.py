import sys
import os
import subprocess
import shutil
from pathlib import Path
from datetime import datetime
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QVBoxLayout, QHBoxLayout, QWidget, 
    QPushButton, QLabel, QFileDialog, QMessageBox, QProgressBar,
    QFrame, QScrollArea
)
from PySide6.QtCore import Qt, QThread, Signal, QTimer
from PySide6.QtGui import QPixmap, QDragEnterEvent, QDropEvent, QFont
from PySide6.QtCore import QMimeData

# Import the backend logic
from FloorplanToBlenderLib.execution import simple_single
from FloorplanToBlenderLib.floorplan import floorplan


class ConversionWorker(QThread):
    """Worker thread for background conversion"""
    finished = Signal(str)  # Success message
    error = Signal(str)     # Error message
    progress = Signal(str)  # Progress message
    
    def __init__(self, image_path, blender_path=None):
        super().__init__()
        self.image_path = image_path
        self.blender_path = blender_path
        
    def run(self):
        try:
            self.progress.emit("Processing...")
            
            # Create floorplan object
            fp = floorplan("Configs/default.ini")
            fp.image_path = self.image_path
            
            # Run conversion to generate data files
            data_path = simple_single(fp, show=False)
            
            self.progress.emit("Generating 3D model in Blender...")
            
            # Now create the .blend file using Blender
            target_dir = Path("Target")
            target_dir.mkdir(exist_ok=True)
            
            # Use provided Blender path or find one
            blender_path = self.blender_path or self.find_blender()
            if not blender_path:
                self.error.emit("❌ Blender not found. Please install Blender or configure the path.")
                return
                
            # Verify Blender installation
            try:
                self.verify_blender(blender_path)
            except Exception as e:
                self.error.emit(f"❌ Blender verification failed: {str(e)}")
                return
                
            # Create unique .blend file name based on input image
            input_name = Path(self.image_path).stem
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            target_file = target_dir / f"{input_name}_{timestamp}.blend"
            self.create_blend_file(blender_path, data_path, target_file)
            
            if target_file.exists():
                self.finished.emit(f"✅ Model saved at {target_file}")
            else:
                self.error.emit("❌ Failed to create .blend file")
                
        except Exception as e:
            self.error.emit(f"❌ Error: {str(e)}")
            
    def find_blender(self):
        """Find Blender installation"""
        possible_paths = [
            r"C:\Program Files\Blender Foundation\Blender 4.5\blender.exe",
            r"C:\Program Files\Blender Foundation\Blender 4.4\blender.exe",
            r"C:\Program Files\Blender Foundation\Blender 4.3\blender.exe",
            r"C:\Program Files\Blender Foundation\Blender 4.2\blender.exe",
            r"C:\Program Files\Blender Foundation\Blender 4.1\blender.exe",
            r"C:\Program Files\Blender Foundation\Blender 4.0\blender.exe",
            r"C:\Program Files\Blender Foundation\Blender 3.6\blender.exe",
            r"C:\Program Files\Blender Foundation\Blender 3.5\blender.exe",
            r"C:\Program Files\Blender Foundation\Blender 3.4\blender.exe",
            r"C:\Program Files\Blender Foundation\Blender 3.3\blender.exe",
            r"C:\Program Files\Blender Foundation\Blender 3.2\blender.exe",
            r"C:\Program Files\Blender Foundation\Blender 3.1\blender.exe",
            r"C:\Program Files\Blender Foundation\Blender 3.0\blender.exe",
        ]
        
        for path in possible_paths:
            if os.path.exists(path):
                return path
        return None
        
    def verify_blender(self, blender_path):
        """Verify Blender installation and script"""
        try:
            # Test Blender can run
            result = subprocess.run([blender_path, "--version"], 
                                  capture_output=True, text=True, timeout=10)
            if result.returncode != 0:
                raise Exception("Blender installation invalid")
            
            # Test script exists
            script_path = "Blender/floorplan_to_3dObject_in_blender.py"
            if not os.path.exists(script_path):
                raise Exception(f"Blender script not found: {script_path}")
                
            return True
        except Exception as e:
            raise Exception(f"Blender verification failed: {str(e)}")
        
    def create_blend_file(self, blender_path, data_path, target_file):
        """Create .blend file using Blender"""
        try:
            # Use the existing Blender script from the project
            blender_script = "Blender/floorplan_to_3dObject_in_blender.py"
            if not os.path.exists(blender_script):
                # Fallback to any available Blender script
                blender_scripts = list(Path("Blender").glob("*.py"))
                if blender_scripts:
                    blender_script = str(blender_scripts[0])
                else:
                    raise Exception("No Blender script found")
            
            print(f"DEBUG: Using Blender script: {blender_script}")
            print(f"DEBUG: Data path: {data_path}")
            print(f"DEBUG: Target file: {target_file}")
            print(f"DEBUG: Program path: {Path.cwd()}")
            
            # Run Blender to create the .blend file
            # The script expects: program_path, target_path, data_paths
            # Pass just the filename, let Blender script construct full path
            target_filename = target_file.name
            
            result = subprocess.run([
                blender_path,
                "-noaudio",  # This is a dockerfile ubuntu hax fix
                "--background",
                "--python", blender_script,
                str(Path.cwd()),  # Program path
                target_filename,  # Target filename only
                str(data_path)     # Data path
            ], check=True, capture_output=True, text=True)
            
            print(f"DEBUG: Blender stdout: {result.stdout}")
            print(f"DEBUG: Blender stderr: {result.stderr}")
            
        except subprocess.CalledProcessError as e:
            error_msg = f"Blender execution failed: {e.stderr}"
            print(f"DEBUG: {error_msg}")
            raise Exception(error_msg)
        except Exception as e:
            error_msg = f"Failed to create .blend file: {str(e)}"
            print(f"DEBUG: {error_msg}")
            raise Exception(error_msg)


class DragDropWidget(QFrame):
    """Custom widget for drag and drop functionality"""
    file_dropped = Signal(str)
    
    def __init__(self):
        super().__init__()
        self.setAcceptDrops(True)
        self.setFrameStyle(QFrame.Box)
        self.setStyleSheet("""
            QFrame {
                border: 2px dashed #aaa;
                border-radius: 10px;
                background-color: #f9f9f9;
                min-height: 150px;
            }
            QFrame:hover {
                border-color: #007acc;
                background-color: #f0f8ff;
            }
        """)
        
        layout = QVBoxLayout()
        self.label = QLabel("Drag & Drop image here\nor click Browse")
        self.label.setAlignment(Qt.AlignCenter)
        self.label.setStyleSheet("color: #666; font-size: 14px;")
        layout.addWidget(self.label)
        self.setLayout(layout)
        
    def dragEnterEvent(self, event: QDragEnterEvent):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
            
    def dropEvent(self, event: QDropEvent):
        files = [url.toLocalFile() for url in event.mimeData().urls()]
        if files:
            file_path = files[0]
            if file_path.lower().endswith(('.jpg', '.jpeg', '.png')):
                self.file_dropped.emit(file_path)
            else:
                QMessageBox.warning(self, "Invalid File", "Please select a .jpg or .png image file.")
        event.acceptProposedAction()


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.selected_file = None
        self.blender_path = None
        self.worker = None
        self.init_ui()
        self.detect_blender()
        self.load_blender_path()
        
    def init_ui(self):
        self.setWindowTitle("2D Blueprint to 3D Model Converter")
        self.setGeometry(100, 100, 800, 600)
        
        # Main widget
        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        
        # Main layout
        layout = QVBoxLayout()
        layout.setSpacing(20)
        layout.setContentsMargins(20, 20, 20, 20)
        
        # Title
        title = QLabel("2D Blueprint to 3D Model Converter")
        title.setAlignment(Qt.AlignCenter)
        title.setStyleSheet("font-size: 24px; font-weight: bold; color: #333; margin-bottom: 20px;")
        layout.addWidget(title)
        
        # File input section
        file_section = QVBoxLayout()
        file_section.setSpacing(10)
        
        # Drag & Drop area
        self.drag_drop = DragDropWidget()
        self.drag_drop.file_dropped.connect(self.on_file_selected)
        file_section.addWidget(self.drag_drop)
        
        # Browse button
        browse_layout = QHBoxLayout()
        self.browse_btn = QPushButton("Browse for Image")
        self.browse_btn.clicked.connect(self.browse_file)
        self.browse_btn.setStyleSheet("""
            QPushButton {
                background-color: #007acc;
                color: white;
                border: none;
                padding: 10px 20px;
                border-radius: 5px;
                font-size: 14px;
            }
            QPushButton:hover {
                background-color: #005a9e;
            }
        """)
        browse_layout.addWidget(self.browse_btn)
        browse_layout.addStretch()
        file_section.addLayout(browse_layout)
        
        layout.addLayout(file_section)
        
        # Image preview section
        preview_section = QVBoxLayout()
        preview_section.setSpacing(10)
        
        preview_label = QLabel("Preview:")
        preview_label.setStyleSheet("font-weight: bold; font-size: 16px;")
        preview_section.addWidget(preview_label)
        
        # Scroll area for image preview
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setMinimumHeight(200)
        self.scroll_area.setStyleSheet("border: 1px solid #ddd; border-radius: 5px;")
        
        self.preview_label = QLabel("No image selected")
        self.preview_label.setAlignment(Qt.AlignCenter)
        self.preview_label.setStyleSheet("color: #999; font-size: 14px;")
        self.scroll_area.setWidget(self.preview_label)
        
        preview_section.addWidget(self.scroll_area)
        layout.addLayout(preview_section)
        
        # Convert button
        self.convert_btn = QPushButton("Convert to 3D Model")
        self.convert_btn.clicked.connect(self.convert_image)
        self.convert_btn.setEnabled(False)
        self.convert_btn.setStyleSheet("""
            QPushButton {
                background-color: #28a745;
                color: white;
                border: none;
                padding: 15px 30px;
                border-radius: 5px;
                font-size: 16px;
                font-weight: bold;
            }
            QPushButton:hover:enabled {
                background-color: #218838;
            }
            QPushButton:disabled {
                background-color: #6c757d;
            }
        """)
        layout.addWidget(self.convert_btn)
        
        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        self.progress_bar.setStyleSheet("""
            QProgressBar {
                border: 2px solid #ddd;
                border-radius: 5px;
                text-align: center;
            }
            QProgressBar::chunk {
                background-color: #007acc;
                border-radius: 3px;
            }
        """)
        layout.addWidget(self.progress_bar)
        
        # Status area
        self.status_label = QLabel("Ready to convert")
        self.status_label.setAlignment(Qt.AlignCenter)
        self.status_label.setStyleSheet("""
            color: #666;
            font-size: 14px;
            padding: 10px;
            background-color: #f8f9fa;
            border-radius: 5px;
        """)
        layout.addWidget(self.status_label)
        
        # Open in Blender button
        self.open_blender_btn = QPushButton("Open in Blender")
        self.open_blender_btn.clicked.connect(self.open_in_blender)
        self.open_blender_btn.setEnabled(False)
        self.open_blender_btn.setStyleSheet("""
            QPushButton {
                background-color: #ff6b35;
                color: white;
                border: none;
                padding: 10px 20px;
                border-radius: 5px;
                font-size: 14px;
            }
            QPushButton:hover:enabled {
                background-color: #e55a2b;
            }
            QPushButton:disabled {
                background-color: #6c757d;
            }
        """)
        layout.addWidget(self.open_blender_btn)
        
        main_widget.setLayout(layout)
        
    def detect_blender(self):
        """Try to detect Blender installation"""
        possible_paths = [
            r"C:\Program Files\Blender Foundation\Blender 4.5\blender.exe",
            r"C:\Program Files\Blender Foundation\Blender 4.4\blender.exe",
            r"C:\Program Files\Blender Foundation\Blender 4.3\blender.exe",
            r"C:\Program Files\Blender Foundation\Blender 4.2\blender.exe",
            r"C:\Program Files\Blender Foundation\Blender 4.1\blender.exe",
            r"C:\Program Files\Blender Foundation\Blender 4.0\blender.exe",
            r"C:\Program Files\Blender Foundation\Blender 3.6\blender.exe",
            r"C:\Program Files\Blender Foundation\Blender 3.5\blender.exe",
            r"C:\Program Files\Blender Foundation\Blender 3.4\blender.exe",
            r"C:\Program Files\Blender Foundation\Blender 3.3\blender.exe",
            r"C:\Program Files\Blender Foundation\Blender 3.2\blender.exe",
            r"C:\Program Files\Blender Foundation\Blender 3.1\blender.exe",
            r"C:\Program Files\Blender Foundation\Blender 3.0\blender.exe",
        ]
        
        for path in possible_paths:
            if os.path.exists(path):
                self.blender_path = path
                break
                
        # Also try to find blender in PATH
        if not self.blender_path:
            try:
                result = subprocess.run(['where', 'blender'], capture_output=True, text=True)
                if result.returncode == 0:
                    self.blender_path = result.stdout.strip().split('\n')[0]
            except:
                pass
                
    def browse_file(self):
        """Open file dialog to select image"""
        file_path, _ = QFileDialog.getOpenFileName(
            self, 
            "Select Image", 
            "", 
            "Image Files (*.png *.jpg *.jpeg)"
        )
        if file_path:
            self.on_file_selected(file_path)
            
    def on_file_selected(self, file_path):
        """Handle file selection"""
        self.selected_file = file_path
        self.load_preview(file_path)
        self.convert_btn.setEnabled(True)
        self.drag_drop.label.setText(f"Selected: {os.path.basename(file_path)}")
        
    def load_preview(self, file_path):
        """Load and display image preview"""
        try:
            pixmap = QPixmap(file_path)
            if not pixmap.isNull():
                # Scale image to fit preview area
                scaled_pixmap = pixmap.scaled(400, 300, Qt.KeepAspectRatio, Qt.SmoothTransformation)
                self.preview_label.setPixmap(scaled_pixmap)
                self.preview_label.setAlignment(Qt.AlignCenter)
            else:
                self.preview_label.setText("Failed to load image")
        except Exception as e:
            self.preview_label.setText(f"Error loading image: {str(e)}")
            
    def convert_image(self):
        """Start conversion process"""
        if not self.selected_file:
            return
            
        # Disable convert button and show progress
        self.convert_btn.setEnabled(False)
        self.progress_bar.setVisible(True)
        self.progress_bar.setRange(0, 0)  # Indeterminate progress
        self.status_label.setText("Processing...")
        
        # Start worker thread
        self.worker = ConversionWorker(self.selected_file, self.blender_path)
        self.worker.finished.connect(self.on_conversion_finished)
        self.worker.error.connect(self.on_conversion_error)
        self.worker.progress.connect(self.on_conversion_progress)
        self.worker.start()
        
    def on_conversion_progress(self, message):
        """Handle progress updates"""
        self.status_label.setText(message)
        
    def on_conversion_finished(self, message):
        """Handle successful conversion"""
        self.progress_bar.setVisible(False)
        self.convert_btn.setEnabled(True)
        self.status_label.setText(message)
        self.open_blender_btn.setEnabled(True)
        
    def on_conversion_error(self, message):
        """Handle conversion error"""
        self.progress_bar.setVisible(False)
        self.convert_btn.setEnabled(True)
        self.status_label.setText(message)
        QMessageBox.critical(self, "Conversion Error", message)
        
    def open_in_blender(self):
        """Open the generated .blend file in Blender"""
        # Look for the most recent .blend file in Target directory
        target_dir = Path("Target")
        if target_dir.exists():
            blend_files = list(target_dir.glob("*.blend"))
            if blend_files:
                # Get the most recently modified file
                blend_file = max(blend_files, key=lambda x: x.stat().st_mtime)
            else:
                QMessageBox.warning(self, "File Not Found", "No .blend file found in Target directory.")
                return
        else:
            QMessageBox.warning(self, "File Not Found", "No .blend file found in Target directory.")
            return
            
        if not self.blender_path:
            # Ask user to configure Blender path
            path, _ = QFileDialog.getOpenFileName(
                self, 
                "Select Blender Executable", 
                "", 
                "Executable Files (*.exe)"
            )
            if path:
                self.blender_path = path
                # Save the path for future use
                self.save_blender_path(path)
            else:
                return
                
        try:
            subprocess.Popen([self.blender_path, str(blend_file)])
            self.status_label.setText("✅ Opening in Blender...")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to open Blender: {str(e)}")
            
    def save_blender_path(self, path):
        """Save Blender path to a config file"""
        try:
            with open("blender_path.txt", "w") as f:
                f.write(path)
        except Exception:
            pass  # Ignore if we can't save
            
    def load_blender_path(self):
        """Load saved Blender path"""
        try:
            if os.path.exists("blender_path.txt"):
                with open("blender_path.txt", "r") as f:
                    path = f.read().strip()
                    if os.path.exists(path):
                        self.blender_path = path
        except Exception:
            pass  # Ignore if we can't load


def main():
    app = QApplication(sys.argv)
    app.setStyle('Fusion')  # Use modern Fusion style
    
    window = MainWindow()
    window.show()
    
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
