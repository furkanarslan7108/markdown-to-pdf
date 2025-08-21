import os
import sys
from datetime import datetime
from pathlib import Path

from PyQt6.QtCore import Qt, QThread, pyqtSignal, QSettings
from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout,
                             QHBoxLayout, QLabel, QLineEdit, QPushButton,
                             QTextEdit, QFileDialog, QProgressBar, QGroupBox,
                             QCheckBox, QSpinBox, QComboBox, QMessageBox,
                             QTabWidget, QGridLayout, QSlider, QStatusBar)

from markdown_to_pdf_converter import MarkdownToPDFConverter


class ConversionThread(QThread):
	"""Thread for handling the conversion process"""
	progress_updated = pyqtSignal(int)
	status_updated = pyqtSignal(str)
	conversion_finished = pyqtSignal(bool, str)

	def __init__(self, converter, input_file, output_file, title, options):
		super().__init__()
		self.converter = converter
		self.input_file = input_file
		self.output_file = output_file
		self.title = title
		self.options = options

	def run(self):
		try:
			self.status_updated.emit("Reading markdown file...")
			self.progress_updated.emit(10)

			# Update converter options
			self.converter.pdf_options.update(self.options)

			self.status_updated.emit("Converting markdown to HTML...")
			self.progress_updated.emit(30)

			self.status_updated.emit("Processing images...")
			self.progress_updated.emit(50)

			self.status_updated.emit("Generating PDF...")
			self.progress_updated.emit(80)

			output_path = self.converter.convert_to_pdf(
				self.input_file,
				self.output_file,
				self.title
			)

			self.progress_updated.emit(100)
			self.status_updated.emit("Conversion completed successfully!")
			self.conversion_finished.emit(True, output_path)

		except Exception as e:
			self.status_updated.emit(f"Error: {str(e)}")
			self.conversion_finished.emit(False, str(e))


class MarkdownToPDFGUI(QMainWindow):
	def __init__(self):
		super().__init__()
		self.converter = MarkdownToPDFConverter()
		self.settings = QSettings('MarkdownToPDF', 'Converter')
		self.conversion_thread = None

		self.init_ui()
		self.load_settings()

	def init_ui(self):
		self.setWindowTitle("Markdown to PDF Converter")
		self.setGeometry(100, 100, 1000, 700)

		# Create central widget and main layout
		central_widget = QWidget()
		self.setCentralWidget(central_widget)

		layout = QVBoxLayout(central_widget)

		# Create tab widget
		self.tab_widget = QTabWidget()
		layout.addWidget(self.tab_widget)

		# Create tabs
		self.create_conversion_tab()
		self.create_settings_tab()
		self.create_preview_tab()

		# Status bar
		self.status_bar = QStatusBar()
		self.setStatusBar(self.status_bar)
		self.status_bar.showMessage("Ready")

		# Progress bar
		self.progress_bar = QProgressBar()
		self.progress_bar.setVisible(False)
		layout.addWidget(self.progress_bar)

		# Apply styling
		# self.apply_styles()

	def create_conversion_tab(self):
		tab = QWidget()
		layout = QVBoxLayout(tab)

		# File selection group
		file_group = QGroupBox("File Selection")
		file_layout = QGridLayout(file_group)

		# Input file
		file_layout.addWidget(QLabel("Markdown File:"), 0, 0)
		self.input_file_edit = QLineEdit()
		self.input_file_edit.setPlaceholderText("Select a markdown file...")
		file_layout.addWidget(self.input_file_edit, 0, 1)

		self.browse_input_btn = QPushButton("Browse")
		self.browse_input_btn.clicked.connect(self.browse_input_file)
		file_layout.addWidget(self.browse_input_btn, 0, 2)

		# Output file
		file_layout.addWidget(QLabel("Output PDF:"), 1, 0)
		self.output_file_edit = QLineEdit()
		self.output_file_edit.setPlaceholderText("Output file (optional - will auto-generate)")
		file_layout.addWidget(self.output_file_edit, 1, 1)

		self.browse_output_btn = QPushButton("Browse")
		self.browse_output_btn.clicked.connect(self.browse_output_file)
		file_layout.addWidget(self.browse_output_btn, 1, 2)

		# Document title
		file_layout.addWidget(QLabel("Document Title:"), 2, 0)
		self.title_edit = QLineEdit()
		self.title_edit.setPlaceholderText("Optional document title")
		file_layout.addWidget(self.title_edit, 2, 1, 1, 2)

		layout.addWidget(file_group)

		# Conversion options
		options_group = QGroupBox("Quick Options")
		options_layout = QGridLayout(options_group)

		# Page size
		options_layout.addWidget(QLabel("Page Size:"), 0, 0)
		self.page_size_combo = QComboBox()
		self.page_size_combo.addItems(['A4', 'Letter', 'A3', 'A5', 'Legal'])
		options_layout.addWidget(self.page_size_combo, 0, 1)

		# Include images
		self.include_images_cb = QCheckBox("Include Images")
		self.include_images_cb.setChecked(True)
		options_layout.addWidget(self.include_images_cb, 0, 2)

		layout.addWidget(options_group)

		# Conversion button
		self.convert_btn = QPushButton("Convert to PDF")
		self.convert_btn.setStyleSheet("""
            QPushButton {
                background-color: #3498db;
                color: white;
                border: none;
                padding: 10px;
                font-size: 14px;
                font-weight: bold;
                border-radius: 5px;
            }
            QPushButton:hover {
                background-color: #2980b9;
            }
            QPushButton:disabled {
                background-color: #bdc3c7;
            }
        """)
		self.convert_btn.clicked.connect(self.start_conversion)
		layout.addWidget(self.convert_btn)

		# Log area
		log_group = QGroupBox("Conversion Log")
		log_layout = QVBoxLayout(log_group)

		self.log_text = QTextEdit()
		self.log_text.setMaximumHeight(150)
		self.log_text.setReadOnly(True)
		log_layout.addWidget(self.log_text)

		layout.addWidget(log_group)

		self.tab_widget.addTab(tab, "Convert")

	def create_settings_tab(self):
		tab = QWidget()
		layout = QVBoxLayout(tab)

		# PDF Settings
		pdf_group = QGroupBox("PDF Settings")
		pdf_layout = QGridLayout(pdf_group)

		# Margins
		pdf_layout.addWidget(QLabel("Margins (inches):"), 0, 0, 1, 2)

		pdf_layout.addWidget(QLabel("Top:"), 1, 0)
		self.margin_top_spin = QSpinBox()
		self.margin_top_spin.setRange(0, 5)
		self.margin_top_spin.setValue(1)
		self.margin_top_spin.setSuffix(" in")
		pdf_layout.addWidget(self.margin_top_spin, 1, 1)

		pdf_layout.addWidget(QLabel("Bottom:"), 1, 2)
		self.margin_bottom_spin = QSpinBox()
		self.margin_bottom_spin.setRange(0, 5)
		self.margin_bottom_spin.setValue(1)
		self.margin_bottom_spin.setSuffix(" in")
		pdf_layout.addWidget(self.margin_bottom_spin, 1, 3)

		pdf_layout.addWidget(QLabel("Left:"), 2, 0)
		self.margin_left_spin = QSpinBox()
		self.margin_left_spin.setRange(0, 5)
		self.margin_left_spin.setValue(1)
		self.margin_left_spin.setSuffix(" in")
		pdf_layout.addWidget(self.margin_left_spin, 2, 1)

		pdf_layout.addWidget(QLabel("Right:"), 2, 2)
		self.margin_right_spin = QSpinBox()
		self.margin_right_spin.setRange(0, 5)
		self.margin_right_spin.setValue(1)
		self.margin_right_spin.setSuffix(" in")
		pdf_layout.addWidget(self.margin_right_spin, 2, 3)

		layout.addWidget(pdf_group)

		# Image Settings
		image_group = QGroupBox("Image Settings")
		image_layout = QGridLayout(image_group)

		image_layout.addWidget(QLabel("Max Image Width:"), 0, 0)
		self.image_width_spin = QSpinBox()
		self.image_width_spin.setRange(200, 2000)
		self.image_width_spin.setValue(800)
		self.image_width_spin.setSuffix(" px")
		image_layout.addWidget(self.image_width_spin, 0, 1)

		image_layout.addWidget(QLabel("Image Quality:"), 1, 0)
		self.image_quality_slider = QSlider(Qt.Orientation.Horizontal)
		self.image_quality_slider.setRange(10, 100)
		self.image_quality_slider.setValue(85)
		self.quality_label = QLabel("85%")
		self.image_quality_slider.valueChanged.connect(
			lambda v: self.quality_label.setText(f"{v}%")
		)
		image_layout.addWidget(self.image_quality_slider, 1, 1)
		image_layout.addWidget(self.quality_label, 1, 2)

		layout.addWidget(image_group)

		# wkhtmltopdf path
		path_group = QGroupBox("wkhtmltopdf Configuration")
		path_layout = QGridLayout(path_group)

		path_layout.addWidget(QLabel("wkhtmltopdf Path:"), 0, 0)
		self.wkhtmltopdf_path_edit = QLineEdit()
		self.wkhtmltopdf_path_edit.setPlaceholderText("Leave empty if in PATH")
		path_layout.addWidget(self.wkhtmltopdf_path_edit, 0, 1)

		self.browse_wkhtmltopdf_btn = QPushButton("Browse")
		self.browse_wkhtmltopdf_btn.clicked.connect(self.browse_wkhtmltopdf)
		path_layout.addWidget(self.browse_wkhtmltopdf_btn, 0, 2)

		layout.addWidget(path_group)

		# Save settings button
		save_settings_btn = QPushButton("Save Settings")
		save_settings_btn.clicked.connect(self.save_settings)
		layout.addWidget(save_settings_btn)

		layout.addStretch()

		self.tab_widget.addTab(tab, "Settings")

	def create_preview_tab(self):
		tab = QWidget()
		layout = QVBoxLayout(tab)

		# Preview controls
		controls_layout = QHBoxLayout()

		self.preview_btn = QPushButton("Generate Preview")
		self.preview_btn.clicked.connect(self.generate_preview)
		controls_layout.addWidget(self.preview_btn)

		controls_layout.addStretch()

		layout.addLayout(controls_layout)

		# Preview area
		self.preview_area = QTextEdit()
		self.preview_area.setReadOnly(True)
		layout.addWidget(self.preview_area)

		self.tab_widget.addTab(tab, "Preview")

	def apply_styles(self):
		self.setStyleSheet("""
            QMainWindow {
                background-color: #f5f5f5;
            }
            QGroupBox {
                font-weight: bold;
                border: 2px solid #cccccc;
                border-radius: 5px;
                margin: 3px;
                padding-top: 10px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px 0 5px;
            }
            QLineEdit {
                border: 1px solid #ddd;
                border-radius: 3px;
                padding: 5px;
                font-size: 12px;
            }
            QPushButton {
                border: 1px solid #ddd;
                border-radius: 3px;
                padding: 5px 10px;
                background-color: white;
            }
            QPushButton:hover {
                background-color: #e9e9e9;
            }
            QComboBox {
                border: 1px solid #ddd;
                border-radius: 3px;
                padding: 5px;
            }
        """)

	def browse_input_file(self):
		file_path, _ = QFileDialog.getOpenFileName(
			self, "Select Markdown File", "",
			"Markdown Files (*.md *.markdown);;All Files (*)"
		)
		if file_path:
			self.input_file_edit.setText(file_path)
			# Auto-generate output filename
			if not self.output_file_edit.text():
				output_path = str(Path(file_path).with_suffix('.pdf'))
				self.output_file_edit.setText(output_path)
			# Auto-generate title
			if not self.title_edit.text():
				title = Path(file_path).stem.replace('_', ' ').replace('-', ' ').title()
				self.title_edit.setText(title)

	def browse_output_file(self):
		file_path, _ = QFileDialog.getSaveFileName(
			self, "Save PDF As", "",
			"PDF Files (*.pdf);;All Files (*)"
		)
		if file_path:
			self.output_file_edit.setText(file_path)

	def browse_wkhtmltopdf(self):
		file_path, _ = QFileDialog.getOpenFileName(
			self, "Select wkhtmltopdf Executable", "",
			"Executable Files (*.exe);;All Files (*)"
		)
		if file_path:
			self.wkhtmltopdf_path_edit.setText(file_path)

	def get_pdf_options(self):
		"""Get PDF options from the settings"""
		return {
			'page-size': self.page_size_combo.currentText(),
			'margin-top': f'{self.margin_top_spin.value()}in',
			'margin-bottom': f'{self.margin_bottom_spin.value()}in',
			'margin-left': f'{self.margin_left_spin.value()}in',
			'margin-right': f'{self.margin_right_spin.value()}in',
			'encoding': "UTF-8",
			'no-outline': None,
			'enable-local-file-access': None
		}

	def start_conversion(self):
		input_file = self.input_file_edit.text().strip()
		if not input_file:
			QMessageBox.warning(self, "Warning", "Please select an input markdown file.")
			return

		if not os.path.exists(input_file):
			QMessageBox.warning(self, "Warning", "Input file does not exist.")
			return

		output_file = self.output_file_edit.text().strip()
		title = self.title_edit.text().strip()

		# Update converter settings
		wkhtmltopdf_path = self.wkhtmltopdf_path_edit.text().strip()
		if wkhtmltopdf_path:
			self.converter = MarkdownToPDFConverter(wkhtmltopdf_path)
		else:
			self.converter = MarkdownToPDFConverter()

		# Get PDF options
		options = self.get_pdf_options()

		# Disable convert button and show progress
		self.convert_btn.setEnabled(False)
		self.progress_bar.setVisible(True)
		self.progress_bar.setValue(0)

		# Clear log
		self.log_text.clear()

		# Start conversion thread
		self.conversion_thread = ConversionThread(
			self.converter, input_file, output_file, title, options
		)
		self.conversion_thread.progress_updated.connect(self.progress_bar.setValue)
		self.conversion_thread.status_updated.connect(self.update_status)
		self.conversion_thread.conversion_finished.connect(self.conversion_finished)
		self.conversion_thread.start()

	def update_status(self, message):
		self.status_bar.showMessage(message)
		self.log_text.append(f"[{datetime.now().strftime('%H:%M:%S')}] {message}")

	def conversion_finished(self, success, result):
		self.convert_btn.setEnabled(True)
		self.progress_bar.setVisible(False)

		if success:
			QMessageBox.information(
				self, "Success",
				f"PDF created successfully!\n\nSaved to: {result}"
			)
			# Ask if user wants to open the file
			reply = QMessageBox.question(
				self, "Open PDF",
				"Would you like to open the generated PDF?",
				QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
			)
			if reply == QMessageBox.StandardButton.Yes:
				os.startfile(result) if os.name == 'nt' else os.system(f'open "{result}"')
		else:
			QMessageBox.critical(self, "Error", f"Conversion failed:\n\n{result}")

	def generate_preview(self):
		input_file = self.input_file_edit.text().strip()
		if not input_file:
			QMessageBox.warning(self, "Warning", "Please select an input markdown file.")
			return

		try:
			with open(input_file, 'r', encoding='utf-8') as f:
				markdown_content = f.read()

			html_content = self.converter.markdown_to_html(markdown_content)
			self.preview_area.setHtml(html_content)

		except Exception as e:
			QMessageBox.critical(self, "Preview Error", f"Could not generate preview:\n\n{str(e)}")

	def save_settings(self):
		"""Save current settings"""
		self.settings.setValue('page_size', self.page_size_combo.currentText())
		self.settings.setValue('margin_top', self.margin_top_spin.value())
		self.settings.setValue('margin_bottom', self.margin_bottom_spin.value())
		self.settings.setValue('margin_left', self.margin_left_spin.value())
		self.settings.setValue('margin_right', self.margin_right_spin.value())
		self.settings.setValue('image_width', self.image_width_spin.value())
		self.settings.setValue('image_quality', self.image_quality_slider.value())
		self.settings.setValue('wkhtmltopdf_path', self.wkhtmltopdf_path_edit.text())
		self.settings.setValue('include_images', self.include_images_cb.isChecked())

		QMessageBox.information(self, "Settings", "Settings saved successfully!")

	def load_settings(self):
		"""Load saved settings"""
		page_size = self.settings.value('page_size', 'A4')
		if page_size in ['A4', 'Letter', 'A3', 'A5', 'Legal']:
			self.page_size_combo.setCurrentText(page_size)

		self.margin_top_spin.setValue(int(self.settings.value('margin_top', 1)))
		self.margin_bottom_spin.setValue(int(self.settings.value('margin_bottom', 1)))
		self.margin_left_spin.setValue(int(self.settings.value('margin_left', 1)))
		self.margin_right_spin.setValue(int(self.settings.value('margin_right', 1)))
		self.image_width_spin.setValue(int(self.settings.value('image_width', 800)))
		self.image_quality_slider.setValue(int(self.settings.value('image_quality', 85)))
		self.wkhtmltopdf_path_edit.setText(self.settings.value('wkhtmltopdf_path', ''))
		self.include_images_cb.setChecked(self.settings.value('include_images', True, type=bool))

	def closeEvent(self, event):
		"""Handle application close"""
		self.save_settings()
		if self.conversion_thread and self.conversion_thread.isRunning():
			reply = QMessageBox.question(
				self, "Close Application",
				"Conversion is in progress. Are you sure you want to close?",
				QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
			)
			if reply == QMessageBox.StandardButton.No:
				event.ignore()
				return
			self.conversion_thread.terminate()
		event.accept()


def main():
	app = QApplication(sys.argv)
	app.setApplicationName("Markdown to PDF Converter")
	app.setOrganizationName("YourOrganization")

	# Set application icon (optional)
	# app.setWindowIcon(QIcon('icon.png'))

	window = MarkdownToPDFGUI()
	window.show()

	sys.exit(app.exec())


if __name__ == "__main__":
	main()