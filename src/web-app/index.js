const os = require('os')
const dns = require('dns').promises
const { program: optionparser } = require('commander')
const { Kafka } = require('kafkajs')
const mysqlx = require('@mysql/xdevapi');
const MemcachePlus = require('memcache-plus');
const express = require('express')

const app = express()
const cacheTimeSecs = 15
const numberOfMissions = 30

// -------------------------------------------------------
// Command-line options
// -------------------------------------------------------

let options = optionparser
	.storeOptionsAsProperties(true)
	// Web server
	.option('--port <port>', "Web server port", 3000)
	// Kafka options
	.option('--kafka-broker <host:port>', "Kafka bootstrap host:port", "my-cluster-kafka-bootstrap:9092")
	.option('--kafka-topic-tracking <topic>', "Kafka topic to tracking data send to", "tracking-data")
	.option('--kafka-client-id < id > ', "Kafka client ID", "tracker-" + Math.floor(Math.random() * 100000))
	// Memcached options
	.option('--memcached-hostname <hostname>', 'Memcached hostname (may resolve to multiple IPs)', 'my-memcached-service')
	.option('--memcached-port <port>', 'Memcached port', 11211)
	.option('--memcached-update-interval <ms>', 'Interval to query DNS for memcached IPs', 5000)
	// Database options
	.option('--mysql-host <host>', 'MySQL host', 'my-app-mysql-service')
	.option('--mysql-port <port>', 'MySQL port', 33060)
	.option('--mysql-schema <db>', 'MySQL Schema/database', 'popular')
	.option('--mysql-username <username>', 'MySQL username', 'root')
	.option('--mysql-password <password>', 'MySQL password', 'mysecretpw')
	// Misc
	.addHelpCommand()
	.parse()
	.opts()

// -------------------------------------------------------
// Database Configuration
// -------------------------------------------------------

const dbConfig = {
	host: options.mysqlHost,
	port: options.mysqlPort,
	user: options.mysqlUsername,
	password: options.mysqlPassword,
	schema: options.mysqlSchema
};

async function executeQuery(query, data) {
	let session = await mysqlx.getSession(dbConfig);
	return await session.sql(query, data).bind(data).execute()
}

async function executeQuery(query) {
	let session = await mysqlx.getSession(dbConfig);
	return await session.sql(query).execute()
}

// -------------------------------------------------------
// Memache Configuration
// -------------------------------------------------------

//Connect to the memcached instances
let memcached = null
let memcachedServers = []

async function getMemcachedServersFromDns() {
	try {
		// Query all IP addresses for this hostname
		let queryResult = await dns.lookup(options.memcachedHostname, { all: true })

		// Create IP:Port mappings
		let servers = queryResult.map(el => el.address + ":" + options.memcachedPort)

		// Check if the list of servers has changed
		// and only create a new object if the server list has changed
		if (memcachedServers.sort().toString() !== servers.sort().toString()) {
			console.log("Updated memcached server list to ", servers)
			memcachedServers = servers

			//Disconnect an existing client
			if (memcached)
				await memcached.disconnect()

			memcached = new MemcachePlus(memcachedServers);
		}
	} catch (e) {
		console.log("Unable to get memcache servers", e)
	}
}

//Initially try to connect to the memcached servers, then each 5s update the list
getMemcachedServersFromDns()
setInterval(() => getMemcachedServersFromDns(), options.memcachedUpdateInterval)

//Get data from cache if a cache exists yet
async function getFromCache(key) {
	if (!memcached) {
		console.log(`No memcached instance available, memcachedServers = ${memcachedServers}`)
		return null;
	}
	return await memcached.get(key);
}

// -------------------------------------------------------
// Kafka Configuration
// -------------------------------------------------------

// Kafka connection
const kafka = new Kafka({
	clientId: options.kafkaClientId,
	brokers: [options.kafkaBroker],
	retry: {
		retries: 0
	}
})

const producer = kafka.producer()

// Send tracking message to Kafka
async function sendTrackingMessage(data) {

	console.log(JSON.stringify(data));

	//Ensure the producer is connected
	await producer.connect()

	//Send message
	await producer.send({
		topic: options.kafkaTopicTracking,
		messages: [
			{ value: JSON.stringify(data) }
		]
	})
}

// -------------------------------------------------------
// Request handler 
// ------------------------------------------------------

app.use(express.static('materialize'));
app.use(express.json());
app.set('view engine', 'ejs');

// Return HTML for start page
app.get("/", (req, res) => {

	console.log("#GET REQUEST RECEIVED");

	//promise is important -> otherwise the JSON data is may not available in the ejs template
	Promise.all([getMachinesFromDatabaseOrCache(), getFailuresFromDatabaseOrCache()]).then(data => {
		//it is important to use <%- %> int he ejs template otherwise the unicode of the JSON data is printed
		res.render("index", { machinesData: data[0], failuresData: data[1] }); 
	});
})

// Receive http post with selected failure in JSON
app.post("/", (req, res) => {

	console.log("#POST REQUEST RECEIVED");
	console.log(req.body);

	//send tracking message to Kafa
	reportFailurePart(req.body, Math.floor(new Date() / 1000));

	//TODO -> should we send a response to the client? -> callback in client is already available
})

// Receive http post with selected statistic parameters in JSON
app.post("/Statistic", (req, res) => {

	console.log("#POST REQUEST RECEIVED: url /Statistic");
	console.log(req.body);

	//promise is important -> otherwise the JSON data is may not available
	Promise.all([getFailurePartStatistic(req.body.Shift, req.body.Date)]).then(data => {
		//send statistic in JSON format to client
		res.send(data[0]);
	});
})

app.post("/Random", (req, res) => {

	console.log("#POST REQUEST RECEIVED: url /Random");
	console.log(req.body);
	
	var days = req.body.Days;
	if(days <= 0)
	return;
	
	Promise.all([getMachinesFromDatabaseOrCache(), getFailuresFromDatabaseOrCache()]).then(data => {
		createRandomData(days, data);
	});
})

// -------------------------------------------------------
// Main method
// -------------------------------------------------------

app.listen(options.port, function () {
	console.log("Node app is running at http://localhost:" + options.port)
});

// -------------------------------------------------------
// Service/application methods
// -------------------------------------------------------

//returns all machines from the database/cache in JSON format
async function getMachinesFromDatabaseOrCache(){
	const key = 'machines'
	let cachedData = await getFromCache(key)

	if(cachedData) {
		console.log(`Found machines in cache ${cachedData}`)
		return cachedData
	}
	else {
		console.log(`Machines not found in cache, reading data from database`)

		let result = await executeQuery("SELECT * FROM Machines", [])
		let data = result.fetchAll()

		if(data) {
			let jsonData = JSON.stringify(data.map(_machineAsJson))

			console.log(`Got machines data from database ${jsonData}, storing data in cache`)
			if(memcached){
				await memcached.set(key, jsonData, cacheTimeSecs)
			}

			return jsonData
		}
		else {
			return `No machines data found`
		}
	}
}

//returns all failures from the database/cache in JSON format
async function getFailuresFromDatabaseOrCache(){
	const key = 'failures'
	let cachedData = await getFromCache(key)

	if(cachedData) {
		console.log(`Found failures in cache ${cachedData}`)
		return cachedData
	}
	else {
		console.log(`Failures not found in cache, reading data from database`)

		let result = await executeQuery("SELECT * FROM Failures", [])
		let data = result.fetchAll()

		if(data) {
			let jsonData = JSON.stringify(data.map(_failureAsJson))

			console.log(`Got failures data from database ${jsonData}, storing data in cache`)
			if(memcached){
				await memcached.set(key, jsonData, cacheTimeSecs)
			}

			return jsonData
		}
		else {
			return `No failures data found`
		}
	}
}

//sends a tracking message to kafka to process the reported failure part
/*
   `Fault_Parts` (
      `Id_Machine` BIGINT NOT NULL,
      `Id_Failure` BIGINT NOT NULL,
      `Pos_X` BIGINT NOT NULL,
      `Pos_Y` BIGINT NOT NULL,
      `Rated_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP, -> must be set on web server side
	);
	
	the parameter failurePart is a JSON object with the elements Id_Machine, Id_Failure, Pos_X and Pos_Y
*/
function reportFailurePart(failurePart, date){

	console.log(`Send tracking message with failure part ${failurePart} to kafka`)

	let jsonData = {
		machine: failurePart.Id_Machine,
		failure: failurePart.Id_Failure,
		posx: failurePart.Pos_X,
		posy: failurePart.Pos_Y,
		timestamp: date
	}

	sendTrackingMessage(jsonData)
		.then(()=> console.log("Send message to kafka"))
		.catch(e => console.log("Failed to send message to kafka due to the error", e))
}

//returns failure parts statistic from database (no cache)
/*
* shift: 1= Frühschicht, 2= Spätschicht, 3= Nachtschicht
* date format: 2020-12-10 -> yyyy-mm-dd
*
* return [{id_failure:4, count:20, date:'2020-12-10', shift=1}, ...]
*/
async function getFailurePartStatistic(shift, date){
	console.log(`Reading failure part statistic data from database`)

	let result = await executeQuery(`SELECT * FROM Shift_Statistics WHERE Shift = ${shift} AND Date = '${date}'`)
	let data = result.fetchAll()

	if(data) {
		let jsonData = JSON.stringify(data.map(_shiftStatisticAsJson));

		console.log(`Got failures part statistic data from database ${jsonData}`)

		return jsonData
	}
	else {
		consolse.log(`No failure part statistic data found`)
		return []
	}
}

//creates a random number of failures for the last days (including today) and transmits them to kafka
async function createRandomData(days, data){
	//create random data for the last i days
	for(var i = days-1; i >= 0; i--){
	
		//get i days before today
		var date = new Date();
		date.setDate(date.getDate()-i);
		
		//get random number of failures to be set -> 50-80
		var failureCnt = _getRandomInt(30) + 50;

		//parse database data
		var machinesData = JSON.parse(data[0]);
		var failureData = JSON.parse(data[1]);

		for(var j = 0; j < failureCnt; j++)
		{
			//set random values 
			var machineIndex = _getRandomInt(machinesData.length-1);
			var failureIndex = _getRandomInt(failureData.length-1);
			var xpos = _getRandomInt(machinesData[machineIndex].max_x);
			var ypos = _getRandomInt(machinesData[machineIndex].max_y);
			var hours = _getRandomInt(24);
			date.setHours(hours);

			var jsonData = {
				Id_Machine: machinesData[machineIndex].id,
				Id_Failure: failureData[failureIndex].id,
				Pos_X: xpos,
				Pos_Y: ypos
			}

			//report random failure
			console.log("Send random failure data " + JSON.stringify(jsonData));
			reportFailurePart(jsonData, Math.floor(date / 1000));
		}
	}
}

//extracts sql result into json format
function _machineAsJson(data){
	return {
		id: data[0],
		name: data[1],
		max_x: data[2],
		max_y: data[3]
	}
}

//extracts sql result into json format
function _failureAsJson(data){
	return {
		id: data[0],
		name: data[1],
		description: data[2]
	}
}

//extracts sql result into json format
function _shiftStatisticAsJson(data){
	return {
		id_failure: data[0],
		count: data[1],
		date: data[2],
		shift: data[3]
	}
}

//returns a random integer
function _getRandomInt(max) {
	return Math.floor(Math.random() * Math.floor(max));
}