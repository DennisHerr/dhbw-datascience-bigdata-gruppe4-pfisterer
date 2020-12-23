
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

#Path for saving the raw data on HDFS
partsPath = "hdfs://my-hadoop-cluster-hadoop-hdfs-nn:9000/parts"
#Path for saving the chackpoints during streaming
checkPath = "hdfs://my-hadoop-cluster-hadoop-hdfs-nn:9000/checkpoint/"

#-----------------help funciton
def getShift(date):
    if (date.hour >= 0 and date.hour < 8 ):
        return 1
    elif (date.hour < 16):
        return 2
    elif (date.hour < 24):
        return 3
    else:
        return 0 

from pyspark.sql.types import IntegerType
#create UDF to get a shift from a datetime
udf_to_shift = udf(lambda z: getShift(z), IntegerType())


# Create a spark session
spark = SparkSession.builder \
    .appName("Structured Streaming").getOrCreate()

# Set log level
spark.sparkContext.setLogLevel('WARN')


# Read messages from Kafka
kafkaMessages = spark \
    .readStream \
    .format("kafka") \
    .option("kafka.bootstrap.servers",
            "my-cluster-kafka-bootstrap:9092") \
    .option("subscribe", "tracking-data") \
    .option("startingOffsets", "earliest") \
    .load()


# Define schema of rating data
ratingMessageSchema = StructType() \
    .add("machine", IntegerType()) \
    .add("failure", IntegerType()) \
    .add("posx", IntegerType()) \
    .add("posy", IntegerType()) \
    .add("timestamp", IntegerType())


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

print('Write raw data into HDFS')
ratingMsgVal.writeStream.format("csv").outputMode('Append').option("path", partsPath).option("checkpointLocation", checkPath).start()

#Add column wirh corresponding shift to timestamp
ratingMsgShift = ratingMsgVal.withColumn("shift", udf_to_shift(col("parsed_timestamp")))
#Add column with corresponding date from timestamp
ratingMsgDate = ratingMsgShift.withColumn("date", (col("parsed_timestamp").cast("date")))


#Grouping the failures over Date and shift for the evaluation
ratingGrouped = ratingMsgDate.groupBy(
    window(
        column("parsed_timestamp"),
        windowDuration,
        slidingDuration
    ),
    column("date"),
    column("shift"),
    column("failure")
).count().withColumnRenamed('count', 'cnt')




# Start running the query; print running counts to the console

consoleDump = ratingGrouped \
    .writeStream \
    .trigger(processingTime=slidingDuration) \
    .outputMode("update") \
    .format("console") \
    .option("truncate", "false") \
    .start()



#Write the processed statistics to the database
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
            sql.bind(row.shift, row.failure, row.cnt, row.date.strftime('%Y-%m-%d'), row.cnt).execute()

        session.close()

    # Perform batch UPSERTS per data partition
    batchDataframe.foreachPartition(save_to_db)

#Stream and write into database
dbInsertStream = ratingGrouped.writeStream \
    .trigger(processingTime=slidingDuration) \
    .outputMode("update") \
    .foreachBatch(saveToDatabase) \
    .start()

# Wait for termination
spark.streams.awaitAnyTermination()
