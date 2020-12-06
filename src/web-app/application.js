//#region public API

//returns all machines from the database/cache in JSON format
async function getMachinesFromDatabaseOrCache(){
	const key = 'machines'
	let cachedData = await getFromCache(key)

	if(caachedData) {
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

//returns a specific machine from the database/cache in JSON format
async function getMachineFromDatabaseOrCache(id){
	const key = "machine_" + id
	let cachedData = await getFromCache(key)

	if(cachedData){
		console.log(`Found machine in cache ${cachedData}`)
		return cachedData
	}
	else {
		console.log(`Machine with id ${id} not found in cache, reading data from database`)

		let result = await executeQuery("SELECT * FROM Machines WHERE Id = ?",[id])
		let data = result.fetchOne();

		if(data){
			let jsonData = JSON.stringify(_machineAsJson(data));

			console.log(`Got machine data from database ${jsonData}, storing data in cache`)
			if(memcached){
				await memcached.set(key, jsonData, cacheTimeSecs)
			}

			return jsonData
		} 
		else {
			throw `No data for machine with id ${id} found`
		}
	}
}

//returns all failures from the database/cache in JSON format
async function getFailuresFromDatabaseOrCache(){
	const key = 'failures'
	let cachedData = await getFromCache(key)

	if(caachedData) {
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
function reportFailurePart(failurePart){

	console.log(`Send tracking message with failure part ${failurePart} to kafka`)

	sendTrackingMessage(failurePart)
		.then(()=> console.log("Send message to kafka"))
		.catch(e => console.log("Failed to send message to kafka due to the error", e))
}

//returns failure parts statistic from database (no cache)
function getFailurePartStatistic(){

}

//#endregion

//#region helper functions

//extracts sql result into json format
function _machineAsJson(data){
	return {
		id: data[0],
		name: data[1],
		max_x: data[2],
		may_y: data[3]
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

//#endregion