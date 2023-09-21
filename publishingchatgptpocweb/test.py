
# import os
# import openai
# import networkx as nx
# import xml.etree.ElementTree as ET
# import requests
# from pathlib import Path
# from dotenv import load_dotenv
# load_dotenv()


# # In[2]:


# from langchain.llms import OpenAI
# from langchain.indexes import GraphIndexCreator
# from langchain.chains import GraphQAChain
# from langchain.prompts import PromptTemplate
# from langchain.graphs.networkx_graph import KnowledgeTriple


# # In[3]:


# PARENT_PATH = Path.cwd().parent
# if 'publishingchatgptpocweb' not in str(PARENT_PATH):
#     PARENT_PATH = PARENT_PATH / 'publishingchatgptpocweb'

# CORE_DIRECTORY = PARENT_PATH / 'core'
# DATA_DIRECTORY = PARENT_PATH / 'data'

# SPAQRQL_QUERY_FILE_PATH = CORE_DIRECTORY / 'sparql_query_template.sparql'
# JATS_DATA_DIRECTORY_PATH = DATA_DIRECTORY / 'raw'
# SAVED_GRAPH_PATH = DATA_DIRECTORY / 'processed' / 'graph.gml'


# # In[4]:


# OPEN_AI_API_SECRET = os.getenv('Open__AI__API__Secret')
# openai.api_key = OPEN_AI_API_SECRET


# # In[5]:


# def build_graph(kg=[], use_openai=False):
#     if use_openai:
#         index_creator = GraphIndexCreator(llm=OpenAI(openai_api_key=OPEN_AI_API_SECRET, temperature=0))
#         graph = index_creator.from_text('')
#         for (node1, relation, node2) in kg:
#             graph.add_triple(KnowledgeTriple(node1, relation, node2))

#         graph.write_to_gml(str(SAVED_GRAPH_PATH))
#     else:
#         graph = nx.DiGraph()  # Updated this line to properly initialize the graph variable
#         for (node1, relation, node2) in kg:
#             graph.add_edge(node1, node2, relation=relation)

#         nx.write_gml(graph, str(SAVED_GRAPH_PATH))


# def fetch_concept_hierarchy(concept, query_template):
#     url = "https://id.cabi.org/PoolParty/sparql/cabt"
#     headers = {
#         'Content-Type': 'application/x-www-form-urlencoded'
#     }
#     query = query_template.format(keyword=concept)
    
#     data = {
#         'query': query,
#         'content-type': 'application/json-ld'
#     }
#     response = requests.post(url, headers=headers, data=data)
#     return response.json()


# def add_concept_triples_to_kg(kg_dict, concept_data, value, pan_number, relation_name):
#     for binding in concept_data.get('results', {}).get('bindings', []):
#         concept = binding.get('concept', {}).get('value')
#         broaderConcept = binding.get('broaderConcept', {}).get('value')
#         broaderLabel = binding.get('broaderLabel', {}).get('value')
#         narrowerConcept = binding.get('narrowerConcept', {}).get('value')
#         narrowerLabel = binding.get('narrowerLabel', {}).get('value')
#         relatedConcept = binding.get('relatedConcept', {}).get('value')
#         relatedLabel = binding.get('relatedLabel', {}).get('value')

#         # Mapping every unique concept to its URI
#         if concept:
#             kg_dict.setdefault('concept_uri', {}).setdefault(value, set()).add(concept)
#         if broaderLabel and broaderConcept:
#             kg_dict.setdefault('concept_uri', {}).setdefault(broaderLabel, set()).add(broaderConcept)
#         if narrowerLabel and narrowerConcept:
#             kg_dict.setdefault('concept_uri', {}).setdefault(narrowerLabel, set()).add(narrowerConcept)
#         if relatedLabel and relatedConcept:
#             kg_dict.setdefault('concept_uri', {}).setdefault(relatedLabel, set()).add(relatedConcept)

#         # Establishing relations between the concepts
#         if broaderLabel:
#             kg_dict.setdefault('broader_relation', {}).setdefault(value, set()).add(broaderLabel)
#         if narrowerLabel:
#             kg_dict.setdefault('narrower_relation', {}).setdefault(value, set()).add(narrowerLabel)
#         if relatedLabel:
#             kg_dict.setdefault('related_relation', {}).setdefault(value, set()).add(relatedLabel)

#     # Linking the calling concept with the PAN number
#     kg_dict.setdefault(relation_name, {}).setdefault(pan_number, set()).add(value)





# def convert_kg_dict_to_triples(kg_dict):
#     triples_list = []

#     for relation_type, relation_data in kg_dict.items():
#         for concept, relations in relation_data.items():
#             for related_concept in relations:
#                 triple = (concept, relation_type, related_concept)
#                 triples_list.append(triple)

#     return triples_list


# def build_knowledge_graph_list(directory_path):
#     kg_dict = {}

#     with open(str(SPAQRQL_QUERY_FILE_PATH), 'r') as file:
#         query_template = file.read().replace('\n', ' ').strip()

#     keywords_vocab_to_relation = {
#         "preferredTerm": "preferred_term",
#         "organismTerm": "organism_name",
#         "geographicTerm": "geographic_tag"
#     }

#     # Walking through each subdirectory in the specified directory
#     for root_dir, sub_dirs, files in os.walk(directory_path):
#         for file_name in files:
#             if file_name.endswith('.xml'):
                
#                 file_path = os.path.join(root_dir, file_name)
#                 with open(file_path, 'r', encoding='utf-8') as file:
#                     jats_xml = file.read()
                
#                 # Parse the XML data to get the root element
#                 root = ET.fromstring(jats_xml)
                
#                 # Extract the pan_number from the XML
#                 pan_number = root.find(".//article-id[@pub-id-type='CABI-pan']").text

#                 # Filter keywords based on vocab of interest
#                 for vocab_type, relation_name in keywords_vocab_to_relation.items():
#                     for kwd in root.findall(f".//kwd[@vocab='{vocab_type}']"):
#                         # Extract value from kwd element
#                         value = kwd.text

#                         # Fetch concept hierarchy data using SPARQL query
#                         concept_data = fetch_concept_hierarchy(value, query_template) 

#                         # Add Concept triples to the knowledge graph list
#                         add_concept_triples_to_kg(kg_dict, concept_data, value, pan_number, relation_name)
                    
#                 # Adding relations for various details extracted from the XML file
#                 kg_dict.setdefault('doi', {}).setdefault(pan_number, set()).add(root.find(".//article-id[@pub-id-type='doi']").text)
#                 kg_dict.setdefault('title', {}).setdefault(pan_number, set()).add(root.find(".//article-title").text)
#                 kg_dict.setdefault('publication_date', {}).setdefault(pan_number, set()).add(root.find(".//pub-date").get('iso-8601-date'))
#                 kg_dict.setdefault('product_source', {}).setdefault(pan_number, set()).add(root.find(".//product[@product-type='source']/source").text)
#                 kg_dict.setdefault('publisher_name', {}).setdefault(pan_number, set()).add(root.find(".//product[@product-type='source']/publisher-name").text)
#                 kg_dict.setdefault('publisher_city', {}).setdefault(pan_number, set()).add(root.find(".//product[@product-type='source']/publisher-loc/city").text)
#                 kg_dict.setdefault('publisher_country', {}).setdefault(pan_number, set()).add(root.find(".//product[@product-type='source']/publisher-loc/country").text)
                
#                 authors_given_names = [name.text for name in root.findall(".//person-group[@person-group-type='author']/string-name/given-names")]
#                 authors_surnames = [name.text for name in root.findall(".//person-group[@person-group-type='author']/string-name/surname")]
#                 kg_dict.setdefault('author_given_names', {}).setdefault(pan_number, set()).update(authors_given_names)
#                 kg_dict.setdefault('author_surnames', {}).setdefault(pan_number, set()).update(authors_surnames)
                
#                 abstract_text = " ".join([p.text for p in root.findall(".//abstract/p")])
#                 kg_dict.setdefault('abstract', {}).setdefault(pan_number, set()).add(abstract_text)
               
#     return kg_dict


# kg_dict = build_knowledge_graph_list(JATS_DATA_DIRECTORY_PATH)
# kg_list = convert_kg_dict_to_triples(kg_dict)
# build_graph(kg=kg_list)



