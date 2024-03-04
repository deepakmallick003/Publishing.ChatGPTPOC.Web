import os
import threading
import openai
import re
import logging
from pathlib import Path

from langchain_community.document_loaders import TextLoader
from neo4j import GraphDatabase
from langchain_community.vectorstores import Neo4jVector
from langchain.text_splitter import CharacterTextSplitter
from langchain_openai import OpenAIEmbeddings

class ScaleDB:

    def __init__(self, settings, pathconfig):
        self.settings = settings
        self.pathconfig = pathconfig  

        openai.api_key = settings.Open_AI_API_Secret
        # openai.util.logger.setLevel(logging.CRITICAL)
        # logging.getLogger().setLevel(logging.CRITICAL)

        self.driver = GraphDatabase.driver(self.settings.Neo4J_URL, auth=(self.settings.Neo4J_UserName, self.settings.Neo4J_Password), database=self.settings.Neo4J_Database)
        self.embeddings = OpenAIEmbeddings(openai_api_key=self.settings.Open_AI_API_Secret, model=self.settings.Open_AI_Embedding_Model, dimensions=self.settings.Open_AI_Embedding_Dimensions)
        # self.neo4j_vector_index = self.get_neo4j_vector_index()
        
        self.documents_uploaded = 0
        self.total_document_to_upload=0
        

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

    def test2(self):
        text_file_path = os.path.join(self.pathconfig.DATA_DIRECTORY, 'Iran_main.txt')
        loader = TextLoader(text_file_path, encoding='utf8')
        documents = loader.load()
        documents[0].page_content = self.shrink_concept_doc_content(documents[0].page_content)
        documents[0] = self.update_concepts_metadata(documents[0])
        
        text_file_path = os.path.join(self.pathconfig.DATA_DIRECTORY, '20220000001_main.txt')
        loader = TextLoader(text_file_path, encoding='utf8')
        documents = loader.load()
        documents[0].page_content = self.shrink_article_doc_content(documents[0].page_content)
        documents[0] = self.update_article_metadata(documents[0])

        pass

    def test(self):
        text_file_path = os.path.join(self.pathconfig.DATA_DIRECTORY, '20220000001.txt')
        loader = TextLoader(text_file_path, encoding='utf8')
        documents = loader.load()
        documents[0] = self.update_article_metadata(documents[0])
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
            pre_delete_collection=False # False by default
        )

        self.neo4j_vector_index = Neo4jVector.from_existing_index(
                self.embeddings,
                url=self.settings.Neo4J_URL, 
                username=self.settings.Neo4J_UserName,
                password=self.settings.Neo4J_Password,
                database=self.settings.Neo4J_Database,
                index_name=self.settings.Neo4J_PrimaryIndexName,
                text_node_property="info", 
            )

        text_file_path = os.path.join(self.pathconfig.DATA_DIRECTORY, '20220000207.txt')
        loader = TextLoader(text_file_path, encoding='utf8')
        documents = loader.load()
        documents[0] = self.update_article_metadata(documents[0])
        self.neo4j_vector_index.add_documents(documents)

        ##concepts
        text_file_path = os.path.join(self.pathconfig.DATA_DIRECTORY, 'Finland.txt')
        loader = TextLoader(text_file_path, encoding='utf8')
        documents = loader.load()
        documents[0] = self.update_concepts_metadata(documents[0])
        self.neo4j_vector_index.add_documents(documents)

        text_file_path = os.path.join(self.pathconfig.DATA_DIRECTORY, 'Iran.txt')
        loader = TextLoader(text_file_path, encoding='utf8')
        documents = loader.load()
        documents[0] = self.update_concepts_metadata(documents[0])
        self.neo4j_vector_index.add_documents(documents)

        # #categories
        # text_file_path = os.path.join(self.pathconfig.DATA_DIRECTORY, 'Materials Science.txt')
        # loader = TextLoader(text_file_path, encoding='utf8')
        # documents = loader.load()
        # documents[0].metadata["title"]='Materials Science'
        # documents[0].metadata["document_type"]='category'
        # self.neo4j_vector_index.add_documents(documents)

        # text_file_path = os.path.join(self.pathconfig.DATA_DIRECTORY, 'Chemical and Biological Processing of Wood.txt')
        # loader = TextLoader(text_file_path, encoding='utf8')
        # documents = loader.load()
        # documents[0].metadata["title"]='Chemical and Biological Processing of Wood'
        # documents[0].metadata["document_type"]='category'
        # documents[0].metadata["source"]=''
        # self.neo4j_vector_index.add_documents(documents)

        # text_file_path = os.path.join(self.pathconfig.DATA_DIRECTORY, 'Bacterial and Fungal Pathogens of Humans.txt')
        # loader = TextLoader(text_file_path, encoding='utf8')
        # documents = loader.load()
        # documents[0].metadata["title"]='Bacterial and Fungal Pathogens of Humans'
        # documents[0].metadata["document_type"]='category'
        # documents[0].metadata["source"]=''
        # self.neo4j_vector_index.add_documents(documents)

        # text_file_path = os.path.join(self.pathconfig.DATA_DIRECTORY, 'Host Resistance and Immunity.txt')
        # loader = TextLoader(text_file_path, encoding='utf8')
        # documents = loader.load()
        # documents[0].metadata["title"]='Host Resistance and Immunity'
        # documents[0].metadata["document_type"]='category'
        # documents[0].metadata["source"]=''
        # self.neo4j_vector_index.add_documents(documents)

        # with self.driver.session(database=self.settings.Neo4J_Database) as session:
        #     relationship_name = "HAS_GEOGRAPHIC_TERM"
            
        #     article_node = session.run(f"MATCH (n) WHERE n.pan = '20220000001' AND n.type = 'article' RETURN n", database=self.settings.Neo4J_Database).data()
        #     article_node= article_node[0]['n']
        #     concept_node = session.run(f"MATCH (n) WHERE n.title = 'Iran' AND n.type = 'concept' RETURN n", database=self.settings.Neo4J_Database).data()
        #     concept_node= concept_node[0]['n']
        #     session.execute_write(self.create_article_concept_relationship, article_node, concept_node, relationship_name)

        #     article_node = session.run(f"MATCH (n) WHERE n.pan = '20220000207' AND n.type = 'article' RETURN n", database=self.settings.Neo4J_Database).data()
        #     article_node= article_node[0]['n']
        #     concept_node = session.run(f"MATCH (n) WHERE n.title = 'Finland' AND n.type = 'concept' RETURN n", database=self.settings.Neo4J_Database).data()
        #     concept_node= concept_node[0]['n']
        #     session.execute_write(self.create_article_concept_relationship, article_node, concept_node, relationship_name)

        # with self.driver.session(database=self.settings.Neo4J_Database) as session:
        #     relationship_name = "IS_CATEGORY_OF"
            
        #     article_node = session.run(f"MATCH (n) WHERE n.pan = '20220000001' AND n.type = 'article' RETURN n", database=self.settings.Neo4J_Database).data()
        #     article_node= article_node[0]['n']
        #     cat_node = session.run(f"MATCH (n) WHERE n.title = 'Materials Science' AND n.type = 'category' RETURN n", database=self.settings.Neo4J_Database).data()
        #     cat_node= cat_node[0]['n']
        #     session.execute_write(self.create_article_category_relationship, article_node, cat_node, relationship_name)

        #     article_node = session.run(f"MATCH (n) WHERE n.pan = '20220000001' AND n.type = 'article' RETURN n", database=self.settings.Neo4J_Database).data()
        #     article_node= article_node[0]['n']
        #     cat_node = session.run(f"MATCH (n) WHERE n.title = 'Chemical and Biological Processing of Wood' AND n.type = 'category' RETURN n", database=self.settings.Neo4J_Database).data()
        #     cat_node= cat_node[0]['n']
        #     session.execute_write(self.create_article_category_relationship, article_node, cat_node, relationship_name)

        #     article_node = session.run(f"MATCH (n) WHERE n.pan = '20220000207' AND n.type = 'article' RETURN n", database=self.settings.Neo4J_Database).data()
        #     article_node= article_node[0]['n']
        #     cat_node = session.run(f"MATCH (n) WHERE n.title = 'Bacterial and Fungal Pathogens of Humans' AND n.type = 'category' RETURN n", database=self.settings.Neo4J_Database).data()
        #     cat_node= cat_node[0]['n']
        #     session.execute_write(self.create_article_category_relationship, article_node, cat_node, relationship_name)

        #     article_node = session.run(f"MATCH (n) WHERE n.pan = '20220000207' AND n.type = 'article' RETURN n", database=self.settings.Neo4J_Database).data()
        #     article_node= article_node[0]['n']
        #     cat_node = session.run(f"MATCH (n) WHERE n.title = 'Host Resistance and Immunity' AND n.type = 'category' RETURN n", database=self.settings.Neo4J_Database).data()
        #     cat_node= cat_node[0]['n']
        #     session.execute_write(self.create_article_category_relationship, article_node, cat_node, relationship_name)



        return None

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
                pre_delete_collection=False # False by default
            )
            
            neo4j_vector_index = self.existing_vector_index()

        return neo4j_vector_index

    def create_vector_data_from_processed_documents(self):   
        self.add_documents_to_neo4j_vector_db_main('articles', n_threads=6)
        self.add_documents_to_neo4j_vector_db('concepts', n_threads=6)

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

        return text_files_to_upload

    def get_already_uploaded_file_names(self, document_type):
        filenames= set()

        with self.driver.session(database=self.settings.Neo4J_Database) as session:
            unique_property = 'pan' if document_type == 'article' else 'name'
        
            query_result = session.run(f"""
            MATCH (n) WHERE n.type = '{document_type}'
            RETURN REPLACE(n.{unique_property}, ' ', '_') + '.txt' AS uploaded_files
            """, database=self.settings.Neo4J_Database).data()

            filenames = {record['uploaded_files'] for record in query_result}

        return filenames
    
    def get_nodes(self, tx, document_type):
        return tx.run(f"MATCH (n) WHERE n.type = '{document_type}' RETURN n", database=self.Neo4J_Database).data()

    def update_article_metadata(self, document):
        # Extracting various details from the page_content
        title_match = re.search(r'Title:\s*(.*?)(?:\n|$)', document.page_content)
        pan_match = re.search(r'PAN:\s*(.*?)(?:\n|$)', document.page_content)
        # source_match = re.search(r'Article Link/URL/Source:\s*(.*?)(?:\n|$)', document.page_content)
        # pub_date = re.search(r'Publishing Date:\s*(.*?)(?:\n|$)', document.page_content)    
        # isbn_match = re.search(r'ISBN:\s*(.*?)(?:\n|$)', document.page_content)
        # day_match = re.search(r'Day:\s*(\d{1,2})(?:\n|$)', document.page_content)
        # month_match = re.search(r'Month:\s*(\d{1,2})(?:\n|$)', document.page_content)
        # year_match = re.search(r'Year:\s*(\d{4})(?:\n|$)', document.page_content)

        # document.metadata['document_type'] = 'article'
        # Updating metadata dictionary
        if title_match:
            document.metadata['title'] = title_match.group(1)
        if pan_match:
            # document.metadata['pan'] = pan_match.group(1)
            document.metadata['source'] = pan_match.group(1)
        # if source_match:
            # document.metadata['source'] = source_match.group(1)
        # if isbn_match:
            # document.metadata['isbn'] = isbn_match.group(1)
        # if day_match and month_match and year_match:
        #     pub_date = f"{year_match.group(1)}-{month_match.group(1).zfill(2)}-{day_match.group(1).zfill(2)}"
        #     document.metadata['publishing_date'] = pub_date   
        
        return document

    def update_concepts_metadata(self, document):
        # Extracting various details from the page_content
        # document.metadata['document_type'] = 'concept'
        # concept_section = re.search(r'Thesaurus Concept:\n\s*Concept:\n(.*?)\n(?:\s*Broader Concept:|\s*Narrower Concepts:|\s*Related Concepts:|\Z)', document.page_content, re.DOTALL)
        # if concept_section:
        #     concept_details = concept_section.group(1)
        #     name_match = re.search(r'name:\s*(.*?)(?:\n|$)', concept_details)
        #     uri_match = re.search(r'uri:\s*(.*?)(?:\n|$)', concept_details)
        #     # Updating metadata dictionary
        #     if name_match:
        #         # document.metadata['name'] = name_match.group(1)
        #         document.metadata['title'] = name_match.group(1)
        #         document.metadata['source'] = name_match.group(1) 
        #     if uri_match:
        #         document.metadata['uri'] = uri_match.group(1)
        #         document.metadata['source'] = uri_match.group(1)   

        name_match = re.search(r'Name:\s*(.*?)(?:\n|$)', document.page_content)
        id_match = re.search(r'ID:\s*(.*?)(?:\n|$)', document.page_content)
        if name_match:
                document.metadata['title'] = name_match.group(1)
        if id_match:
                document.metadata['source'] = id_match.group(1) 

        return document    

    def add_documents_to_neo4j_vector_db_child(self, type, file_name):
        data_directory = os.path.join(self.pathconfig.PROCESSED_DATA_DIRECTORY, type)
        error_file_path = os.path.join(self.pathconfig.ERRORS_DIRECTORY_PATH, f"{type}_errors_neo4j.txt")

        try:
            text_file_path = os.path.join(data_directory, file_name)
            loader = TextLoader(text_file_path, encoding='utf8')
            documents = loader.load()
            if type=='articles':
                documents[0] = self.update_article_metadata(documents[0])
            elif type=='concepts':
                documents[0] = self.update_concepts_metadata(documents[0])
            
            self.neo4j_vector_index.add_documents(documents)

            documents_left_to_upload = self.total_document_to_upload - self.documents_uploaded
            print(f"\rUploaded {self.documents_uploaded}/{documents_left_to_upload} Documents. {documents_left_to_upload} files left to upload.", end='')     

        except Exception as e:
            with open(error_file_path, 'a', encoding='utf-8') as error_file:
                error_file.write(f"{file_name}\n")

        self.documents_uploaded += 1

    def worker_function(self, type, files):
        for file in files:
            self.add_documents_to_neo4j_vector_db_child(type, file)

    def add_documents_to_neo4j_vector_db_main(self, type='articles', n_threads=4):
        documents_set = self.get_text_files_to_upload(type)
        documents_set = list(documents_set)
        self.total_document_to_upload = len(documents_set)
        self.documents_uploaded = 0
        print(f"\nTotal Unique Documents of Type {type}, which are not already processed: {self.total_document_to_upload}")

        # Divide files among threads
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


    def create_relationships_in_neo4j_db(self):
        with self.driver.session(database=self.settings.Neo4J_Database) as session:
            all_articles_nodes = session.execute_read(self.get_nodes,'article')
            all_concept_nodes = session.execute_read(self.get_nodes,'concept')

            # Creating a mapping of concept names to nodes for efficient lookup
            concept_name_to_node = {node['n'].get('name'): node['n'] for node in all_concept_nodes if node['n'].get('name')}

            # Mapping of vocab type to relationship name
            vocab_type_to_relationship_name = {
                'preferred_terms': 'HAS_PREFERRED_TERM',
                'organism_terms': 'HAS_ORGANISM_TERM',
                'geographic_terms': 'HAS_GEOGRAPHIC_TERM',
            }
            
            # Step 2: Create Article to Concept relationships
            for article_node in all_articles_nodes:
                article_node= article_node['n']
                article_content = article_node['info']
                
                vocab_sections = self.extract_vocab_sections_from_article_content(article_content)
            
                for vocab_type, concepts in vocab_sections.items():
                    relationship_name = vocab_type_to_relationship_name.get(vocab_type)
                    for concept_name in concepts:
                        concept_node = concept_name_to_node.get(concept_name)
                        if concept_node and relationship_name:                    
                            try:
                                session.execute_write(self.create_article_concept_relationship, article_node, concept_node, relationship_name)
                                print(article_node['pan'], relationship_name, concept_node['name'], 'DONE')                        
                            except:
                                print(article_node['pan'], relationship_name, concept_node['name'], 'ERROR')        
            
                print()
                print('---------------')
                print()
        
            # Step 3: Create Concept to Concept relationships
            for concept_node in all_concept_nodes:
                concept_details = concept_node['n']['info']  # Adjust field name based on your data structure
                concept_node= concept_node['n']
                if 'name' not in concept_node:
                    continue
                
                # Identify broader, narrower, and related concepts using regex
                broader_concept_section = re.search(r'Broader Concept:\s*\n*\s*name: (.*?)(?:\n|, uri)', concept_details)
                if broader_concept_section:
                    broader_concepts = [broader_concept_section.group(1)]
                else:
                    broader_concepts = []
                
                narrower_concept_section = re.search(r'Narrower Concepts:([\s\S]*?)(?:Broader Concepts:|Related Concepts:|$)', concept_details)
                if narrower_concept_section:
                    narrower_concepts = re.findall(r'name: (.*?)(?:, uri|\n|$)', narrower_concept_section.group(1))
                else:
                    narrower_concepts = []
                
                related_concept_section = re.search(r'Related Concepts:([\s\S]*?)(?:Broader Concepts:|Narrower Concepts:|$)', concept_details)
                if related_concept_section:
                    related_concepts = re.findall(r'name: (.*?)(?:, uri|\n|$)', related_concept_section.group(1))
                else:
                    related_concepts = []
                
                # Create relationships with other concept nodes based on broader, narrower, and related concepts
                for broader_concept_name in broader_concepts:
                    broader_concept_node = concept_name_to_node.get(broader_concept_name)
                    if broader_concept_node:
                        try:
                            session.execute_write(self.create_concept_relationship, broader_concept_node, concept_node, 'BROADER_TERM_FOR')
                            print(broader_concept_node['name'], 'BROADER_TERM_FOR', concept_node['name'], 'DONE')                    
                        except Exception as e:
                            print(broader_concept_node['name'], 'BROADER_TERM_FOR', concept_node['name'], 'ERROR')  
                            print(e)
                        
                for narrower_concept_name in narrower_concepts:
                    narrower_concept_node = concept_name_to_node.get(narrower_concept_name)
                    if narrower_concept_node:
                        try:
                            session.execute_write(self.create_concept_relationship, narrower_concept_node, concept_node, 'NARROWER_TERM_FOR')
                            print(narrower_concept_node['name'], 'NARROWER_TERM_FOR', concept_node['name'], 'DONE')                    
                        except Exception as e:
                            print(narrower_concept_node['name'], 'NARROWER_TERM_FOR', concept_node['name'], 'ERROR')
                            print(e)
                        
                for related_concept_name in related_concepts:
                    related_concept_node = concept_name_to_node.get(related_concept_name)
                    if related_concept_node:
                        try:
                            session.execute_write(self.create_concept_relationship, related_concept_node, concept_node, 'RELATED_TERM')
                            print(related_concept_node['name'], 'RELATED_TERM', concept_node['name'], 'DONE')                    
                        except Exception as e:                
                            print(related_concept_node['name'], 'RELATED_TERM', concept_node['name'], 'ERROR')
                            print(e)
                            
                print()
                print('---------------')
                print()

    def create_article_concept_relationship(self, tx, start_node, end_node, relationship_type):
        query = f"""
        MATCH (a {{pan: '{start_node['pan']}'}})
        MATCH (b {{title: '{end_node['title']}'}})
        MERGE (a)-[r:{relationship_type}]->(b)
        """
        tx.run(query, database=self.settings.Neo4J_Database)

    def create_article_category_relationship(self, tx, start_node, end_node, relationship_type):
        query = f"""
        MATCH (a {{pan: '{start_node['pan']}'}})
        MATCH (b {{title: '{end_node['title']}'}})
        MERGE (a)-[r:{relationship_type}]->(b)
        """
        tx.run(query, database=self.settings.Neo4J_Database)

    def create_concept_relationship(self, tx, start_node, end_node, relationship_type):
        query = f"""
        MATCH (a {{name: '{start_node['name']}'}})
        MATCH (b {{name: '{end_node['name']}'}})
        MERGE (a)-[r:{relationship_type}]->(b)
        """
        tx.run(query, database=self.settings.Neo4J_Database)
    
    def extract_vocab_sections_from_article_content(self, article_content):
        vocab_sections = {
            'preferred_terms': [],
            'organism_terms': [],
            'geographic_terms': [],
        }
        
        # Define patterns for each section
        patterns = {
            'preferred_terms': r'Preferred Terms \(Non-geographic, Non-organism contents from thesaurus\):\s*\n(.*?)(?:\s*(?:Organism Terms|Geographic Terms|$))',
            'organism_terms': r'Organism Terms \(Organism names from thesaurus\):\s*\n(.*?)(?:\s*(?:Preferred Terms|Geographic Terms|$))',
            'geographic_terms': r'Geographic Terms \(Geographic Tags indicating content about a place\):\s*\n(.*?)(?:\s*\n{2,}|$)',
        }

        # Extract terms for each section
        for section, pattern in patterns.items():
            match = re.search(pattern, article_content, re.DOTALL)
            if match:
                vocab_sections[section] = [term.lstrip('- ').strip() for term in match.group(1).split('\n') if term.strip()]

        return vocab_sections

# create_vector_data_from_processed_documents()
# create_relationships_in_neo4j_db()
