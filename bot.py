import time
import re
import json
import os
import logging
import threading
from threading import Thread, Event, Lock
import requests
import phonenumbers
from phonenumbers import geocoder
from datetime import datetime, timedelta
import pycountry

# ═══════════════════════════════════════════════════════════════
# 🔐 تحميل المتغيرات
# ═══════════════════════════════════════════════════════════════
def load_env():
    if os.path.exists('.env'):
        with open('.env', 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    os.environ[key.strip()] = value.strip()

load_env()

BOT_TOKEN = os.environ.get("BOT_TOKEN", "")
MAIN_ADMIN_ID = int(os.environ.get("MAIN_ADMIN_ID", "0"))
NUMBERS_ADMIN_ID = int(os.environ.get("NUMBERS_ADMIN_ID", "0"))
OTP_GROUP = int(os.environ.get("OTP_GROUP_ID", "0"))
GROUP_LINK = os.environ.get("GROUP_LINK", "")
CHANNEL_LINK = os.environ.get("CHANNEL_LINK", "")
DEVELOPER_LINK = os.environ.get("DEVELOPER_LINK", "")
NUMBERPANEL_API_URL = os.environ.get("NUMBERPANEL_API_URL", "https://numberpanel.tech")
NUMBERPANEL_API_TOKEN = os.environ.get("NUMBERPANEL_API_TOKEN", "np_live_ygwxxtf3R8H6VuM43h5dkXbrS0navp")
BOT_USERNAME = os.environ.get("BOT_USERNAME", "")

if not BOT_TOKEN:
    raise ValueError("BOT_TOKEN غير موجود!")
if MAIN_ADMIN_ID == 0:
    raise ValueError("MAIN_ADMIN_ID غير موجود!")

# ═══════════════════════════════════════════════════════════════
# 📝 Logging
# ═══════════════════════════════════════════════════════════════
os.makedirs("logs", exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.FileHandler(f"logs/bot_{datetime.now().strftime('%Y%m%d')}.log", encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("OTP_Bot")

# ═══════════════════════════════════════════════════════════════
# 🔒 أقفال
# ═══════════════════════════════════════════════════════════════
USERS_LOCK = Lock()
REFERRALS_LOCK = Lock()
collected_codes_lock = Lock()
my_numbers_lock = Lock()
code_owners_lock = Lock()
np_last_code_lock = Lock()
known_countries_lock = Lock()
available_countries_lock = Lock()

# ═══════════════════════════════════════════════════════════════
# 📱 ملفات
# ═══════════════════════════════════════════════════════════════
COLLECTED_CODES_FILE = "collected_codes.json"
MY_NUMBERS_FILE = "my_numbers.json"
MY_NUMBERS_SENT_FILE = "my_numbers_sent.json"
NP_LAST_CODE_FILE = "np_last_code.json"
CODE_OWNERS_FILE = "code_owners.json"
KNOWN_COUNTRIES_FILE = "known_countries.json"
AVAILABLE_COUNTRIES_FILE = "available_countries.json"

collected_codes = []
available_countries_cache = {}

# ═══════════════════════════════════════════════════════════════
# 🌍 جدول أكواد الدول
# ═══════════════════════════════════════════════════════════════
COUNTRY_PREFIXES = {
    "IL": "972", "EG": "20", "SA": "966", "AE": "971", "IQ": "964",
    "SY": "963", "RU": "7", "US": "1", "GB": "44", "MA": "212",
    "DZ": "213", "TN": "216", "LY": "218", "JO": "962", "LB": "961",
    "PS": "970", "KW": "965", "QA": "974", "BH": "973", "OM": "968",
    "YE": "967", "SD": "249", "TG": "228", "HT": "509", "CF": "236",
    "PK": "92", "TZ": "255", "PE": "51", "BF": "226", "AM": "374",
    "GE": "995", "AZ": "994", "TR": "90", "IN": "91", "ID": "62",
    "PH": "63", "MY": "60", "SG": "65", "TH": "66", "VN": "84",
    "BD": "880", "LK": "94", "NP": "977", "CN": "86", "JP": "81",
    "KR": "82", "AU": "61", "NZ": "64", "BR": "55", "AR": "54",
    "MX": "52", "CA": "1", "CL": "56", "CO": "57", "VE": "58",
    "EC": "593", "DE": "49", "FR": "33", "IT": "39", "ES": "34",
    "PT": "351", "NL": "31", "BE": "32", "CH": "41", "AT": "43",
    "SE": "46", "NO": "47", "DK": "45", "FI": "358", "IE": "353",
    "GR": "30", "PL": "48", "RO": "40", "BG": "359", "CZ": "420",
    "SK": "421", "HU": "36", "UA": "380", "NG": "234", "KE": "254",
    "GH": "233", "ZA": "27", "UG": "256", "MZ": "258", "ZM": "260",
    "ZW": "263", "AO": "244", "CM": "237", "SN": "221", "CI": "225",
    "GN": "224", "ML": "223", "NE": "227", "TD": "235", "MR": "222",
    "CV": "238", "GM": "220", "SL": "232", "LR": "231", "BJ": "229",
    "GA": "241", "CG": "242", "CD": "243", "GQ": "240", "ST": "239",
    "ET": "251", "SO": "252", "DJ": "253", "ER": "291", "SS": "211",
    "RW": "250", "BI": "257", "MG": "261", "MU": "230", "SC": "248",
    "KM": "269", "MW": "265", "LS": "266", "SZ": "268", "BW": "267",
    "NA": "264", "KZ": "7", "UZ": "998", "TM": "993", "TJ": "992",
    "KG": "996", "AF": "93", "IR": "98", "MN": "976", "MM": "95",
    "KH": "855", "LA": "856", "BN": "673", "MV": "960", "BT": "975",
    "DO": "1", "CU": "53", "JM": "1", "TT": "1", "BS": "1",
    "BB": "1", "BZ": "501", "GT": "502", "HN": "504", "SV": "503",
    "NI": "505", "CR": "506", "PA": "507", "BO": "591", "PY": "595",
    "UY": "598", "GY": "592", "SR": "597", "FJ": "679", "PG": "675",
    "SB": "677", "VU": "678", "WS": "685", "TO": "676", "TV": "688",
    "KI": "686", "NR": "674", "PW": "680", "FM": "691", "MH": "692",
    "BY": "375", "MD": "373", "AL": "355", "MK": "389", "ME": "382",
    "RS": "381", "BA": "387", "HR": "385", "SI": "386", "XK": "383",
    "MT": "356", "CY": "357", "IS": "354", "LU": "352", "LI": "423",
    "AD": "376", "MC": "377", "SM": "378", "VA": "379",
    "EE": "372", "LV": "371", "LT": "370",
}

def number_matches_country(number, country_code):
    cleaned = re.sub(r'\D', '', str(number))
    if not cleaned:
        return False
    prefix = COUNTRY_PREFIXES.get(country_code)
    if prefix:
        return cleaned.startswith(prefix)
    try:
        cleaned_with_plus = '+' + cleaned if not cleaned.startswith('+') else cleaned
        parsed = phonenumbers.parse(cleaned_with_plus, None)
        region = phonenumbers.region_code_for_number(parsed)
        return region == country_code
    except:
        return False

# ═══════════════════════════════════════════════════════════════
# 🎨 أيقونات الخدمات
# ═══════════════════════════════════════════════════════════════
SERVICE_ICONS = {
    "whatsapp": "📞", "telegram": "✈️", "facebook": "📘", "instagram": "📸",
    "tiktok": "🎵", "google": "🔍", "netflix": "🎬", "twitter": "🐦",
    "discord": "🎮", "uber": "🚗", "amazon": "📦", "paypal": "💳",
    "openai": "🤖", "tinder": "❤️",
}

def get_service_icon(service_name):
    if not service_name:
        return "🌐"
    s = str(service_name).lower()
    for key, icon in SERVICE_ICONS.items():
        if key in s:
            return icon
    return "🌐"

def mask_number_partial(number):
    s = re.sub(r'\D', '', str(number))
    if len(s) <= 6:
        return s
    return s[:3] + "•" * (len(s) - 6) + s[-3:]

def clean_number(num_str):
    if num_str is None:
        return ""
    return re.sub(r'\D', '', str(num_str))

def extract_otp(msg):
    if not msg:
        return None
    otp_match = re.search(r'\d{3}[-\s]?\d{3,4}|\d{4,8}', str(msg))
    return otp_match.group(0) if otp_match else None

def auto_delete_message(chat_id, message_id, delay=300):
    def delete():
        time.sleep(delay)
        try:
            bot.delete_message(chat_id, message_id)
            logger.info(f"🗑️ تم حذف رسالة من {chat_id}")
        except Exception as e:
            logger.debug(f"فشل حذف: {e}")
    Thread(target=delete, daemon=True).start()

# ═══════════════════════════════════════════════════════════════
# 🌍 أسماء الدول والأعلام
# ═══════════════════════════════════════════════════════════════
COUNTRIES_NAMES_AR = {
    "PK": "🇵🇰 باكستان", "HT": "🇭🇹 هايتي", "TG": "🇹🇬 توجو",
    "BF": "🇧🇫 بوركينا فاسو", "LB": "🇱🇧 لبنان", "TZ": "🇹🇿 تنزانيا",
    "PE": "🇵🇪 بيرو", "CF": "🇨🇫 أفريقيا الوسطى",
    "AM": "🇦🇲 أرمينيا", "GE": "🇬🇪 جورجيا", "AZ": "🇦🇿 أذربيجان",
    "US": "🇺🇸 أمريكا", "GB": "🇬🇧 بريطانيا", "DE": "🇩🇪 ألمانيا",
    "FR": "🇫🇷 فرنسا", "CA": "🇨🇦 كندا", "RU": "🇷🇺 روسيا",
    "TR": "🇹🇷 تركيا", "ID": "🇮🇩 إندونيسيا", "BR": "🇧🇷 البرازيل",
    "EG": "🇪🇬 مصر", "SA": "🇸🇦 السعودية", "MA": "🇲🇦 المغرب",
    "DZ": "🇩🇿 الجزائر", "TN": "🇹🇳 تونس", "LY": "🇱🇾 ليبيا",
    "IN": "🇮🇳 الهند", "NG": "🇳🇬 نيجيريا", "KE": "🇰🇪 كينيا",
    "GH": "🇬🇭 غانا", "ZA": "🇿🇦 جنوب أفريقيا", "MY": "🇲🇾 ماليزيا",
    "CI": "🇨🇮 ساحل العاج", "UA": "🇺🇦 أوكرانيا", "PL": "🇵🇱 بولندا",
    "RO": "🇷🇴 رومانيا", "IT": "🇮🇹 إيطاليا", "ES": "🇪🇸 إسبانيا",
    "PT": "🇵🇹 البرتغال", "NL": "🇳🇱 هولندا", "BE": "🇧🇪 بلجيكا",
    "CH": "🇨🇭 سويسرا", "SE": "🇸🇪 السويد", "NO": "🇳🇴 النرويج",
    "DK": "🇩🇰 الدنمارك", "IE": "🇮🇪 أيرلندا", "GR": "🇬🇷 اليونان",
    "CZ": "🇨🇿 التشيك", "VN": "🇻🇳 فيتنام", "TH": "🇹🇭 تايلاند",
    "PH": "🇵🇭 الفلبين", "SG": "🇸🇬 سنغافورة", "BD": "🇧🇩 بنغلاديش",
    "NP": "🇳🇵 نيبال", "LK": "🇱🇰 سريلانكا", "IQ": "🇮🇶 العراق",
    "JO": "🇯🇴 الأردن", "AE": "🇦🇪 الإمارات", "KW": "🇰🇼 الكويت",
    "QA": "🇶🇦 قطر", "BH": "🇧🇭 البحرين", "OM": "🇴🇲 عمان",
    "YE": "🇾🇪 اليمن", "SD": "🇸🇩 السودان", "SY": "🇸🇾 سوريا",
    "PS": "🇵🇸 فلسطين", "UZ": "🇺🇿 أوزبكستان", "KZ": "🇰🇿 كازاخستان",
    "AF": "🇦🇫 أفغانستان", "AL": "🇦🇱 ألبانيا", "AD": "🇦🇩 أندورا",
    "AO": "🇦🇴 أنغولا", "AG": "🇦🇬 أنتيغوا وبربودا", "AR": "🇦🇷 الأرجنتين",
    "AW": "🇦🇼 أروبا", "AU": "🇦🇺 أستراليا", "AT": "🇦🇹 النمسا",
    "BS": "🇧🇸 الباهاما", "BB": "🇧🇧 بربادوس", "BY": "🇧🇾 بيلاروسيا",
    "BZ": "🇧🇿 بليز", "BJ": "🇧🇯 بنين", "BT": "🇧🇹 بوتان",
    "BO": "🇧🇴 بوليفيا", "BA": "🇧🇦 البوسنة", "BW": "🇧🇼 بوتسوانا",
    "BN": "🇧🇳 بروناي", "BG": "🇧🇬 بلغاريا", "BI": "🇧🇮 بوروندي",
    "KH": "🇰🇭 كمبوديا", "CM": "🇨🇲 الكاميرون", "CV": "🇨🇻 الرأس الأخضر",
    "CL": "🇨🇱 تشيلي", "CN": "🇨🇳 الصين", "CO": "🇨🇴 كولومبيا",
    "KM": "🇰🇲 جزر القمر", "CG": "🇨🇬 الكونغو", "CD": "🇨🇩 الكونغو الديمقراطية",
    "CR": "🇨🇷 كوستاريكا", "HR": "🇭🇷 كرواتيا", "CU": "🇨🇺 كوبا",
    "CY": "🇨🇾 قبرص", "DJ": "🇩🇯 جيبوتي", "DM": "🇩🇲 دومينيكا",
    "DO": "🇩🇴 الدومينيكان", "EC": "🇪🇨 الإكوادور", "SV": "🇸🇻 السلفادور",
    "GQ": "🇬🇶 غينيا الاستوائية", "ER": "🇪🇷 إريتريا", "EE": "🇪🇪 إستونيا",
    "ET": "🇪🇹 إثيوبيا", "FJ": "🇫🇯 فيجي", "FI": "🇫🇮 فنلندا",
    "GA": "🇬🇦 الغابون", "GM": "🇬🇲 غامبيا", "GT": "🇬🇹 غواتيمالا",
    "GN": "🇬🇳 غينيا", "GW": "🇬🇼 غينيا بيساو", "GY": "🇬🇾 غيانا",
    "HN": "🇭🇳 هندوراس", "HU": "🇭🇺 هنغاريا", "IS": "🇮🇸 آيسلندا",
    "IR": "🇮🇷 إيران", "IL": "🇮🇱 إسرائيل", "JM": "🇯🇲 جامايكا",
    "JP": "🇯🇵 اليابان", "KI": "🇰🇮 كيريباتي", "KP": "🇰🇵 كوريا الشمالية",
    "KR": "🇰🇷 كوريا الجنوبية", "KG": "🇰🇬 قيرغيزستان", "LA": "🇱🇦 لاوس",
    "LV": "🇱🇻 لاتفيا", "LS": "🇱🇸 ليسوتو", "LR": "🇱🇷 ليبيريا",
    "LI": "🇱🇮 ليختنشتاين", "LT": "🇱🇹 ليتوانيا", "LU": "🇱🇺 لوكسمبورغ",
    "MO": "🇲🇴 ماكاو", "MG": "🇲🇬 مدغشقر", "MW": "🇲🇼 مالاوي",
    "MV": "🇲🇻 المالديف", "ML": "🇲🇱 مالي", "MT": "🇲🇹 مالطا",
    "MH": "🇲🇭 جزر مارشال", "MR": "🇲🇷 موريتانيا", "MU": "🇲🇺 موريشيوس",
    "MX": "🇲🇽 المكسيك", "FM": "🇫🇲 ميكرونيزيا", "MD": "🇲🇩 مولدوفا",
    "MC": "🇲🇨 موناكو", "MN": "🇲🇳 منغوليا", "ME": "🇲🇪 الجبل الأسود",
    "MZ": "🇲🇿 موزمبيق", "MM": "🇲🇲 ميانمار", "NA": "🇳🇦 ناميبيا",
    "NR": "🇳🇷 ناورو", "NI": "🇳🇮 نيكاراغوا", "NE": "🇳🇪 النيجر",
    "PW": "🇵🇼 بالاو", "PA": "🇵🇦 بنما", "PG": "🇵🇬 بابوا غينيا الجديدة",
    "PY": "🇵🇾 باراغواي", "RW": "🇷🇼 رواندا",
    "KN": "🇰🇳 سانت كيتس", "LC": "🇱🇨 سانت لوسيا", "VC": "🇻🇨 سانت فنسنت",
    "WS": "🇼🇸 ساموا", "SM": "🇸🇲 سان مارينو", "ST": "🇸🇹 ساو تومي",
    "SN": "🇸🇳 السنغال", "RS": "🇷🇸 صربيا", "SC": "🇸🇨 سيشل",
    "SL": "🇸🇱 سيراليون", "SK": "🇸🇰 سلوفاكيا", "SI": "🇸🇮 سلوفينيا",
    "SB": "🇸🇧 جزر سليمان", "SO": "🇸🇴 الصومال", "SS": "🇸🇸 جنوب السودان",
    "SR": "🇸🇷 سورينام", "SZ": "🇸🇿 إسواتيني", "TJ": "🇹🇯 طاجيكستان",
    "TL": "🇹🇱 تيمور الشرقية", "TO": "🇹🇴 تونغا", "TT": "🇹🇹 ترينيداد",
    "TM": "🇹🇲 تركمانستان", "TV": "🇹🇻 توفالو", "UG": "🇺🇬 أوغندا",
    "UY": "🇺🇾 أوروغواي", "VU": "🇻🇺 فانواتو", "VA": "🇻🇦 الفاتيكان",
    "VE": "🇻🇪 فنزويلا", "ZM": "🇿🇲 زامبيا", "ZW": "🇿🇼 زيمبابوي",
}

DEFAULT_SERVICES = {
    "whatsapp": "واتساب",
}

def load_known_countries():
    with known_countries_lock:
        if os.path.exists(KNOWN_COUNTRIES_FILE):
            try:
                with open(KNOWN_COUNTRIES_FILE, "r", encoding="utf-8") as f:
                    return json.load(f)
            except: pass
        return {}

def save_known_countries(data):
    with known_countries_lock:
        try:
            with open(KNOWN_COUNTRIES_FILE, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
        except Exception as e:
            logger.error(f"Save known countries error: {e}")

def register_discovered_country(country_code):
    known = load_known_countries()
    if country_code not in known:
        known[country_code] = {
            "code": country_code,
            "discovered_at": datetime.now().isoformat(),
            "name": COUNTRIES_NAMES_AR.get(country_code, country_code)
        }
        save_known_countries(known)
        logger.info(f"🆕 تم اكتشاف دولة جديدة: {country_code}")

def get_all_test_countries():
    known = load_known_countries()
    all_countries = set(COUNTRY_PREFIXES.keys())
    for code in known.keys():
        all_countries.add(code)
    return list(all_countries)

def load_available_cache():
    global available_countries_cache
    with available_countries_lock:
        if os.path.exists(AVAILABLE_COUNTRIES_FILE):
            try:
                with open(AVAILABLE_COUNTRIES_FILE, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    available_countries_cache = data
                    logger.info(f"📂 كاش: {len(data)} خدمة")
            except Exception as e:
                logger.error(f"خطأ تحميل الكاش: {e}")
                available_countries_cache = {}

def save_available_cache():
    with available_countries_lock:
        try:
            with open(AVAILABLE_COUNTRIES_FILE, "w", encoding="utf-8") as f:
                json.dump(available_countries_cache, f, indent=2, ensure_ascii=False)
        except Exception as e:
            logger.error(f"خطأ حفظ الكاش: {e}")

def load_code_owners():
    with code_owners_lock:
        if os.path.exists(CODE_OWNERS_FILE):
            try:
                with open(CODE_OWNERS_FILE, "r", encoding="utf-8") as f:
                    return json.load(f)
            except: pass
        return {}

def save_code_owners(data):
    with code_owners_lock:
        try:
            with open(CODE_OWNERS_FILE, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
        except Exception as e:
            logger.error(f"Save owners error: {e}")

def register_number_owner(number, user_id, username, first_name, service, country):
    owners = load_code_owners()
    cleaned = re.sub(r'\D', '', str(number))
    if cleaned:
        owners[cleaned] = {
            "user_id": user_id, "username": username or "",
            "first_name": first_name or "مستخدم",
            "service": service, "country": country,
            "requested_at": datetime.now().isoformat()
        }
        save_code_owners(owners)

def get_number_owner(number):
    owners = load_code_owners()
    cleaned = re.sub(r'\D', '', str(number))
    return owners.get(cleaned)

# ═══════════════════════════════════════════════════════════════
# 📁 ملفات النظام
# ═══════════════════════════════════════════════════════════════
COUNTRIES_FILE = "countriesi.json"
CHANNELS_FILE = "channelsi.json"
USERS_FILE = "usersiy.json"
ADMINS_FILE = "admins.ijson"
BANNED_FILE = "bannedi.json"
OTP_GROUP_FILE = "otp_groupi.json"
GROUPS_FILE = "groupsi.json"
STATISTICS_FILE = "statisticsi.json"
REFERRALS_FILE = "referralsi.json"
REFERRAL_SETTINGS_FILE = "referral_settings.json"
NUMBERS_ADMINS_FILE = "numbers_admins.json"
OTP_BUTTONS_FILE = "otp_buttons.json"

COUNTRIES = {}
CHANNELS = []
USERS = {}
ADMINS = []
BANNED = []
GROUPS = []
REFERRALS = {}
NUMBERS_ADMINS = []

DEFAULT_REFERRAL_SETTINGS = {
    "codes_required_for_referral": 10,
    "referral_bonus": 0.05,
    "code_bonus": 0.002,
    "min_withdrawal": 5.0,
    "enabled": True
}

DEFAULT_OTP_BUTTONS = [
    {"name": "🔗 جروب البوت", "url": GROUP_LINK},
]

import telebot
from telebot.types import (
    InlineKeyboardMarkup, InlineKeyboardButton,
    ReplyKeyboardMarkup, KeyboardButton, CopyTextButton
)

bot = telebot.TeleBot(BOT_TOKEN)

def load_otp_buttons():
    if os.path.exists(OTP_BUTTONS_FILE):
        try:
            with open(OTP_BUTTONS_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except: pass
    return DEFAULT_OTP_BUTTONS.copy()

def save_otp_buttons(buttons):
    with open(OTP_BUTTONS_FILE, "w", encoding="utf-8") as f:
        json.dump(buttons, f, indent=2, ensure_ascii=False)

OTP_BUTTONS = load_otp_buttons()

STATISTICS = {
    "total_codes": 0, "codes_today": 0, "codes_this_week": 0, "codes_this_month": 0,
    "last_reset_day": None, "last_reset_week": None, "last_reset_month": None,
    "daily_history": {}, "recent_activations": []
}

user_states = {}
broadcast_state = {}

def load_numbers_admins():
    global NUMBERS_ADMINS
    if os.path.exists(NUMBERS_ADMINS_FILE):
        try:
            with open(NUMBERS_ADMINS_FILE, "r", encoding="utf-8") as f:
                NUMBERS_ADMINS = [int(x) for x in json.load(f)]
        except: NUMBERS_ADMINS = []
    if NUMBERS_ADMIN_ID and NUMBERS_ADMIN_ID not in NUMBERS_ADMINS:
        NUMBERS_ADMINS.append(NUMBERS_ADMIN_ID)
        save_numbers_admins()
    return NUMBERS_ADMINS

def save_numbers_admins():
    with open(NUMBERS_ADMINS_FILE, "w", encoding="utf-8") as f:
        json.dump(NUMBERS_ADMINS, f, indent=2, ensure_ascii=False)

def is_numbers_admin(user_id):
    return user_id in NUMBERS_ADMINS or is_admin(user_id)

def is_admin(user_id):
    return user_id == MAIN_ADMIN_ID or user_id in ADMINS

def is_banned(user_id):
    return user_id in BANNED

SPECIAL_FLAGS = {
    "US": "🇺🇸", "RU": "🇷🇺", "EG": "🇪🇬", "SA": "🇸🇦", "DE": "🇩🇪",
    "FR": "🇫🇷", "GB": "🇬🇧", "CA": "🇨🇦", "TR": "🇹🇷", "BR": "🇧🇷",
    "ID": "🇮🇩", "IN": "🇮🇳", "TG": "🇹🇬", "IQ": "🇮🇶", "JO": "🇯🇴",
    "AE": "🇦🇪", "KW": "🇰🇼", "MA": "🇲🇦", "DZ": "🇩🇿", "TN": "🇹🇳",
    "LY": "🇱🇾", "HT": "🇭🇹", "BF": "🇧🇫", "LB": "🇱🇧", "TZ": "🇹🇿",
    "PE": "🇵🇪", "PK": "🇵🇰", "CF": "🇨🇫", "NG": "🇳🇬", "KE": "🇰🇪",
    "GH": "🇬🇭", "ZA": "🇿🇦", "UA": "🇺🇦", "PL": "🇵🇱", "RO": "🇷🇴",
    "BG": "🇧🇬", "IT": "🇮🇹", "ES": "🇪🇸", "PT": "🇵🇹", "NL": "🇳🇱",
    "BE": "🇧🇪", "CH": "🇨🇭", "AT": "🇦🇹", "SE": "🇸🇪", "NO": "🇳🇴",
    "DK": "🇩🇰", "FI": "🇫🇮", "IE": "🇮🇪", "GR": "🇬🇷", "CZ": "🇨🇿",
    "SK": "🇸🇰", "HU": "🇭🇺", "VN": "🇻🇳", "TH": "🇹🇭", "PH": "🇵🇭",
    "MY": "🇲🇾", "SG": "🇸🇬", "BD": "🇧🇩", "LK": "🇱🇰", "NP": "🇳🇵",
    "AM": "🇦🇲", "GE": "🇬🇪", "AZ": "🇦🇿", "AF": "🇦🇫",
    "AL": "🇦🇱", "AD": "🇦🇩", "AO": "🇦🇴", "AR": "🇦🇷",
    "AU": "🇦🇺", "BS": "🇧🇸", "BH": "🇧🇭", "BB": "🇧🇧",
    "BY": "🇧🇾", "BZ": "🇧🇿", "BJ": "🇧🇯", "BT": "🇧🇹",
    "BO": "🇧🇴", "BA": "🇧🇦", "BW": "🇧🇼", "BN": "🇧🇳",
    "BI": "🇧🇮", "KH": "🇰🇭", "CM": "🇨🇲", "CV": "🇨🇻", "CL": "🇨🇱",
    "CN": "🇨🇳", "CO": "🇨🇴", "KM": "🇰🇲", "CG": "🇨🇬", "CD": "🇨🇩",
    "CR": "🇨🇷", "CI": "🇨🇮", "HR": "🇭🇷", "CU": "🇨🇺", "CY": "🇨🇾",
    "DJ": "🇩🇯", "DM": "🇩🇲", "DO": "🇩🇴", "EC": "🇪🇨", "SV": "🇸🇻",
    "GQ": "🇬🇶", "ER": "🇪🇷", "EE": "🇪🇪", "ET": "🇪🇹", "FJ": "🇫🇯",
    "GA": "🇬🇦", "GM": "🇬🇲", "GT": "🇬🇹", "GN": "🇬🇳",
    "GW": "🇬🇼", "GY": "🇬🇾", "HN": "🇭🇳", "IS": "🇮🇸",
    "IR": "🇮🇷", "IL": "🇮🇱", "JM": "🇯🇲", "JP": "🇯🇵", "KZ": "🇰🇿",
    "KI": "🇰🇮", "KP": "🇰🇵", "KR": "🇰🇷", "KG": "🇰🇬", "LA": "🇱🇦",
    "LV": "🇱🇻", "LS": "🇱🇸", "LR": "🇱🇷", "LI": "🇱🇮", "LT": "🇱🇹",
    "LU": "🇱🇺", "MO": "🇲🇴", "MG": "🇲🇬", "MW": "🇲🇼", "MV": "🇲🇻",
    "ML": "🇲🇱", "MT": "🇲🇹", "MH": "🇲🇭", "MR": "🇲🇷", "MU": "🇲🇺",
    "MX": "🇲🇽", "FM": "🇫🇲", "MD": "🇲🇩", "MC": "🇲🇨", "MN": "🇲🇳",
    "ME": "🇲🇪", "MZ": "🇲🇿", "MM": "🇲🇲", "NA": "🇳🇦", "NR": "🇳🇷",
    "NI": "🇳🇮", "NE": "🇳🇪", "OM": "🇴🇲", "PW": "🇵🇼", "PS": "🇵🇸",
    "PA": "🇵🇦", "PG": "🇵🇬", "PY": "🇵🇾", "QA": "🇶🇦", "RW": "🇷🇼",
    "KN": "🇰🇳", "LC": "🇱🇨", "VC": "🇻🇨", "WS": "🇼🇸", "SM": "🇸🇲",
    "ST": "🇸🇹", "SN": "🇸🇳", "RS": "🇷🇸", "SC": "🇸🇨", "SL": "🇸🇱",
    "SI": "🇸🇮", "SB": "🇸🇧", "SO": "🇸🇴", "SS": "🇸🇸", "SD": "🇸🇩",
    "SR": "🇸🇷", "SZ": "🇸🇿", "SY": "🇸🇾", "TJ": "🇹🇯", "TL": "🇹🇱",
    "TO": "🇹🇴", "TT": "🇹🇹", "TM": "🇹🇲", "TV": "🇹🇻", "UG": "🇺🇬",
    "UY": "🇺🇾", "UZ": "🇺🇿", "VU": "🇻🇺", "VA": "🇻🇦", "VE": "🇻🇪",
    "YE": "🇾🇪", "ZM": "🇿🇲", "ZW": "🇿🇼",
}

def get_flag(country_code):
    if not country_code:
        return "🌍"
    code = str(country_code).upper()
    return SPECIAL_FLAGS.get(code, "🌍")

def get_country_name(country_code):
    if country_code in COUNTRIES_NAMES_AR:
        return COUNTRIES_NAMES_AR[country_code]
    return f"{get_flag(country_code)} {country_code}"

def detect_country_from_number(number, user_id=None):
    try:
        s = str(number).strip()
        if not s:
            return "Unknown", "🌍", "UN"
        if not s.startswith('+'):
            s = '+' + s
        try:
            parsed = phonenumbers.parse(s)
            if not phonenumbers.is_valid_number(parsed):
                parsed = phonenumbers.parse(s + "00000000")
        except:
            try:
                parsed = phonenumbers.parse(s + "00000000")
            except:
                return "Unknown", "🌍", "UN"
        region = phonenumbers.region_code_for_number(parsed)
        if not region:
            return "Unknown", "🌍", "UN"
        country_name = geocoder.description_for_number(parsed, "ar")
        if not country_name or country_name == "Unknown":
            country_name = geocoder.description_for_number(parsed, "en")
        if not country_name or country_name == "Unknown":
            country_name = region
        return country_name, get_flag(region), region
    except:
        return "Unknown", "🌍", "UN"

def get_country_flags_final(country_name):
    if not country_name:
        return "🌍"
    for code, flag in SPECIAL_FLAGS.items():
        if country_name.upper() == code:
            return flag
    return "🌍"

def extract_from_message(raw_text):
    if not raw_text:
        return None, None
    text = str(raw_text)
    patterns = [
        r'(?:code|كود|رمز|otp)[:\s]*(\d{4,8})',
        r'\b(\d{6})\b', r'\b(\d{5})\b', r'\b(\d{4})\b',
    ]
    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            return match.group(1), text
    return None, text

# ═══════════════════════════════════════════════════════════════
# 🛠️ دالة تحويل اسم الدولة إلى شكل جميل (علم + اسم عربي)
# ═══════════════════════════════════════════════════════════════
def format_country_button(country_input):
    code = ""
    if len(country_input) == 2 and country_input.isalpha():
        code = country_input.upper()
    else:
        try:
            country_obj = pycountry.countries.get(name=country_input)
            if country_obj:
                code = country_obj.alpha_2
            else:
                results = pycountry.countries.search_fuzzy(country_input)
                if results:
                    code = results[0].alpha_2
        except:
            pass
    
    if code and code in COUNTRIES_NAMES_AR:
        return COUNTRIES_NAMES_AR[code]
    return f"🌍 {country_input}"

# ═══════════════════════════════════════════════════════════════
# 🔌 اتصالات الـ API الخاصة بـ NumberPanel
# ═══════════════════════════════════════════════════════════════
NUMBERPANEL_BASE = f"{NUMBERPANEL_API_URL.rstrip('/')}/api"
HEADERS = {
    "Authorization": f"Bearer {NUMBERPANEL_API_TOKEN}",
    "Content-Type": "application/json",
    "Accept": "application/json"
}

def np_get_countries(service_name="WhatsApp"):
    """جلب الدول المتاحة لخدمة معينة من الموقع مباشرة"""
    try:
        r = requests.get(f"{NUMBERPANEL_BASE}/countries", params={"service": service_name}, headers=HEADERS, timeout=15)
        if r.status_code == 200:
            return r.json().get("countries", [])
        else:
            logger.error(f"❌ فشل جلب الدول: {r.status_code} - {r.text}")
    except Exception as e:
        logger.error(f"❌ خطأ اتصال: {e}")
    return []

def np_request_number(service_name, country_name_en):
    """طلب رقم جديد من الموقع بالاسم الإنجليزي الدقيق للدولة"""
    url = f"{NUMBERPANEL_BASE}/request_number"
    payload = {"service": service_name, "country": country_name_en}
    logger.info(f"📡 طلب رقم: {payload}")
    try:
        r = requests.post(url, json=payload, headers=HEADERS, timeout=30)
        logger.info(f"📡 الرد: {r.status_code} - {r.text[:200]}")
        if r.status_code == 200:
            data = r.json()
            if data.get("success") is True and data.get("number"):
                return True, data.get("number")
            else:
                return False, data.get("message", "فشل الطلب: رقم غير متاح")
        else:
            return False, f"خطأ من الموقع (HTTP {r.status_code}): {r.text[:100]}"
    except Exception as e:
        logger.error(f"⚠️ خطأ: {e}")
        return False, f"خطأ اتصال: {str(e)}"

def load_np_last_code():
    with np_last_code_lock:
        if os.path.exists(NP_LAST_CODE_FILE):
            try:
                with open(NP_LAST_CODE_FILE, "r", encoding="utf-8") as f:
                    return json.load(f)
            except: pass
        return {}

def save_np_last_code(data):
    with np_last_code_lock:
        try:
            with open(NP_LAST_CODE_FILE, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
        except: pass

def np_get_latest_codes():
    """جلب البث العام للأكواد"""
    url = f"{NUMBERPANEL_BASE}/otp?count=200"
    try:
        r = requests.get(url, headers=HEADERS, timeout=15)
        if r.status_code != 200:
            logger.error(f"❌ API error: {r.status_code}")
            return []
        data = r.json()
        if isinstance(data, list):
            return data
        return []
    except Exception as e:
        logger.error(f"❌ خطأ في الاتصال: {e}")
        return []

def find_number_for_country(country_name_en, service_key, user_id):
    """طلب رقم من الموقع مباشرة باستخدام اسم الدولة الإنجليزي"""
    service_map = {"whatsapp": "WhatsApp"}
    service_name = service_map.get(service_key.lower(), service_key.capitalize())
    user_numbers = set()
    for n in load_my_numbers():
        if n.get("added_by") == user_id:
            user_numbers.add(n.get("number"))
    success, result = np_request_number(service_name, country_name_en)
    if success:
        cleaned = clean_number(result)
        if cleaned and cleaned not in user_numbers:
            logger.info(f"✅ تم طلب رقم جديد: {result}")
            return True, cleaned, "تم الطلب بنجاح"
        else:
            return False, None, "الرقم الذي تم جلبه مستخدم من قبل، جرب مرة أخرى"
    else:
        return False, None, result

# ═══════════════════════════════════════════════════════════════
# 💰 نظام الإحالات والرصيد
# ═══════════════════════════════════════════════════════════════
def load_referral_settings():
    if os.path.exists(REFERRAL_SETTINGS_FILE):
        try:
            with open(REFERRAL_SETTINGS_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except: pass
    return DEFAULT_REFERRAL_SETTINGS.copy()

def generate_referral_code(user_id):
    import hashlib
    hash_input = f"{user_id}_{datetime.now().timestamp()}"
    return hashlib.md5(hash_input.encode()).hexdigest()[:8].upper()

def load_referrals():
    global REFERRALS
    if os.path.exists(REFERRALS_FILE):
        try:
            with open(REFERRALS_FILE, "r", encoding="utf-8") as f:
                REFERRALS = json.load(f)
        except: REFERRALS = {}
    return REFERRALS

def save_referrals(data=None):
    global REFERRALS
    with REFERRALS_LOCK:
        if data:
            REFERRALS = data
        with open(REFERRALS_FILE, "w", encoding="utf-8") as f:
            json.dump(REFERRALS, f, indent=2, ensure_ascii=False)

def get_user_referral_data(user_id):
    global REFERRALS
    REFERRALS = load_referrals()
    user_key = str(user_id)
    if user_key not in REFERRALS:
        REFERRALS[user_key] = {
            "referral_code": generate_referral_code(user_id),
            "referred_by": None, "referrals": [], "active_referrals": 0,
            "codes_received": 0, "balance": 0.0, "total_earned": 0.0
        }
        save_referrals(REFERRALS)
    return REFERRALS[user_key]

def process_referral(user_id, referrer_id):
    global REFERRALS
    REFERRALS = load_referrals()
    user_key = str(user_id)
    referrer_key = str(referrer_id)
    if user_key not in REFERRALS:
        REFERRALS[user_key] = {
            "referred_by": referrer_key, "referrals": [], "active_referrals": 0,
            "codes_received": 0, "balance": 0.0, "total_earned": 0.0
        }
    else:
        if REFERRALS[user_key].get("referred_by"):
            return False
        REFERRALS[user_key]["referred_by"] = referrer_key
    if referrer_key not in REFERRALS:
        REFERRALS[referrer_key] = {
            "referred_by": None, "referrals": [], "active_referrals": 0,
            "codes_received": 0, "balance": 0.0, "total_earned": 0.0
        }
    if user_key not in REFERRALS[referrer_key]["referrals"]:
        REFERRALS[referrer_key]["referrals"].append(user_key)
    save_referrals(REFERRALS)
    return True

def add_code_bonus(user_id):
    global REFERRALS
    REFERRALS = load_referrals()
    settings = load_referral_settings()
    user_key = str(user_id)
    if user_key not in REFERRALS:
        REFERRALS[user_key] = {
            "referred_by": None, "referrals": [], "active_referrals": 0,
            "codes_received": 0, "balance": 0.0, "total_earned": 0.0
        }
    REFERRALS[user_key]["codes_received"] = REFERRALS[user_key].get("codes_received", 0) + 1
    cb = settings.get("code_bonus", 0.002)
    REFERRALS[user_key]["balance"] += cb
    REFERRALS[user_key]["total_earned"] += cb
    referrer_key = REFERRALS[user_key].get("referred_by")
    if referrer_key and referrer_key in REFERRALS:
        codes_required = settings.get("codes_required_for_referral", 10)
        if REFERRALS[user_key]["codes_received"] == codes_required:
            REFERRALS[referrer_key]["active_referrals"] += 1
            rb = settings.get("referral_bonus", 0.05)
            REFERRALS[referrer_key]["balance"] += rb
            REFERRALS[referrer_key]["total_earned"] += rb
            try:
                bot.send_message(int(referrer_key),
                    f"🎉 <b>إحالة جديدة!</b>\n💰 <b>${rb:.2f}</b> لرصيدك!",
                    parse_mode="HTML")
            except: pass
    save_referrals(REFERRALS)

# ═══════════════════════════════════════════════════════════════
# 📱 إدارة الأرقام الخاصة
# ═══════════════════════════════════════════════════════════════
def load_my_numbers():
    with my_numbers_lock:
        if os.path.exists(MY_NUMBERS_FILE):
            try:
                with open(MY_NUMBERS_FILE, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except: pass
        return []

def save_my_numbers(numbers):
    with my_numbers_lock:
        try:
            with open(MY_NUMBERS_FILE, 'w', encoding='utf-8') as f:
                json.dump(numbers, f, indent=2, ensure_ascii=False)
            return True
        except: return False

def load_my_numbers_sent():
    with my_numbers_lock:
        if os.path.exists(MY_NUMBERS_SENT_FILE):
            try:
                with open(MY_NUMBERS_SENT_FILE, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except: pass
        return {}

def save_my_numbers_sent(data):
    with my_numbers_lock:
        try:
            with open(MY_NUMBERS_SENT_FILE, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
        except: pass

def add_my_number(number, label="", added_by=None):
    numbers = load_my_numbers()
    cleaned = re.sub(r'\D', '', str(number))
    if not cleaned:
        return False, "❌ رقم غير صالح"
    if any(n.get("number") == cleaned for n in numbers):
        return False, "⚠️ موجود"
    country_name, flag, region = detect_country_from_number(cleaned)
    entry = {
        "number": cleaned, "label": label or country_name,
        "country": country_name, "flag": flag, "region": region,
        "added_at": datetime.now().isoformat(), "added_by": added_by,
        "last_code": None, "codes_count": 0
    }
    numbers.append(entry)
    save_my_numbers(numbers)
    return True, entry

def remove_my_number(number):
    numbers = load_my_numbers()
    cleaned = re.sub(r'\D', '', str(number))
    new_numbers = [n for n in numbers if n.get("number") != cleaned]
    if len(new_numbers) == len(numbers):
        return False
    save_my_numbers(new_numbers)
    return True

def update_my_number_last_code(number, code):
    numbers = load_my_numbers()
    cleaned = re.sub(r'\D', '', str(number))
    for n in numbers:
        if n.get("number") == cleaned:
            n["last_code"] = code
            n["last_code_at"] = datetime.now().isoformat()
            n["codes_count"] = n.get("codes_count", 0) + 1
            break
    save_my_numbers(numbers)

# ═══════════════════════════════════════════════════════════════
# 📦 الأكواد المجمعة
# ═══════════════════════════════════════════════════════════════
def load_collected_codes():
    global collected_codes
    if os.path.exists(COLLECTED_CODES_FILE):
        try:
            with open(COLLECTED_CODES_FILE, 'r', encoding='utf-8') as f:
                collected_codes = json.load(f)
        except: collected_codes = []
    return collected_codes

def save_collected_codes():
    with collected_codes_lock:
        with open(COLLECTED_CODES_FILE, 'w', encoding='utf-8') as f:
            json.dump(collected_codes, f, indent=2, ensure_ascii=False)

# ═══════════════════════════════════════════════════════════════
# 🔄 تحميل وحفظ كل البيانات
# ═══════════════════════════════════════════════════════════════
def load_data():
    global COUNTRIES, CHANNELS, USERS, ADMINS, BANNED, OTP_GROUP, GROUPS, REFERRALS, NUMBERS_ADMINS
    if os.path.exists(COUNTRIES_FILE):
        try:
            with open(COUNTRIES_FILE, "r", encoding="utf-8") as f:
                COUNTRIES = json.load(f)
        except: pass
    if os.path.exists(CHANNELS_FILE):
        try:
            with open(CHANNELS_FILE, "r", encoding="utf-8") as f:
                CHANNELS = json.load(f)
        except: pass
    if os.path.exists(USERS_FILE):
        try:
            with open(USERS_FILE, "r", encoding="utf-8") as f:
                USERS = json.load(f)
        except: pass
    if os.path.exists(ADMINS_FILE):
        try:
            with open(ADMINS_FILE, "r", encoding="utf-8") as f:
                ADMINS = json.load(f)
        except: pass
    ADMINS = [int(x) for x in ADMINS if str(x).isdigit()]
    if MAIN_ADMIN_ID != 0 and MAIN_ADMIN_ID not in ADMINS:
        ADMINS.append(MAIN_ADMIN_ID)
        save_admins()
    if os.path.exists(BANNED_FILE):
        try:
            with open(BANNED_FILE, "r", encoding="utf-8") as f:
                BANNED = json.load(f)
        except: pass
    if os.path.exists(OTP_GROUP_FILE):
        try:
            with open(OTP_GROUP_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                OTP_GROUP = data.get("group_id", OTP_GROUP)
        except: pass
    if os.path.exists(GROUPS_FILE):
        try:
            with open(GROUPS_FILE, "r", encoding="utf-8") as f:
                GROUPS = json.load(f)
        except: pass
    if os.path.exists(REFERRALS_FILE):
        try:
            with open(REFERRALS_FILE, "r", encoding="utf-8") as f:
                REFERRALS = json.load(f)
        except: pass
    load_numbers_admins()
    load_statistics()
    load_collected_codes()

def save_users():
    with USERS_LOCK:
        with open(USERS_FILE, "w", encoding="utf-8") as f:
            json.dump(USERS, f, indent=2, ensure_ascii=False)

def save_admins():
    with open(ADMINS_FILE, "w", encoding="utf-8") as f:
        json.dump(ADMINS, f, indent=2, ensure_ascii=False)

def save_banned():
    with open(BANNED_FILE, "w", encoding="utf-8") as f:
        json.dump(BANNED, f, indent=2, ensure_ascii=False)

def save_otp_group():
    with open(OTP_GROUP_FILE, "w", encoding="utf-8") as f:
        json.dump({"group_id": OTP_GROUP}, f, indent=2)

def save_statistics():
    with open(STATISTICS_FILE, 'w', encoding='utf-8') as f:
        json.dump(STATISTICS, f, indent=2, ensure_ascii=False)

def load_statistics():
    global STATISTICS
    if os.path.exists(STATISTICS_FILE):
        try:
            with open(STATISTICS_FILE, 'r', encoding='utf-8') as f:
                STATISTICS = json.load(f)
        except: pass

# ═══════════════════════════════════════════════════════════════
# 🔥 فحص الأكواد وإرسالها للجروب
# ═══════════════════════════════════════════════════════════════
def build_group_code_message(number, code_val, service, country, message=""):
    cleaned = clean_number(number)
    masked = mask_number_partial(cleaned)
    service_icon = get_service_icon(service)
    flag = get_flag(country) if country else "🌍"
    service_display = DEFAULT_SERVICES.get(service.lower() if service else "", service or "غير معروفة")

    text = (
        f"{service_icon} <b>كود جديد</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━━\n"
        f"🌍 <b>الدولة:</b> {flag}\n"
        f"📱 <b>الخدمة:</b> {service_display}\n"
        f"📵 <b>الرقم:</b> <code>{masked}</code>\n"
        f"🔑 <b>الكود:</b> <code>{code_val}</code>\n"
        f"🕐 <b>الوقت:</b> {datetime.now().strftime('%H:%M:%S')}"
    )

    markup = InlineKeyboardMarkup(row_width=1)
    try:
        markup.add(InlineKeyboardButton(
            text=f"📋 نسخ الكود: {code_val}",
            copy_text=CopyTextButton(text=str(code_val)),
            style="success"
        ))
    except: pass

    markup.add(InlineKeyboardButton(
        text="📊 معلومات الرقم",
        callback_data=f"code_info_{cleaned}",
        style="success"
    ))

    for btn in OTP_BUTTONS:
        try:
            markup.add(InlineKeyboardButton(btn["name"], url=btn["url"], style="success"))
        except: pass

    return text, markup

def np_check_new_code_loop():
    logger.info("🚀 بدء فحص NumberPanel (كل 5 ثوان)...")
    time.sleep(3)
    while True:
        try:
            codes_list = np_get_latest_codes()
            last_sent = load_np_last_code()

            for item in codes_list[:100]:
                # الرد: ["WhatsApp", "1234567890", "12345", "10 sec ago"]
                if not isinstance(item, list) or len(item) < 3:
                    continue
                
                service = str(item[0])
                number = str(item[1])
                code_val = str(item[2])

                if not number or not code_val:
                    continue

                cleaned_number = clean_number(number)
                if not cleaned_number:
                    continue

                country_name, flag, region = detect_country_from_number(cleaned_number)
                country = region

                unique_key = f"{cleaned_number}|{code_val}"
                if unique_key in last_sent:
                    continue

                logger.info(f"🔔 كود جديد: {code_val} للرقم {cleaned_number} - {country}")

                text, markup = build_group_code_message(
                    number=cleaned_number, code_val=code_val,
                    service=service, country=country, message=""
                )

                sent = False
                if OTP_GROUP:
                    try:
                        msg = bot.send_message(OTP_GROUP, text, parse_mode="HTML", reply_markup=markup)
                        auto_delete_message(OTP_GROUP, msg.message_id, delay=300)
                        sent = True
                    except Exception as e:
                        logger.error(f"خطأ إرسال: {e}")

                for gid in list(GROUPS):
                    if gid != OTP_GROUP:
                        try:
                            msg = bot.send_message(gid, text, parse_mode="HTML", reply_markup=markup)
                            auto_delete_message(gid, msg.message_id, delay=300)
                            sent = True
                        except: pass

                if sent:
                    last_sent[unique_key] = datetime.now().isoformat()
                    if len(last_sent) > 1000:
                        for k in list(last_sent.keys())[:-1000]:
                            del last_sent[k]
                    save_np_last_code(last_sent)
                    update_my_number_last_code(cleaned_number, code_val)

                    with collected_codes_lock:
                        collected_codes.append({
                            "number": cleaned_number, "sms": "",
                            "service": service, "otp": code_val,
                            "site": "NumberPanel", "timestamp": time.time()
                        })
                        if len(collected_codes) > 500:
                            collected_codes[:] = collected_codes[-500:]
                        save_collected_codes()

                    # إضافة بونص
                    owner = get_number_owner(cleaned_number)
                    if owner:
                        add_code_bonus(owner.get("user_id"))

                    STATISTICS["total_codes"] = STATISTICS.get("total_codes", 0) + 1
                    save_statistics()
        except Exception as e:
            logger.error(f"خطأ: {e}")
        time.sleep(5)

# ═══════════════════════════════════════════════════════════════
# 📲 الأزرار الرئيسية
# ═══════════════════════════════════════════════════════════════
def get_main_reply_keyboard(user_id=None):
    markup = ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    markup.row(
        KeyboardButton("📲 احصل على رقم", style="primary"),
        KeyboardButton("💰 الرصيد", style="primary")
    )
    markup.row(
        KeyboardButton("💸 سحب", style="success"),
        KeyboardButton("👥 إحالة", style="success")
    )
    markup.row(
        KeyboardButton("📊 حالتي", style="danger"),
        KeyboardButton("📈 الحركة المباشرة", style="danger")
    )
    if user_id:
        if user_id == MAIN_ADMIN_ID:
            markup.row(KeyboardButton("👑 لوحة المالك"))
        if is_admin(user_id):
            markup.row(KeyboardButton("🎛 لوحة الإدارة"))
        if is_numbers_admin(user_id) or is_admin(user_id):
            markup.row(KeyboardButton("📱 لوحة الأرقام"))
    return markup

def get_services_menu():
    markup = InlineKeyboardMarkup(row_width=1)
    markup.add(InlineKeyboardButton("📞 واتساب", callback_data="service_whatsapp", style="success"))
    return markup

def get_owner_panel_text():
    known = load_known_countries()
    with available_countries_lock:
        wa_count = len(available_countries_cache.get("whatsapp", []))
    return (
        "╔═══════════════════════════════╗\n"
        "        👑 <b>لوحة المالك</b> 👑\n"
        "╚═══════════════════════════════╝\n\n"
        f"👤 <b>المالك:</b> <code>{MAIN_ADMIN_ID}</code>\n"
        f"👥 <b>المستخدمون:</b> {len(USERS)}\n"
        f"🔧 <b>المشرفون:</b> {len(ADMINS)}\n"
        f"🚫 <b>المحظورون:</b> {len(BANNED)}\n"
        f"📱 <b>الأرقام:</b> {len(load_my_numbers())}\n"
        f"🌍 <b>الدول المكتشفة:</b> {len(known)}\n"
        f"📞 <b>دول واتساب:</b> {wa_count}\n"
        f"📨 <b>إجمالي الأكواد:</b> {STATISTICS.get('total_codes', 0)}\n\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━\n🎯 اختر من القائمة:"
    )

def get_owner_menu():
    markup = InlineKeyboardMarkup(row_width=2)
    markup.row(InlineKeyboardButton("📲 طلب رقم جديد", callback_data="owner_request_number", style="success"))
    markup.row(
        InlineKeyboardButton("📱 لوحة الأرقام", callback_data="numberpanel", style="success"),
        InlineKeyboardButton("📥 آخر الأكواد", callback_data="np_last_codes", style="success")
    )
    markup.row(
        InlineKeyboardButton("🌍 الدول المكتشفة", callback_data="owner_known_countries", style="success"),
        InlineKeyboardButton("📞 دول واتساب", callback_data="owner_wa_countries", style="primary")
    )
    markup.row(InlineKeyboardButton("📣 الإذاعة للمستخدمين", callback_data="owner_broadcast_btn", style="success"))
    markup.row(
        InlineKeyboardButton("➕ إضافة مشرف", callback_data="owner_add_admin_btn", style="success"),
        InlineKeyboardButton("➖ حذف مشرف", callback_data="owner_remove_admin_btn", style="success")
    )
    markup.row(InlineKeyboardButton("📋 قائمة المشرفين", callback_data="owner_list_admins", style="success"))
    markup.row(
        InlineKeyboardButton("🚫 حظر مستخدم", callback_data="owner_ban_btn", style="success"),
        InlineKeyboardButton("✅ فك حظر", callback_data="owner_unban_btn", style="success")
    )
    markup.row(InlineKeyboardButton("📋 قائمة المحظورين", callback_data="owner_list_banned", style="success"))
    markup.row(InlineKeyboardButton("📊 إحصائيات كاملة", callback_data="owner_full_stats", style="success"))
    return markup

def get_numberpanel_text():
    numbers = load_my_numbers()
    total = len(numbers)
    text = f"📱 <b>لوحة الأرقام</b>\n\n📊 <b>الإجمالي:</b> {total}\n\n"
    if total == 0:
        text += "⚠️ لا توجد أرقام"
    else:
        for n in numbers[-5:][::-1]:
            text += f"{n.get('flag', '🌍')} <code>+{n.get('number', '')}</code> — {n.get('label', 'غير مسمى')}\n"
    return text

def get_numberpanel_menu():
    total = len(load_my_numbers())
    markup = InlineKeyboardMarkup(row_width=1)
    markup.add(InlineKeyboardButton(f"📋 عرض الأرقام ({total})", callback_data="np_show_numbers", style="success"))
    markup.add(InlineKeyboardButton("➕ إضافة رقم", callback_data="np_add_number", style="success"))
    markup.add(InlineKeyboardButton("📥 آخر الأكواد", callback_data="np_last_codes", style="success"))
    markup.add(InlineKeyboardButton("🗑 حذف رقم", callback_data="np_remove_number", style="success"))
    markup.add(InlineKeyboardButton("🔙 رجوع", callback_data="owner_panel", style="success"))
    return markup

def get_admin_menu_with_numberpanel():
    markup = InlineKeyboardMarkup(row_width=1)
    markup.add(InlineKeyboardButton("📱 لوحة الأرقام", callback_data="numberpanel", style="success"))
    markup.add(InlineKeyboardButton("📊 الإحصائيات", callback_data="admin_statistics", style="success"))
    markup.add(InlineKeyboardButton("📣 البث", callback_data="admin_broadcast_menu", style="success"))
    markup.add(InlineKeyboardButton("🔙 رجوع", callback_data="back_to_main", style="success"))
    return markup

def build_number_success_message(service_key, country_name_en, number):
    service_name = DEFAULT_SERVICES.get(service_key, service_key)
    service_icon = get_service_icon(service_key)
    cleaned = clean_number(number)

    text = (
        f"✅ <b>تم استلام رقم {service_name}!</b>\n\n"
        f"━━━━━━━━━━━━━━━━━━━━━\n"
        f"📞 <b>الرقم:</b> <code>+{cleaned}</code>\n"
        f"🌍 <b>الدولة:</b> {country_name_en}\n"
        f"{service_icon} <b>الخدمة:</b> {service_name}\n"
        f"━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"🔔 سيصلك الكود هنا تلقائياً عند وصوله."
    )

    markup = InlineKeyboardMarkup(row_width=1)
    try:
        markup.add(InlineKeyboardButton(
            text="📋 نسخ الرقم",
            copy_text=CopyTextButton(text=f"+{cleaned}"),
            style="success"
        ))
    except:
        markup.add(InlineKeyboardButton("📋 نسخ الرقم", callback_data=f"copy_num_{cleaned}", style="success"))

    markup.add(InlineKeyboardButton("📲 طلب رقم جديد", callback_data=f"new_number_{service_key}", style="success"))
    markup.add(InlineKeyboardButton("🌍 رجوع للدول", callback_data=f"service_{service_key}", style="success"))
    markup.add(InlineKeyboardButton("🔗 جروب البوت", url=GROUP_LINK, style="success"))

    return text, markup

# ═══════════════════════════════════════════════════════════════
# 📲 الأوامر (/start وغيرها)
# ═══════════════════════════════════════════════════════════════
@bot.message_handler(commands=["start"])
def start(msg):
    user_id = msg.from_user.id
    if is_banned(user_id):
        bot.reply_to(msg, "🚫 أنت محظور")
        return
    if len(msg.text.split()) > 1:
        param = msg.text.split()[1]
        if param.startswith("ref_"):
            try:
                referrer_id = int(param.replace("ref_", ""))
                if referrer_id != user_id:
                    if str(user_id) not in USERS:
                        USERS[str(user_id)] = {
                            "language": "ar", "activations": 0,
                            "join_date": datetime.now().strftime('%Y-%m-%d')
                        }
                        save_users()
                    process_referral(user_id, referrer_id)
            except: pass
    if str(user_id) not in USERS:
        USERS[str(user_id)] = {
            "language": "ar", "activations": 0,
            "join_date": datetime.now().strftime('%Y-%m-%d')
        }
        save_users()
    first_name = msg.from_user.first_name or "User"
    welcome = (
        f"⚡ مرحباً {first_name}!\n\n"
        f"🔑 <b>بوت أرقام OTP المميز</b>\n"
        f"👋 خدمة سريعة وموثوقة\n\n"
        f"🦦 اختر من القائمة:"
    )
    bot.send_message(msg.chat.id, welcome, reply_markup=get_main_reply_keyboard(user_id), parse_mode="HTML")

@bot.message_handler(commands=["debug"])
def debug_cmd(msg):
    if msg.from_user.id != MAIN_ADMIN_ID: return
    bot.reply_to(msg, "⏳ جاري اختبار الاتصال بـ NumberPanel...")
    countries = np_get_countries("WhatsApp")
    txt = f"🌍 عدد دول الواتساب المتاحة: {len(countries)}\n"
    if countries:
        txt += f"أمثلة: {countries[:5]}\n\n"
        test_country = countries[0]["name"]
        success, result = np_request_number("WhatsApp", test_country)
        txt += f"📡 اختبار طلب رقم من {test_country}:\nالنتيجة: {success}\nالرد: {result}"
    else:
        txt += "❌ لا توجد دول متاحة لاختبار الطلب."
    bot.send_message(msg.chat.id, txt, parse_mode="HTML")

@bot.message_handler(commands=["numberpanel"])
def numberpanel_cmd(msg):
    user_id = msg.from_user.id
    if not is_numbers_admin(user_id) and not is_admin(user_id):
        bot.reply_to(msg, "⛔️ للمشرفين فقط!")
        return
    bot.send_message(msg.chat.id, get_numberpanel_text(), parse_mode="HTML",
                     reply_markup=get_numberpanel_menu())

@bot.message_handler(commands=["owner"])
def owner_cmd(msg):
    user_id = msg.from_user.id
    if user_id != MAIN_ADMIN_ID:
        bot.reply_to(msg, "⛔️ للمالك فقط!")
        return
    bot.send_message(msg.chat.id, get_owner_panel_text(), parse_mode="HTML",
                     reply_markup=get_owner_menu())

# ═══════════════════════════════════════════════════════════════
# 📨 معالجة الرسائل النصية
# ═══════════════════════════════════════════════════════════════
@bot.message_handler(content_types=["text"])
def handle_messages(msg):
    user_id = msg.from_user.id

    if user_states.get(user_id, {}).get("action") == "np_add_number":
        raw = msg.text.strip()
        candidates = re.split(r'[,\n\s]+', raw)
        added, failed = [], []
        for c in candidates:
            cleaned = re.sub(r'\D', '', c)
            if not cleaned or len(cleaned) < 8:
                continue
            ok, result = add_my_number(cleaned, added_by=user_id)
            if ok: added.append(result)
            else: failed.append(cleaned)
        del user_states[user_id]
        text = "✅ <b>تم الإضافة:</b>\n\n"
        if added:
            for a in added:
                text += f"{a['flag']} <code>+{a['number']}</code>\n"
        else:
            text = "⚠️ لم يتم إضافة أي رقم\n"
        bot.reply_to(msg, text, parse_mode="HTML")
        return

    if user_states.get(user_id, {}).get("action") == "owner_add_admin":
        if user_id != MAIN_ADMIN_ID: return
        try:
            new_admin = int(msg.text.strip())
            if new_admin not in ADMINS:
                ADMINS.append(new_admin)
                save_admins()
            bot.reply_to(msg, f"✅ <code>{new_admin}</code>", parse_mode="HTML")
            del user_states[user_id]
        except:
            bot.reply_to(msg, "❌ ID غير صالح")
        return

    if user_states.get(user_id, {}).get("action") == "owner_remove_admin":
        if user_id != MAIN_ADMIN_ID: return
        try:
            rem = int(msg.text.strip())
            if rem in ADMINS and rem != MAIN_ADMIN_ID:
                ADMINS.remove(rem)
                save_admins()
                bot.reply_to(msg, f"✅ تم حذف <code>{rem}</code>", parse_mode="HTML")
            del user_states[user_id]
        except:
            bot.reply_to(msg, "❌ ID غير صالح")
        return

    if user_states.get(user_id, {}).get("action") == "owner_ban_user":
        if user_id != MAIN_ADMIN_ID: return
        try:
            ban_id = int(msg.text.strip())
            if ban_id not in BANNED:
                BANNED.append(ban_id)
                save_banned()
            bot.reply_to(msg, f"🚫 <code>{ban_id}</code>", parse_mode="HTML")
            del user_states[user_id]
        except:
            bot.reply_to(msg, "❌ ID غير صالح")
        return

    if user_states.get(user_id, {}).get("action") == "owner_unban_user":
        if user_id != MAIN_ADMIN_ID: return
        try:
            ub = int(msg.text.strip())
            if ub in BANNED:
                BANNED.remove(ub)
                save_banned()
            bot.reply_to(msg, f"✅ <code>{ub}</code>", parse_mode="HTML")
            del user_states[user_id]
        except:
            bot.reply_to(msg, "❌ ID غير صالح")
        return

    if user_states.get(user_id, {}).get("action") == "owner_broadcast":
        if user_id != MAIN_ADMIN_ID: return
        btext = msg.text
        s, f = 0, 0
        prog = bot.send_message(msg.chat.id, "⏳...")
        for uid in list(USERS.keys()):
            try:
                bot.send_message(int(uid), btext, parse_mode="HTML")
                s += 1
            except: f += 1
        try: bot.delete_message(prog.chat.id, prog.message_id)
        except: pass
        bot.send_message(msg.chat.id, f"✅ نجح: {s}\n❌ فشل: {f}")
        del user_states[user_id]
        return

    if msg.text == "👑 لوحة المالك":
        if user_id != MAIN_ADMIN_ID:
            bot.reply_to(msg, "⛔️")
            return
        bot.send_message(msg.chat.id, get_owner_panel_text(), parse_mode="HTML",
                         reply_markup=get_owner_menu())
        return

    if msg.text == "🎛 لوحة الإدارة":
        if not is_admin(user_id): return
        bot.send_message(msg.chat.id, "🎛 <b>لوحة الإدارة</b>",
                         parse_mode="HTML", reply_markup=get_admin_menu_with_numberpanel())
        return

    if msg.text == "📱 لوحة الأرقام":
        if not is_numbers_admin(user_id) and not is_admin(user_id): return
        bot.send_message(msg.chat.id, get_numberpanel_text(), parse_mode="HTML",
                         reply_markup=get_numberpanel_menu())
        return

    if msg.text == "📲 احصل على رقم":
        if is_banned(user_id):
            bot.reply_to(msg, "🚫")
            return
        bot.send_message(
            msg.chat.id,
            "🎯 <b>اختر الخدمة:</b>",
            parse_mode="HTML", reply_markup=get_services_menu()
        )
        return

    if msg.text == "💰 الرصيد":
        rd = get_user_referral_data(user_id)
        bal = rd.get("balance", 0.0)
        rc = len(rd.get("referrals", []))
        mw = load_referral_settings().get("min_withdrawal", 5.0)
        bot.send_message(msg.chat.id,
            f"💰 <b>رصيدك</b>\n\n💵 {bal:.3f} $\n👥 {rc}\n📉 {mw}$",
            parse_mode="HTML")
        return

    if msg.text == "💸 سحب":
        rd = get_user_referral_data(user_id)
        bal = rd.get("balance", 0.0)
        mw = load_referral_settings().get("min_withdrawal", 5.0)
        if bal >= mw:
            bot.send_message(msg.chat.id, f"💸 رصيدك: {bal:.2f}$\n📞 تواصل مع الأدمن.", parse_mode="HTML")
        else:
            bot.send_message(msg.chat.id, f"⚠️ رصيدك: {bal:.2f}$\n📉 الحد الأدنى: {mw}$", parse_mode="HTML")
        return

    if msg.text == "👥 إحالة":
        uname = bot.get_me().username
        link = f"https://t.me/{uname}?start=ref_{user_id}"
        rc = len(get_user_referral_data(user_id).get("referrals", []))
        markup = InlineKeyboardMarkup()
        markup.add(InlineKeyboardButton("📤 مشاركة", url=f"https://t.me/share/url?url={link}", style="success"))
        bot.send_message(msg.chat.id,
            f"👥 <b>الإحالات</b>\n\n🔗 <code>{link}</code>\n\n👥 {rc}",
            parse_mode="HTML", reply_markup=markup)
        return

    if msg.text == "📊 حالتي":
        ud = USERS.get(str(user_id), {})
        rd = get_user_referral_data(user_id)
        bot.send_message(msg.chat.id,
            f"📊 <b>إحصائياتك</b>\n\n📅 {ud.get('join_date', '—')}\n📨 {ud.get('activations', 0)}\n"
            f"💰 {rd.get('balance', 0.0):.2f}$\n💵 {rd.get('total_earned', 0.0):.2f}$",
            parse_mode="HTML")
        return

    if msg.text == "📈 الحركة المباشرة":
        now = datetime.now()
        ten_ago = (now - timedelta(minutes=10)).timestamp()
        rec = STATISTICS.get("recent_activations", [])
        last10 = [a for a in rec if a[0] > ten_ago]
        tot = len(last10)
        cc = {}
        for _, c in last10:
            cc[c] = cc.get(c, 0) + 1
        sc = sorted(cc.items(), key=lambda x: x[1], reverse=True)
        txt = f"📈 <b>الحركة المباشرة</b>\n\n⏰ آخر 10 دقائق\n📨 {tot}\n\n"
        for i, (name, cnt) in enumerate(sc[:5], 1):
            pct = (cnt / tot * 100) if tot > 0 else 0
            txt += f"{i}. {get_country_flags_final(name)} {name} ➡️ {pct:.1f}%\n"
        bot.send_message(msg.chat.id, txt, parse_mode="HTML")
        return

# ═══════════════════════════════════════════════════════════════
# 🔥 اختيار خدمة (جلب الدول من الموقع مباشرة)
# ═══════════════════════════════════════════════════════════════
@bot.callback_query_handler(func=lambda call: call.data.startswith("service_"))
def service_selected(call):
    service_key = call.data.replace("service_", "")
    service_name = DEFAULT_SERVICES.get(service_key, service_key)
    service_icon = get_service_icon(service_key)

    bot.answer_callback_query(call.id, "🔄 جاري جلب الدول المتاحة من الموقع...")
    bot.edit_message_text(
        f"{service_icon} <b>جاري جلب الدول المتاحة لـ {service_name}...</b>\n\n⏳ انتظر قليلاً",
        call.message.chat.id, call.message.message_id, parse_mode="HTML"
    )

    countries = np_get_countries("WhatsApp")

    if not countries:
        markup = InlineKeyboardMarkup(row_width=1)
        markup.add(InlineKeyboardButton("🔄 حاول تاني", callback_data=f"service_{service_key}", style="success"))
        markup.add(InlineKeyboardButton("🔗 جروب البوت", url=GROUP_LINK, style="success"))
        bot.edit_message_text(
            "❌ <b>لا توجد دول متاحة حالياً لواتساب.</b>\n\n"
            "💡 قد يكون الرصيد غير كافٍ أو السيرفر مشغول.",
            call.message.chat.id, call.message.message_id, parse_mode="HTML", reply_markup=markup
        )
        return

    markup = InlineKeyboardMarkup(row_width=2)
    for c in countries[:20]:
        country_name_en = c["name"]
        count = c.get("count", 0)
        display_name = format_country_button(country_name_en)
        clean_callback_name = country_name_en.replace(" ", "_")
        markup.add(InlineKeyboardButton(
            f"{display_name} ({count})",
            callback_data=f"pick_country_{service_key}_{clean_callback_name}",
            style="success"
        ))

    markup.add(InlineKeyboardButton("🔄 حاول تاني", callback_data=f"service_{service_key}", style="success"))
    markup.add(InlineKeyboardButton("🔗 جروب البوت", url=GROUP_LINK, style="success"))

    text = f"{service_icon} <b>{service_name} متاح في {len(countries)} دولة</b>\n\n🎯 <b>اختر الدولة:</b>"
    bot.edit_message_text(text, call.message.chat.id, call.message.message_id, parse_mode="HTML", reply_markup=markup)

# ═══════════════════════════════════════════════════════════════
# 🔥 اختيار دولة — طلب مباشر من الموقع
# ═══════════════════════════════════════════════════════════════
@bot.callback_query_handler(func=lambda call: call.data.startswith("pick_country_"))
def pick_country_cb(call):
    user_id = call.from_user.id
    parts = call.data.replace("pick_country_", "").split("_", 1)
    if len(parts) < 2:
        bot.answer_callback_query(call.id, "❌")
        return

    service_key = parts[0]
    country_name_clean = parts[1]
    country_name_en = country_name_clean.replace("_", " ")
    service_name = DEFAULT_SERVICES.get(service_key, service_key)
    service_icon = get_service_icon(service_key)
    display_name = format_country_button(country_name_en)

    try:
        bot.edit_message_text(
            f"{service_icon} <b>جاري طلب رقم {service_name} من {display_name}...</b>\n\n"
            f"📡 بنطلب من الموقع...\n⏳ استنى شوية",
            call.message.chat.id, call.message.message_id, parse_mode="HTML"
        )
    except: pass

    success, cleaned_number, error_msg = find_number_for_country(country_name_en, service_key, user_id)

    if success:
        register_number_owner(cleaned_number, user_id,
                              call.from_user.username or "",
                              call.from_user.first_name or "مستخدم",
                              service_key, country_name_en)
        add_my_number(cleaned_number, label=f"{service_key} - {display_name}", added_by=user_id)

        text, markup = build_number_success_message(service_key, display_name, cleaned_number)
        bot.edit_message_text(text, call.message.chat.id, call.message.message_id,
                              parse_mode="HTML", reply_markup=markup)
        return

    text = (
        f"❌ <b>فشل طلب الرقم من {display_name}</b>\n\n"
        f"⚠️ <b>السبب من الموقع:</b>\n<code>{error_msg}</code>\n\n"
        f"💡 جرب دولة تانية أو انتظر قليلاً."
    )
    markup = InlineKeyboardMarkup(row_width=1)
    markup.add(InlineKeyboardButton("🌍 رجوع للدول", callback_data=f"service_{service_key}", style="success"))
    markup.add(InlineKeyboardButton("🔗 جروب البوت", url=GROUP_LINK, style="success"))
    bot.edit_message_text(text, call.message.chat.id, call.message.message_id,
                          parse_mode="HTML", reply_markup=markup)

# ═══════════════════════════════════════════════════════════════
# 🔥 طلب رقم جديد
# ═══════════════════════════════════════════════════════════════
@bot.callback_query_handler(func=lambda call: call.data.startswith("new_number_"))
def new_number_cb(call):
    service_key = call.data.replace("new_number_", "")
    bot.answer_callback_query(call.id, "🔄 جاري التحديث...")
    fake_call = call
    fake_call.data = f"service_{service_key}"
    service_selected(fake_call)

@bot.callback_query_handler(func=lambda call: call.data.startswith("copy_num_"))
def copy_num_cb(call):
    num = call.data.replace("copy_num_", "")
    bot.answer_callback_query(call.id, f"📋 +{num}", show_alert=True)

# ═══════════════════════════════════════════════════════════════
# 🔥 معلومات الرقم (للمالك)
# ═══════════════════════════════════════════════════════════════
@bot.callback_query_handler(func=lambda call: call.data.startswith("code_info_"))
def code_info_callback(call):
    user_id = call.from_user.id
    if user_id != MAIN_ADMIN_ID:
        bot.answer_callback_query(call.id, "⛔️ للمالك فقط!", show_alert=True)
        return

    number = call.data.replace("code_info_", "")
    cleaned = re.sub(r'\D', '', str(number))
    owner = get_number_owner(cleaned)

    if not owner:
        bot.answer_callback_query(call.id, "⚠️ الرقم غير مسجل", show_alert=True)
        return

    my_nums = load_my_numbers()
    num_entry = next((n for n in my_nums if n.get("number") == cleaned), {})
    sent_data = load_my_numbers_sent()
    sent_codes = sent_data.get(cleaned, [])
    last_code = sent_codes[-1].get("code") if sent_codes else "—"

    owner_id = owner.get("user_id")
    owner_username = owner.get("username", "")
    owner_name = owner.get("first_name", "مستخدم")
    service = owner.get("service", "غير معروف")
    requested_at = owner.get("requested_at", "")[:19].replace("T", " ")

    user_data = USERS.get(str(owner_id), {})
    referral_data = load_referrals().get(str(owner_id), {})

    mention_link = f'<a href="tg://user?id={owner_id}">{owner_name}</a>'

    text = (
        f"📊 <b>معلومات الرقم</b>\n━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"🔢 <b>الرقم:</b> <code>+{cleaned}</code>\n"
        f"🌍 <b>الدولة:</b> {num_entry.get('flag', '🌍')}\n"
        f"📱 <b>الخدمة:</b> {get_service_icon(service)} {service}\n"
        f"🕐 <b>الوقت:</b> {requested_at}\n\n"
        f"━━━━━━━━━━━━━━━━━━━━━\n"
        f"👤 <b>المالك:</b> {mention_link}\n"
        f"🆔 <code>{owner_id}</code>\n"
        f"📛 @{owner_username if owner_username else 'لا يوجد'}\n"
        f"📅 الانضمام: {user_data.get('join_date', '—')}\n"
        f"📨 أكواده: {user_data.get('activations', 0)}\n"
        f"💰 رصيده: {referral_data.get('balance', 0.0):.3f} $\n\n"
        f"━━━━━━━━━━━━━━━━━━━━━\n"
        f"📨 أكواد هذا الرقم: {len(sent_codes)}\n"
        f"🔑 آخر كود: <code>{last_code}</code>"
    )

    try:
        bot.send_message(user_id, text, parse_mode="HTML")
        bot.answer_callback_query(call.id, "✅ في الخاص")
    except Exception as e:
        bot.answer_callback_query(call.id, f"⚠️ فشل: {e}", show_alert=True)

# ═══════════════════════════════════════════════════════════════
# 🎯 Owner Panel Callbacks
# ═══════════════════════════════════════════════════════════════
@bot.callback_query_handler(func=lambda call: call.data == "owner_panel")
def owner_panel_cb(call):
    if call.from_user.id != MAIN_ADMIN_ID:
        bot.answer_callback_query(call.id, "⛔️", show_alert=True)
        return
    bot.edit_message_text(get_owner_panel_text(), call.message.chat.id,
                          call.message.message_id, parse_mode="HTML",
                          reply_markup=get_owner_menu())

@bot.callback_query_handler(func=lambda call: call.data == "owner_request_number")
def owner_request_number_cb(call):
    if call.from_user.id != MAIN_ADMIN_ID: return
    bot.edit_message_text("🎯 <b>اختر الخدمة:</b>", call.message.chat.id, call.message.message_id,
                          parse_mode="HTML", reply_markup=get_services_menu())

@bot.callback_query_handler(func=lambda call: call.data == "owner_known_countries")
def owner_known_countries_cb(call):
    if call.from_user.id != MAIN_ADMIN_ID: return
    known = load_known_countries()
    if not known:
        bot.answer_callback_query(call.id, "⚠️ لم يتم اكتشاف دول جديدة بعد", show_alert=True)
        return
    txt = f"🌍 <b>الدول المكتشفة ({len(known)})</b>\n\n"
    for code, data in sorted(known.items()):
        flag = get_flag(code)
        name = COUNTRIES_NAMES_AR.get(code, code)
        txt += f"{flag} <code>{code}</code> — {name}\n"
    markup = InlineKeyboardMarkup()
    markup.add(InlineKeyboardButton("🔙 رجوع", callback_data="owner_panel", style="success"))
    bot.send_message(call.message.chat.id, txt, parse_mode="HTML", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data == "owner_wa_countries")
def owner_wa_countries_cb(call):
    if call.from_user.id != MAIN_ADMIN_ID: return
    bot.answer_callback_query(call.id, "🔄 جاري جلب الدول من الموقع...")
    countries = np_get_countries("WhatsApp")
    if not countries:
        bot.answer_callback_query(call.id, "⚠️ لسه مفيش دول محفوظة", show_alert=True)
        return
    txt = f"📞 <b>دول واتساب المتاحة حالياً ({len(countries)})</b>\n\n"
    for item in countries[:30]:
        txt += f"• {item['name']} ({item.get('count', 0)})\n"
    markup = InlineKeyboardMarkup()
    markup.add(InlineKeyboardButton("🔙 رجوع", callback_data="owner_panel", style="success"))
    try:
        bot.edit_message_text(txt, call.message.chat.id, call.message.message_id,
                              parse_mode="HTML", reply_markup=markup)
    except:
        bot.send_message(call.message.chat.id, txt, parse_mode="HTML", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data == "owner_add_admin_btn")
def owner_add_admin_cb(call):
    if call.from_user.id != MAIN_ADMIN_ID: return
    user_states[call.from_user.id] = {"action": "owner_add_admin"}
    bot.send_message(call.message.chat.id, "➕ أرسل ID:", parse_mode="HTML")

@bot.callback_query_handler(func=lambda call: call.data == "owner_remove_admin_btn")
def owner_remove_admin_cb(call):
    if call.from_user.id != MAIN_ADMIN_ID: return
    user_states[call.from_user.id] = {"action": "owner_remove_admin"}
    bot.send_message(call.message.chat.id, "➖ أرسل ID:", parse_mode="HTML")

@bot.callback_query_handler(func=lambda call: call.data == "owner_ban_btn")
def owner_ban_cb(call):
    if call.from_user.id != MAIN_ADMIN_ID: return
    user_states[call.from_user.id] = {"action": "owner_ban_user"}
    bot.send_message(call.message.chat.id, "🚫 أرسل ID:", parse_mode="HTML")

@bot.callback_query_handler(func=lambda call: call.data == "owner_unban_btn")
def owner_unban_cb(call):
    if call.from_user.id != MAIN_ADMIN_ID: return
    user_states[call.from_user.id] = {"action": "owner_unban_user"}
    bot.send_message(call.message.chat.id, "✅ أرسل ID:", parse_mode="HTML")

@bot.callback_query_handler(func=lambda call: call.data == "owner_broadcast_btn")
def owner_broadcast_cb(call):
    if call.from_user.id != MAIN_ADMIN_ID: return
    user_states[call.from_user.id] = {"action": "owner_broadcast"}
    bot.send_message(call.message.chat.id, "📣 أرسل الرسالة:", parse_mode="HTML")

@bot.callback_query_handler(func=lambda call: call.data == "owner_list_admins")
def owner_list_admins_cb(call):
    if call.from_user.id != MAIN_ADMIN_ID: return
    txt = "📋 <b>المشرفون</b>\n\n"
    for i, a in enumerate(ADMINS, 1):
        role = "👑" if a == MAIN_ADMIN_ID else "🔧"
        txt += f"{i}. {role} <code>{a}</code>\n"
    bot.send_message(call.message.chat.id, txt, parse_mode="HTML")

@bot.callback_query_handler(func=lambda call: call.data == "owner_list_banned")
def owner_list_banned_cb(call):
    if call.from_user.id != MAIN_ADMIN_ID: return
    if not BANNED:
        bot.answer_callback_query(call.id, "لا يوجد محظورون", show_alert=True)
        return
    txt = "📋 <b>المحظورون</b>\n\n"
    for i, b in enumerate(BANNED, 1):
        txt += f"{i}. <code>{b}</code>\n"
    bot.send_message(call.message.chat.id, txt, parse_mode="HTML")

@bot.callback_query_handler(func=lambda call: call.data == "owner_full_stats")
def owner_full_stats_cb(call):
    if call.from_user.id != MAIN_ADMIN_ID: return
    known = load_known_countries()
    with available_countries_lock:
        wa_count = len(available_countries_cache.get("whatsapp", []))
    txt = (f"📊 <b>الإحصائيات</b>\n\n"
           f"👥 المستخدمون: {len(USERS)}\n"
           f"🔧 المشرفون: {len(ADMINS)}\n"
           f"🚫 المحظورون: {len(BANNED)}\n"
           f"📱 الأرقام: {len(load_my_numbers())}\n"
           f"🌍 الدول المكتشفة: {len(known)}\n"
           f"📞 دول واتساب المحفوظة: {wa_count}\n"
           f"📨 إجمالي الأكواد: {STATISTICS.get('total_codes', 0)}")
    bot.send_message(call.message.chat.id, txt, parse_mode="HTML")

# ═══════════════════════════════════════════════════════════════
# 🎯 Admin Panel Callbacks
# ═══════════════════════════════════════════════════════════════
@bot.callback_query_handler(func=lambda call: call.data == "admin_panel")
def admin_panel_cb(call):
    if not is_admin(call.from_user.id):
        bot.answer_callback_query(call.id, "⛔️", show_alert=True)
        return
    bot.edit_message_text("🎛 <b>لوحة الإدارة</b>", call.message.chat.id,
                          call.message.message_id, parse_mode="HTML",
                          reply_markup=get_admin_menu_with_numberpanel())

@bot.callback_query_handler(func=lambda call: call.data == "back_to_main")
def back_to_main_cb(call):
    try:
        bot.edit_message_text("⚡ اختر من القائمة:", call.message.chat.id,
                              call.message.message_id, parse_mode="HTML")
    except: pass
    bot.answer_callback_query(call.id, "✅")

@bot.callback_query_handler(func=lambda call: call.data == "admin_statistics")
def admin_stats_cb(call):
    if not is_admin(call.from_user.id): return
    txt = (f"📊 <b>الإحصائيات</b>\n\n👥 {len(USERS)}\n"
           f"📨 {STATISTICS.get('total_codes', 0)}\n"
           f"📅 {STATISTICS.get('codes_today', 0)}")
    bot.send_message(call.message.chat.id, txt, parse_mode="HTML")

@bot.callback_query_handler(func=lambda call: call.data == "admin_broadcast_menu")
def admin_broadcast_menu_cb(call):
    if not is_admin(call.from_user.id): return
    broadcast_state[call.from_user.id] = {"type": "normal", "step": "waiting_message"}
    bot.send_message(call.message.chat.id, "📣 أرسل الرسالة:")

# ═══════════════════════════════════════════════════════════════
# 🎯 NumberPanel Callbacks
# ═══════════════════════════════════════════════════════════════
@bot.callback_query_handler(func=lambda call: call.data == "numberpanel")
def numberpanel_cb(call):
    if not is_numbers_admin(call.from_user.id) and not is_admin(call.from_user.id): return
    try:
        bot.edit_message_text(get_numberpanel_text(), call.message.chat.id,
                              call.message.message_id, parse_mode="HTML",
                              reply_markup=get_numberpanel_menu())
    except: pass

@bot.callback_query_handler(func=lambda call: call.data == "np_refresh")
def np_refresh_cb(call):
    numberpanel_cb(call)
    bot.answer_callback_query(call.id, "✅")

@bot.callback_query_handler(func=lambda call: call.data == "np_show_numbers")
def np_show_numbers_cb(call):
    if not is_numbers_admin(call.from_user.id) and not is_admin(call.from_user.id): return
    numbers = load_my_numbers()
    if not numbers:
        bot.answer_callback_query(call.id, "⚠️ لا توجد أرقام", show_alert=True)
        return
    text = f"📋 <b>الأرقام ({len(numbers)})</b>\n\n"
    for idx, n in enumerate(numbers, 1):
        text += f"{idx}. {n.get('flag', '🌍')} <code>+{n.get('number', '')}</code>\n"
    markup = InlineKeyboardMarkup()
    markup.add(InlineKeyboardButton("🔙", callback_data="numberpanel", style="success"))
    bot.edit_message_text(text, call.message.chat.id, call.message.message_id,
                          parse_mode="HTML", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data == "np_add_number")
def np_add_number_cb(call):
    if not is_numbers_admin(call.from_user.id) and not is_admin(call.from_user.id): return
    user_states[call.from_user.id] = {"action": "np_add_number"}
    markup = InlineKeyboardMarkup()
    markup.add(InlineKeyboardButton("❌ إلغاء", callback_data="numberpanel", style="success"))
    bot.edit_message_text("➕ أرسل الأرقام:", call.message.chat.id,
                          call.message.message_id, parse_mode="HTML", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data == "np_last_codes")
def np_last_codes_cb(call):
    if not is_numbers_admin(call.from_user.id) and not is_admin(call.from_user.id): return
    sent_data = load_my_numbers_sent()
    if not sent_data:
        # نعرض آخر الأكواد المجمعة
        all_codes = []
        for c in collected_codes[-20:]:
            all_codes.append(c)
        if not all_codes:
            bot.answer_callback_query(call.id, "⚠️ لا توجد أكواد", show_alert=True)
            return
        text = f"📥 <b>آخر {len(all_codes)} كود</b>\n\n"
        for c in reversed(all_codes):
            text += f"📱 <code>+{c.get('number', '')}</code> 🔑 <code>{c.get('otp', '—')}</code>\n"
    else:
        all_codes = []
        for num, codes in sent_data.items():
            for c in codes[-10:]:
                all_codes.append((num, c))
        all_codes.sort(key=lambda x: x[1].get("timestamp", ""), reverse=True)
        all_codes = all_codes[:20]
        text = f"📥 <b>آخر {len(all_codes)} كود</b>\n\n"
        for num, c in all_codes:
            text += f"📱 <code>+{num}</code> 🔑 <code>{c.get('code', '—')}</code>\n"
    markup = InlineKeyboardMarkup()
    markup.add(InlineKeyboardButton("🔙", callback_data="numberpanel", style="success"))
    bot.edit_message_text(text, call.message.chat.id, call.message.message_id,
                          parse_mode="HTML", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data == "np_remove_number")
def np_remove_number_cb(call):
    if not is_numbers_admin(call.from_user.id) and not is_admin(call.from_user.id): return
    numbers = load_my_numbers()
    if not numbers:
        bot.answer_callback_query(call.id, "⚠️ لا توجد أرقام", show_alert=True)
        return
    markup = InlineKeyboardMarkup(row_width=1)
    for n in numbers:
        markup.add(InlineKeyboardButton(f"🗑 {n.get('flag', '🌍')} +{n.get('number', '')}",
                                        callback_data=f"np_del_{n.get('number', '')}", style="success"))
    markup.add(InlineKeyboardButton("🔙", callback_data="numberpanel", style="success"))
    bot.edit_message_text("🗑 اختر:", call.message.chat.id,
                          call.message.message_id, parse_mode="HTML", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith("np_del_"))
def np_del_number_cb(call):
    if not is_numbers_admin(call.from_user.id) and not is_admin(call.from_user.id): return
    number = call.data.replace("np_del_", "")
    if remove_my_number(number):
        bot.answer_callback_query(call.id, f"✅ تم حذف +{number}")
    else:
        bot.answer_callback_query(call.id, "❌")
    np_remove_number_cb(call)

# ═══════════════════════════════════════════════════════════════
# 🔥 معالج الأزرار القديمة (Copy)
# ═══════════════════════════════════════════════════════════════
@bot.callback_query_handler(func=lambda call: call.data.startswith("copy_") and not call.data.startswith("copy_num_"))
def handle_copy_cb(call):
    otp = call.data.split("_", 1)[1]
    bot.answer_callback_query(call.id, f"{otp}", show_alert=True)

# ═══════════════════════════════════════════════════════════════
# 🚀 التشغيل
# ═══════════════════════════════════════════════════════════════
if __name__ == "__main__":
    load_data()
    load_available_cache()
    logger.info("🚀 بدء التشغيل...")

    Thread(target=np_check_new_code_loop, daemon=True).start()
    logger.info("✅ فحص الأكواد فوري (كل 5 ثوان)")

    try:
        requests.get(f"https://api.telegram.org/bot{BOT_TOKEN}/deleteWebhook?drop_pending_updates=true", timeout=10)
    except: pass

    try:
        from telebot.types import BotCommand
        bot.set_my_commands([
            BotCommand("start", "بدء البوت"),
            BotCommand("owner", "لوحة المالك"),
            BotCommand("numberpanel", "لوحة الأرقام"),
            BotCommand("debug", "اختبار الاتصال بالموقع"),
        ])
    except: pass

    for attempt in range(5):
        try:
            logger.info(f"🚀 polling (محاولة {attempt + 1})...")
            bot.infinity_polling(timeout=60, long_polling_timeout=60, skip_pending=True)
            break
        except Exception as e:
            if "409" in str(e) or "Conflict" in str(e):
                if attempt < 4:
                    time.sleep(5 * (attempt + 1))
                else:
                    raise
            else:
                raise
