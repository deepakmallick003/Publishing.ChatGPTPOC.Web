import os
import threading
import time
import xml.etree.ElementTree as ET
import requests
import json

class ProcessDB:

    def __init__(self, settings, pathconfig):
        self.settings = settings
        self.pathconfig = pathconfig   
        self.processed_files_count = 0  # Shared counter for tracking processed files
        self.processed_files_lock = threading.Lock()  # Lock for synchronizing access to the counter
        self.total_files_to_process = 0  # Total number of files to be processed

    def parse_element(self, element, output_lines, indent_level=0):
        indent_unit = 4  

        def write_line(content, indent_level=0):
            # file.write(' ' * (indent_level * indent_unit) + content + '\n')
            output_lines.append(' ' * (indent_level * indent_unit) + content + '\n')

        if element.tag == "article":
            write_line("Article:", indent_level)

        elif element.tag == "article-id":
            attrib = element.attrib.get('pub-id-type')
            text = element.text.strip()
            if attrib == 'CABI-pan':
                write_line(f"PAN: {text}", indent_level+1)
            elif attrib == 'doi':
                write_line(f"DOI: {text}", indent_level+1)
                write_line(f"Article Link/URL/Source: {self.settings.ARTICLES_BASE_URL + text}", indent_level+1)

        elif element.tag == "title-group":
            article_title = element.find('article-title')
            if article_title is not None:
                title_text = ''.join(article_title.itertext()).strip()
                if title_text:
                    write_line(f"Title: {title_text}", indent_level+1)
                
        elif element.tag == "abstract":
            abstract_summary = element.find('p')
            if abstract_summary is not None:
                summary_text = ''.join(abstract_summary.itertext()).strip()
                if summary_text:
                    write_line(f"Abstract Summary: {summary_text}", indent_level+1)

        elif element.tag == "pub-date":
            write_line("Publishing Date:", indent_level+1)
            for child in element:
                if child.text:
                    write_line(f"{child.tag.capitalize()}: {child.text.strip()}", indent_level + 2)

        elif element.tag == "isbn" and element.text:
            write_line("ISBN:", indent_level+1)
            write_line(element.text.strip(), indent_level + 2)

        elif element.tag == "publisher-name" and element.text:
            write_line("Publisher Name:", indent_level+1)
            write_line(element.text.strip(), indent_level + 2)

        elif element.tag == "publisher-loc":
            write_line("Publisher Location:", indent_level+1)
            for child in element:
                if child.text:
                    write_line(f"{child.tag.capitalize()}: {child.text.strip()}", indent_level + 2)

        elif element.tag == "subj-group" and element.attrib.get('subj-group-type') == "cabi-codes":
            write_line("Subjects or Categories:", indent_level+1)
            for compound_subject in element.findall('compound-subject'):
                labels = [label.text for label in compound_subject.findall('compound-subject-part[@content-type="label"]') if label.text]
                for label in labels:
                    write_line(f"- {label.strip()}", indent_level + 2)

        elif element.tag == "person-group" and element.attrib.get('person-group-type') == "author":
            author_names = []
            for child in element:
                name_parts = [sub_child.text for sub_child in child if sub_child.tag in ['given-names', 'surname'] and sub_child.text]
                if name_parts:
                    author_names.append(' '.join(name_parts))
            if author_names:
                write_line("Authors:", indent_level+1)
                for name in author_names:
                    write_line(f"- {name}", indent_level + 2)

        elif element.tag == "kwd-group" and element.attrib.get('kwd-group-type') == "CABI-keyword":
            write_line("Keywords/Thesaurus Concepts:", indent_level+1)
            
            vocab_map = {
                'preferredTerm': "Preferred Terms (Non-geographic, Non-organism contents from thesaurus):",
                'organismTerm': "Organism Terms (Organism names from thesaurus):",
                'geographicTerm': "Geographic Terms (Geographic Tags indicating content about a place):"
            }
            terms = {key: [] for key in vocab_map}
        
            for kwd in element.findall('kwd'):
                vocab = kwd.attrib.get('vocab')
                if vocab and vocab in vocab_map and kwd.text:
                    terms[vocab].append(kwd.text.strip())

            for vocab, description in vocab_map.items():
                if terms[vocab]:
                    write_line(description, indent_level + 2)
                    for term in terms[vocab]:
                        write_line(f"- {term}", indent_level + 3)

        for child in element:
            self.parse_element(child, output_lines, indent_level)

    def fetch_concept_hierarchy(self, concept, query_template):
        headers = {'Content-Type': 'application/x-www-form-urlencoded'}
        query = query_template.format(keyword=concept)
        data = {'query': query, 'content-type': 'application/json-ld'}
        response = requests.post(self.settings.CABT_PP_BASE_URL, headers=headers, data=data)
        
        try:
            response_json = response.json()
            if not response_json.get('results', {}).get('bindings'):                        
                return None
            return response_json
        except json.JSONDecodeError:
            print(f"Failed to decode JSON. Response text: {response.text}")
            return None
            
    def extract_terms_from_xml(self, root):
        vocab_map = {
            'preferredTerm': "Preferred Terms (Non-geographic, Non-organism contents from thesaurus)",
            'organismTerm': "Organism Terms (Organism names from thesaurus)",
            'geographicTerm': "Geographic Terms (Geographic Tags indicating content about a place)"
        }

        filtered_terms = []

        kwd_group = root.find(".//kwd-group[@kwd-group-type='CABI-keyword']")
        if kwd_group is not None:
            for kwd in kwd_group.findall('kwd'):
                vocab_type = kwd.get('vocab')
                if vocab_type in vocab_map:
                    filtered_terms.append(kwd.text)

        return filtered_terms

    def write_concept_to_file(self, output_text_file_path, concept_dict):      
        # print('Creating new Concept document:', output_text_file_path)
        with open(output_text_file_path, 'w', encoding='utf-8') as file:    
            for key, value in concept_dict.items():
                file.write(f"{key}:\n")
                for subkey, subvalue in value.items():
                    if isinstance(subvalue, list):
                        file.write(f"    {subkey}:\n")
                        for item in subvalue:
                            file.write(f"        Concept:\n")
                            for k, v in item.items():  # Changed this line
                                file.write(f"            {k}: {v}\n")
                    else:
                        file.write(f"    {subkey}:\n")
                        for k, v in subvalue.items():
                            file.write(f"        {k}: {v}\n")

    def build_concept_dict(self, concept_name, concept_data):
        concept_dict = {
            "Thesaurus Concept": {
                "Concept": None,
                "Broader Concept": None,
                "Narrower Concepts": set(),
                "Related Concepts": set()
            }
        }

        for binding in concept_data.get('results', {}).get('bindings', []):
            # get all the necessary data
            concept_uri = binding.get('concept', {}).get('value')
            broader_name = binding.get('broaderLabel', {}).get('value')
            broader_uri = binding.get('broaderConcept', {}).get('value')
            narrower_name = binding.get('narrowerLabel', {}).get('value')
            narrower_uri = binding.get('narrowerConcept', {}).get('value')
            related_name = binding.get('relatedLabel', {}).get('value')
            related_uri = binding.get('relatedConcept', {}).get('value')

            # set the main concept
            if concept_name:
                concept_dict["Thesaurus Concept"]["Concept"] = {
                    "name": concept_name,
                    "uri": binding.get('concept', {}).get('value')
                }
            
            # set the broader concept
            if broader_name and broader_uri:
                concept_dict["Thesaurus Concept"]["Broader Concept"] = {
                    "name": broader_name,
                    "uri": broader_uri
                }

            # add unique narrower concepts
            if narrower_name and narrower_uri:
                concept_dict["Thesaurus Concept"]["Narrower Concepts"].add(
                    json.dumps({"name": narrower_name, "uri": narrower_uri})
                )

            # add unique related concepts
            if related_name and related_uri:
                concept_dict["Thesaurus Concept"]["Related Concepts"].add(
                    json.dumps({"name": related_name, "uri": related_uri})
                )

        # convert sets to lists of dicts
        concept_dict["Thesaurus Concept"]["Narrower Concepts"] = [
            json.loads(item) for item in concept_dict["Thesaurus Concept"]["Narrower Concepts"]
        ]
        concept_dict["Thesaurus Concept"]["Related Concepts"] = [
            json.loads(item) for item in concept_dict["Thesaurus Concept"]["Related Concepts"]
        ]

        return concept_dict

    def get_jats_files_to_process(self):
        print(f"Getting JATS Files to Process..")
        unprocessed_files = []
        processed_files_dir = self.pathconfig.ARTICLES_DATA_DIRECTORY_PATH

        # Create a set of already processed file names without the extension
        processed_files_set = {
            os.path.splitext(file_name)[0]
            for file_name in os.listdir(processed_files_dir)
        }

        # Walk through the directory containing raw JATS XML files
        for root_dir, sub_dirs, files in os.walk(self.pathconfig.RAW_DATA_DIRECTORY):
            for file_name in files:
                if file_name.endswith('.xml'):
                    file_base_name = os.path.splitext(file_name)[0]
                    # Check if this file is not in the set of processed files
                    if file_base_name not in processed_files_set:
                        unprocessed_files.append(os.path.join(root_dir, file_name))

        return unprocessed_files

    def process_xml_file(self, xml_file_path, concepts_lock):
        file_name = os.path.basename(xml_file_path)
        try:
            tree = ET.parse(xml_file_path)
            root = tree.getroot()

            # Parse JATS XML and create document
            output_text_file_path = os.path.join(self.pathconfig.ARTICLES_DATA_DIRECTORY_PATH, file_name.replace('.xml', '.txt'))
            with open(output_text_file_path, 'w', encoding='utf-8') as f:
                output_lines = []
                self.parse_element(root, output_lines)
                f.writelines(output_lines)

            # Extract concepts of this article
            concepts = self.extract_terms_from_xml(root)

            # Synchronized write to CONCEPTS_TO_PROCESS_FILE
            with concepts_lock:
                with open(self.pathconfig.CONCEPTS_TO_PROCESS_FILE_PATH, 'a', encoding='utf-8') as concepts_to_process_file:
                     concepts_to_process_file.writelines([concept + '\n' for concept in concepts])

            with self.processed_files_lock:
                self.processed_files_count += 1
                print(f"\rProcessed {self.processed_files_count}/{self.total_files_to_process} XML files.", end='')

        except Exception as e:
            with self.processed_files_lock:
                with open(self.pathconfig.ARTICLES_ERRORS_FILE_PATH, 'a', encoding='utf-8') as error_file:
                    error_file.write(f"{file_name}\n")

    def worker_function(self, files):
        for xml_file_path in files:
            self.process_xml_file(xml_file_path, self.processed_files_lock)


    def process_abstracts_xml_and_create_documents_for_abstracts(self, n_threads=4):
        unprocessed_files = self.get_jats_files_to_process()
        self.total_files_to_process = len(unprocessed_files)

        if not os.path.exists(self.pathconfig.ARTICLES_DATA_DIRECTORY_PATH):
            os.makedirs(self.pathconfig.ARTICLES_DATA_DIRECTORY_PATH)

        print(f"Total JATS XML files which are not already processed: {self.total_files_to_process}")

        # Divide files among threads
        files_per_thread = len(unprocessed_files) // n_threads + (len(unprocessed_files) % n_threads > 0)

        if files_per_thread>0:
            threads = []
            for i in range(0, len(unprocessed_files), files_per_thread):
                thread_files = unprocessed_files[i:i+files_per_thread]
                thread = threading.Thread(target=self.worker_function, args=(thread_files,))
                threads.append(thread)
                thread.start()

            for thread in threads:
                thread.join()

        print("\nARTICLES Processing complete.")


    def get_concepts_to_process(self):
        concepts_set = set()

        # Read concepts from CONCEPTS_TO_PROCESS_FILE
        with open(self.pathconfig.CONCEPTS_TO_PROCESS_FILE_PATH, 'r', encoding='utf-8') as concept_lists_file:
            for line in concept_lists_file:
                concept = line.strip()
                concepts_set.add(concept)

        # Remove concepts present in already processed CONCEPTS_DATA_DIRECTORY_PATH
        processed_dir_path = self.pathconfig.CONCEPTS_DATA_DIRECTORY_PATH
        for file_name in os.listdir(processed_dir_path):
            concept_name = file_name[:-4].replace('_', ' ')
            if concept_name in concepts_set:
                concepts_set.remove(concept_name)

        return concepts_set

    def process_abstracts_xml_and_create_documents_for_concepts(self):
        if not os.path.exists(self.pathconfig.CONCEPTS_DATA_DIRECTORY_PATH):
            os.makedirs(self.pathconfig.CONCEPTS_DATA_DIRECTORY_PATH)

        with open(str(self.pathconfig.SPAQRQL_QUERY_FILE_PATH), 'r') as file:
            query_template = file.read().replace('\n', ' ').strip()
        
        concepts_set = self.get_concepts_to_process()
        total_concepts_to_process = len(concepts_set)
        concepts_processed = 0
        print(f"\nTotal Unique Concepts which are not already processed: {total_concepts_to_process}")

        # Extract Concept Data from CABT and Create new documents for each concept
        for concept_name in concepts_set:
            try:
                concept_file_name = concept_name.replace(' ', '_')
                output_text_file_path = os.path.join(self.pathconfig.CONCEPTS_DATA_DIRECTORY_PATH, f'{concept_file_name}.txt')
                concept_data = self.fetch_concept_hierarchy(concept_name, query_template)
                if concept_data is not None:
                    concept_dict = self.build_concept_dict(concept_name, concept_data)
                    self.write_concept_to_file(output_text_file_path, concept_dict)
                else:
                    with open(self.pathconfig.CONCEPTS_ERRORS_FILE_PATH, 'a', encoding='utf-8') as file:
                        file.write(concept_name + '\n')      

                concepts_left_to_process = total_concepts_to_process - concepts_processed
                print(f"\rProcessed {concepts_processed}/{total_concepts_to_process} Concepts. {concepts_left_to_process} files left to process.", end='')          
            
                time.sleep(0.5)
            except Exception as e:
                with open(self.pathconfig.CONCEPTS_ERRORS_FILE_PATH, 'a', encoding='utf-8') as error_file:
                    error_file.write(f"{concept_name}\n")

            concepts_processed += 1

        print("\CONCEPTS Processing complete.")

