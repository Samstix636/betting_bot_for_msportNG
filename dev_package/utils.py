import requests

def login(username, password, app_key) -> str:
    headers = {'X-Application': app_key, 'Content-Type': 'application/x-www-form-urlencoded'}
    payload = 'username=' + username + '&password=' + password
    # path = r'C:\Users\ekoko\Desktop\Upwork\Ross P\bot1_cred'

    # status = json_resp['loginStatus']
    try:
        resp = requests.post('https://identitysso-cert.betfair.com/api/certlogin',
                             data=payload,
                             cert=('rocco_app.crt', 'client-2048.pem'),
                             headers=headers

                             )
        json_resp = resp.json()
        print(json_resp)
        return json_resp['sessionToken']
    except Exception as e :
        print(resp.text)
        print(f'Could not login with Login status: {e}')




