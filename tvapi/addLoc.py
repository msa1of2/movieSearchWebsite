import os
import xmltodict

def addLoc(path="./indexTvShows", extension=".tvs"):
    for dirpath, dirnames, files in os.walk(path):
        out = {}
        folder = os.fsencode(dirpath)
        for file in os.listdir(folder):
            filename = os.fsdecode(file)
            if filename.endswith(extension):
                d = {}
                with open(dirpath+"/"+filename, 'r', encoding='utf-8') as f:
 #                   print(dirpath + "/" + filename)
#                    print(f"Adding Loc to {filename}")
                    d = xmltodict.parse(f.read())['movie']
                    if 'loc' in d.keys():
                        continue
                    d['loc'] = "TV/"+dirpath.split("/")[-1]
                with open(dirpath+"/"+filename, 'w+') as f:
                    f.write(xmltodict.unparse({'movie':d}))

if __name__ == "__main__":
    addLoc()
    print("All done")
