# Bag File Converter

A desktop application for converting and extracting data from RealSense .bag files with a simple graphical user interface.

![Bag File Converter Screenshot](https://github.com/Abdullah-Nasir-Chowdhury/Bag-File-Converter/blob/master/others/app-interface.png)

## Features

- Batch convert multiple .bag files from Intel RealSense cameras
- Extract .ply (3D point cloud) and .png (image) data from .bag files
- User-friendly interface with file selection and progress tracking
- Automatic folder organization for converted files
- Real-time progress monitoring with time estimation
- Cancel ongoing conversions at any time

## Requirements

- Windows, macOS, or Linux
- Python 3.6+
- PyQt5
- Intel RealSense SDK (specifically rs-convert utility)

## Installation

1. Clone this repository:
   ```
   git clone https://github.com/user/bag-file-converter.git
   cd bag-file-converter
   ```

2. Install the required Python packages:
   ```
   pip install -r requirements.txt
   ```

3. Ensure you have the Intel RealSense SDK installed, which includes the `rs-convert.exe` utility.
   - You can download it from the [Intel RealSense website](https://www.intelrealsense.com/sdk-2/)

## Usage

1. Run the application:
   ```
   python bag_converter.py
   ```

2. Configure the application:
   - Click "Browse" to select the path to your `rs-convert.exe` utility
   - Click "Browse" to select the directory containing your .bag files

3. Select the files you want to convert:
   - Use "Select All" or "Select None" to quickly manage file selection
   - Or manually check/uncheck individual files

4. Click "Start Conversion" to begin the process

5. Monitor the progress:
   - The progress bar shows overall completion
   - Status messages provide details about the current operation
   - Estimated time remaining is displayed during conversion

6. Cancel the conversion at any time by clicking the "Cancel" button

## Output Structure

For each converted .bag file named `example.bag`, the application creates:

```
/selected_directory
  /example
    example.bag (copy of the original)
    /example_ply
      /ply (extracted 3D point cloud data)
    /example_png
      /png (extracted image data)
```

## Development

The application is built with PyQt5 and utilizes threading to keep the UI responsive during long conversion processes.

### Key Components:

- `BagConverterApp`: Main application window and UI
- `ConversionWorker`: Background worker thread that handles file conversion without freezing the UI

## License

[MIT License](LICENSE)

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add some amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## Acknowledgments

- This application utilizes the Intel RealSense SDK
- Thanks to the PyQt5 team for providing the GUI framework
