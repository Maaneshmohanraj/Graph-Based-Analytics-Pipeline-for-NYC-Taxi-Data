from neo4j import GraphDatabase

class Interface:
    def __init__(self, uri="bolt://localhost:7687", user="neo4j", password="project1phase2"):
        self._driver = GraphDatabase.driver(uri, auth=(user, password), encrypted=False)
        try:
            # Verify connectivity to the Neo4j server
            self._driver.verify_connectivity()
            print("Successfully connected to Neo4j.")
        except Exception as e:
            print(f"Error connecting to Neo4j: {e}")
            raise


    def close(self):
        self._driver.close()

    def bfs(self, start_node, last_node):
        with self._driver.session() as session:
            result = session.run("""
                MATCH (start:Location {name: $start_node}), (end:Location {name: $last_node})
                MATCH path = shortestPath((start)-[:TRIP*]-(end))
                RETURN [node IN nodes(path) | {name: node.name}] AS path
            """, start_node=int(start_node), last_node=int(last_node))
            record = result.single()
            if record and record["path"]:
                return [{"path": record["path"]}]
            else:
                return []



    def pagerank(self, max_iterations, weight_property):
        with self._driver.session() as session:
            try:
                session.run(f"""
                    CALL gds.graph.project.cypher(
                        'myGraph',
                        'MATCH (n:Location) RETURN id(n) AS id',
                        'MATCH (n:Location)-[r:TRIP]->(m:Location) RETURN id(n) AS source, id(m) AS target, r.{weight_property} AS weight'
                    )
                """)

                result = session.run(f"""
                    CALL gds.pageRank.stream('myGraph', {{
                        maxIterations: {max_iterations},
                        relationshipWeightProperty: 'weight'
                    }})
                    YIELD nodeId, score
                    RETURN gds.util.asNode(nodeId).name AS name, score
                    ORDER BY score DESC
                """)

                result=[{"name": record["name"], "score": record["score"]}
                        for record in result]
                return [result[0],result[-1]]
            finally:
                # Ensure graph is dropped after the operation
                session.run("CALL gds.graph.drop('myGraph', false)")
    def get_all_records(self):
        with self._driver.session() as session:
            # Fetch all nodes and all relationships
            nodes_result = session.run("MATCH (n) RETURN n LIMIT 1000")  # Adjust LIMIT based on your data size
            relationships_result = session.run("MATCH ()-[r]->() RETURN r LIMIT 1000")  # Adjust LIMIT

            nodes = [{"node_id": record["n"].id, "node_labels": list(record["n"].labels), "node_properties": dict(record["n"].items())} 
                     for record in nodes_result]

            relationships = [{"relationship_id": record["r"].id, "start_node": record["r"].start_node.id, 
                              "end_node": record["r"].end_node.id, "relationship_type": record["r"].type, 
                              "relationship_properties": dict(record["r"].items())} 
                             for record in relationships_result]

            return {"nodes": nodes, "relationships": relationships}



if __name__ == "__main__":

    interface = Interface()
    start_node = 159
    last_node = 212
    print(f"\nRunning BFS from {start_node} to {last_node}...")
    bfs_result = interface.bfs(start_node=start_node, last_node=last_node)
    print("BFS Path:", bfs_result)

    print("Running PageRank...")
    pagerank_result = interface.pagerank(max_iterations=20, weight_property="distance")
    print("Top node by PageRank:", pagerank_result[0])
    print("Bottom node by PageRank:", pagerank_result[1])
    interface.close()
