from neo4j import GraphDatabase

class Neo4jHelper:
    def __init__(self, settings):
        self.settings = settings
        self.driver = GraphDatabase.driver(self.settings.Neo4J_URL, auth=(self.settings.Neo4J_UserName, self.settings.Neo4J_Password), database=self.settings.Neo4J_Database)
        
    def close(self):
        self.driver.close()

    def article_exists_by_pan_and_source(self, pan, source):
        query = (
            "MATCH (n:PublishingDataChunk) "
            "WHERE n.document_type='article' AND n.pan = $pan AND n.source = $source "
            "RETURN count(n) as cnt"
        )
        with self.driver.session() as session:
            result = session.run(query, pan=pan, source=source)
            count = result.single()["cnt"]
        return count > 0

    def concept_exists_by_name_and_source(self, name, source):
        query = (
            "MATCH (n:PublishingDataChunk) "
            "WHERE n.document_type='concept' AND n.title = $name AND n.source = $source "
            "RETURN count(n) as cnt"
        )
        with self.driver.session() as session:
            result = session.run(query, name=name, source=source)
            count = result.single()["cnt"]
        return count > 0

    def fetch_sources_for_ngrams(self, ngrams):
        query = (
            "UNWIND $ngrams as ngram "
            "MATCH (n:PublishingDataChunk) "
            "WHERE n.document_type='concept' AND toLower(n.title) = toLower(ngram) "
            "RETURN ngram, COLLECT(n.source) as sources"
        )

        with self.driver.session() as session:
            result = session.run(query, ngrams=list(ngrams))
            # For each ngram, only take the first source (if multiple exist)
            sources_map = {record["ngram"]: record["sources"][0] for record in result if record["sources"]}

        return sources_map

    def fetch_related_nodes_and_relations(self, collection):
        with self.driver.session() as session:
            return session.write_transaction(self._fetch_related_nodes_and_relations, collection)

    @staticmethod
    def _fetch_related_nodes_and_relations(tx, collection):
        query = """
        UNWIND $data AS d
        MATCH (n)
        WHERE n.source = d.source
        OPTIONAL MATCH (n)-[r]->(connected)
        RETURN 
            n.title AS NodeTitle, 
            n.source AS NodeSource, 
            n.document_type AS NodeDocType,
            type(r) AS RelationType,
            connected.title AS ConnectedTitle, 
            connected.source AS ConnectedSource, 
            connected.document_type AS ConnectedDocType
        """
        results = tx.run(query, data=collection['articles'] + collection['concepts'])
        
        nodes_and_relations = []
        for record in results:
            node = {
                'title': record['NodeTitle'],
                'source': record['NodeSource'],
                'document_type': record['NodeDocType']
            }
            
            relation = {
                'type': record['RelationType']
            } if record['RelationType'] else None

            connected_node = {
                'title': record['ConnectedTitle'],
                'source': record['ConnectedSource'],
                'document_type': record['ConnectedDocType']
            } if record['ConnectedTitle'] else None

            nodes_and_relations.append({
                'node': node,
                'relation': relation,
                'connected_node': connected_node
            })

        return nodes_and_relations