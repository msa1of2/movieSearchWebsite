import sys
import xmltodict

def readFile(file, errorLog=None, ignore=["File", "cover", "backdrop", "mediainfo", "@ThumbGen", '@xmlns:xsd', '@xmlns:xsi', 'hasrighttoleftdirection', 'mpaa', 'plot', 'trailer', 'releasedate'], 
            collapseNameEntry=["actor", "country", "director", "genre", "studio", "writers", "gueststars"],
            rootName = "movie"):
    #Reads the specified xml file, extracts the relevant data, returns as dict the exact info in the file
    out = {}
    try:
        out = xmltodict.parse(file.read())[rootName]
    except Exception as e:
        if errorLog is not None:
            errorLog.write(f"xml to dict failed parsing {file.name}\n")
            errorLog.write(str(e))
            errorLog.write("\n")
        else:
            print(f"xml to dict failed parsing {file.name}")
            print(str(e))
    for item in ignore:
        if (item in out.keys()):
            del out[item]
    for item in collapseNameEntry:
        if item in out.keys() and out[item] is not None and type(out[item]) is dict and 'name' in out[item].keys():
            out[item] = out[item]['name']
    return out
    
def writeFile(file, data, rootName="movie"):
    #give data as a dictionary
    #Writes an xml like file of the data recorded
    file.write(xmltodict.unparse({rootName : data}))

def sanatize(string):
    send = string.replace(";", "")
    send = send.replace(":", "")
    send = send.replace("#", "")
    send = send.replace("@", " at ")
    return send

def reverseShowDict(writeOut, episodes, valueName, titleValue):
    writeOut['runtime'] = {}
    writeOut['title']={titleValue.lower():valueName}
    runtime = writeOut['runtime']
    title = writeOut['title']
    name = sanatize(valueName)
    filterVals = ""
    if '\\' in valueName:
        name = valueName.split("\\")
        filterVals = "\\" + "\\".join(name[1:])
        name = sanatize(name[0])
    for key in episodes:
        if episodes[key]['runtime'] not in runtime.keys():
            runtime[episodes[key]['runtime']] = []
        runtime[episodes[key]['runtime']].append(name+f"#S{episodes[key]['seasonNum']}x{episodes[key]['number']:>03} - {sanatize(episodes[key]['name'])}"+filterVals)
        title[sanatize(episodes[key]['name']).lower()] = name+f"#S{episodes[key]['seasonNum']}x{episodes[key]['number']:>03} - {sanatize(episodes[key]['name'])}"+filterVals
        if ('franchise' not in writeOut.keys()):
            writeOut['franchise'] = {titleValue.lower(): []}
        writeOut['franchise'][titleValue.lower()].append(name+f"#S{episodes[key]['seasonNum']}x{episodes[key]['number']:>03} - {sanatize(episodes[key]['name'])}"+filterVals)

def reverseDict(dictIn, valueName, errorLog=None, startFrom=0, isShow = False, prefix=""):
    # used for these movie xml files, reverses the actor names to be keys in a dict under actor that points to valueName
    # ie: {actor : [personA, personB]} -> {actor : {personA: valueName, personB: valueName}
    out = dictIn.fromkeys(dictIn.keys()) # copy over the old root-level keys
    valueName = sys.intern(sanatize(valueName[startFrom:])) # gets the canonical rep for the string
    for key in dictIn.keys():
        if (dictIn[key] is None):
            continue
        if isShow and key=="episodeData":
            reverseShowDict(out, dictIn['episodeData'], prefix + valueName, sanatize(dictIn['title']))
            del out['episodeData']
            continue
        if isShow and (key=="episodeNames" or key=="title"):
            continue #Episode names data is added by reverse show dict
        if isShow and key=="runtime":
            continue #The runtime for shows are replaced with each episode's runtime
        if (isinstance(dictIn[key], dict)):
            if errorLog is None:
                print(f"I don't know how to reverseDict a dictionary, have fun debuging, this entry is skipped: {dictIn[key]}, key: {key}, valueName: {valueName}")
            else:
                errorLog.write(f"I don't know how to reverseDict a dictionary, have fun debuging, this entry is skipped: {dictIn[key]}, key: {key}, valueName: {valueName}")
            continue
        if (isinstance(dictIn[key], list)):
            #print(list(map(lambda x: str(x).lower(), dictIn[key])) )
            out[key] = dictIn.fromkeys(map(lambda x: sanatize(str(x)).lower(), dictIn[key]), prefix + valueName)
            continue
        else:
            #Otherwise its a simple string
            out[key] = {sanatize(dictIn[key]).lower(): prefix + valueName}
    
    return out
    
if __name__ == "__main__":
    import pprint
    if (len(sys.argv) <= 1):
        print("Add a file to the invocation next time\nGoodbye!")
        sys.exit(0)
    out={}
    with open(sys.argv[1], "r") as file:
        out = readFile(file)
        #pprint.pprint(out)
        print("\n\n")
        reversed = reverseDict(out, "testing", isShow=True)
        pprint.pprint(reversed['title'])
    
    if (len(sys.argv) <= 2):
        print("Add a second file to the invocation to write to\nGoodbye!")
        sys.exit(0)

    print("\n\n")
    
    with open(sys.argv[2], "w+") as file:
        writeFile(file, out)
    
    print("Goodbye!")
