import requests
from private import username, password, delayed_app_key
from utils import login
import datetime
import pytz
from time import time
import json
import csv


# bot_starttime = datetime.datetime.now().strftime('%Y-%m-%dT%H:%M:%SZ')
# with open('/home/ec2-user/rossbot/bot2/jobLog.txt', 'a') as f:
#     f.write(f'Started bot at {bot_starttime}\n')

rocco_tz = pytz.timezone('Europe/London')
#FILTERS
eventTypeId = '["1"]'
countryCode = '["UK"]'
# marketTypeCode = '["WIN"]'
marketStartTime = datetime.datetime.now(tz=rocco_tz)
marketStartTime = marketStartTime.strftime('%Y-%m-%dT%H:%M:%SZ')
today_date = datetime.datetime.now().strftime('%Y-%m-%dT')
finish_timestamp = time()+50400
botStartTime = time()
maxResults = '"1000"'
inPlayOnly = "false"
locale = '"en"'
sort = '"FIRST_TO_START"'
marketProjection = '["EVENT"]' #"MARKET_DESCRIPTION", "RUNNER_METADATA", "RUNNER_DESCRIPTION"
marketProjection2 = '["EVENT","RUNNER_METADATA","RUNNER_DESCRIPTION"]' #"MARKET_DESCRIPTION", 
'["1.215825379","1.215837173","1.215825139","1.215825259","1.215825499","1.215825019","1.215824899","1.215824779","1.215921454","1.215958795","1.215959564","1.215955696","1.215898228","1.215963646","1.215964778","1.215963526","1.215964243","1.215964658"]'
typeCodes = '["MATCH_ODDS"]'
bettingTypes = '["ODDS"]'
virtualise = "true"
priceData = '["EX_BEST_OFFERS"]'
# "competitionIds": '+str(competitionIds)+'

#URLS
bet_url = "https://api.betfair.com/exchange/betting/json-rpc/v1/"
acct_url = 'https://api.betfair.com/exchange/account/json-rpc/v1'


#LOGIN TO BETFAIR
# ssoid = 'Uf5xmQgzm0Ljop2cko19GZHzLww85nDPAg/BJELxW3s='
ssoid = login(username, password, delayed_app_key)
# print(ssoid)

bf_ids = []
# Open file
with open('Competition IDs.csv') as file_obj:
    reader_obj = csv.reader(file_obj)
    count = 0
    for row in reader_obj:
        count += 1
        if row[3] == 'Y' and count > 1:
            bf_ids.append(f'"{row[2]}"')
           
bf_ids = ','.join(bf_ids)
bf_ids = f'[{bf_ids}]'


def get_betfair_data(time_range):
    ids = getEventIds(time_range)
    ids = ','.join(ids)
    ids = f'[{ids}]'
    # print(ids)
    
    events = getEventTypes(time_range, market_ids=ids)
    events_data = []
    for event in events:
        event_data = {}
        if event['marketName'] == "Match Odds":
            marketId = event['marketId']
            runners = event['runners']
            try:
                bfCountryCode = event['event']['countryCode']
            except:
                bfCountryCode = 'INT'
            home = runners[0]['runnerName']
            away = runners[1]['runnerName']
            totalMatched = event['totalMatched']    
            price_data = get_odds(f'["{marketId}"]')
            event_data['bfHomeTeam'] = home
            event_data['bfAwayTeam'] = away
            event_data['bfCountryCode'] = bfCountryCode
            event_data['totalMatched'] = totalMatched
            event_data['bfPriceInfo'] = price_data
            events_data.append(event_data)
    
    return events_data
    
def getEventIds(time_range):
    if 'h' in time_range:
        ts_range = int(time_range.replace('h','')) * 3600
    elif 'm' in time_range:
        ts_range = int(time_range.replace('m','')) * 60
    elif 'd' in time_range:
        ts_range = int(time_range.replace('d','')) * 86400
    else:
        raise Exception('Error: Invalid time range format specified')
        
    marketEndTime = datetime.datetime.now(tz=rocco_tz)+datetime.timedelta(seconds=ts_range)
    marketEndTime = marketEndTime.strftime('%Y-%m-%dT%H:%M:%SZ')
    market_req = '{"jsonrpc": "2.0", "method":"SportsAPING/v1.0/listMarketCatalogue", ' \
                             '"params": {"filter": {"eventTypeIds": ' + str(
                    eventTypeId) + ',  "marketBettingTypes":' + str(bettingTypes) + ', "competitionIds": ' + str(bf_ids) + ', "inPlayOnly":' + str(inPlayOnly) + ', ' \
                    '"marketStartTime": {"from":' + '"' + str(marketStartTime) + '"' + ', "to": ' + '"' + str(marketEndTime) + '"' + '}, "marketTypeCodes":' + str(typeCodes) + '},' \
                    '"locale":' + str( locale) + ', "sort": ' + str(sort) + ', "maxResults": ' + str(
                    maxResults) + ', "marketProjection": ' + str(marketProjection) + ' }, "id": 1}'
    headers = {'X-Application': delayed_app_key, 'X-Authentication': ssoid, 'content-type': 'application/json'}

    req = requests.post(bet_url, data=market_req.encode('utf-8'), headers=headers)
    resp = req.json()
    json_obj = json.dumps(resp, indent=4)
    with open('betfair_result.json', 'w') as file:
        file.write(json_obj)
        
    market_ids = []
    results = resp['result']
    for event in results:
        if event['marketName'] == "Match Odds":
            eventId = event['marketId']
            market_ids.append(f'"{eventId}"')
            
    return market_ids

def getEventTypes(time_range, market_ids):
    if 'h' in time_range:
        ts_range = int(time_range.replace('h','')) * 3600
    elif 'm' in time_range:
        ts_range = int(time_range.replace('m','')) * 60
    elif 'd' in time_range:
        ts_range = int(time_range.replace('d','')) * 86400
    else:
        raise Exception('Error: Invalid time range format specified')
        
    marketEndTime = datetime.datetime.now(tz=rocco_tz)+datetime.timedelta(seconds=ts_range)
    marketEndTime = marketEndTime.strftime('%Y-%m-%dT%H:%M:%SZ')
    print(f'Market End Time: {marketEndTime}')
    market_req = '{"jsonrpc": "2.0", "method":"SportsAPING/v1.0/listMarketCatalogue", ' \
                             '"params": {"filter": {"eventTypeIds": ' + str(eventTypeId) + ',  "marketIds":' + str(market_ids) + ',"inPlayOnly":' + str(inPlayOnly) + ' },' \
                    '"locale":' + str( locale) + ', "sort": ' + str(sort) + ', "maxResults": ' + str(maxResults) + ', "marketProjection": ' + str(marketProjection2) + ' }, "id": 1}'
    print ('Calling listEventTypes')
    headers = {'X-Application': delayed_app_key, 'X-Authentication': ssoid, 'content-type': 'application/json'}

    req = requests.post(bet_url, data=market_req.encode('utf-8'), headers=headers)
    resp = req.json()
    
    results = resp['result']
    return results

def get_odds(marketIds):
    req = '{"jsonrpc": "2.0", "method": "SportsAPING/v1.0/listMarketBook", "params": ' \
            '{"marketIds":' + str(marketIds) + ', "priceProjection": {"priceData": ' + str(priceData) + ', "virtualise": ' +str(virtualise) + '} }, "id": 1}'
    headers = {'X-Application': delayed_app_key, 'X-Authentication': ssoid, 'content-type': 'application/json'}
    #
    req = requests.post(bet_url, data=req.encode('utf-8'), headers=headers)
    resp = req.json()
    results = resp['result']
    price_data = {}
    for result in results:
        try:
            selections = result['runners']
            price_data['1'] = {'Back': selections[0]['ex']['availableToBack'][0]['price'], 'Lay': selections[0]['ex']['availableToLay'][0]['price']}
            price_data['X'] = {'Back': selections[2]['ex']['availableToBack'][0]['price'], 'Lay': selections[2]['ex']['availableToLay'][0]['price']}
            price_data['2'] = {'Back': selections[1]['ex']['availableToBack'][0]['price'], 'Lay': selections[1]['ex']['availableToLay'][0]['price']}
        except:
            pass
    
    return price_data
        
