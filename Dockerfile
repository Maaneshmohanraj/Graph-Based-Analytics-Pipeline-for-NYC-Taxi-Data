# Base image: ubuntu:22.04
FROM ubuntu:22.04

# ARGs
ARG TARGETPLATFORM=linux/amd64,linux/arm64
ARG DEBIAN_FRONTEND=noninteractive

# Install Java 17 and other dependencies
RUN apt-get update && \
    apt-get install -y wget gnupg software-properties-common && \
    add-apt-repository -y ppa:openjdk-r/ppa && \
    apt-get update && \
    apt-get install -y openjdk-17-jdk

# Install Neo4j
RUN wget -O - https://debian.neo4j.com/neotechnology.gpg.key | apt-key add - && \
    echo 'deb https://debian.neo4j.com stable latest' > /etc/apt/sources.list.d/neo4j.list && \
    add-apt-repository universe && \
    apt-get update && \
    apt-get install -y nano unzip neo4j=1:5.5.0 python3-pip && \
    apt-get autoremove -y && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/* /tmp/* /var/tmp/*

# Create the /cse511 directory
RUN mkdir /cse511

# Download the NYC Taxi dataset and the data_loader.py file
RUN wget -O /cse511/yellow_tripdata_2022-03.parquet \
    https://d37ci6vzurychx.cloudfront.net/trip-data/yellow_tripdata_2022-03.parquet
COPY data_loader.py /cse511/

# Install required Python packages
RUN pip3 install --upgrade pip && \
    pip3 install neo4j pandas pyarrow

# Configure Neo4j
RUN echo "dbms.security.procedures.unrestricted=gds.*" >> /etc/neo4j/neo4j.conf && \
    echo "dbms.connector.bolt.listen_address=0.0.0.0:7687" >> /etc/neo4j/neo4j.conf && \
    echo "dbms.connector.http.listen_address=0.0.0.0:7474" >> /etc/neo4j/neo4j.conf && \
    echo "dbms.default_listen_address=0.0.0.0" >> /etc/neo4j/neo4j.conf && \
    echo "dbms.directories.import=import" >> /etc/neo4j/neo4j.conf && \
    echo "dbms.security.auth_enabled=false" >> /etc/neo4j/neo4j.conf && \
    echo "dbms.memory.heap.initial_size=1G" >> /etc/neo4j/neo4j.conf && \
    echo "dbms.memory.heap.max_size=2G" >> /etc/neo4j/neo4j.conf

# Install Neo4j GDS Plugin
RUN wget -P /var/lib/neo4j/plugins \
    https://graphdatascience.ninja/neo4j-graph-data-science-2.3.1.jar

# Set proper permissions
RUN chown -R neo4j:neo4j /var/lib/neo4j /var/log/neo4j

# Run the data loader script
RUN chmod +x /cse511/data_loader.py && \
    neo4j start && \
    sleep 30 && \
    python3 /cse511/data_loader.py && \
    neo4j stop

# Expose neo4j ports
EXPOSE 7474 7687

# Start neo4j service and show the logs
CMD ["neo4j", "console"]
