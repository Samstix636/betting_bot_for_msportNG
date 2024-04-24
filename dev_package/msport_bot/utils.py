import csv            
from pprint import pprint
from itertools import combinations
import random
import aiohttp
from time import perf_counter
import asyncio
import requests


headers = {
        "authority": "www.msport.com",
        "accept": "application/json, text/plain, */*",
        "accept-language": "en-US,en;q=0.6",
        "apilevel": "2",
        "clientid": "WEB",
        "content-type": "application/json",
        "cookie": "UPDATE_COOKIE",
        "devmem": "0.5",
        "network": "undefined",
        "operid": "2",
        "origin": "https://www.msport.com",
        "platform": "WEB",
        # "referer": "https://www.msport.com/ng/web/sports/list/Soccer?t=sr:tournament:851,sr:tournament:17",
        "sec-fetch-dest": "empty",
        "sec-fetch-mode": "cors",
        "sec-fetch-site": "same-origin",
        "sec-gpc": "1",
        "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36",
    }



# def filter_accumulators(accumulators: list) -> list:
    
#     for accumulator in accumulators:
#         for selection in accumulator:
#             if selection['id']
def split_bets_btw_accounts(accumulators:list, accounts:list)->list:
    no_of_accounts = len(accounts)
    no_of_accumulators = len(accumulators)
    # Get average bets per account
    avg_bpa = no_of_accumulators / no_of_accounts
    upper_limit = round(avg_bpa * 1.1)
    lower_limit = round(avg_bpa * 0.9)
    print('avg_bpa(bets_per_account): ',round(avg_bpa, 2), 'lower_bpa: ',lower_limit, 'upper_bpa: ', upper_limit)
    no_of_accumulators_assigned = 0
    for i, account in enumerate(accounts):
        no_of_bets = random.randint(lower_limit, upper_limit)
        if i == len(accounts) - 1 or len(accumulators) < no_of_bets:
            account.update({'bets':accumulators})
            break
        elif no_of_accumulators_assigned < no_of_accumulators:
            no_of_accumulators_assigned += no_of_bets
            selected_bets = accumulators[:no_of_bets]
            accumulators = accumulators[no_of_bets:]
            account.update({'bets': selected_bets})
    
    return accounts
            
# print(split_bets_btw_accounts(accumulators, accounts))
def drop_invalid_account(account:dict)        :
    account['driver'].quit()
    print(f'Dropping account {account["phone"]}')
        

def split_stake_to_accumulators(total_stake:float, accumulators:list[str])-> tuple[int,list[dict]]:
    no_of_bets = len(accumulators)
    avg_stake = total_stake/no_of_bets
    print('avg_stake: ', round(avg_stake,2))
    if avg_stake < 100:
        raise ValueError("Average Stake amount less than N100 which is minimum stake value")
    elif avg_stake < 1000:
        upper_limit = int(round(avg_stake * 1.1, -1))
        lower_limit = int(round(avg_stake * 0.9, -1))
    else: 
        upper_limit = int(round(avg_stake * 1.1, -2))
        lower_limit = int(round(avg_stake * 0.9, -2))
    # print('avg_stake: ',avg_stake, 'lower_stake: ',lower_limit, 'upper_stake: ', upper_limit)
    bet_data = []
    total_expected_stake = 0
    for acc in accumulators:
        if lower_limit < 1000:
            stake = round(random.randint(lower_limit, upper_limit), -1)
        else:
            stake = round(random.randint(lower_limit, upper_limit), -2)
        bet_data.append({'code': acc, 'stake': stake})
        total_expected_stake += stake
    
    return total_expected_stake, bet_data
        
        
     
        
    

def get_betting_accounts(total_stake:float, accounts:list) -> list:
    no_of_accounts = len(accounts)
    half_accounts = round(no_of_accounts/2)
    weighted_stake = total_stake/half_accounts
    print('weighted_stake:', round(weighted_stake, 2))
    valid_accounts_list = []
    for account in accounts:
        if account['balance'] > weighted_stake:
            valid_accounts_list.append(account)
        else:
            print(f'Dropping account {account["phone"]} due to low balance')
    valid_phones = [acc['phone'] for acc in valid_accounts_list]

    no_valid_accounts = len(valid_accounts_list)
    if no_valid_accounts < 4:
        raise ValueError("Insufficient number of valid Accounts")
    elif 4 <= no_valid_accounts < 8:
        betting_accounts = random.sample(valid_accounts_list,k=4)
    else:
        no_betting_accounts = round(no_valid_accounts * 0.6)
        betting_accounts = random.sample(valid_accounts_list,k=no_betting_accounts)
        
    valid_phones = [acc['phone'] for acc in valid_accounts_list]
    betting_phones = [acc['phone'] for acc in betting_accounts]

    for phone in valid_phones:
        if phone not in betting_phones:
            print(f'Dropping account {phone} due to Random Selection')
    return betting_accounts

def map_selection(selection):
    if selection == '1':
        outcome = '1'
        market_id = 1
    elif selection == 'X':
        outcome = '2'
        market_id = 1
    elif selection == '2':
        outcome = '3'
        market_id = 1
    elif selection == '1X':
        outcome = '9'
        market_id = 10
    elif selection == '12':
        outcome = '10'
        market_id = 10
    elif selection == 'X2':
        outcome = '11'
        market_id = 10
    else:
        raise ValueError('Invalid selection')
    
    return outcome, market_id

  

def get_accumulators(k, s):
    
    bets = []
    with open('final_output.csv', mode='r') as csv_file:
        csv_reader = csv.reader(csv_file, delimiter=',')
        line_count = 0
        print('Pre checks for invalid selections...')
        for row in csv_reader:
            # print(row)
            line_count += 1
            if line_count == 1:
                continue
            if row[-1] == 'Y': 
                # print('yes row')
                bet = {}
                bet['id'] = row[2]
                bet['outcome'], bet['market_id'] = map_selection(row[3])
                bet['initial_odds'] = row[5]
                bets.append(bet)
                
    # print('length of available bets: {}'.format(len(bets)))

    accumulators = []
    for i in range(k, s+1):
        comb = combinations(bets, i)
        comb_list = list(comb)
        accumulators.extend(comb_list)
        
    print(f'{len(accumulators)} Valid Accumulators Generated')
    return bets, accumulators

# get_accumulators(4,4)

async def get_codes_for_accumulators(accumulators:list) -> list:
    list_of_bet_codes = []
    payloads = []
    for accumulator in accumulators:
        payload = {'selections': []}
        for selection in accumulator:
            selection_payload = {'eventId': selection['id'], 'marketId': selection['market_id'], 'specifier':'', 'outcomeId':selection['outcome']}
            payload['selections'].append(selection_payload)
        payloads.append(payload)
    results = await main(payloads)
    
    # print(f'Total generated bet codes: {len(results)}')
    return results
    


# Asynchronous function to fetch data from an API
async def fetch_data(payload):
    url = "https://www.msport.com/api/ng/orders/real-sports/order/share"
    async with aiohttp.ClientSession(headers=headers) as session:
        async with session.post(url, json= payload) as response:
            data = await response.json()
            return data['data']['shareCode']


async def main(payloads):
    
    time_before = perf_counter()
    # Use asyncio.gather() to concurrently fetch data from multiple APIs
    results = await asyncio.gather(*(fetch_data(payload) for payload in payloads))
    # print(f'Total time: {perf_counter() - time_before}')
    return results


async def fetch_event_data(match_id):
    url = f"https://www.msport.com/api/ng/facts-center/query/frontend/match/detail?eventId={match_id}"
    payload = ""
    async with aiohttp.ClientSession(headers=headers) as session:
        async with session.post(url, json = payload) as response:
            data = await response.json()
            return data['data']['markets']


async def get_events_data(event_ids):
    # Use asyncio.gather() to concurrently fetch data from multiple APIs
    results = await asyncio.gather(*(fetch_event_data(event_id) for event_id in event_ids))
    # print(f'Total time: {perf_counter() - time_before}')
    return results


def multiplyList(myList):
    # Multiply elements one by one
    result = 1
    for x in myList:
        result = result * x
    return result

def get_running_stakes(headers):
    bets_list = []
    lastEventId = ''
    payload = ""
    while True:
        url = "https://www.msport.com/api/ng/real-sports-game/frontend/order/my-bets"

        querystring = {"type":"0","lastBetId":lastEventId,"limit":"20"}
        response = requests.request("GET", url, headers=headers, params=querystring).json()
        # print(response)
        bets = response['data']['bets']
        if len(bets) > 0:
            bets_list.extend(bets)
            lastEventId = bets[-1]['betId']
        else:
            break
    
    stakes = []
    for bet in bets_list:
        stake = bet['totalStake']
        stakes.append(float(stake))
    total_stake = sum(stakes)
    # print(total_stake)
    return total_stake


def get_live_booking_odds(booking_code):
    url = f"https://www.msport.com/api/ng/orders/real-sports/order/share/{booking_code}"
    response = requests.request("GET", url, headers=headers).json()
    slip = response['data']['bettableBetSlip']
    events_data = []
    for s in slip:
        data = {}
        data['event_id'] = s['event']['eventId']
        data['event'] = f"{s['event']['homeTeam']} vs {s['event']['awayTeam']}"
        data['outcome_odds'] = s['outcome']['odds']
        events_data.append(data)
        
    slip_odds = [float(d['outcome_odds']) for d in events_data]
    total_odds = multiplyList(slip_odds)
    
    
    return events_data, total_odds
      
def check_for_dropped_odds(initial_selections, live_slip):
    invalid_ids = []
    for live_event in live_slip:
        for sel in initial_selections:
            if live_event['event']['eventId'] == sel['id'] and (float(sel['initial_odds']) - 0.02) >= float(live_event['outcome']['odds']):
                invalid_ids.append(f"{live_event['event']['homeTeam']} vs {live_event['event']['awayTeam']}")
    
    return invalid_ids
                
