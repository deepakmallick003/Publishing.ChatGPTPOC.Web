
# import os
# import openai
# import networkx as nx
# import xml.etree.ElementTree as ET
# import requests
# import json
# from pathlib import Path
# from dotenv import load_dotenv
# load_dotenv()


# # from langchain.llms import OpenAI
# # from langchain.chat_models import ChatOpenAI
# # from langchain.chains import GraphCypherQAChain
# # from langchain.graphs import Neo4jGraph
# from neo4j import GraphDatabase


# PARENT_PATH = Path.cwd().parent
# if 'publishingchatgptpocweb' not in str(PARENT_PATH):
#     PARENT_PATH = PARENT_PATH / 'publishingchatgptpocweb'

# CORE_DIRECTORY = PARENT_PATH / 'core'
# DATA_DIRECTORY = PARENT_PATH / 'data'

# SPAQRQL_QUERY_FILE_PATH = CORE_DIRECTORY / 'sparql_query_template.sparql'
# GRAPH_STRUC_FILE_PATH = CORE_DIRECTORY / 'graph_data_structure.json'
# JATS_DATA_DIRECTORY_PATH = DATA_DIRECTORY / 'raw'
# BASIC_GRAPH_SAVED_FILE_PATH = DATA_DIRECTORY / 'processed' / 'basic_graph.gml'
# OPEN_AI_GRAPH_SAVED_FILE_PATH = DATA_DIRECTORY / 'processed' / 'open_ai_graph.gml'


# OPEN_AI_API_SECRET = os.getenv('Open__AI__API__Secret')
# openai.api_key = OPEN_AI_API_SECRET


# # Load the JSON structure
# with open(GRAPH_STRUC_FILE_PATH, 'r') as file:
#     structure = json.load(file)

# with open(str(SPAQRQL_QUERY_FILE_PATH), 'r') as file:
#     query_template = file.read().replace('\n', ' ').strip()

# # Initialize the Neo4j driver
# uri = "bolt://localhost:7687"
# driver = GraphDatabase.driver(uri, auth=("neo4j", os.getenv('PublishingChatGPT_Neo4J_Password_Local')))

# class KnowledgeGraphBuilder:
#     def __init__(self, structure):
#         self.driver = driver
#         self.structure = structure
#         self.query_template = query_template
        
#     # def close(self):
#     #     self.driver.close()

#     def fetch_concept_hierarchy(self, concept):
#         url = "https://id.cabi.org/PoolParty/sparql/cabt"
#         headers = {'Content-Type': 'application/x-www-form-urlencoded'}
#         query = self.query_template.format(keyword=concept)
#         data = {'query': query, 'content-type': 'application/json-ld'}
#         response = requests.post(url, headers=headers, data=data)
#         return response.json()
    
#     def add_or_update_concept_kg(self, concept_name, pan_number, vocab_type=None):
#         # Fetch concept hierarchy data using SPARQL query
#         concept_data = self.fetch_concept_hierarchy(concept_name)
        
#         # Helper function to create or update a concept node
#         def create_or_update_concept(session, name, uri):
#             query = f"""
#             MERGE (c:Concept {{name: '{name}'}})
#             ON CREATE SET c.uri = '{uri}'
#             """
#             # session.run(query)
        
#         with self.driver.session() as session:
#             # Creating a relationship between the main concept and the article at the end, outside of the inner loop but inside the session
#             if vocab_type:
#                 query = f"""
#                 MATCH (a:Concept {{name: '{concept_name}'}})
#                 MATCH (b:Article {{PAN_number: '{pan_number}'}})
#                 MERGE (a)-[:{vocab_type}]->(b)
#                 """
#                 # session.run(query)

#             # Get the URI for the main concept (assumes there is always a main concept)
#             conceptUri = concept_data['results']['bindings'][0].get('concept', {}).get('value')
#             # Create or update the main concept node (outside the loop to avoid repetition)
#             create_or_update_concept(session, concept_name, conceptUri)

#             # Iterate through concept_data (which contains information from the SPARQL query)
#             for relation_data in concept_data['results']['bindings']:
#                 broaderConceptName = relation_data.get('broaderLabel', {}).get('value')
#                 broaderConceptUri = relation_data.get('broaderConcept', {}).get('value')
#                 narrowerConceptName = relation_data.get('narrowerLabel', {}).get('value')
#                 narrowerConceptUri = relation_data.get('narrowerConcept', {}).get('value')
#                 relatedConceptName = relation_data.get('relatedLabel', {}).get('value')
#                 relatedConceptUri = relation_data.get('relatedConcept', {}).get('value')

#                 # Creating a list of tuples containing relation type and concept name
#                 mapping_types_and_names = [
#                     ('BROADER_TERM', broaderConceptName, broaderConceptUri),
#                     ('NARROWER_TERM', narrowerConceptName, narrowerConceptUri),
#                     ('RELATED_TERM', relatedConceptName, relatedConceptUri),
#                 ]
                
#                 for relation_type, mappingConceptLabel, mappingConceptUri in mapping_types_and_names:
#                     if mappingConceptLabel:
#                         create_or_update_concept(session, mappingConceptLabel, mappingConceptUri)
#                         query = f"""
#                         MATCH (a:Concept {{name: '{concept_name}'}})
#                         MATCH (b:Concept {{name: '{mappingConceptLabel}'}})
#                         MERGE (a)-[:{relation_type}]->(b)
#                         """
#                         # session.run(query)

#     def get_related_entity_property(self, related_entity_name):
#         # Get the related entity structure from the JSON structure
#         related_entity_structure = self.structure.get(related_entity_name, {})
#         # Get the first property defined for the related entity
#         property_name = related_entity_structure.get("properties", [{}])[0].get("property_name")
#         return property_name

#     def build_knowledge_graph(self, directory_path):        

#         # Walking through each subdirectory in the specified directory
#         for root_dir, sub_dirs, files in os.walk(directory_path):
#             for file_name in files:
#                 if file_name.endswith('.xml'):
                    
#                     file_path = os.path.join(root_dir, file_name)
#                     with open(file_path, 'r', encoding='utf-8') as file:
#                         jats_xml = file.read()
                    
#                     # Parse the XML data to get the root element
#                     root = ET.fromstring(jats_xml)
                    
#                     # Extract the pan_number from the XML
#                     pan_number = root.find(".//article-id[@pub-id-type='CABI-pan']").text

#                     # Dynamic XML Parsing and Cypher Query Construction
#                     for entity_name, entity_structure in self.structure.items():
#                         entity = entity_structure["entity"]

#                         # If there are properties defined, construct property queries
#                         for property_mapping in entity_structure.get("properties", []):
#                             xml_tag = property_mapping["xml_tag"]
#                             property_name = property_mapping["property_name"]
                            
#                             element = root.find(f".//{xml_tag}")
#                             if element is not None:
#                                 element_text = element.text
#                                 with self.driver.session() as session:
#                                     query = f"""
#                                     MATCH (n:{entity} {{PAN_number: '{pan_number}'}})
#                                     SET n.{property_name} = '{element_text}'
#                                     """
#                                     # session.run(query)
                        
#                         # If there are relations defined, construct relation queries
#                         for relation_mapping in entity_structure.get("relations", []):
#                             relation_type = relation_mapping["relation_type"]
#                             xml_tag = relation_mapping["xml_tag"]
#                             related_entity = relation_mapping.get("related_entity")
#                             sparql_query = relation_mapping.get("sparql_query", False)

#                             # Find related entities using the specified XML tag
#                             related_elements = root.findall(f".//{xml_tag}")

#                             for related_element in related_elements:
#                                 if related_element is not None:
#                                     related_element_text = related_element.text

#                                     # Identify the type of the concept based on the vocab attribute
#                                     vocab_type = related_element.attrib.get('vocab', None)

#                                     # Get the correct property to use in the query
#                                     related_property_name = self.get_related_entity_property(related_entity_name=related_entity)

#                                     # If SPARQL query is needed, fetch concept hierarchy and build relations dynamically
#                                     if sparql_query:
#                                         # Add or update concept in the Knowledge Graph
#                                         self.add_or_update_concept_kg(related_element_text, pan_number, vocab_type)
#                                     else:
#                                         # Construct and execute a Cypher query to create the relationship
#                                         with self.driver.session() as session:
#                                             query = f"""
#                                             MATCH (a:{entity} {{PAN_number: '{pan_number}'}})
#                                             MATCH (b:{related_entity}) WHERE b.{related_property_name} = '{related_element_text}' 
#                                             MERGE (a)-[:{relation_type}]->(b)
#                                             """
#                                             # session.run(query)


# kg_builder = KnowledgeGraphBuilder(structure)
# kg_builder.build_knowledge_graph(JATS_DATA_DIRECTORY_PATH)
# kg_builder.close()



