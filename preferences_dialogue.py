from PyQt5.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton, QComboBox, QSpinBox
from PyQt5.QtCore import pyqtSignal

import speech_recognition as sr
import sounddevice as sd

class PreferencesDialog(QDialog):
    preferencesUpdated = pyqtSignal()

    def __init__(self, settings_manager, parent=None):
        super().__init__(parent)
        self.settings_manager = settings_manager
        self.initUI()
        self.setWindowTitle('Preferences')  # Set window title to 'Preferences'
        self.resize(self.width() * 6, self.height())  # Make the window twice as wide

    def initUI(self):
        layout = QVBoxLayout(self)

        # API Key
        api_key_layout = QHBoxLayout()
        api_key_label = QLabel('OpenAI Whisper API Key:', self)
        self.api_key_input = QLineEdit(self)
        self.api_key_input.setEchoMode(QLineEdit.Password)  # Set the echo mode to password to hide the API key
        self.api_key_input.setText(self.settings_manager.get_setting('DEFAULT', 'openai_api_key', fallback=''))
        self.show_api_key_button = QPushButton('Show', self)  # Button to toggle visibility of the API key
        self.show_api_key_button.setCheckable(True)
        self.show_api_key_button.toggled.connect(self.toggle_api_key_visibility)
        api_key_layout.addWidget(api_key_label)
        api_key_layout.addWidget(self.api_key_input)
        api_key_layout.addWidget(self.show_api_key_button)
        layout.addLayout(api_key_layout)

        # whisperInt API Key
        whisperInt_api_key_layout = QHBoxLayout()
        whisperInt_api_key_label = QLabel('WhisperInt API Key:', self)
        self.whisperInt_api_key_input = QLineEdit(self)
        self.whisperInt_api_key_input.setEchoMode(QLineEdit.Password)  # Set the echo mode to password to hide the API key
        self.whisperInt_api_key_input.setText(self.settings_manager.get_setting('DEFAULT', 'whisperInt_auth_header', fallback=''))
        self.show_whisperInt_api_key_button = QPushButton('Show', self)  # Button to toggle visibility of the API key
        self.show_whisperInt_api_key_button.setCheckable(True)
        self.show_whisperInt_api_key_button.toggled.connect(lambda checked: self.whisperInt_api_key_input.setEchoMode(QLineEdit.Normal if checked else QLineEdit.Password))
        whisperInt_api_key_layout.addWidget(whisperInt_api_key_label)
        whisperInt_api_key_layout.addWidget(self.whisperInt_api_key_input)
        whisperInt_api_key_layout.addWidget(self.show_whisperInt_api_key_button)
        layout.addLayout(whisperInt_api_key_layout)

        # Device Name
        device_name_layout = QHBoxLayout()
        device_name_label = QLabel('Device Name:', self)
        self.device_name_input = QComboBox(self)
        device_names = sr.Microphone.list_microphone_names()
        self.device_name_input.addItems(device_names)
        device_name_setting = self.settings_manager.get_setting('DEFAULT', 'device_name', fallback='')
        current_device_index = device_names.index(device_name_setting) if device_name_setting in device_names else self.settings_manager.get_setting('DEFAULT', 'device_index', fallback=0, value_type=int)
        self.device_name_input.setCurrentIndex(current_device_index)
        device_name_layout.addWidget(device_name_label)
        device_name_layout.addWidget(self.device_name_input)
        layout.addLayout(device_name_layout)

        # Transcription Service
        transcription_service_layout = QHBoxLayout()
        transcription_service_label = QLabel('Transcription Service:', self)
        self.transcription_service_dropdown = QComboBox(self)
        transcription_services = ['whisper', 'whisperInt']
        self.transcription_service_dropdown.addItems(transcription_services)
        self.transcription_service_dropdown.setCurrentText(self.settings_manager.get_setting('DEFAULT', 'transcription_service', fallback='none'))
        transcription_service_layout.addWidget(transcription_service_label)
        transcription_service_layout.addWidget(self.transcription_service_dropdown)
        layout.addLayout(transcription_service_layout)

        # Font Size
        font_size_layout = QHBoxLayout()
        font_size_label = QLabel('Font Size:', self)
        self.font_size_spinbox = QSpinBox(self)
        self.font_size_spinbox.setRange(8, 32)  # Assuming a reasonable range for font sizes
        self.font_size_spinbox.setValue(self.settings_manager.get_setting('DEFAULT', 'font_size', fallback=16, value_type=int))
        font_size_layout.addWidget(font_size_label)
        font_size_layout.addWidget(self.font_size_spinbox)
        layout.addLayout(font_size_layout)

        # Restart App Label
        restart_app_label = QLabel('You might need to either stop and restart listening or close and re-open the app for some setup preferences changes to apply.', self)
        layout.addWidget(restart_app_label)

        # Save Button
        save_button = QPushButton('Save', self)
        save_button.clicked.connect(self.save_preferences)
        layout.addWidget(save_button)

    def save_preferences(self):
        # Update settings with the new values from the input fields
        self.settings_manager.set_setting('DEFAULT', 'openai_api_key', self.api_key_input.text())
        self.settings_manager.set_setting('DEFAULT', 'whisperInt_auth_header', self.whisperInt_api_key_input.text())
        self.settings_manager.set_setting('DEFAULT', 'device_name', self.device_name_input.currentText())
        self.settings_manager.set_setting('DEFAULT', 'device_index', self.device_name_input.currentIndex())
        self.settings_manager.set_setting('DEFAULT', 'transcription_service', self.transcription_service_dropdown.currentText())
        self.settings_manager.set_setting('DEFAULT', 'font_size', self.font_size_spinbox.value())
        self.settings_manager.save_config()
        self.accept()
        
        self.preferencesUpdated.emit()

    def toggle_api_key_visibility(self, checked):
        if checked:
            self.api_key_input.setEchoMode(QLineEdit.Normal)
        else:
            self.api_key_input.setEchoMode(QLineEdit.Password)

