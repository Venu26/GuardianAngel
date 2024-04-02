from flask import Flask,request
import os
import pygeohash as pgh
app = Flask(__name__)

import geohash



@app.route('/getGeohash', methods=['GET'])
def getGeohash():
    long = float(request.args.get('long'))
    lat = float(request.args.get('lat'))
    latmax = round(lat,2)
    if latmax > lat:
        latmin = round(lat,2) - 0.01
    else:
        latmin = latmax
        latmax = latmax + 0.1
    longmax = round(long,2)
    if longmax > long:
        longmin = round(long,2) - 0.01
    else:
        longmin = longmax
        longmax = longmax + 0.01
    
    avgPoint = ((longmax+longmin)/2.0,(latmax + latmin)/2.0)
    avgPoint = (round(avgPoint[0],2),round(avgPoint[1],2))
    print(avgPoint)
    geohash1 = pgh.encode(avgPoint[1],avgPoint[0])
    return geohash1


if __name__ == '__main__':  
   app.run(host='10.2.8.16',port=5000,debug=True)
