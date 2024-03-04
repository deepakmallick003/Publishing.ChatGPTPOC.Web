import os
import threading
import openai
import re

from langchain_community.document_loaders import TextLoader
from neo4j import GraphDatabase
from langchain_community.vectorstores import Neo4jVector
from langchain_openai import OpenAIEmbeddings

class ScaleDB:

    def __init__(self, settings, pathconfig):
        self.settings = settings
        self.pathconfig = pathconfig  

        openai.api_key = settings.Open_AI_API_Secret
        self.driver = GraphDatabase.driver(self.settings.Neo4J_URL, auth=(self.settings.Neo4J_UserName, self.settings.Neo4J_Password), database=self.settings.Neo4J_Database)
        # self.embeddings = OpenAIEmbeddings(openai_api_key=self.settings.Open_AI_API_Secret, model=self.settings.Open_AI_Embedding_Model, dimensions=self.settings.Open_AI_Embedding_Dimensions)
        # self.neo4j_vector_index = self.get_neo4j_vector_index()
        self.documents_uploaded = 0
        self.total_document_to_upload=0

    def existing_vector_index(self):
        try:
            existing_index = Neo4jVector.from_existing_index(
                self.embeddings,
                url=self.settings.Neo4J_URL, 
                username=self.settings.Neo4J_UserName,
                password=self.settings.Neo4J_Password,
                database=self.settings.Neo4J_Database,
                index_name=self.settings.Neo4J_PrimaryIndexName,
                text_node_property="info", 
            )
            return existing_index
        except Exception as e:
            return None
        
    def get_neo4j_vector_index(self):
        neo4j_vector_index = self.existing_vector_index()
        if neo4j_vector_index is None:
            loader = TextLoader(os.path.join(self.pathconfig.RAW_DATA_DIRECTORY, 'test.txt'))
            documents = loader.load()
            documents[0].metadata["source"]=''
            Neo4jVector.from_documents(
                documents,
                self.embeddings,
                url=self.settings.Neo4J_URL, 
                username=self.settings.Neo4J_UserName,
                password=self.settings.Neo4J_Password,
                database=self.settings.Neo4J_Database,
                index_name=self.settings.Neo4J_PrimaryIndexName,
                node_label="PublishingDataChunk",  # Chunk by default
                text_node_property="info",  # text by default
                embedding_node_property="vector",  # embedding by default
                create_id_index=True,  # True by default
                pre_delete_collection=True # False by default
            )
            
            neo4j_vector_index = self.existing_vector_index()

        return neo4j_vector_index

    def get_text_files_to_upload(self, type):
        text_files_to_upload = set()
        source_directory = os.path.join(self.pathconfig.PROCESSED_DATA_DIRECTORY, type)
        uploaded_file_names = self.get_already_uploaded_file_names(type[:-1])

        for root_dir, sub_dirs, files in os.walk(source_directory):
            print(f"Total {type} files found in source directory: {len(files)}")
            print(f"Getting pending {type} files to Upload to Vector DB..")
            for file_name in files:
                if file_name.endswith('.txt'):
                    # Check if this file is not already uploaded to vector db
                    if file_name not in uploaded_file_names:
                        text_files_to_upload.add(file_name)

        return list(text_files_to_upload)

    def get_already_uploaded_file_names(self, document_type):
        filenames= set()

        with self.driver.session(database=self.settings.Neo4J_Database) as session:
            unique_property = 'source' if document_type == 'article' else 'title'
            query_result = session.run(f"""
            MATCH (n) WHERE n.type='{document_type}'
            RETURN REPLACE(n.{unique_property}, ' ', '_') + '.txt' AS uploaded_files
            """, database=self.settings.Neo4J_Database).data()

            filenames = {record['uploaded_files'] for record in query_result}

        return filenames
    
    def get_total_concept_nodes(self):
        with self.driver.session(database=self.settings.Neo4J_Database) as session:
            query = """
            MATCH (n) WHERE n.type='concept'
            RETURN count(n) AS totalConcepts
            """
            result = session.run(query).single()
            total_concepts = result["totalConcepts"] if result else 0
            return total_concepts

    def delete_unreferenced_concept_nodes(self, referenced_concepts):
        with self.driver.session(database=self.settings.Neo4J_Database) as session:
            referenced_concepts_lower = [concept.lower() for concept in referenced_concepts]
            query = """
            CALL apoc.periodic.iterate(
                "MATCH (concept) WHERE concept.type = 'concept' RETURN concept",
                "WITH concept WHERE NOT TOLOWER(concept.title) IN $referencedConcepts DELETE concept",
                {batchSize:100, parallel:false}
            )
            """

            session.run(query, referencedConcepts=referenced_concepts_lower)
            print("Unreferenced concept nodes deleted.")

    def check_article_node_exists(self, source):
        with self.driver.session(database=self.settings.Neo4J_Database) as session:
            query = f"""
            MATCH (n) WHERE n.type = 'article' AND n.source = '{source}'
            RETURN COUNT(n) > 0 AS node_exists
            """
            result = session.run(query, database=self.settings.Neo4J_Database).single()

            if result is not None:
                return result['node_exists']
            else:
                return False
            
    def check_concept_node_exists(self, title):
        with self.driver.session(database=self.settings.Neo4J_Database) as session:
            query = f"""
            MATCH (n) WHERE n.type = 'concept' AND TOLOWER(n.title) = TOLOWER('{title}')
            RETURN COUNT(n) > 0 AS node_exists
            """
            result = session.run(query, database=self.settings.Neo4J_Database).single()

            if result is not None:
                return result['node_exists']
            else:
                return False

    def create_vector_data_from_processed_documents(self, type='articles', n_threads=6):
        documents_set = self.get_text_files_to_upload(type)
        documents_set = list(documents_set)
        self.total_document_to_upload = len(documents_set)
        self.documents_uploaded = 0
        print(f"\nTotal Unique Documents of Type {type}, which are not already processed: {self.total_document_to_upload}")

        ## Test purpose, comment otherwise
        # self.worker_function(type, documents_set)

        ## Divide files among threads
        files_per_thread = self.total_document_to_upload // n_threads + (self.total_document_to_upload % n_threads > 0)

        if files_per_thread>0:
            threads = []
            for i in range(0, self.total_document_to_upload, files_per_thread):
                thread_files = documents_set[i:i+files_per_thread]
                thread = threading.Thread(target=self.worker_function, args=(type, thread_files))
                threads.append(thread)
                thread.start()

            for thread in threads:
                thread.join()

        print(f"\nDocument Upload for type {type} complete.")
    
    def worker_function(self, type, files):
        if type=="articles":
            for file in files:
                self.add_articles_documents_to_vector_db_thread(file)
        else:
            for file in files:
                self.add_concept_documents_to_vector_db_thread(file)

    def add_articles_documents_to_vector_db_thread(self, file_name):
        article_pan = file_name.replace('.txt', '')
        data_directory = os.path.join(self.pathconfig.PROCESSED_DATA_DIRECTORY, 'articles')

        try:
            if not self.check_article_node_exists(article_pan):
                text_file_path = os.path.join(data_directory, file_name)
                loader = TextLoader(text_file_path, encoding='utf8')
                documents = loader.load()
                # concepts = self.extract_concepts_from_article_content(documents[0].page_content)
                documents[0].page_content = self.shrink_article_doc_content(documents[0].page_content, [])
                documents[0] = self.update_article_metadata(documents[0])
                
                ##### Add Article doc to Vector DB #####
                self.neo4j_vector_index.add_documents(documents)
                self.documents_uploaded += 1
                # if len(concepts) > 0:
                #     self.add_concept_documents_to_vector_db(concepts)
        except Exception as e:
            self.write_to_error_file('articles', article_pan)

        documents_left_to_upload = self.total_document_to_upload - self.documents_uploaded
        print(f"\rUploaded {self.documents_uploaded}/{self.total_document_to_upload} Documents. {documents_left_to_upload} files left to upload.", end='')     

    def add_concept_documents_to_vector_db_thread(self, file_name):
        concept_name = file_name.replace('.txt', '').replace('_', ' ')
        data_directory = os.path.join(self.pathconfig.PROCESSED_DATA_DIRECTORY, 'concepts')
        
        try:
            if not self.check_concept_node_exists(concept_name):
                text_file_path = os.path.join(data_directory, file_name)
                loader = TextLoader(text_file_path, encoding='utf8')
                documents = loader.load()
                documents[0].page_content = self.shrink_concept_doc_content(documents[0].page_content, [])
                documents[0] = self.update_concepts_metadata(documents[0])

                ##### Add Concept doc to Vector DB #####
                self.neo4j_vector_index.add_documents(documents)
                self.documents_uploaded += 1
        except Exception as e:
            self.write_to_error_file('concepts', concept_name)

        documents_left_to_upload = self.total_document_to_upload - self.documents_uploaded
        print(f"\rUploaded {self.documents_uploaded}/{self.total_document_to_upload} Documents. {documents_left_to_upload} files left to upload.", end='')     

    def shrink_article_doc_content(self, original_text, formatted_text=[]):
        indent_level = 0
        indent_unit = 4

        def write_line(content, indent_level=0):
            formatted_text.append(' ' * (indent_level * indent_unit) + content + '\n')

        # Extract PAN, Title, Publisher Name, Location, Date, Authors, Abstract Summary
        pan_match = re.search(r'PAN:\s*(\S+)', original_text)
        title_match = re.search(r'Title:\s*(.*?)\n', original_text, re.DOTALL)
        publisher_name_match = re.search(r'Publisher Name:\n\s*(.*?)\n', original_text, re.DOTALL)
        city_match = re.search(r'City:\s*(.*?)\n', original_text)
        country_match = re.search(r'Country:\s*(.*?)\n', original_text)
        day_match = re.search(r'Day:\s*(\d+)', original_text)
        month_match = re.search(r'Month:\s*(\d+)', original_text)
        year_match = re.search(r'Year:\s*(\d+)', original_text)
        authors_matches = re.findall(r'Authors:\n\s*-\s*(.*?)\n', original_text, re.DOTALL)
        abstract_summary_match = re.search(r'Abstract Summary:\s*(.*?)\n\s*Keywords', original_text, re.DOTALL)

        # Writing the extracted information
        write_line('Article:', indent_level)
        if pan_match:
            write_line(f'PAN: {pan_match.group(1)}', indent_level + 1)
        if title_match:
            write_line(f'Title: {title_match.group(1)}', indent_level + 1)

        subjects_section_match = re.search(r'Subjects or Categories:\n(.*?)\n\s*(?:Title|Publisher Name):', original_text, re.DOTALL)
        if subjects_section_match:
            subjects_section = subjects_section_match.group(1)
            subjects_matches = re.findall(r'\s*-\s*(.+)', subjects_section)
            if subjects_matches:
                write_line('Subjects or Categories:', indent_level + 1)
                for subject in subjects_matches:
                    write_line(subject, indent_level + 2)

        if publisher_name_match:
            write_line('Publisher Name:', indent_level + 1)
            write_line(publisher_name_match.group(1).strip(), indent_level + 2)

        if city_match and country_match:
            write_line('Publisher Location:', indent_level + 1)
            write_line(f'City: {city_match.group(1)}', indent_level + 2)
            write_line(f'Country: {country_match.group(1)}', indent_level + 2)

        if day_match and month_match and year_match:
            months = ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"]
            month_name = months[int(month_match.group(1)) - 1]
            write_line(f'Publishing Date: {month_name} {day_match.group(1)}, {year_match.group(1)}', indent_level + 1)

        if authors_matches:
            write_line('Authors:', indent_level + 1)
            for author in authors_matches:
                write_line(author.strip(), indent_level + 2)

        if abstract_summary_match:
            write_line(f'Abstract Summary: {abstract_summary_match.group(1).strip()}', indent_level+1)

        return ''.join(formatted_text)

    def shrink_concept_doc_content(self, original_text, formatted_text=[]):
        indent_level = 0
        indent_unit = 4  

        def write_line(content, indent_level=0):
            formatted_text.append(' ' * (indent_level * indent_unit) + content + '\n')

        concept_section = re.search(r'Thesaurus Concept:\n\s*Concept:\n(.*?)\n(?:\s*Broader Concept:|\s*Narrower Concepts:|\s*Related Concepts:|\Z)', original_text, re.DOTALL)
        if concept_section:
            write_line('Concept:', indent_level)
            concept = concept_section.group(1)
            concept_name_match = re.search(r'name:\s*(.*?)(?:\n|$)', concept)
            concept_uri_match = re.search(r'uri:\s*(.*?)(?:\n|$)', concept)
            if concept_name_match:
                write_line(f'Name: {concept_name_match.group(1)}', indent_level+1)
            if concept_uri_match:
                match = re.search(r"(\d+)$", concept_uri_match.group(1))
                id = match.group() if match else None
                write_line(f'ID: {id}', indent_level+1)
        
        broader_concept_section = re.search(r'Broader Concept:\n\s*name: (.*?)\n\s*uri: (https?://\S+)', original_text, re.DOTALL)
        if broader_concept_section:
            write_line('Broader:', indent_level + 1)
            name, _ = broader_concept_section.groups()
            write_line(name, indent_level + 2)

        narrower_concepts_section = re.findall(r'Narrower Concepts:\n\s*Concept:\n\s*name: (.*?)\n\s*uri: (https?://\S+)', original_text, re.DOTALL)
        if narrower_concepts_section:
            write_line('Narrower:', indent_level + 1)
            for name, _ in narrower_concepts_section:
                write_line(name, indent_level + 2)

        related_concepts_section_match  = re.search(r'Related Concepts:(.*)', original_text, re.DOTALL)
        if related_concepts_section_match:
            write_line('Related:', indent_level + 1)
            related_concepts_section = related_concepts_section_match.group(1)
            related_concepts = re.findall(r'name: (.*?)\n\s*uri: (https?://\S+)', related_concepts_section, re.DOTALL)
            for name, _ in related_concepts:
                write_line(name, indent_level + 2)
        
        return ''.join(formatted_text)

    def update_article_metadata(self, document):
        # title_match = re.search(r'Title:\s*(.*?)(?:\n|$)', document.page_content)
        pan_match = re.search(r'PAN:\s*(.*?)(?:\n|$)', document.page_content)
        document.metadata['type'] = 'article'
        # if title_match:
            # document.metadata['title'] = title_match.group(1)
        if pan_match:
            document.metadata['source'] = pan_match.group(1)
            document.metadata['title'] = pan_match.group(1)
        return document

    def update_concepts_metadata(self, document):
        name_match = re.search(r'Name:\s*(.*?)(?:\n|$)', document.page_content)
        id_match = re.search(r'ID:\s*(.*?)(?:\n|$)', document.page_content)
        document.metadata['type'] = 'concept'
        if name_match:
                document.metadata['title'] = name_match.group(1)
        if id_match:
                document.metadata['source'] = id_match.group(1) 

        return document    

    def extract_concepts_from_article_content(self, article_content):
        concepts = []
        
        # Define patterns for each section
        patterns = {
            'preferred_terms': r'Preferred Terms \(Non-geographic, Non-organism contents from thesaurus\):\s*\n(.*?)(?:\s*(?:Organism Terms|Geographic Terms|$))',
            'organism_terms': r'Organism Terms \(Organism names from thesaurus\):\s*\n(.*?)(?:\s*(?:Preferred Terms|Geographic Terms|$))',
            'geographic_terms': r'Geographic Terms \(Geographic Tags indicating content about a place\):\s*\n(.*?)(?:\s*\n{2,}|$)',
        }

        # Extract terms for each section
        for _, pattern in patterns.items():
            match = re.search(pattern, article_content, re.DOTALL)
            if match:
                for term in match.group(1).split('\n'):
                    if term.strip():
                        concepts.append(term.lstrip('- ').strip())

        return concepts

    def write_to_error_file(self, type, text):
        if type=="articles":
            error_file_path = os.path.join(self.pathconfig.ERRORS_DIRECTORY_PATH, "articles_errors_neo4j.txt")
        else:
            error_file_path = os.path.join(self.pathconfig.ERRORS_DIRECTORY_PATH, "concepts_errors_neo4j.txt")
        
        text_exists = False
        try:
            with open(error_file_path, 'r', encoding='utf-8') as error_file:
                contents = error_file.read()
                if text in contents:
                    text_exists = True
        except FileNotFoundError:
            text_exists = False

        if not text_exists:
            with open(error_file_path, 'a', encoding='utf-8') as error_file:
                error_file.write(f"{text}\n")
                
    def remove_unreferenced_concept_nodes(self):
        referenced_concepts = set()

        ### Fetch all referenced concepts###
        type = 'articles'
        data_directory = os.path.join(self.pathconfig.PROCESSED_DATA_DIRECTORY, type)
        uploaded_abstracts_file_names = self.get_already_uploaded_file_names(type[:-1])
        print(f"Total abstracts in database: {len(uploaded_abstracts_file_names)}")
        print(f"Fetching all concepts related to these articles")

        for file_name in uploaded_abstracts_file_names:
            text_file_path = os.path.join(data_directory, file_name)
            with open(text_file_path, 'r', encoding='utf-8') as abstract_file:
                abstractcontents = abstract_file.read()
                concepts = self.extract_concepts_from_article_content(abstractcontents)
                for concept in concepts:
                    referenced_concepts.add(concept)
        ######################################
                    
        print(f"Total referenced concepts in database: {len(referenced_concepts)}")
        print(f"Total concept nodes in database before deletion: {self.get_total_concept_nodes()}")
        
        print(f"Deleting unreferenced concepts nodes in database")
        self.delete_unreferenced_concept_nodes(referenced_concepts)

        print(f"Total concept nodes in database after deletion: {self.get_total_concept_nodes()}")
        print("Done")
