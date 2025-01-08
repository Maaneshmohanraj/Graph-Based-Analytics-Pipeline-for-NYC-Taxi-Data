import pyarrow.parquet as pq
import pandas as pd
from neo4j import GraphDatabase

class DataLoader:
    def __init__(self, uri, user, password):
        """
        Initialize the connection to the Neo4j database.
        """
        self.driver = GraphDatabase.driver(uri, auth=(user, password), encrypted=False)
        self.driver.verify_connectivity()

    def close(self):
        """
        Close the connection to the Neo4j database.
        """
        self.driver.close()

    def load_transform_file(self, file_path):
        """
        Load the parquet file, filter the data, and transform it for Neo4j.
        """
        # Load the data from the parquet file
        trips = pq.read_table(file_path).to_pandas()

        # Filter columns and clean data
        trips = trips[['tpep_pickup_datetime', 'tpep_dropoff_datetime', 'PULocationID', 'DOLocationID', 'trip_distance', 'fare_amount']]
        bronx = [3, 18, 20, 31, 32, 46, 47, 51, 58, 59, 60, 69, 78, 81, 94, 119, 126, 136, 147, 159, 167, 168, 169, 174, 
                 182, 183, 184, 185, 199, 200, 208, 212, 213, 220, 235, 240, 241, 242, 247, 248, 250, 254, 259]
        trips = trips[trips['PULocationID'].isin(bronx) & trips['DOLocationID'].isin(bronx) & (trips['trip_distance'] > 0.1) & (trips['fare_amount'] > 2.5)]

        # Convert date-time columns to standard datetime format
        trips['tpep_pickup_datetime'] = pd.to_datetime(trips['tpep_pickup_datetime'])
        trips['tpep_dropoff_datetime'] = pd.to_datetime(trips['tpep_dropoff_datetime'])

        # Load data into Neo4j
        with self.driver.session() as session:
            # Create Location nodes
            for location_id in set(trips['PULocationID']).union(set(trips['DOLocationID'])):
                session.run("MERGE (l:Location {name: $name})", name=int(location_id))

            # Create Trip relationships
            for _, row in trips.iterrows():
                session.run(
                    """
                    MATCH (start:Location {name: $PULocationID}), (end:Location {name: $DOLocationID})
                    CREATE (start)-[:TRIP {
                        trip_distance: $trip_distance,
                        fare_amount: $fare_amount,
                        pickup_dt: $pickup_dt,
                        dropoff_dt: $dropoff_dt
                    }]->(end)
                    """,
                    PULocationID=int(row['PULocationID']),
                    DOLocationID=int(row['DOLocationID']),
                    trip_distance=float(row['trip_distance']),
                    fare_amount=float(row['fare_amount']),
                    pickup_dt=row['tpep_pickup_datetime'],
                    dropoff_dt=row['tpep_dropoff_datetime']
                )

def main():
    data_loader = DataLoader("bolt://localhost:7687", "neo4j", "project1phase1")
    try:
        data_loader.load_transform_file("/cse511/yellow_tripdata_2022-03.parquet")
    except Exception as e:
        print(f"Error loading data: {e}")
    finally:
        data_loader.close()

if __name__ == "__main__":
    main()

