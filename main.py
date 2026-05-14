# # -*- coding: utf-8 -*-
# # Делает "одну группу один раз" из CSV с related-брендами.
# # Вход: C:\Users\user\Desktop\tgbot\export\related_edges.csv
# # Выход:
# #   export\related_groups_unique.csv : id ; count ; brands (через " | ")
# #   export\brand_to_group.csv        : brand ; group_id ; group_size
#
# import csv, os, re
# from urllib.parse import urlparse, unquote
#
# # --- ПУТИ ПОД ТВОЙ ПРОЕКТ ---
# BASE_DIR    = r"C:\Users\user\Desktop\tgbot"
# IN_CSV      = os.path.join(BASE_DIR, "export", "related_edges.csv")
# OUT_GROUPS  = os.path.join(BASE_DIR, "export", "related_groups_unique.csv")
# OUT_MAP     = os.path.join(BASE_DIR, "export", "brand_to_group.csv")
#
# # --- CSV utils ---
# def read_csv_smart(path):
#     with open(path, 'r', encoding='utf-8', newline='') as f:
#         sample = f.read(4096); f.seek(0)
#         try:
#             dialect = csv.Sniffer().sniff(sample, delimiters=";,")
#             delim = dialect.delimiter
#         except Exception:
#             delim = ';'
#         rows = list(csv.reader(f, delimiter=delim))
#     return rows, delim
#
# def write_csv(path, rows, delim=';'):
#     os.makedirs(os.path.dirname(path), exist_ok=True)
#     with open(path, 'w', encoding='utf-8', newline='') as f:
#         csv.writer(f, delimiter=delim).writerows(rows)
#
# # --- Нормализация имён ---
# BAD_TOKENS = {
#     'огляд','українська','українська мова','огляди','опис','детальніше','вхід','реєстрація',
#     'украинская','описание','обзор','войти','регистрация','читати','читати далі','переглянути'
# }
# def looks_bad(name):
#     n = (name or '').strip()
#     if not n or len(n) <= 2: return True
#     low = n.lower()
#     if low in BAD_TOKENS: return True
#     if any(t in low for t in ('огляд','україн','детальн','реєстрац','войти','регистрац')) and 'casino' not in low:
#         return True
#     return False
#
# def brand_from_slug(url):
#     if not url: return ''
#     try:
#         base = os.path.basename(urlparse(url).path).strip('/')
#         base = unquote(base)
#         base = re.sub(r'\.(html?|php)$','', base, flags=re.I)
#         base = re.sub(r'^(ohlyad|oglyad|ohliad|review|obzor)[\-_]+','', base, flags=re.I)
#         base = base.replace('-', ' ').replace('_',' ')
#         base = re.sub(r'\s+',' ', base).strip()
#         if not base: return ''
#         words = base.split(' ')
#         if words[-1].lower() == 'casino':
#             words[-1] = 'Casino'
#         elif 'casino' in base.lower():
#             words = [w for w in words if w.lower() != 'casino'] + ['Casino']
#         words = [w if w.isupper() else w.capitalize() for w in words]
#         title = ' '.join(words)
#         if 'casino' not in title.lower():
#             title += ' Casino'
#         return title.strip()
#     except Exception:
#         return ''
#
# def normalize_name(name, url=None):
#     if looks_bad(name):
#         n = brand_from_slug(url or '')
#         return n or (name or '').strip()
#     n = re.sub(r'\s+',' ', name or '').strip()
#     n = re.sub(r'\bcasino\b','Casino', n, flags=re.I)
#     return n
#
# # --- Распознаём формат входа ---
# ALIASES = {
#     'from_name': {'from_name','from','a','casino_from','source_name','brand_a'},
#     'from_url' : {'from_url','fromlink','a_url','url_from','link_from','source_url'},
#     'to_name'  : {'to_name','to','b','casino_to','target_name','brand_b'},
#     'to_url'   : {'to_url','tolink','b_url','url_to','link_to','target_url'},
#     'brands'   : {'brands','group','related','related_brands'}
# }
# def colmap(header):
#     h = [(c or '').strip().lower() for c in header]
#     res = {}
#     for key, aliases in ALIASES.items():
#         idx = -1
#         for i, name in enumerate(h):
#             if name in aliases: idx = i; break
#         res[key] = idx
#     return res
#
# # --- Union-Find ---
# class DSU:
#     def __init__(self): self.p = {}
#     def find(self, x):
#         if x not in self.p: self.p[x] = x
#         while self.p[x] != x:
#             self.p[x] = self.p[self.p[x]]
#             x = self.p[x]
#         return x
#     def union(self, a, b):
#         ra, rb = self.find(a), self.find(b)
#         if ra != rb: self.p[rb] = ra
#
# # --- Основное ---
# def main():
#     rows, _ = read_csv_smart(IN_CSV)
#     if not rows:
#         print("Пустой CSV"); return
#
#     header = rows[0]
#     cm = colmap(header)
#
#     dsu = DSU()
#     nodes = set()
#
#     if cm['brands'] != -1:
#         # Формат "brands": одна строка = список брендов через " | "
#         for r in rows[1:]:
#             raw = (r[cm['brands']] or '').strip()
#             if not raw: continue
#             brands = [b.strip() for b in raw.split('|') if b.strip()]
#             # нормализация названий (без URL в этом формате)
#             brands = [normalize_name(b) for b in brands if b]
#             if len(brands) < 2:
#                 if brands: nodes.add(brands[0])
#                 continue
#             first = brands[0]
#             nodes.add(first)
#             for b in brands[1:]:
#                 nodes.add(b)
#                 dsu.union(first, b)
#     else:
#         # Формат рёбер: from_*/to_*
#         need = all(cm[k] != -1 for k in ('from_name','from_url','to_name','to_url'))
#         if not need:
#             print("Не нашёл колонки. Заголовки:", header)
#             return
#         for r in rows[1:]:
#             a = normalize_name(r[cm['from_name']], r[cm['from_url']])
#             b = normalize_name(r[cm['to_name']],   r[cm['to_url']])
#             if not a or not b or a == b: continue
#             nodes.add(a); nodes.add(b)
#             dsu.union(a, b)
#
#     # Собираем компоненты (РОВНО ОДИН РАЗ КАЖДАЯ ГРУППА)
#     comps = {}
#     for n in nodes:
#         root = dsu.find(n)
#         comps.setdefault(root, set()).add(n)
#
#     # Сортируем и сохраняем
#     groups_sorted = sorted(comps.values(), key=lambda s: (-len(s), sorted(s)[0]))
#
#     # 1) related_groups_unique.csv
#     out_groups = [["id","count","brands"]]
#     brand_to_gid = {}
#     for gid, g in enumerate(groups_sorted, start=1):
#         brands = sorted(g)
#         out_groups.append([gid, len(g), " | ".join(brands)])
#         for b in brands:
#             brand_to_gid[b] = (gid, len(g))
#     write_csv(OUT_GROUPS, out_groups, ';')
#
#     # 2) brand_to_group.csv
#     out_map = [["brand","group_id","group_size"]]
#     for b in sorted(brand_to_gid.keys()):
#         gid, sz = brand_to_gid[b]
#         out_map.append([b, gid, sz])
#     write_csv(OUT_MAP, out_map, ';')
#
#     print("OK. Групп:", len(groups_sorted), "Брендов:", len(nodes))
#     print("Файлы:")
#     print(" -", OUT_GROUPS)
#     print(" -", OUT_MAP)
#
# if __name__ == "__main__":
#     main()
from telegram import Update, ReplyKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import (
    ApplicationBuilder, CommandHandler, MessageHandler, filters,
    ContextTypes, ConversationHandler
)
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime

# =========================
# BOT SETTINGS
# =========================

BOT_TOKEN = "7623342514:AAE8j5RRJVK2z0DPbqhsdqAcLngj0IoyHhs"

ADMIN_CHAT_ID = -1002544442389

GOOGLE_JSON_FILE = "google_api.json"
SPREADSHEET_NAME = "PlayCash_WELCOME_data"
WORKSHEET_NAME = "AFFHUBKIEV"

# =========================
# STATES
# =========================

(
    LANG,
    WELCOME,
    PARTNER_BEFORE,
    PARTNER_TYPE,
    OTHER_PARTNER_TYPE,
    TRAFFIC_SOURCE,
    OTHER_TRAFFIC_SOURCE,
    ACCOUNT_STATUS,
    ACCOUNT_DETAILS,
    COMPANY_NAME,
    EXPECTATIONS
) = range(11)

# =========================
# GOOGLE SHEETS
# =========================

scope = [
    "https://spreadsheets.google.com/feeds",
    "https://www.googleapis.com/auth/drive"
]

creds = ServiceAccountCredentials.from_json_keyfile_name(GOOGLE_JSON_FILE, scope)
client = gspread.authorize(creds)
sheet = client.open(SPREADSHEET_NAME).worksheet(WORKSHEET_NAME)

# =========================
# TRANSLATIONS
# =========================

translations = {
    "UA": {
        "choose_lang": "Оберіть мову:",
        "welcome": (
            "Вітання від команди PlayCash!\n"
            "Це наш велком-бот для знайомства та рестарту партнерів.\n\n"
            "Якщо ти зацікавлений у партнерстві з PlayCash — дай відповіді на кілька питань."
        ),
        "ok": "ОК",

        "partner_before": "Ти раніше вже співпрацював з PlayCash?",
        "partner_before_options": [
            ["працювали в минулому"],
            ["зараз процюємо"],
            ["ні, але можна спробувати"],
            ["та я взагалі не з гембли"]
        ],

        "partner_type": "Ти розглядаєш партнерство з PlayCash як..",
        "partner_type_options": [
            ["рекламодавець"],
            ["вебмайстер"],
            ["арбітражна команда"],
            ["інше"]
        ],
        "other_partner_type": "Будь ласка, введіть вашу роль вручну:",

        "traffic_source": "Вкажіть основне джерело трафіку.",
        "traffic_source_options": [
            ["SEO"],
            ["ASO"],
            ["FB"],
            ["Google"],
            ["інше"]
        ],
        "other_traffic_source": "Будь ласка, введіть ваше джерело трафіку вручну:",

        "account_status": "Чи маєш ти зареєстрований партнерський акаунт PlayCash?",
        "account_status_options": [
            ["так, вкажу email (бажано)"],
            ["так, вкажу ID кабінету"],
            ["був, але втратив доступ"],
            ["не маю акаунту"]
        ],
        "account_details": "Будь ласка, введіть email або ID:",

        "company_name": "Назва компанії / команди:",
        "expectations": "Які очікування від подальшого партнерства з PlayCash?",

        "thank_you": "✅ Дякуємо!",
        "your_id": "Твій ID для розіграшу:",
        "already_registered": "Ви вже зареєстровані.",
        "old_id": "Ваш ID:"
    },

    "EN": {
        "choose_lang": "Choose language:",
        "welcome": (
            "Hi from the PlayCash team!\n"
            "This is our welcome bot for partners.\n"
            "Please answer the following questions."
        ),
        "ok": "OK",

        "partner_before": "Have you worked with PlayCash before?",
        "partner_before_options": [
            ["Worked before"],
            ["Currently working"],
            ["No, but can try"],
            ["Not from gambling"]
        ],

        "partner_type": "Would you partner with PlayCash as...",
        "partner_type_options": [
            ["advertiser"],
            ["webmaster"],
            ["arbitrage team"],
            ["other"]
        ],
        "other_partner_type": "Please enter your role manually:",

        "traffic_source": "What's your main traffic source?",
        "traffic_source_options": [
            ["SEO"],
            ["ASO"],
            ["FB"],
            ["Google"],
            ["other"]
        ],
        "other_traffic_source": "Please enter your traffic source manually:",

        "account_status": "Do you have a registered PlayCash partner account?",
        "account_status_options": [
            ["Yes, I'll provide email"],
            ["Yes, I'll provide account ID"],
            ["Had one, lost access"],
            ["No account"]
        ],
        "account_details": "Please enter email or ID:",

        "company_name": "Your company/team name:",
        "expectations": "What is your expectations?",

        "thank_you": "✅ Thank you!",
        "your_id": "Your raffle ID:",
        "already_registered": "You are already registered.",
        "old_id": "Your ID:"
    },

    "RU": {
        "choose_lang": "Выберите язык:",
        "welcome": (
            "Привет от команды PlayCash!\n"
            "Пожалуйста, ответьте на вопросы."
        ),
        "ok": "ОК",

        "partner_before": "Ты уже работал с PlayCash?",
        "partner_before_options": [
            ["Раньше работал"],
            ["Сейчас работаю"],
            ["Нет, но могу попробовать"],
            ["Не из гемблы"]
        ],

        "partner_type": "Ты партнер как...",
        "partner_type_options": [
            ["рекламодатель"],
            ["вебмастер"],
            ["арбитражная команда"],
            ["другое"]
        ],
        "other_partner_type": "Введите роль вручную:",

        "traffic_source": "Основное джерело трафіку:",
        "traffic_source_options": [
            ["SEO"],
            ["ASO"],
            ["FB"],
            ["Google"],
            ["другое"]
        ],
        "other_traffic_source": "Введите источник вручную:",

        "account_status": "Есть ли у тебя партнерский аккаунт PlayCash?",
        "account_status_options": [
            ["Да, email"],
            ["Да, ID"],
            ["Был, потерял доступ"],
            ["Нет аккаунта"]
        ],
        "account_details": "Введите email или ID:",

        "company_name": "Название компании/команды:",
        "expectations": "Ожидания от работы с нами ?:",

        "thank_you": "✅ Спасибо!",
        "your_id": "Ваш ID для розыгрыша:",
        "already_registered": "Вы уже зарегистрированы.",
        "old_id": "Ваш ID:"
    }
}


# =========================
# HELPERS
# =========================

def get_username_or_fallback(update: Update) -> str:
    """
    Возвращает username пользователя.
    Если username отсутствует — возвращает user_<telegram_id>.
    """
    username = update.effective_user.username
    if username:
        return username.strip()
    return f"user_{update.effective_user.id}"


def get_existing_id_by_username(username: str):
    """
    Проверяет колонку C (Username).
    Если такой username уже есть — возвращает ID из колонки A.
    Если нет — возвращает None.
    """
    if not username:
        return None

    try:
        usernames = sheet.col_values(3)  # C column
    except Exception:
        return None

    for row_index, stored_username in enumerate(usernames[1:], start=2):
        if str(stored_username).strip().lower() == str(username).strip().lower():
            try:
                id_value = sheet.cell(row_index, 1).value  # A column
                return int(str(id_value).strip())
            except Exception:
                return None

    return None


def get_next_id() -> int:
    """
    Надёжно считает следующий ID через колонку A.
    Заголовок в первой строке пропускается.
    """
    try:
        col_a = sheet.col_values(1)
    except Exception:
        return 1

    existing_ids = []

    for value in col_a[1:]:
        try:
            existing_ids.append(int(str(value).strip()))
        except Exception:
            pass

    if not existing_ids:
        return 1

    return max(existing_ids) + 1


def is_traffic_required_partner_type(value: str) -> bool:
    """
    Проверяет, нужно ли задавать вопросы 4.1 и 4.2.
    Только для вебмастера и арбитражной команды.
    """
    normalized = value.strip().lower()

    return normalized in [
        "вебмайстер",
        "вебмастер",
        "webmaster",
        "арбітражна команда",
        "арбитражная команда",
        "arbitrage team"
    ]


def is_other_option(value: str) -> bool:
    normalized = value.strip().lower()
    return normalized in ["інше", "другое", "other"]


def is_positive_account_answer(value: str) -> bool:
    normalized = value.strip().lower()
    return normalized.startswith(("так", "yes", "да"))


# =========================
# BOT HANDLERS
# =========================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    username = get_username_or_fallback(update)

    existing_id = get_existing_id_by_username(username)
    if existing_id:
        await update.message.reply_text(
            f"Вы уже зарегистрированы.\nВаш ID: {existing_id}",
            reply_markup=ReplyKeyboardRemove()
        )
        return ConversationHandler.END

    await update.message.reply_text(
        f"{translations['UA']['choose_lang']} / "
        f"{translations['EN']['choose_lang']} / "
        f"{translations['RU']['choose_lang']}",
        reply_markup=ReplyKeyboardMarkup(
            [["UA", "EN", "RU"]],
            one_time_keyboard=True,
            resize_keyboard=True
        )
    )
    return LANG


async def get_lang(update: Update, context: ContextTypes.DEFAULT_TYPE):
    lang = update.message.text.strip().upper()

    if lang not in translations:
        await update.message.reply_text(
            "Choose language / Оберіть мову / Выберите язык:",
            reply_markup=ReplyKeyboardMarkup(
                [["UA", "EN", "RU"]],
                one_time_keyboard=True,
                resize_keyboard=True
            )
        )
        return LANG

    context.user_data["lang"] = lang

    await update.message.reply_text(
        translations[lang]["welcome"],
        reply_markup=ReplyKeyboardMarkup(
            [[translations[lang]["ok"]]],
            one_time_keyboard=True,
            resize_keyboard=True
        )
    )
    return WELCOME


async def get_welcome(update: Update, context: ContextTypes.DEFAULT_TYPE):
    lang = context.user_data["lang"]

    await update.message.reply_text(
        translations[lang]["partner_before"],
        reply_markup=ReplyKeyboardMarkup(
            translations[lang]["partner_before_options"],
            one_time_keyboard=True,
            resize_keyboard=True
        )
    )
    return PARTNER_BEFORE


async def get_partner_before(update: Update, context: ContextTypes.DEFAULT_TYPE):
    lang = context.user_data["lang"]
    context.user_data["partner_before"] = update.message.text.strip()

    await update.message.reply_text(
        translations[lang]["partner_type"],
        reply_markup=ReplyKeyboardMarkup(
            translations[lang]["partner_type_options"],
            one_time_keyboard=True,
            resize_keyboard=True
        )
    )
    return PARTNER_TYPE


async def get_partner_type(update: Update, context: ContextTypes.DEFAULT_TYPE):
    lang = context.user_data["lang"]
    choice = update.message.text.strip()

    context.user_data["partner_type"] = choice

    if is_traffic_required_partner_type(choice):
        await update.message.reply_text(
            translations[lang]["traffic_source"],
            reply_markup=ReplyKeyboardMarkup(
                translations[lang]["traffic_source_options"],
                one_time_keyboard=True,
                resize_keyboard=True
            )
        )
        return TRAFFIC_SOURCE

    if is_other_option(choice):
        await update.message.reply_text(
            translations[lang]["other_partner_type"],
            reply_markup=ReplyKeyboardRemove()
        )
        return OTHER_PARTNER_TYPE

    await update.message.reply_text(
        translations[lang]["company_name"],
        reply_markup=ReplyKeyboardRemove()
    )
    return COMPANY_NAME


async def get_other_partner_type(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Если выбрали 'другое' в вопросе 4 — сохраняем введённую роль.
    После этого НЕ задаём traffic/account вопросы, потому что 4.1/4.2 нужны только для webmaster/arbitrage.
    """
    lang = context.user_data["lang"]
    context.user_data["partner_type"] = update.message.text.strip()

    await update.message.reply_text(
        translations[lang]["company_name"],
        reply_markup=ReplyKeyboardRemove()
    )
    return COMPANY_NAME


async def get_traffic_source(update: Update, context: ContextTypes.DEFAULT_TYPE):
    lang = context.user_data["lang"]
    choice = update.message.text.strip()

    context.user_data["traffic_source"] = choice

    if is_other_option(choice):
        await update.message.reply_text(
            translations[lang]["other_traffic_source"],
            reply_markup=ReplyKeyboardRemove()
        )
        return OTHER_TRAFFIC_SOURCE

    await update.message.reply_text(
        translations[lang]["account_status"],
        reply_markup=ReplyKeyboardMarkup(
            translations[lang]["account_status_options"],
            one_time_keyboard=True,
            resize_keyboard=True
        )
    )
    return ACCOUNT_STATUS


async def get_other_traffic_source(update: Update, context: ContextTypes.DEFAULT_TYPE):
    lang = context.user_data["lang"]
    context.user_data["traffic_source"] = update.message.text.strip()

    await update.message.reply_text(
        translations[lang]["account_status"],
        reply_markup=ReplyKeyboardMarkup(
            translations[lang]["account_status_options"],
            one_time_keyboard=True,
            resize_keyboard=True
        )
    )
    return ACCOUNT_STATUS


async def get_account_status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    lang = context.user_data["lang"]
    choice = update.message.text.strip()

    context.user_data["account_status"] = choice

    if is_positive_account_answer(choice):
        await update.message.reply_text(
            translations[lang]["account_details"],
            reply_markup=ReplyKeyboardRemove()
        )
        return ACCOUNT_DETAILS

    await update.message.reply_text(
        translations[lang]["company_name"],
        reply_markup=ReplyKeyboardRemove()
    )
    return COMPANY_NAME


async def get_account_details(update: Update, context: ContextTypes.DEFAULT_TYPE):
    lang = context.user_data["lang"]
    context.user_data["account_status_details"] = update.message.text.strip()

    await update.message.reply_text(
        translations[lang]["company_name"],
        reply_markup=ReplyKeyboardRemove()
    )
    return COMPANY_NAME


async def get_company(update: Update, context: ContextTypes.DEFAULT_TYPE):
    lang = context.user_data["lang"]
    context.user_data["company_name"] = update.message.text.strip()

    await update.message.reply_text(
        translations[lang]["expectations"],
        reply_markup=ReplyKeyboardRemove()
    )
    return EXPECTATIONS


async def get_expectations(update: Update, context: ContextTypes.DEFAULT_TYPE):
    lang = context.user_data["lang"]
    context.user_data["expectations"] = update.message.text.strip()

    username = get_username_or_fallback(update)

    existing_id = get_existing_id_by_username(username)
    if existing_id:
        await update.message.reply_text(
            f"{translations[lang]['already_registered']}\n"
            f"{translations[lang]['old_id']} {existing_id}",
            reply_markup=ReplyKeyboardRemove()
        )

        try:
            await context.bot.send_message(
                chat_id=ADMIN_CHAT_ID,
                text=(
                    "♻️ Повторная попытка регистрации:\n"
                    f"Username: @{username}\n"
                    f"Существующий ID: {existing_id}"
                )
            )
        except Exception:
            pass

        return ConversationHandler.END

    new_id = get_next_id()

    row = [
        new_id,
        datetime.now().strftime("%d.%m.%Y"),
        username,
        context.user_data.get("partner_before", ""),
        context.user_data.get("partner_type", ""),
        context.user_data.get("traffic_source", ""),
        context.user_data.get("account_status", ""),
        context.user_data.get("account_status_details", ""),
        context.user_data.get("company_name", ""),
        context.user_data.get("expectations", "")
    ]

    sheet.append_row(row)

    await update.message.reply_text(
        f"{translations[lang]['thank_you']}\n"
        f"{translations[lang]['your_id']} {new_id}",
        reply_markup=ReplyKeyboardRemove()
    )

    admin_message = (
        "🆕 Новый участник зарегистрирован:\n"
        f"ID: {new_id}\n"
        f"Date: {row[1]}\n"
        f"Username: @{row[2]}\n"
        f"Опыт с PlayCash: {row[3]}\n"
        f"Роль: {row[4]}\n"
        f"Трафик: {row[5]}\n"
        f"Аккаунт PlayCash: {row[6]}\n"
        f"Детали аккаунта: {row[7]}\n"
        f"Компания: {row[8]}\n"
        f"Ожидания: {row[9]}"
    )

    await context.bot.send_message(
        chat_id=ADMIN_CHAT_ID,
        text=admin_message
    )

    return ConversationHandler.END


# =========================
# APP START
# =========================

app = ApplicationBuilder().token(BOT_TOKEN).build()

conversation_handler = ConversationHandler(
    entry_points=[CommandHandler("start", start)],
    states={
        LANG: [
            MessageHandler(filters.TEXT & ~filters.COMMAND, get_lang)
        ],
        WELCOME: [
            MessageHandler(filters.TEXT & ~filters.COMMAND, get_welcome)
        ],
        PARTNER_BEFORE: [
            MessageHandler(filters.TEXT & ~filters.COMMAND, get_partner_before)
        ],
        PARTNER_TYPE: [
            MessageHandler(filters.TEXT & ~filters.COMMAND, get_partner_type)
        ],
        OTHER_PARTNER_TYPE: [
            MessageHandler(filters.TEXT & ~filters.COMMAND, get_other_partner_type)
        ],
        TRAFFIC_SOURCE: [
            MessageHandler(filters.TEXT & ~filters.COMMAND, get_traffic_source)
        ],
        OTHER_TRAFFIC_SOURCE: [
            MessageHandler(filters.TEXT & ~filters.COMMAND, get_other_traffic_source)
        ],
        ACCOUNT_STATUS: [
            MessageHandler(filters.TEXT & ~filters.COMMAND, get_account_status)
        ],
        ACCOUNT_DETAILS: [
            MessageHandler(filters.TEXT & ~filters.COMMAND, get_account_details)
        ],
        COMPANY_NAME: [
            MessageHandler(filters.TEXT & ~filters.COMMAND, get_company)
        ],
        EXPECTATIONS: [
            MessageHandler(filters.TEXT & ~filters.COMMAND, get_expectations)
        ],
    },
    fallbacks=[]
)

app.add_handler(conversation_handler)

print("Bot is running...")
app.run_polling()