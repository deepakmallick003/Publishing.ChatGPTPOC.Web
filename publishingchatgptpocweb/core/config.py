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
    FLASK_SECRET_KEY: str = os.urandom(24).hex()
    FLASK_SESSION_TYPE : str = 'filesystem'

    Open_AI_API_Secret: str = Field(alias='PublishingChatGPT_Open_AI_API_Secret')
    Open_AI_Model: str = Field(alias='PublishingChatGPT_Open_AI_Model')
    Open_AI_Embedding_Model: str = Field(alias='PublishingChatGPT_Open_AI_Embedding_Model')
    Open_AI_Embedding_Dimensions: str = Field(alias='PublishingChatGPT_Open_AI_Embedding_Dimensions')
    Open_AI_Max_Token: str = Field(alias='PublishingChatGPT_Open_AI_Max_Token')

    AzureAd_TenantId: str = Field(alias='PublishingChatGPT_AzureAd_TenantId')
    AzureAd_ClientId: str = Field(alias='PublishingChatGPT_AzureAd_ClientId')
    AzureAd_ClientSecret: str = Field(alias='PublishingChatGPT_AzureAd_ClientSecret')

    Neo4J_URL: str = Field(alias='PublishingChatGPT_Neo4J_URL')
    Neo4J_UserName: str = Field(alias='PublishingChatGPT_Neo4J_UserName')
    Neo4J_Database: str = Field(alias='PublishingChatGPT_Neo4J_Database')
    Neo4J_Password: str = Field(alias='PublishingChatGPT_Neo4J_Password')
    Neo4J_PrimaryIndexName: str = Field(alias='PublishingChatGPT_Neo4J_PrimaryIndexName')
    
class Settings(ApplicationSettings):
    PROJECT_NAME: str = 'Publishing ChatGPT POC'

    AzureAd_Redirect_Path: str = '/signin-oidc'
    AzureAd_Authority: str = 'https://login.microsoftonline.com/'

    ARTICLES_BASE_URL: str  = 'https://www.cabidigitallibrary.org/doi/'
    CABT_PP_BASE_URL: str  = 'https://id.cabi.org/PoolParty/sparql/cabt'

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
    STATIC_DIRECTORY = os.path.join(PARENT_PATH_STR, 'static')
    DATA_DIRECTORY = os.path.join(PARENT_PATH_STR, 'data')
    MODEL_DIRECTORY = os.path.join(PARENT_PATH_STR, 'models')
    SCRIPT_DIRECTORY = os.path.join(PARENT_PATH_STR, 'scripts')
    EVA_TEMPLATES_DIRECTORY = os.path.join(STATIC_DIRECTORY, 'eva-templates')

    RAW_DATA_DIRECTORY = os.path.join(DATA_DIRECTORY, 'raw')
    INTERIM_DATA_DIRECTORY = os.path.join(DATA_DIRECTORY, 'interim')
    PROCESSED_DATA_DIRECTORY = os.path.join(DATA_DIRECTORY, 'processed')
    ERRORS_DIRECTORY_PATH = os.path.join(DATA_DIRECTORY, 'errors')

    ARTICLES_DATA_DIRECTORY_PATH = os.path.join(PROCESSED_DATA_DIRECTORY, 'articles')
    CONCEPTS_DATA_DIRECTORY_PATH = os.path.join(PROCESSED_DATA_DIRECTORY, 'concepts')

    AUDIO_DATA_DIRECTORY =  os.path.join(DATA_DIRECTORY, 'audio')
    
    CHROMA_DB = os.path.join(MODEL_DIRECTORY, 'langchain_chroma_db_pub')
    CONCEPT_TRAINED_NER_PATH = os.path.join(MODEL_DIRECTORY, 'trained_ner')
    AUDIO_FILE_PATH = os.path.join(AUDIO_DATA_DIRECTORY, 'blob.wav')
    
    SPAQRQL_QUERY_FILE_PATH = os.path.join(STATIC_DIRECTORY, 'sparql', 'sparql_query_template.sparql')
    ARTICLES_ERRORS_FILE_PATH = os.path.join(ERRORS_DIRECTORY_PATH, 'articles_errors.txt')
    CONCEPTS_ERRORS_FILE_PATH = os.path.join(ERRORS_DIRECTORY_PATH, 'concepts_errors.txt')
    ARTICLES_ERRORS_NEO4J_FILE_PATH = os.path.join(ERRORS_DIRECTORY_PATH, 'articles_errors_neo4j.txt')
    CONCEPTS_ERRORS_NEO4J_FILE_PATH = os.path.join(ERRORS_DIRECTORY_PATH, 'concepts_errors_neo4j.txt')
    CONCEPTS_TO_PROCESS_FILE_PATH = os.path.join(INTERIM_DATA_DIRECTORY, 'concepts_to_process.txt')

    EVA_TEMPLATE_ANSWER_FILE_PATH = os.path.join(EVA_TEMPLATES_DIRECTORY, 'eva-template-answer.txt')
    EVA_SETTINGS_FILE_PATH = os.path.join(EVA_TEMPLATES_DIRECTORY, 'eva-settings.xml')

    @classmethod
    def init_app(cls, app):
        app.template_folder = cls.TEMPLATE_DIRECTORY
        app.data_folder = cls.DATA_DIRECTORY


settings = Settings()