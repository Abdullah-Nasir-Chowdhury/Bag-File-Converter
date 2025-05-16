def update_extraction_options(self, mode):
        """Ensure only one extraction option is selected at a time"""
        self.extraction_mode = mode
        
        # Update checkboxes
        self.extract_both_radio.setChecked(mode == "both")
        self.extract_ply_only_radio.setChecked(mode == "ply")
        self.extract_png_only_radio.setChecked(mode == "png")

import os
import sys
import shutil
import subprocess
import time
from PyQt5.QtWidgets import (QApplication, QMainWindow, QPushButton, QVBoxLayout, QHBoxLayout, 
                            QWidget, QFileDialog, QLabel, QProgressBar, QListWidget, 
                            QListWidgetItem, QCheckBox, QGroupBox, QMessageBox)
from PyQt5.QtCore import Qt, QThread, pyqtSignal, QSize

class ConversionWorker(QThread):
    """Worker thread to handle the conversion process without freezing the UI"""
    update_progress = pyqtSignal(int, str)
    conversion_complete = pyqtSignal()
    
    def __init__(self, bag_files, rs_convert_path, extraction_mode="both"):
        super().__init__()
        self.bag_files = bag_files
        self.rs_convert_path = rs_convert_path
        self.canceled = False
        self.start_time = None
        self.extraction_mode = extraction_mode  # "both", "ply", or "png"
        
    def run(self):
        total_files = len(self.bag_files)
        self.start_time = os.path.getmtime(self.bag_files[0]) if self.bag_files else None
        processed_files = 0
        
        for i, bag_file in enumerate(self.bag_files):
            if self.canceled:
                break
                
            try:
                bag_filename = os.path.basename(bag_file)
                file_size = os.path.getsize(bag_file)
                
                # Initialize progress for this file
                base_progress = (i / total_files) * 100
                file_progress_weight = 100 / total_files
                
                # Update with file starting
                self.update_progress.emit(
                    int(base_progress), 
                    f"Starting file {i+1}/{total_files}: {bag_filename}"
                )
                
                # Create folder structure - 10% of the file's progress
                self.update_progress.emit(
                    int(base_progress + file_progress_weight * 0.1),
                    f"Creating folders for {bag_filename}"
                )
                
                # Create folder structure
                source_folder, item_folder, ply_folder, png_folder = self.create_folder_structure(bag_file)
                
                # Copy the original .bag file - 20% of the file's progress
                self.update_progress.emit(
                    int(base_progress + file_progress_weight * 0.2), 
                    f"Copying {bag_filename}"
                )
                
                item_bag_file = os.path.join(item_folder, bag_filename)
                shutil.copy2(bag_file, item_bag_file)
                
                # Extraction is the most time-consuming part - Starts at 20% of this file's allocation
                self.update_progress.emit(
                    int(base_progress + file_progress_weight * 0.2), 
                    f"Extracting data from {bag_filename} (this may take a while)"
                )
                
                # Extract .ply and .png files
                ply_output_path = os.path.join(ply_folder, "ply")
                png_output_path = os.path.join(png_folder, "png")
                
                # The extraction process with time estimation
                success = self.extract_data(bag_file, ply_output_path, png_output_path, 
                                           base_progress, file_progress_weight, i, total_files)
                
                if success:
                    processed_files += 1
                    # File complete - full progress for this file
                    self.update_progress.emit(
                        int(base_progress + file_progress_weight), 
                        f"Completed file {i+1}/{total_files}: {bag_filename}"
                    )
                
            except Exception as e:
                self.update_progress.emit(
                    int((i / total_files) * 100), 
                    f"Error processing {os.path.basename(bag_file)}: {str(e)}"
                )
        
        self.conversion_complete.emit()
    
    def create_folder_structure(self, bag_file):
        """Create folder structure for a bag file"""
        source_folder = os.path.dirname(bag_file)
        bag_filename = os.path.basename(bag_file)
        item_name = os.path.splitext(bag_filename)[0]
        
        # Create a new folder for this item
        item_folder = os.path.join(source_folder, item_name)
        os.makedirs(item_folder, exist_ok=True)
        
        # Create subfolders only for the file types we're extracting
        ply_folder = None
        png_folder = None
        
        if self.extraction_mode == "both" or self.extraction_mode == "ply":
            ply_folder = os.path.join(item_folder, f"{item_name}_ply")
            os.makedirs(ply_folder, exist_ok=True)
            
        if self.extraction_mode == "both" or self.extraction_mode == "png":
            png_folder = os.path.join(item_folder, f"{item_name}_png")
            os.makedirs(png_folder, exist_ok=True)
        
        return source_folder, item_folder, ply_folder, png_folder
    
    def extract_data(self, bag_file, ply_output_path, png_output_path, base_progress, file_progress_weight, 
                    current_file_index, total_files):
        """Extract data from a bag file with progress monitoring"""
        bag_filename = os.path.basename(bag_file)
        
        # Build the command to run rs-convert.exe based on extraction mode
        command = [self.rs_convert_path, "-i", bag_file]
        
        # Add output parameters based on extraction mode
        if self.extraction_mode == "both" or self.extraction_mode == "ply":
            command.extend(["-l", ply_output_path])
            
        if self.extraction_mode == "both" or self.extraction_mode == "png":
            command.extend(["-p", png_output_path])
            
        try:
            # Start the process with pipe for output
            process = subprocess.Popen(
                command,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                universal_newlines=True,
                bufsize=1
            )
            
            # Track start time for this specific extraction
            extraction_start_time = self.get_current_time()
            progress_updates = 0
            
            # Read output line by line to estimate progress
            for line in iter(process.stdout.readline, ''):
                if self.canceled:
                    process.terminate()
                    return False
                
                # Increment progress based on output lines - this is an approximation
                # since we don't know the exact percentage from rs-convert
                progress_updates += 1
                
                # Let's assume a typical extraction produces ~100 lines of output
                # and limit our extract phase to go from 20% to 90% of file's progress
                extract_progress = min(0.7, (progress_updates / 100) * 0.7)
                
                # Calculate elapsed time and estimate remaining time
                elapsed_seconds = self.get_current_time() - extraction_start_time
                remaining_files = total_files - current_file_index - 1
                
                # Only show time estimate after we've processed for at least 2 seconds
                time_estimate = ""
                if elapsed_seconds > 2:
                    # Estimate for this file
                    if extract_progress > 0.1:  # Only estimate after some progress
                        file_remaining = elapsed_seconds * (0.7 - extract_progress) / extract_progress
                        
                        # Estimate for all remaining files
                        total_remaining = file_remaining + (elapsed_seconds / extract_progress) * remaining_files
                        
                        if total_remaining < 60:
                            time_estimate = f" - Est. {int(total_remaining)} seconds remaining"
                        else:
                            time_estimate = f" - Est. {int(total_remaining/60)} minutes remaining"
                
                # Update progress
                progress = base_progress + (0.2 + extract_progress) * file_progress_weight
                
                # Update status message based on extraction mode
                if self.extraction_mode == "both":
                    status = f"Extracting PLY and PNG from {bag_filename}"
                elif self.extraction_mode == "ply":
                    status = f"Extracting PLY from {bag_filename}"
                else:  # png
                    status = f"Extracting PNG from {bag_filename}"
                    
                self.update_progress.emit(
                    int(progress),
                    f"{status} ({int((0.2 + extract_progress) * 100)}%){time_estimate}"
                )
            
            # Wait for the process to complete
            process.wait()
            
            # Final extraction update - 90% of file's progress
            self.update_progress.emit(
                int(base_progress + file_progress_weight * 0.9),
                f"Finalizing {bag_filename}"
            )
            
            return process.returncode == 0
            
        except Exception as e:
            self.update_progress.emit(
                int(base_progress + file_progress_weight * 0.5),
                f"Error during extraction: {str(e)}"
            )
            return False
    
    def get_current_time(self):
        """Get current time in seconds"""
        return time.time()
    
    def cancel(self):
        """Cancel the conversion process"""
        self.canceled = True


class BagConverterApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Bag File Converter")
        self.setGeometry(100, 100, 800, 600)
        
        self.bag_files = []
        self.rs_convert_path = ""
        self.worker = None
        self.extraction_mode = "both"  # Default to extract both PLY and PNG
        
        self.init_ui()
        
    def init_ui(self):
        # Create central widget and main layout
        central_widget = QWidget()
        main_layout = QVBoxLayout(central_widget)
        self.setCentralWidget(central_widget)
        
        # Create configuration group
        config_group = QGroupBox("Configuration")
        config_layout = QVBoxLayout()
        config_group.setLayout(config_layout)
        
        # Add browse button for rs-convert.exe
        rs_convert_layout = QHBoxLayout()
        self.rs_convert_label = QLabel("rs-convert.exe path: Not selected")
        rs_convert_browse_btn = QPushButton("Browse")
        rs_convert_browse_btn.clicked.connect(self.browse_rs_convert)
        rs_convert_layout.addWidget(self.rs_convert_label)
        rs_convert_layout.addWidget(rs_convert_browse_btn)
        config_layout.addLayout(rs_convert_layout)
        
        # Add browse button for directory containing .bag files
        dir_layout = QHBoxLayout()
        self.dir_label = QLabel("Bag files directory: Not selected")
        dir_browse_btn = QPushButton("Browse")
        dir_browse_btn.clicked.connect(self.browse_directory)
        dir_layout.addWidget(self.dir_label)
        dir_layout.addWidget(dir_browse_btn)
        config_layout.addLayout(dir_layout)
        
        # Add extraction options
        extraction_layout = QVBoxLayout()
        extraction_label = QLabel("Select file types to extract:")
        extraction_layout.addWidget(extraction_label)
        
        # Radio buttons for extraction options
        self.extract_both_radio = QCheckBox("Extract both PLY and PNG files")
        self.extract_both_radio.setChecked(True)
        self.extract_ply_only_radio = QCheckBox("Extract PLY files only")
        self.extract_png_only_radio = QCheckBox("Extract PNG files only")
        
        extraction_layout.addWidget(self.extract_both_radio)
        extraction_layout.addWidget(self.extract_ply_only_radio)
        extraction_layout.addWidget(self.extract_png_only_radio)
        
        # Connect signals to ensure only one option is selected at a time
        self.extract_both_radio.clicked.connect(lambda: self.update_extraction_options("both"))
        self.extract_ply_only_radio.clicked.connect(lambda: self.update_extraction_options("ply"))
        self.extract_png_only_radio.clicked.connect(lambda: self.update_extraction_options("png"))
        
        config_layout.addLayout(extraction_layout)
        
        main_layout.addWidget(config_group)
        
        # Create file selection group
        file_group = QGroupBox("Bag File Selection")
        file_layout = QVBoxLayout()
        file_group.setLayout(file_layout)
        
        # Add list of bag files with checkboxes
        self.file_list = QListWidget()
        self.file_list.setSelectionMode(QListWidget.NoSelection)
        file_layout.addWidget(self.file_list)
        
        # Add select all/none buttons
        select_layout = QHBoxLayout()
        select_all_btn = QPushButton("Select All")
        select_all_btn.clicked.connect(self.select_all_files)
        select_none_btn = QPushButton("Select None")
        select_none_btn.clicked.connect(self.select_no_files)
        select_layout.addWidget(select_all_btn)
        select_layout.addWidget(select_none_btn)
        file_layout.addLayout(select_layout)
        
        main_layout.addWidget(file_group)
        
        # Add progress tracking
        progress_group = QGroupBox("Conversion Progress")
        progress_layout = QVBoxLayout()
        progress_group.setLayout(progress_layout)
        
        self.progress_bar = QProgressBar()
        self.progress_bar.setTextVisible(True)
        self.progress_bar.setFormat("%p% complete")
        
        # Two labels for status and time
        self.progress_label = QLabel("Ready to convert")
        self.progress_label.setWordWrap(True)
        
        progress_layout.addWidget(self.progress_bar)
        progress_layout.addWidget(self.progress_label)
        
        main_layout.addWidget(progress_group)
        
        # Add action buttons
        button_layout = QHBoxLayout()
        self.convert_btn = QPushButton("Start Conversion")
        self.convert_btn.setEnabled(False)
        self.convert_btn.clicked.connect(self.start_conversion)
        
        self.cancel_btn = QPushButton("Cancel")
        self.cancel_btn.setEnabled(False)
        self.cancel_btn.clicked.connect(self.cancel_conversion)
        
        button_layout.addWidget(self.convert_btn)
        button_layout.addWidget(self.cancel_btn)
        
        main_layout.addLayout(button_layout)
    
    def browse_rs_convert(self):
        """Browse for the rs-convert.exe file"""
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Select rs-convert.exe", "", "Executable Files (*.exe)"
        )
        if file_path:
            self.rs_convert_path = file_path
            self.rs_convert_label.setText(f"rs-convert.exe path: {os.path.basename(file_path)}")
            self.check_ready_status()
    
    def browse_directory(self):
        """Browse for the directory containing .bag files"""
        directory = QFileDialog.getExistingDirectory(self, "Select Directory")
        if directory:
            self.dir_label.setText(f"Bag files directory: {os.path.basename(directory)}")
            self.load_bag_files(directory)
            self.check_ready_status()
            
            # Reset progress when a new directory is selected
            self.progress_bar.setValue(0)
            self.progress_label.setText("Ready to convert")
    
    def load_bag_files(self, directory):
        """Load .bag files from the selected directory"""
        self.file_list.clear()
        self.bag_files = []
        
        # Find all .bag files in the directory
        for file in os.listdir(directory):
            if file.endswith(".bag"):
                file_path = os.path.join(directory, file)
                self.bag_files.append(file_path)
                
                # Add to list with checkbox
                item = QListWidgetItem()
                item.setText(file)
                item.setFlags(item.flags() | Qt.ItemIsUserCheckable)
                item.setCheckState(Qt.Checked)
                self.file_list.addItem(item)
    
    def select_all_files(self):
        """Select all bag files in the list"""
        for i in range(self.file_list.count()):
            item = self.file_list.item(i)
            item.setCheckState(Qt.Checked)
    
    def select_no_files(self):
        """Unselect all bag files in the list"""
        for i in range(self.file_list.count()):
            item = self.file_list.item(i)
            item.setCheckState(Qt.Unchecked)
    
    def check_ready_status(self):
        """Check if all required inputs are provided to enable conversion"""
        has_rs_convert = bool(self.rs_convert_path)
        has_bag_files = self.file_list.count() > 0
        
        self.convert_btn.setEnabled(has_rs_convert and has_bag_files)
    
    def get_selected_bag_files(self):
        """Get list of selected bag files"""
        selected_files = []
        for i in range(self.file_list.count()):
            item = self.file_list.item(i)
            if item.checkState() == Qt.Checked:
                file_name = item.text()
                directory = os.path.dirname(self.bag_files[0])
                selected_files.append(os.path.join(directory, file_name))
        return selected_files
    
    def start_conversion(self):
        """Start the conversion process for selected bag files"""
        selected_files = self.get_selected_bag_files()
        
        if not selected_files:
            QMessageBox.warning(self, "No Files Selected", "Please select at least one bag file to convert.")
            return
        
        # Disable UI elements during conversion
        self.convert_btn.setEnabled(False)
        self.cancel_btn.setEnabled(True)
        
        # Reset progress
        self.progress_bar.setValue(0)
        self.progress_label.setText("Starting conversion...")
        
        # Start worker thread with current extraction mode
        self.worker = ConversionWorker(selected_files, self.rs_convert_path, self.extraction_mode)
        self.worker.update_progress.connect(self.update_progress)
        self.worker.conversion_complete.connect(self.conversion_complete)
        self.worker.start()
    
    def update_progress(self, value, message):
        """Update progress bar and status message"""
        self.progress_bar.setValue(value)
        self.progress_label.setText(message)
        # Force UI update
        QApplication.processEvents()
    
    def conversion_complete(self):
        """Called when conversion is complete"""
        self.progress_label.setText("Conversion completed!")
        self.convert_btn.setEnabled(True)
        self.cancel_btn.setEnabled(False)
        
        QMessageBox.information(self, "Conversion Complete", 
                               "All selected bag files have been processed successfully!")
        
        # Reset the progress bar after completion
        self.progress_bar.setValue(0)
    
    def cancel_conversion(self):
        """Cancel the current conversion process"""
        if self.worker and self.worker.isRunning():
            self.worker.cancel()
            self.worker.wait()
            self.progress_label.setText("Conversion canceled")
            self.convert_btn.setEnabled(True)
            self.cancel_btn.setEnabled(False)
            
            # Reset the progress bar after cancellation
            self.progress_bar.setValue(0)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = BagConverterApp()
    window.show()
    sys.exit(app.exec_())