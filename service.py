from pymongo import MongoClient
import time
import json
import paho.mqtt.client as mqtt
import pygeohash as pgh
import math
import requests
from bson import json_util

languages = {}

languages['as'] = 'assamese'
languages['bn'] = 'bangla'
languages['brx'] = 'boro'
languages['gu'] = 'gujarati'
languages['hi'] = 'hindi'
languages['kn'] = 'kannada'
languages['ks'] = 'kashmiri'
languages['gom'] = 'konkani goan'
languages['mai'] = 'maithili'
languages['ml'] = 'malayalam'
languages['mni'] = 'manipuri'
languages['mr'] = 'marathi'
languages['ne'] = 'nepali'
languages['or'] = 'oriya'
languages['pa'] = 'panjabi'
languages['sa'] = 'sanskrit'
languages['si'] = 'sinhala'
languages['ta'] = 'tamil'
languages['te'] = 'telugu'
languages['ur'] = 'urdu'

def connectToMongo():
    try :
        client = MongoClient('mongodb+srv://Developer:Bahubhashak@bahubhashaak-project.ascwu.mongodb.net/EMRI?retryWrites=true&w=majority')
        print("Connected successfully!!!")
    except:
        print("Could not connect to MongoDB")
    return client

def haversine_distance(lat1, lon1, lat2, lon2):
    R = 6371.0  # Earth's radius in kilometers
    dLat = math.radians(lat2 - lat1)
    dLon = math.radians(lon2 - lon1)
    a = (math.sin(dLat / 2) ** 2 +
         math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) *
         math.sin(dLon / 2) ** 2)
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return R * c

def getRelevantLocations(center_lat,center_lon,km_radius = 5):
    
    points = []
    step = 0.01
    # Compute the maximum latitude and longitude changes in degrees
    max_change_km = km_radius / 111.32  # Approximate conversion from degrees to kilometers at the equator
    max_lat = center_lat + max_change_km
    min_lat = center_lat - max_change_km
    max_lon = center_lon + max_change_km / math.cos(math.radians(center_lat))
    min_lon = center_lon - max_change_km / math.cos(math.radians(center_lat))

    lat = round(min_lat / step) * step
    while lat <= max_lat:
        lon = round(min_lon / step) * step
        while lon <= max_lon:
            if haversine_distance(center_lat, center_lon, lat, lon) <= km_radius:
                points.append((round(lat, 2), round(lon, 2)))  # Ensure rounding to two decimal places
            lon = round((lon + step), 2)  # Increment and round to ensure precision
        lat = round((lat + step), 2)  # Increment and round to ensure precision
    
    return points

def connectToMQTT():
    try:
        hosts = [1883,1884,1885]
        for i in range(len(hosts)):
            mqttBroker = "ec2-52-66-230-245.ap-south-1.compute.amazonaws.com"
            client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION1,"Server",clean_session=False)
            client.connect(mqttBroker,hosts[i])
            print("Connected to MQTT")
            break
    except:
        print("Could not connect to MQTT host with port {hosts[i]}")
    return client

def getCredibility(client,news):
    guardianAngel = client['GuardianAngel']
    sourceTrustScore = guardianAngel['sourceTrustScore']
    score = 0

    #if source is not the key then continue
    if 'source' not in news:
        return 0
    source = news['source']


    news_source = sourceTrustScore.find({"source":source})

    if news_source is None:
        sourceTrustScore.insert_one({"source":source,"credibility":1})
        return
    else:
        for j in news_source:
            score = max(j['credibility'],score)


    return score

def getNewsinLanguages(news):
    languageNews = {}
    headline = news.get('headline')
    
    description = news.get('description')
    languageNews['english'] = news
    for i in languages:
        news1 = news.copy()
        languageNews[languages[i]] = news1
        url = "http://ec2-52-66-230-245.ap-south-1.compute.amazonaws.com/personalised"
        json_data = { 
            "output_language":i,
            "message":headline
        }
        x = requests.post(url,json = json_data)
        if x.status_code != 200:
            continue

        y = x.json()
        y = y['result']
        print(i,y['message'])
        
        languageNews[languages[i]]['headline'] = y['message']
        if 'audio' in y.keys():
            languageNews[languages[i]]['audio'] = y['audio']
        json_data = {
            "output_language":i,
            "message":description
        }
        languageNews[languages[i]]['description'] = requests.post(url,json=json_data).json()['result']['message']
    
    return languageNews

def publishNews(mqtt_client,news):
    lat = float(news['latitude'])
    long = float(news['longitude'])
    #if lat == 0 and long == 0:
    #    return 
    # location = news['location']
    # lat = location['lat']
    # lon = location['lon']
    relevantLocations = getRelevantLocations(float(lat),float(long))
    
    languagesNews = getNewsinLanguages(news)
    for i in relevantLocations:
        geohash = pgh.encode(i[0],i[1])
        topic = geohash+"/flood/"
        for j in languagesNews:
            print(j)
            
            topic1 = topic + j
            # print(languagesNews[j])
            # print(json.dumps(languagesNews[j]))
            print(topic1)
            time.sleep(1)
            mqtt_client.publish(topic = topic1,payload = json_util.dumps(languagesNews[j]),qos = 0,retain = True)
            print("Published ", languagesNews[j]['headline'] ,"to",topic1)
            
        




def callquery(client):
    guardianAngel = client['GuardianAngel']
    news = guardianAngel['events']
    query = list(news.find({"visited":False}))

    result = news.update_many({"visited":False},{"$set":{"visited":True}})
    value = result.modified_count
    print(f'Fetched', value, 'news articles')
    return query


client = connectToMongo()
mqtt_client = connectToMQTT()
while(1):
    news = callquery(client)
    for i in news:
        lat = float(i['latitude'])
        long = float(i['longitude'])
        if lat == 0 and long == 0:
            continue
        credibility = getCredibility(client,i)
        if credibility >= 0.5:
            publishNews(mqtt_client,i)

    time.sleep(6000)
