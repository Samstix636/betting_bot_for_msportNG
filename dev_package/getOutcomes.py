import pprint
from private import bot2_app_key, bot2_pass, bot2_user
import pygsheetS
import datetime
import requests
from utils import login
import re

marketStartTime = datetime.datetime.now() - datetime.timedelta(hours=24)
marketStartTime = marketStartTime.strftime('%Y-%m-%dT%H:%M:%SZ')
marketEndTime = datetime.datetime.now()+datetime.timedelta(hours=24)
marketEndTime = marketEndTime.strftime('%Y-%m-%dT%H:%M:%SZ')

today_date = datetime.datetime.now().strftime('%Y-%m-%dT')
eventTypeId = '["7"]'
print(str(eventTypeId))



bet_url = "https://api.betfair.com/exchange/betting/json-rpc/v1/"
acct_url = 'https://api.betfair.com/exchange/account/json-rpc/v1'

# # #CONNECT TO GOOGLE SHEET
gc = pygsheets.authorize(service_file='secret_key.json')
sht1 = gc.open_by_key('1RKoSFzGWdBJy5wBNYHm0RIpb78wFOCfXl0ozp1QTWOg')
wks = sht1.worksheet_by_title('InformRacingBot')
print("connected to Googlesheet")

ssoid = login(bot2_user, bot2_pass, bot2_app_key)
print(ssoid)


def get_betIds(raceDate) -> list:
    betIds = []
    rows = wks.get_all_values(include_tailing_empty=False, include_tailing_empty_rows=False, returnas='matrix')
    for row in rows:
        if raceDate in row[0]:
            betIds.append(row[9])
    return betIds

def save_to_gsheet(data_list):
    try:
        rows = wks.get_all_values(include_tailing_empty=False, include_tailing_empty_rows=False, returnas='matrix')
        prev_index_count = int(len(rows))
        wks.update_row(index=prev_index_count + 1, values=[data_list])
        sheet_status = 'saved'
    except Exception as e:
        sheet_status = e
    print(sheet_status)


id_list = []
betId_list = get_betIds('2021-12')
for ids in betId_list:
    id = int(ids)
    id_list.append(id)

print(str(id_list))


req = '{"jsonrpc": "2.0", "method": "SportsAPING/v1.0/listClearedOrders", "params": ' \
              '{"betStatus": "SETTLED","betIds":'+str(id_list)+', "side":"BACK"}, "id": 1}'
headers = {'X-Application': bot2_app_key, 'X-Authentication': ssoid, 'content-type': 'application/json'}

req = requests.post(bet_url, data=req.encode('utf-8'), headers=headers)
resp = req.json()
pprint.pprint(resp)
results = resp['result']['clearedOrders']
for result in results:
    try:
        betId = result['betId']
    except:
        continue
    pricereq = result['priceMatched']
    print(pricereq)
    outcome = result['betOutcome']
    if outcome == 'WON':
        pv = 1
        point = (pv * float(pricereq))-1
    else:
        point = -1




    cell = wks.find(pattern=betId, cols=(9,10))
    # print(cell)
    match = (str(cell[0])).split(' ')[1]
    cellNo = re.findall(r'\d+', match)
    wks.update_value(addr=f'k{cellNo[0]}', val=point)
    wks.update_value(addr=f'l{cellNo[0]}', val=pricereq)
