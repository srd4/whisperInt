import configparser
import os

class SettingsManager:
    def __init__(self, config_file='config.ini'):
        self.config = configparser.ConfigParser()
        self.config_file = config_file
        if not os.path.exists(config_file):
            self.create_default_config()
        self.load_settings()

    def create_default_config(self):
        # Set default values for the configuration
        self.config['DEFAULT'] = {
            'openai_api_key': '',
            'whisperInt_auth_header': '',
            'device_name': 'Default Device',
            'device_index': '0',
            'transcription_service': 'none',
            'energy_threshold': '1000',
            'record_timeout': '23',
            'phrase_timeout': '1.5',
            'font_size': '12'
        }
        self.save_config()

    def load_settings(self):
        try:
            self.config.read(self.config_file)
            self.openai_api_key = self.config.get('DEFAULT', 'openai_api_key', fallback='')
            self.huggingface_auth_header = self.config.get('DEFAULT', 'whisperInt_auth_header', fallback='')
            self.device_name = self.config.get('DEFAULT', 'device_name', fallback='Default Device')
            self.device_index = self.config.getint('DEFAULT', 'device_index', fallback=0)
            self.translation_service = self.config.get('DEFAULT', 'transcription_service', fallback='none')
            self.energy_threshold = self.config.getint('DEFAULT', 'energy_threshold', fallback=1000)
            self.record_timeout = self.config.getint('DEFAULT', 'record_timeout', fallback=23)
            self.phrase_timeout = self.config.getfloat('DEFAULT', 'phrase_timeout', fallback=1.5)
            self.phrase_timeout = self.config.getint('DEFAULT', 'font_size', fallback=16)
        except configparser.Error as e:
            print(f"Error reading configuration file: {e}")
            self.create_default_config()

    def save_config(self):
        with open(self.config_file, 'w') as configfile:
            self.config.write(configfile)

    def get_setting(self, section, option, fallback=None, value_type=str):
        try:
            if value_type == int:
                return self.config.getint(section, option, fallback=fallback)
            elif value_type == float:
                return self.config.getfloat(section, option, fallback=fallback)
            elif value_type == bool:
                return self.config.getboolean(section, option, fallback=fallback)
            else:
                return self.config.get(section, option, fallback=fallback)
        except ValueError as e:
            print(f"Error casting setting value: {e}")
            return fallback
        except configparser.NoOptionError:
            return fallback
        except configparser.NoSectionError:
            if section != 'DEFAULT':
                self.config.add_section(section)
            return fallback

    def set_setting(self, section, option, value):
        if section not in self.config:
            self.config.add_section(section)
        if isinstance(value, bool):
            self.config.set(section, option, str(value).lower())
        elif isinstance(value, int) or isinstance(value, float):
            self.config.set(section, option, str(value))
        else:
            self.config.set(section, option, str(value))
        # Update the corresponding attribute if it exists
        attribute_name = option.lower()
        if hasattr(self, attribute_name):
            if isinstance(value, int) or isinstance(value, float):
                setattr(self, attribute_name, value)
            else:
                setattr(self, attribute_name, str(value))
        self.save_config()

