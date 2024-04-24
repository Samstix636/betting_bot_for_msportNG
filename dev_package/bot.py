from betfair import get_betfair_data
from msport import get_msport_data
from pprint import pprint
from fuzzywuzzy import fuzz
from fuzzywuzzy import process
import json
import logging
import csv



def get_match_score(home:str, away:str, home_options: list, away_options: list):
    homeScore = process.extract(home, home_options, scorer=fuzz.token_sort_ratio, limit=4)
    awayScore = process.extract(away, away_options, scorer=fuzz.token_sort_ratio, limit=4)
    return homeScore[0], awayScore[0]

def average(a, b):
    avg = (a + b)/2
    return avg

with open('inputs.csv') as file_obj:
    reader_obj = csv.reader(file_obj)
    count = 0
    for row in reader_obj:
        if row[0] == 'Minimum Odds':
            try:
                min_odds = float(row[1])
            except:
                raise ValueError('Invalid Minimum Odds')
        elif row[0] == 'Maximum Odds':
            try:
                max_odds = float(row[1])
            except:
                raise ValueError('Invalid Maximum Odds')
        elif row[0] == 'Time Period':
            try:
                time_range = str(row[1])
            except:
                raise ValueError('Invalid Time Period')
        elif row[0] == 'Betfair Matched Amount':
            try:
                bf_match_amt = float(row[1])
            except:
                raise ValueError('Invalid Betfair Matched Amount')
        elif row[0] == 'Minimum EV':
            try:
                min_ev = float(row[1])
            except:
                raise ValueError('Invalid Minium EV')
        if count == 7:
            break
        count+=1

print('Read inputs successfully')
#Scrape the betfair and msport events
betfairEvents = get_betfair_data(time_range)
msportEvents = get_msport_data(min_odds, max_odds)

final_data = []

#Match the events between betfair and msport and drop events that have matched amount lower than the specified bf matched amount
for bf in betfairEvents:
    if bf['totalMatched'] < bf_match_amt:
        continue
    matched_data = None
    # print('==========================')
    prev_home_score, prev_away_score = 0, 0
    for msportEvent in msportEvents:
        home_result, away_result = get_match_score(bf['bfHomeTeam'], bf['bfAwayTeam'], [msportEvent['msportHomeTeam']], [msportEvent['msportAwayTeam']])
        if home_result[1] > 50 and away_result[1] > 50 and bf['bfCountryCode'] == msportEvent['msportCountryCode']:
            # print(home_result, away_result)
            if (home_result[1] >= prev_home_score or home_result[0] in bf['bfHomeTeam'] or bf['bfHomeTeam'] in home_result[0]) and (away_result[1] >= prev_away_score or away_result[0] in bf['bfAwayTeam'] or bf['bfAwayTeam'] in away_result[0]):
                prev_home_score, prev_away_score = home_result[1], away_result[1]
                matched_data = msportEvent

    if matched_data is not None:
        bf.update(matched_data)
        final_data.append(bf)
        
json_obj = json.dumps(final_data, indent=4)
with open('initial_results.json', 'w') as file:
    file.write(json_obj)  
    

#Calculate the averages, probability matrix and EV for the events
for data in final_data:  
    try:
        newPriceInfo_1 = average(data['bfPriceInfo']['1']['Back'], data['bfPriceInfo']['1']['Lay'])
    except:
        newPriceInfo_1 = 1000000000000000
    try:
        newPriceInfo_X = average(data['bfPriceInfo']['X']['Back'], data['bfPriceInfo']['X']['Lay'])
    except:
        newPriceInfo_X = 1000000000000000
    try:
        newPriceInfo_2 = average(data['bfPriceInfo']['2']['Back'], data['bfPriceInfo']['2']['Lay'])
    except:
        newPriceInfo_2 = 1000000000000000
    inv1, invX, inv2 = 1/newPriceInfo_1, 1/newPriceInfo_X, 1/newPriceInfo_2
    inv1X = inv1+invX
    inv12 = inv1 + inv2
    invX2 = invX + inv2
    
    try:
        ev1 = float(data['msport_market']['1']) * inv1
        ev1 = round((ev1 - 1), 3)
    except:
        ev1 = -100000000
    try:
        evX = float(data['msport_market']['X']) * invX
        evX = round((evX - 1), 3)
    except:
        evX = -100000000
    try:
        ev2 = float(data['msport_market']['2']) * inv2
        ev2 = round((ev2 - 1), 3)
    except:
        ev2 = -100000000
    try:
        ev1X = float(data['msport_market']['1X']) * inv1X
        ev1X = round((ev1X - 1), 3)
    except:
        ev1X = -100000000
    try:
        ev12 = float(data['msport_market']['12']) * inv12
        ev12 = round((ev12 - 1), 3)
    except:
        ev12 = -100000000
    try:
        evX2 = float(data['msport_market']['X2']) * invX2
        evX2 = round((evX2 - 1), 3)
    except:
        evX2 = -100000000
    
    new1X, new12, newX2 = round(1/inv1X, 3), round(1/inv12, 3), round(1/invX2, 3)
    
    data['bfPriceInfo']['1'], data['bfPriceInfo']['X'], data['bfPriceInfo']['2'] = newPriceInfo_1, newPriceInfo_X, newPriceInfo_2
    data['bfPriceInfo']['1X'], data['bfPriceInfo']['12'], data['bfPriceInfo']['X2'] = new1X, new12, newX2
    data['ev'] = {'1': ev1, 'X':evX, '2':ev2, '1X':ev1X, '12': ev12, 'X2': evX2}


json_obj = json.dumps(final_data, indent=4)
with open('results.json', 'w') as file:
    file.write(json_obj)

# Remove outcomes with EV less than specified minimum EV
for data in final_data:
    try:
        if data['ev']['1'] < min_ev:
            del data['bfPriceInfo']['1']
            del data['msport_market']['1']
            del data['ev']['1']
        if data['ev']['X'] < min_ev:
            del data['bfPriceInfo']['X']
            del data['msport_market']['X']
            del data['ev']['X']
        if data['ev']['2'] < min_ev:
            del data['bfPriceInfo']['2']
            del data['msport_market']['2']
            del data['ev']['2']
        if data['ev']['1X'] < min_ev:
            del data['bfPriceInfo']['1X']
            del data['msport_market']['1X']
            del data['ev']['1X']
        if data['ev']['12'] < min_ev:
            del data['bfPriceInfo']['12']
            del data['msport_market']['12']
            del data['ev']['12']
        if data['ev']['X2'] < min_ev:
            del data['bfPriceInfo']['X2']
            del data['msport_market']['X2']
            del data['ev']['X2']
    except Exception as e:
        logging.error(e, exc_info=True)
        print('ERROR FOR DATA: ')
        print(data)
        

# get maximum EV outcome
outputs = []
for data in final_data:
    output = {}
    if data['ev'] == {}:
        continue
    max_sel = max(data['ev'], key=data['ev'].get)
    output['homeTeam'] = data['bfHomeTeam']
    output['awayTeam'] = data['bfAwayTeam']
    output['msportEventId'] = data['msportEventId']
    output['outcome'] = max_sel
    output['betfairOdds'] = round(data['bfPriceInfo'][max_sel], 3)
    output['msportOdds'] = round(float(data['msport_market'][max_sel]), 3)
    output['EV'] = data['ev'][max_sel]
    output['Select'] = 'Y'
    outputs.append(output)

print('======================= Final Result ============================')
pprint(outputs)

csv_columns = ['homeTeam','awayTeam','msportEventId','outcome', 'betfairOdds', 'msportOdds', 'EV', 'Select']
csv_file = "outfile.csv"
try:
    with open(csv_file, 'w') as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=csv_columns)
        writer.writeheader()
        # for data in outputs:
        writer.writerows(outputs)
        # for key, value in dict1.items():
        #     writer.writerow([key, value])
except IOError:
    print("I/O error: Close csv file if it is opened in any application.")

try:
    with open('outfile.csv', newline='') as in_file:
        with open('final_output.csv', 'w', newline='') as out_file:
            writer = csv.writer(out_file)
            for row in csv.reader(in_file):
                if row:
                    writer.writerow(row)
except:
    print("I/O error: Close csv file if it is opened in any application.")
print('======================= Program finished =========================')
    
# for bf_event in betfairEvents:
#     if bf_event['totalMatched'] < bf_match_amt:
#         betfairEvents.remove(bf_event)
        
    

