import os
import time
import json
import urllib.request
import pandas as pd
from datetime import datetime, timedelta
from pandas.io.json import json_normalize
from selenium import webdriver
from selenium.webdriver.common.desired_capabilities import DesiredCapabilities

# Slack関連の設定を環境変数から読み込む
BOT_USERNAME = os.environ['BOT_USERNAME'] 
SLACK_ENDPOINT_URL = os.environ['SLACK_ENDPOINT_URL'] 
SLACK_CHANNEL = os.environ['SLACK_CHANNEL']
# alphaus.cloudのユーザ名とパスワードを環境変数から読み込む
USER_ID = os.environ['USER_ID']
USER_PS = os.environ['USER_PS']


def getAuthId(user_id, user_ps):
    """
    alphaus.cloudにログインして、APIにアクセスするためのAuthorizationを取得
    
    Parameters
    ----------
    user_id  : string
        alphaus.cloudのユーザ名
    user_ps  : string
        alphaus.cloudのパスワード

    returns
    -------
    auth_id : string
        APIにアクセスするためのAuthorization
    """

    URL = "https://app.alphaus.cloud/wave/login"
    
    options = webdriver.ChromeOptions()
    options.binary_location = "/opt/headless/python/bin/headless-chromium"
    options.add_argument("--headless")
    options.add_argument("--disable-gpu")
    # options.add_argument("--hide-scrollbars")
    options.add_argument("--single-process")
    # options.add_argument("--ignore-certificate-errors")
    options.add_argument("--window-size=880x996")
    options.add_argument("--no-sandbox")
    options.add_argument("--homedir=/tmp")
    
    # ログを取得するために設定
    d = DesiredCapabilities.CHROME
    d['loggingPrefs'] = { 'performance': 'ALL' }

    auth_id = ''
    
    try:
        browser = webdriver.Chrome(
            executable_path="/opt/headless/python/bin/chromedriver",
            options=options,
            desired_capabilities=d
        )

        # サイトにアクセス
        browser.get(URL)
        # ログイン
        browser.find_element_by_id("user_id").send_keys(user_id)
        browser.find_element_by_id("user_pass").send_keys(user_ps)
        time.sleep(3)
        browser.find_element_by_tag_name("button").click()
    
        time.sleep(10)
        
        # ログの「performance」からAuthorizationを取得
        for entry_json in browser.get_log('performance'):
            entry = json.loads(entry_json['message'])
            if entry['message']['method'] != 'Network.responseReceived':
                continue;
            if 'response' in entry['message']['params']: 
                if 'requestHeaders' in entry['message']['params']['response']:
                    if 'cookie' in entry['message']['params']['response']['requestHeaders']:
                        auth_id = entry['message']['params']['response']['requestHeaders']['cookie'].split(';')[0].split('=')[1]
    finally:
        browser.close()

    return 'Bearer ' + auth_id


def getCost(auth_id):
    """
    alphaus.cloudにAPI接続して今月の費用を取得
    
    Parameters
    ----------
    auth_id : string
        APIにアクセスするためのAuthorization

    returns
    -------
    sum : int
        今月の総コスト
     : [string]
        コスト内訳
    """
    pd.options.display.float_format = '{:.1f}'.format
    # 費用取得期間
    today = datetime.today()
    lastyear = today - timedelta(days=365)
    
    # API費用を取得
    req = urllib.request.Request('https://api.alphaus.cloud/m/wave/reports/company/monthly?from=' + lastyear.strftime('%Y-%m-01') + '&to=' + today.strftime('%Y-%m-01') + '&by=service&vendor=aws')
    req.add_header('Authorization', auth_id)
    with urllib.request.urlopen(req) as res:
        json_data = json.loads(res.read().decode('utf-8'))
    
    # 取得した情報をから今月分を取得
    cols = ['id', 'date', 'unblended_cost', 'true_unblended_cost', 'blended_cost', 'timestamp']
    df_items = pd.DataFrame(columns=cols)
    
    for entry_json in json_data['aws']:
        df_items = df_items.append(json_normalize(entry_json, 'date', 'id'), ignore_index=True )
    
    df = df_items[df_items['date'] == today.strftime('%Y-%m')].loc[:,['id', 'true_unblended_cost']]
    df_new = df.rename(columns={'id': 'Service', 'true_unblended_cost': 'Cost'})

    return df_new['Cost'].sum(), df_new.sort_values('Cost', ascending=False).to_string(index=False)
  

def send_slack_message(text, username, channel, slack_endpoint_url):
    """
    Slackにメッセージを送信
    
    Parameters
    ----------
    text : string
        送信メッセージ
    username : string
        送信元ユーザ名
    channel : string
        送信先チャンネル
    slack_endpoint_url : string
        SlackのエンドポイントURL
    returns
    -------
    body : string
        レスポンス
    """
    
    data = {
        'username':username, # 表示名
        'text':text, # 内容
        'channel': channel # 送信先チャンネル
    }
    method = "POST"
    headers = {"Content-Type" : "application/json"}
    req = urllib.request.Request(slack_endpoint_url, method=method, data=json.dumps(data).encode(), headers=headers)
    with urllib.request.urlopen(req) as res:
        body = res.read()

    return body
    
    
def lambda_handler(event, context):
    auth_id = getAuthId(USER_ID, USER_PS)

    if auth_id != '':
        costall, msg = getCost(auth_id)
    else:
        msg = 'Not a valid account name or password.'
    #print(msg)
    #msg = 'this month costs: $ ' + str("{:.1f}".format(costall)) + '\n\n```' + msg + '```'
    print('this month costs: $ ' + str("{:.1f}".format(costall)) + '\n\n```' + msg + '```')
    send_slack_message(msg, BOT_USERNAME, SLACK_CHANNEL, SLACK_ENDPOINT_URL)

    return {
        'statusCode': 200,
        'body': json.dumps('Success!')
    }
