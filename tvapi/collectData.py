import xmltodict
import os
import sys
import tvdb_v4_official
import addLoc
from progress import printBar
import time
tvdb = tvdb_v4_official.TVDB("2509e363-01dc-4d1f-b0f9-5f1fd60910d2")
#get_countries
#get_all_companies
#get_series
#get_series_by_slug - by url friendly name
#get_series_episodes
#get_all_seasons
#get_season_extended
#get_all_genres
#get_all_people
#get_person_extended
#search

def getActors(characters):
    return [ tvdb.get_person(character['peopleId'])['name'] for character in characters ]

def getSeasonCount(seasonIn):
    count = 0
    for season in seasonIn:
        if 'type' in season.keys() and 'name' in season['type'].keys() and season['type']['name'] == "Aired Order":
            count+=1
    return count

def sanatize(string):
    send = string.replace(":", "")
    send = send.replace(";", "")
    send = send.replace("@", " at ")
    send = send.replace("\\", "")
    return send

def asciiAlias(out, alt=""):
    if alt != "" and alt.isascii():
        return alt
    if 'aliases' not in out:
        return out['name']
    for alias in out['aliases']:
        if alias['language'] == 'eng':
            return alias['name']
    return out['name']

def getEnglishName(out):
    if 'translations' not in out:
        return asciiAlias(out, out['name'])
    for nameDict in out['translations']['nameTranslations']:
        if nameDict['language'] == 'eng':
            return asciiAlias(out, nameDict['name'])
    return asciiAlias(out, out['name'])

def addEpisodeData(data, toAdd, typeName = "Aired Order"):
    directors = set()
    writers = set()
    seasonCount = 0
    seasonIds = []
    episodeCount = 0
    episodeNames = set()
    episodeData = {}
    for season in data['seasons']:
#        print(season['type'])
        if 'type' in season.keys() and 'name' in season['type'].keys() and season['type']['name'] == typeName and season['number'] > 0:
            seasonCount+=1
            seasonIds.append(season['id'])
    if seasonCount == 0:
        return
    currSeasonNum = 1
    seasonStartTime = time.time()
    for id in seasonIds:
        print(f"\rSeason ", end="")
        epStartTime = time.time()
        printBar(currSeasonNum, seasonCount, timeSinceStart=seasonStartTime, timeNow=epStartTime, clearLine=False)
        print() #To move to the episode progress bar
        currSeasonNum += 1

        season = tvdb.get_season_extended(id)

        currEpNum = 1
        for ep in season["episodes"]:
            print("\r Episode ", end="")
            printBar(currEpNum, len(season['episodes']), timeSinceStart = epStartTime, timeNow = time.time(), clearLine = False)
            currEpNum += 1

            episode = tvdb.get_episode_extended(ep['id'], meta='translations')
            name = getEnglishName(episode)
            if (episode['absoluteNumber'] <= 0):
                continue
            epDirs = set()
            epWrite = set()
            if episode['characters'] != None:
                for person in episode['characters']:
                    if person['peopleType'].lower() == "director":
                        epDirs.add(person['personName'])
                    if person['peopleType'].lower() == "writer":
                        epWrite.add(person['personName'])
            directors |= epDirs
            writers |= epWrite
            episodeNames.add(sanatize(name))
            episodeData[f"episode{episode['absoluteNumber']:03}"] = {"director": list(epDirs)}
            dir = episodeData[f"episode{episode['absoluteNumber']:03}"]
            dir['writers'] = list(epWrite)
            dir['number'] = episode['number']
            dir['runtime'] = episode['runtime']
            dir['seasonNum'] = episode['seasonNumber']
            dir['name'] = sanatize(name)
        print("\r\033[K\033[A", end="") #Moves the cursor to the season count of the series (up 1)
    #toAdd['episodes'] = len(episodeNames)
    #toAdd['title'].extend(list(episodeNames))
    toAdd['director'] = list(directors)
    toAdd['writers'] = list(writers)
    toAdd['seasons'] = seasonCount
    toAdd['episodeData'] = episodeData

    print()
    print("\r\033[K\033[A") #Removes the series progress, to remove progress altogether add a '2' before the 'A'

def parseSeriesExtended(out, seasonType = "Aired Order"):
    send = {'id' : out['id']}
    send['releasedate'] = out['firstAired']
    send['title'] = getEnglishName(out)
    send['year'] = out['firstAired'][:4] #stored in yyyy-mm-dd format from api
    send['country'] = out['originalCountry']
    send['runtime'] = out['averageRuntime']
    send['studio'] = [ company['name'] for company in out['companies'] ]
    send['genre'] = [ genre['name'] for genre in out['genres'] ]
    send['actor'] = getActors(out['characters'])
#    send['seasons'] = getSeasonCount(out['seasons'])
    send['certification'] = out['contentRatings'][0]['name'] if len(out['contentRatings']) > 0 else None
    addEpisodeData(out, send, typeName = seasonType)
    return send

def getSeriesIds(filename = "./tvShows.txt", toWrite = "./tvShowsIds.txt"):
    with open(filename, 'r') as file:
        with open(toWrite, 'w+') as write:
            for line in file:
                line = line.strip()
                res = tvdb.search(query = line)
                for d in res:
                    print(d['id'])
                    write.write(str(d['id']) + ":" + line + "\n")

def getSeriesInfo(filename="./tvShowsIds.txt", type="series", writeDir = "./indexTvShows", seasonType = "Aired Order"):
    seriesCount = 0
    currSeriesNum = 1
    with open(filename, 'r') as ids:
        seriesCount = sum(1 for _ in ids)
    with open(filename, 'r') as ids:
        seriesStartTime = time.time()
        for line in ids:
            line = line.strip()
            id = -1

#            print(f"\rSeries ", end="")
 #           printBar(currSeriesNum, seriesCount, timeSinceStart=seriesStartTime, timeNow=time.time(), clearLine=False)
  #          print() #To move to the series progress bar
   #         currSeriesNum += 1

            if ('-' in line):
                lineTarget, name = line.split('-')
                if (lineTarget != type):
                    continue
                id, name = name.split(":")
                print(f"\rWorking on {name} ", end = "")
            else:
                try:
                    id = int(line)
                except:
                    print(f"Line failed, wanted it to start '{type}-(id)' or just '(id)', got '{line}'")
                    continue
                print(f"\rWoring on tv series, id: {id} ", end = "")

#            print(f"\rSeries ", end="")
            printBar(currSeriesNum, seriesCount, timeSinceStart=seriesStartTime, timeNow=time.time(), clearLine=False)
            print() #To move to the series progress bar
            currSeriesNum += 1

            res = tvdb.get_series_extended(id, meta="translations")
            series = parseSeriesExtended(res, seasonType = seasonType)
            if '-' not in line:
                name = series['title']
            os.makedirs(writeDir + "/" + name, exist_ok = True)
 #           import pprint
  #          pprint.pprint(series)
            with open(writeDir + "/" + name + "/" + series['title'] + ".tvs", 'w+') as file:
                file.write(xmltodict.unparse({"movie" : series}))

            if currSeriesNum <= seriesCount:
                print("\r\033[K\033[2A", end="")
            else:
                print("\r\033[K\033[A", end="")
    addLoc.addLoc() #adds the location tags based on the file's position

if __name__ == "__main__":
    if (len(sys.argv) < 2):
        print("Add usage type\ngetid - gets the ids from tvShows.txt and writes it to tvShowsIds.txt\ngetdata - gets the ids from tvShowsIds.txt and writes to the indexTVShows Directory, optionally add season type to specifiy DVD Order, Aired, or Absolute season type")
        sys.exit(0)
    if (sys.argv[1].lower() == "getid"):
        getSeriesIds()
        print("got ids")
    elif (sys.argv[1].lower() == "getdata"):
        seasonType = "DVD Order"
        if (len(sys.argv) > 2):
            seasonType = sys.argv[2]
            print(f"Going after a season type of {seasonType}")
        print("Starting series getting")
        getSeriesInfo(filename = "./tvShowsIds.txt", type="series", writeDir = "./indexTvShows", seasonType = seasonType)
        print("\r\033[KAll done")
    elif (sys.argv[1].lower() =='test'):
        print("HI:)")
 #       import pprint
#        pprint.pprint(tvdb.get_series_extended(78660))
    else:
        print("Command not recognized")
