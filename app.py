# ================== tahmid_bot_final_working.py ==================
import json
import asyncio
import aiohttp
import ssl
import gzip
import time
import threading
import random
import sqlite3
from datetime import datetime
from Crypto.Cipher import AES
from Crypto.Util.Padding import pad, unpad
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes
import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# ================== إعدادات البوت ==================
BOT_TOKEN = "8670120476:AAF3N2TTN_k_m9HETEizzswG5cGvqBPY_oI"
ALLOWED_GROUP_ID = -1004297548500
DEVELOPER_ID = 6129372969
DEVELOPER_USERNAME = "@LORD1_A"
CHANNEL_URL = "https://t.me/LORDXXXXXXXXXX"
API_KEY = "STALINAWYq"
INFO_API_URL = "https://stalin-info-sit2.vercel.app/sendINFO/bcse?uid={uid}&region=&key={api_key}"

# ================== دوال التشفير ==================
AES_KEY = bytes([89, 103, 38, 116, 99, 37, 68, 69, 117, 104, 54, 37, 90, 99, 94, 56])
AES_IV = bytes([54, 111, 121, 90, 68, 114, 50, 50, 69, 51, 121, 99, 104, 106, 77, 37])

def ua():
    versions = ['4.0.18P6', '4.0.19P7', '4.0.20P1', '4.1.0P3', '4.1.5P2', '4.2.1P8',
                '4.2.3P1', '5.0.1B2', '5.0.2P4', '5.1.0P1', '5.2.0B1', '5.2.5P3',
                '5.3.0B1', '5.3.2P2', '5.4.0P1', '5.4.3B2', '5.5.0P1', '5.5.2P3']
    models = ['SM-A125F', 'SM-A225F', 'SM-A325M', 'SM-A515F', 'SM-A725F', 'SM-M215F', 'SM-M325FV',
              'Redmi 9A', 'Redmi 9C', 'POCO M3', 'POCO M4 Pro', 'RMX2185', 'RMX3085',
              'moto g(9) play', 'CPH2239', 'V2027', 'OnePlus Nord', 'ASUS_Z01QD']
    android_versions = ['9', '10', '11', '12', '13', '14']
    languages = ['en-US', 'es-MX', 'pt-BR', 'id-ID', 'ru-RU', 'hi-IN']
    countries = ['USA', 'MEX', 'BRA', 'IDN', 'RUS', 'IND']
    return f"GarenaMSDK/{random.choice(versions)}({random.choice(models)};Android {random.choice(android_versions)};{random.choice(languages)};{random.choice(countries)};)"

def encPacket(hexStr, k, iv):
    return AES.new(k, AES.MODE_CBC, iv).encrypt(pad(bytes.fromhex(hexStr), 16)).hex()

def encVarint(n):
    if n < 0: return b''
    h = []
    while True:
        b = n & 0x7F
        n >>= 7
        if n: b |= 0x80
        h.append(b)
        if not n: break
    return bytes(h)

def createVarint(field, value):
    return encVarint((field << 3) | 0) + encVarint(value)

def createLength(field, value):
    hdr = encVarint((field << 3) | 2)
    enc = value.encode() if isinstance(value, str) else value
    return hdr + encVarint(len(enc)) + enc

def createProto(fields):
    pkt = bytearray()
    for f, v in fields.items():
        if isinstance(v, dict):
            nested = createProto(v)
            pkt.extend(createLength(f, nested))
        elif isinstance(v, int):
            pkt.extend(createVarint(f, v))
        elif isinstance(v, (str, bytes)):
            pkt.extend(createLength(f, v))
    return pkt

def decodeHex(h):
    r = hex(h)[2:]
    return "0" + r if len(r) == 1 else r

def genPkt(pkt, n, k, iv):
    enc = encPacket(pkt, k, iv)
    l = decodeHex(len(enc) // 2)
    if len(l) == 2: hdr = n + "000000"
    elif len(l) == 3: hdr = n + "00000"
    elif len(l) == 4: hdr = n + "0000"
    elif len(l) == 5: hdr = n + "000"
    else: hdr = n + "000000"
    return bytes.fromhex(hdr + l + enc)

def openRoom(k, iv):
    f = {1: 2, 2: {1: 1, 2: 15, 3: 5, 4: "SPAM ROOM", 5: "1", 6: 12, 7: 1,
                    8: 1, 9: 1, 11: 1, 12: 2, 14: 36981056,
                    15: {1: "IDC3", 2: 126, 3: "ME"},
                    16: "\u0001\u0003\u0004\u0007\t\n\u000b\u0012\u000f\u000e\u0016\u0019\u001a \u001d",
                    18: 2368584, 27: 1, 34: "\u0000\u0001", 40: "en", 48: 1,
                    49: {1: 21}, 50: {1: 36981056, 2: 2368584, 5: 2}}}
    return genPkt(str(createProto(f).hex()), '0E15', k, iv)

def spmRoom(k, iv, uid):
    f = {1: 22, 2: {1: int(uid)}}
    return genPkt(str(createProto(f).hex()), '0E15', k, iv)

def friendRequest(k, iv, target_uid):
    f = {1: 4, 2: {1: int(target_uid), 3: ""}}
    return genPkt(str(createProto(f).hex()), '0E16', k, iv)

# ================== دوال المصادقة ==================
async def gAccess(u, p, session):
    url = "https://100067.connect.garena.com/oauth/guest/token/grant"
    headers = {
        "Host": "100067.connect.garena.com",
        "User-Agent": ua(),
        "Content-Type": "application/x-www-form-urlencoded",
        "Accept-Encoding": "gzip, deflate, br",
        "Connection": "close"
    }
    data = {
        "uid": str(u),
        "password": str(p),
        "response_type": "token",
        "client_type": "2",
        "client_secret": "2ee44819e9b4598845141067b281621874d0d5d7af9d8f7e00c1e54715b7d1e3",
        "client_id": "100067"
    }
    try:
        async with session.post(url, headers=headers, data=data, ssl=False, timeout=15) as resp:
            if resp.status == 200:
                js = await resp.json()
                return js.get('access_token'), js.get('open_id')
    except:
        pass
    return None, None

async def majorLogin(pyl, session):
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    conn = aiohttp.TCPConnector(ssl=ctx)
    async with aiohttp.ClientSession(connector=conn) as sess:
        headers = {
            'X-Unity-Version': '2022.3.47f1',
            'ReleaseVersion': 'OB54',
            'Content-Type': 'application/x-www-form-urlencoded',
            'X-GA': 'v1 1',
            'User-Agent': 'UnityPlayer/2022.3.47f1 (UnityWebRequest/1.0, libcurl/8.5.0-DEV)',
            'Host': 'loginbp.ggpolarbear.com',
            'Connection': 'Keep-Alive',
            'Accept-Encoding': 'deflate, gzip'
        }
        try:
            async with sess.post("https://loginbp.ggpolarbear.com/MajorLogin", headers=headers, data=pyl, timeout=20) as resp:
                raw = await resp.read()
                if resp.headers.get('Content-Encoding') == 'gzip':
                    raw = gzip.decompress(raw)
                if resp.status in (200, 201):
                    return raw
        except:
            pass
    return None

async def getPorts(tok, pyl, session):
    headers = {
        'Expect': '100-continue',
        'Authorization': f'Bearer {tok}',
        'X-Unity-Version': '2022.3.47f1',
        'X-GA': 'v1 1',
        'ReleaseVersion': 'OB54',
        'Content-Type': 'application/x-www-form-urlencoded',
        'User-Agent': 'UnityPlayer/2022.3.47f1 (UnityWebRequest/1.0, libcurl/8.5.0-DEV)',
        'Host': 'clientbp.ggpolarbear.com',
        'Connection': 'close',
        'Accept-Encoding': 'deflate, gzip'
    }
    try:
        async with session.post("https://clientbp.ggpolarbear.com/GetLoginData", headers=headers, data=pyl, ssl=False, timeout=20) as resp:
            raw = await resp.read()
            from google.protobuf import descriptor_pool as _descriptor_pool
            from google.protobuf import symbol_database as _symbol_database
            from google.protobuf.internal import builder as _builder
            DESCRIPTOR = _descriptor_pool.Default().AddSerializedFile(b'\n\x15GetLoginDataRes.proto\"\xa4\x01\n\x0cGetLoginData\x12\x12\n\nAccountUID\x18\x01 \x01(\x04\x12\x0e\n\x06Region\x18\x03 \x01(\t\x12\x13\n\x0b\x41\x63\x63ountName\x18\x04 \x01(\t\x12\x16\n\x0eOnline_IP_Port\x18\x0e \x01(\t\x12\x0f\n\x07\x43lan_ID\x18\x14 \x01(\x03\x12\x16\n\x0e\x41\x63\x63ountIP_Port\x18  \x01(\t\x12\x1a\n\x12\x43lan_Compiled_Data\x18\x37 \x01(\tb\x06proto3')
            _builder.BuildMessageAndEnumDescriptors(DESCRIPTOR, globals())
            _builder.BuildTopDescriptorsAndMessages(DESCRIPTOR, 'GetLoginDataRes_pb2', globals())
            GetLoginData = globals()['GetLoginData']
            msg = GetLoginData()
            msg.ParseFromString(raw)
            a1 = msg.AccountIP_Port
            a2 = msg.Online_IP_Port
            return a1[:len(a1)-6], a1[len(a1)-5:], a2[:len(a2)-6], a2[len(a2)-5:]
    except:
        return None, None, None, None

def getKiv(raw):
    try:
        from google.protobuf import descriptor_pool as _descriptor_pool
        from google.protobuf import symbol_database as _symbol_database
        from google.protobuf.internal import builder as _builder
        DESCRIPTOR = _descriptor_pool.Default().AddSerializedFile(b'\n\x13MajorLoginRes.proto\"|\n\rMajorLoginRes\x12\x13\n\x0b\x61\x63\x63ount_uid\x18\x01 \x01(\x04\x12\x0e\n\x06region\x18\x02 \x01(\t\x12\r\n\x05token\x18\x08 \x01(\t\x12\x0b\n\x03url\x18\n \x01(\t\x12\x11\n\ttimestamp\x18\x15 \x01(\x03\x12\x0b\n\x03key\x18\x16 \x01(\x0c\x12\n\n\x02iv\x18\x17 \x01(\x0c\x62\x06proto3')
        _builder.BuildMessageAndEnumDescriptors(DESCRIPTOR, globals())
        _builder.BuildTopDescriptorsAndMessages(DESCRIPTOR, 'MajorLoginRes_pb2', globals())
        MajorLoginRes = globals()['MajorLoginRes']
        msg = MajorLoginRes()
        msg.ParseFromString(raw)
        return msg.timestamp, msg.key, msg.iv
    except:
        return None, None, None

def buildAuth(jwtTok, k, iv, ts):
    try:
        dec = pyjwt.decode(jwtTok, options={"verify_signature": False})
        enc = hex(dec['account_id'])[2:]
        tsH = decodeHex(ts)
        jH = jwtTok.encode().hex()
        hLen = hex(len(encPacket(jH, k, iv)) // 2)[2:]
        padMap = {9: '0000000', 8: '00000000', 10: '000000', 7: '000000000'}
        pad = padMap.get(len(enc), '00000000')
        return f'0115{pad}{enc}{tsH}00000{hLen}' + encPacket(jH, k, iv)
    except:
        return None

def build_major_login_payload(open_id, access_token, platform_id=2):
    from google.protobuf import descriptor_pool as _descriptor_pool
    from google.protobuf import symbol_database as _symbol_database
    from google.protobuf.internal import builder as _builder
    DESCRIPTOR = _descriptor_pool.Default().AddSerializedFile(b'\n\x13MajorLoginReq.proto\"\xfa\n\n\nMajorLogin\x12\x12\n\nevent_time\x18\x03 \x01(\t\x12\x11\n\tgame_name\x18\x04 \x01(\t\x12\x13\n\x0bplatform_id\x18\x05 \x01(\x05\x12\x16\n\x0e\x63lient_version\x18\x07 \x01(\t\x12\x17\n\x0fsystem_software\x18\x08 \x01(\t\x12\x17\n\x0fsystem_hardware\x18\t \x01(\t\x12\x18\n\x10telecom_operator\x18\n \x01(\t\x12\x14\n\x0cnetwork_type\x18\x0b \x01(\t\x12\x14\n\x0cscreen_width\x18\x0c \x01(\r\x12\x15\n\rscreen_height\x18\r \x01(\r\x12\x12\n\nscreen_dpi\x18\x0e \x01(\t\x12\x19\n\x11processor_details\x18\x0f \x01(\t\x12\x0e\n\x06memory\x18\x10 \x01(\r\x12\x14\n\x0cgpu_renderer\x18\x11 \x01(\t\x12\x13\n\x0bgpu_version\x18\x12 \x01(\t\x12\x18\n\x10unique_device_id\x18\x13 \x01(\t\x12\x11\n\tclient_ip\x18\x14 \x01(\t\x12\x10\n\x08language\x18\x15 \x01(\t\x12\x0f\n\x07open_id\x18\x16 \x01(\t\x12\x14\n\x0copen_id_type\x18\x17 \x01(\t\x12\x13\n\x0b\x64\x65vice_type\x18\x18 \x01(\t\x12\'\n\x10memory_available\x18\x19 \x01(\x0b\x32\r.GameSecurity\x12\x14\n\x0c\x61\x63\x63\x65ss_token\x18\x1d \x01(\t\x12\x17\n\x0fplatform_sdk_id\x18\x1e \x01(\x05\x12\x1a\n\x12network_operator_a\x18) \x01(\t\x12\x16\n\x0enetwork_type_a\x18* \x01(\t\x12\x1c\n\x14\x63lient_using_version\x18\x39 \x01(\t\x12\x1e\n\x16\x65xternal_storage_total\x18< \x01(\x05\x12\"\n\x1a\x65xternal_storage_available\x18= \x01(\x05\x12\x1e\n\x16internal_storage_total\x18> \x01(\x05\x12\"\n\x1ainternal_storage_available\x18? \x01(\x05\x12#\n\x1bgame_disk_storage_available\x18@ \x01(\x05\x12\x1f\n\x17game_disk_storage_total\x18\x41 \x01(\x05\x12%\n\x1d\x65xternal_sdcard_avail_storage\x18\x42 \x01(\x05\x12%\n\x1d\x65xternal_sdcard_total_storage\x18\x43 \x01(\x05\x12\x10\n\x08login_by\x18I \x01(\x05\x12\x14\n\x0clibrary_path\x18J \x01(\t\x12\x12\n\nreg_avatar\x18L \x01(\x05\x12\x15\n\rlibrary_token\x18M \x01(\t\x12\x14\n\x0c\x63hannel_type\x18N \x01(\x05\x12\x10\n\x08\x63pu_type\x18O \x01(\x05\x12\x18\n\x10\x63pu_architecture\x18Q \x01(\t\x12\x1b\n\x13\x63lient_version_code\x18S \x01(\t\x12\x14\n\x0cgraphics_api\x18V \x01(\t\x12\x1d\n\x15supported_astc_bitset\x18W \x01(\r\x12\x1a\n\x12login_open_id_type\x18X \x01(\x05\x12\x18\n\x10\x61nalytics_detail\x18Y \x01(\x0c\x12\x14\n\x0cloading_time\x18\\ \x01(\r\x12\x17\n\x0frelease_channel\x18] \x01(\t\x12\x12\n\nextra_info\x18^ \x01(\t\x12 \n\x18\x61ndroid_engine_init_flag\x18_ \x01(\r\x12\x0f\n\x07if_push\x18\x61 \x01(\x05\x12\x0e\n\x06is_vpn\x18\x62 \x01(\x05\x12\x1c\n\x14origin_platform_type\x18\x63 \x01(\t\x12\x1d\n\x15primary_platform_type\x18\x64 \x01(\t\"5\n\x0cGameSecurity\x12\x0f\n\x07version\x18\x06 \x01(\x05\x12\x14\n\x0chidden_value\x18\x08 \x01(\x04\x62\x06proto3')
    _builder.BuildMessageAndEnumDescriptors(DESCRIPTOR, globals())
    _builder.BuildTopDescriptorsAndMessages(DESCRIPTOR, 'MajorLoginReq_pb2', globals())
    MajorLogin = globals()['MajorLogin']
    major_login = MajorLogin()
    major_login.event_time = str(datetime.now())[:-7]
    major_login.game_name = "free fire"
    major_login.platform_id = platform_id
    major_login.client_version = "1.126.1"
    major_login.system_software = "Android OS 9 / API-28 (PQ3B.190801.10101846/G9650ZHU2ARC6)"
    major_login.system_hardware = "Handheld"
    major_login.telecom_operator = "Verizon"
    major_login.network_type = "WIFI"
    major_login.screen_width = 1920
    major_login.screen_height = 1080
    major_login.screen_dpi = "280"
    major_login.processor_details = "ARM64 FP ASIMD AES VMH | 2865 | 4"
    major_login.memory = 3003
    major_login.gpu_renderer = "Adreno (TM) 640"
    major_login.gpu_version = "OpenGL ES 3.1 v1.46"
    major_login.unique_device_id = "Google|34a7dcdf-a7d5-4cb6-8d7e-3b0e448a0c57"
    major_login.client_ip = "223.191.51.89"
    major_login.language = "en"
    major_login.open_id = open_id
    major_login.open_id_type = "4"
    major_login.device_type = "Handheld"
    memory_available = major_login.memory_available
    memory_available.version = 55
    memory_available.hidden_value = 81
    major_login.access_token = access_token
    major_login.platform_sdk_id = 1
    major_login.network_operator_a = "Verizon"
    major_login.network_type_a = "WIFI"
    major_login.client_using_version = "7428b253defc164018c604a1ebbfebdf"
    major_login.external_storage_total = 36235
    major_login.external_storage_available = 31335
    major_login.internal_storage_total = 2519
    major_login.internal_storage_available = 703
    major_login.game_disk_storage_available = 25010
    major_login.game_disk_storage_total = 26628
    major_login.external_sdcard_avail_storage = 32992
    major_login.external_sdcard_total_storage = 36235
    major_login.login_by = 3
    major_login.library_path = "/data/app/com.dts.freefireth-YPKM8jHEwAJlhpmhDhv5MQ==/lib/arm64"
    major_login.reg_avatar = 1
    major_login.library_token = "5b892aaabd688e571f688053118a162b|/data/app/com.dts.freefireth-YPKM8jHEwAJlhpmhDhv5MQ==/base.apk"
    major_login.channel_type = 3
    major_login.cpu_type = 2
    major_login.cpu_architecture = "64"
    major_login.client_version_code = "2019116753"
    major_login.graphics_api = "OpenGLES2"
    major_login.supported_astc_bitset = 16383
    major_login.login_open_id_type = 4
    major_login.analytics_detail = b"FwQVTgUPX1UaUllDDwcWCRBpWAUOUgsvA1snWlBaO1kFYg=="
    major_login.loading_time = 13564
    major_login.release_channel = "android"
    major_login.extra_info = "KqsHTymw5/5GB23YGniUYN2/q47GATrq7eFeRatf0NkwLKEMQ0PK5BKEk72dPflAxUlEBir6Vtey83XqF593qsl8hwY="
    major_login.android_engine_init_flag = 110009
    major_login.if_push = 1
    major_login.is_vpn = 1
    major_login.origin_platform_type = "4"
    major_login.primary_platform_type = "4"
    protobuf_raw = major_login.SerializeToString()
    cipher = AES.new(AES_KEY, AES.MODE_CBC, AES_IV)
    padded = pad(protobuf_raw, AES.block_size)
    encrypted = cipher.encrypt(padded)
    return encrypted, protobuf_raw.hex()

async def login_account(u, p, session):
    try:
        at, oid = await gAccess(u, p, session)
        if not at:
            return None
        encrypted_payload, _ = build_major_login_payload(oid, at)
        raw = await majorLogin(encrypted_payload, session)
        if not raw:
            return None
        ts, k, iv = getKiv(raw)
        if not k:
            return None
        return {'key': k, 'iv': iv, 'uid': u}
    except:
        return None

# ================== قاعدة البيانات ==================
DB_PATH = "bot_data.db"

def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS users
                 (user_id INTEGER PRIMARY KEY, username TEXT, subscription_end INTEGER, credits INTEGER DEFAULT 0, created_at INTEGER)''')
    c.execute('''CREATE TABLE IF NOT EXISTS accounts
                 (uid TEXT PRIMARY KEY, password TEXT, is_active INTEGER DEFAULT 1, added_by INTEGER, added_at INTEGER)''')
    c.execute('''CREATE TABLE IF NOT EXISTS spam_targets
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, target_uid TEXT, user_id INTEGER, started_at INTEGER, is_active INTEGER DEFAULT 1)''')
    c.execute('''CREATE TABLE IF NOT EXISTS spam_logs
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, target_uid TEXT, account_uid TEXT, sent_at INTEGER, status TEXT)''')
    conn.commit()
    conn.close()

def get_user(user_id):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT user_id, username, subscription_end, credits FROM users WHERE user_id=?", (user_id,))
    row = c.fetchone()
    conn.close()
    return row

def add_or_update_user(user_id, username):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    now = int(time.time())
    c.execute("INSERT OR IGNORE INTO users (user_id, username, subscription_end, credits, created_at) VALUES (?, ?, 0, 0, ?)",
              (user_id, username, now))
    c.execute("UPDATE users SET username=? WHERE user_id=?", (username, user_id))
    conn.commit()
    conn.close()

def set_subscription(user_id, days):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    now = int(time.time())
    end = now + (days * 86400)
    c.execute("UPDATE users SET subscription_end=? WHERE user_id=?", (end, user_id))
    conn.commit()
    conn.close()
    return end

def get_active_accounts():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT uid, password FROM accounts WHERE is_active=1")
    rows = c.fetchall()
    conn.close()
    return rows

def get_all_accounts():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT uid, password, is_active, added_by, added_at FROM accounts")
    rows = c.fetchall()
    conn.close()
    return rows

def add_account(uid, password, added_by):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    now = int(time.time())
    c.execute("INSERT OR REPLACE INTO accounts (uid, password, is_active, added_by, added_at) VALUES (?, ?, 1, ?, ?)",
              (uid, password, added_by, now))
    conn.commit()
    conn.close()

def add_spam_target(target_uid, user_id):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    now = int(time.time())
    c.execute("INSERT INTO spam_targets (target_uid, user_id, started_at, is_active) VALUES (?, ?, ?, 1)",
              (target_uid, user_id, now))
    conn.commit()
    conn.close()

def get_active_spam_targets():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT target_uid, user_id FROM spam_targets WHERE is_active=1")
    rows = c.fetchall()
    conn.close()
    return rows

# ================== هيكل الحسابات والسبام ==================
_clis = []
_clis_lock = threading.Lock()
_spam_target = None
_spam_running = False
_spam_stop_event = None
_spam_type = "friend"
_spam_count = 0

class Account:
    def __init__(self, u, p):
        self.u = u
        self.p = p
        self.key = None
        self.iv = None
        self.alive = False
        self.count = 0
        self._start()

    def _start(self):
        thread = threading.Thread(target=self._run_async, daemon=True)
        thread.start()

    def _run_async(self):
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(self._run())
        loop.close()

    async def _run(self):
        while True:
            try:
                async with aiohttp.ClientSession() as session:
                    res = await login_account(self.u, self.p, session)
                    if not res:
                        await asyncio.sleep(10)
                        continue
                    self.key, self.iv = res['key'], res['iv']
                    self.alive = True
                    with _clis_lock:
                        _clis.append(self)
                    print(f'[+] {self.u} متصل')
                    await self._spam()
            except:
                await asyncio.sleep(10)

    async def _spam(self):
        global _spam_count
        while self.alive and _spam_target and _spam_running:
            try:
                if _spam_type == "friend":
                    pkt = friendRequest(self.key, self.iv, _spam_target)
                else:
                    pkt = spmRoom(self.key, self.iv, _spam_target)
                self.count += 1
                _spam_count += 1
                await asyncio.sleep(0.05)
            except:
                await asyncio.sleep(1)

def load_accounts_from_db_and_run():
    accounts = get_active_accounts()
    print(f"🔍 جاري تشغيل {len(accounts)} حساب...")
    for uid, pwd in accounts:
        Account(uid, pwd)
        time.sleep(0.2)

# ================== دوال API ==================
async def get_player_info(uid):
    try:
        url = INFO_API_URL.format(uid=uid, api_key=API_KEY)
        async with aiohttp.ClientSession() as session:
            async with session.get(url, timeout=10) as resp:
                if resp.status == 200:
                    return await resp.json()
                return {'error': f'HTTP {resp.status}'}
    except:
        return {'error': 'Connection failed'}

# ================== دالة عرض الأوامر ==================
def get_help_text():
    return (
        "🔥 TAHMID BOT - SPAM FRIEND 🔥\n\n"
        "👤 Dev: @LORD1_A\n"
        "📢 Channel: https://t.me/LORDXXXXXXXXXX\n\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        "📌 Commands:\n\n"
        "• /start - Welcome\n"
        "• /help - Command List\n"
        "• /info <UID> - Player Info\n"
        "• /friend <UID> - Friend Spam\n"
        "• /room <UID> - Room Spam\n"
        "• /stop - Stop Spam\n"
        "• /status - System Status\n"
        "• /my - My Subscription\n\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        "👑 Developer Commands:\n\n"
        "• /addacc <UID> <Pass> - Add Account\n"
        "• /sub <UID> <Days> - Give Sub\n"
        "• /accounts - Show Accounts\n"
        "• /autospam <UID> <Days> - Auto Spam\n\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        "💳 Subscription: Contact Dev\n"
        "⚡ Only works in group"
    )

# ================== أوامر البوت ==================

def is_allowed_group(update: Update):
    return update.effective_chat.id == ALLOWED_GROUP_ID

def is_developer(user_id):
    return user_id == DEVELOPER_ID

def is_subscribed(user_id):
    user = get_user(user_id)
    if not user:
        return False
    return user[2] > int(time.time()) or is_developer(user_id)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_allowed_group(update):
        await update.message.reply_text("⚠️ هذا البوت يعمل فقط في المجموعة المخصصة.")
        return
    user_id = update.effective_user.id
    username = update.effective_user.username or "مستخدم"
    add_or_update_user(user_id, username)
    await update.message.reply_text(
        "🌟 WELCOME TO TAHMID BOT 🌟\n\n"
        "🔥 SPAM FRIEND REQUEST 🔥\n\n"
        "👤 Dev: @LORD1_A\n"
        "📢 Channel: https://t.me/LORDXXXXXXXXXX\n\n"
        "📌 Use /help for commands\n"
        "💳 For Subscription contact Dev"
    )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_allowed_group(update):
        await update.message.reply_text("⚠️ هذا البوت يعمل فقط في المجموعة المخصصة.")
        return
    await update.message.reply_text(get_help_text())

async def info(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_allowed_group(update):
        return
    user_id = update.effective_user.id
    if not is_subscribed(user_id) and not is_developer(user_id):
        await update.message.reply_text("❌ أنت غير مشترك. تواصل مع المطور للاشتراك.")
        return
    args = context.args
    if not args:
        await update.message.reply_text("⚠️ استخدم: /info <UID>")
        return
    uid = args[0]
    if not uid.isdigit():
        await update.message.reply_text("⚠️ يجب أن يكون UID رقمياً.")
        return
    await update.message.reply_text(f"⏳ جاري جلب معلومات اللاعب {uid}...")
    data = await get_player_info(uid)
    if 'error' in data:
        await update.message.reply_text(f"❌ {data['error']}")
        return
    
    name = data.get('nickname', 'N/A')
    level = data.get('level', 'N/A')
    likes = data.get('likes', 'N/A')
    region = data.get('region', 'N/A')
    br_rank = data.get('br_rank', 'N/A')
    br_points = data.get('br_points', 'N/A')
    cs_rank = data.get('cs_rank', 'N/A')
    cs_points = data.get('cs_points', 'N/A')
    clan = data.get('clan', 'N/A')
    clan_id = data.get('clan_id', 'N/A')
    clan_level = data.get('clan_level', 'N/A')
    clan_members = data.get('clan_members', 'N/A')
    clan_capacity = data.get('clan_capacity', 'N/A')
    title = data.get('title', 'N/A')
    diamond_cost = data.get('diamond_cost', 'N/A')
    season = data.get('season', 'N/A')
    badges = data.get('badges', 'N/A')
    created = data.get('created_at', 'N/A')
    last_login = data.get('last_login', 'N/A')
    pet_id = data.get('pet_id', 'N/A')
    pet_level = data.get('pet_level', 'N/A')
    credit_score = data.get('credit_score', 'N/A')
    is_banned = data.get('is_banned', 'غير محظور')
    signature = data.get('signature', 'لا يوجد')
    
    msg = (
        f"✅ PLAYER INFO\n\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"👤 Nickname: {name}\n"
        f"🆔 UID: {uid}\n"
        f"🌍 Region: {region}\n"
        f"📈 Level: {level}\n"
        f"❤️ Likes: {likes}\n\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"🏆 BR Rank: {br_rank}\n"
        f"🎯 BR Points: {br_points}\n"
        f"⚔️ CS Rank: {cs_rank}\n"
        f"⚡ CS Points: {cs_points}\n\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"💎 Diamond Cost: {diamond_cost}\n"
        f"🔥 Elite Pass: --\n"
        f"🎫 Season: {season}\n"
        f"🏅 Badges: {badges}\n"
        f"🎗 Title: {title}\n"
        f"📦 OB Version: OB54\n\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"📅 Created: {created}\n"
        f"⏱ Last Login: {last_login}\n\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"🐾 Pet ID: {pet_id}\n"
        f"⭐ Pet Level: {pet_level}\n\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"🏰 Guild: {clan}\n"
        f"🆔 Guild ID: {clan_id}\n"
        f"📈 Guild Level: {clan_level}\n"
        f"👥 Members: {clan_members}/{clan_capacity}\n\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"🛡 Credit Score: {credit_score}\n"
        f"🔒 Banned: {is_banned}\n\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"👑 Dev: @LORD1_A\n"
        f"━━━━━━━━━━━━━━━━━━━━"
    )
    await update.message.reply_text(msg)

async def friend(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_allowed_group(update):
        return
    user_id = update.effective_user.id
    if not is_subscribed(user_id) and not is_developer(user_id):
        await update.message.reply_text("❌ أنت غير مشترك. تواصل مع المطور للاشتراك.")
        return
    args = context.args
    if not args:
        await update.message.reply_text("⚠️ استخدم: /friend <UID>")
        return
    target = args[0]
    if not target.isdigit():
        await update.message.reply_text("⚠️ يجب أن يكون UID رقمياً.")
        return
    
    global _spam_target, _spam_running, _spam_stop_event, _spam_type, _spam_count
    if _spam_running and _spam_stop_event:
        _spam_stop_event.set()
        time.sleep(0.5)
    
    _spam_target = target
    _spam_type = "friend"
    _spam_count = 0
    _spam_stop_event = threading.Event()
    _spam_running = True
    add_spam_target(target, user_id)
    
    accounts = get_active_accounts()
    info = await get_player_info(target)
    name = info.get('nickname', target) if 'error' not in info else target
    
    msg = (
        f"🚀 تم بدء سبام الصداقة\n\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"👤 اللاعب: {name}\n"
        f"🆔 UID: {target}\n"
        f"📊 عدد الحسابات المرسلة: {len(accounts)}\n"
        f"📡 الحالة: ✅ يعمل في الخلفية\n\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"👑 Dev: @LORD1_A"
    )
    await update.message.reply_text(msg)

async def room(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_allowed_group(update):
        return
    user_id = update.effective_user.id
    if not is_subscribed(user_id) and not is_developer(user_id):
        await update.message.reply_text("❌ أنت غير مشترك. تواصل مع المطور للاشتراك.")
        return
    args = context.args
    if not args:
        await update.message.reply_text("⚠️ استخدم: /room <UID>")
        return
    target = args[0]
    if not target.isdigit():
        await update.message.reply_text("⚠️ يجب أن يكون UID رقمياً.")
        return
    
    global _spam_target, _spam_running, _spam_stop_event, _spam_type, _spam_count
    if _spam_running and _spam_stop_event:
        _spam_stop_event.set()
        time.sleep(0.5)
    
    _spam_target = target
    _spam_type = "room"
    _spam_count = 0
    _spam_stop_event = threading.Event()
    _spam_running = True
    add_spam_target(target, user_id)
    
    accounts = get_active_accounts()
    info = await get_player_info(target)
    name = info.get('nickname', target) if 'error' not in info else target
    
    msg = (
        f"🚀 تم بدء سبام الغرفة\n\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"👤 اللاعب: {name}\n"
        f"🆔 UID: {target}\n"
        f"📊 عدد الحسابات المرسلة: {len(accounts)}\n"
        f"📡 الحالة: ✅ يعمل في الخلفية\n\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"👑 Dev: @LORD1_A"
    )
    await update.message.reply_text(msg)

async def stop_spam(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_allowed_group(update):
        return
    global _spam_running, _spam_stop_event
    if _spam_running and _spam_stop_event:
        _spam_stop_event.set()
        _spam_running = False
        await update.message.reply_text("✅ تم إيقاف السبام")
    else:
        await update.message.reply_text("⚠️ لا يوجد سبام نشط")

async def status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_allowed_group(update):
        return
    with _clis_lock:
        total = len(_clis)
        alive = sum(1 for c in _clis if c.alive)
    targets = get_active_spam_targets()
    await update.message.reply_text(
        f"📊 حالة النظام\n\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"🟢 حسابات متصلة: {alive}\n"
        f"🔴 إجمالي الحسابات: {total}\n"
        f"🎯 الهدف: {_spam_target or 'لا يوجد'}\n"
        f"⚡ الحالة: {'يعمل' if _spam_running else 'متوقف'}\n"
        f"📋 أهداف نشطة: {len(targets)}\n"
        f"📤 إجمالي الطلبات: {_spam_count}\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"👑 Dev: @LORD1_A"
    )

async def my(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_allowed_group(update):
        return
    user_id = update.effective_user.id
    user = get_user(user_id)
    if not user:
        await update.message.reply_text("⚠️ أنت غير مسجل. استخدم /start للتسجيل.")
        return
    remaining = max(0, user[2] - int(time.time()))
    days = remaining // 86400
    hours = (remaining % 86400) // 3600
    await update.message.reply_text(
        f"👤 معلومات حسابك\n\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"🆔 المعرف: {user[0]}\n"
        f"📛 اليوزر: @{user[1] or 'غير محدد'}\n"
        f"⏳ المتبقي: {days} يوم {hours} ساعة\n"
        f"💰 الرصيد: {user[3]} وحدة\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"👑 Dev: @LORD1_A"
    )

# ================== أوامر المطور ==================

async def addacc(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_allowed_group(update):
        return
    user_id = update.effective_user.id
    if not is_developer(user_id):
        await update.message.reply_text("❌ هذا الأمر للمطور فقط.")
        return
    args = context.args
    if len(args) < 2:
        await update.message.reply_text("⚠️ استخدم: /addacc <UID> <كلمة المرور>")
        return
    uid, pwd = args[0], args[1]
    add_account(uid, pwd, user_id)
    Account(uid, pwd)
    await update.message.reply_text(f"✅ تم إضافة الحساب {uid} وتشغيله.")

async def sub(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_allowed_group(update):
        return
    user_id = update.effective_user.id
    if not is_developer(user_id):
        await update.message.reply_text("❌ هذا الأمر للمطور فقط.")
        return
    args = context.args
    if len(args) < 2:
        await update.message.reply_text("⚠️ استخدم: /sub <UID> <أيام>")
        return
    target_uid, days = int(args[0]), int(args[1])
    end_time = set_subscription(target_uid, days)
    await update.message.reply_text(f"✅ تم منح اشتراك {days} يوم للمستخدم {target_uid} (ينتهي في {datetime.fromtimestamp(end_time)})")

async def accounts_list(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_allowed_group(update):
        return
    user_id = update.effective_user.id
    if not is_developer(user_id):
        await update.message.reply_text("❌ هذا الأمر للمطور فقط.")
        return
    accs = get_all_accounts()
    msg = "📋 الحسابات النشطة:\n\n"
    for uid, pwd, active, added_by, added_at in accs[:20]:
        msg += f"• {uid} -> {'✅ نشط' if active else '❌ غير نشط'}\n"
    if len(accs) > 20:
        msg += f"\n... و {len(accs) - 20} حساب آخر"
    await update.message.reply_text(msg)

async def auto_spam(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_allowed_group(update):
        return
    user_id = update.effective_user.id
    if not is_developer(user_id):
        await update.message.reply_text("❌ هذا الأمر للمطور فقط.")
        return
    args = context.args
    if len(args) < 2:
        await update.message.reply_text("⚠️ استخدم: /autospam <UID> <أيام>")
        return
    target, days = args[0], int(args[1])
    await update.message.reply_text(f"✅ بدأ السبام التلقائي على {target} لمدة {days} يوم")

# ================== ترحيل الحسابات ==================
def migrate_accounts_from_json():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    now = int(time.time())
    count = 0
    
    try:
        with open("accs.json", "r") as f:
            accs = json.load(f)
            for uid, pwd in accs.items():
                c.execute("INSERT OR IGNORE INTO accounts (uid, password, is_active, added_by, added_at) VALUES (?, ?, 1, 0, ?)",
                          (uid, pwd, now))
                count += 1
        print(f"✅ تم ترحيل {len(accs)} حساب من accs.json")
    except:
        pass
    
    try:
        with open("acont.json", "r") as f:
            acont = json.load(f)
            for uid, pwd in acont.items():
                c.execute("INSERT OR IGNORE INTO accounts (uid, password, is_active, added_by, added_at) VALUES (?, ?, 1, 0, ?)",
                          (uid, pwd, now))
                count += 1
        print(f"✅ تم ترحيل {len(acont)} حساب من acont.json")
    except:
        pass
    
    conn.commit()
    conn.close()
    print(f"✅ إجمالي الحسابات: {count}")

# ================== تشغيل البوت ==================
async def main():
    init_db()
    migrate_accounts_from_json()
    print("🔍 جاري تشغيل الحسابات...")
    
    def run_accounts():
        load_accounts_from_db_and_run()
    
    threading.Thread(target=run_accounts, daemon=True).start()
    
    app = Application.builder().token(BOT_TOKEN).build()
    
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("info", info))
    app.add_handler(CommandHandler("friend", friend))
    app.add_handler(CommandHandler("room", room))
    app.add_handler(CommandHandler("stop", stop_spam))
    app.add_handler(CommandHandler("status", status))
    app.add_handler(CommandHandler("my", my))
    app.add_handler(CommandHandler("addacc", addacc))
    app.add_handler(CommandHandler("sub", sub))
    app.add_handler(CommandHandler("accounts", accounts_list))
    app.add_handler(CommandHandler("autospam", auto_spam))
    
    print("🚀 تشغيل البوت...")
    await app.initialize()
    await app.start()
    await app.updater.start_polling()
    
    while True:
        await asyncio.sleep(3600)

if __name__ == "__main__":
    asyncio.run(main())