from datetime import datetime

import mysqlx
from pyspark.sql import SparkSession
from pyspark.sql.functions import *
from pyspark.sql.functions import udf
from pyspark.sql.types import IntegerType
from pyspark.sql.types import (IntegerType, StringType, StructType,
                               TimestampType)

dbOptions = {"host": "my-app-mysql-service", 'port': 33060,
             "user": "root", "password": "mysecretpw"}
dbSchema = 'popular'
windowDuration = '5 minutes'
slidingDuration = '1 minute'

partsPath = "hdfs://my-hadoop-cluster-hadoop-hdfs-nn:9000/parts"
checkPath = "hdfs://my-hadoop-cluster-hadoop-hdfs-nn:9000/checkpoint/"

#-----------------help funciton
def getShift(date):
    print(date)
    print(date.hour)
    if (date.hour >= 0 and date.hour < 8 ):
        return 1
    elif (date.hour < 16):
        return 2
    elif (date.hour < 24):
        return 3
    else:
        return 0 

from pyspark.sql.types import IntegerType
udf_to_shift = udf(lambda z: getShift(z), IntegerType())

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
testi = ratingMsgVal.withColumn("shift", udf_to_shift(col("parsed_timestamp")))
"""query = testi.writeStream.format("console").start()
import time
time.sleep(10) # sleep 10 seconds
query.stop()
 """
# Example Part 4
# Compute most popular slides

ratingGrouped = testi.groupBy(
    window(
        column("parsed_timestamp"),
        windowDuration,
        slidingDuration
    ),
    column("shift"),
    column("failure")
).count().withColumnRenamed('count', 'cnt')

""" ratingGrouped = ratingMsgVal.groupBy(
    window(
        column("parsed_timestamp"),
        windowDuration,
        slidingDuration
    ),
    column("machine"),
    column("failure")
).count().withColumnRenamed('count', 'cnt') """

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
            sql = session.sql("INSERT INTO Shift_Statistics "
                              "(Shift, Id_Failure, Count, Date) VALUES (?,?,?,?) "
                              "ON DUPLICATE KEY UPDATE Count=?")
            sql.bind(row.shift, row.failure, row.cnt, datetime.today().strftime('%Y-%m-%d'), row.cnt).execute()

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
