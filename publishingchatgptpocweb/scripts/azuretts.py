import azure.cognitiveservices.speech as speechsdk
import requests

class AzureTTS:
    def __init__(self, speech_key, service_region):        
        self.speech_key = speech_key
        self.service_region = service_region

        self.voices  = self.fetch_available_voices()
        self.voice_names  = [voice['ShortName'] for voice in self.voices]
        self.speech_config = speechsdk.SpeechConfig(subscription=self.speech_key, region=self.service_region)
        self.switch_voice("en-GB-AlfieNeural")   

        # audio_output = speechsdk.audio.AudioOutputConfig(filename=audio_file_path)     
        # self.speech_synthesizer = speechsdk.SpeechSynthesizer(speech_config=self.speech_config, audio_config=audio_output)
        self.speech_synthesizer = speechsdk.SpeechSynthesizer(speech_config=self.speech_config)


    def fetch_available_voices(self):
        endpoint = f"https://{self.service_region}.tts.speech.microsoft.com/cognitiveservices/voices/list"
        headers = {
            "Ocp-Apim-Subscription-Key": self.speech_key
        }
        response = requests.get(endpoint, headers=headers)
        if response.status_code == 200:
            return response.json()
        else:
            response.raise_for_status()

    # ... other parts of the AzureTTS class ...

    def switch_voice(self, voice_name):
        if voice_name in self.voice_names:
            self.voice_name = voice_name
            self.speech_config.speech_synthesis_voice_name = self.voice_name
        else:
            print(f"Voice name '{voice_name}' not found. Using the default voice.")
            self.voice_name="en-GB-EthanNeural"

    def synthesize(self, text):
        result = self.speech_synthesizer.speak_text_async(text).get()
        
        if result.reason == speechsdk.ResultReason.SynthesizingAudioCompleted:
            return True
        elif result.reason == speechsdk.ResultReason.Canceled:
            cancellation_details = result.cancellation_details
            print(f"Speech synthesis canceled: {cancellation_details.reason}")
            if cancellation_details.reason == speechsdk.CancellationReason.Error:
                print(f"Error details: {cancellation_details.error_details}")
            return False
