from datetime import datetime

import mysqlx
from pyspark.sql import SparkSession
from pyspark.sql.functions import *
from pyspark.sql.types import (IntegerType, StringType, StructType,
                               TimestampType)

dbOptions = {"host": "my-app-mysql-service", 'port': 33060,
             "user": "root", "password": "mysecretpw"}
dbSchema = 'popular'
windowDuration = '5 minutes'
slidingDuration = '1 minute'

partsPath = "hdfs://my-hadoop-cluster-hadoop-hdfs-nn:9000/parts"
checkPath = "hdfs://my-hadoop-cluster-hadoop-hdfs-nn:9000/checkpoint/"

# Example Part 1
# Create a spark session
spark = SparkSession.builder \
    .appName("Structured Streaming").getOrCreate()

# Set log level
spark.sparkContext.setLogLevel('WARN')
print('#######################################################################################')
print('#############neuer lauf', datetime.now())

# Example Part 2
# Read messages from Kafka
kafkaMessages = spark \
    .readStream \
    .format("kafka") \
    .option("kafka.bootstrap.servers",
            "my-cluster-kafka-bootstrap:9092") \
    .option("subscribe", "tracking-data") \
    .option("startingOffsets", "earliest") \
    .load()



# sends a tracking message to kafka to process the reported failure part

"""    `Fault_Parts` (
      `Id_Machine` BIGINT NOT NULL,
      `Id_Failure` BIGINT NOT NULL,
      `Pos_X` BIGINT NOT NULL,
      `Pos_Y` BIGINT NOT NULL,
      `Rated_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP, -> web server
    ); """

# Define schema of rating data
ratingMessageSchema = StructType() \
    .add("machine", IntegerType()) \
    .add("failure", IntegerType()) \
    .add("posx", IntegerType()) \
    .add("posy", IntegerType()) \
    .add("timestamp", IntegerType())

print('Struct angelegt')


# Example Part 3
# Convert value: binary -> JSON -> fields + parsed timestamp
ratingMessages = kafkaMessages.select(
    # Extract 'value' from Kafka message (i.e., the tracking data)
    from_json(
        column("value").cast("string"),
        ratingMessageSchema
    ).alias("json")
)
ratingMsgVal = ratingMessages.select(
    # Convert Unix timestamp to TimestampType
    from_unixtime(column('json.timestamp'))
    .cast(TimestampType())
    .alias("parsed_timestamp"),

    # Select all JSON fields
    column("json.*")
) \
    .withColumnRenamed('json.machine', 'machine') \
    .withColumnRenamed('json.failure', 'failure') \
    .withColumnRenamed('json.posx', 'posx') \
    .withColumnRenamed('json.posy', 'posy') \
    .withWatermark("parsed_timestamp", windowDuration)
print('Schreibe in HDFS')

#initDF = jasonmsg.writeStream.format("csv").outputMode('Append').option("path", partsPath).option("checkpointLocation", checkPath).start()


# Example Part 4
# Compute most popular slides
ratingGrouped = ratingMsgVal.groupBy(
    window(
        column("parsed_timestamp"),
        windowDuration,
        slidingDuration
    ),
    column("machine"),
    column("failure")
).count().withColumnRenamed('count', 'cnt')

print('ist gruppiert')

# Example Part 5
# Start running the query; print running counts to the console


consoleDump = ratingGrouped \
    .writeStream \
    .trigger(processingTime=slidingDuration) \
    .outputMode("update") \
    .format("console") \
    .option("truncate", "false") \
    .start()

# Example Part 6


def saveToDatabase(batchDataframe, batchId):
    # Define function to save a dataframe to mysql

    def save_to_db(iterator):
        # Connect to database and use schema
        session = mysqlx.get_session(dbOptions)
        session.sql("USE popular").execute()

        for row in iterator:
            print('REIHE', str(row))
            # Run upsert (insert or update existing)
            sql = session.sql("INSERT INTO faults "
                              "(Id_Machine, Id_Failure, count) VALUES (?, ?,?) "
                              "ON DUPLICATE KEY UPDATE count=?")
            #print(row.machine, row.failure, row.count, row.count)
            sql.bind(row.machine, row.failure, row.cnt, row.cnt).execute()

        session.close()

    # Perform batch UPSERTS per data partition
    batchDataframe.foreachPartition(save_to_db)

# Example Part 7


print('streame jetzt')

dbInsertStream = ratingGrouped.writeStream \
    .trigger(processingTime=slidingDuration) \
    .outputMode("update") \
    .foreachBatch(saveToDatabase) \
    .start()

# Wait for termination
spark.streams.awaitAnyTermination()
