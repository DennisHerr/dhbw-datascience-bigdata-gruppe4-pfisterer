
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
function reportFailurePart(failurePart){

	console.log(`Send tracking message with failure part ${failurePart} to kafka`)

	let currentTimestamp = new Date().toJSON().slice(0, 19).replace('T', ' ')
	let jsonData = {
		Id_Machine: failurePart.Id_Machine,
		Id_Failure: failurePart.Id_Failure,
		Pos_X: failurePart.Pos_X,
		Pos_Y: failurePart.Pos_Y,
		Rated_at: currentTimestamp
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
function getFailurePartStatistic(shift, date){
	console.log(`Reading failure part statistic data from database`)

	let result = await executeQuery("SELECT * FROM Shift_Statistics WHERE Shift == ? AND Date == '?'", [shift, date])
	let data = result.fetchAll()

	if(data) {
		let jsonData = JSON.stringify(data.map(_shiftStatisticAsJson))

		console.log(`Got failures part statistic data from database ${jsonData}`)

		return jsonData
	}
	else {
		return `No failure part statistic data found`
	}
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

//extracts sql result into json format
function _shiftStatisticAsJson(data){
	return {
		id_failure: data[0],
		count: data[1],
		date: data[2],
		shift: data[3]
	}
}

//#endregion