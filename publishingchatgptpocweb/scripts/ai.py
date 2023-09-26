# All AI related functions
import openai

from langchain.embeddings.openai import OpenAIEmbeddings
from langchain.chat_models import ChatOpenAI
from langchain.prompts import PromptTemplate
from langchain.vectorstores import Neo4jVector
from langchain.chains import RetrievalQAWithSourcesChain
from langchain.callbacks.base import BaseCallbackHandler
from langchain.schema import HumanMessage

class AI:

    def __init__(self, settings, pathconfig, socketio):
        self.settings = settings
        self.pathconfig = pathconfig

        # Set up the OpenAI API client
        openai.api_key = settings.Open_AI_API_Secret     
        self.model = settings.Open_AI_Model
        self.temperature = 0
        self.max_tokens_response=500
        
        self.data_instance = self.init_data_instance()
        self.custom_callback_handler_normal = NormalCallbackHandler(socketio)
        self.custom_callback_handler_answer = AnswerCallbackHandler(socketio)
        self.custom_callback_handler_reference = ReferenceCallbackHandler(socketio)
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
        with open(self.pathconfig.EVA_TEMPLATE_ANSWER_FILE_PATH, "r") as file:
            eva_answer_template = file.read()

        with open(self.pathconfig.EVA_TEMPLATE_REFERNCE_FILE_PATH, "r") as file:
            eva_reference_template = file.read()
        
        input_variables=["summaries", "question"]
       
        prompt_template_answer = PromptTemplate(
            template=eva_answer_template, 
            input_variables=input_variables)  

        prompt_template_reference = PromptTemplate(
            template=eva_reference_template, 
            input_variables=input_variables) 
              
        return prompt_template_answer, prompt_template_reference            

    def init_retieval_qa(self):

        llm_answer = ChatOpenAI(
            model_name=self.model,
            streaming=True,
            callbacks=[self.custom_callback_handler_answer],
            temperature=self.temperature,
            max_tokens=self.max_tokens_response,
            openai_api_key=self.settings.Open_AI_API_Secret,
        )

        llm_reference = ChatOpenAI(
            model_name=self.model,
            streaming=True,
            callbacks=[self.custom_callback_handler_reference],
            temperature=self.temperature,
            max_tokens=self.max_tokens_response,
            openai_api_key=self.settings.Open_AI_API_Secret,
        )

        prompt_template_answer, prompt_template_reference = self.get_prompt_templates()    


        retieval_qa_normal = ChatOpenAI(model=self.model,
                          openai_api_key=self.settings.Open_AI_API_Secret,
                          max_tokens=self.max_tokens_response,
                          streaming=True, 
                          temperature=self.temperature,
                          callbacks=[self.custom_callback_handler_normal])

        retieval_qa_answer = RetrievalQAWithSourcesChain.from_chain_type(
            llm=llm_answer,
            chain_type="stuff",
            retriever=self.data_instance.as_retriever(),
            chain_type_kwargs={
                "verbose": False,
                "prompt": prompt_template_answer
            }
        )

        retieval_qa_reference = RetrievalQAWithSourcesChain.from_chain_type(
            llm=llm_reference,
            chain_type="stuff",
            retriever=self.data_instance.as_retriever(),
            chain_type_kwargs={
                "verbose": False,
                "prompt": prompt_template_reference
            }
        )        

        return retieval_qa_normal, retieval_qa_answer, retieval_qa_reference

    def process_query(self, prompt, type):
        if type=="gptnormal":
            self.retieval_qa_normal([HumanMessage(content=prompt)])
            # for output_string in self.custom_callback_handler_normal.outputs:
            #     yield output_string

        if type=='answer':
            self.retieval_qa_answer({"question": prompt}, return_only_outputs=True)
            # for output_string in self.custom_callback_handler_answer.outputs:
            #     yield output_string
        elif type=='reference':
            self.retieval_qa_reference({"question": prompt}, return_only_outputs=True)
            # for output_string in self.custom_callback_handler_reference.outputs:
            #     yield output_string      

class NormalCallbackHandler(BaseCallbackHandler):
    def __init__(self, socketio):
        self.socketio = socketio

    def on_llm_new_token(self, token: str, **kwargs) -> None:
        self.socketio.emit('gptnormal_response', token)

class AnswerCallbackHandler(BaseCallbackHandler):
    def __init__(self, socketio):
        self.socketio = socketio

    def on_llm_new_token(self, token: str, **kwargs) -> None:
        self.socketio.emit('answer_response', token)    

class ReferenceCallbackHandler(BaseCallbackHandler):
    def __init__(self, socketio):
        self.socketio = socketio

    def on_llm_new_token(self, token: str, **kwargs) -> None:
        self.socketio.emit('reference_response', token)