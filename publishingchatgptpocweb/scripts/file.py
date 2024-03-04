import os
import xml.etree.ElementTree as ET

class FILES:

    def __init__(self, pathconfig):
        self.pathconfig = pathconfig

    def read_eva_settings(self):
        try:
            tree = ET.parse(self.pathconfig.EVA_SETTINGS_FILE_PATH)
            root = tree.getroot()

            max_token = int(root.find('max-token').text)
            temperature = float(root.find('temperature').text)

            if not (100 <= max_token <= 1500) or not (0.2 <= temperature <= 2):
                raise ValueError("Invalid values in settings file")

            return max_token, temperature

        except Exception as e:
            print(f"Exception occurred while reading file: {e}")
            return 500, 1  # return default values on error

    def read_template_files(self):
        with open(self.pathconfig.EVA_TEMPLATE_ANSWER_FILE_PATH, "r") as file:
            eva_answer_template = file.read()

        return eva_answer_template

    def save_template(self, file_name, content):
        try:
            file_path = os.path.join(self.pathconfig.EVA_TEMPLATES_DIRECTORY, file_name)
            with open(file_path, 'w') as file:
                file.write(content)
            return 'File saved successfully!', 200

        except Exception as e:
            return f'An error occurred while saving the file: {e}', 500

    def save_settings(self, max_token, temperature):
        try:
            root = ET.Element("settings")
            ET.SubElement(root, "max-token").text = max_token
            ET.SubElement(root, "temperature").text = temperature

            tree = ET.ElementTree(root)      
            tree.write(self.pathconfig.EVA_SETTINGS_FILE_PATH)

            return 'Settings saved successfully!', 200

        except Exception as e:
            return f'An error occurred while saving the settings: {e}', 500
    