# All AI related functions
import openai

from langchain.embeddings.openai import OpenAIEmbeddings
from langchain.chat_models import ChatOpenAI
from langchain.prompts import PromptTemplate
from langchain.vectorstores import Neo4jVector
from langchain.chains import RetrievalQAWithSourcesChain
from langchain.schema import HumanMessage
from scripts.handlers import LLMCallbackHandler

class AI:

    def __init__(self, settings, pathconfig, file_instance, socketio=None):
        self.settings = settings
        self.pathconfig = pathconfig
        self.socketio = socketio
        self.file_instance = file_instance

        # Set up the OpenAI API client
        openai.api_key = settings.Open_AI_API_Secret     
        self.model = settings.Open_AI_Model        
        
        self.data_instance = self.init_data_instance()
        self.custom_callback_handler_normal = LLMCallbackHandler('gptnormal', self.socketio)
        self.custom_callback_handler_answer = LLMCallbackHandler('answer', self.socketio)
        self.custom_callback_handler_reference = LLMCallbackHandler('reference', self.socketio)

        self.refresh_settings_and_templates()

    def refresh_settings_and_templates(self):
        self.max_tokens_response, self.temperature= self.file_instance.read_eva_settings()
        self.retieval_qa_normal, self.retieval_qa_answer, self.retieval_qa_reference = self.init_retieval_qa()    

    def init_data_instance(self):
        embeddings = OpenAIEmbeddings(openai_api_key=self.settings.Open_AI_API_Secret, model='text-embedding-ada-002')
        instance=None
        instance = Neo4jVector.from_existing_index(
                embeddings,
                url=self.settings.Neo4J_URL, 
                username=self.settings.Neo4J_UserName,
                password=self.settings.Neo4J_Password,
                database=self.settings.Neo4J_Database,
                index_name=self.settings.Neo4J_PrimaryIndexName,
                text_node_property="info", 
            )
        return instance
    
    def get_prompt_templates(self):
        eva_answer_template, eva_reference_template = self.file_instance.read_template_files()

        input_variables=["summaries", "question"]
       
        prompt_template_answer = PromptTemplate(
            template=eva_answer_template, 
            input_variables=input_variables)  

        prompt_template_reference = PromptTemplate(
            template=eva_reference_template, 
            input_variables=input_variables) 
              
        return prompt_template_answer, prompt_template_reference            

    def init_retieval_qa(self):
        param_llm = {
            'model_name': self.model,
            'temperature': self.temperature,
            'max_tokens': self.max_tokens_response,
            'openai_api_key': self.settings.Open_AI_API_Secret,
            'streaming': True,
        }

        param_llm_answer = dict(param_llm)
        param_llm_reference = dict(param_llm)
        param_llm_normal= dict(param_llm)
        
        param_llm_answer.update({                
            'callbacks': [self.custom_callback_handler_answer]
        })
        param_llm_reference.update({
            'callbacks': [self.custom_callback_handler_reference] 
        })
        param_llm_normal.update({
            'callbacks': [self.custom_callback_handler_normal] 
        })

        llm_answer = ChatOpenAI(**param_llm_answer)
        llm_reference = ChatOpenAI(**param_llm_reference)
        llm_normal= ChatOpenAI(**param_llm_normal)

        prompt_template_answer, prompt_template_reference = self.get_prompt_templates()    
        
        retrieval_qa_answer = RetrievalQAWithSourcesChain.from_chain_type(
            llm=llm_answer,
            chain_type="stuff",
            retriever=self.data_instance.as_retriever(),
            chain_type_kwargs={
                "verbose": False,
                "prompt": prompt_template_answer
            }
        )

        retrieval_qa_reference = RetrievalQAWithSourcesChain.from_chain_type(
            llm=llm_reference,
            chain_type="stuff",
            retriever=self.data_instance.as_retriever(),
            chain_type_kwargs={
                "verbose": False,
                "prompt": prompt_template_reference
            }
        )           

        return llm_normal, retrieval_qa_answer, retrieval_qa_reference

    def process_query(self, type, prompt):
        print(f"process_query called with type: {type}, prompt: {prompt}")

        if type=="gptnormal":
            self.retieval_qa_normal([HumanMessage(content=prompt)])

        if type=='answer':
            self.retieval_qa_answer({"question": prompt}, return_only_outputs=True)
          
        if type=='reference':
            self.retieval_qa_reference({"question": prompt}, return_only_outputs=True)
                