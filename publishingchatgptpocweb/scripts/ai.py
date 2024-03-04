# All AI related functions
import openai
import re

from langchain_openai import OpenAIEmbeddings
from langchain_openai import ChatOpenAI
from langchain.prompts import PromptTemplate
from langchain_community.vectorstores import Neo4jVector
from langchain.chains import RetrievalQAWithSourcesChain
from scripts.handlers import LLMCallbackHandler
from scripts.db import Neo4jHelper

import spacy

class AI:

    def __init__(self, settings, pathconfig, file_instance):
        self.settings = settings
        self.pathconfig = pathconfig
        self.file_instance = file_instance

        openai.api_key = settings.Open_AI_API_Secret     
        self.model = settings.Open_AI_Model        
        self.max_tokens_response = settings.Open_AI_Max_Token
        self.temperature = 0.3 
        self.frequency_penalty = 0
        self.presence_penalty = 0

        self.data_instance = self.init_data_instance()
        self.dbhelper = Neo4jHelper(self.settings)
        
        self.refresh_retieval_qa()    

        ## Run once only when new concepts are added to database #####
        # self.save_concepts_and_sources_ner_model()
        ##############################################################
        self.nlp = self.load_concepts_and_sources_ner_model()


    def init_data_instance(self):
        embeddings = OpenAIEmbeddings(openai_api_key=self.settings.Open_AI_API_Secret, model=self.settings.Open_AI_Embedding_Model, dimensions=int(self.settings.Open_AI_Embedding_Dimensions))
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
        eva_answer_template = self.file_instance.read_template_files()
        input_variables=["summaries", "question"]
        
        prompt_template_answer = PromptTemplate(
            template=eva_answer_template, 
            input_variables=input_variables)  
        
        return prompt_template_answer            

    def init_retieval_qa(self):
        param_llm = {
            'model_name': self.model,
            'temperature': self.temperature,
            'max_tokens': self.max_tokens_response,
            'openai_api_key': self.settings.Open_AI_API_Secret,
            'streaming': True
        }

        params_model={
            "presence_penalty": self.presence_penalty,
            "frequency_penalty": self.frequency_penalty
        }

        param_llm = dict(param_llm)
        llm_eva = ChatOpenAI(**param_llm, model_kwargs=params_model)

        prompt_template_answer = self.get_prompt_templates()    
        
        retrieval_qa_answer = RetrievalQAWithSourcesChain.from_chain_type(
            llm=llm_eva,
            chain_type="stuff",
            retriever=self.data_instance.as_retriever(search_kwargs={"k": 10}),
            chain_type_kwargs={
                "verbose": False,
                "prompt": prompt_template_answer
            }
        )

        return retrieval_qa_answer
    

    def refresh_retieval_qa(self):
        self.retieval_qa_answer = self.init_retieval_qa() 

    def get_callback_instance(self, sessionId):
        return LLMCallbackHandler(sessionId=sessionId)

    def process_query_answer(self, callback_instance, prompt, temperature, frequency_penalty, presence_penalty):
        self.temperature = float(temperature) if temperature else 0.3
        self.frequency_penalty = float(frequency_penalty) if frequency_penalty else 0
        self.presence_penalty = float(presence_penalty) if presence_penalty else 0

        self.refresh_retieval_qa()

        print(f"process_query_answer called: sessionId: {callback_instance.sessionId}, prompt: {prompt}")
        self.retieval_qa_answer({"question": prompt}, return_only_outputs=True, callbacks = [callback_instance])
    
    def load_spacy_model(self, model_name="en_core_web_sm"):
        try:
            return spacy.load(model_name)
        except OSError:
            from spacy.cli import download
            download(model_name)
            return spacy.load(model_name)

    def save_concepts_and_sources_ner_model(self):
        nlp = self.load_spacy_model("en_core_web_sm")
        if "entity_ruler" not in nlp.pipe_names:
            entity_ruler = nlp.add_pipe("entity_ruler")
        else:
            entity_ruler = nlp.get_pipe("entity_ruler")
        
        concepts_sources = self.dbhelper.fetch_concepts_and_sources()
        patterns = [{"label": "CONCEPT", "pattern": concept, "id": source} 
                for concept, source in concepts_sources.items()]
        entity_ruler.add_patterns(patterns)

        nlp.to_disk(self.pathconfig.CONCEPT_TRAINED_NER_PATH)

    def load_concepts_and_sources_ner_model(self):
        try:
            nlp = spacy.load(self.pathconfig.CONCEPT_TRAINED_NER_PATH, enable=["entity_ruler"])
        except Exception:
            self.save_concepts_and_sources_ner_model()
            nlp = spacy.load(self.pathconfig.CONCEPT_TRAINED_NER_PATH)

        return nlp

    def fetch_concepts(self, text):
        # print(text)
        # start_time = time.time()

        doc = self.nlp(text)
        concepts_sources = {}
        for ent in doc.ents:
            if ent.label_ == "CONCEPT":
                concepts_sources[ent.text] = ent.ent_id_

        # end_time = time.time()
        # time_taken = end_time - start_time
        # print(f"Time taken to fetch concepts: {time_taken} seconds")
        # print()
        return concepts_sources

    def fetch_sources(self, pans):
        
        sources = []

        try:
            sources = self.dbhelper.fetch_sources_for_pans(pans)

            # Updated patterns for improved flexibility
            title_pattern = re.compile(r'Title:\s*(.+?)(?=\n|$)', re.DOTALL)
            publisher_name_pattern = re.compile(r'Publisher Name:\s*(.+?)(?=\n|$)')
            publisher_location_pattern = re.compile(r'Publisher Location:\n\s*City: (.+?)\n\s+Country: (.+?)(?=\n|$)')
            publishing_date_pattern = re.compile(r'Publishing Date: (.+?)(?=\n|$)')
            abstract_summary_pattern = re.compile(r'Abstract Summary:\s*(.+)', re.DOTALL)
            
            categories_pattern = re.compile(r"Subjects or Categories:\n\s*(.*?)(?=Publisher Name:)", re.DOTALL)
            authors_pattern = re.compile(r"Authors:\n\s*(.*?)(?=Abstract Summary:)", re.DOTALL)

            for source in sources:
                info = source['info']
                info = source['info'].encode('latin1').decode('utf-8')
                
                source.pop('info', None)

                source['PAN'] = source['source']
                source['Title'] = title_match.group(1).strip() if (title_match := title_pattern.search(info)) else None
                source['Publisher Name'] = publisher_name_match.group(1).strip() if (publisher_name_match := publisher_name_pattern.search(info)) else None
                publisher_location_match = publisher_location_pattern.search(info)
                if publisher_location_match:
                    source['Publisher Location'] = f"{publisher_location_match.group(1).strip()}, {publisher_location_match.group(2).strip()}"
                source['Publishing Date'] = publishing_date_match.group(1).strip() if (publishing_date_match := publishing_date_pattern.search(info)) else None
                source['Abstract Summary'] = abstract_summary_match.group(1).strip() if (abstract_summary_match := abstract_summary_pattern.search(info)) else None

                categories_match = categories_pattern.search(info)
                if categories_match:
                    categories_text = categories_match.group(1).strip()
                    source['Categories'] = [line.strip() for line in categories_text.split("\n") if line.strip()]

                authors_match = authors_pattern.search(info)
                if authors_match:
                    authors_text = authors_match.group(1).strip()
                    source['Authors'] = [line.strip() for line in authors_text.split("\n") if line.strip()]

        except Exception as e:
            pass
        
        return sources
    