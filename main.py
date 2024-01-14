# Standard library imports
import sys
import logging

# Third-party imports
from PyQt5.QtGui import QFont
from PyQt5.QtWidgets import (
    QSizePolicy, QApplication, QMainWindow,
    QTextEdit, QVBoxLayout, QMenuBar, QAction, QPushButton, QWidget,
    )

from PyQt5.QtCore import pyqtSignal, QObject

# Replaced keyboard library with pynput for hotkeys
from pynput import keyboard

from recorder import AudioRecorder
# from player import AudioPlayer
from settings_manager import SettingsManager
from preferences_dialogue import PreferencesDialog
# from audio_stream_processor import AudioStreamProcessor

# Configure logging
logging.basicConfig(filename='app.log', filemode='w', level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

class Communicate(QObject):
    force_transcribe_signal = pyqtSignal()

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        logging.info('Initializing MainWindow')
        self.settings_manager = SettingsManager()
        self.initUI()
        self.audio_recorder = None
        self.init_audio_recorder()
        self.installEventFilter(self)  # Install an event filter to capture key events globally

        # Set up keyboard hotkeys for toggling the mic and transcribe buttons
        self.setup_keyboard_hotkeys()

        # Initialize communication signal
        self.comm = Communicate()
        self.comm.force_transcribe_signal.connect(self.force_transcribe)

    def setup_keyboard_hotkeys(self):
        # Set up hotkeys using pynput
        self.listener = keyboard.GlobalHotKeys({
            '<ctrl>+k': lambda: self.comm.force_transcribe_signal.emit(),
        })
        self.listener.start()
        logging.info('Keyboard hotkeys set up')

    def open_preferences(self):
        logging.info('Opening preferences dialog')
        dialog = PreferencesDialog(self.settings_manager, self)
        dialog.preferencesUpdated.connect(self.apply_new_preferences)
        dialog.exec_()  # This will show the dialog as a modal window

    def apply_new_preferences(self):
        # Apply new preferences without the need to restart the application
        logging.info('Applying new preferences')
        if self.audio_recorder:
            self.audio_recorder.openai_api_key = self.settings_manager.get_setting('DEFAULT', 'openai_api_key')
            self.audio_recorder.huggingface_auth_header = self.settings_manager.get_setting('DEFAULT', 'whisperInt_auth_header')
            self.audio_recorder.device_index = self.settings_manager.get_setting('DEFAULT', 'device_index', value_type=int)

        font_size = self.settings_manager.get_setting('DEFAULT', 'font_size', fallback=12, value_type=int)
        font = QFont("Arial", font_size)
        self.text_edit.setFont(font)

    def init_audio_recorder(self):
        logging.info('Initializing audio recorder')
        if self.audio_recorder:
            self.audio_recorder.stop_recording()
    
        self.audio_recorder = AudioRecorder(
            energy_threshold=self.settings_manager.get_setting('DEFAULT', 'energy_threshold', fallback=1000, value_type=int),
            record_timeout=self.settings_manager.get_setting('DEFAULT', 'record_timeout', fallback=18, value_type=int),
            phrase_timeout=self.settings_manager.get_setting('DEFAULT', 'phrase_timeout', fallback=1/10, value_type=float),
            device_index=self.settings_manager.get_setting('DEFAULT', 'device_index', fallback=0, value_type=int),
            whisperInt_auth_header=self.settings_manager.get_setting('DEFAULT', 'whisperInt_auth_header'),
            openai_api_key=self.settings_manager.get_setting('DEFAULT', 'openai_api_key'),
            transcription_service=self.settings_manager.get_setting('DEFAULT', 'transcription_service', fallback="whisperInt"),
        )

        self.audio_recorder.update_text.connect(self.update_text)
        self.audio_recorder.started_listening.connect(self.on_recording_started)
        self.audio_recorder.stopped_listening.connect(self.on_recording_stopped)

    def on_recording_started(self):
        logging.info('Recording started')
        self.start_button.setText('Stop Listening')
        self.start_button.setStyleSheet("QPushButton { background-color: #90EE90; border: none; }")

    def on_recording_stopped(self):
        logging.info('Recording stopped')
        self.start_button.setText('Start Listening')
        self.start_button.setStyleSheet("QPushButton { background-color: none; }")

    def toggle_recording(self):
        logging.info('Toggling recording')
        if self.audio_recorder and self.audio_recorder.running:
            self.audio_recorder.stop_recording()
        else:
            if not self.audio_recorder:
                self.init_audio_recorder()
            self.audio_recorder.start_recording()

    def update_text(self, text):
        self.text_edit.append(text)

    def closeEvent(self, event):
        logging.info('Closing MainWindow')
        if self.audio_recorder:
            self.audio_recorder.stop_recording()
        super().closeEvent(event)

    def force_transcribe(self):
        logging.info('Forcing transcription')
        if self.audio_recorder:
            self.audio_recorder.force_transcribe_signal.emit()

    def initUI(self):
        logging.info('Initializing UI')
        # Set the window title
        self.setWindowTitle('whisperInt')

        # Main layout for the window
        main_layout = QVBoxLayout()

        # Upper layout for transcription and settings
        upper_layout = QVBoxLayout()

        # Menu bar for settings and other options
        top_bar = QMenuBar()
        file_menu = top_bar.addMenu('File')
        main_layout.setMenuBar(top_bar)

        # Text edit area for displaying transcriptions
        self.text_edit = QTextEdit(self)
        self.text_edit.setReadOnly(True)  # Make the text_edit read-only
        font = QFont("Arial", self.settings_manager.get_setting('DEFAULT', 'font_size', fallback='default', value_type=int))
        self.text_edit.setFont(font)
        upper_layout.addWidget(self.text_edit, 1)  # Set stretch factor to 1

        # Clear Text edit action on top bar.
        clear_action = QAction('Clear Text', self)
        clear_action.triggered.connect(self.text_edit.clear)
        file_menu.addAction(clear_action)

        # Preferences dialog button on top bar.
        settings_action = QAction('Preferences', self)
        settings_action.triggered.connect(self.open_preferences)
        file_menu.addAction(settings_action)
        
        # Buttons layout for recording controls
        buttons_layout = QVBoxLayout()  # Changed to QVBoxLayout for stacking

        # Toggle button to start/stop the recording process
        self.start_button = QPushButton('Start Listening', self)
        self.start_button.setCheckable(True)
        self.start_button.clicked.connect(self.toggle_recording)
        self.start_button.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Preferred)
        buttons_layout.addWidget(self.start_button)

        # Button to transcribe up to the current point
        self.transcribe_button = QPushButton('Transcribe Here', self)
        self.transcribe_button.clicked.connect(self.force_transcribe)
        self.transcribe_button.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Preferred)
        buttons_layout.addWidget(self.transcribe_button)

        # Resize the window to the screen's size before maximizing to avoid issues on some platforms
        self.resize(QApplication.desktop().screenGeometry().width(), QApplication.desktop().screenGeometry().height())
        # Set the initial position to the top-left corner of the screen
        self.move(0, 0)

        self.showMaximized()
        self.showMaximized()

        bottom_layout = QVBoxLayout()

        # Add upper layout to the main layout
        main_layout.addLayout(upper_layout, 1)  # Set stretch factor to 1
        main_layout.addLayout(bottom_layout, 1)
        
        bottom_layout.addLayout(buttons_layout, 1)
        
        # Container for the main layout
        container = QWidget()
        container.setLayout(main_layout)
        self.setCentralWidget(container)

        # Display the main window
        self.show()


if __name__ == '__main__':
    app = QApplication(sys.argv)
    ex = MainWindow()
    sys.exit(app.exec_())