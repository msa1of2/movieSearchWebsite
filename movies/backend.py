from flask import Flask, request, jsonify, render_template, send_from_directory, abort, make_response, url_for, redirect
from werkzeug.utils import safe_join
from flask_cors import CORS
from datetime import datetime
import ctypes
import time
import mmap
import subprocess
import sys
import threading
import os
import re
from collectData import xmlReader as xmlReader
from collectData import movieWalker as movieWalker
from collectData import configParser
from backendHelpers import *
from backendHelpers.authChecker import Auth
from backendHelpers.cookieManager import CookieManager
from zipfile import ZipFile

#Stores the cookies, only need to store for active time, no preservation across server restarts
CM = CookieManager()

app = Flask(__name__)
CORS(app) # Enables CORS so browser fetch requests aren't blocked

config = configParser.readFile('/var/www/movieSearchWebsite/config.json')

START_CUT=19

lib_path = os.path.abspath("./dataExtractor.so")
print("LIBPATH", lib_path)
getData=ctypes.CDLL(lib_path)

getData.extractData.argtypes = [
    ctypes.c_char_p,
    ctypes.c_char_p,
    ctypes.c_char_p,
    ctypes.POINTER(ctypes.c_size_t),
    ctypes.c_bool
]
getData.extractData.restype = ctypes.POINTER(ctypes.c_char_p)

getData.extractRangedData.argtypes = [
    ctypes.c_char_p,
    ctypes.c_size_t,
    ctypes.c_size_t,
    ctypes.c_char_p,
    ctypes.POINTER(ctypes.c_size_t)
]
getData.extractRangedData.restype = ctypes.POINTER(ctypes.c_char_p)

getData.extractFilterData.argtypes = [
    ctypes.c_char_p,
    ctypes.POINTER(ctypes.c_char_p),
    ctypes.c_size_t,
    ctypes.c_char_p,
    ctypes.POINTER(ctypes.c_size_t),
    ctypes.c_bool
]
getData.extractFilterData.restype = ctypes.POINTER(ctypes.c_char_p)

getData.freeArray.argtypes = [
    ctypes.POINTER(ctypes.c_char_p),
    ctypes.c_size_t
]

def filtersToString(data):
    if (isinstance(data, str)):
        return "as"+data+";"

    if (isinstance(data, list)):
        send = ""
        for mpaa in data:
            send += "as"+mpaa.lower()+";"
        return send
    send = ""
    if 'searchMpaa' in data.keys():
        for mpaa in data['searchMpaa']:
            send += "as"+mpaa.lower()+';'
    if 'metascore' in data.keys():
        send += 'bm'+str(data['metascore']['min'])+":"+str(data['metascore']['max'])+';'
    if 'rating' in data.keys():
        send += 'cm'+str(data['rating']['min'])+":"+str(data['rating']['max'])+';'
    if 'runtime' in data.keys():
        send += 'dm'+str(data['runtime']['min'])+":"+str(data['runtime']['max'])+';'
    if 'codec' in data and False:
        # Reindexing causes codec filter names in filter with search to be different than the codecs found and delievered to website (used to search), possibly due to tgmd codec and ffprobe codec getting diff results
        # Simple fix is to not look at codecs while filtering aka 'and False'
        for code in data['codec']:
            send += 'es'+code.lower()+';'
    return send

def extractData(filename, query, toAdd, filters={}, start=""):
    #extracts the file location data from file based on match results and adds each entry to toAdd
    name = filename.encode('utf-8')
    query = query.encode('utf-8')
    filterString = filtersToString(filters).encode('utf-8')
    count=0
    count_val = ctypes.c_size_t(count)
    count_ptr = ctypes.byref(count_val)
    result_ptr = getData.extractData(name, query, filterString, count_ptr, ctypes.c_bool(False))
    size = count_val.value
    send = [None]*size
    if result_ptr:
        for i in range(size):
            bytes = result_ptr[i]
            if bytes is not None:
                send[i] = start + bytes.decode('utf-8')
        getData.freeArray(result_ptr, count_val)
    #return send
    toAdd.extend(send); #[x for x in send if x is not None])

def extractRangedData(filename, low, high, toAdd, filters={}, start=""):
    name = filename.encode('utf-8')
    lowVal = ctypes.c_size_t(low)
    highVal =ctypes.c_size_t(high)
    filterString = filtersToString(filters).encode('utf-8')
    countVal = ctypes.c_size_t(0)
    countPtr = ctypes.byref(countVal)
    resPtr = getData.extractRangedData(name, lowVal, highVal, filterString, countPtr)
    size = countVal.value
    send = []
    if resPtr:
        send = [start+resPtr[i].decode('utf-8') for i in range(size) if resPtr[i] is not None]
        getData.freeArray(resPtr, countVal)
    toAdd.extend(send)

def extractFilterData(filename, filters, toAdd, filtersDict={}, start=""):
    name = filename.encode('utf-8')
    queries = [x.encode('utf-8') for x in filters]
    arrType = ctypes.c_char_p * len(queries)
    arr = arrType(*queries)
    filterSize = ctypes.c_size_t(len(queries))
    filterString = filtersToString(filtersDict).encode('utf-8')
    countVal = ctypes.c_size_t(0)
    countPtr = ctypes.byref(countVal)
    resPtr = getData.extractFilterData(name, arr, filterSize, filterString, countPtr, ctypes.c_bool(True))
    size = countVal.value
    send = [None]*size
    if resPtr:
        for i in range(size):
            bytes = resPtr[i]
            if bytes is not None:
                send[i] = start + bytes.decode('utf-8')
        getData.freeArray(resPtr, countVal)
    toAdd.extend(send)

def reindex():
    with open("/home/turtl/indexer.log", "w+") as f:
        proc = subprocess.Popen(
        ["at", "now"],
        stdin=subprocess.PIPE,
        stdout=f,
        stderr=f,
        text=True
        )
        proc.communicate(input="python3 /var/www/html/reindexer.py > /home/turtl/at.log")
    with open('./lastIndex', 'w+') as file:
        file.write(datetime.now().strftime("%Y-%m-%d %H:%M:%S"))

def dummyData():
    send = {'Dummy': 'Test Data'}
    data = {'actor': 'Dummy'}
    data['certification'] = 'Nothing Burger'
    data['country'] = "over there"
    data['director'] = "me"
    data['genre'] = 'Meh'
    data['id'] = 'thatd'
    data['metascore'] = '79'
    data['rating'] = '7.9'
    data['title'] = "The Dumbest data you ever did see"
    data['tagline'] = "You'll never see this again"
    data['year'] = 'this one'
    send['Dummy data'] = data
    return jsonify(send)

def getFilterFilename(userName):
    match userName:
        case "mpaa":
            return 'certification'
        case "meta":
            return 'metascore'
        case "rate":
            return 'rating'
        case "time":
            return 'runtime'
        case "code":
            return 'codec'
        case _:
            return "NONE"

def getFilterData(filename, filters, toAdd, start=""):
    if filename == "certification":
        extractFilterData(f"./data/{filename}.mdr", filters['searchMpaa'], toAdd, filtersDict = filters, start = start)
    if filename == "codec":
        extractFilterData(f"./data/{filename}.mdr", filters['codec'], toAdd, filtersDict = filters, start = start)
    elif filename=="rating":
        low = int(float(filters['rating']['min'])*10)
        high = int(float(filters['rating']['max'])*10)
        extractRangedData(f"./data/{filename}.mdr", low, high, toAdd, filters = filters, start = start)
    else:
        low = int(filters[filename]['min'])
        high =int(filters[filename]['max'])
        extractRangedData(f"./data/{filename}.mdr", low, high, toAdd, filters = filters, start = start)

def getEpisodeData(loc, data):
    if "#" not in loc or 'episodeData' not in data.keys():
        return data
    name = loc.split("#")[1]
    split = name.find('x')
    try:
        s = str(int(name[1:split]))
        e = str(int(name[split+1:name.find(" - ")]))
        eps = data['episodeData']
        if eps == None:
            return data
        for ep in eps:
            if eps[ep]['seasonNum'] == s and eps[ep]['number'] == e:
                return eps[ep]
    except:
        return data

def getTitle(loc, data):
    if "#" not in loc:
        return data['title']
    return loc[loc.find(" - ")+3:]

@app.route('/api/login', methods = ['POST'])
def apiLogin():
    data = request.form
    username = data.get('username')
    password = data.get('password')
    authType = data.get('loginType')
    cookie = Auth.loginCookie(CM, username, password, authType)
    if cookie is None:
        return jsonify({"error": "Invalid Credentials"}), 401
    res = make_response(redirect(url_for('getAdminWebsite')))
    res.set_cookie(
        key = "loginDetails",
        value = cookie.tokenID,
        httponly = True,
        secure=False,
        samesite='Lax',
        path='/'
    )
    return res, 200

@app.route('/api/logout', methods = ['POST'])
def apiLogout():
    cookieToken = request.cookies.get('loginDetails')
    CM.deleteCookie(cookieToken)

    res = make_response(jsonify({"message": "Logged out successfully"}))
    res.set_cookie(
        key = "loginDetail",
        value = "",
        maxAge=0,
        httponly=True,
        secure=False,
        samesite='Lax'
    )
    return res, 200

@app.route("/login", methods = ['GET', 'POST'])
def login():
    return render_template("login.html")

@app.route('/admin', methods = ['GET', 'POST'])
def getAdminWebsite():
    cookieToken = request.cookies.get('loginDetails')
    if not CM.cookieHasPrivlige(cookieToken, CM.AUTH_ADMIN):
        return redirect(url_for("login"))
    return render_template("testing.html", dynamic_line = "Admin console")

@app.route('/data/get/codecs', methods = ['GET'])
def getCodecs():
    codecs = []
    with open('./codecs', 'r') as f:
        try:
            codecs = xmlReader.readFile(f)['codec']
        except:
            codecs = ["No Codecs in file"]
    return jsonify(codecs), 200

@app.route('/data/get/<season>/<episode>/<path:location>')
def getFilmData(season, episode, location):
    try:
        season = int(season)
        episode = int(episode)
    except ValueError:
        abort(400, description="Season and episode values must be numbers")
    #Returns the data of a single file requested
    path = None
    debug={}
    try:
        if location.startswith(config['movie prefix']):
            debug["startswith"] = "true"
            location = location[len(config['movie prefix'])+1:]
            debug['location'] = location
        path = safe_join(safe_join(config['write location'], 'local'), location)
        debug['path'] = path
    except:
        abort(403, description="What'chu looking for?")
    if path is None or not os.path.exists(path) or not os.path.isfile(path):
        #print("Failed path:", path)
        abort(404, description=debug) #"Not here man")
    if not path.endswith(".mdd"):
        abort(403, description="Wrong file type")
    out = {}
    with open(path, 'r') as file:
        out = xmlReader.readFile(file)
    if not out:
        abort(404, description=f"File is missing: {location}")

    out['debug'] = debug

    if (season > 0 and episode > 0):
        #Getting specific episode data
        data = out['episodeData']
        for epKey in data:
#            print(epKey, data[epKey]['number'], "=?=", episode, data[epKey]['seasonNum'], "=?=", season, data[epKey]['number'] == episode, data[epKey]['seasonNum'] == season, data[epKey]['name'], data[epKey]['runtime'])
            if int(data[epKey]['number']) == episode and int(data[epKey]['seasonNum']) == season:
                out['title'] = data[epKey]['name']
                out['runtime']=data[epKey]['runtime']
                break
        del out['episodeData']
        return jsonify(out), 200
    if (season == 0 and episode == 0):
        #Getting General series data
        del out['episodeData']
        return jsonify(out), 200
    if (season < 0 or episode < 0):
        #Just returns the data without messing with it
        return jsonify(out), 200
    abort(400, description="Improper season, episode values")

@app.route('/', methods=['GET', 'POST'])
def handle_fetch():
    if request.method =='GET':
        return render_template('index.html')
    # .get_json() parses the raw 'body' string from fetch into a Python dictionary
    data = request.get_json() 
    times={"start": time.time_ns()}
    if not data:
        return jsonify({"error": "Missing JSON data"}), 400
    if 'index-key' in data.keys():
        if data['index-key'] == "turtlturtl":
            threading.Thread(
                target=reindex
            ).start()
            return '{"result":"indexing started successfully"}', 202
        else:
            return jsonify({"error": "Incorrect credentials"})
    if 'last-index' in data.keys():
        lastIndexString = "No time stored"
        with open('./lastIndex', 'r') as file:
            lastIndexString = file.read()
        return jsonify({"last-index": lastIndexString}), 200
    if data['search'] == "dummytest":
        return dummyData(), 200

    movieLocations = {}
    debug = []
    filterSearch = False
    #Filter searching ie: 'find all movies with PG mpaa rating' other filters still apply
    if 'filterSearch' in data.keys() and len(data['filterSearch']) > 0:
        #do stuffs to instead search through the filters, ignoring search request and settings, normal filters apply though
        for file in data['filterSearch']:
            movieLocations[file] = []
            filename = getFilterFilename(file)
            if filename == "NONE":
                return jsonify({"error": "The filter wildcard does not exist, check spelling"}), 400
            if not os.path.exists(f"./data/{filename}.mdr"):
                return jsonify({"error": f"edge condition found for type {filename}.mdr during filter wildcard"}), 500
            getFilterData(filename, data['filters'], movieLocations[file], start="")
        debug.append("Filter searching");
        filterSearch = True
        #Grab all the movies that fit the search term for specified fields
    else:
        debug.append("normal searching");
        for file in data['searchSettings']:
            if file is None:
                continue
            movieLocations[file] = []
            if not os.path.exists("./data/"+file+".mdr"):
                return jsonify({"error": f"edge condition found for type {file}.mdr"}), 500
            extractData("./data/"+file+".mdr", data['search'], movieLocations[file], filters = data['filters'], start="")
    times["End Extraction"] = time.time_ns()
    toSend = {}
    toSend['results'] = movieLocations
    toSend["timings"] = times
    toSend['debug'] = debug
    toSend['count'] = len(movieLocations)
    return jsonify(toSend)

@app.route('/test/<valIn>')
def testing(valIn):
    return render_template('testing.html', dynamic_line=valIn)
    
@app.route('/favicon.ico')
def favicon():
    return send_from_directory(os.path.join(app.root_path, 'static'), 'favicon.ico')

#@app.before_request
#def log_request_info():
#    print(f"--- Incoming Request ---")

if __name__ == '__main__':
    #extractRangedData(filename, low, high, toAdd, start=""):
    import pprint
    out = []
    #extractRangedData('./test.mdr', 0, 110, out)
    #pprint.pprint(out)
    #extractData(filename, query, toAdd, start=""):
    out = []
    filters = {'metascore':{'max':100, 'min':0},
               'rating':{'max':10.0, 'min':0},
               'runtime':{'max':1440, 'min':0},
               'searchMpaa':['pg-13']} #['not rated', 'g', 'pg', 'pg-13', 'r', 'x']}
#    getCodecs()
    reindex()
#    extractData('./data/title.mdr', "9", out, filters)
#    pprint.pprint(out)
#    app.run(port=5000, debug=True)


"""Users can search for:
Actor
Director
Genre
ID
Studio
Tagline
Title (also works on original title)
Year
Country

Filter for:
Certification (mpaa rating)
Metascore (critic score)
Rating
Runtime
"""
