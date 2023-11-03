# All AI related functions
import openai
import re

from langchain.embeddings.openai import OpenAIEmbeddings
from langchain.chat_models import ChatOpenAI
from langchain.prompts import PromptTemplate
from langchain.vectorstores import Neo4jVector
from langchain.chains import RetrievalQAWithSourcesChain
from langchain.schema import HumanMessage
from scripts.handlers import LLMCallbackHandler
from scripts.db import Neo4jHelper

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

        self.dbhelper = Neo4jHelper(self.settings)


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
        param_llm_normal= {
            'model_name': 'gpt-3.5-turbo',
            'temperature': self.temperature,
            'max_tokens': self.max_tokens_response,
            'openai_api_key': self.settings.Open_AI_API_Secret,
            'streaming': True,
        }
        
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

    # def validate_and_fix_response_urls(self, text):
        # Extract all hyperlinks from texts, then seperate pan from article type anchors e.g
        # <a href="https://www.cabidigitallibrary.org/doi/10.5555/20183000178">The ebola epidemic in West Africa: proceedings of a workshop.</a>
        # Extract pan number 20183000178 which would be usefult to find correct node and source
        # from a concept type anchor like <a href="https://id.cabi.org/cabt/301097">Ebola haemorrhagic fever</a>
        # exrtact "Ebola haemorrhagic fever" which is title of the node and would be useful to find correct node.

        # After extracting all article and concept types values, loop through them to validate one by one.
        # For an article type check if the article is present by pan, if yes then see if the source value match with this. If node deosn't exists remove hyperlink and simply keep the text.
        # For a concept type check if the concept is present is present by name, if yes then see if the source value match with this. If node deosn't exists remove hyperlink and simply keep the text.

        # After this do one more thing. From the text get different trigram cobinations, sequential ones only no reverse or random mix match.
        # FOr each of those combinations get all concepts which exists in the database and their source.
        # If a concept exists for a concept replace it with a hyperlink using it's source from the node.


    def split_text_on_ngrams(self, text, ngrams):
        segments = []
        i = 0
        while i < len(text):
            found = False
            for ngram in ngrams:
                if text[i:].startswith(ngram):
                    segments.append(ngram)
                    i += len(ngram)
                    found = True
                    break
            if not found:
                segments.append(text[i])
                i += 1
        return segments

    def validate_and_fix_response_urls(self, text, send_report_data=False):
        if isinstance(send_report_data, str):
            send_report_data = send_report_data.lower() == 'true'

        collection = {
            'articles': [],
            'concepts': []
        }
        
        article_links = re.findall(r'<a href="(https://www\.cabidigitallibrary\.org/doi/[^/]+/([^/"]+))">([^<]+)</a>', text)
        concept_links = re.findall(r'<a href="(https://id\.cabi\.org/cabt/[^"]+)">([^<]+)</a>', text)

        # Validate and fix article links
        for link, pan, title in article_links:
            if not self.dbhelper.article_exists_by_pan_and_source(pan, link):
                text = text.replace(f'<a href="{link}">', '').replace('</a>', '')
            else:
                if send_report_data==True:
                    collection['articles'].append({
                        'title': title,
                        'pan': pan,
                        'source': link,
                        'document_type': 'article'
                    })

        # Validate and fix concept links
        for link, name in concept_links:
            if not self.dbhelper.concept_exists_by_name_and_source(name, link):
                text = text.replace(f'<a href="{link}">', '').replace('</a>', '')
            else:
                if send_report_data==True:
                    collection['concepts'].append({
                        'title': title,
                        'source': link,
                        'document_type': 'concept'
                    })

        # Enrich text with trigram-based concept links        
        stop_words = set([
            "i", "me", "my", "myself", "we", "our", "ours", "ourselves", "you", "your", "yours", "yourself", "yourselves",
            "he", "him", "his", "himself", "she", "her", "hers", "herself", "it", "its", "itself", "they", "them", "their",
            "theirs", "themselves", "what", "which", "who", "whom", "this", "that", "these", "those", "am", "is", "are", "was",
            "were", "be", "been", "being", "have", "has", "had", "having", "do", "does", "did", "doing", "a", "an", "the", "and",
            "but", "if", "or", "because", "as", "until", "while", "of", "at", "by", "for", "with", "about", "against", "between",
            "into", "through", "during", "before", "after", "above", "below", "to", "from", "up", "down", "in", "out", "on", "off",
            "over", "under", "again", "further", "then", "once", "also", "given"
        ])    

        # Extract and temporarily store the source and related articles part
        source_articles_match = re.search(r'(<h4>Source Articles</h4>.*)', text, flags=re.DOTALL)
        if source_articles_match:
            source_articles = source_articles_match.group(1)
            placeholder = "##SOURCE_ARTICLES_PLACEHOLDER##"
            text = text.replace(source_articles, placeholder)
        else:
            source_articles = ""

        # Use regex tokenizer to split the text into words, excluding punctuation.
        tokenizer = re.compile(r'\w+')
        words = [word for word in tokenizer.findall(text) if word.lower() not in stop_words]

        # Extracting potential ngrams
        # Step 1: Collect all ngrams
        all_ngrams = set()
        for n in range(1, 4):  # 1 for unigram, 2 for bigram, 3 for trigram
            for i in range(len(words) - n + 1):
                ngram = ' '.join(words[i:i+n])
                if len(ngram) >= 2:
                    all_ngrams.add(ngram)

        # Step 2: Fetch sources for all ngrams at once
        ngram_sources = self.dbhelper.fetch_sources_for_ngrams(all_ngrams)

        # Sorting ngrams by length (descending)
        sorted_ngrams = sorted(ngram_sources.keys(), key=len, reverse=True)

        segments = self.split_text_on_ngrams(text, sorted_ngrams)

        # Replacing ngrams in the segments
        modified_segments = []
        for segment in segments:
            if segment in ngram_sources:
                modified_segments.append(f'<a href="{ngram_sources[segment]}">{segment}</a>')
                if send_report_data==True:
                    collection['concepts'].append({
                        'title': segment,
                        'source': ngram_sources[segment],
                        'document_type': 'concept'
                    })
            else:
                modified_segments.append(segment)

        # Reassembling the segments to get the modified text
        text = ''.join(modified_segments)

        # Restore the source articles portion
        if source_articles:
            text = text.replace(placeholder, source_articles)

        nodes_and_relations=None
        if send_report_data==True:
            nodes_and_relations = self.dbhelper.fetch_related_nodes_and_relations(collection)

        return text, nodes_and_relations   