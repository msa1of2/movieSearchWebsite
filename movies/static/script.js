//Set dark or light mode depending on browser setting
const isDarkMode = window.matchMedia('(prefers-color-scheme: dark)').matches;
let movies = {};
let focused = {};
let appendMode=false;
let goodColor = 'green';
let okayColor = 'orange';
let badColor = 'red';
document.body.style.backgroundColor = isDarkMode ? "black" : "white";
document.body.style.color = isDarkMode ? "white" : "black";
if (!isDarkMode){
	const style = document.documentElement.style;
	style.setProperty('--off-color', '#505050');
	style.setProperty('--bkg-color', '#f0f0f0');
	style.setProperty('--frg-color', '#000000');
	style.setProperty('--off-bkg-color', '#d0d0d0');
	goodColor = '#00ff00';
	okayColor = '#ffac00';
	badColor = '#ff0000';
}
sourceColors = {
	'lightMode':{
		'title': '#00ff00',
		'actor': '#00ffbb',
		'director': '#ff8000',
		'genre': '#00ffff',
		'franchise': '#ff00ff',
		'tagline': '#ff0000',
		'loc': '#ffbb00',
	},
	'darkMode':{
		'title': '#005000',
		'actor': '#006050',
		'director': '#603000',
        'genre': '#008080',
        'franchise': '#800080',
        'tagline': '#800000',
		'loc': '#705000',
	}
}

function searchToColors(name){
	name = name.toLowerCase();
	if (name == 'location') name = 'loc';
	return name;
}
const searchSettings = document.querySelectorAll('input[type="checkbox"][id^=st]');
searchSettings.forEach(option => {
	if (option.labels.length <= 0) return;
	if (searchToColors(option.labels[0].textContent) in sourceColors[isDarkMode?'darkMode':'lightMode']){
        option.parentElement.style.backgroundColor = sourceColors[isDarkMode?'darkMode':'lightMode'][searchToColors(option.labels[0].textContent)];
    }
});

//For Fetch calls
const targetUrl = new URL(window.location.href);

//For showing the throbber
const loader = document.getElementById("loader");

let previousSearch = null;

function clearTable(table){
	while (table.rows.length > 2){
		table.deleteRow(1);
	}
	for (let i=0;i<table.rows[0].cells.length;i++){
		table.rows[1].cells[i].innerText="-";
	}
	table.rows[1].className="void";
	movies={};
	focused={};
	onFocusChange();
}

function addRow(rowArray, table){
	if (table.rows[1].className === "void"){
		table.deleteRow(1);
	}
	const row = table.insertRow(-1);
	for (let i=0;i<table.rows[0].cells.length;i++){
		const cell = row.insertCell(-1);
		if (rowArray.length > i) { cell.innerText = rowArray[i]; }
		else cell.innerText="-";
	}
	return row;
}

function locationToName(loc){
	let name = loc.split("/");
	name = name[name.length-(name[name.length-1].includes("#")?1:2)];
	if (!name) return "NAME PARSING FAILED-----------------------------------------------------------------------------------------------------------------------------";
	if (name.includes("(")){
		const open = name.indexOf("(");
		const close = name.indexOf(")");
		name = name.substring(0, open) + name.substring(close+1);
	}
	if (name.includes("[")){
		const open = name.indexOf("[");
		const close= name.indexOf("]");
		name = name.substring(0, open) + name.substring(close+1);
	}
	if (name.includes(".mdd")){
		let ind = name.indexOf(".mdd");
		name = name.substring(0, ind) + name.substring(ind+4);
	}
	if (!name.includes("#")) return name.trim();
	ind = name.indexOf("#");
	return (name.substring(0, ind) + " - " + name.substring(ind+1)).trim();
}

function cleanLocation(loc){
	let ind = loc.lastIndexOf("/");
	return loc.substring(0, ind).trim();
}

function logData(data, table, searchString = "Search Results"){
	if (!appendMode){
		clearTable(table);
	}
	if (data.hasOwnProperty("error")){
		addRow(['ERROR:', data['error'], 'Error'], table);
		return;
	}
	const extension = ".mdd";
	let count = 0;
	for (const source of Object.keys(data['results'])){
		count += data['results'][source].length;
		for (let j=0;j<data['results'][source].length;j++){
			if (typeof data['results'][source][j] === "string"){
				let value = data['results'][source][j] + extension;
				let location = value;
				let season = -1;
				let episode = -1;
				if (data['results'][source][j].includes("#")){
					value = data['results'][source][j];
					location = value.substring(0, value.indexOf("#")) + extension;
					const start = value.indexOf("#");
					season = Number(value.substring(value.indexOf("S", start)+1, value.indexOf("x", start)));
					episode= Number(value.substring(value.indexOf("x", start)+1, value.indexOf(" - ", start) != -1 ? value.indexOf(" - ", start) : value.length));
				}
				const name = locationToName(value);
				const row = addRow([name, cleanLocation(value), source], table);
				row.id = "movie"+count+j;
				if (source in sourceColors[isDarkMode?'darkMode':'lightMode']){
					row.style.backgroundColor = sourceColors[isDarkMode?'darkMode':'lightMode'][source];
				}
				movies[row.id] = {
					'gotData': false,
					'data':{},
					'loc':location,
					'season':season,
					'episode':episode
				};
			}
		}
	}
	times = data['timings'];
	if (times == null) return;
	const extractTime = (Number(times['End Extraction']) - Number(times['start'])) / 1e9;
	table.caption.textContent = searchString + " - " + extractTime.toFixed(2) + "s - " + count + " movie" + (count > 1 ? "s":"");
}

function setUlElements(list, array){
	if (array == null) return;
	for (let i=0;i<array.length;i++){
		const newItem = document.createElement('li');
		newItem.textContent = array[i];
		list.appendChild(newItem);
	}
}

function setFocusedMovieVisible(toggleValue){
	const parentDiv = document.getElementById('focused-movie');
	if (toggleValue){
		if (history.state && !history.state.movieOpen) history.pushState({movieOpen: true}, "", null);
		parentDiv.style.display="block";
		return;
	}
	parentDiv.style.display="none";
}

function setElementInnerText(element, text, hideInstead=false, extraFunc = ()=>{}){
	if (hideInstead){
		element.style.display = "none";
		return;
	}
	element.style.display = "";
	element.innerText = text;
	extraFunc();
}

function setElementListItems(element, singularName, pluralName, displayItems) {
	if (displayItems == null){
		element.style.display = 'none';
		return;
	}
	element.style.display = "";
	if (typeof displayItems === 'string'){
		element.querySelector('summary').textContent = singularName;
		const list = element.querySelector('ul');
		list.innerHTML = `<li>${displayItems}</li>`; //clears the old list
	}
	else{
		element.querySelector('summary').textContent = pluralName;
		const list = element.querySelector('ul');
		list.innerHTML = ``; //clears the old list
		setUlElements(list, displayItems);
	}
}

function setDropdownList(element, title, obj, keys = [], names=[]){
	//showInfo, focused['showTitle'], focused, ['episodesnames', 'seasons' 'episodes', 'loc', 'year']
	if (title == null){
		element.style.display = 'none';
		return;
	}
	element.style.display = '';
	element.querySelector('summary').textContent = title;
	if (keys.length == 0){
		for (const key of Object.keys(obj)){
			keys.push(key);
		}
	}
	const superList = element.querySelector('ul');
	while (superList.firstChild){
		superList.removeChild(superList.firstChild);
	}
	for (let i=0;i<keys.length;i++){
		const key = keys[i];
		if (Array.isArray(obj[key])){
			const newDrop = document.createElement('details');
			const newDropSum = document.createElement('summary');
			newDrop.appendChild(newDropSum);
			newDropSum.textContent = i<names.length?names[i]:key;
			superList.appendChild(newDrop);
			const list = document.createElement('ul');
			newDrop.appendChild(list);
			setUlElements(list, obj[key]);
		}
		else{
			const newLine = document.createElement('h2');
			newLine.textContent = (i<names.length?names[i]:key) + ": " + obj[key];
			superList.appendChild(newLine);
		}
	}
}

function onFocusChange(){
	const parentDiv = document.getElementById('focused-movie');
	if (Object.keys(focused).length === 0){
		setFocusedMovieVisible(false);
		return;
	}
	setFocusedMovieVisible(true);

	const title = document.getElementById('title');
	const tagline = document.getElementById('tagline');
	const runtime = document.getElementById('runtime');

	if (Object.hasOwn(focused, 'data') && Object.hasOwn(focused['data'], 'error')){
		setElementInnerText(title, focused['data']['error'], false);
		setElementInnerText(tagline, focused['data']['reason'], false);
		setElementInnerText(runtime, focused['data']['data'], false);
	}
	else{
		setElementInnerText(title, focused['title'], focused['title'] == null);

		setElementInnerText(tagline, focused['tagline'], focused['tagline'] == null);

		setElementInnerText(runtime, "Placeholder", focused['runtime'] == null,
			extraFunc = () => {
				let mins = Number.parseFloat(focused['runtime']);
				const hrs = (mins/60) | 0; //drops the decimal
				mins%=60;
				runtime.innerText = `${hrs} hr ${mins} mins`;
			});
	}
	const year = document.getElementById('year');
	setElementInnerText(year, focused['year'], focused['year'] == null);

	const mpaa = document.getElementById('certification');
	setElementInnerText(mpaa, focused['certification'], focused['certification'] == null);

	const codec = document.getElementById('codecDisplay');
	setElementInnerText(codec, "Codec: " + focused['codec'], focused['codec'] == null);

	const metascore = document.getElementById('metascore');
	setElementInnerText(metascore, "Metascore: " + focused['metascore'] + " / 100", focused['metascore'] == null,
		extraFunc = () => {
			const val = Number(focused['metascore']);
			if (val >= 81) metascore.style.backgroundColor = goodColor;
			else if (val >= 40) metascore.style.backgroundColor=okayColor;
			else metascore.style.backgroundColor=badColor;
		});

	const rating = document.getElementById('rating');
	setElementInnerText(rating, "Rating: " + focused['rating'] + "/10", focused['rating'] == null,
		extraFunc = () => {
			const val = Number(focused['rating']);
			if (val >= 8) rating.style.backgroundColor=goodColor;
			else if (val >= 4) rating.style.backgroundColor=okayColor;
			else rating.style.backgroundColor=badColor;
		});

	const director = document.getElementById('director');
	setElementListItems(director, "Director", "Directors", focused['director']);

	const actor = document.getElementById('actor');
	setElementListItems(actor, "Actor", "Actors", focused['actor'])

	const writer = document.getElementById('writers');
	setElementListItems(writer, "Writer", "Writers", focused['writers'])

	const guestStars = document.getElementById('guestStars');
	setElementListItems(guestStars, "Guest Star", "Guest Stars", focused['guestStars'])

	const genre = document.getElementById('genre');
	setElementListItems(genre, "Genre", "Genres", focused['genre'])

	const id = document.getElementById('id');
	setElementInnerText(id, focused['id'], focused['id'] == null);

	const country = document.getElementById('country');
	setElementListItems(country, "Country", "Countries", focused['country'])

	const studio = document.getElementById('studio');
	setElementListItems(studio, "Studio", "Studios", focused['studio'])

	const showInfo = document.getElementById('show-info');
	setDropdownList(showInfo, focused['showTitle'], focused, ['seasons', 'episodes', 'loc', 'year', 'episodesnames'], ['Seasons', 'Episodes', 'Location', 'Year', 'Episode Names']);
}

async function setMovieFocused(row){
	console.log(row.id);
	collection = movies[row.id];
	if (collection == null) return;
	if (collection['gotData']){
		focused = collection['data'];
		onFocusChange();
		return;
	}
	collection['gotData'] = true;
	collection['data'] = await getFilmData(collection['loc'], collection['season'], collection['episode']);
	collection['data']['title'] = row.cells[0].innerText;
	focused = collection['data'];
	onFocusChange();
}

async function getFilmData(value, season, episode){
	loader.classList.add('show');
	if (!season) season = -1;
	if (!episode) episode= -1;
	try{
		const res = await fetch("http://"+targetUrl.hostname+"/data/get/"+season+"/"+episode+"/"+value, {
			method: 'GET',
			headers: { 'Content-Type': 'application/json' },
		});
		if (!res.ok){
			if (res.status === 404) return {'title':'Error - 404', 'data':{'error' : "File not found", 'reason': 'The location saved was not a valid location of data', 'data' : value}}
		}
		const data = await res.json();
		return data;
	} catch (error) {
		console.error("Error Getting data:", error);
	} finally{
		loader.classList.remove('show');
	}
	return {};
}

async function onSearch(table){
	loader.classList.add('show');
	const toSend = {};
	
	const searchBox = document.getElementById('search');
	toSend["search"] = searchBox.value.toLowerCase();
	searchBox.value = "";

	if (toSend['search'] === "" && previousSearch != null) toSend['search'] = previousSearch; //If no search in box, just search the next one
	else previousSearch = toSend['search'];

	searchBox.placeholder = previousSearch;

	if (toSend['search'].includes("*") && toSend['search'].length > 1){ //its a wild card, but targeting filters
		toSend['filterSearch'] = toSend['search'].split("*").slice(1).map(element => element.trim() );
	}
	
	const checkedBoxes = document.querySelectorAll('input[type="checkbox"][id^=st]:checked');
	const checkValues = [];
	// Loop through the NodeList to grab the values
	checkedBoxes.forEach(checkbox => {
		checkValues.push(checkbox.name);
	});
	
	toSend["searchSettings"] = checkValues;
	
	filters = {};
	
	const checkedFilterBoxes = document.querySelectorAll('input[type="checkbox"][id^="mpaaSt"]:checked');
	const checkFilterValues = [];
	// Loop through the NodeList to grab the values
	checkedFilterBoxes.forEach(checkbox => {
		checkFilterValues.push(checkbox.name.toLowerCase());
	});
	//checkFilterValues.push("Approved"); //Weird classifiers - given to user
	filters["searchMpaa"] = checkFilterValues;

	const codecFilterBoxes = document.querySelectorAll('input[type="checkbox"][id^="codecSt"]:checked');
	const codecFilterValues = [];
	codecFilterBoxes.forEach(checkbox => {
		codecFilterValues.push(checkbox.name.toLowerCase());
	});
	filters['codec'] = codecFilterValues;

	filters["metascore"] = {'min':document.getElementById('stMetascoreMin').value,
							'max':document.getElementById('stMetascoreMax').value};
	
	filters["rating"] = {'min':document.getElementById('stRatingMin').value,
						'max':parseFloat(document.getElementById('stRatingMax').value).toFixed(1)};
	
	filters["runtime"] = {'min':document.getElementById('stRuntimeMin').value,
						  'max':document.getElementById('stRuntimeMax').value};
	
	toSend['filters'] = filters;

	try{
		const res = await fetch("http://"+targetUrl.hostname+":8000", {
			method: 'POST',
			headers: { 'Content-Type': 'application/json' },
			body: JSON.stringify(toSend)
		});
		const data = await res.json();
		logData(data, table, toSend['search']);
	} catch (error) {
		console.error("Error Getting data:", error);
	} finally{
		loader.classList.remove('show');
	}
}

function setMinValue(event, input){
	input.min = event.target.value;
	keepWithinBounds(input);
}

function setMaxValue(event, input){
	input.max = event.target.value;
	keepWithinBounds(input);
}

function keepWithinBounds(input){
	if (parseFloat(input.value) > parseFloat(input.max)){
		input.value = input.max;
	}
	if (parseFloat(input.value) < parseFloat(input.min)){
		input.value = input.min;
	}
}

function minToReadable(event, label){
	let mins = Number(event.target.value);
	const hrs = (mins/60) | 0; //drops the decimal
	mins %= 60;
	label.innerText = `${hrs} hr ${mins} min`;
}

function logCodecs(codecObj, codecDiv){
	for (const codec of codecObj){
		const newCodecDiv = document.createElement('div');
		codecDiv.appendChild(newCodecDiv);
		const newCodecBox = document.createElement('input');
		newCodecBox.setAttribute('type', 'checkbox');
		newCodecBox.setAttribute('id', 'codecSt' + codec);
		newCodecBox.setAttribute('name', codec);
		newCodecBox.checked = true;
		newCodecDiv.appendChild(newCodecBox);
        const newCodecLabel = document.createElement('label');
        newCodecLabel.setAttribute('for', 'codecSt'+codec);
		newCodecLabel.textContent = codec;
		newCodecDiv.appendChild(newCodecLabel);
	}
}

function sendIndexPwd(){
	const bar = document.getElementById('index-movies')
	fetch("http://"+targetUrl.hostname+":8000", {
		method: 'POST',
		headers: {'Content-type' : 'application/json' },
		body: JSON.stringify({'index-key': bar.value})
	});
	bar.value="";
}

const resultsTable = document.getElementById('output');
resultsTable.addEventListener('click', function(event){
	const row = event.target.closest('tr');
	if (!row) return;
	setMovieFocused(row);
});

const button = document.getElementById('search-button');
button.addEventListener('click', () => onSearch(resultsTable));

const searchBar = document.getElementById('search');
searchBar.addEventListener('keydown', function(event){
	if (event.key === 'Enter'){
		event.preventDefault();
		onSearch(resultsTable);
	}
});

const indexBar = document.getElementById('index-movies');
indexBar.addEventListener('keydown', function(event){
	if (event.key === 'Enter'){
		event.preventDefault();
		sendIndexPwd();
	}
});

const closeBtn = document.getElementById('close-button');
closeBtn.addEventListener('click', () => setFocusedMovieVisible(false));

const clear = document.getElementById('clear');
clear.addEventListener('click', () => clearTable(resultsTable));

const runtimeFilterMin = document.getElementById('stRuntimeMin');
const runtimeFilterMinLabel = document.getElementById("runtimeMinLabel");

const runtimeFilterMax = document.getElementById('stRuntimeMax');
const runtimeFilterMaxLabel = document.getElementById("runtimeMaxLabel");

runtimeFilterMin.addEventListener('input', (event) => minToReadable(event, runtimeFilterMinLabel));
//runtimeFilterMin.addEventListener('change', (event) => setMinValue(event, runtimeFilterMax)); //really buggy behaviour, this and below when combined
//runtimeFilterMin.addEventListener('input', (event) => keepWithinBounds(this));

runtimeFilterMax.addEventListener('input', (event) => minToReadable(event, runtimeFilterMaxLabel));
//runtimeFilterMax.addEventListener('change', (event) => setMaxValue(event, runtimeFilterMin));
//runtimeFilterMax.addEventListener('input', (event) => keepWithinBounds(this));

const appendBtn = document.getElementById("append-table");
appendBtn.addEventListener('click', () => {
	appendMode = !appendMode;
});

const lastIndexLabel = document.getElementById('lastIndex')
fetch("http://"+targetUrl.hostname+":8000", {
	method: 'POST',
	headers: { 'Content-Type': 'application/json' },
	body: JSON.stringify({'last-index':'time request'})
})
.then(res => {obj = res.json(); return obj;})
.then(data => {
	lastIndexLabel.textContent = data['last-index'];
})
.catch(error=> {console.error("error:", error.message) });

const codecDiv = document.getElementById('codec');
fetch("http://"+targetUrl.hostname+"/data/get/codecs", {
	method: 'GET',
	headers: { 'Content-Type': 'application/json' },
})
.then(res => {obj = res.json(); return obj;})
.then(obj => {logCodecs(obj, codecDiv);})
.catch(error=> {console.error("error:", error.message) });

window.addEventListener('popstate', (event) => {
	if (event.state && event.state.movieOpen) setFocusedMovieVisible(true);
	else setFocusedMovieVisible(false);
});
window.addEventListener('keydown', (event) => {
	if (event.key === "Escape") setFocusedMovieVisible(false);
});

window.addEventListener('DOMContentLoaded', () => {
	if (history.state) {
		history.replaceState({movieOpen: false}, "", null);
	}
	history.pushState({movieOpen: false}, "", null);
});

const searchToggle = document.getElementById("allSearchTypes");
searchToggle.addEventListener('change', (event) => {
	const searchBoxes = document.querySelectorAll('input[type="checkbox"][id^=st]');
	// Loop through the NodeList to grab the values
	searchBoxes.forEach(searchbox => {
		searchbox.checked = event.target.checked;
	});
});

const filterToggle = document.getElementById("allFiltersToggle");
filterToggle.addEventListener('change', (event) => {
	const searchBoxes = document.querySelectorAll('input[type="checkbox"][id^=mpaaSt]');
	// Loop through the NodeList to grab the values
	searchBoxes.forEach(searchbox => {
		searchbox.checked = event.target.checked;
	});
});

const codecToggle = document.getElementById("allCodecsToggle");
codecToggle.addEventListener('change', (event) => {
	const codecBoxes = document.querySelectorAll('input[type="checkbox"][id^=codecSt]');
	codecBoxes.forEach(box => {
		box.checked = event.target.checked
	});
});

const debugButton = document.getElementById("debugButton");
if (debugButton != null){
	debugButton.addEventListener("click", () => {
		getFilmData("TV/Aeon Flux/Aeon Flux.mdd");
	});
}
