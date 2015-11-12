import json
import urllib2

with open("../key.txt") as f:
  key = f.read()

def getSummonerId(summonerName):
  standardizedSummonerName = summonerName.replace(" ", "").lower()
  f = urllib2.urlopen("https://na.api.pvp.net/api/lol/na/v1.4/summoner/by-name/" + standardizedSummonerName + "?api_key=" + key)
  j = json.loads(f.read())
  return j[standardizedSummonerName]["id"]

def getChampionMastery(summonerId, n):
  f = urllib2.urlopen("https://global.api.pvp.net/championmastery/location/NA1/player/" + str(summonerId) + "/champions?api_key=" + key)
  j = json.loads(f.read())
  return [x["championId"] for x in j[:n]]
