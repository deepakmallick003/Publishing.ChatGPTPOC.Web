# Application Settings
# From the enviornments vaiables

import os
from pydantic import Field
from pydantic_settings import BaseSettings
from pathlib import Path

class ApplicationSettings(BaseSettings):
    # SEQ_API_KEY: str = Field(alias='SEQ_API_KEY')
    # SEQ_SERVER: str = Field(alias='SEQ_SERVER')
    DEPLOYED_BASE_PATH: str = Field(alias='PublishingChatGPT_DEPLOYED_BASE_PATH')
    FLASK_ENV: str = Field(alias='PublishingChatGPT_FLASK_ENV')  
    USE_WEB_SOCKET: str = Field(alias='PublishingChatGPT_USE_WEB_SOCKET')  

    Open_AI_API_Secret: str = Field(alias='PublishingChatGPT_Open_AI_API_Secret')
    Open_AI_Model: str = Field(alias='PublishingChatGPT_Open_AI_Model')
    
    # AzureAd_TenantId: str = Field(alias='AzureAd_TenantId')
    # AzureAd_ClientId: str = Field(alias='AzureAd_ClientId')
    # AzureAd_ClientSecret: str = Field(alias='AzureAd_ClientSecret')

    # MS_AZURE_SPEECH_KEY: str = Field(alias='MS_AZURE_SPEECH_KEY')
    # MS_AZURE_SPEECH_REGION: str = Field(alias='MS_AZURE_SPEECH_REGION')

    Neo4J_URL: str = Field(alias='PublishingChatGPT_Neo4J_URL')
    Neo4J_UserName: str = Field(alias='PublishingChatGPT_Neo4J_UserName')
    Neo4J_Database: str = Field(alias='PublishingChatGPT_Neo4J_Database')
    Neo4J_Password: str = Field(alias='PublishingChatGPT_Neo4J_Password')
    Neo4J_PrimaryIndexName: str = Field(alias='PublishingChatGPT_Neo4J_PrimaryIndexName')

    PBI_WORKSPACE_ID: str = Field(alias='PublishingChatGPT_PBI_WORKSPACE_ID')
    PBI_REPORT_ID_KG: str = Field(alias='PublishingChatGPT_PBI_REPORT_ID_KG')
    PBI_REPORTd_ID_HM: str = Field(alias='PublishingChatGPT_PBI_REPORT_ID_HM')
    PBI_TENANT_ID: str = Field(alias='PublishingChatGPT_PBI_TENANT_ID')
    PBI_CLIENT_ID: str = Field(alias='PublishingChatGPT_PBI_CLIENT_ID')
    PBI_CLIENT_SECRET: str = Field(alias='PublishingChatGPT_PBI_CLIENT_SECRET')
    PBI_USER: str = Field(alias='PublishingChatGPT_PBI_USER')
    # PBI_PASSWORD: str = Field(alias='PublishingChatGPT_PBI_PASSWORD')
    PBI_PASSWORD: str = Field(alias='PublishingChatGPT_PBI_PASSWORD')

    
    
class Settings(ApplicationSettings):
    PROJECT_NAME: str = 'Publishing ChatGPT POC'
    # AzureAd_Redirect_Path: str = '/signin-oidc'
    # AzureAd_Authority: str

    # @property
    # def AzureAd_Authority(self) -> str:
    #     return 'https://login.microsoftonline.com/' + self.AzureAd_TenantId
    
    
    PBI_AUTHENTICATION_MODE: str = 'ServicePrincipal'
    PBI_AUTHORITY_URL: str = 'https://login.microsoftonline.com/organizations'
    PBI_SCOPE_BASE: str = 'https://analysis.windows.net/powerbi/api/.default'

    class Config:
        env_file = ".env"
        env_file_encoding = 'utf-8'
        case_sensitive = True

class PathConfig:
    PARENT_PATH = Path.cwd().parent
    if 'publishingchatgptpocweb' not in str(PARENT_PATH):
        PARENT_PATH = PARENT_PATH / 'publishingchatgptpocweb'
    
    PARENT_PATH_STR = str(PARENT_PATH)

    TEMPLATE_DIRECTORY = os.path.join(PARENT_PATH_STR, 'templates')
    DATA_DIRECTORY = os.path.join(PARENT_PATH_STR, 'data')
    MODEL_DIRECTORY = os.path.join(PARENT_PATH_STR, 'models')
    SCRIPT_DIRECTORY = os.path.join(PARENT_PATH_STR, 'scripts')

    RAW_DATA_DIRECTORY = os.path.join(DATA_DIRECTORY, 'raw')
    PROCESSED_DATA_DIRECTORY = os.path.join(DATA_DIRECTORY, 'processed')
    AUDIO_DATA_DIRECTORY =  os.path.join(DATA_DIRECTORY, 'audio')
    
    CHROMA_DB = os.path.join(MODEL_DIRECTORY, 'langchain_chroma_db_pub')
    AUDIO_FILE_PATH = os.path.join(AUDIO_DATA_DIRECTORY, 'blob.wav')
    EVA_TEMPLATE_ANSWER_FILE_PATH = os.path.join(TEMPLATE_DIRECTORY, 'eva-template-answer.txt')
    EVA_TEMPLATE_REFERNCE_FILE_PATH = os.path.join(TEMPLATE_DIRECTORY, 'eva-template-reference.txt')

    @classmethod
    def init_app(cls, app):
        app.template_folder = cls.TEMPLATE_DIRECTORY
        app.data_folder = cls.DATA_DIRECTORY


settings = Settings()