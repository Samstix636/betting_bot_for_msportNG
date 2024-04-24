from datetime import datetime
import json
import time
from time import sleep
from play import *
from msport_bot.utils import *
from time import perf_counter
from threading import Lock
import logging
import sys
from concurrent.futures import ThreadPoolExecutor
from playwright.async_api import async_playwright
from aioconsole import ainput



async def get_accumulators_stats(accumulators):
    max_accumulator_odds = 0
    max_accumulator = None
    min_accumulator_odds = 10000000000000
    min_accumulator = None
    for accumulator in accumulators:
        acc_odds = [float(acc['initial_odds']) for acc in accumulator]
        total_odds = multiplyList(acc_odds)
        # print('accumulator odds: ', total_odds)
        if total_odds > max_accumulator_odds:
            max_accumulator_odds = total_odds
            max_accumulator = accumulator
        if total_odds < min_accumulator_odds:
            min_accumulator_odds = total_odds
            min_accumulator = accumulator
    
    acc_list = [min_accumulator, max_accumulator]
    min_acc_code, max_acc_code = await get_codes_for_accumulators(acc_list)
    return min_acc_code, max_acc_code
            

def multiplyList(myList):
    # Multiply elements one by one
    result = 1
    for x in myList:
        result = result * x
    return result 

def get_input_data():
    accounts = []
    with open('accounts.csv') as file_obj:
        reader_obj = csv.reader(file_obj)
        count = 0
        for row in reader_obj:
            count += 1
            if count == 1:
                continue
            account = {}
            account['phone'], account['password'], account['proxy'] = row[0], row[1], row[2]
            accounts.append(account)
    
    with open('inputs.csv') as file_obj:
        reader_obj = csv.reader(file_obj)
        count = 0
        data = {}
        for row in reader_obj:
            if row[0] == 'Minimum Fold':
                data['Minimum Fold'] = row[1]
            elif row[0] == 'Maximum Fold':
                data['Maximum Fold'] = row[1]
        
    return accounts, data
                

async def create_multiple_contexts():
    accounts, inputs = get_input_data()
    
    print('Launching browsers...')
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        context_list = []
        no_accounts = len(accounts)

        # Create multiple contexts dynamically
        for account in accounts:  # Create 3 contexts as an example; adjust as needed
        
            context = await browser.new_context()
            context_list.append(context)
        print(f'Initialized {no_accounts} browsers')

        accessed_accounts = []
        no_contexts = len(context_list)
            
        # with ThreadPoolExecutor(max_workers=no_contexts) as executor:
        #     # accounts = await asyncio.gather(*(get_account_balance(context, accounts[i]) for i, context in enumerate(context_list)))
        #     accounts = await asyncio.gather(
        #         *[loop.create_task(get_account_balance(context, accounts[i])) for i, context in enumerate(context_list)]
        # )
        #     # ips = executor.map(get_ip, drivers)
        # accounts_list = list(accounts)
        
        accounts_list = []
        unthreaded = no_contexts
        threaded = 0
        no_of_threads = 3
        while True:
            if unthreaded > no_of_threads:
                with ThreadPoolExecutor(max_workers=no_of_threads) as executor:
                    # results = executor.map(get_account_balance, drivers[threaded:threaded+4], accounts[threaded:threaded+4])
                    results = await asyncio.gather(
                        *[loop.create_task(get_account_balance(context, accounts[i+threaded])) for i, context in enumerate(context_list[threaded:threaded+no_of_threads])]
                            )
                acc_list = list(results)
                accounts_list.extend(acc_list)
                unthreaded-=no_of_threads
                threaded+=no_of_threads
                
            elif unthreaded == 0:
                break
            else:
                with ThreadPoolExecutor(max_workers=unthreaded) as executor:
                    # results = executor.map(get_account_balance, drivers[threaded:], accounts[threaded:])
                    results = await asyncio.gather(
                        *[loop.create_task(get_account_balance(context, accounts[i+threaded])) for i, context in enumerate(context_list[threaded:])]
                            )
                acc_list = list(results)
                accounts_list.extend(acc_list)
                threaded+=unthreaded
                unthreaded = 0
                
   
        
        await display_account_balances(accounts_list)
        
        
        while True:
            is_to_bet = await ainput('Do you want to place bets (y/n) >>')
            if is_to_bet in ['y','Y']:
                pass
            else:
                break
            try:
                print('--------------------------------------------------------------------------'*2)
                k = inputs['Minimum Fold']
                s = inputs['Maximum Fold']
                total_input_stake = await ainput('Enter Total Stake Amount >')
                k, s, total_input_stake = int(k), int(s), float(total_input_stake)
                
                print('--------------------------------------------------------------------------'*2)
                # Get valid accounts
                valid_accounts = get_betting_accounts(total_stake=total_input_stake, accounts=accounts_list)
                #Exit drivers for accounts not in valid accounts
                print('--------------------------------------------------------------------------'*2)
                # [drop_invalid_account(a) for a in accounts_list if a['phone'] not in [v['phone'] for v in valid_accounts]]
                
                print(f'No of Valid accounts: {len(valid_accounts)}')
                #Filter and Get valid accumulators
                time_before = perf_counter()

                initial_bets_data, accumulators = get_accumulators(k,s)
                min_accumulator, max_accumulator = await get_accumulators_stats(accumulators)
                # pprint(f'accumulators_stats:  {accumulators_stats}')
                print('--------------------------------------------------------------------------')
                #Get betting codes for accumulators
                booking_codes = await get_codes_for_accumulators(accumulators) # -> ['bxbxs','bsbssb']
                # print('First Ten booking codes: ', booking_codes[:10])
                #Get stake data for each accumulator code and total expected stake
                total_expected_stake, accumulators_with_stakes = split_stake_to_accumulators(total_stake=total_input_stake, accumulators=booking_codes) #-> (2000, [{'code': 'a', 'stake': 200}, {'code': 'b', 'stake': 200}])
                print(f'Total Expected stake: {total_expected_stake}')
                print('--------------------------------------------------------------------------')
                
                # Split and assign list of accumulator bets to each account
                accounts_with_bets = split_bets_btw_accounts(accumulators=accumulators_with_stakes, accounts=valid_accounts) # accounts_with_bets would be in the format: [{'phone': 'phone', 'password': 'password', 'proxy': 'proxy', 'balance': 'balance', 'driver': 'driver', 'bets': [{'code': 1, 'stake': 100}, {'code': 2, 'stake':200}]}]
                accounts_data = list(accounts_with_bets)
                accounts_with_bets = [{'account_with_bets': acc, "initial_selections_data":initial_bets_data, 'total_bets':len(accumulators_with_stakes)} for acc in accounts_data]
                    
                    
                no_valid_drivers = len(valid_accounts)
                    
                start_time = time.time()
                with ThreadPoolExecutor(max_workers=no_valid_drivers) as executor:
                    # placed_bets_info = executor.map(run_msport, accounts_with_bets)
                    placed_bets_info = await asyncio.gather(
                        *[loop.create_task(run_msport(acc)) for acc in accounts_with_bets]
                        )
                
                result_classes = list(placed_bets_info)
                global_class:globalBS = result_classes[0]
                failed_bets = global_class.failed_bets
                global_class.failed_bets = []
                twenty_percent_of_total_bets = len(accumulators_with_stakes) * 0.2
                if len(failed_bets) < twenty_percent_of_total_bets:
                    retries = 3
                    retry_count = 0
                    while 0 < len(failed_bets) and retry_count < retries:
                        retry_count += 1
                        #Assign failed bets to random account
                        print("failed_bets: ", failed_bets)
                        print('::Retrying Failed Bets')
                        random_acct_to_use = random.choice(accounts_with_bets)
                        random_acct_to_use['account_with_bets'].update({'bets': failed_bets})
                        # with ThreadPoolExecutor(max_workers=1) as executor:
                        # placed_bets_info = executor.map(run_msport, accounts_with_bets)
                        global_class:globalBS = await run_msport(random_acct_to_use)
                        
                        failed_bets = global_class.failed_bets
                    
                break
            except KeyboardInterrupt:
                break
            except Exception as e:
                logging.error(f'Error: {e}', exc_info=True)
                break
        try:
            all_accumulator_odds = global_class.accumulator_odds
            all_potential_wins = global_class.potential_wins
            bet_count = global_class.counter
            total_actual_stake = global_class.total_stake
            max_accumulator_odds = round(max(all_accumulator_odds), 2)
            least_accumulator_odds = round(min(all_accumulator_odds), 2)
            avg_accumulator_odds = sum(all_accumulator_odds)/len(all_accumulator_odds)
            avg_accumulator_odds = round(avg_accumulator_odds, 2)
            potential_max_win = sum(all_potential_wins)
            potential_max_win = round(potential_max_win, 2)
            print('------------------------------------SUMMARY--------------------------------------')
            print(f"TOTAL NUMBER OF EXPECTED BETS: {len(booking_codes)} | NUMBER OF ACTUAL BETS PLACED: {bet_count}.")
            print(f"TOTAL EXPECTED STAKE: {total_expected_stake} | ACTUAL TOTAL STAKE: {total_actual_stake}")
            print(f"ACCUMULATOR WITH HIGHEST ODDS OF {max_accumulator_odds}: {max_accumulator}. ")
            print(f"ACCUMULATOR WITH LOWEST ODDS OF {least_accumulator_odds}: {min_accumulator}")
            print(f"AVERAGE ACCUMULATOR ODDS: {avg_accumulator_odds}")
            print(f'POTENTIAL MAXIMUM WIN AMOUNT: {potential_max_win}')
            print('-----------------------------INDIVIDUAL ACCOUNT SUMMARY--------------------------------')
            for a in global_class.account_stakes:
                print(a)
            print('--------------------------------------------------------------------------')
            
                
            
            finish_time = time.time()
            print(f'Time taken to place all bets {finish_time - start_time} secs')
        except:
            pass

        # Close pages and contexts when done
        for context in context_list:
            await context.close()

        # Close the browser
        await browser.close()


if __name__ == '__main__':
    loop = asyncio.new_event_loop()

    # 2) set the current event loop for the current OS thread ✅
    asyncio.set_event_loop(loop)
    loop.run_until_complete(create_multiple_contexts())