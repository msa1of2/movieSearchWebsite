import sys
from . import xmlReader

def readFile(file):
    out = {}
    lines = file.read().split(";")
    for line in lines:
        if not line:
            continue
        items = line.split(":")
        entry = items[1].split("@")
        if (len(entry) == 1):
            entry = entry[0]
        out[items[0]] = entry
    return out

def writeFile(file, data):
    for key in data.keys():
        if (data[key] is None):
            continue
        elif (type(data[key]) is dict):
            writeFile(file, data[key])
            file.write(";")
            continue
        elif (type(data[key]) is list):
            file.write(str(key)+":"+("@".join(data[key]))+";")
        elif (type(data[key]) is str):
            file.write(str(key)+":"+str(data[key])+";")
        else:
            print(f"Unknown type, got {type(data[key])} and I is too stupid to do conversion")
    file.seek(0, 2)
    pos = file.tell() - 1
    if pos >= 0:
        file.seek(pos)
        file.truncate() #voids the last ; at the end of the file
    
    
if __name__ == "__main__":
    import pprint
    if (len(sys.argv) <= 1):
        print("Add a file to the invocation next time\nGoodbye!")
        sys.exit(0)
    out={}
    with open(sys.argv[1], "r") as file:
        #out = readFile(file)
        out = xmlReader.reverseDict(xmlReader.readFile(file), "testing")
        pprint.pprint(out)
    
    if (len(sys.argv) <= 2):
        print("Add a second file to the invocation to write to\nGoodbye!")
        sys.exit(0)
    
    print("\n\n")
    
    with open(sys.argv[2], "w+") as file:
        writeFile(file, out)
    
    print("Goodbye!")
