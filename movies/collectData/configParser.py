import json

def sanatize(val: str):
	if val[-1] == '/':
		val = val[:-1]
	return val

def sanatizeValues(data: dict):
	for key, value in data.items():
		if isinstance(value, str):
			data[key] = sanatize(value)
			continue
		if isinstance(value, list):
			out = []
			for item in value:
				out.append(sanatize(item))
			data[key] = out
			continue
		if isinstance(value, dict):
			data[key] = sanatizeValues(value)
	return {k: v for k, v in data.items() if k[0] != "_"}

def readFile(fileLocation):
	send = {
		'codec extensions': ['.mp4', '.mov', '.mkv', '.avi', '.m4v'],
		'data extension': '.tgmd',
		'franchise ignore': ['.tgmd',
		                  '.jpg',
		                  '.srt',
		                  '.sub',
		                  '.idx',
		                  '.exe',
		                  '.txt',
		                  '.nfo'],
		'movie directory': '/mnt/saturn/backup',
		'tv data directory': '/home/turtl/tvapi/indexTvShows',
		'write location': '/var/www/html/data'
	}
	with open(fileLocation, 'r') as file:
		send.update(sanatizeValues(json.load(file)))
	return send

if __name__ == "__main__":
	import pprint
	pprint.pprint(readFile("/home/turtl/config.json"))
