from pyspark.sql import SparkSession
from pyspark.sql.functions import *
from pyspark.sql.types import IntegerType, StringType, StructType, TimestampType
import mysqlx
from datetime import datetime


dbOptions = {"host": "my-app-mysql-service", 'port': 33060, "user": "root", "password": "mysecretpw"}
dbSchema = 'popular'
windowDuration = '5 minutes'
slidingDuration = '1 minute'

# Example Part 1
# Create a spark session
spark = SparkSession.builder \
    .appName("Structured Streaming").getOrCreate()

# Set log level
spark.sparkContext.setLogLevel('WARN')
print('#######################################################################################')
print('#############neuer lauf' , datetime.now())

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


""" # Define schema of tracking data
trackingMessageSchema = StructType() \
    .add("mission", StringType()) \
    .add("timestamp", IntegerType()) """


#sends a tracking message to kafka to process the reported failure part

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

#OLD-------------------------------------------------------------------------------------
# Example Part 3
# Convert value: binary -> JSON -> fields + parsed timestamp
""" trackingMessages = kafkaMessages.select(
    # Extract 'value' from Kafka message (i.e., the tracking data)
    from_json(
        column("value").cast("string"),
        trackingMessageSchema
    ).alias("json")
).select(
    # Convert Unix timestamp to TimestampType
    from_unixtime(column('json.timestamp'))
    .cast(TimestampType())
    .alias("parsed_timestamp"),

    # Select all JSON fields
    column("json.*")
) \
    .withColumnRenamed('json.mission', 'mission') \
    .withWatermark("parsed_timestamp", windowDuration).printSchema()
print('nachrichten holen') """

#-------------------------------------------------------------------------------------------------
# Example Part 3
# Convert value: binary -> JSON -> fields + parsed timestamp
ratingMessages = kafkaMessages.select(
    # Extract 'value' from Kafka message (i.e., the tracking data)
    from_json(
        column("value").cast("string"),
        ratingMessageSchema
    ).alias("json")
)
jasonmsg= ratingMessages.select(
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
print('JSON konvertiert')
ratingMessages.printSchema() 




#--------OLD----------------------------------------------------------------
# Example Part 4
# Compute most popular slides
""" popular = trackingMessages.groupBy(
    window(
        column("parsed_timestamp"),
        windowDuration,
        slidingDuration
    ),
    column("mission")
).count().withColumnRenamed('count', 'views') """

#^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

# Example Part 4
# Compute most popular slides
failures = jasonmsg.groupBy(
    window(
        column("parsed_timestamp"),
        windowDuration,
        slidingDuration
    ),
    column("machine"),
    column("failure")
   # column("failure")
).count().withColumnRenamed('count', 'faulty')

print('ist gruppiert')

# Example Part 5
# Start running the query; print running counts to the console
""" consoleDump = popular \
    .writeStream \
    .trigger(processingTime=slidingDuration) \
    .outputMode("update") \
    .format("console") \
    .option("truncate", "false") \
    .start() """

consoleDump = failures \
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
            sql = session.sql("INSERT INTO popular "
                              "(mission, count) VALUES (?, ?) "
                              "ON DUPLICATE KEY UPDATE count=?")
            sql.bind('' ,1, 1).execute()

        session.close()

    # Perform batch UPSERTS per data partition
    batchDataframe.foreachPartition(save_to_db)

# Example Part 7

print('streame jetzt')

dbInsertStream = failures.writeStream \
    .trigger(processingTime=slidingDuration) \
    .outputMode("update") \
    .foreachBatch(saveToDatabase) \
    .start()

# Wait for termination
spark.streams.awaitAnyTermination()
