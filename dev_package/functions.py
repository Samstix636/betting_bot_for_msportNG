import scrapy
from scrapy.http import FormRequest, Request
import requests
from private import username, password, delayed_app_key
import urllib
import json
from utils import login
import datetime
import pytz
import pprint
import pygsheets
from time import sleep, time
from scrapy.crawler import CrawlerProcess
import re

#pytz.timezone('Australia/Sydney')
#FILTERS
eventTypeId = '["1"]'
countryCode = '["GB"]'
marketTypeCode = '["WIN"]'
marketStartTime = datetime.datetime.now() - datetime.timedelta(hours=24)
marketStartTime = marketStartTime.strftime('%Y-%m-%dT%H:%M:%SZ')
marketEndTime = datetime.datetime.now()+datetime.timedelta(hours=24)
marketEndTime = marketEndTime.strftime('%Y-%m-%dT%H:%M:%SZ')
today_date = datetime.datetime.now().strftime('%Y-%m-%dT')
finish_timestamp = time()+50400
botStartTime = time()
maxResults = '"100"'
inPlayOnly = "false"
locale = '"en"'
sort = '"FIRST_TO_START"'
marketProjection = '["EVENT","RUNNER_METADATA", "MARKET_DESCRIPTION", "RUNNER_DESCRIPTION"]'
competitionIds = '["10547970","12375833","10932509","81","12298986","9404054","194215","13","67387"]'
# "competitionIds": '+str(competitionIds)+'

#URLS
bet_url = "https://api.betfair.com/exchange/betting/json-rpc/v1/"
acct_url = 'https://api.betfair.com/exchange/account/json-rpc/v1'


#LOGIN TO BETFAIR
# ssoid = 'IL4pOkJ1uX1M6RZKDeX1PMWmgoJSo4Fhkfsnv7CjheQ='
ssoid = login(username, password, delayed_app_key)
print(ssoid)

def getCompetitionsTypes():
    req = '{"jsonrpc": "2.0", "method": "SportsAPING/v1.0/listCompetitions", "params": {"filter":{ "eventTypeIds": ' + str(eventTypeId) + '} }, "id": 1}'
    print ('Calling listEventTypes to get event Type ID')
    headers = {'X-Application': delayed_app_key, 'X-Authentication': ssoid, 'content-type': 'application/json'}

    req = requests.post(bet_url, data=req.encode('utf-8'), headers=headers)
    resp = req.json()
    print(resp)
    json_obj = json.dumps(resp, indent=4)
    with open('results.json', 'w') as file:
        file.write(json_obj)
        
def get_odds(marketId, selectionId):
    req = '{"jsonrpc": "2.0", "method": "SportsAPING/v1.0/listRunnerBook", "params": ' \
            '{"marketId":"' + str(marketId) + '","selectionId":"' + str(selectionId) + '" }, "id": 1}'
    headers = {'X-Application': delayed_app_key, 'X-Authentication': ssoid, 'content-type': 'application/json'}
    #
    req = requests.post(bet_url, data=req.encode('utf-8'), headers=headers)
    resp = req.json()
    odds = resp['result'][0]['runners'][0]['lastPriceTraded']
    return odds
        
getCompetitionsTypes()