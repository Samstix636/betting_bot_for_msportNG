from time import sleep
from scrapy.selector import Selector
from pprint import pprint
from selenium.webdriver.remote.remote_connection import LOGGER
from playwright.sync_api import sync_playwright
from playwright.async_api import async_playwright
from playwright.async_api import Page, expect, Request
import json
from time import perf_counter
from threading import Lock
import logging
from datetime import datetime
import sys
import subprocess
import csv
from concurrent.futures import ThreadPoolExecutor
import asyncio
from msport_bot.utils import *
counter = 0
lock = Lock()


class globalBS():
    counter = 0
    total_stake = 0
    potential_wins = []
    accumulator_odds = []
    failed_bets = []
    fail_streak = 0
    account_stakes = []

async def launch_driver(proxy):
    p = await async_playwright().start()
    driver = await p.chromium.launch()
    return driver
    
    
async def login(context, account:dict):
    # print(account)
    
    try:
        page:Page = await context.new_page()
        try:
            await page.goto('https://www.msport.com/ng/web/')
            await page.get_by_placeholder("Mobile Phone").fill(account['phone'])
            await page.get_by_placeholder("Password").fill(account['password'])
            await page.route("**/*", lambda route, request: route.continue_())
        except:
            pass

        # Initialize a list to store API responses
        api_responses = []

        # Intercept network responses
        page.on("response", lambda response: api_responses.append(response))

        # Navigate to a page that makes API requests
        await page.get_by_role("button", name="Login").click()

        # Perform actions on the page that trigger API requests

        # Wait for some time to capture API responses
        # await page.wait_for_timeout(5000) 
        # try:
        await asyncio.sleep(5)
        
        retry_duration = 10  # Adjust as needed
        end_time = asyncio.get_event_loop().time() + retry_duration
        while asyncio.get_event_loop().time() < end_time:
            await asyncio.sleep(2) 
        # Iterate through the captured responses
            for response in api_responses:
                found_bal = False
                # Check if the response is from an API endpoint (customize this condition)
                if "/financialAccounts/balance" in response.url:
                    text_resp =  await response.text()
                    bal_resp = json.loads(text_resp)
                    found_bal = True
                    print(f'Logged in to account: {account["phone"]}')
                    return bal_resp, page
                if found_bal == False:
                    # print(f'Retrying for account: {account["phone"]}')
                    continue
                
        # except:
        #     print(f'Retrying balance Retrieval for account {account["phone"]}')
        #     await asyncio.sleep(5)
            
        #     # Iterate through the captured responses
        #     for response in api_responses:
        #         # Check if the response is from an API endpoint (customize this condition)
        #         if "/financialAccounts/balance" in response.url:
        #             text_resp =  await response.text()
        #             bal_resp = json.loads(text_resp)
        #             print(f'Logged in to account: {account["phone"]}')
        #             return bal_resp, page
    except:
        print('ERROR:: Could Not Log IN')
            
async def get_bets(page:Page):
    requests:list[Request] = []
    await page.route("https://www.msport.com/api/ng/*", lambda route, request: route.continue_())
    # Intercept network responses
    page.on("requestfinished", lambda request: requests.append(request))
    await page.goto('https://www.msport.com/ng/web/my_bets/cashout')
    await asyncio.sleep(5)
    for req in requests:
        if "/order/my-bets" in req.url:
            headers = await req.all_headers()
            return headers
    return None
    

async def load_code(page:Page, bet:dict):
    b_code = bet['code']
    booking_code_box = page.get_by_placeholder("Booking Code")
    await booking_code_box.clear(timeout=5000)
    await booking_code_box.fill(b_code,timeout=5000)
    # await asyncio.sleep(1)
    load_code = page.locator("//form[@class='m-booking-code']//button")
    await load_code.click(timeout=5000)
    # await asyncio.sleep(1)
    stake_box = page.get_by_placeholder("min. 100")
    await stake_box.scroll_into_view_if_needed()
    await stake_box.clear(timeout=5000)
    await stake_box.fill(str(bet['stake']), timeout=5000)
    
    
    
    
    
async def dismiss_popup(page:Page):
    try:
        for pop in await page.locator('//div[contains(@class,"pop")]//*[contains(@class,"close")]').all():
            try:
                await pop.click(timeout=2000)
                print('::Pop-up dismissed')
            except:
                pass
    except:
        try:
            for pop in await page.locator('//div[contains(@class,"dialog")]//*[contains(@class,"close")]').all():
                try:
                    await pop.click(timeout=2000)
                    print('::alert dismissed')
                except:
                    pass
        except:
            pass
            
async def update_failed_bet(bet, total_bets):
    
    percent20_of_bets = round(total_bets * 0.2)
    lock.acquire()
    globalBS.failed_bets.append(bet)
    globalBS.fail_streak +=1
    if len(globalBS.failed_bets) > percent20_of_bets or globalBS.fail_streak >=10:
        status = "Stop"
        globalBS.failed_bets.clear()
        # globalBS.failed_bets.extend(bets)
    else:
        status = 'Continue'
    # unlock the state
    lock.release()
    return status
        
async def check_bets(bet, initial_sel, page:Page):
    responses:list = []
    await page.route("**/*", lambda route, request: route.continue_())
    page.on("response", lambda resp: responses.append(resp))
    await load_code(page, bet)
    retry_duration = 10  # Adjust as needed
    end_time = asyncio.get_event_loop().time() + retry_duration
    while asyncio.get_event_loop().time() < end_time:
        await asyncio.sleep(2) 
        # Iterate through the captured responses
        for response in responses:
            found_resp = False
            # Check if the response is from an API endpoint (customize this condition)
            if "/orders/real-sports/order/share/" in response.url:
                text_resp =  await response.text()
                json_resp = json.loads(text_resp)
                # print('response status: ', json_resp['message'])
                bet_slip = json_resp['data']['bettableBetSlip']
                invalid_ids = check_for_dropped_odds(initial_sel, bet_slip)
                total_odds = multiplyList([float(slip['outcome']['odds']) for slip in bet_slip])
                found_resp = True
                
                return invalid_ids, total_odds
            if found_resp == False:
                # print(f'Waiting 2 more seconds for betslip response')
                continue

def multiplyList(myList):
    # Multiply elements one by one
    result = 1
    for x in myList:
        result = result * x
    return result
            
async def run_msport(payload):
    page:Page = payload['account_with_bets']['page']
    # page.set_default_timeout(timeout=3000)
    bets = payload['account_with_bets']['bets']
    total_bets = payload['total_bets']
    phone = payload['account_with_bets']['phone']
    initial_selections_data = payload['initial_selections_data']
    bets_data = {}
    bets_data['account'] = phone
    bets_data['placed_bets'] = 0
    bets_data['account_stake'] = 0
    
    for bet in bets:
        try:
            try:
                await expect(page.locator('//*[@id="target-betslip"]/div[2]/div[1]/div[1]/div[2]/div/div[2]/div[1]')).not_to_be_attached(timeout=3000)
            except:
                await page.locator('//*[@id="target-betslip"]/div[2]/div[1]/div[1]/div[2]/div/div[2]/div[1]').click(timeout=5000)
                # await page.locator("//a[@class='btn btn--ok'][text()='Confirm']").click(timeout=5000)
                await page.locator("(//a[@class='btn btn--ok'][text()='Confirm'])[last()]").click(timeout=2000)
            try:
                invalids, total_odds = await check_bets(bet, initial_selections_data, page)
                if len(invalids)>0:
                    print('::Skipping invalid events: ', invalids)
                    continue
            except:
                await page.reload()
                await dismiss_popup(page)
                invalids, total_odds = await check_bets(bet, initial_selections_data, page)
                if len(invalids)>0:
                    print('::Skipping invalid events: ', invalids)
                    continue
            try:
                try:
                    await expect(page.locator("//div[@class='m-select-bar--show']")).not_to_be_attached(timeout=3000)
                except:
                    # print('Trying to click out pop up')
                    await page.locator("//div[@class='m-select-bar--show']").click(timeout=3000)
                await page.get_by_role("button", name='Place Bet').click(timeout=5000)
            except:
                await dismiss_popup(page)
                await page.reload()
                invalids, total_odds = await check_bets(bet, initial_selections_data, page)
                if len(invalids)>0:
                    print('::Skipping invalid events: ', invalids)
                    continue
                try:
                    try:
                        await expect(page.locator("//div[@class='m-select-bar--show']")).not_to_be_attached(timeout=3000)
                    except:
                        print('Trying to click out pop up')
                        await page.locator("//div[@class='m-select-bar--show']").click(timeout=3000)
                    await page.get_by_role("button", name='Place Bet').click(timeout=3000)
                except:
                    print(f'::Error while placing bet for accumulator {bet["code"]}. Check error image')
                        
                    await page.screenshot(path=f'error_images/{bet["code"]}_error.png')
                    status = await update_failed_bet(bet, total_bets)
                    if status == "Continue":
                        continue
                    else:
                        print(f'TOO MANY FAILED BETS IN ACCOUNT: {phone}. STOPPING ACCOUNT RUN')
                        break
            try:
                confirm_bet_btn = page.locator("//div[@class='dialog--wrap account-dialog-grpups']//div[@class='m-close-btn']")
                await confirm_bet_btn.click(timeout=5000)
            except:
                await dismiss_popup(page)
                await page.reload()
            
            bets_data['account_stake'] += float(bet['stake'])
            bets_data['placed_bets'] += 1
            potential_win = float(bet['stake']) * total_odds
            lock.acquire()

            local_counter = globalBS.counter
            local_total_stake = globalBS.total_stake
            local_counter += 1
            local_total_stake += float(bet['stake'])
            # await asyncio.sleep(0.1)
            globalBS.counter = local_counter
            globalBS.total_stake = local_total_stake
            globalBS.potential_wins.append(potential_win)
            globalBS.accumulator_odds.append(total_odds)
            globalBS.fail_streak = 0
            
            # unlock the state
            lock.release()
            
            print(f'Bet {bet["code"]} placed successfully in account {phone}. Stake {bet["stake"]}. Pot Win: {round(potential_win, 2)}.  Bet Count: {globalBS.counter}')
        except Exception as e:
            logging.error(f'{e}')
            print(f'::Failed to place bet for accumulator {bet["code"]}')
            await page.screenshot(path=f'error_images/{bet["code"]}_error.png')
            status = await update_failed_bet(bet, total_bets)
            if status == "Continue":
                continue
            else:
                print(f'TOO MANY FAILED BETS IN ACCOUNT: {phone}')
                break
    print(f'finished process in {phone}')
    lock.acquire()
    try:
        if bets_data['account'] in [a['account'] for a in globalBS.account_stakes]:
            for a in globalBS.account_stakes:
                if a['account'] == bets_data['account']:
                    a['placed_bets']+=bets_data['placed_bets']
                    a['account_stake']+=bets_data['account_stake']
                    
        else:
            globalBS.account_stakes.append(bets_data)
    except:
        logging.error(f'{e}')
    lock.release()
    return globalBS
            
            
async def get_account_balance(context, account:dict) -> dict:
    resp_obj, page = await login(context, account)
    headers = await get_bets(page)
    total_stake = get_running_stakes(headers)
    await page.go_back()
    # print("Available Balance: ", resp_obj['data']['avlBal'])
    # print("Total Stake: ", total_stake)
    balance = resp_obj['data']['avlBal']/10000
    account.update({'balance': balance, 'page': page, 'running_stake':total_stake})
    return account
    
    
 
    

async def display_account_balances(accounts):
    accounts_data = []
    balances = []
    stakes = []
    for account in accounts:
        if account['balance'] is None:
            continue
        data = {}
        data['phone'] = account['phone']
        data['balance'] = account['balance']
        data['Running Stake'] = account['running_stake']
        accounts_data.append(data)
        balances.append(account['balance'])
        stakes.append(account['running_stake'])

    balance_sum = sum(balances)
    total_running_stake = sum(stakes)
    
    print("ACCOUNTS BALANCES: ")
    pprint(accounts_data)
    print(f'TOTAL BALANCE FOR ALL {len(balances)} accounts: {round(balance_sum, 2)}')
    print(f'TOTAL RUNNING STAKE FOR ALL {len(balances)} accounts: {round(total_running_stake, 2)}')



    