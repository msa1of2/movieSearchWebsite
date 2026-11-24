from collectData import movieWalker
from collectData import xmlReader
from collectData import progress
from collectData import configParser
from datetime import datetime
from zipfile import ZipFile
import os
import re
import time
import sys
from pathlib import Path

config = {}
#Should add ['name seperator'] = '@'?
config = configParser.readFile("/var/www/movieSearchWebsite/config.json")

def sanatize(string):
    send = string.replace(";", "")
    send = send.replace(":", "")
    send = send.replace("#", "")
    send = send.replace("@", " at ")
    return send

def addFranchises(totalDict, showBar = True):
    totalCount = 0
    fileCount = 0
    startTime = time.time()
    if (showBar):
        with open(config['franchise location'], 'r') as file:
            for line in file:
                totalCount += 1

    with open(config['franchise location'], "r") as file:
        for line in file:
            if (showBar):
                fileCount += 1
                progress.printBar(fileCount, totalCount, barLength=40, timeSinceStart=startTime, timeNow=time.time())
            line = line[:-1]
            fran, targets = line.split(":")
            if targets[-1] == "*":
                #For when Im lazy and just put the directory /*
                directory = config['movie directory'] + targets[:-1]
                targets = ""
                for filePath in Path(directory).rglob("*"): #Go through every file in the directory / subdirectories
                    if (not filePath.is_file() or filePath.suffix in set(config['franchise ignore'])): #Dont include directories or files we don't want
                        continue
                    filterString = ""
                    if (Path(str(filePath)+config['data extension']).exists()): #if the tgmd file exists
                        with ZipFile(str(filePath)+config['data extension'], 'r') as zip:
                            with zip.open("NFO") as fs:
                                out = xmlReader.readFile(fs) #grab the nfo file from the tgmd file
                                filterString = movieWalker.filtersToString(out) #set the filter string
                        targets += "@" + sanatize(str(filePath)[len(directory):])+filterString #Add to franchise targets
                if targets == "": #Rare case where .tgmd files weren't found, I got no info
                    continue
                targets = targets[1:]
            if 'franchise' in totalDict.keys():
                if fran in totalDict['franchise'].keys():
                    totalDict['franchise'][fran].extend(targets.split('@')) #add to existing
                else:
                    totalDict['franchise'][fran] = targets.split('@') #add to existing
            else:
                totalDict['franchise'] = {fran: targets.split('@')} #create the franchise list
    if showBar:
        print() #moves cursor down a line

def getSeasonCount(pathDir, errorLog=None):
    seasonFileSearch = re.compile(r'[sS](\d+)[eE]')
    seasonDirSearch  = re.compile(r'[sS](?:eason[ _-]?){0,1}(\d+)')
    maxSeason = 1
    if not Path(pathDir).is_dir():
        #Does not exist or is not a directory
        if (errorLog is None):
            print(f"{pathDir} does not exist as a directory")
        else:
            errorLog.write(f"{pathDir} does not exist as a directory, this was pulled from a file name in ~/tvapi/indexTvShows/... - change the file name to fix the issue\n")
        return -1
    for file in Path(pathDir).iterdir():
        s = 0
        if (file.is_file()):
            matchRes = seasonFileSearch.search(str(file))
            if matchRes is None:
                continue
            s = int(matchRes.group(1))
        if (file.is_dir()):
            matchRes = seasonDirSearch.search(str(file))
            if matchRes is None:
                continue
            s = int(matchRes.group(1))
#        if (s == 0):
#            print("THIS FILE FAILED A MATCH", file)
        maxSeason = max(s, maxSeason)
    return maxSeason

def reverseEpisodeDict(eps, orig, valName):
    filters = movieWalker.filtersToString(orig) #Get the original filters applied to the output
    startInd = filters.find('\\d\\')+3
    start = filters[:startInd]
    endInd = filters.find('\\', startInd)
    end = filters[endInd:] if endInd != -1 else ""
    titles = {}
    runtimes = {}
    franchise = []
    for epKey in eps:
        seasonEpisode = f"#S{eps[epKey]['seasonNum']}x{eps[epKey]['number']:0>2}"
        value = valName + seasonEpisode + start + str(eps[epKey]['runtime']) + end
        titles[sanatize(eps[epKey]['name']).lower()] = value
        runtimes[eps[epKey]['runtime']] = value
        franchise.append(value)
    return titles, runtimes, franchise

def getTvCodec(parentDir, movieDir, codecExtensions=config['codec extensions']):
    #Compromises in that it only checks 1 file of this typing for its codec and assumes the all the episodes have the same codec
    for file in Path(movieDir + '/' + parentDir).rglob('*'):
        if (file.suffix in codecExtensions):
            return movieWalker.getCodec(file)
    return "Unknown"

def addTVShows(totalDict, showBar = True):
    dir = Path(config['tv data directory'])
    writeTo = config['write location'] + '/local'
    movieDir = config['movie directory']
    totalCount = 0
    currCount = 0
    startTime = time.time()

    errorLog = open("./tvShowError.log", 'w+')

    if (showBar):
        for filePath in dir.rglob("*.tvs"):

            totalCount+=1

    for filePath in dir.rglob("*.tvs"):
        out = {}
        try:
            with open(filePath, 'r') as f:
                out = xmlReader.readFile(f)
        except Exception as e:
            errorLog.write(str(e) + "\n")
        if showBar:
            currCount += 1
            progress.printBar(currCount, totalCount, barLength=40, timeSinceStart=startTime, timeNow=time.time())
        #Change the indexed seasons to match what is present on our servers
        seasons = getSeasonCount(movieDir + '/' + out['loc'], errorLog=errorLog)
        if (seasons == -1):
            errorLog.write(f"Seasons returned -1 on file {filePath}\n")
        epData = {}
        extraEps = 0
        totalEps = 0
        if 'episodeData' in out and out['episodeData'] is not None:
            out['seriesTitle'] = out['title'].lower()
            out['title'] = []
            out['runtime'] = []
            for epKey in out['episodeData']:
                totalEps += 1
                if 'seasonNum' not in out['episodeData'][epKey] or out['episodeData'][epKey]['seasonNum'] is None:
                    errorLog.write(f"Episode number {epKey} of {out['seriesTitle']} does not have a season number\n")
                    continue
                if int(out['episodeData'][epKey]['seasonNum']) > seasons: #If episode season count is more than our seasons
                    extraEps += 1 # Accumulate the count of non-additions
                    errorLog.write(f"Episode number {epKey} of {out['seriesTitle']} has a season number of {out['episodeData'][epKey]['seasonNum']} when it should have no more than {seasons}\n")
                    continue
                out['title'].append(sanatize(out['episodeData'][epKey]['name']).lower())
                out['runtime'].append(out['episodeData'][epKey]['runtime'])
            epData = out['episodeData'].copy()
            del out['episodeData']
        if 'genres' in out:
            out['genre'] = out['genres']
            del out['genres']
        if 'studios' in out:
            out['studio'] = out['studios']
            del out['studios']
        if 'homepage' in out:
            del out['homepage']
        if 'actors' in out:
            out['actor'] = out['actors']
            del out['actors']
        if 'certification' in out:
            out['certification'] = movieWalker.standardMpaa(out['certification'])
        if 'seriesTitle' in out:
            out['franchise'] = out['seriesTitle']
        out['seasons'] = str(seasons)
#        out['codec'] = getTvCodec(out['loc'], movieDir)
        if 'episodes' in out:
            out['episodes'] = str( int(out['episodes']) - extraEps )
        else:
            out['episodes'] = str(totalEps - extraEps)
        reversed = xmlReader.reverseDict(out, out['loc']+ "/"+filePath.stem +movieWalker.filtersToString(out), startFrom=0, isShow = False)
        titles, runtimes, episodeList = reverseEpisodeDict(epData, out, out['loc'] + "/" + filePath.stem)
        reversed['title'] = titles
        reversed['runtime'] = runtimes
        if 'seriesTitle' in out:
            reversed['franchise'] = {out['seriesTitle'] : episodeList}
#        movieWalker.unionAdd(reversed, reverseEpisodes)
        movieWalker.unionAdd(totalDict, reversed)
    if showBar:
        print() #moves cursor down a line
    errorLog.close()

if __name__ == '__main__':
    total = {}
    debug = False
    quietMode = False
    getCodecs = True
    addingFlags = ['m','f','t']
    addingResults = [True] * len(addingFlags)

    """
    Possible Flags:
    -d Execute in Debug mode
    -q Don't print any outputs
    -c Don't get codecs
    -m Don't get movies
    -f Don't get franchises
    -t Don't get tv shows
    The reindexer will completely erase all data of previous indexing operations before adding the new info, so if the -m flag is used, the final ouput will not contain movie data
    """

    if (len(sys.argv) > 1):
        args = sys.argv[1:]
        for arg in args:
            if arg[0] == '-':
                arg = arg[1:]
            arg = set(list(arg))
            if 'd' in arg:
                debug = True
            if 'q' in arg:
                quietMode = True
            if 'c' in arg:
                getCodecs = False
            for item in arg:
                if item in addingFlags:
                    addingResults[addingFlags.index(item)] = False

    if not quietMode:
        print("Started reindexing")

    if addingResults[0]:
        if not quietMode:
            print("Started indexing movies")
        total = movieWalker.walkDir(config['movie directory'], writeTo = config['write location'] + '/local', prefix = config['movie prefix'], codecDirectories=config['codec grabbing'], progressBar=not quietMode, getCodecs=getCodecs)
        if not quietMode:
            print("Movies finished")

    if addingResults[1]:
        if not quietMode:
            print("Started Franchises")

        addFranchises(total, showBar = not quietMode)

        if not quietMode:
            print("Franchises added")

    if addingResults[2]:
        if not quietMode:
            print("Started Tv Shows")

        addTVShows(total, showBar = not quietMode)

        if not quietMode:
            print("Tv shows finished")

    if (debug):
        if not quietMode and False:
            import pprint
            pprint.pprint(total)
            pprint.pprint(config)

        movieWalker.writeOut(total, config['write location'] + '/testing', ignoreWriting = set(['homepage', 'showTitle', 'filename', 'originaltitle']))
        sys.exit(0)

    movieWalker.writeOut(total, config['write location'], ignoreWriting = set(["homepage", "showTitle", 'filename', 'originaltitle']))

    with open("./lastIndex", "w+") as file:
    	file.write("Index finished: " + datetime.now().strftime("%Y-%m-%d %H:%M:%S"))

    if 'codec' in total:
        with open("./codecs", 'w+') as file:
            xmlReader.writeFile(file, {'codec': total['codec'].keys()})

    print("All done")
