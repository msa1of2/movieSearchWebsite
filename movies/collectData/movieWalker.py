import os
from zipfile import ZipFile
from pathlib import Path
import subprocess
import json
import time
from collections import defaultdict
from . import xmlReader
from . import movieDataReader
from . import progress

#only works with 2 layered dictionary, im not dealing with everything else
def unionAdd(send, toAdd):
    #Adds toAdd to send's items, send is modified in place
    for key in toAdd.keys():
        if (toAdd[key] is None):
            continue
        if (type(toAdd[key]) is not dict):
            print(f"I dont know how to unionAdd an element of type {type(toAdd[key])}, value {toAdd[key]}, key {key}")
            continue
        if key in send.keys():
            for item, value in toAdd[key].items():
                if item in send[key].keys():
                    if isinstance(value, list):
                        send[key][item].extend(value)
                    else:
                        send[key][item].append(value)
                else:
                    if isinstance(value, list):
                        send[key][item] = value
                    else:
                        send[key][item] = [value,]
        else:
            send[key]={}
            for item, value in toAdd[key].items():
                if isinstance(value, list):
                    send[key][item] = value
                else:
                    send[key][item] = [value,]
    return send

#master here is the dict to write out to files
def writeOut(master, writeTo=".", ignoreWriting=set()):
    for key in master.keys():
        if key in ignoreWriting:
            continue
        with open(writeTo+"/"+key+".mdr", "w+") as file:
            movieDataReader.writeFile(file, master[key])

def standardMpaa(val):
    if (val is None):
        return 'Not Rated'
    match val.lower():
        case 'unrated' | 'approved' | 'passed':
            return 'Not Rated'
        case 'tv-g' | 'ga' | 'atp' | 'u':
            return 'G'
        case 'tv-pg' | '12' | '12+':
            return 'PG'
        case 'tv-14' | 'ma15+' | 'm16' | 'tv-y' | '16' | '14' | '15' | '16+':
            return 'PG-13'
        case 'tv-ma' | 'm' | '18' | '+18':
            return 'R'
        case 'nc-17':
            return 'X'
        case _:
            return val # Didn't catch this one yet, or its a default

def avg(arr):
    if (len(arr) <= 0):
        return 0
    return sum(arr) / len(arr)

def filtersToString(data):
    send = ""
    if 'certification' in data.keys() and data['certification'] is not None:
        send += "\\a\\"+data['certification'].lower()
    if 'metascore' in data.keys() and data['metascore'] is not None:
        if (isinstance(data['metascore'], list)):
            send += "\\b\\"+str( int( avg( list( map( int, data['runtime'] ) ) ) ) )
        else:
            send += "\\b\\"+data['metascore']
    if 'rating' in data.keys() and data['rating'] is not None:
        if (isinstance(data['rating'], list)):
            send += "\\c\\"+str( round( avg( list( map( float, data['rating'] ) ) ), 1) )
        else:
            send += "\\c\\"+data['rating']
    if 'runtime' in data.keys() and data['runtime'] is not None:
        if (isinstance(data['runtime'], list)):
            send += "\\d\\" + str( int( avg( list( map( int, data['runtime'] ) ) ) ) )
        else:
            send += "\\d\\"+data['runtime']
    if 'codec' in data.keys() and data['codec'] is not None:
        send += "\\e\\"+data['codec']
    return send

def sanatize(string):
    send = string.replace(";", "")
    send = send.replace(":", "")
    send = send.replace("#", "")
    send = send.replace("@", " at ")
    return send

def getCodec(filePath, errorLog=None):
    command = [
        'ffprobe',
        '-v',
        'quiet',
        '-print_format',
        'json',
        '-show_streams',
        filePath
    ]
    res = None
    try:
        res = subprocess.run(command, capture_output=True, text=True, check=True)
    except Exception as e:
        if (errorLog is not None):
            errorLog.write(f"ffprobe failed on file path {filePath}\n")
            errorLog.write(str(e))
            errorLog.write("\n")
        else:
            print(f"ffprobe failed on file path {filePath}")
            print(str(e))
        return "Error"
    resJson = json.loads(res.stdout)
    for stream in resJson.get('streams', []):
        if stream.get('codec_type') == 'video':
            return stream.get('codec_name')
    return 'none'

def walkDir(path, writeTo=".", errorLogPath="./movieWalkError.log", extension = ".tgmd", prefix="", codecDirectories=[], codecExtensions=['.mp4', '.mov', '.mkv', '.avi', '.m4v', '.divx'], noZip=False, isShow=False, progressBar=False, getCodecs=True):
    """
    path <str>: The path to the parent directory to being walking
    writeTo <str>: The path write local copies of all tgmd files found, if getting codecs, it will write the codec value to a local file
    extension <str>: What extension will be targeted to find info on the movie
    codecExtensions <list(str)>: What extensions will be targeted to ffprobe the codec value
    noZip <bool>: True -> Will use the standard python open() to read the file, False -> Will use ZipFile's open to look for a file labeled 'nfo' for the information
    isShow <bool>: True -> Will move 'showTitle' field to 'title' field, False -> nothing else
    progressBar <bool>: True -> Shows a progress bar of how far the walk has yet to do, False -> No progress bar
    getCodecs <bool>: True -> Uses codecExtensions to look for the codecs using linux command ffprobe on the file, False -> Any codecs found will be from the .tgmd file - File codec found takes precedence over .tgmd codec mentioned
    """
    master = {}  # Total dict of all keys
    path = str(os.path.abspath(path)) # Get the absolute path
    walkDir = Path(path)  # The dir object to recursively look through
    fileCount = 0  # Count how many files we've already seen, only used when progressBar == True
    totalCount = 0    # Total count of files, only used when progressBar == True
    startTime = 0  # UTC start time of program
    writeToSize = len(writeTo)
    pathSize = len(path)+1
    codecExtensions = set(codecExtensions)
    
    if progressBar:
        #Gets the total count of files we're looking for
        startTime = time.time()
        for filePath in walkDir.rglob('*'): #Count files ending in extension
            if filePath.suffix == extension:
                totalCount += 1
        if getCodecs and len(codecDirectories) > 0: #Count the codec items
            for directory in codecDirectories:
                for filePath in Path(directory).rglob('*'):
                    if filePath.suffix in codecExtensions:
                        totalCount += 1

    errorLog = open(os.path.abspath(errorLogPath), 'w+')

    codecValue = {}
    codecs = {} # Holds all the codecs by location, codecs will not have the other filter data

    if getCodecs:
        #First pass to get all the codecs from the actual files
        if len(codecDirectories) <= 0:
            errorLog.write("There are no directories to walk through for getting the codecs\n")
        for directory in codecDirectories:
            for filePath in Path(directory).rglob("*"):
                if (filePath.suffix in codecExtensions):
                    codecs[str(filePath)[pathSize:]] = getCodec(filePath, errorLog = errorLog).lower()
                    fileCount+=1
                    if progressBar:
                        progress.printBar(fileCount, totalCount, barLength=80, timeSinceStart=startTime, timeNow=time.time())
    for filePath in walkDir.rglob("*"):
        out = {}

        if filePath.suffix != extension: # Will not move to the data colsolidation step if this isn't the file type we want
            continue

        if progressBar:
            fileCount += 1
            progress.printBar(fileCount, totalCount, barLength=80, timeSinceStart=startTime, timeNow=time.time())

        #Get xml data from the file
        if not noZip:
            with ZipFile(filePath, 'r') as zip:
                with zip.open("NFO") as fs:
                    out = xmlReader.readFile(fs, errorLog=errorLog, ignore=["cover", "backdrop", "mediainfo", "@ThumbGen", '@xmlns:xsd', '@xmlns:xsi', 'hasrighttoleftdirection', 'mpaa', 'plot', 'trailer', 'releasedate', 'File'])
        else:
            with open(filePath, 'r') as file:
                out = xmlReader.readFile(file, errorLog=errorLog, ignore=[])
        if isShow:
            out['showTitle'] = out['title']
        if 'certification' in out.keys():
            out['certification'] = standardMpaa(out['certification'])
        else:
            out['certification'] = 'Not Rated'

        if getCodecs:
            codecName = str(filePath)[pathSize:-len(extension)]
            if codecName in codecs:
                out['codec'] = codecs[codecName]
                del codecs[codecName]
            else:
                errorLog.write(f"File {codecName} in {path} does not have a codec value, there was no recognized video extension in the directory\nRecognized extensions: {codecExtensions}")
        
        writeSave = writeTo + "/" + sanatize(str(filePath)[pathSize:][:-len(extension)])+".mdd"
        #Check if the file wants to be somewhere other than the default
        if 'loc' in out.keys():
            valName = out['loc']
            writeSave = writeTo + "/" + valName + "/" + sanatize(str(filePath).split('/')[-1][:-len(extension)])+".mdd"
            #valName += "/" + str(filePath).split('/')[-1][:-4]
        else:
            out['loc']=str(filePath)[:-5]
        #Write a local save in an easy to access location
        savePath = os.path.dirname(writeSave)
        if savePath:
            os.makedirs(savePath, exist_ok=True)
        with open(writeSave, "w+") as file:
            xmlReader.writeFile(file, out)
        out = xmlReader.reverseDict(out, writeSave[:-4]+filtersToString(out), errorLog=errorLog, startFrom=writeToSize, isShow = isShow, prefix=prefix)
        unionAdd(master, out)
    #Adding the codecs from movies without tgmd files
    if (getCodecs):
        for key, val in codecs.items():
            addTo = master['codec']
            if (val in addTo):
                if isinstance(addTo[val], list):
                    addTo[val].append(key)
                else:
                    print(f"addTo[val] is not a list, what do I do now? type: {type(addTo[val])}")
            else:
                addTo[val] = [key,]
#            out = {val: [key,]}
#            unionAdd(master, out)
    if (progressBar):
        print() #Moves cursor to next line
    errorLog.close()
    return master

def walkAndWrite(path, writeTo='.', ignoreWriting=set(), extension = '.tgmd'):
    master = walkDir(path, writeTo, extension)
    writeOut(master, writeTo, ignoreWriting)

if __name__ == "__main__":
    import pprint
    #/home/turtl/tvapi/indexTvShows/Aeon Flux
    out = walkDir(r'/mnt/saturn/backup/Movies/A/12 Monkeys (1995)[1080p]/', writeTo="./testData", extension = ".tgmd", noZip=False, isShow=False, progressBar=True, getCodecs=True)
    pprint.pprint(out)
    writeOut(out, writeTo="/var/www/html/testData")
#     out = walkAndWrite(r"/mnt/saturn/backup", writeTo=r"/var/www/html/data")
#     print("All Done!")
