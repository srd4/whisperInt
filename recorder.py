# Standard library imports
from datetime import datetime, timedelta
from queue import Queue
from tempfile import NamedTemporaryFile

import time
import threading
import io
import requests
import logging

# Third-party imports
from PyQt5.QtCore import QThread, pyqtSignal
import speech_recognition as sr

from openai import OpenAI

import custom_recorder


class AudioRecorder(QThread):
    update_text = pyqtSignal(str)
    started_listening = pyqtSignal()
    stopped_listening = pyqtSignal()
    force_transcribe_signal = pyqtSignal()

    def __init__(self, energy_threshold, record_timeout, phrase_timeout, device_index, whisperInt_auth_header, openai_api_key, transcription_service="whisperInt"):
        super().__init__()
        self.energy_threshold = energy_threshold
        self.record_timeout = record_timeout
        self.phrase_timeout = phrase_timeout
        self.device_index = device_index
        self.MIN_DURATION = 2
        self.running = False
        self.temp_file = NamedTemporaryFile(suffix=".wav").name
        self.data_queue = Queue()
        self.background_listening = None
        self.whisperInt_auth_header = whisperInt_auth_header
        self.openai_api_key = openai_api_key
        self.transcription_service = transcription_service

        self.recorder = custom_recorder.CustomBackgroundRecorder()
        self.recorder.energy_threshold = self.energy_threshold
        self.recorder.dynamic_energy_threshold = False

        self.client = OpenAI(
            api_key=self.openai_api_key,
        )
        
        self.force_transcribe_signal.connect(self.force_transcribe)
        
    def force_transcribe(self):
        # Set the force_callback flag to True to ensure the next audio sample is processed
        self.recorder.force_stop = True


    def start_listening(self):
        # Find the index of the microphone by name (since device names tend to change less)
        self.source = sr.Microphone(sample_rate=16000, device_index=self.device_index)

        with self.source as mic:
            self.recorder.adjust_for_ambient_noise(mic)

        if self.background_listening is None:
            self.background_listening = self.recorder.listen_in_background(
                self.source, self.record_callback, phrase_time_limit=self.record_timeout
            )

    def stop_listening(self):
        if self.background_listening is not None:
            self.background_listening(wait_for_stop=False)
            self.background_listening = None

    def transcribe_with_whisper(self, audio_file, duration):
        transcript = None
        start_time = datetime.now()
        def transcription_thread():
            nonlocal transcript
            try:
                transcript = str(self.client.audio.transcriptions.create(
                    model="whisper-1",
                    file=audio_file,
                    response_format="text",
                ))
            except Exception as e:
                transcript = "Problem with transcription: " + str(e)

        t = threading.Thread(target=transcription_thread)
        t.start()
        t.join(timeout=3.5)
        if t.is_alive():
            transcript = "Transcription timed out after 5 seconds."
            t.join()  # Ensure thread is cleaned up even if it has timed out
        latency = datetime.now() - start_time
        seconds = latency.total_seconds()
        logging.info(f"Whisper transcription latency: {seconds} seconds for {duration} seconds of audio ({seconds/duration})")
        return transcript


    def transcribe_with_huggingface(self, audio_file, auth_header, duration):
        transcript = None
        API_URL = "https://y63omv344x74unnb.us-east-1.aws.endpoints.huggingface.cloud"
        headers = {
            "Authorization": auth_header,
            "Content-Type": "audio/wav"
        }

        def transcription_thread():
            nonlocal transcript
            start_time = datetime.now()
            with open(audio_file, "rb") as f:
                data = f.read()
            response = requests.post(API_URL, headers=headers, data=data)
            latency = datetime.now() - start_time
            seconds = latency.total_seconds()
            logging.info(f"HuggingFace transcription latency: {seconds} seconds for {duration} seconds of audio ({seconds/duration})")
            transcript = response.json().get("text", "No transcription available")

        t = threading.Thread(target=transcription_thread)
        t.start()
        t.join(timeout=3.5)
        if t.is_alive():
            transcript = "Transcription timed out after 5 seconds."
            t.join()  # Ensure thread is cleaned up even if it has timed out
        return transcript


    def process_audio_data(self, raw_data):
        audio_data = sr.AudioData(raw_data, self.source.SAMPLE_RATE, self.source.SAMPLE_WIDTH)
        duration = len(audio_data.frame_data) / (audio_data.sample_rate * audio_data.sample_width)

        if duration >= self.MIN_DURATION:
            with open(self.temp_file, 'w+b') as f:
                f.write(io.BytesIO(audio_data.get_wav_data()).read())
                f.seek(0)
                transcript = ""
                if self.transcription_service == 'whisper':
                    # Use OpenAI Whisper for transcription
                    transcript = self.transcribe_with_whisper(f, duration)
                elif self.transcription_service == 'whisperInt':
                    # Use HuggingFace endpoint for transcription
                    transcript = self.transcribe_with_huggingface(self.temp_file, self.whisperInt_auth_header, duration)
                if transcript:
                    self.update_text.emit(transcript+"\n")
                    logging.info(f"Transcription length: {len(transcript.split())} words, duration: {duration:.2f} seconds, proportion: {len(transcript.split()) / duration:.2f} words per second")

    def run(self):
        self.start_listening()
        DELTA = timedelta(seconds=self.phrase_timeout)
        phrase_time = None
        self.last_sample = bytes()
        self.english_transcript_buffer = []
        self.spanish_transcript_buffer = []

        self.started_listening.emit()

        while self.running:
            try:
                now = datetime.utcnow()
                if not self.data_queue.empty():
                    if phrase_time and (now - phrase_time) > DELTA:
                        self.last_sample = bytes()
                    phrase_time = now

                    while not self.data_queue.empty():
                        self.last_sample += self.data_queue.get()
                    
                    self.process_audio_data(self.last_sample)
            except sr.WaitTimeoutError:
                pass
            time.sleep(1/10)


    def start_recording(self):
        if not self.running:
            self.running = True
            self.start()

    def stop_recording(self):
        if self.running:
            self.running = False
            self.stop_listening()
            self.wait()
            self.stopped_listening.emit()
        
    # Threaded callback function to recieve audio data when recordings finish.
    def record_callback(self, _, audio:sr.AudioData) -> None:
        if self.running:# If running.
            # Grab the raw bytes and push it into the thread safe queue.
            self.data_queue.put( audio.get_raw_data() )