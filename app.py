
import streamlit as st
import pandas as pd
import json, hashlib, base64, re, os, hmac, re
from pathlib import Path
from datetime import datetime
from sqlalchemy import create_engine, text

st.set_page_config(page_title="Partner Portal Partner Portal", page_icon="🎓", layout="wide")

BASE = Path(__file__).parent
DATA = BASE / "data"
LOGO = BASE / "uniquest_logo.png"
USERS = DATA / "users.json"
UNIS = DATA / "universities.csv"
CRITERIA = DATA / "admission_criteria.csv"
SCHOLARSHIPS = DATA / "scholarship_rules.csv"
ELIG_LOGS = DATA / "eligibility_logs.csv"
TUIT_LOGS = DATA / "tuition_logs.csv"
INQUIRIES = DATA / "inquiries.csv"
APPLICATIONS = DATA / "applications.csv"
DATABASE_URL_KEY = "DATABASE_URL"

CSV_TABLE_MAP = {
    "universities.csv": "universities",
    "admission_criteria.csv": "admission_criteria",
    "scholarship_rules.csv": "scholarship_rules",
    "eligibility_logs.csv": "eligibility_logs",
    "tuition_logs.csv": "tuition_logs",
    "inquiries.csv": "inquiries",
    "applications.csv": "applications",
}
JSON_TABLE_MAP = {
    "users.json": "users",
    "agencies.json": "agencies",
}

def hash_pw(p): return hashlib.sha256(p.encode()).hexdigest()

def get_database_url():
    """
    Supabase/PostgreSQL connection string.
    Locally: .streamlit/secrets.toml
    Streamlit Cloud: App settings > Secrets
    """
    try:
        url = st.secrets.get(DATABASE_URL_KEY, "")
    except Exception:
        url = ""
    if not url:
        url = os.getenv(DATABASE_URL_KEY, "")
    if not url:
        st.error("DATABASE_URL is not set. Please add it to .streamlit/secrets.toml or Streamlit Cloud Secrets.")
        st.stop()
    return url

@st.cache_resource(show_spinner=False)
def get_engine():
    return create_engine(get_database_url(), pool_pre_ping=True)

def _clean_df_for_db(df):
    return df.fillna("").replace(["nan", "NaN", "None", "null", "<NA>"], "")

def _table_for_csv_path(p):
    return CSV_TABLE_MAP.get(Path(p).name)

def _table_for_json_path(p):
    return JSON_TABLE_MAP.get(Path(p).name)

def _table_exists(table):
    try:
        with get_engine().connect() as c:
            result = c.execute(text("SELECT to_regclass(:table_name)"), {"table_name": table}).scalar()
            return result is not None
    except Exception:
        return False

def _ensure_db_table_from_file(p):
    """
    First-use migration helper for Supabase/PostgreSQL.
    Keeps the v58 design/code structure, but stores data in Supabase.
    If the DB table does not exist yet, it is created from the original CSV/JSON seed file.
    """
    p = Path(p)

    if p.suffix.lower() == ".csv":
        table = _table_for_csv_path(p)
        if not table:
            return

        if _table_exists(table):
            return

        if p.exists():
            df = pd.read_csv(p, keep_default_na=False).fillna("")
        else:
            df = pd.DataFrame()

        _clean_df_for_db(df).to_sql(table, get_engine(), if_exists="replace", index=False)

    elif p.suffix.lower() == ".json":
        table = _table_for_json_path(p)
        if not table:
            return

        if _table_exists(table):
            return

        if p.exists():
            data = json.loads(p.read_text(encoding="utf-8"))
            df = pd.DataFrame(data)
        else:
            df = pd.DataFrame()

        _clean_df_for_db(df).to_sql(table, get_engine(), if_exists="replace", index=False)

@st.cache_data(ttl=300, show_spinner=False)
def _read_sql_table_cached(table):
    return pd.read_sql_query(text(f'SELECT * FROM "{table}"'), get_engine()).fillna("")

@st.cache_data(ttl=300, show_spinner=False)
def _read_seed_csv_cached(path_str):
    return pd.read_csv(path_str, keep_default_na=False).fillna("")

@st.cache_data(ttl=300, show_spinner=False)
def _read_seed_json_cached(path_str):
    return json.loads(Path(path_str).read_text(encoding="utf-8")) if Path(path_str).exists() else []

def read_csv(p):
    table = _table_for_csv_path(p)
    if table:
        _ensure_db_table_from_file(p)
        try:
            return _read_sql_table_cached(table).copy()
        except Exception as e:
            st.error(f"Could not read table '{table}': {e}")
            return pd.DataFrame()

    if not Path(p).exists():
        return pd.DataFrame()
    return _read_seed_csv_cached(str(p)).copy()

def write_csv(p, df):
    df = _clean_df_for_db(df)
    table = _table_for_csv_path(p)
    if table:
        df.to_sql(table, get_engine(), if_exists="replace", index=False)

        # Also update the local seed CSV for local backup. Supabase is still the main DB.
        try:
            Path(p).parent.mkdir(parents=True, exist_ok=True)
            df.to_csv(p, index=False, encoding="utf-8-sig")
        except Exception:
            pass

        st.cache_data.clear()
        return

    df.to_csv(p, index=False, encoding="utf-8-sig")
    st.cache_data.clear()

def add_row(p, row):
    df = read_csv(p)
    if df.empty:
        df = pd.DataFrame([row])
    else:
        df.loc[len(df)] = row
    write_csv(p, df)

def read_json(p):
    table = _table_for_json_path(p)
    if table:
        _ensure_db_table_from_file(p)
        try:
            df = _read_sql_table_cached(table).copy()
            return df.to_dict(orient="records")
        except Exception as e:
            st.error(f"Could not read table '{table}': {e}")
            return []

    return _read_seed_json_cached(str(p))

def write_json(p, d):
    table = _table_for_json_path(p)
    if table:
        pd.DataFrame(d).fillna("").to_sql(table, get_engine(), if_exists="replace", index=False)
        st.cache_data.clear()
        return

    Path(p).write_text(json.dumps(d, ensure_ascii=False, indent=2), encoding="utf-8")
    st.cache_data.clear()

def find_user(username):
    for u in read_json(USERS):
        if str(u["username"]).lower() == str(username).lower():
            return u
    return None


def normalize_agency_id(name):
    base = re.sub(r"[^a-z0-9]+", "_", str(name).lower()).strip("_")
    return base or "unknown_agency"

def read_agencies():
    path = DATA / "agencies.json"
    if not path.exists():
        return []
    return read_json(path)

def write_agencies(items):
    write_json(DATA / "agencies.json", items)

def find_agency_by_name(name):
    for a in read_agencies():
        if str(a.get("agency_name","")).lower() == str(name).lower():
            return a
    return None


def get_current_user():
    if not st.session_state.get("username"):
        return None
    return find_user(st.session_state.username)

def current_agency_id():
    user = get_current_user()
    if not user:
        return ""
    return user.get("agency_id", normalize_agency_id(user.get("agency_name","")))

def can_view_log_row(row):
    if st.session_state.role == "admin":
        return True
    if st.session_state.role == "agency_rep":
        return str(row.get("agency_id","")) == str(current_agency_id())
    return str(row.get("partner_username","")) == str(st.session_state.username)

def visible_logs(df):
    if not len(df):
        return df
    if st.session_state.role == "admin":
        return df
    if st.session_state.role == "agency_rep":
        return df[df.get("agency_id", "") == current_agency_id()]
    return df[df.get("partner_username", "") == st.session_state.username]

@st.cache_data(ttl=3600, show_spinner=False)
def _b64_file_cached(path_str):
    p = Path(path_str)
    return base64.b64encode(p.read_bytes()).decode() if p.exists() and p.is_file() else ""

def b64(path):
    try:
        if path is None:
            return ""
        p = str(path).strip()
        if p == "" or p.lower() in ["nan", "none", "null", "<na>"]:
            return ""
        full_path = BASE / p
        if not full_path.exists() or not full_path.is_file():
            return ""
        return _b64_file_cached(str(full_path))
    except Exception:
        return ""

def asset_img_url(relative_path):
    encoded = b64(relative_path)
    return "data:image/jpeg;base64," + encoded if encoded else ""

def asset_img_html(relative_path, class_name="uni-photo"):
    encoded = b64(relative_path)
    if not encoded:
        return '<div class="thumb">🏛️</div>'
    return f'<img class="{class_name}" src="data:image/jpeg;base64,{encoded}">'

@st.cache_data(ttl=300, show_spinner=False)
def universities():
    return read_csv(UNIS)

@st.cache_data(ttl=300, show_spinner=False)
def criteria():
    return read_csv(CRITERIA)

@st.cache_data(ttl=300, show_spinner=False)
def scholarship_rules():
    return read_csv(SCHOLARSHIPS) if SCHOLARSHIPS.exists() else pd.DataFrame()

if "page" not in st.session_state: st.session_state.page = "Home"
if "logged_in" not in st.session_state: st.session_state.logged_in = False
if "role" not in st.session_state: st.session_state.role = None
if "username" not in st.session_state: st.session_state.username = None
if "agency_name" not in st.session_state: st.session_state.agency_name = None
if "full_name" not in st.session_state: st.session_state.full_name = None
if "agency_id" not in st.session_state: st.session_state.agency_id = None
if "account_type" not in st.session_state: st.session_state.account_type = None


def _set_login_session_from_user_v60(user):
    st.session_state.logged_in = True
    st.session_state.username = user["username"]
    st.session_state.role = user["role"]
    st.session_state.agency_name = user.get("agency_name", "")
    st.session_state.agency_id = user.get("agency_id", normalize_agency_id(user.get("agency_name", "")))
    st.session_state.full_name = user.get("full_name", "")
    st.session_state.account_type = user.get("account_type", user.get("role", ""))

def _make_auth_token_v60(user):
    data = f'{user.get("username","")}|{user.get("password_hash","")}|{user.get("status","")}|{user.get("role","")}'
    secret = get_database_url()
    sig = hmac.new(secret.encode("utf-8"), data.encode("utf-8"), hashlib.sha256).hexdigest()[:40]
    return f'{user.get("username","")}:{sig}'

def _verify_auth_token_v60(token):
    try:
        username, sig = str(token).split(":", 1)
        user = find_user(username)
        if not user or user.get("status") != "approved":
            return None
        expected = _make_auth_token_v60(user).split(":", 1)[1]
        if hmac.compare_digest(sig, expected):
            return user
    except Exception:
        return None
    return None

def restore_login_from_query_v60():
    if st.session_state.get("logged_in"):
        return
    try:
        token = st.query_params.get("auth", "")
    except Exception:
        token = ""
    if isinstance(token, list):
        token = token[0] if token else ""
    if token:
        user = _verify_auth_token_v60(token)
        if user:
            _set_login_session_from_user_v60(user)
            if st.session_state.page in ["Home", "Login", "Partner Sign Up"]:
                st.session_state.page = "Admin Dashboard" if user["role"] == "admin" else "Dashboard"

restore_login_from_query_v60()


st.markdown("""
<style>
:root {--navy:#002B5B;--navy2:#053B7A;--blue:#005BDB;--black:#101828;--muted:#667085;--light:#F6F8FC;--border:#D9E2F1;}
.stApp {background:#FFFFFF;color:var(--black);}
.block-container {padding-top:0rem !important; max-width:100% !important; padding-left:1.5rem !important; padding-right:1.5rem !important;}
h1,h2,h3,h4,h5,h6,p,div,span,label,li {color:var(--black);}
.navy, .navy * {color:white !important;}
.header-box {background:white;border-bottom:1px solid #E7EEF8;padding:6px 12px 8px 12px;margin-bottom:0;}
.logo {max-width:280px;max-height:92px;object-fit:contain;}
.hero {background:linear-gradient(90deg,rgba(0,43,91,.98),rgba(5,59,122,.82)), radial-gradient(circle at 70% 10%, rgba(255,255,255,.12), rgba(255,255,255,0)); padding:64px 56px; min-height:350px;}
.hero h1 {color:white!important;font-size:50px;line-height:1.1;font-weight:900;margin:18px 0;}
.hero p {color:white!important;font-size:18px;max-width:700px;}
.badge {display:inline-block;background:#005BDB;color:white!important;padding:8px 18px;border-radius:999px;font-weight:850;margin-bottom:10px;}
.blue-btn {display:inline-block;background:#005BDB;color:white!important;padding:12px 22px;border-radius:8px;font-weight:850;margin-right:10px;}
.outline-white {display:inline-block;color:white!important;border:1px solid white;padding:12px 22px;border-radius:8px;font-weight:850;}
.section {padding:30px 56px;}
.card-grid {display:grid;grid-template-columns:repeat(5,1fr);gap:18px;}
.card {background:#fff;border:1px solid var(--border);border-radius:15px;padding:18px;box-shadow:0 8px 20px rgba(16,24,40,.06);}
.thumb {height:105px;border-radius:12px;background:linear-gradient(135deg,#E3EFFF,#F8FBFF);display:flex;align-items:center;justify-content:center;font-size:42px;color:#005BDB!important;font-weight:900;margin-bottom:12px;}
.muted {color:var(--muted)!important;}
.features {display:grid;grid-template-columns:repeat(4,1fr);gap:15px;background:#EEF5FF;padding:22px 56px;}
.feature {display:flex;gap:12px;align-items:center;}
.icon {width:42px;height:42px;border-radius:50%;background:white;color:#005BDB!important;display:flex;align-items:center;justify-content:center;font-weight:900;}
.footer {background:#002B5B;padding:30px 56px;color:white!important;}
.footer * {color:white!important;}
.footer-grid {display:grid;grid-template-columns:2fr 1.4fr 1.4fr 1.7fr 1.3fr;gap:20px;}
.split {display:grid;grid-template-columns:1fr 1.35fr;min-height:640px;}
.left-navy {background:linear-gradient(90deg,#002B5B,#053B7A);padding:55px 55px;}
.left-navy * {color:white!important;}
.white-panel {background:white;border:1px solid var(--border);border-radius:18px;padding:24px;box-shadow:0 10px 26px rgba(16,24,40,.08);}
.dash {display:grid;grid-template-columns:250px 1fr;min-height:720px;}
.side {background:#002B5B;padding:25px 16px;}
.side * {color:white!important;}
.main {background:#F6F8FC;padding:28px 34px;}
.stats {display:grid;grid-template-columns:repeat(5,1fr);gap:14px;margin-bottom:18px;}
.stat {background:white;border:1px solid var(--border);border-radius:14px;padding:18px;box-shadow:0 6px 18px rgba(16,24,40,.05);}
.stat h2 {color:#005BDB!important;font-size:31px;margin:8px 0 0;}
.two {display:grid;grid-template-columns:1.2fr 1fr;gap:18px;}
.status-pass{background:#E5F8ED;color:#067647!important;padding:5px 10px;border-radius:999px;font-weight:850;}
.status-fail{background:#FDE8E8;color:#B42318!important;padding:5px 10px;border-radius:999px;font-weight:850;}
.status-pending{background:#FFF4D6;color:#B54708!important;padding:5px 10px;border-radius:999px;font-weight:850;}
.stTextInput input,.stNumberInput input,.stTextArea textarea,input[type="text"],input[type="password"],input[type="number"]{color:#101828!important;background:white!important;border:1px solid #C9D4E5!important;}
.stTextInput label,.stNumberInput label,.stTextArea label,.stSelectbox label,.stCheckbox label{color:#101828!important;font-weight:750!important;}
div[data-baseweb="select"]>div{background:white!important;color:#101828!important;border:1px solid #C9D4E5!important;}
div[data-baseweb="select"] *{color:#101828!important;fill:#101828!important;}
div[data-baseweb="popover"],div[data-baseweb="popover"] *{background:white!important;color:#101828!important;}
.stButton>button{border-radius:9px!important;font-weight:850!important;}
.main .stButton>button,.white-panel .stButton>button,.left-navy .stButton>button{background:#005BDB!important;color:white!important;border:1px solid #005BDB!important;}
.main .stButton>button *,.white-panel .stButton>button *,.left-navy .stButton>button *{color:white!important;}
.nav-row .stButton>button{background:white!important;color:#061A40!important;border:0!important;box-shadow:none!important;}
.nav-row .stButton>button *{color:#061A40!important;}
.nav-row .stButton>button:hover{color:#005BDB!important;border-bottom:3px solid #005BDB!important;}
section[data-testid="stSidebar"]{display:none;}
.stAlert *{color:#101828!important;}
[data-testid="stDataFrame"] *{color:#101828!important;}
@media(max-width:1000px){.card-grid,.features,.footer-grid,.split,.dash,.stats,.two{grid-template-columns:1fr}.hero h1{font-size:36px}}

/* v12 layout fixes */
.public-form-wrap {
    padding: 34px 44px;
}
.public-left-box {
    background: linear-gradient(90deg,#002B5B,#053B7A);
    padding: 48px 46px;
    min-height: 620px;
    border-radius: 0;
}
.public-left-box, .public-left-box * {
    color: #FFFFFF !important;
}
.hero-actions-real {
    margin-top: -110px;
    padding-left: 56px;
    padding-bottom: 40px;
}
.footer-link-button .stButton > button {
    background: transparent !important;
    color: #FFFFFF !important;
    border: 1px solid rgba(255,255,255,.45) !important;
}
.header-box {
    padding-top: 0px !important;
}


/* v13 clean clickable fixes */
.hero {
    padding-top: 58px !important;
}
.real-cta-area {
    margin-top: -94px;
    margin-left: 56px;
    margin-bottom: 46px;
    max-width: 520px;
}
.real-cta-area .stButton > button {
    height: 48px !important;
    font-weight: 850 !important;
}
.header-box img.logo {max-width:280px;max-height:92px;object-fit:contain;}


/* v14: put real clickable hero buttons visually inside navy hero */
.hero {
    padding-bottom: 90px !important;
}
.hero-real-buttons {
    margin-top: -88px;
    margin-left: 56px;
    margin-bottom: 42px;
    max-width: 560px;
    position: relative;
    z-index: 5;
}
.hero-real-buttons .stButton > button {
    background: #005BDB !important;
    color: #FFFFFF !important;
    border: 1px solid #005BDB !important;
    height: 48px !important;
    font-weight: 850 !important;
    border-radius: 8px !important;
}
.hero-real-buttons .stButton > button * {
    color: #FFFFFF !important;
}
.hero-real-buttons div[data-testid="column"]:nth-of-type(2) .stButton > button {
    background: transparent !important;
    border: 1px solid #FFFFFF !important;
    color: #FFFFFF !important;
}
.footer {
    background: #002B5B !important;
}
.footer, .footer * {
    color: #FFFFFF !important;
}


/* v15 admin fix: reduce unnecessary top blank space */
[data-testid="stHeader"] {
    height: 0rem !important;
    background: rgba(255,255,255,0) !important;
}
.main .block-container {padding-top:0rem !important; max-width:100% !important; padding-left:1.5rem !important; padding-right:1.5rem !important;}
.dash {
    margin-top: 0rem !important;
}
.main {
    padding-top: 18px !important;
}


/* v16: remove top blank area and clean footer */
[data-testid="stHeader"] {
    height: 0px !important;
    min-height: 0px !important;
    background: transparent !important;
}
[data-testid="stToolbar"] {
    display: none !important;
}
.main .block-container {padding-top:0rem !important; max-width:100% !important; padding-left:1.5rem !important; padding-right:1.5rem !important;}
.dash {
    margin-top: 0 !important;
    padding-top: 0 !important;
}
.main {
    padding-top: 12px !important;
}
.clean-footer {
    padding: 34px 56px 22px 56px !important;
}
.clean-footer-grid {
    display: grid;
    grid-template-columns: 1.4fr 1fr;
    gap: 80px;
    align-items: start;
}
.footer-brand h2 {
    font-size: 34px;
    margin-bottom: 8px;
}
.footer-brand p {
    font-size: 17px;
    opacity: 0.95;
}
.footer-contact {
    background: rgba(255,255,255,0.06);
    border: 1px solid rgba(255,255,255,0.14);
    border-radius: 16px;
    padding: 22px 26px;
}
.footer-contact h3 {
    margin-top: 0;
    font-size: 22px;
}
.footer-contact p {
    margin: 9px 0;
    font-size: 16px;
}
@media(max-width:900px){
    .clean-footer-grid {
        grid-template-columns: 1fr;
        gap: 20px;
    }
}


/* v17 logo + footer + admin spacing fixes */
[data-testid="stHeader"] {
    height: 0px !important;
    min-height: 0px !important;
    background: transparent !important;
}
[data-testid="stToolbar"] {
    display: none !important;
}
.main .block-container {
    padding-top: 0rem !important;
}
.header-box {
    padding-top: 4px !important;
    padding-bottom: 8px !important;
}
.footer-logo {
    width: 220px;
    max-height: 82px;
    object-fit: contain;
    background: #FFFFFF;
    border-radius: 12px;
    padding: 8px 10px;
    margin-bottom: 12px;
}
.clean-footer-grid {
    display: grid;
    grid-template-columns: 1.2fr 1fr;
    gap: 80px;
    align-items: center;
}
.footer-brand {
    display: flex;
    align-items: center;
    gap: 22px;
}
.footer-brand-text h2 {
    margin: 0 0 8px 0;
    font-size: 34px;
}
.footer-brand-text p {
    margin: 0;
    font-size: 17px;
}
.main {
    padding-top: 10px !important;
}
.dash {
    margin-top: 0 !important;
}
@media(max-width:900px){
    .footer-brand {
        display: block;
    }
    .clean-footer-grid {
        grid-template-columns: 1fr;
        gap: 24px;
    }
}


/* v18: stronger top-gap removal */
[data-testid="stHeader"],
header[data-testid="stHeader"] {
    height: 0px !important;
    min-height: 0px !important;
    max-height: 0px !important;
    background: transparent !important;
}
[data-testid="stToolbar"] {
    display: none !important;
}
.block-container {
    padding-top: 0rem !important;
    margin-top: 0rem !important;
}
div[data-testid="stVerticalBlock"] > div:empty {
    display: none !important;
    height: 0px !important;
    min-height: 0px !important;
}
.dash {
    margin-top: 0rem !important;
    padding-top: 0rem !important;
    min-height: auto !important;
}
.main {
    padding-top: 8px !important;
    margin-top: 0rem !important;
}
.public-left-box {
    padding-top: 38px !important;
}
.clean-footer {
    padding: 34px 56px 20px 56px !important;
}
.footer-contact, .footer-contact * {
    color: #FFFFFF !important;
}
.footer-contact {
    background: rgba(255,255,255,0.06);
    border: 1px solid rgba(255,255,255,0.16);
    border-radius: 16px;
    padding: 22px 26px;
}
.footer-logo {
    width: 220px !important;
    max-height: 82px !important;
    object-fit: contain !important;
    background: #FFFFFF !important;
    border-radius: 12px !important;
    padding: 8px 10px !important;
}


/* v19 Partner dashboard polished design */
.partner-hero {
    background: linear-gradient(90deg, rgba(0,43,91,.98), rgba(5,59,122,.86)),
                radial-gradient(circle at 80% 15%, rgba(255,255,255,.16), rgba(255,255,255,0));
    border-radius: 22px;
    padding: 42px 46px;
    margin-bottom: 24px;
    box-shadow: 0 12px 28px rgba(16,24,40,.12);
}
.partner-hero, .partner-hero * {
    color: #FFFFFF !important;
}
.partner-hero h1 {
    font-size: 42px;
    line-height: 1.14;
    margin: 0 0 12px 0;
    font-weight: 900;
}
.partner-hero p {
    font-size: 17px;
    margin: 0;
    opacity: .96;
}
.partner-status-pill {
    display: inline-block;
    background: rgba(255,255,255,.16);
    border: 1px solid rgba(255,255,255,.35);
    border-radius: 999px;
    padding: 8px 16px;
    font-weight: 850;
    margin-bottom: 16px;
}
.partner-stat-grid {
    display: grid;
    grid-template-columns: repeat(4, 1fr);
    gap: 16px;
    margin-bottom: 22px;
}
.partner-stat-card {
    background: #FFFFFF;
    border: 1px solid #D9E2F1;
    border-radius: 18px;
    padding: 20px 22px;
    box-shadow: 0 10px 24px rgba(16,24,40,.06);
}
.partner-stat-card h3 {
    margin: 0;
    color: #667085 !important;
    font-size: 15px;
}
.partner-stat-card h2 {
    margin: 10px 0 0 0;
    color: #005BDB !important;
    font-size: 34px;
    font-weight: 900;
}
.partner-grid-2 {
    display: grid;
    grid-template-columns: 1.25fr .9fr;
    gap: 18px;
}
.partner-panel {
    background: #FFFFFF;
    border: 1px solid #D9E2F1;
    border-radius: 18px;
    padding: 22px;
    box-shadow: 0 10px 24px rgba(16,24,40,.06);
}
.partner-action-card {
    background: #F6F8FC;
    border: 1px solid #D9E2F1;
    border-radius: 14px;
    padding: 16px;
    margin-bottom: 12px;
}
.partner-action-card h4 {
    margin: 0 0 6px 0;
    color: #101828 !important;
}
.partner-action-card p {
    margin: 0;
    color: #667085 !important;
}
@media(max-width:1000px){
    .partner-stat-grid, .partner-grid-2 {
        grid-template-columns: 1fr;
    }
}


/* v20 university image cards */
.uni-photo {
    width: 100%;
    height: 145px;
    object-fit: cover;
    border-radius: 12px;
    display: block;
    margin-bottom: 12px;
    border: 1px solid #E4EAF4;
}
.uni-photo-large {
    width: 100%;
    height: 240px;
    object-fit: cover;
    border-radius: 16px;
    display: block;
    margin-bottom: 18px;
    border: 1px solid #E4EAF4;
}
.card {
    overflow: hidden;
}


/* v21 top nav + footer cleanup */
.header-box {
    background: #FFFFFF !important;
    border-bottom: 1px solid #E7EEF8 !important;
    padding: 10px 18px 12px 18px !important;
    margin-bottom: 0 !important;
}
.logo-wrap {
    display: flex;
    align-items: center;
    height: 72px;
}
.logo {
    max-width: 260px !important;
    max-height: 72px !important;
    object-fit: contain !important;
}
.nav-button-wrap {
    display: flex;
    align-items: center;
    height: 72px;
}
.nav-button-wrap .stButton {
    width: 100%;
}
.nav-button-wrap .stButton > button {
    height: 44px !important;
    background: #FFFFFF !important;
    color: #061A40 !important;
    border: 1px solid #C8D3E2 !important;
    border-radius: 9px !important;
    font-weight: 850 !important;
    box-shadow: none !important;
}
.nav-button-wrap .stButton > button * {
    color: #061A40 !important;
}
.nav-button-wrap .stButton > button:hover {
    color: #005BDB !important;
    border-color: #005BDB !important;
}
.clean-footer {
    background: #002B5B !important;
    padding: 34px 56px 22px 56px !important;
}
.clean-footer, .clean-footer * {
    color: #FFFFFF !important;
}
.clean-footer-grid {
    display: grid;
    grid-template-columns: 1.25fr 1fr;
    gap: 80px;
    align-items: center;
}
.footer-brand {
    display: flex;
    align-items: center;
    gap: 22px;
}
.footer-logo {
    width: 220px !important;
    max-height: 82px !important;
    object-fit: contain !important;
    background: #FFFFFF !important;
    border-radius: 12px !important;
    padding: 8px 10px !important;
}
.footer-brand-text h2 {
    margin: 0 0 8px 0 !important;
    font-size: 34px !important;
}
.footer-brand-text p {
    margin: 0 !important;
    font-size: 17px !important;
}
.footer-contact {
    background: rgba(255,255,255,0.06) !important;
    border: 1px solid rgba(255,255,255,0.16) !important;
    border-radius: 16px !important;
    padding: 22px 26px !important;
}
.footer-contact h3 {
    margin-top: 0 !important;
}
.footer-contact p {
    margin: 8px 0 !important;
}
@media(max-width:900px){
    .clean-footer-grid {
        grid-template-columns: 1fr;
        gap: 24px;
    }
    .footer-brand {
        display: block;
    }
}


/* v22 basic university info */
.basic-info-grid {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 10px 18px;
    margin-top: 12px;
}
.basic-info-item {
    background: #F6F8FC;
    border: 1px solid #E3EAF5;
    border-radius: 10px;
    padding: 10px 12px;
    color: #101828 !important;
}
.basic-info-item b {
    color: #002B5B !important;
}
@media(max-width:900px){
    .basic-info-grid {
        grid-template-columns: 1fr;
    }
}


/* v23 footer and school-size fixes */
.clean-footer {
    background: #002B5B !important;
    padding: 34px 56px 22px 56px !important;
}
.clean-footer,
.clean-footer *,
.footer-brand-safe,
.footer-brand-safe *,
.footer-contact-safe,
.footer-contact-safe * {
    color: #FFFFFF !important;
}
.footer-brand-safe {
    display: flex;
    align-items: center;
    gap: 22px;
}
.footer-brand-safe h2 {
    margin: 0 0 8px 0 !important;
    font-size: 34px !important;
}
.footer-brand-safe p {
    margin: 0 !important;
    font-size: 17px !important;
}
.footer-logo {
    width: 220px !important;
    max-height: 82px !important;
    object-fit: contain !important;
    background: #FFFFFF !important;
    border-radius: 12px !important;
    padding: 8px 10px !important;
}
.footer-contact-safe {
    background: rgba(255,255,255,0.08) !important;
    border: 1px solid rgba(255,255,255,0.18) !important;
    border-radius: 16px !important;
    padding: 22px 26px !important;
}
.footer-contact-safe h3 {
    margin-top: 0 !important;
    color: #FFFFFF !important;
}
.footer-contact-safe p {
    margin: 8px 0 !important;
    color: #FFFFFF !important;
}


/* v24 English info + footer final fix */
.clean-footer {
    background: #002B5B !important;
    padding: 34px 56px 22px 56px !important;
}
.clean-footer, .clean-footer * {
    color: #FFFFFF !important;
}
.clean-footer-grid {
    display: grid;
    grid-template-columns: 1.25fr 1fr;
    gap: 80px;
    align-items: center;
}
.footer-brand-safe {
    display: flex;
    align-items: center;
    gap: 22px;
}
.footer-brand-safe h2 {
    margin: 0 0 8px 0 !important;
    font-size: 34px !important;
}
.footer-brand-safe p {
    margin: 0 !important;
    font-size: 17px !important;
}
.footer-logo {
    width: 220px !important;
    max-height: 82px !important;
    object-fit: contain !important;
    background: #FFFFFF !important;
    border-radius: 12px !important;
    padding: 8px 10px !important;
}
.footer-contact-safe {
    background: rgba(255,255,255,0.08) !important;
    border: 1px solid rgba(255,255,255,0.18) !important;
    border-radius: 16px !important;
    padding: 22px 26px !important;
}
.footer-contact-safe h3,
.footer-contact-safe p {
    color: #FFFFFF !important;
}
.footer-contact-safe h3 {
    margin-top: 0 !important;
}
.footer-contact-safe p {
    margin: 8px 0 !important;
}
.basic-info-item {
    color: #101828 !important;
}
.basic-info-item b {
    color: #002B5B !important;
}
@media(max-width:900px){
    .clean-footer-grid {
        grid-template-columns: 1fr;
        gap: 24px;
    }
    .footer-brand-safe {
        display: block;
    }
}


/* v25 uploaded Excel data tables */
.excel-note {
    background: #FFF7ED;
    border: 1px solid #FDBA74;
    color: #7C2D12 !important;
    border-radius: 12px;
    padding: 12px 14px;
    margin: 12px 0 16px 0;
}
.excel-note * { color: #7C2D12 !important; }
.program-section-title {
    margin-top: 16px;
    margin-bottom: 8px;
    color: #002B5B !important;
    font-weight: 900;
}


/* v26 requested homepage/header/footer updates */
.clean-header {
    background:#FFFFFF !important;
    border-bottom:1px solid #E7EEF8 !important;
    padding:18px 26px !important;
}
.site-title-wrap {
    height:64px;
    display:flex;
    align-items:center;
}
.site-title {
    color:#002B5B !important;
    font-size:24px;
    font-weight:900;
    line-height:1.12;
    letter-spacing:-.02em;
}
.nav-button-wrap {
    height:64px;
    display:flex;
    align-items:center;
}
.nav-button-wrap .stButton {width:100%;}
.nav-button-wrap .stButton > button {
    height:42px !important;
    background:#FFFFFF !important;
    color:#061A40 !important;
    border:0px solid transparent !important;
    border-radius:0 !important;
    font-weight:850 !important;
    box-shadow:none !important;
}
.nav-button-wrap .stButton > button * {color:#061A40 !important;}
.nav-button-wrap .stButton > button:hover {
    color:#005BDB !important;
    border-bottom:3px solid #005BDB !important;
}
.hero-photo {
    min-height:560px;
    background-size:cover;
    background-position:center;
    display:flex;
    align-items:center;
    margin:0;
}
.hero-content {
    max-width:720px;
    padding-left:56px;
    padding-top:10px;
}
.hero-content h1 {
    color:#FFFFFF !important;
    font-size:56px;
    line-height:1.13;
    font-weight:900;
    margin:0 0 28px 0;
}
.hero-content p {
    color:#FFFFFF !important;
    font-size:18px;
    line-height:1.55;
    margin:0 0 18px 0;
}
.lock-line {
    font-size:15px !important;
}
.hero-tab-buttons {
    margin-top:-150px;
    margin-left:56px;
    margin-bottom:88px;
    position:relative;
    z-index:5;
    max-width:560px;
}
.hero-tab-buttons .stButton > button {
    height:56px !important;
    background:#FFFFFF !important;
    color:#002B5B !important;
    border:1px solid #FFFFFF !important;
    border-radius:8px !important;
    font-weight:900 !important;
    box-shadow:0 8px 22px rgba(0,0,0,.14) !important;
}
.hero-tab-buttons .stButton > button * {color:#002B5B !important;}
.footer-lite {
    background:#FFFFFF !important;
    padding:30px 56px 22px 56px !important;
    border-top:1px solid #E7EEF8;
}
.footer-lite-grid {
    display:grid;
    grid-template-columns:1.1fr 2fr;
    gap:40px;
    align-items:center;
}
.footer-lite h3 {
    color:#002B5B !important;
    margin:0 0 8px 0 !important;
    font-size:22px !important;
}
.footer-lite p {
    color:#667085 !important;
    margin:0 !important;
}
.footer-contact-row {
    display:flex;
    justify-content:space-between;
    gap:22px;
    flex-wrap:wrap;
}
.footer-contact-row span {
    color:#002B5B !important;
    font-weight:850 !important;
}
.footer-lite hr {
    border:0;
    border-top:1px solid #E5EAF2;
    margin:24px 0 18px 0;
}
.copyright {
    text-align:center;
    font-size:13px;
}
@media(max-width:1000px){
    .footer-lite-grid {grid-template-columns:1fr;}
    .hero-content h1 {font-size:38px;}
    .hero-tab-buttons {margin-top:-120px;margin-left:28px;}
    .hero-content {padding-left:28px;}
}


/* v27 final homepage layout fixes */
.clean-header-v27 {
    background:#FFFFFF !important;
    border-bottom:1px solid #E7EEF8 !important;
    padding:14px 26px 12px 26px !important;
    margin-bottom:0 !important;
}
.site-title-wrap-v27 {
    height:62px;
    display:flex;
    align-items:center;
}
.site-title-v27 {
    color:#002B5B !important;
    font-size:22px;
    font-weight:900;
    line-height:1.08;
    letter-spacing:-.02em;
}
.nav-button-wrap-v27 {
    height:62px;
    display:flex;
    align-items:center;
}
.nav-button-wrap-v27 .stButton {width:100%;}
.nav-button-wrap-v27 .stButton > button {
    height:40px !important;
    background:#FFFFFF !important;
    color:#061A40 !important;
    border:0 !important;
    border-radius:0 !important;
    font-weight:850 !important;
    box-shadow:none !important;
    padding-left:4px !important;
    padding-right:4px !important;
}
.nav-button-wrap-v27 .stButton > button * {color:#061A40 !important;}
.nav-button-wrap-v27 .stButton > button:hover {
    color:#005BDB !important;
    border-bottom:3px solid #005BDB !important;
}
.hero-photo-v27 {
    min-height:560px;
    background-color:#002B5B;
    background-size:cover;
    background-position:center;
    display:flex;
    align-items:center;
    margin:0;
    border-radius:0;
}
.hero-content-v27 {
    max-width:700px;
    padding-left:56px;
    padding-top:0;
}
.hero-content-v27 h1 {
    color:#FFFFFF !important;
    font-size:54px !important;
    line-height:1.12 !important;
    font-weight:900 !important;
    margin:0 0 28px 0 !important;
    text-shadow:none !important;
    opacity:1 !important;
}
.hero-content-v27 p {
    color:#FFFFFF !important;
    font-size:18px !important;
    line-height:1.55 !important;
    margin:0 0 18px 0 !important;
    opacity:1 !important;
}
.lock-line-v27 {
    font-size:15px !important;
}
.hero-tab-buttons-v27 {
    margin-top:-122px;
    margin-left:56px;
    margin-bottom:60px;
    position:relative;
    z-index:50;
    max-width:580px;
}
.hero-tab-buttons-v27 .stButton > button {
    height:56px !important;
    background:#FFFFFF !important;
    color:#002B5B !important;
    border:1px solid #FFFFFF !important;
    border-radius:8px !important;
    font-weight:900 !important;
    box-shadow:0 8px 22px rgba(0,0,0,.16) !important;
}
.hero-tab-buttons-v27 .stButton > button * {color:#002B5B !important;}
.featured-section-v27 {
    padding-top:10px !important;
}
.footer-lite-v27 {
    background:#FFFFFF !important;
    padding:30px 56px 22px 56px !important;
    border-top:1px solid #E7EEF8;
}
.footer-lite-grid-v27 {
    display:grid;
    grid-template-columns:1fr 2.3fr;
    gap:38px;
    align-items:center;
}
.footer-lite-v27 h3 {
    color:#002B5B !important;
    margin:0 0 8px 0 !important;
    font-size:22px !important;
    line-height:1.15;
}
.footer-lite-v27 p {
    color:#667085 !important;
    margin:0 !important;
}
.footer-contact-row-v27 {
    display:flex;
    justify-content:space-between;
    gap:20px;
    flex-wrap:wrap;
}
.footer-contact-row-v27 span {
    color:#002B5B !important;
    font-weight:850 !important;
}
.footer-lite-v27 hr {
    border:0;
    border-top:1px solid #E5EAF2;
    margin:24px 0 18px 0;
}
.copyright-v27 {
    text-align:center;
    font-size:13px;
}
@media(max-width:1000px){
    .footer-lite-grid-v27 {grid-template-columns:1fr;}
    .site-title-v27 {font-size:18px;}
    .hero-content-v27 h1 {font-size:38px !important;}
    .hero-tab-buttons-v27 {margin-top:-108px;margin-left:28px;}
    .hero-content-v27 {padding-left:28px;}
}


/* v28 agency role structure */
.role-note {
    background:#EEF5FF;
    border:1px solid #CFE0FF;
    color:#002B5B!important;
    border-radius:12px;
    padding:14px 16px;
    font-weight:750;
}


/* v31 layout, hero, info cards, eligibility result fixes */
.clean-header-v31 {
    background:#FFFFFF !important;
    border-bottom:1px solid #E7EEF8 !important;
    padding:14px 26px 12px 26px !important;
    margin-bottom:0 !important;
}
.site-title-wrap-v31 {
    height:62px;
    display:flex;
    align-items:center;
}
.site-title-v31 {
    color:#061A40 !important;
    font-size:22px;
    font-weight:950;
    line-height:1.08;
    letter-spacing:-.02em;
}
.nav-button-wrap-v31 {
    height:62px;
    display:flex;
    align-items:center;
}
.nav-button-wrap-v31 .stButton {width:100%;}
.nav-button-wrap-v31 .stButton > button {
    height:40px !important;
    background:#FFFFFF !important;
    color:#061A40 !important;
    border:0 !important;
    border-radius:0 !important;
    font-weight:850 !important;
    box-shadow:none !important;
    padding-left:2px !important;
    padding-right:2px !important;
}
.nav-button-wrap-v31 .stButton > button * {color:#061A40 !important;}
.nav-button-wrap-v31 .stButton > button:hover {
    color:#005BDB !important;
    border-bottom:3px solid #005BDB !important;
}
.hero-photo-v31 {
    min-height:590px;
    background-color:#002B5B;
    background-size:cover;
    background-position:center;
    display:flex;
    align-items:center;
    margin:0;
}
.hero-content-v31 {
    max-width:720px;
    padding-left:56px;
    padding-bottom:40px;
}
.hero-content-v31 h1 {
    color:#FFFFFF !important;
    font-size:56px !important;
    line-height:1.12 !important;
    font-weight:950 !important;
    margin:0 0 26px 0 !important;
    opacity:1 !important;
    text-shadow:0 2px 12px rgba(0,0,0,.28);
}
.hero-content-v31 p {
    color:#FFFFFF !important;
    font-size:18px !important;
    line-height:1.55 !important;
    margin:0 0 16px 0 !important;
    opacity:1 !important;
    text-shadow:0 1px 8px rgba(0,0,0,.25);
}
.lock-line-v31 {
    font-size:15px !important;
}
.hero-tab-buttons-v31 {
    margin-top:-155px;
    margin-left:56px;
    margin-bottom:85px;
    position:relative;
    z-index:50;
    max-width:590px;
}
.hero-tab-buttons-v31 .stButton > button {
    height:56px !important;
    background:#FFFFFF !important;
    color:#002B5B !important;
    border:1px solid #FFFFFF !important;
    border-radius:8px !important;
    font-weight:900 !important;
    box-shadow:0 8px 22px rgba(0,0,0,.16) !important;
}
.hero-tab-buttons-v31 .stButton > button * {color:#002B5B !important;}
.featured-section-v31 {padding-top:8px !important;}
.page-section-v31 {
    padding:44px 0 10px 0;
}
.uni-info-card-v31 {
    background:#FFFFFF;
    border:1px solid #DCE6F4;
    border-radius:18px;
    overflow:hidden;
    margin:24px 0;
    box-shadow:0 10px 26px rgba(16,24,40,.06);
}
.uni-photo-wide-v31 {
    width:100%;
    height:360px;
    object-fit:cover;
    object-position:center;
    display:block;
    border:0;
    border-radius:0;
}
.uni-info-body-v31 {
    padding:28px 30px 30px 30px;
}
.uni-info-body-v31 h2 {
    margin-top:0;
    color:#101828!important;
}
.uni-overview-v31 {
    color:#344054!important;
    font-size:16px;
    margin-bottom:22px;
}
.basic-info-grid-v31 {
    display:grid;
    grid-template-columns:repeat(2, minmax(0, 1fr));
    gap:14px;
    align-items:stretch;
}
.basic-info-item-v31 {
    min-height:86px;
    background:#F6F8FC;
    border:1px solid #E3EAF5;
    border-radius:12px;
    padding:14px 16px;
    color:#101828!important;
    display:flex;
    flex-direction:column;
    justify-content:flex-start;
}
.basic-info-item-v31 b {
    color:#002B5B!important;
    margin-bottom:8px;
}
.basic-info-item-v31 span {
    color:#101828!important;
    line-height:1.35;
}
@media(max-width:1000px){
    .basic-info-grid-v31 {grid-template-columns:1fr;}
    .hero-content-v31 h1 {font-size:38px!important;}
    .hero-tab-buttons-v31 {margin-left:28px;margin-top:-125px;}
    .hero-content-v31 {padding-left:28px;}
}


/* v32 final corrections */
.header-v32{background:#fff!important;border-bottom:1px solid #E7EEF8!important;padding:12px 26px!important;margin:0!important;}
.brand-v32{height:60px;display:flex;align-items:center;color:#001B44!important;font-size:24px!important;font-weight:950!important;line-height:1.08!important;letter-spacing:-.03em!important;}
.nav-v32{height:60px;display:flex;align-items:center;}
.nav-v32 .stButton{width:100%;}
.nav-v32 .stButton>button{height:40px!important;background:#fff!important;color:#061A40!important;border:0!important;border-radius:0!important;font-weight:850!important;box-shadow:none!important;padding-left:2px!important;padding-right:2px!important;}
.nav-v32 .stButton>button *{color:#061A40!important;}
.nav-v32 .stButton>button:hover{color:#005BDB!important;border-bottom:3px solid #005BDB!important;}
.hero-v32{min-height:600px;background-color:#002B5B;background-size:cover!important;background-position:center!important;display:flex!important;align-items:center!important;margin:0!important;border-radius:0!important;}
.hero-text-v32{max-width:760px!important;padding-left:56px!important;padding-bottom:64px!important;}
.hero-text-v32 h1{color:#fff!important;font-size:58px!important;line-height:1.12!important;font-weight:950!important;margin:0 0 26px 0!important;text-shadow:0 2px 14px rgba(0,0,0,.34)!important;opacity:1!important;}
.hero-text-v32 p{color:#fff!important;font-size:18px!important;line-height:1.55!important;margin:0 0 16px 0!important;text-shadow:0 1px 8px rgba(0,0,0,.32)!important;opacity:1!important;}
.lock-v32{font-size:15px!important;}
.hero-buttons-v32{margin-top:-170px!important;margin-left:56px!important;margin-bottom:95px!important;position:relative!important;z-index:80!important;max-width:600px!important;}
.hero-buttons-v32 .stButton>button{height:56px!important;background:#fff!important;color:#002B5B!important;border:1px solid #fff!important;border-radius:8px!important;font-weight:900!important;box-shadow:0 8px 22px rgba(0,0,0,.18)!important;}
.hero-buttons-v32 .stButton>button *{color:#002B5B!important;}
.featured-v32{padding-top:8px!important;}
.universities-wrap-v32{padding:36px 0 10px 0!important;}
.uni-card-v32{background:#fff;border:1px solid #DCE6F4;border-radius:18px;overflow:hidden;margin:24px 0;box-shadow:0 10px 26px rgba(16,24,40,.06);}
.uni-wide-v32{width:100%!important;height:390px!important;object-fit:cover!important;object-position:center!important;display:block!important;border:0!important;border-radius:0!important;margin:0!important;}
.uni-body-v32{padding:28px 30px 30px 30px!important;}
.uni-body-v32 h2{margin:0 0 12px 0!important;color:#101828!important;}
.uni-overview-v32{color:#344054!important;font-size:16px!important;margin-bottom:22px!important;}
.info-grid-v32{display:grid!important;grid-template-columns:repeat(2,minmax(0,1fr))!important;gap:14px!important;align-items:stretch!important;}
.info-box-v32{min-height:92px!important;background:#F6F8FC!important;border:1px solid #E3EAF5!important;border-radius:12px!important;padding:14px 16px!important;color:#101828!important;display:flex!important;flex-direction:column!important;justify-content:flex-start!important;}
.info-box-v32 b{color:#002B5B!important;margin-bottom:8px!important;}
.info-box-v32 span{color:#101828!important;line-height:1.35!important;}
.eligibility-table-title-v32{font-size:18px;font-weight:900;color:#002B5B;margin:16px 0 10px 0;}
@media(max-width:1000px){.info-grid-v32{grid-template-columns:1fr!important}.hero-text-v32{padding-left:28px!important}.hero-text-v32 h1{font-size:40px!important}.hero-buttons-v32{margin-left:28px!important;margin-top:-145px!important}.brand-v32{font-size:18px!important}}


/* v33 final override: hero title white and university image quality/layout */
.hero-v32 .hero-text-v32 h1,
.hero-v32 .hero-text-v32 h1 *,
.hero-text-v32 h1,
.hero-text-v32 h1 * {
    color: #FFFFFF !important;
    -webkit-text-fill-color: #FFFFFF !important;
    opacity: 1 !important;
    text-shadow: 0 3px 16px rgba(0,0,0,.45) !important;
}

.hero-v32 .hero-text-v32 p,
.hero-v32 .hero-text-v32 p * {
    color: #FFFFFF !important;
    -webkit-text-fill-color: #FFFFFF !important;
}

.uni-card-v32 {
    overflow: hidden !important;
}

.uni-wide-v32 {
    width: 100% !important;
    height: 440px !important;
    object-fit: cover !important;
    object-position: center center !important;
    display: block !important;
    border: 0 !important;
    border-radius: 0 !important;
    margin: 0 !important;
    image-rendering: auto !important;
}

.card .uni-photo {
    object-fit: cover !important;
    object-position: center center !important;
}


/* v34 signup alignment and approval request card */
.approval-card-v34 {
    background:#FFFFFF;
    border:1px solid #DCE6F4;
    border-radius:14px;
    padding:18px 20px;
    margin:12px 0 8px 0;
    box-shadow:0 8px 18px rgba(16,24,40,.05);
}
.approval-card-v34 h4 {
    margin:0 0 8px 0!important;
    color:#002B5B!important;
}
.approval-card-v34 p {
    margin:4px 0!important;
    color:#101828!important;
}


/* v36 eligibility and tuition result card redesign */
.elig-form-panel-v36 {
    background: #FFFFFF;
    border: 1px solid #DCE6F4;
    border-radius: 16px;
    padding: 20px 20px 16px 20px;
    box-shadow: 0 8px 20px rgba(16,24,40,.05);
}
.elig-empty-v36, .elig-summary-pass-v36, .elig-summary-fail-v36 {
    border-radius: 18px;
    padding: 24px 26px;
    margin-bottom: 18px;
    border: 1px solid #DCE6F4;
    background: #FFFFFF;
    box-shadow: 0 10px 24px rgba(16,24,40,.06);
}
.elig-summary-pass-v36 {
    background: linear-gradient(135deg, #EAF8EF, #FFFFFF);
    border-color: #BDECCB;
}
.elig-summary-fail-v36 {
    background: linear-gradient(135deg, #FFF1F0, #FFFFFF);
    border-color: #FFD1CC;
}
.elig-empty-v36 h3, .elig-summary-pass-v36 h3, .elig-summary-fail-v36 h3 {
    margin-top: 0!important;
    color: #002B5B!important;
}
.elig-mini-list-v36 {display:flex; flex-wrap:wrap; gap:10px; margin-top:16px;}
.elig-mini-list-v36 span {background:#EEF5FF; color:#002B5B!important; border-radius:999px; padding:8px 12px; font-weight:800;}
.elig-card-v36 {
    background:#FFFFFF;
    border:1px solid #DCE6F4;
    border-radius:18px;
    padding:22px 24px;
    margin-bottom:18px;
    box-shadow:0 10px 26px rgba(16,24,40,.07);
}
.elig-card-top-v36 {display:flex; justify-content:space-between; align-items:flex-start; gap:18px; border-bottom:1px solid #E7EEF8; padding-bottom:15px; margin-bottom:16px;}
.elig-university-v36 {font-size:23px; font-weight:950; color:#002B5B!important;}
.elig-major-v36 {font-size:17px; font-weight:800; color:#101828!important; margin-top:6px;}
.elig-pass-v36 {background:#DFF7E8; color:#067647!important; border:1px solid #A7E5BB; padding:9px 16px; border-radius:999px; font-weight:950;}
.elig-detail-grid-v36 {display:grid; grid-template-columns:repeat(2,minmax(0,1fr)); gap:12px;}
.elig-detail-grid-v36 div, .fee-grid-v36 div {background:#F6F8FC; border:1px solid #E3EAF5; border-radius:12px; padding:12px 14px; min-height:72px;}
.elig-detail-grid-v36 b, .fee-grid-v36 b {display:block; color:#002B5B!important; margin-bottom:7px;}
.elig-detail-grid-v36 span, .fee-grid-v36 span {display:block; color:#101828!important; line-height:1.35;}
.elig-wide-v36 {grid-column:1 / -1;}
.fee-result-card-v36 {background:#FFFFFF; border:1px solid #DCE6F4; border-radius:20px; padding:24px 26px; box-shadow:0 14px 32px rgba(16,24,40,.08);}
.fee-result-head-v36 {display:flex; justify-content:space-between; align-items:flex-start; border-bottom:1px solid #E7EEF8; padding-bottom:16px; margin-bottom:18px;}
.fee-result-head-v36 h3 {margin:0 0 6px 0!important; color:#002B5B!important;}
.fee-result-head-v36 p {margin:0!important; color:#344054!important; font-weight:750;}
.fee-badge-v36 {background:#EEF5FF; color:#005BDB!important; padding:9px 14px; border-radius:999px; font-weight:950;}
.fee-grid-v36 {display:grid; grid-template-columns:repeat(2,minmax(0,1fr)); gap:12px;}
@media(max-width:900px){.elig-detail-grid-v36,.fee-grid-v36{grid-template-columns:1fr;}}


/* v37 dynamic major + equal cards + image quality */
.card {
    height: 520px !important;
    min-height: 520px !important;
    max-height: 520px !important;
    display: flex !important;
    flex-direction: column !important;
    justify-content: flex-start !important;
    overflow: hidden !important;
}
.card h3 {
    min-height: 78px !important;
    max-height: 78px !important;
    overflow: hidden !important;
    margin-bottom: 14px !important;
}
.card p {
    margin: 8px 0 !important;
}
.card .uni-photo,
.uni-photo {
    width: 100% !important;
    height: 175px !important;
    min-height: 175px !important;
    max-height: 175px !important;
    object-fit: cover !important;
    object-position: center center !important;
    border-radius: 12px !important;
    image-rendering: auto !important;
}
div[data-testid="stButton"] button[kind="secondary"] {
    color: #101828 !important;
}
.page-section-v37 {
    padding: 24px 0 10px 0;
}
.form-panel-v37 {
    padding: 22px 22px !important;
}
.info-card-v37 {
    background: #FFFFFF;
    border: 1px solid #DCE6F4;
    border-radius: 18px;
    padding: 34px 38px;
    min-height: 230px;
    box-shadow: 0 10px 24px rgba(16,24,40,.06);
}
.info-card-v37 h2 {
    color:#101828!important;
    margin-top:0!important;
}
.info-card-v37 p {
    color:#344054!important;
    font-size:17px;
    line-height:1.55;
}
.fee-card-v37 {
    background:#FFFFFF;
    border:1px solid #CFE0FF;
    border-radius:20px;
    overflow:hidden;
    box-shadow:0 16px 34px rgba(16,24,40,.09);
}
.fee-card-head-v37 {
    background:linear-gradient(135deg,#002B5B,#1E3A8A);
    padding:28px 32px;
    display:flex;
    justify-content:space-between;
    align-items:flex-start;
    gap:20px;
}
.fee-card-head-v37 h2,
.fee-card-head-v37 p,
.eyebrow-v37 {
    color:#FFFFFF!important;
}
.fee-card-head-v37 h2 {
    margin:4px 0 8px 0!important;
    font-size:30px!important;
}
.eyebrow-v37 {
    font-size:13px!important;
    text-transform:uppercase;
    letter-spacing:.08em;
    opacity:.85;
    margin:0!important;
}
.fee-badge-v37 {
    background:#FFFFFF;
    color:#002B5B!important;
    border-radius:999px;
    padding:8px 14px;
    font-weight:900;
    white-space:nowrap;
}
.fee-grid-v37 {
    display:grid;
    grid-template-columns:repeat(2,minmax(0,1fr));
    gap:14px;
    padding:24px 28px;
}
.fee-grid-v37 div {
    background:#F7F9FC;
    border:1px solid #E3EAF5;
    border-radius:14px;
    padding:16px 18px;
    min-height:82px;
}
.fee-grid-v37 span {
    display:block;
    color:#667085!important;
    font-size:13px;
    margin-bottom:8px;
}
.fee-grid-v37 b {
    color:#101828!important;
    font-size:17px;
}
.note-v37 {
    color:#667085!important;
    border-top:1px solid #E5EAF2;
    padding:16px 28px 22px 28px;
    margin:0!important;
}
@media(max-width:1000px){
    .card {height:auto!important; max-height:none!important;}
    .fee-grid-v37 {grid-template-columns:1fr;}
}


/* v40 tuition dynamic dropdown and cleaner fee summary */
.elig-form-panel-v40 {
    background:#FFFFFF;
    border:1px solid #DCE6F4;
    border-radius:16px;
    padding:24px 22px;
    box-shadow:0 10px 24px rgba(16,24,40,.06);
}
.form-title-v40 {
    color:#101828!important;
    margin:0 0 18px 0!important;
    font-size:22px!important;
}
.dynamic-note-v40 {
    margin-top:18px;
    background:#EEF5FF;
    border:1px solid #CFE0FF;
    border-radius:12px;
    color:#002B5B!important;
    font-weight:800;
    padding:14px 16px;
    line-height:1.45;
}
.fee-result-card-v40 {
    background:#FFFFFF;
    border:1px solid #CFE0FF;
    border-radius:20px;
    overflow:hidden;
    box-shadow:0 16px 34px rgba(16,24,40,.09);
}
.fee-result-head-v40 {
    background:linear-gradient(135deg,#002B5B,#1E3A8A);
    padding:28px 32px;
    display:flex;
    justify-content:space-between;
    align-items:flex-start;
    gap:20px;
}
.fee-result-head-v40 h3 {
    color:#FFFFFF!important;
    margin:6px 0 10px 0!important;
    font-size:31px!important;
    line-height:1.15;
}
.fee-result-head-v40 p,
.fee-eyebrow-v40 {
    color:#FFFFFF!important;
    margin:0!important;
}
.fee-eyebrow-v40 {
    text-transform:uppercase;
    letter-spacing:.08em;
    font-size:13px!important;
    opacity:.9;
}
.fee-badge-v40 {
    background:#FFFFFF;
    color:#002B5B!important;
    border-radius:999px;
    padding:9px 15px;
    font-weight:900;
    white-space:nowrap;
}
.fee-grid-v40 {
    display:grid;
    grid-template-columns:repeat(2,minmax(0,1fr));
    gap:14px;
    padding:24px 28px;
}
.fee-grid-v40 div {
    background:#F7F9FC;
    border:1px solid #E3EAF5;
    border-radius:14px;
    padding:16px 18px;
    min-height:88px;
}
.fee-grid-v40 b {
    display:block;
    color:#002B5B!important;
    font-size:15px;
    margin-bottom:9px;
}
.fee-grid-v40 span {
    display:block;
    color:#101828!important;
    font-size:16px;
    line-height:1.35;
}
.fee-note-v40 {
    border-top:1px solid #E5EAF2;
    color:#667085!important;
    padding:16px 28px 22px 28px;
    line-height:1.45;
}
/* keep university cards equal height */
.card {height:520px!important; min-height:520px!important; max-height:520px!important; display:flex!important; flex-direction:column!important; overflow:hidden!important;}
.card h3 {min-height:78px!important; max-height:78px!important; overflow:hidden!important;}
.card .uni-photo, .uni-photo {height:175px!important; min-height:175px!important; max-height:175px!important; object-fit:cover!important; object-position:center!important; border-radius:12px!important;}
@media(max-width:1000px){.fee-grid-v40{grid-template-columns:1fr}.card{height:auto!important;max-height:none!important}}


/* v41 scholarship and university program cards */
.elig-form-panel-v41 {
    background:#FFFFFF;
    border:1px solid #DCE6F4;
    border-radius:14px;
    padding:20px 22px;
    box-shadow:0 8px 18px rgba(16,24,40,.05);
}
.elig-card-v41 {
    background:#FFFFFF;
    border:1px solid #DCE6F4;
    border-radius:20px;
    margin:18px 0;
    overflow:hidden;
    box-shadow:0 16px 34px rgba(16,24,40,.08);
}
.elig-card-top-v41 {
    background:linear-gradient(135deg,#002B5B,#1E3A8A);
    padding:24px 28px;
    display:flex;
    align-items:flex-start;
    justify-content:space-between;
    gap:20px;
}
.elig-university-v41 {color:#FFFFFF!important;font-size:26px;font-weight:950;line-height:1.15;}
.elig-major-v41 {color:#DCEAFF!important;font-size:16px;margin-top:7px;}
.elig-pass-v41 {background:#D1FADF;color:#027A48!important;border-radius:999px;padding:9px 16px;font-weight:950;white-space:nowrap;}
.elig-detail-grid-v41 {display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:14px;padding:24px 28px;}
.elig-detail-grid-v41 div {background:#F7F9FC;border:1px solid #E3EAF5;border-radius:14px;padding:15px 17px;min-height:78px;}
.elig-detail-grid-v41 b {display:block;color:#002B5B!important;margin-bottom:8px;}
.elig-detail-grid-v41 span {display:block;color:#101828!important;line-height:1.35;}
.pass-text-v41 {color:#027A48!important;font-weight:900;}
.final-tuition-v41 {color:#005BDB!important;font-weight:950;font-size:18px;}
.available-title-v41 {color:#002B5B!important;margin:28px 0 16px 0!important;}
.program-tabs-v41 {display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:16px;margin-top:12px;}
.program-tab-card-v41 {background:#F7F9FC;border:1px solid #DCE6F4;border-radius:16px;padding:18px 20px;min-height:190px;}
.program-tab-card-v41 h4 {color:#002B5B!important;margin:0 0 12px 0!important;font-size:18px!important;}
.program-tab-card-v41 ul {margin:0;padding-left:18px;}
.program-tab-card-v41 li {color:#101828!important;margin:6px 0;line-height:1.35;}
@media(max-width:1000px){.elig-detail-grid-v41,.program-tabs-v41{grid-template-columns:1fr;}}


/* v42 clean text + fee header white */
.fee-result-head-v40 h3,
.fee-result-head-v40 h3 *,
.fee-result-head-v40 p,
.fee-result-head-v40 p *,
.fee-eyebrow-v40 {
    color:#FFFFFF !important;
    -webkit-text-fill-color:#FFFFFF !important;
    opacity:1 !important;
}
.fee-result-head-v40 h3 {
    font-size:32px !important;
    font-weight:950 !important;
    margin:4px 0 12px 0 !important;
    text-shadow:0 2px 10px rgba(0,0,0,.22) !important;
}
.fee-note-v40, .dynamic-note-v40 {display:none !important;}
.elig-form-panel-v40 {padding-bottom:24px !important;}
.fee-result-card-v40 {overflow:hidden !important;}


/* v43 hide blank/not-provided info and clean program boxes */
.programs-section-v43 {
    display:grid;
    grid-template-columns:repeat(3, minmax(0, 1fr));
    gap:14px;
    margin-top:18px;
}
.program-mini-v43 {
    background:#F7F9FC;
    border:1px solid #E3EAF5;
    border-radius:12px;
    padding:14px 16px;
    min-height:78px;
}
.program-mini-v43 b {
    display:block;
    color:#002B5B!important;
    margin-bottom:8px;
}
.program-mini-v43 span {
    color:#101828!important;
    line-height:1.35;
}
.info-mini-v43 {
    background:#F7F9FC;
    border:1px solid #E3EAF5;
    border-radius:12px;
    padding:14px 16px;
}
.info-mini-v43 b {
    display:block;
    color:#002B5B!important;
    margin-bottom:8px;
}
.info-mini-v43 span {
    color:#101828!important;
}
@media(max-width:1000px){
    .programs-section-v43 {grid-template-columns:1fr;}
}


/* v44 final cleanup: remove not-provided scholarship fields */
.fee-grid-v37 div:has(b:empty),
.fee-grid-v37 div:has(b:-webkit-any()) {
    /* kept for browser compatibility; main hiding is done in Python HTML generation */
}


/* v47 header alignment and scholarship percent consistency */
.clean-header-v31,
.header-box,
.header-v32,
.header-v40 {
    display: flex !important;
    align-items: center !important;
    gap: 18px !important;
    padding-top: 18px !important;
    padding-bottom: 18px !important;
    min-height: 94px !important;
}

.site-title-wrap-v31,
.site-title-wrap-v32,
.site-title-wrap-v40 {
    display: flex !important;
    align-items: center !important;
    height: 62px !important;
    margin: 0 !important;
}

.site-title-v31,
.site-title-v32,
.site-title-v40,
.site-name,
.logo-text {
    color: #002B5B !important;
    font-weight: 950 !important;
    line-height: 1.08 !important;
    letter-spacing: -0.03em !important;
    display: flex !important;
    align-items: center !important;
}

.nav-button-wrap-v31,
.nav-button-wrap-v32,
.nav-button-wrap-v40 {
    display: flex !important;
    align-items: center !important;
    justify-content: center !important;
    height: 62px !important;
    margin: 0 !important;
}

.nav-button-wrap-v31 .stButton,
.nav-button-wrap-v32 .stButton,
.nav-button-wrap-v40 .stButton {
    display: flex !important;
    align-items: center !important;
}

.nav-button-wrap-v31 .stButton > button,
.nav-button-wrap-v32 .stButton > button,
.nav-button-wrap-v40 .stButton > button,
.header-box .stButton > button {
    height: 46px !important;
    display: flex !important;
    align-items: center !important;
    justify-content: center !important;
    margin-top: 0 !important;
    margin-bottom: 0 !important;
    border-radius: 10px !important;
    font-weight: 800 !important;
}

div[data-testid="stHorizontalBlock"] {
    align-items: center !important;
}

div[data-testid="stHorizontalBlock"] > div {
    display: flex !important;
    flex-direction: column !important;
    justify-content: center !important;
}

.fee-grid-v40 span,
.fee-grid-v37 span,
.fee-grid-v40 b,
.fee-grid-v37 b {
    word-break: keep-all !important;
}


.header-align-v47 {
    border-bottom: 1px solid #E7EEF8;
    padding: 18px 0 18px 0;
    margin-bottom: 26px;
}
.site-title-wrap-v47 {
    height: 58px;
    display: flex;
    align-items: center;
}
.site-title-v47 {
    color: #002B5B !important;
    font-size: 22px;
    font-weight: 950;
    line-height: 1.05;
    letter-spacing: -0.03em;
}
.nav-button-wrap-v47 {
    height: 58px;
    display:flex;
    align-items:center;
    justify-content:center;
}
.nav-button-wrap-v47 .stButton {
    width:100%;
}
.nav-button-wrap-v47 .stButton > button {
    height:44px !important;
    background:#FFFFFF !important;
    color:#101828 !important;
    border:1px solid #CDD5DF !important;
    border-radius:10px !important;
    font-weight:800 !important;
    box-shadow:none !important;
}
.nav-button-wrap-v47 .stButton > button:hover {
    border-color:#2F5BFF !important;
    color:#002B5B !important;
    background:#F7FAFF !important;
}


/* v48 admin editable management */
[data-testid="stDataFrame"], [data-testid="stDataEditor"] {border-radius: 14px !important; overflow: hidden !important;}


/* v49 admin add/edit management pages */
div[data-testid="stFileUploader"] label {
    color:#101828!important;
    font-weight:800!important;
}
.stTabs [data-baseweb="tab-list"] {
    gap: 10px;
}
.stTabs [data-baseweb="tab"] {
    background: #F6F8FC;
    border: 1px solid #DCE6F4;
    border-radius: 10px 10px 0 0;
    padding: 10px 18px;
}


/* v50 hide empty/nan information fields */
.basic-info-grid-v31 {
    align-items: stretch;
}
.basic-info-grid-v31:empty {
    display: none !important;
}
.basic-info-item-v31 span:empty {
    display: none !important;
}


/* v51: Home university cards row alignment */
.featured-section-v31 div[data-testid="stHorizontalBlock"] {
    align-items: stretch !important;
}
.featured-section-v31 div[data-testid="column"] {
    display: flex !important;
    flex-direction: column !important;
}
.featured-section-v31 .card {
    height: 520px !important;
    min-height: 520px !important;
    max-height: 520px !important;
}
.card-row-gap-v51 {
    height: 28px;
}


/* v52: safe image placeholder */
.uni-photo-placeholder-v52 {
    background: linear-gradient(135deg, #F2F6FC, #E8EEF8);
    color: #64748B !important;
    display: flex !important;
    align-items: center !important;
    justify-content: center !important;
    font-weight: 800 !important;
    border-radius: 12px !important;
    border: 1px solid #DCE6F4 !important;
}


/* v53: fixed Featured Universities rows and equal card alignment */
.featured-v32 div[data-testid="stHorizontalBlock"] {
    align-items: stretch !important;
}
.featured-v32 div[data-testid="stHorizontalBlock"] > div,
.featured-v32 div[data-testid="column"] {
    display: flex !important;
    flex-direction: column !important;
    justify-content: flex-start !important;
    align-items: stretch !important;
}
.featured-v32 .uni-card-v53,
.featured-v32 .card {
    height: 500px !important;
    min-height: 500px !important;
    max-height: 500px !important;
    display: flex !important;
    flex-direction: column !important;
    justify-content: flex-start !important;
    overflow: hidden !important;
}
.featured-v32 .uni-photo {
    width: 100% !important;
    height: 170px !important;
    object-fit: cover !important;
    object-position: center center !important;
    border-radius: 12px !important;
    margin-bottom: 24px !important;
}
.featured-v32 .card h3 {
    min-height: 76px !important;
    margin-bottom: 14px !important;
}
.featured-v32 .stButton > button {
    height: 46px !important;
    margin-top: 0 !important;
}
.home-row-gap-v53 {
    height: 34px;
}


/* Button color fix for Streamlit Cloud v60 */
.stButton > button,
div[data-testid="stButton"] > button,
button[kind="secondary"],
button[kind="primary"] {
    background-color: #FFFFFF !important;
    color: #111827 !important;
    -webkit-text-fill-color: #111827 !important;
    border: 1px solid #D1D5DB !important;
    border-radius: 10px !important;
    box-shadow: none !important;
    font-weight: 500 !important;
}

.stButton > button:hover,
div[data-testid="stButton"] > button:hover,
button[kind="secondary"]:hover,
button[kind="primary"]:hover {
    background-color: #F8FAFC !important;
    color: #0F172A !important;
    -webkit-text-fill-color: #0F172A !important;
    border: 1px solid #94A3B8 !important;
}


/* v61 advanced university and application UI */
.filter-panel-v61 {background:#F6F8FC;border:1px solid #DCE6F4;border-radius:16px;padding:18px 18px 6px 18px;margin:16px 0 24px 0;}
.uni-title-row-v61 {display:flex;justify-content:space-between;align-items:flex-start;gap:18px;}
.status-area-v61 {display:flex;flex-direction:column;gap:8px;min-width:170px;}
.status-badge-v61,.scholarship-badge-v61 {display:inline-flex;justify-content:center;align-items:center;border-radius:999px;padding:9px 14px;font-weight:900;font-size:13px;}
.open-v61 {background:#10B981!important;color:#FFFFFF!important;}
.closed-v61 {background:#DC2626!important;color:#FFFFFF!important;}
.scholarship-badge-v61 {background:#EEF5FF!important;color:#002B5B!important;border:1px solid #CFE0FF;}
.info-grid-v61 {display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:12px;margin-top:20px;}
.info-grid-v61 div,.program-detail-v61 div {background:#F7F9FC;border:1px solid #E3EAF5;border-radius:12px;padding:13px 15px;}
.info-grid-v61 b,.program-detail-v61 b {display:block;color:#002B5B!important;margin-bottom:6px;}
.info-grid-v61 span,.program-detail-v61 span {display:block;color:#101828!important;}
.student-chart-v61 {display:flex;gap:18px;align-items:center;background:#FFFFFF;border:1px solid #DCE6F4;border-radius:16px;padding:16px;margin-top:20px;}
.student-chart-v61 span {display:block;color:#475467!important;margin-top:5px;}
.pie-v61 {width:105px;height:105px;min-width:105px;border-radius:50%;border:6px solid #FFFFFF;box-shadow:0 8px 20px rgba(16,24,40,.08);}
.subhead-v61 {color:#002B5B!important;margin-top:22px!important;margin-bottom:10px!important;}
.country-list-v61 {display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:10px;}
.country-list-v61 div,.country-list-v61 span {background:#F7F9FC;border:1px solid #E3EAF5;border-radius:12px;padding:12px;}
.country-list-v61 b {display:block;color:#101828!important;}
.country-list-v61 span {color:#475467!important;}
.map-box-v61 {border:1px solid #DCE6F4;border-radius:16px;overflow:hidden;height:310px;background:#F6F8FC;}
.map-box-v61 iframe {width:100%;height:100%;border:0;}
.program-detail-v61 {display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:10px;margin:12px 0 8px 0;}
.application-head-v61 {background:linear-gradient(90deg,#002B5B,#053B7A);border-radius:22px;padding:30px;margin-bottom:24px;}
.application-head-v61,.application-head-v61 * {color:#FFFFFF!important;}
.application-head-v61 span {display:inline-block;background:#10B981;border-radius:999px;padding:8px 14px;font-weight:900;}
@media(max-width:1000px){.info-grid-v61,.country-list-v61,.program-detail-v61{grid-template-columns:1fr;}.uni-title-row-v61{flex-direction:column;}}


/* v62 premium UniQuest redesign */
.uq-topbar-v62 {
    position: sticky; top: 0; z-index: 999;
    height: 76px; background:#FFFFFF;
    border-bottom:1px solid #E6ECF5;
    display:flex; align-items:center;
    padding: 8px 28px 8px 28px;
    box-shadow:0 4px 18px rgba(16,24,40,.04);
}
.uq-brand-v62 {display:flex;align-items:center;height:58px;}
.uq-logo-v62 {height:54px; object-fit:contain;}
.uq-logo-text-v62 {font-size:32px;font-weight:900;color:#002B5B;}
.uq-nav-btn-v62 div[data-testid="stButton"] button,
.uq-nav-btn-v62 .stButton button {
    background:transparent!important;
    color:#002B5B!important;
    -webkit-text-fill-color:#002B5B!important;
    border:0!important;
    box-shadow:none!important;
    border-radius:10px!important;
    font-weight:800!important;
    height:48px!important;
}
.uq-nav-btn-v62.active-nav-v62 div[data-testid="stButton"] button {
    color:#005BDB!important;
    -webkit-text-fill-color:#005BDB!important;
    border-bottom:3px solid #005BDB!important;
    border-radius:0!important;
}
.uq-nav-btn-v62 div[data-testid="stButton"] button:hover {
    background:#F3F7FF!important;
    color:#005BDB!important;
    -webkit-text-fill-color:#005BDB!important;
}
.hero-premium-v62 {
    min-height:360px; background-size:cover; background-position:center;
    position:relative; overflow:hidden; display:flex; align-items:center; padding:34px 54px;
}
.hero-pattern-v62 {
    position:absolute; left:22%; top:20px; width:420px; height:240px;
    background:radial-gradient(circle, rgba(255,255,255,.14) 1px, transparent 2px);
    background-size:16px 16px; opacity:.65;
}
.hero-content-v62 {position:relative; z-index:2; max-width:640px;}
.step-pill-v62 {
    display:inline-flex; gap:10px; align-items:center; background:rgba(255,255,255,.12);
    color:#FFFFFF!important; border:1px solid rgba(255,255,255,.25);
    border-radius:999px; padding:6px 16px; font-weight:800; margin-bottom:16px;
}
.step-pill-v62 span {background:#005BDB;color:#FFFFFF!important;border-radius:999px;padding:5px 14px;}
.hero-premium-v62 h1 {font-size:48px!important;line-height:1.08!important;color:#FFFFFF!important;margin:0 0 18px 0!important;}
.hero-premium-v62 p {font-size:17px!important;line-height:1.55!important;color:#FFFFFF!important;}
.featured-head-v62 {display:flex;justify-content:space-between;align-items:center;margin:24px 54px 10px;}
.featured-head-v62 h2 {color:#101828!important;font-size:24px!important;}
.featured-head-v62 span {color:#005BDB!important;font-weight:800;}
.uni-feature-card-v62 {
    background:#FFFFFF;border:1px solid #DDE7F5;border-radius:14px;overflow:hidden;
    box-shadow:0 8px 22px rgba(16,24,40,.06); min-height:245px; padding-bottom:14px; position:relative;
}
.uni-photo-premium-v62 {width:100%;height:85px;object-fit:cover;display:block;}
.uni-shield-v62 {position:absolute;top:60px;left:20px;background:#FFFFFF;border:4px solid #EFF5FF;border-radius:50%;width:52px;height:52px;display:flex;align-items:center;justify-content:center;}
.uni-feature-card-v62 h3 {font-size:16px!important;color:#002B5B!important;padding:24px 18px 4px;margin:0!important;}
.uni-feature-card-v62 p {color:#475467!important;font-size:13px!important;padding:0 18px;margin:6px 0!important;}
.access-note-v62 {text-align:center;color:#667085!important;margin:16px 0 10px!important;}
.features-v62 {display:grid;grid-template-columns:repeat(4,1fr);gap:0;background:#EFF6FF;border-top:1px solid #DDE7F5;border-bottom:1px solid #DDE7F5;padding:20px 55px;margin-top:28px;}
.feature-v62 {display:flex;gap:14px;align-items:center;justify-content:center;border-right:1px solid #D6E2F2;}
.feature-v62:last-child{border-right:0;}
.feature-icon-v62 {width:44px;height:44px;border-radius:50%;background:#FFFFFF;color:#005BDB;display:flex;align-items:center;justify-content:center;font-size:22px;}
.feature-v62 b{color:#002B5B!important;}
.feature-v62 span{color:#667085!important;}
.uq-footer-v62 {background:linear-gradient(90deg,#002B5B,#001C3D);padding:32px 55px 18px;color:#FFFFFF!important;}
.uq-footer-v62 * {color:#FFFFFF!important;}
.uq-footer-grid-v62 {display:grid;grid-template-columns:1.6fr 1.15fr 1.1fr 1.55fr 1fr;gap:28px;align-items:start;}
.footer-logo-v62 {max-width:190px;filter:brightness(0) invert(1);}
.footer-action-v62 {background:#005BDB;border:0;border-radius:8px;padding:10px 20px;font-weight:800;}
.socials-v62 span {display:inline-flex;width:38px;height:38px;align-items:center;justify-content:center;background:rgba(255,255,255,.12);border-radius:50%;margin-right:8px;}
.footer-bottom-v62 {border-top:1px solid rgba(255,255,255,.15);margin-top:22px;padding-top:14px;font-size:13px;color:#C7D7EA!important;display:flex;justify-content:space-between;}
.signup-shell-v62 {background:linear-gradient(90deg,#002B5B 0%,#002B5B 43%,#F5F8FF 43%,#F5F8FF 100%);padding:34px 64px 24px;}
.signup-left-v62 {color:#FFFFFF!important;padding:24px 10px;}
.signup-left-v62 * {color:#FFFFFF!important;}
.signup-left-v62 h1{font-size:46px!important;line-height:1.12!important;}
.signup-left-v62 p{font-size:17px!important;line-height:1.55!important;}
.signup-benefit-v62 {display:flex;gap:18px;margin:28px 0;align-items:flex-start;}
.signup-benefit-v62 > div {width:54px;height:54px;border-radius:14px;border:1px solid rgba(255,255,255,.25);display:flex;align-items:center;justify-content:center;font-size:25px;}
.important-note-v62 {background:rgba(255,255,255,.10);border:1px solid rgba(255,255,255,.22);border-radius:14px;padding:18px;margin-top:24px;}
.signup-card-v62 {background:#FFFFFF;border-radius:18px;padding:28px 34px;box-shadow:0 16px 40px rgba(16,24,40,.18);border:1px solid #E3EAF5;}
.dashboard-layout-v62 {display:flex;background:#F7FAFF;min-height:720px;}
.sidebar-v62 {position:fixed;left:0;top:76px;bottom:0;width:282px;background:linear-gradient(180deg,#002B5B,#001C3D);padding:24px 18px;z-index:100;color:#FFFFFF!important;}
.sidebar-v62 * {color:#FFFFFF!important;}
.side-brand-v62 {font-size:26px;font-weight:900;margin-bottom:22px;}
.side-line-v62 {height:1px;background:rgba(255,255,255,.16);margin-bottom:16px;}
.sidebar-v62 div[data-testid="stButton"] button {background:transparent!important;color:#FFFFFF!important;-webkit-text-fill-color:#FFFFFF!important;border:0!important;text-align:left!important;justify-content:flex-start!important;font-weight:800!important;}
.sidebar-v62 div[data-testid="stButton"] button:hover {background:#005BDB!important;}
.side-status-v62 {position:absolute;bottom:80px;left:18px;right:18px;border:1px solid rgba(255,255,255,.20);border-radius:14px;padding:18px;}
.side-status-v62 span{color:#65E095!important;}
.main-v62 {margin-left:282px;padding:24px 30px;width:calc(100% - 282px);background:#F7FAFF;}
.welcome-v62 {font-size:19px;font-weight:900;color:#002B5B!important;padding:12px 0;}
.avatar-v62 {width:42px;height:42px;background:#002B5B;color:#FFFFFF!important;border-radius:50%;display:flex;align-items:center;justify-content:center;font-weight:900;}
.partner-hero,.partner-stat-card,.partner-panel,.white-panel,.card {box-shadow:0 10px 30px rgba(16,24,40,.06)!important;border:1px solid #E3EAF5!important;border-radius:16px!important;}
@media(max-width:1050px){
    .features-v62,.uq-footer-grid-v62{grid-template-columns:1fr;}
    .signup-shell-v62{background:#002B5B;padding:24px;}
    .sidebar-v62{position:relative;top:0;width:100%;bottom:auto;}
    .main-v62{margin-left:0;width:100%;}
}

</style>
""", unsafe_allow_html=True)

def set_page(p):
    st.session_state.page = p
    st.rerun()








def header():
    logo_b64 = b64("uniquest_logo.png")
    logo_html = f'<img src="data:image/png;base64,{logo_b64}" class="uq-logo-v62">' if logo_b64 else '<div class="uq-logo-text-v62">UniQuest</div>'
    st.markdown('<div class="uq-topbar-v62">', unsafe_allow_html=True)
    cols = st.columns([1.9, .55, .75, 1.05, .85, .75, .85, .55, .95], gap="small")

    with cols[0]:
        st.markdown(f'<div class="uq-brand-v62">{logo_html}</div>', unsafe_allow_html=True)

    menu_items = [
        ("Home", "Home"),
        ("Universities", "Universities"),
        ("Eligibility Check", "Eligibility Check"),
        ("Tuition Fees", "Tuition & Scholarship"),
        ("Contact Us", "Contact Us"),
        ("MoU Contact", "Contact Us"),
        ("Login", "Login"),
        ("👥  Partner Sign Up", "Partner Sign Up"),
    ]

    for col, (label, page) in zip(cols[1:], menu_items):
        with col:
            active = "active-nav-v62" if st.session_state.get("page") == page else ""
            st.markdown(f'<div class="uq-nav-btn-v62 {active}">', unsafe_allow_html=True)
            if st.button(label, key=f"nav_v62_{label}", use_container_width=True):
                set_page(page)
            st.markdown('</div>', unsafe_allow_html=True)

    st.markdown('</div>', unsafe_allow_html=True)



def footer():
    logo_b64 = b64("uniquest_logo_footer.png") or b64("uniquest_logo.png")
    logo_html = f'<img src="data:image/png;base64,{logo_b64}" class="footer-logo-v62">' if logo_b64 else '<h2>UniQuest</h2>'
    st.markdown(f"""
    <div class="features-v62">
      <div class="feature-v62"><div class="feature-icon-v62">🛡️</div><div><b>Trusted Partnerships</b><br><span>Work with verified universities</span></div></div>
      <div class="feature-v62"><div class="feature-icon-v62">📄</div><div><b>Accurate Information</b><br><span>Up-to-date admission & fee details</span></div></div>
      <div class="feature-v62"><div class="feature-icon-v62">✓</div><div><b>Eligibility Made Easy</b><br><span>Quick checks for better guidance</span></div></div>
      <div class="feature-v62"><div class="feature-icon-v62">🎓</div><div><b>Scholarship Support</b><br><span>Maximize opportunities for students</span></div></div>
    </div>

    <div class="uq-footer-v62">
      <div class="uq-footer-grid-v62">
        <div>{logo_html}</div>
        <div>
          <h4>Contact Us</h4>
          <p>☎ +82 10 1234 5678</p>
          <p>✉ info@uniquest.com</p>
          <p>📍 Seoul, South Korea</p>
        </div>
        <div>
          <h4>Quick Links</h4>
          <p>Universities</p>
          <p>Eligibility Check</p>
          <p>Tuition Fees</p>
        </div>
        <div>
          <h4>Partnership Inquiries</h4>
          <p>Interested in becoming an approved partner?</p>
          <button class="footer-action-v62">✉ Get in Touch</button>
        </div>
        <div>
          <h4>Follow Us</h4>
          <div class="socials-v62"><span>f</span><span>in</span><span>▶</span><span>◎</span></div>
        </div>
      </div>
      <div class="footer-bottom-v62">© 2026 UniQuest. All rights reserved. <span>Privacy Policy&nbsp;&nbsp; | &nbsp;&nbsp;Terms of Use</span></div>
    </div>
    """, unsafe_allow_html=True)


def format_money_v37(x):
    try:
        if pd.isna(x) or str(x).strip() == "":
            return "Not provided"
        s = str(x).strip()
        if s.upper().startswith("KRW"):
            return s
        num = float(str(s).replace(",", "").replace("KRW", "").strip())
        return "KRW " + f"{int(num):,}"
    except Exception:
        return str(x)

def clean_scholarship_v37(x):
    if pd.isna(x) or str(x).strip() == "" or "Not provided" in str(x):
        return "Not provided"
    return str(x)




def fee_grid_item_v43(label, value):
    value = clean_criteria_text_v43(value)
    if is_blank_info_v43(value):
        return ""
    return f"<div><span>{label}</span><b>{value}</b></div>"


def is_blank_info_v43(value):
    if value is None:
        return True
    s = str(value).strip()
    if s == "":
        return True
    bad_values = [
        "not provided",
        "not provided in uploaded excel file",
        "nan",
        "none",
        "null",
        "-"
    ]
    return s.lower() in bad_values

def clean_criteria_text_v43(value):
    if value is None:
        return ""
    s = str(value).strip()
    if s.lower() in ["nan", "none", "null", "not provided", "not provided in uploaded excel file"]:
        return ""
    # remove repeated commas and comma around empty items
    parts = [p.strip() for p in s.split(",") if p.strip()]
    s = ", ".join(parts)
    s = re.sub(r"\s+,", ",", s)
    s = re.sub(r",\s*,+", ",", s)
    s = re.sub(r"\s{2,}", " ", s).strip(" ,")
    return s

def info_box_html_v43(label, value):
    value = clean_criteria_text_v43(value)
    if is_blank_info_v43(value):
        return ""
    return f'<div class="info-mini-v43"><b>{label}</b><span>{value}</span></div>'

def program_box_html_v43(title, value):
    value = clean_criteria_text_v43(value)
    if is_blank_info_v43(value):
        return ""
    return f'<div class="program-mini-v43"><b>{title}</b><span>{value}</span></div>'



def is_blank_display_v44(value):
    if value is None:
        return True
    s = str(value).strip()
    if s == "":
        return True
    s_low = s.lower()
    blank_tokens = [
        "not provided",
        "not provided in uploaded excel file",
        "nan",
        "none",
        "null",
        "-"
    ]
    return s_low in blank_tokens

def clean_display_text_v44(value):
    if value is None:
        return ""
    s = str(value).strip()
    if is_blank_display_v44(s):
        return ""
    parts = [p.strip() for p in s.split(",") if p.strip()]
    s = ", ".join(parts)
    s = re.sub(r",\s*,+", ",", s)
    s = re.sub(r"\s{2,}", " ", s).strip(" ,")
    return s

def fee_item_v44(label, value):
    value = clean_display_text_v44(value)
    if is_blank_display_v44(value):
        return ""
    return f"""
    <div>
        <span>{label}</span>
        <b>{value}</b>
    </div>
    """



def normalize_scholarship_display_v47(value):
    if value is None:
        return ""
    s = str(value).strip()
    if s == "" or s.lower() in ["nan", "none", "null", "not provided", "not provided in uploaded excel file"]:
        return ""

    # Convert decimal scholarship values to percentage text
    decimal_map = {
        "0.1": "10% of Tuition fee",
        "0.2": "20% of Tuition fee",
        "0.3": "30% of Tuition fee",
        "0.4": "40% of Tuition fee",
        "0.5": "50% of Tuition fee",
        "0.6": "60% of Tuition fee",
        "0.7": "70% of Tuition fee",
        "0.8": "80% of Tuition fee",
        "0.9": "90% of Tuition fee",
        "1.0": "100% of Tuition fee",
        "1": "100% of Tuition fee",
    }
    if s in decimal_map:
        return decimal_map[s]

    # Convert exact numeric decimal strings embedded alone
    try:
        f = float(s)
        if 0 < f <= 1:
            return f"{int(round(f * 100))}% of Tuition fee"
    except Exception:
        pass

    # Clean common mixed wording
    s = s.replace("Deduction on tuition fee", "of Tuition fee")
    s = s.replace("deduction on tuition fee", "of Tuition fee")
    s = s.replace("Deduction on Tuition fee", "of Tuition fee")
    s = s.replace("deduction on Tuition fee", "of Tuition fee")
    s = re.sub(r"(\d+)%\s+of\s+Tuition\s+fee", r"\1% of Tuition fee", s, flags=re.I)
    return s



def safe_slug_v49(text):
    text = str(text).strip().lower()
    text = re.sub(r"[^a-z0-9]+", "_", text)
    text = re.sub(r"_+", "_", text).strip("_")
    return text or "university"

def ensure_columns_v49(df, columns):
    for c in columns:
        if c not in df.columns:
            df[c] = ""
    return df

def save_uploaded_university_photo_v49(uploaded_file, university_name):
    if uploaded_file is None:
        return ""
    from PIL import Image, ImageEnhance
    slug = safe_slug_v49(university_name)
    out_dir = BASE / "assets" / "universities"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / f"{slug}.jpg"

    img = Image.open(uploaded_file).convert("RGB")
    target_size = (1600, 900)
    target_ratio = target_size[0] / target_size[1]
    w, h = img.size
    ratio = w / h

    if ratio > target_ratio:
        new_w = int(h * target_ratio)
        left = (w - new_w) // 2
        img = img.crop((left, 0, left + new_w, h))
    else:
        new_h = int(w / target_ratio)
        top = max(0, (h - new_h) // 2)
        img = img.crop((0, top, w, top + new_h))

    img = img.resize(target_size, Image.Resampling.LANCZOS)
    img = ImageEnhance.Sharpness(img).enhance(1.08)
    img.save(out_path, quality=94, optimize=True)
    return f"assets/universities/{slug}.jpg"

def reload_data_v49():
    try:
        st.cache_data.clear()
    except Exception:
        pass



def display_clean_v50(value):
    try:
        if pd.isna(value):
            return ""
    except Exception:
        pass
    s = str(value).strip()
    if s.lower() in ["nan", "none", "null", "<na>", "not provided", "not provided in uploaded excel file"]:
        return ""
    return s

def info_item_v50(label, value):
    value = display_clean_v50(value)
    if value == "":
        return ""
    return f'<div class="basic-info-item-v31"><b>{label}</b><span>{value}</span></div>'

def clean_df_v50(df):
    if df is None or len(df) == 0:
        return df
    return df.fillna("").replace(["nan", "NaN", "None", "null", "<NA>"], "")



def chunks_v51(items, size):
    for i in range(0, len(items), size):
        yield items[i:i+size]



def asset_img_html(path, cls):
    encoded = b64(path)
    if not encoded:
        return f'<div class="{cls} uni-photo-placeholder-v52">No image</div>'
    return f'<img class="{cls}" src="data:image/jpeg;base64,{encoded}"/>'



def display_value_v53(value):
    try:
        if pd.isna(value):
            return ""
    except Exception:
        pass
    s = str(value).strip()
    if s.lower() in ["nan", "none", "null", "<na>", "not provided", "not provided in uploaded excel file"]:
        return ""
    return s

def student_count_v53(u):
    for key in ["School_Size", "Total_Students", "Student_Count", "Students", "school_size", "total_students"]:
        try:
            val = u.get(key, "")
        except Exception:
            val = ""
        if display_value_v53(val):
            return display_value_v53(val)
    return ""

def intl_count_v53(u):
    for key in ["International_Students", "Foreign_Students", "International Students", "foreign_students"]:
        try:
            val = u.get(key, "")
        except Exception:
            val = ""
        if display_value_v53(val):
            return display_value_v53(val)
    return ""

def chunk_records_v53(records, size=5):
    for i in range(0, len(records), size):
        yield records[i:i+size]



def home():
    header()
    hero_img = asset_img_url("assets/home_hero.jpg")
    bg = ""
    if hero_img:
        bg = "background-image: linear-gradient(90deg, rgba(0,43,91,.98) 0%, rgba(0,43,91,.92) 34%, rgba(0,91,219,.35) 62%, rgba(0,43,91,.08) 100%), url('" + hero_img + "');"
    st.markdown(f"""
    <div class="hero-premium-v62" style="{bg}">
      <div class="hero-pattern-v62"></div>
      <div class="hero-content-v62">
        <div class="step-pill-v62"><span>Step 1</span> Home Page</div>
        <h1>Partner Portal for<br>University Recruitment</h1>
        <p>Approved partner agencies can access university details, application requirements, eligibility checking, and tuition/scholarship calculation.</p>
      </div>
    </div>
    """, unsafe_allow_html=True)

    c1, c2, c3 = st.columns([1.15, 1.15, 5.4])
    with c1:
        if st.button("👥  Apply for Partner Access", key="hero_apply_v62", use_container_width=True): set_page("Partner Sign Up")
    with c2:
        if st.button("🏛️  Explore Universities", key="hero_explore_v62", use_container_width=True): set_page("Universities")

    st.markdown('<div class="featured-head-v62"><h2>Featured Universities</h2><span>View All Universities →</span></div>', unsafe_allow_html=True)
    unis = universities().reset_index(drop=True).head(5)
    cols = st.columns(5, gap="medium")
    for col_idx, (i, u) in enumerate(unis.iterrows()):
        with cols[col_idx]:
            image_html = asset_img_html(u.get("Image", ""), "uni-photo-premium-v62")
            st.markdown(f"""
            <div class="uni-feature-card-v62">
              {image_html}
              <div class="uni-shield-v62">🏛️</div>
              <h3>{display_value_v53(u.get('University',''))}</h3>
              <p>📍 {display_value_v53(u.get('Location',''))}</p>
              <p>👥 {student_count_v53(u) or 'Students'}</p>
            </div>
            """, unsafe_allow_html=True)
            cc1, cc2 = st.columns(2)
            with cc1:
                if st.button("View Details", key=f"view_v62_{i}", use_container_width=True):
                    st.session_state.selected_uni = u["University"]
                    set_page("Universities")
            with cc2:
                if st.button("Requirements", key=f"req_v62_{i}", use_container_width=True):
                    st.session_state.selected_uni = u["University"]
                    set_page("Universities")

    st.markdown('<p class="access-note-v62">🔒 Access to detailed university information, programs, and fees is limited to approved partners.</p>', unsafe_allow_html=True)
    footer()



def signup():
    header()
    st.markdown('<div class="signup-shell-v62">', unsafe_allow_html=True)
    left, right = st.columns([0.95, 1.35], gap="large")

    with left:
        st.markdown("""
        <div class="signup-left-v62">
          <div class="step-pill-v62"><span>Step 2</span> Partner Sign Up</div>
          <h1>Partner Sign Up /<br>Agency Registration</h1>
          <p>Create your partner account to access UniQuest's university network, eligibility tools, and partner resources.</p>
          <hr>
          <div class="signup-benefit-v62"><div>🛡️</div><section><h3>Admin Approval Required</h3><p>All partner accounts are verified by our team. Access is granted only after approval.</p></section></div>
          <div class="signup-benefit-v62"><div>👥</div><section><h3>Trusted Partner Network</h3><p>We work with experienced and verified education partners worldwide.</p></section></div>
          <div class="signup-benefit-v62"><div>🔒</div><section><h3>Secure & Confidential</h3><p>Your information is safe with us and used strictly for partnership purposes.</p></section></div>
          <div class="important-note-v62"><b>ℹ️ Important Note</b><br>Your access will remain limited until your account is reviewed and approved by the UniQuest admin team.</div>
        </div>
        """, unsafe_allow_html=True)

    with right:
        st.markdown('<div class="signup-card-v62">', unsafe_allow_html=True)
        st.subheader("Create Your Partner Account")
        st.caption("Please fill in the details below to register your agency with UniQuest.")

        with st.form("signup"):
            row1_left, row1_right = st.columns(2)
            with row1_left:
                agency = st.text_input("Agency / Company Name", placeholder="Enter agency or company name")
            with row1_right:
                connection = st.selectbox("Official Partner Connection", ["KIEC","Realize Education","Other / New Agency"])

            row2_left, row2_right = st.columns(2)
            with row2_left:
                name = st.text_input("Representative Full Name", placeholder="Enter full name")
            with row2_right:
                email = st.text_input("Email Address", placeholder="Enter email address")

            row3_left, row3_right = st.columns(2)
            with row3_left:
                phone = st.text_input("Phone Number / WhatsApp", placeholder="+977 98XXXXXXXX")
            with row3_right:
                country = st.selectbox("Country", ["Nepal","South Korea","India","Bangladesh","Sri Lanka","Vietnam","Other"])

            row4_left, row4_right = st.columns(2)
            with row4_left:
                account_type = st.selectbox("Business Registration Type", ["Agency Representative", "Agency Staff", "Other"])
            with row4_right:
                username = st.text_input("Create Username")

            row5_left, row5_right = st.columns(2)
            with row5_left:
                password = st.text_input("Create Password", type="password")
            with row5_right:
                confirm = st.text_input("Confirm Password", type="password")

            supporting_doc = st.file_uploader("Upload Supporting Documents Optional", type=["pdf","jpg","jpeg","png"])
            agree = st.checkbox("I agree to UniQuest's Terms of Use and Privacy Policy.")

            if st.form_submit_button("✈ Submit for Approval", use_container_width=True):
                if not all([agency,name,email,username,password,confirm,account_type]):
                    st.error("Please complete all required fields.")
                elif password != confirm:
                    st.error("Passwords do not match.")
                elif not agree:
                    st.error("Please agree to the terms.")
                elif find_user(username):
                    st.error("This username already exists.")
                else:
                    role = "agency_rep" if account_type == "Agency Representative" else "agency_staff"
                    agency_id = normalize_agency_id(agency)
                    users = read_json(USERS)
                    users.append({
                        "username": username,
                        "password_hash": hash_pw(password),
                        "role": role,
                        "agency_name": agency,
                        "agency_id": agency_id,
                        "full_name": name,
                        "email": email,
                        "phone": phone,
                        "country": country,
                        "partner_group": connection,
                        "account_type": account_type,
                        "status": "pending",
                        "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    })
                    write_json(USERS, users)
                    set_page("Approval Pending")
        st.markdown('</div>', unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)
    footer()


def pending():
    header()
    st.markdown("""
    <div class="hero navy">
      <span class="badge">Step 3 &nbsp; Approval Pending</span>
      <h1>Thank You!<br>Your Registration Is Submitted</h1>
      <p>Your partner registration has been received and is now pending review by the administration team.</p>
    </div>
    """, unsafe_allow_html=True)
    st.markdown('<div class="section"><div class="two">', unsafe_allow_html=True)
    st.markdown("""
    <div class="white-panel"><h2>Application Timeline</h2>
    <p>✅ <b>Application Submitted</b><br><span class="muted">Your registration details have been submitted.</span></p>
    <p>🔵 <b>Under Review</b><br><span class="muted">Our team is reviewing your application.</span></p>
    <p>⚪ <b>Access Full Platform</b><br><span class="muted">Access is available after approval.</span></p></div>
    <div class="white-panel"><h2 style="color:#B54708!important;">Pending Approval</h2>
    <p>Detailed university information, eligibility check, tuition fees, and partner features will be available after approval.</p></div>
    """, unsafe_allow_html=True)
    st.markdown('</div></div>', unsafe_allow_html=True)
    footer()


def login():
    header()
    left, right = st.columns([0.95, 1.35], gap="large")

    with left:
        st.markdown("""
        <div class="public-left-box navy">
          <h1 style="font-size:42px;line-height:1.12;">Partner Portal for<br>University Recruitment</h1>
          <p style="font-size:17px;">Approved partner agencies can access university details, application requirements, eligibility checking, and tuition/scholarship calculation.</p>
          <hr style="border-color:rgba(255,255,255,.25);">
          <h3>🔐 Approved Partner Login</h3>
          <p>Only approved partners can access the dashboard.</p>
          <h3>📌 New Partner?</h3>
          <p>Please submit the partner sign-up form and wait for admin approval.</p>
        </div>
        """, unsafe_allow_html=True)

    with right:
        st.markdown('<div class="public-form-wrap"><div class="white-panel">', unsafe_allow_html=True)
        st.subheader("Welcome Back")
        st.caption("Partner Login")
        with st.form("login"):
            username = st.text_input("Username")
            password = st.text_input("Eligibleword", type="password")
            if st.form_submit_button("Login", use_container_width=True):
                user = find_user(username)
                if not user or user["password_hash"] != hash_pw(password):
                    st.error("Invalid username or password.")
                elif user["status"] != "approved":
                    set_page("Pending")
                else:
                    _set_login_session_from_user_v60(user)
                    try:
                        st.query_params["auth"] = _make_auth_token_v60(user)
                    except Exception:
                        pass
                    set_page("Admin Dashboard" if user["role"] == "admin" else "Dashboard")
        if st.button("Create New Partner Account", key="go_signup_from_login", use_container_width=True):
            set_page("Partner Sign Up")
        st.markdown('</div></div>', unsafe_allow_html=True)
    footer()



def dash_shell(items):
    st.markdown('<div class="dashboard-layout-v62">', unsafe_allow_html=True)
    st.markdown("""
    <div class="sidebar-v62">
      <div class="side-brand-v62">🛡️ UniQuest</div>
      <div class="side-line-v62"></div>
    """, unsafe_allow_html=True)
    for item in items:
        icon = {
            "Dashboard":"⌂", "Universities":"🏛️", "Eligibility Check":"◎", "Tuition & Scholarship":"▣",
            "Contact Us":"☏", "Partner Management":"👥", "Eligibility Rules":"☑", "Tuition Rules":"💵",
            "Scholarship Rules":"🎓", "Applications":"📄", "Admin Dashboard":"⌂"
        }.get(item, "›")
        if st.button(f"{icon}  {item}", key=f"dashnav_v62_{item}", use_container_width=True):
            set_page(item)
    st.markdown("""
      <div class="side-status-v62">
        <b>Partner Status</b><br>
        <span>● Approved Partner</span>
      </div>
    </div>
    """, unsafe_allow_html=True)
    st.markdown('<div class="main-v62">', unsafe_allow_html=True)
    top_cols = st.columns([5.2, 1.2, .35])
    with top_cols[0]:
        st.markdown(f'<div class="welcome-v62">Welcome, {st.session_state.get("agency_name") or st.session_state.get("full_name") or "Partner"}</div>', unsafe_allow_html=True)
    with top_cols[1]:
        if st.button("Logout", key="logout_v62", use_container_width=True):
            for k in ["logged_in","role","username","agency_name","agency_id","full_name","account_type"]:
                st.session_state[k] = False if k == "logged_in" else None
            try:
                st.query_params.clear()
            except Exception:
                pass
            set_page("Home")
    with top_cols[2]:
        st.markdown('<div class="avatar-v62">GP</div>', unsafe_allow_html=True)

admin_shell = dash_shell


def close_shell():
    st.markdown('</div></div>', unsafe_allow_html=True)



def partner_dashboard():
    dash_shell(["Dashboard","Universities","Eligibility Check","Tuition & Scholarship","Contact Us"])

    e = read_csv(ELIG_LOGS)
    t = read_csv(TUIT_LOGS)
    users_df = pd.DataFrame(read_json(USERS))

    visible_e = visible_logs(e)
    visible_t = visible_logs(t)

    total_unis = len(universities())
    total_checks = len(visible_e)
    pass_count = len(visible_e[visible_e["result"] == "Eligible"]) if len(visible_e) and "result" in visible_e.columns else 0
    fail_count = len(visible_e[visible_e["result"] == "FAIL"]) if len(visible_e) and "result" in visible_e.columns else 0

    if st.session_state.role == "agency_rep":
        portal_label = "Agency Representative Portal"
        intro = "Monitor all eligibility checks, tuition estimates, and staff activities within your agency."
    else:
        portal_label = "Agency Staff Portal"
        intro = "Check student eligibility, estimate tuition and scholarship, and manage your own student records."

    st.markdown(f"""
    <div class="partner-hero">
        <div class="partner-status-pill">{portal_label}</div>
        <h1>Welcome back,<br>{st.session_state.agency_name}</h1>
        <p>{intro}</p>
    </div>
    """, unsafe_allow_html=True)

    st.markdown(f"""
    <div class="partner-stat-grid">
        <div class="partner-stat-card">
            <h3>Available Universities</h3>
            <h2>{total_unis}</h2>
            <p class="muted">University profiles</p>
        </div>
        <div class="partner-stat-card">
            <h3>Eligibility Checks</h3>
            <h2>{total_checks}</h2>
            <p class="muted">{'Agency-wide records' if st.session_state.role == 'agency_rep' else 'Your records'}</p>
        </div>
        <div class="partner-stat-card">
            <h3>Eligible Results</h3>
            <h2>{pass_count}</h2>
            <p class="muted">Students matched</p>
        </div>
        <div class="partner-stat-card">
            <h3>Review Needed</h3>
            <h2>{fail_count}</h2>
            <p class="muted">Need alternatives</p>
        </div>
    </div>
    """, unsafe_allow_html=True)

    left, right = st.columns([1.25, .9], gap="large")

    with left:
        st.markdown('<div class="partner-panel">', unsafe_allow_html=True)
        st.subheader("Recent Student Eligibility Checks")
        if len(visible_e):
            st.dataframe(visible_e.sort_values("timestamp", ascending=False).head(12), use_container_width=True, hide_index=True)
        else:
            st.info("No eligibility checks yet.")
        st.markdown('</div>', unsafe_allow_html=True)

        if st.session_state.role == "agency_rep":
            st.markdown('<br>', unsafe_allow_html=True)
            st.markdown('<div class="partner-panel">', unsafe_allow_html=True)
            st.subheader("Agency Staff Activity")
            if len(users_df):
                staff = users_df[(users_df.get("agency_id","") == current_agency_id()) & (users_df.get("role","") == "agency_staff")]
                if len(staff):
                    rows = []
                    for _, s in staff.iterrows():
                        uname = s.get("username","")
                        staff_logs = e[e.get("partner_username","") == uname] if len(e) else pd.DataFrame()
                        rows.append({
                            "Staff Name": s.get("full_name",""),
                            "Username": uname,
                            "Status": s.get("status",""),
                            "Eligibility Checks": len(staff_logs)
                        })
                    st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
                else:
                    st.info("No staff accounts found for your agency yet.")
            else:
                st.info("No staff accounts found.")
            st.markdown('</div>', unsafe_allow_html=True)

    with right:
        st.markdown('<div class="partner-panel">', unsafe_allow_html=True)
        st.subheader("Quick Actions")

        st.markdown("""
        <div class="partner-action-card">
            <h4>Student Eligibility Check</h4>
            <p>Check whether a student matches available universities and majors.</p>
        </div>
        """, unsafe_allow_html=True)
        if st.button("Go to Eligibility Check", key="partner_go_elig", use_container_width=True):
            set_page("Eligibility Check")

        st.markdown("""
        <div class="partner-action-card">
            <h4>Tuition & Scholarship</h4>
            <p>Estimate tuition after scholarship based on IELTS score.</p>
        </div>
        """, unsafe_allow_html=True)
        if st.button("Go to Tuition Calculator", key="partner_go_tuition", use_container_width=True):
            set_page("Tuition & Scholarship")

        st.markdown("""
        <div class="partner-action-card">
            <h4>Contact Support</h4>
            <p>Send questions or partnership inquiries directly to UniQuest.</p>
        </div>
        """, unsafe_allow_html=True)
        if st.button("Contact Support", key="partner_go_contact", use_container_width=True):
            set_page("Contact Us")

        st.markdown('</div>', unsafe_allow_html=True)

        st.markdown('<br>', unsafe_allow_html=True)
        st.markdown(f"""
        <div class="partner-panel">
            <h3>Account Information</h3>
            <p><b>Agency:</b> {st.session_state.agency_name}</p>
            <p><b>User:</b> {st.session_state.full_name}</p>
            <p><b>Role:</b> {st.session_state.account_type}</p>
            <p><b>Status:</b> <span class="status-pass">Approved</span></p>
        </div>
        """, unsafe_allow_html=True)

    close_shell()



def universities_page(public=False):
    if public:
        header()
        st.markdown('<div class="universities-wrap-v32">', unsafe_allow_html=True)
    else:
        dash_shell(["Dashboard","Universities","Eligibility Check","Tuition & Scholarship","Contact Us"])
        st.markdown('<div class="universities-wrap-v32">', unsafe_allow_html=True)
    st.title("Universities Information")
    search = st.text_input("Search universities by name, location, or major")
    df = universities()
    if search:
        s = search.lower()
        df = df[df.apply(lambda r: s in " ".join(map(str, r.values)).lower(), axis=1)]

    for _, u in df.iterrows():
        image_html = asset_img_html(u.get("Image", ""), "uni-wide-v32")
        programs_html = program_list_html_for_university(u['University'])
        st.markdown(f"""
        <div class="uni-card-v32">
          {image_html}
          <div class="uni-body-v32">
            <h2>{u['University']}</h2>
            <p class="uni-overview-v32">{u.get('Overview', '')}</p>
            <div class="info-grid-v32">
              <div class="info-box-v32"><b>Homepage</b><span>{u.get('Homepage', '')}</span></div>
              <div class="info-box-v32"><b>Region</b><span>{u.get('Region', '')}</span></div>
              <div class="info-box-v32"><b>Address</b><span>{u.get('Address', '')}</span></div>
              <div class="info-box-v32"><b>School Size</b><span>{u.get('School_Size', '')}</span></div>
              <div class="info-box-v32"><b>Representative Phone</b><span>{u.get('Representative_Phone', '')}</span></div>
              <div class="info-box-v32"><b>Representative Fax</b><span>{u.get('Representative_Fax', '')}</span></div>
              <div class="info-box-v32"><b>Foreign Students</b><span>{display_clean_v50(u.get('International_Students', ''))}</span></div>
              <div class="info-box-v32"><b>Tuition Range</b><span>{u.get('Tuition_Range', '')}</span></div>
            </div>
            <h3 class="available-title-v41">Available Programs & Majors</h3>
            {programs_html}
          </div>
        </div>
        """, unsafe_allow_html=True)

    st.markdown('</div>', unsafe_allow_html=True)
    if public:
        footer()
    else:
        close_shell()





def program_applies(rule_program, selected_program):
    rp = str(rule_program or '').lower()
    sp = str(selected_program or '').lower()
    if 'undergraduate & graduate' in rp:
        return 'undergraduate' in sp or 'graduate' in sp
    if 'korean language' in rp or 'klp' in rp:
        return 'korean language' in sp or 'klp' in sp
    if 'undergraduate' in rp:
        return 'undergraduate' in sp
    if 'graduate' in rp and 'undergraduate' not in rp:
        return 'graduate' in sp and 'undergraduate' not in sp
    return rp == sp

def get_rule_min(rule, test_type):
    if test_type == 'IELTS': return rule.get('IELTS_Min', '')
    if test_type == 'TOEFL iBT': return rule.get('TOEFL_iBT_Min', '')
    if test_type == 'New TOEFL': return rule.get('New_TOEFL_Min', '')
    if test_type == 'TOPIK': return rule.get('TOPIK_Min', '')
    return ''

def scholarship_for_student(university, program, test_type, score):
    rules = scholarship_rules()
    if rules is None or len(rules) == 0:
        return {'percent':0, 'text':'Not provided', 'criteria':'No scholarship rule data'}
    rules = rules[rules['University'].astype(str).str.lower() == str(university).lower()].copy()
    if len(rules) == 0:
        return {'percent':0, 'text':'Not provided', 'criteria':'No scholarship rule for this university'}
    applicable = []
    for _, rule in rules.iterrows():
        if not program_applies(rule.get('Program_Rule',''), program):
            continue
        crit = str(rule.get('Language_Criteria',''))
        sch_text = str(rule.get('Scholarship_Text',''))
        pct = float(rule.get('Scholarship_Percent',0) or 0)
        if 'no scholarship' in sch_text.lower():
            applicable.append({'percent':0, 'text':sch_text, 'criteria':crit})
            continue
        if 'no need' in crit.lower() and ('korean language' in str(program).lower() or 'klp' in str(program).lower()):
            applicable.append({'percent':pct, 'text':sch_text, 'criteria':crit})
            continue
        need = get_rule_min(rule, test_type)
        try:
            if str(need).strip() != '' and float(score) >= float(need):
                applicable.append({'percent':pct, 'text':sch_text, 'criteria':crit})
        except Exception:
            pass
    if not applicable:
        return {'percent':0, 'text':'No scholarship matched', 'criteria':'Score does not meet available scholarship criteria'}
    return sorted(applicable, key=lambda x: x['percent'], reverse=True)[0]

def final_tuition_text(tuition_value, scholarship_percent):
    try:
        base = float(str(tuition_value).replace(',', '').replace('KRW','').strip())
        final = base * (1 - float(scholarship_percent)/100)
        return f"KRW {int(final):,}"
    except Exception:
        return 'Not calculated'

def program_list_html_for_university(university):
    df = criteria()
    sub = df[df['University'] == university].copy()
    groups = ['Undergraduate','Graduate','Korean Language Program (KLP)']
    html = '<div class="program-tabs-v41">'
    for g in groups:
        if 'Korean Language' in g:
            majors = sub[sub['Program'].astype(str).str.contains('Korean Language|KLP', case=False, regex=True, na=False)]['Major'].dropna().unique().tolist()
            title = 'Korean Language Program'
        else:
            majors = sub[sub['Program'] == g]['Major'].dropna().unique().tolist()
            title = g
        items = ''.join([f'<li>{m}</li>' for m in majors]) if majors else '<li>Not provided</li>'
        html += f'<div class="program-tab-card-v41"><h4>{title}</h4><ul>{items}</ul></div>'
    html += '</div>'
    return html


def parse_required_score(text, test_name, default_value):
    text = str(text or "")
    patterns = {
        "IELTS": r"IELTS\s*([0-9]+(?:\.[0-9]+)?)",
        "TOEFL iBT": r"TOEFL\s*iBT\s*([0-9]+(?:\.[0-9]+)?)",
        "New TOEFL": r"New\s*TOEFL\s*([0-9]+(?:\.[0-9]+)?)",
        "TOPIK": r"TOPIK\s*(?:Level\s*)?([0-9]+(?:\.[0-9]+)?)",
    }
    m = re.search(patterns.get(test_name, ""), text, flags=re.I)
    if m:
        try:
            return float(m.group(1))
        except Exception:
            return float(default_value or 0)
    return float(default_value or 0)

def money_text(value):
    try:
        if pd.isna(value) or str(value).strip() == "":
            return "Not provided"
        return f"KRW {int(float(value)):,}"
    except Exception:
        return str(value)

def nice_requirement(row, test_type="IELTS"):
    program = str(row.get("Program", ""))
    if "Korean Language" in program or "KLP" in program:
        return "English score not required"
    criteria_text = str(row.get("IELTS_Criteria", ""))
    required = parse_required_score(criteria_text, test_type, row.get("Minimum_IELTS", 0))
    if test_type == "TOEFL iBT":
        return f"TOEFL iBT {required:g} or higher"
    if test_type == "New TOEFL":
        return f"New TOEFL {required:g} or higher"
    if test_type == "TOPIK":
        return f"TOPIK Level {required:g} or higher"
    return f"IELTS {required:g} or higher"

def eligibility_match(row, program, gpa, test_type, score):
    if str(row.get("Program", "")) != str(program):
        return False
    try:
        if float(row.get("Minimum_GPA", 0) or 0) > float(gpa):
            return False
    except Exception:
        return False
    # Korean Language Program does not require English score.
    if "Korean Language" in str(program) or "KLP" in str(program):
        return True
    required = parse_required_score(row.get("IELTS_Criteria", ""), test_type, row.get("Minimum_IELTS", 0))
    try:
        return float(score) >= float(required)
    except Exception:
        return False

def render_eligibility_cards(matches, program, gpa, test_type, score):
    if not len(matches):
        return
    for i, (_, m) in enumerate(matches.iterrows()):
        app_fee = money_text(m.get("Application_Fee_KRW", m.get("Application Fee", "")))
        adm_fee = money_text(m.get("Admission_Fee_KRW", m.get("Admission Fee", "")))
        tuition_raw = m.get("Tuition_Fee_Per_Semester_KRW", m.get("Tuition_KRW", ""))
        tuition = money_text(tuition_raw)
        req = nice_requirement(m, test_type)
        gpa_req = m.get("GPA_Criteria", f"GPA {m.get('Minimum_GPA','')} or higher")
        sch = scholarship_for_student(m.get('University',''), m.get('Program',''), test_type, score)
        sch_percent = sch.get('percent', 0)
        final_tuition = final_tuition_text(tuition_raw, sch_percent)
        sch_display = f"{int(sch_percent)}% scholarship" if sch_percent else "No scholarship / Not matched"
        lang_value = 'Not required' if ('Korean Language' in str(program) or 'KLP' in str(program)) else f'{test_type} {float(score):g}'
        st.markdown(f"""
        <div class="elig-card-v41">
            <div class="elig-card-top-v41">
                <div>
                    <div class="elig-university-v41">{m.get('University','')}</div>
                    <div class="elig-major-v41">{m.get('Major','')}</div>
                </div>
                <div class="elig-pass-v41">Eligible</div>
            </div>
            <div class="elig-detail-grid-v41">
                <div><b>Program</b><span>{m.get('Program','')}</span></div>
                <div><b>Admission Eligibility</b><span class="pass-text-v41">Eligible</span></div>
                <div><b>Student GPA</b><span>{float(gpa):.2f}</span></div>
                <div><b>Language Score</b><span>{lang_value}</span></div>
                <div><b>GPA / % Requirement</b><span>{gpa_req}</span></div>
                <div><b>Language Requirement</b><span>{req}</span></div>
                <div><b>Application Fee</b><span>{app_fee}</span></div>
                <div><b>Admission Fee</b><span>{adm_fee}</span></div>
                <div><b>Original Tuition / Semester</b><span>{tuition}</span></div>
                <div><b>Scholarship Result</b><span>{clean_display_text_v44(sch_display)}</span></div>
                <div><b>Estimated Tuition Fee After Scholarship</b><span class="final-tuition-v41">{final_tuition}</span></div>
                <div><b>Scholarship Criteria</b><span>{clean_display_text_v44(sch.get('criteria',''))}</span></div>
            </div>
        </div>
        """, unsafe_allow_html=True)



def eligibility():
    dash_shell(["Dashboard","Universities","Eligibility Check","Tuition & Scholarship","Contact Us"])
    st.subheader("Eligibility Check")
    df = criteria()

    c1, c2 = st.columns([0.92, 1.38], gap="large")
    with c1:
        st.markdown('<div class="elig-form-panel-v41">', unsafe_allow_html=True)
        program = st.selectbox("Program Level", sorted(df["Program"].unique()), key="elig_program_v41")
        name = st.text_input("Student Full Name", key="elig_student_name_v41")
        gpa = st.number_input("GPA", 0.0, 4.5, 3.0, 0.01, key="elig_gpa_v41")

        if "Korean Language" in str(program) or "KLP" in str(program):
            st.info("Korean Language Program does not require IELTS, TOEFL iBT, New TOEFL, or TOPIK score.")
            test_type = "Not required"
            score = 0.0
        else:
            test_type = st.selectbox("Language Score Type", ["IELTS", "TOEFL iBT", "New TOEFL", "TOPIK"], key="elig_test_type_v41")
            if test_type == "IELTS":
                score = st.number_input("IELTS Score", 0.0, 9.0, 5.5, 0.5, key="elig_score_ielts_v41")
            elif test_type == "TOEFL iBT":
                score = st.number_input("TOEFL iBT Score", 0.0, 120.0, 71.0, 1.0, key="elig_score_toefl_v41")
            elif test_type == "New TOEFL":
                score = st.number_input("New TOEFL Score", 0.0, 6.0, 3.5, 0.1, key="elig_score_newtoefl_v41")
            else:
                score = st.number_input("TOPIK Level", 0.0, 6.0, 3.0, 1.0, key="elig_score_topik_v41")

        submitted = st.button("Check Eligibility", use_container_width=True, key="check_elig_v41")
        st.markdown('</div>', unsafe_allow_html=True)

    with c2:
        if submitted:
            if not str(name).strip():
                st.markdown("""
                <div class="elig-summary-fail-v36">
                    <h3>Student Name Required</h3>
                    <p>Please enter the student name before checking eligibility.</p>
                </div>
                """, unsafe_allow_html=True)
                close_shell(); return
            matches = df[df.apply(lambda r: eligibility_match(r, program, gpa, test_type, score), axis=1)].copy()
            if len(matches):
                st.markdown(f"""
                <div class="elig-summary-pass-v36">
                    <h3>Eligible Programs Found</h3>
                    <p><b>{name}</b> is eligible for <b>{len(matches)}</b> program(s). Scholarship is calculated based on the available scholarship rules.</p>
                </div>
                """, unsafe_allow_html=True)
                render_eligibility_cards(matches, program, gpa, test_type, score)
                for _, m in matches.iterrows():
                    sch = scholarship_for_student(m.get('University',''), m.get('Program',''), test_type, score)
                    add_row(ELIG_LOGS, {
                        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                        "partner_username": st.session_state.username,
                        "agency_id": st.session_state.get("agency_id", ""),
                        "agency_name": st.session_state.agency_name,
                        "checked_by_name": st.session_state.get("full_name", ""),
                        "student_name": name,
                        "program": program,
                        "english_test_type": test_type,
                        "english_score": score,
                        "scholarship_percent": sch.get('percent', 0),
                        "university": m.get("University", ""),
                        "major": m.get("Major", ""),
                        "gpa": gpa,
                        "ielts": score if test_type == "IELTS" else 0,
                        "toefl_ibt": score if test_type == "TOEFL iBT" else 0,
                        "new_toefl": score if test_type == "New TOEFL" else 0,
                        "topik": score if test_type == "TOPIK" else 0,
                        "result": "Eligible"
                    })
            else:
                st.markdown(f"""
                <div class="elig-summary-fail-v36">
                    <h3>No Eligible Program Found</h3>
                    <p><b>{name}</b>'s profile does not meet the current criteria for <b>{program}</b>. Please check another program level, GPA, or language score.</p>
                </div>
                """, unsafe_allow_html=True)
                add_row(ELIG_LOGS, {
                    "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "partner_username": st.session_state.username,
                    "agency_id": st.session_state.get("agency_id", ""),
                    "agency_name": st.session_state.agency_name,
                    "checked_by_name": st.session_state.get("full_name", ""),
                    "student_name": name,
                    "program": program,
                    "english_test_type": test_type,
                    "english_score": score,
                    "scholarship_percent": 0,
                    "university": "",
                    "major": "",
                    "gpa": gpa,
                    "ielts": score if test_type == "IELTS" else 0,
                    "toefl_ibt": score if test_type == "TOEFL iBT" else 0,
                    "new_toefl": score if test_type == "New TOEFL" else 0,
                    "topik": score if test_type == "TOPIK" else 0,
                    "result": "FAIL"
                })
        else:
            st.markdown("""
            <div class="elig-empty-v36">
                <h3>Check Student Eligibility</h3>
                <p>Enter the student name first, then select program level, GPA, and language score. The result will show university, department/major, admission result, scholarship result, and final tuition in clean cards.</p>
                <div class="elig-mini-list-v36">
                    <span>Student name required</span>
                    <span>IELTS supported</span>
                    <span>TOEFL iBT supported</span>
                    <span>New TOEFL supported</span>
                    <span>TOPIK supported</span>
                    <span>KLP no score required</span>
                </div>
            </div>
            """, unsafe_allow_html=True)
    close_shell()


def scholarship_percent(x):
    if x >= 8: return 100
    if x >= 7: return 50
    if x >= 5.5: return 30
    return 0




def scholarship_rules_summary_v45(university, program):
    rules = scholarship_rules()
    if rules is None or len(rules) == 0:
        return ""

    sub = rules[
        rules["University"].astype(str).str.strip().str.lower()
        == str(university).strip().lower()
    ].copy()

    if len(sub) == 0:
        return ""

    rows = []
    for _, rule in sub.iterrows():
        if not program_applies(rule.get("Program_Rule", ""), program):
            continue

        crit = clean_display_text_v44(rule.get("Language_Criteria", ""))
        text = clean_display_text_v44(rule.get("Scholarship_Text", ""))
        text = normalize_scholarship_display_v47(text)

        if is_blank_display_v44(crit) and is_blank_display_v44(text):
            continue

        if "no scholarship" in str(text).lower():
            continue

        if crit and text:
            rows.append(f"{crit} → {text}")
        elif text:
            rows.append(text)
        elif crit:
            rows.append(crit)

    # Remove duplicates while preserving order
    clean_rows = []
    seen = set()
    for r in rows:
        r = clean_display_text_v44(r)
        if r and r not in seen:
            clean_rows.append(r)
            seen.add(r)

    return "<br>".join(clean_rows)

def fee_grid_item_v45(label, value):
    value = clean_display_text_v44(value)
    if is_blank_display_v44(value):
        return ""
    return f'<div><b>{label}</b><span>{value}</span></div>'



def tuition():
    dash_shell(["Dashboard","Universities","Eligibility Check","Tuition & Scholarship","Contact Us"])
    st.subheader("Tuition Fees & Scholarship Information")

    df = criteria()
    if df is None or len(df) == 0:
        st.error("No tuition data found. Please check the uploaded data file.")
        close_shell()
        return

    c1, c2 = st.columns([0.90, 1.40], gap="large")

    with c1:
        st.markdown('<div class="elig-form-panel-v40">', unsafe_allow_html=True)
        st.markdown("<h3 class='form-title-v40'>Select Program Information</h3>", unsafe_allow_html=True)

        universities_list = sorted(df["University"].dropna().unique().tolist())
        uni = st.selectbox("University", universities_list, key="fee_uni_v45")

        programs_list = sorted(df[df["University"] == uni]["Program"].dropna().unique().tolist())
        program = st.selectbox("Program", programs_list, key="fee_program_v45")

        major_df = df[(df["University"] == uni) & (df["Program"] == program)].copy()
        majors = sorted(major_df["Major"].dropna().unique().tolist())
        if not majors:
            majors = ["No major found"]
        major = st.selectbox("Major", majors, key=f"fee_major_v45_{uni}_{program}")
        st.markdown('</div>', unsafe_allow_html=True)

    with c2:
        if major == "No major found" or len(major_df) == 0:
            st.markdown("""
            <div class="elig-empty-v36">
                <h3>No fee information found</h3>
                <p>Please select another university or program.</p>
            </div>
            """, unsafe_allow_html=True)
        else:
            row = major_df[major_df["Major"] == major].iloc[0]
            app_fee = money_text(row.get("Application_Fee_KRW", row.get("Application Fee", "")))
            adm_fee = money_text(row.get("Admission_Fee_KRW", row.get("Admission Fee", "")))
            tuition_fee = money_text(row.get("Tuition_Fee_Per_Semester_KRW", row.get("Tuition_KRW", "")))

            gpa_req = clean_display_text_v44(row.get("GPA_Criteria", f"GPA {row.get('Minimum_GPA','')} or higher"))
            lang_req = clean_display_text_v44(row.get("IELTS_Criteria", row.get("Language_Criteria", row.get("Minimum_IELTS", ""))))

            scholarship_summary = scholarship_rules_summary_v45(uni, program)
            scholarship_html = fee_grid_item_v45("Scholarship Criteria", scholarship_summary)

            st.markdown(f"""
            <div class="fee-result-card-v40">
                <div class="fee-result-head-v40">
                    <div>
                        <p class="fee-eyebrow-v40">Fee Summary</p>
                        <h3>{uni}</h3>
                        <p>{program} · {major}</p>
                    </div>
                    <div class="fee-badge-v40">Auto Updated</div>
                </div>
                <div class="fee-grid-v40">
                    <div><b>Application Fee</b><span>{app_fee}</span></div>
                    <div><b>Admission Fee</b><span>{adm_fee}</span></div>
                    <div><b>Tuition / Semester</b><span>{tuition_fee}</span></div>
                    {scholarship_html}
                    <div><b>GPA / Percentage Requirement</b><span>{gpa_req}</span></div>
                    <div><b>Language Requirement</b><span>{lang_req}</span></div>
                </div>
            </div>
            """, unsafe_allow_html=True)

    close_shell()


def contact():
    if st.session_state.logged_in:
        dash_shell(["Dashboard","Universities","Eligibility Check","Tuition & Scholarship","Contact Us"])
    else:
        header(); st.markdown('<div class="section">', unsafe_allow_html=True)
    st.subheader("Contact Us")
    with st.form("contact"):
        name = st.text_input("Name")
        email = st.text_input("Email")
        msg = st.text_area("Message")
        if st.form_submit_button("Send Inquiry", use_container_width=True):
            add_row(INQUIRIES, {"timestamp":datetime.now().strftime("%Y-%m-%d %H:%M:%S"),"name":name,"email":email,"message":msg,"status":"New"})
            st.success("Your inquiry has been saved.")
    if st.session_state.logged_in:
        close_shell()
    else:
        st.markdown('</div>', unsafe_allow_html=True); footer()


def admin():
    dash_shell(["Admin Dashboard","Partner Management","Universities","Eligibility Rules","Tuition Rules","Scholarship Rules","Applications"])

    users = pd.DataFrame(read_json(USERS))
    if len(users):
        partners = users[users["role"].isin(["agency_rep", "agency_staff", "partner"])].copy()
    else:
        partners = pd.DataFrame()

    e = read_csv(ELIG_LOGS)
    inquiries = read_csv(INQUIRIES)

    pending = len(partners[partners["status"]=="pending"]) if len(partners) else 0
    approved = len(partners[partners["status"]=="approved"]) if len(partners) else 0
    agency_reps = len(partners[partners["role"]=="agency_rep"]) if len(partners) else 0
    agency_staff = len(partners[partners["role"]=="agency_staff"]) if len(partners) else 0

    st.subheader("Admin Dashboard")
    st.markdown(f"""
    <div class="stats">
      <div class="stat"><b>Total Partner Users</b><h2>{len(partners)}</h2></div>
      <div class="stat"><b>Pending Approvals</b><h2>{pending}</h2></div>
      <div class="stat"><b>Agency Representatives</b><h2>{agency_reps}</h2></div>
      <div class="stat"><b>Agency Staff</b><h2>{agency_staff}</h2></div>
      <div class="stat"><b>Eligibility Checks</b><h2>{len(e)}</h2></div>
    </div>
    """, unsafe_allow_html=True)

    st.subheader("Partner Approval Requests")
    pending_partners = partners[partners["status"]=="pending"] if len(partners) else pd.DataFrame()

    if len(pending_partners):
        for idx, p in pending_partners.iterrows():
            st.markdown(f"""
            <div class="approval-card-v34">
                <div>
                    <h4>{p.get('agency_name','')}</h4>
                    <p><b>Name:</b> {p.get('full_name','')} &nbsp; | &nbsp; <b>Username:</b> {p.get('username','')}</p>
                    <p><b>Account Type:</b> {p.get('account_type', p.get('role',''))} &nbsp; | &nbsp; <b>Email:</b> {p.get('email','')}</p>
                    <p><b>Country:</b> {p.get('country','')} &nbsp; | &nbsp; <b>Status:</b> <span class="status-pending">pending</span></p>
                </div>
            </div>
            """, unsafe_allow_html=True)

            c1, c2, c3 = st.columns([1,1,5])
            with c1:
                if st.button("Approve", key=f"approve_{p.get('username','')}", use_container_width=True):
                    all_users = read_json(USERS)
                    for u in all_users:
                        if u.get("username") == p.get("username"):
                            u["status"] = "approved"
                    write_json(USERS, all_users)
                    st.success(f"{p.get('username')} approved.")
                    st.rerun()
            with c2:
                if st.button("Reject", key=f"reject_{p.get('username','')}", use_container_width=True):
                    all_users = read_json(USERS)
                    for u in all_users:
                        if u.get("username") == p.get("username"):
                            u["status"] = "rejected"
                    write_json(USERS, all_users)
                    st.warning(f"{p.get('username')} rejected.")
                    st.rerun()
    else:
        st.info("No pending partner approval requests.")

    st.subheader("Eligibility Check History")
    if len(e):
        st.dataframe(e.sort_values("timestamp", ascending=False), use_container_width=True, hide_index=True)
    else:
        st.info("No eligibility checks yet.")

    st.subheader("Recent Contact Inquiries")
    if len(inquiries):
        st.dataframe(inquiries.sort_values("timestamp", ascending=False), use_container_width=True, hide_index=True)
    else:
        st.info("No contact inquiries yet.")

    close_shell()


def update_user_record_v58(old_username, new_row):
    users = read_json(USERS)
    updated = []
    for u in users:
        if str(u.get("username", "")).strip() == str(old_username).strip():
            # keep password if the editor leaves it blank
            existing_pw_hash = u.get("password_hash", "")
            existing_pw = u.get("password", "")
            u.update(new_row)
            if not str(u.get("password", "")).strip() and existing_pw:
                u["password"] = existing_pw
            if not str(u.get("password_hash", "")).strip() and existing_pw_hash:
                u["password_hash"] = existing_pw_hash
        updated.append(u)
    write_json(USERS, updated)

def delete_user_record_v58(username):
    users = read_json(USERS)
    users = [u for u in users if str(u.get("username", "")).strip() != str(username).strip()]
    write_json(USERS, users)

def add_user_record_v58(new_row):
    users = read_json(USERS)
    users.append(new_row)
    write_json(USERS, users)


def admin_partner_management_v58():
    dash_shell(["Admin Dashboard","Partner Management","Universities","Eligibility Rules","Tuition Rules","Scholarship Rules","Applications"])
    st.subheader("Partner Management")
    st.caption("Edit, approve/reject, or delete partner users. Admin account cannot be deleted here for safety.")

    users = read_json(USERS)
    if not users:
        st.info("No partner users found.")
        close_shell()
        return

    df = pd.DataFrame(users).fillna("").replace(["nan", "NaN", "None", "null", "<NA>"], "")
    hidden_cols = [c for c in ["password_hash", "password"] if c in df.columns]
    display_cols = [c for c in df.columns if c not in hidden_cols]

    st.markdown("### Current Users")
    st.dataframe(df[display_cols], use_container_width=True, hide_index=True)

    st.markdown("### Edit / Delete User")
    usernames = [str(u.get("username", "")).strip() for u in users if str(u.get("username", "")).strip()]
    selected_username = st.selectbox("Select User", usernames, key="pm_select_user_v58")
    selected_user = next((u for u in users if str(u.get("username", "")).strip() == selected_username), {})

    with st.form("edit_user_form_v58"):
        c1, c2, c3 = st.columns(3)
        with c1:
            username = st.text_input("Username", value=str(selected_user.get("username", "")))
            full_name = st.text_input("Full Name", value=str(selected_user.get("full_name", selected_user.get("name", ""))))
            email = st.text_input("Email", value=str(selected_user.get("email", "")))
        with c2:
            phone = st.text_input("Phone", value=str(selected_user.get("phone", "")))
            country = st.text_input("Country", value=str(selected_user.get("country", "")))
            agency_name = st.text_input("Agency Name", value=str(selected_user.get("agency_name", selected_user.get("partner_group", ""))))
        with c3:
            role_options = ["admin", "agency_rep", "agency_staff", "partner"]
            current_role = str(selected_user.get("role", "agency_staff"))
            role = st.selectbox("Role", role_options, index=role_options.index(current_role) if current_role in role_options else 1)
            status_options = ["pending", "approved", "rejected"]
            current_status = str(selected_user.get("status", "pending"))
            status = st.selectbox("Status", status_options, index=status_options.index(current_status) if current_status in status_options else 0)
            new_password = st.text_input("New Password Optional", type="password", help="Leave blank to keep current password.")

        csave, cdelete = st.columns(2)
        save_clicked = csave.form_submit_button("Save User Changes", use_container_width=True)
        delete_clicked = cdelete.form_submit_button("Delete Selected User", use_container_width=True)

        if save_clicked:
            if not username.strip():
                st.error("Username is required.")
            elif username.strip() != selected_username and username.strip() in usernames:
                st.error("This username already exists.")
            else:
                new_row = dict(selected_user)
                new_row.update({
                    "username": username.strip(),
                    "full_name": full_name.strip(),
                    "email": email.strip(),
                    "phone": phone.strip(),
                    "country": country.strip(),
                    "agency_name": agency_name.strip(),
                    "partner_group": agency_name.strip(),
                    "role": role,
                    "status": status,
                })
                if new_password.strip():
                    try:
                        new_row["password_hash"] = hash_pw(new_password.strip())
                    except Exception:
                        new_row["password"] = new_password.strip()
                update_user_record_v58(selected_username, new_row)
                st.success("User information updated successfully.")
                st.rerun()

        if delete_clicked:
            if selected_username == "admin":
                st.error("The main admin account cannot be deleted.")
            else:
                delete_user_record_v58(selected_username)
                st.warning(f"{selected_username} has been deleted.")
                st.rerun()

    st.markdown("### Add User Manually")
    with st.form("add_user_form_v58"):
        c1, c2, c3 = st.columns(3)
        with c1:
            new_username = st.text_input("New Username")
            new_full_name = st.text_input("New Full Name")
            new_email = st.text_input("New Email")
        with c2:
            new_phone = st.text_input("New Phone")
            new_country = st.text_input("New Country", value="Nepal")
            new_agency = st.text_input("New Agency Name")
        with c3:
            new_role = st.selectbox("New Role", ["agency_rep", "agency_staff", "partner"], key="new_role_v58")
            new_status = st.selectbox("New Status", ["approved", "pending", "rejected"], key="new_status_v58")
            pw = st.text_input("Password", type="password", key="new_pw_v58")

        if st.form_submit_button("Add User", use_container_width=True):
            if not all([new_username.strip(), new_full_name.strip(), new_agency.strip(), pw.strip()]):
                st.error("Username, full name, agency name, and password are required.")
            elif new_username.strip() in usernames:
                st.error("This username already exists.")
            else:
                add_user_record_v58({
                    "username": new_username.strip(),
                    "password_hash": hash_pw(pw.strip()),
                    "full_name": new_full_name.strip(),
                    "email": new_email.strip(),
                    "phone": new_phone.strip(),
                    "country": new_country.strip(),
                    "agency_name": new_agency.strip(),
                    "partner_group": new_agency.strip(),
                    "role": new_role,
                    "status": new_status,
                    "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                })
                st.success("New user added successfully.")
                st.rerun()

    close_shell()

def admin_table(title, df):
    dash_shell(["Admin Dashboard","Partner Management","Universities","Eligibility Rules","Tuition Rules","Scholarship Rules","Applications"])
    st.subheader(title)
    st.dataframe(clean_df_v50(df), use_container_width=True, hide_index=True)
    st.info("Later, we can add Add/Edit/Delete forms here.")
    close_shell()



# ===== v48 Admin Editable Database Management =====
def clear_data_cache_v48():
    try:
        st.cache_data.clear()
    except Exception:
        pass

def safe_write_csv_v48(path, df):
    # v55: Save through the DB-aware write_csv helper.
    # This keeps the v53 design while making Admin table edits persistent in SQLite.
    df = df.copy().fillna("").replace(["nan", "NaN", "None", "null", "<NA>"], "")
    write_csv(path, df)
    clear_data_cache_v48()

def editable_table_v48(title, path, key, help_text=""):
    dash_shell(["Admin Dashboard","Partner Management","Universities","Eligibility Rules","Tuition Rules","Scholarship Rules","Applications"])
    st.subheader(title)
    if help_text:
        st.caption(help_text)
    df = read_csv(path)
    if len(df) == 0:
        st.warning("No data found. A blank table will be created after you add rows.")
    edited = st.data_editor(
        df,
        num_rows="dynamic",
        use_container_width=True,
        hide_index=True,
        key=key
    )
    c1, c2 = st.columns([1, 4])
    with c1:
        if st.button("Save Changes", key=f"save_{key}", use_container_width=True):
            safe_write_csv_v48(path, edited)
            st.success("Saved successfully. The website data has been updated.")
            st.rerun()
    with c2:
        st.info("You can edit cells directly, add new rows, or delete rows in the table above. Click Save Changes when finished.")
    close_shell()

def admin_universities_edit_v48():
    dash_shell(["Admin Dashboard","Partner Management","Universities","Eligibility Rules","Tuition Rules","Scholarship Rules","Applications"])
    st.subheader("Universities Management")
    st.caption("Edit school information directly. Uploading a photo will update the selected school's image path automatically.")

    df = read_csv(UNIS)
    if len(df) == 0:
        st.error("No university data found.")
        close_shell(); return

    st.markdown("### Quick Photo Update")
    uni_names = df["University"].dropna().astype(str).tolist()
    selected_uni = st.selectbox("Select University for Photo Update", uni_names, key="photo_uni_v48")
    uploaded = st.file_uploader("Upload university image", type=["png", "jpg", "jpeg"], key="uni_photo_upload_v48")
    if uploaded is not None:
        from PIL import Image, ImageEnhance
        img = Image.open(uploaded).convert("RGB")
        assets_dir = BASE / "assets" / "universities"
        assets_dir.mkdir(parents=True, exist_ok=True)
        clean_name = re.sub(r"[^a-z0-9]+", "_", selected_uni.lower()).strip("_") or "university"
        out_path = assets_dir / f"{clean_name}.jpg"
        # Website-friendly 16:9 cover image
        target = (1600, 900)
        target_ratio = target[0] / target[1]
        w, h = img.size
        ratio = w / h
        if ratio > target_ratio:
            new_w = int(h * target_ratio)
            left = (w - new_w) // 2
            img = img.crop((left, 0, left + new_w, h))
        else:
            new_h = int(w / target_ratio)
            top = max(0, (h - new_h) // 2)
            img = img.crop((0, top, w, top + new_h))
        img = img.resize(target, Image.Resampling.LANCZOS)
        img = ImageEnhance.Sharpness(img).enhance(1.10)
        img.save(out_path, quality=96, optimize=True, progressive=True)
        df.loc[df["University"].astype(str) == selected_uni, "Image"] = str(out_path.relative_to(BASE)).replace("\\", "/")
        safe_write_csv_v48(UNIS, df)
        st.success(f"Photo updated for {selected_uni}.")
        st.rerun()

    st.markdown("### Edit University Data")
    edited = st.data_editor(
        df,
        num_rows="dynamic",
        use_container_width=True,
        hide_index=True,
        key="universities_editor_v48"
    )
    if st.button("Save University Changes", key="save_universities_v48", use_container_width=True):
        safe_write_csv_v48(UNIS, edited)
        st.success("University information saved successfully.")
        st.rerun()
    close_shell()

def admin_criteria_edit_v48():
    editable_table_v48(
        "Eligibility Criteria / Program & Major Management",
        CRITERIA,
        "criteria_editor_v48",
        "Edit university, program level, major, GPA, language criteria, application fee, admission fee, and tuition fee."
    )

def admin_scholarship_edit_v48():
    editable_table_v48(
        "Scholarship Rules Management",
        SCHOLARSHIPS,
        "scholarship_editor_v48",
        "Edit scholarship criteria by university and program. Decimal values such as 0.4 should be written as 40% of Tuition fee for clearer display."
    )

def admin_tuition_edit_v48():
    editable_table_v48(
        "Tuition Rules Management",
        CRITERIA,
        "tuition_editor_v48",
        "Tuition values are stored in the criteria database. Edit Application_Fee_KRW, Admission_Fee_KRW, Tuition_KRW, and Tuition_Fee_Per_Semester_KRW here."
    )


def admin_university_management_v49():
    dash_shell(["Admin Dashboard","Partner Management","Universities","Eligibility Rules","Tuition Rules","Scholarship Rules","Applications"])
    st.subheader("University Management")
    st.caption("Add, edit, or update university information. New universities will appear on the Home and Universities pages. To appear in Eligibility, add at least one major in Eligibility Rules after adding the university.")

    uni_file = DATA / "universities.csv"
    df = read_csv(uni_file)
    required_cols = [
        "University","Location","Total_Students","International_Students","Top_Majors",
        "Intake","Tuition_Range","Scholarship_Info","Overview","Image",
        "Homepage","Address","Representative_Phone","Representative_Fax","Region","School_Size",
        "Application_Status","Application_Deadline","Maps_URL","Country_Students"
    ]
    df = ensure_columns_v49(df, required_cols)

    tab_add, tab_edit = st.tabs(["Add New University", "Edit Existing Universities"])

    with tab_add:
        st.markdown("### Add New University")
        with st.form("add_university_v49"):
            c1, c2 = st.columns(2)
            with c1:
                university = st.text_input("University Name")
                location = st.text_input("Location")
                region = st.text_input("Region")
                homepage = st.text_input("Homepage")
                phone = st.text_input("Representative Phone")
                fax = st.text_input("Representative Fax")
                school_size = st.text_input("School Size")
                intl_students = st.text_input("Foreign / International Students")
            with c2:
                address = st.text_area("Address", height=92)
                overview = st.text_area("Overview", height=120)
                intake = st.text_input("Intake", value="March, September")
                tuition_range = st.text_input("Tuition Range")
                scholarship_info = st.text_input("Scholarship Info")
                top_majors = st.text_area("Top Majors / Summary", height=80)
                application_status = st.selectbox("Application Status", ["Open", "Closed"], key="add_app_status_v61")
                application_deadline = st.text_input("Application Deadline Optional")
                maps_url = st.text_input("Google Maps URL or Address Optional")
                country_students = st.text_area("Country-wise Students e.g. Nepal:500; Vietnam:200", height=70)
                photo = st.file_uploader("University Photo", type=["png","jpg","jpeg"], key="add_uni_photo_v49")

            submitted = st.form_submit_button("Add University", use_container_width=True)
            if submitted:
                if not university.strip():
                    st.error("University Name is required.")
                elif university.strip() in df["University"].astype(str).str.strip().tolist():
                    st.error("This university already exists. Please use Edit Existing Universities.")
                else:
                    image_path = save_uploaded_university_photo_v49(photo, university)
                    new_row = {
                        "University": university.strip(),
                        "Location": location.strip(),
                        "Total_Students": school_size.strip(),
                        "International_Students": intl_students.strip(),
                        "Top_Majors": top_majors.strip(),
                        "Intake": intake.strip(),
                        "Tuition_Range": tuition_range.strip(),
                        "Scholarship_Info": scholarship_info.strip(),
                        "Overview": overview.strip(),
                        "Image": image_path,
                        "Homepage": homepage.strip(),
                        "Address": address.strip(),
                        "Representative_Phone": phone.strip(),
                        "Representative_Fax": fax.strip(),
                        "Region": region.strip(),
                        "School_Size": school_size.strip(),
                        "Total_Students": school_size.strip(),
                        "Application_Status": application_status,
                        "Application_Deadline": application_deadline.strip(),
                        "Maps_URL": maps_url.strip(),
                        "Country_Students": country_students.strip(),
                    }
                    df2 = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)
                    write_csv(uni_file, df2)
                    reload_data_v49()
                    st.success(f"{university} has been added.")
                    st.rerun()

    with tab_edit:
        st.markdown("### Edit Existing Universities")
        if len(df) == 0:
            st.info("No universities found.")
        else:
            selected = st.selectbox("Select University to Edit", df["University"].dropna().tolist(), key="edit_uni_select_v49")
            idx = df.index[df["University"] == selected][0]
            row = df.loc[idx]

            with st.form("edit_university_v49"):
                c1, c2 = st.columns(2)
                with c1:
                    university = st.text_input("University Name", value=display_clean_v50(row.get("University", "")))
                    location = st.text_input("Location", value=display_clean_v50(row.get("Location", "")))
                    region = st.text_input("Region", value=display_clean_v50(row.get("Region", "")))
                    homepage = st.text_input("Homepage", value=display_clean_v50(row.get("Homepage", "")))
                    phone = st.text_input("Representative Phone", value=display_clean_v50(row.get("Representative_Phone", "")))
                    fax = st.text_input("Representative Fax", value=display_clean_v50(row.get("Representative_Fax", "")))
                    school_size = st.text_input("School Size", value=display_clean_v50(row.get("School_Size", "")))
                    intl_students = st.text_input("Foreign / International Students", value=display_clean_v50(row.get("International_Students", "")))
                with c2:
                    address = st.text_area("Address", value=display_clean_v50(row.get("Address", "")), height=92)
                    overview = st.text_area("Overview", value=display_clean_v50(row.get("Overview", "")), height=120)
                    intake = st.text_input("Intake", value=display_clean_v50(row.get("Intake", "")))
                    tuition_range = st.text_input("Tuition Range", value=display_clean_v50(row.get("Tuition_Range", "")))
                    scholarship_info = st.text_input("Scholarship Info", value=display_clean_v50(row.get("Scholarship_Info", "")))
                    top_majors = st.text_area("Top Majors / Summary", value=display_clean_v50(row.get("Top_Majors", "")), height=80)
                    current_status = display_clean_v50(row.get("Application_Status", "Open")) or "Open"
                    application_status = st.selectbox("Application Status", ["Open", "Closed"], index=0 if current_status != "Closed" else 1, key="edit_app_status_v61")
                    application_deadline = st.text_input("Application Deadline Optional", value=display_clean_v50(row.get("Application_Deadline", "")))
                    maps_url = st.text_input("Google Maps URL or Address Optional", value=display_clean_v50(row.get("Maps_URL", "")))
                    country_students = st.text_area("Country-wise Students e.g. Nepal:500; Vietnam:200", value=display_clean_v50(row.get("Country_Students", "")), height=70)
                    current_img = st.text_input("Current Image Path", value=display_clean_v50(row.get("Image", "")))
                    photo = st.file_uploader("Upload New Photo", type=["png","jpg","jpeg"], key="edit_uni_photo_v49")

                b1, b2 = st.columns(2)
                save_clicked = b1.form_submit_button("Save Changes", use_container_width=True)
                delete_clicked = b2.form_submit_button("Delete University", use_container_width=True)

                if save_clicked:
                    image_path = save_uploaded_university_photo_v49(photo, university) if photo else current_img
                    df.loc[idx, "University"] = university.strip()
                    df.loc[idx, "Location"] = location.strip()
                    df.loc[idx, "Region"] = region.strip()
                    df.loc[idx, "Homepage"] = homepage.strip()
                    df.loc[idx, "Address"] = address.strip()
                    df.loc[idx, "Representative_Phone"] = phone.strip()
                    df.loc[idx, "Representative_Fax"] = fax.strip()
                    df.loc[idx, "School_Size"] = school_size.strip()
                    df.loc[idx, "Total_Students"] = school_size.strip()
                    df.loc[idx, "International_Students"] = intl_students.strip()
                    df.loc[idx, "Overview"] = overview.strip()
                    df.loc[idx, "Intake"] = intake.strip()
                    df.loc[idx, "Tuition_Range"] = tuition_range.strip()
                    df.loc[idx, "Scholarship_Info"] = scholarship_info.strip()
                    df.loc[idx, "Top_Majors"] = top_majors.strip()
                    df.loc[idx, "Application_Status"] = application_status
                    df.loc[idx, "Application_Deadline"] = application_deadline.strip()
                    df.loc[idx, "Maps_URL"] = maps_url.strip()
                    df.loc[idx, "Country_Students"] = country_students.strip()
                    df.loc[idx, "Image"] = image_path
                    write_csv(uni_file, df)
                    reload_data_v49()
                    st.success("University information saved.")
                    st.rerun()

                if delete_clicked:
                    df = df[df["University"] != selected].copy()
                    write_csv(uni_file, df)
                    reload_data_v49()
                    st.warning(f"{selected} has been deleted.")
                    st.rerun()

            st.markdown("### Current University Data")
            st.dataframe(clean_df_v50(df), use_container_width=True, hide_index=True)

    close_shell()


def admin_criteria_management_v49():
    dash_shell(["Admin Dashboard","Partner Management","Universities","Eligibility Rules","Tuition Rules","Scholarship Rules","Applications"])
    st.subheader("Program, Eligibility Criteria & Tuition Management")
    st.caption("Add or edit majors, criteria, application fee, admission fee, and tuition by university/program.")

    criteria_file = DATA / "admission_criteria.csv"
    df = read_csv(criteria_file)
    required_cols = [
        "University","Program","Major","Minimum_GPA","Minimum_IELTS","Minimum_TOEFL_iBT",
        "Minimum_New_TOEFL","Minimum_TOPIK","Application_Fee_KRW","Admission_Fee_KRW",
        "Tuition_Fee_Per_Semester_KRW","IELTS_Criteria","GPA_Criteria"
    ]
    df = ensure_columns_v49(df, required_cols)

    universities_df = read_csv(DATA / "universities.csv")
    university_options = sorted(universities_df["University"].dropna().unique().tolist()) if len(universities_df) else sorted(df["University"].dropna().unique().tolist())
    program_options = ["Undergraduate", "Graduate", "Korean Language Program"]

    tab_add, tab_edit = st.tabs(["Add New Major / Criteria", "Edit Existing Criteria"])

    with tab_add:
        with st.form("add_criteria_v49"):
            c1, c2, c3 = st.columns(3)
            with c1:
                university = st.selectbox("University", university_options, key="add_crit_uni_v49") if university_options else st.text_input("University")
                program = st.selectbox("Program", program_options, key="add_crit_program_v49")
                major = st.text_input("Major / Department")
                min_gpa = st.text_input("Minimum GPA / Percentage")
            with c2:
                min_ielts = st.text_input("Minimum IELTS")
                min_toefl = st.text_input("Minimum TOEFL iBT")
                min_new_toefl = st.text_input("Minimum New TOEFL")
                min_topik = st.text_input("Minimum TOPIK")
            with c3:
                app_fee = st.text_input("Application Fee KRW")
                adm_fee = st.text_input("Admission Fee KRW")
                tuition = st.text_input("Tuition Fee Per Semester KRW")
                ielts_criteria = st.text_input("Language Criteria Text")
                gpa_criteria = st.text_input("GPA Criteria Text")

            submitted = st.form_submit_button("Add Major / Criteria", use_container_width=True)
            if submitted:
                if not str(university).strip() or not major.strip():
                    st.error("University and Major are required.")
                else:
                    new_row = {
                        "University": str(university).strip(),
                        "Program": program,
                        "Major": major.strip(),
                        "Minimum_GPA": min_gpa.strip(),
                        "Minimum_IELTS": min_ielts.strip(),
                        "Minimum_TOEFL_iBT": min_toefl.strip(),
                        "Minimum_New_TOEFL": min_new_toefl.strip(),
                        "Minimum_TOPIK": min_topik.strip(),
                        "Application_Fee_KRW": app_fee.strip(),
                        "Admission_Fee_KRW": adm_fee.strip(),
                        "Tuition_Fee_Per_Semester_KRW": tuition.strip(),
                        "IELTS_Criteria": ielts_criteria.strip(),
                        "GPA_Criteria": gpa_criteria.strip(),
                    }
                    df2 = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)
                    write_csv(criteria_file, df2)
                    reload_data_v49()
                    st.success("New major / criteria added.")
                    st.rerun()

    with tab_edit:
        if len(df) == 0:
            st.info("No criteria found.")
        else:
            df = df.reset_index(drop=True)
            labels = [f"{i} | {r.get('University','')} | {r.get('Program','')} | {r.get('Major','')}" for i, r in df.iterrows()]
            selected_label = st.selectbox("Select Row to Edit", labels, key="edit_crit_row_v49")
            idx = int(selected_label.split(" | ")[0])
            row = df.loc[idx]

            with st.form("edit_criteria_v49"):
                c1, c2, c3 = st.columns(3)
                with c1:
                    university = st.text_input("University", value=display_clean_v50(row.get("University", "")))
                    program = st.selectbox("Program", program_options, index=program_options.index(row.get("Program")) if row.get("Program") in program_options else 0)
                    major = st.text_input("Major / Department", value=display_clean_v50(row.get("Major", "")))
                    min_gpa = st.text_input("Minimum GPA / Percentage", value=display_clean_v50(row.get("Minimum_GPA", "")))
                with c2:
                    min_ielts = st.text_input("Minimum IELTS", value=display_clean_v50(row.get("Minimum_IELTS", "")))
                    min_toefl = st.text_input("Minimum TOEFL iBT", value=display_clean_v50(row.get("Minimum_TOEFL_iBT", "")))
                    min_new_toefl = st.text_input("Minimum New TOEFL", value=display_clean_v50(row.get("Minimum_New_TOEFL", "")))
                    min_topik = st.text_input("Minimum TOPIK", value=display_clean_v50(row.get("Minimum_TOPIK", "")))
                with c3:
                    app_fee = st.text_input("Application Fee KRW", value=display_clean_v50(row.get("Application_Fee_KRW", "")))
                    adm_fee = st.text_input("Admission Fee KRW", value=display_clean_v50(row.get("Admission_Fee_KRW", "")))
                    tuition = st.text_input("Tuition Fee Per Semester KRW", value=display_clean_v50(row.get("Tuition_Fee_Per_Semester_KRW", "")))
                    ielts_criteria = st.text_input("Language Criteria Text", value=display_clean_v50(row.get("IELTS_Criteria", "")))
                    gpa_criteria = st.text_input("GPA Criteria Text", value=display_clean_v50(row.get("GPA_Criteria", "")))

                b1, b2 = st.columns(2)
                save_clicked = b1.form_submit_button("Save Criteria", use_container_width=True)
                delete_clicked = b2.form_submit_button("Delete Criteria", use_container_width=True)

                if save_clicked:
                    updates = {
                        "University": university.strip(),
                        "Program": program,
                        "Major": major.strip(),
                        "Minimum_GPA": min_gpa.strip(),
                        "Minimum_IELTS": min_ielts.strip(),
                        "Minimum_TOEFL_iBT": min_toefl.strip(),
                        "Minimum_New_TOEFL": min_new_toefl.strip(),
                        "Minimum_TOPIK": min_topik.strip(),
                        "Application_Fee_KRW": app_fee.strip(),
                        "Admission_Fee_KRW": adm_fee.strip(),
                        "Tuition_Fee_Per_Semester_KRW": tuition.strip(),
                        "IELTS_Criteria": ielts_criteria.strip(),
                        "GPA_Criteria": gpa_criteria.strip(),
                    }
                    for k, v in updates.items():
                        df.loc[idx, k] = v
                    write_csv(criteria_file, df)
                    reload_data_v49()
                    st.success("Criteria saved.")
                    st.rerun()

                if delete_clicked:
                    df = df.drop(idx).reset_index(drop=True)
                    write_csv(criteria_file, df)
                    reload_data_v49()
                    st.warning("Criteria deleted.")
                    st.rerun()

            st.dataframe(clean_df_v50(df), use_container_width=True, hide_index=True)

    close_shell()


def admin_scholarship_management_v49():
    dash_shell(["Admin Dashboard","Partner Management","Universities","Eligibility Rules","Tuition Rules","Scholarship Rules","Applications"])
    st.subheader("Scholarship Rule Management")
    st.caption("Add or edit scholarship rules by university and program.")

    sch_file = DATA / "scholarship_rules.csv"
    df = read_csv(sch_file)
    required_cols = [
        "University","Program_Rule","Language_Criteria","Scholarship_Text",
        "Scholarship_Percent","IELTS_Min","TOEFL_iBT_Min","New_TOEFL_Min","TOPIK_Min"
    ]
    df = ensure_columns_v49(df, required_cols)

    universities_df = read_csv(DATA / "universities.csv")
    university_options = sorted(universities_df["University"].dropna().unique().tolist()) if len(universities_df) else sorted(df["University"].dropna().unique().tolist())
    program_options = ["Undergraduate", "Graduate", "Korean Language Program", "All"]

    tab_add, tab_edit = st.tabs(["Add Scholarship Rule", "Edit Scholarship Rules"])

    with tab_add:
        with st.form("add_scholarship_v49"):
            c1, c2, c3 = st.columns(3)
            with c1:
                university = st.selectbox("University", university_options, key="add_sch_uni_v49") if university_options else st.text_input("University")
                program = st.selectbox("Program Rule", program_options, key="add_sch_program_v49")
                criteria_text = st.text_area("Scholarship Criteria Text", height=90)
            with c2:
                scholarship_text = st.text_input("Scholarship Text", placeholder="e.g., 50% of Tuition fee")
                scholarship_percent = st.text_input("Scholarship Percent", placeholder="e.g., 50")
                ielts_min = st.text_input("IELTS Min")
            with c3:
                toefl_min = st.text_input("TOEFL iBT Min")
                new_toefl_min = st.text_input("New TOEFL Min")
                topik_min = st.text_input("TOPIK Min")

            submitted = st.form_submit_button("Add Scholarship Rule", use_container_width=True)
            if submitted:
                if not str(university).strip():
                    st.error("University is required.")
                else:
                    new_row = {
                        "University": str(university).strip(),
                        "Program_Rule": program,
                        "Language_Criteria": criteria_text.strip(),
                        "Scholarship_Text": scholarship_text.strip(),
                        "Scholarship_Percent": scholarship_percent.strip(),
                        "IELTS_Min": ielts_min.strip(),
                        "TOEFL_iBT_Min": toefl_min.strip(),
                        "New_TOEFL_Min": new_toefl_min.strip(),
                        "TOPIK_Min": topik_min.strip(),
                    }
                    df2 = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)
                    df2.fillna("").replace(["nan", "NaN", "None", "null", "<NA>"], "").to_csv(sch_file, index=False, encoding="utf-8-sig")
                    reload_data_v49()
                    st.success("Scholarship rule added.")
                    st.rerun()

    with tab_edit:
        if len(df) == 0:
            st.info("No scholarship rules found.")
        else:
            df = df.reset_index(drop=True)
            labels = [f"{i} | {r.get('University','')} | {r.get('Program_Rule','')} | {r.get('Language_Criteria','')}" for i, r in df.iterrows()]
            selected_label = st.selectbox("Select Scholarship Rule", labels, key="edit_sch_row_v49")
            idx = int(selected_label.split(" | ")[0])
            row = df.loc[idx]

            with st.form("edit_scholarship_v49"):
                c1, c2, c3 = st.columns(3)
                with c1:
                    university = st.text_input("University", value=display_clean_v50(row.get("University", "")))
                    program = st.selectbox("Program Rule", program_options, index=program_options.index(row.get("Program_Rule")) if row.get("Program_Rule") in program_options else 0)
                    criteria_text = st.text_area("Scholarship Criteria Text", value=display_clean_v50(row.get("Language_Criteria", "")), height=90)
                with c2:
                    scholarship_text = st.text_input("Scholarship Text", value=display_clean_v50(row.get("Scholarship_Text", "")))
                    scholarship_percent = st.text_input("Scholarship Percent", value=display_clean_v50(row.get("Scholarship_Percent", "")))
                    ielts_min = st.text_input("IELTS Min", value=display_clean_v50(row.get("IELTS_Min", "")))
                with c3:
                    toefl_min = st.text_input("TOEFL iBT Min", value=display_clean_v50(row.get("TOEFL_iBT_Min", "")))
                    new_toefl_min = st.text_input("New TOEFL Min", value=display_clean_v50(row.get("New_TOEFL_Min", "")))
                    topik_min = st.text_input("TOPIK Min", value=display_clean_v50(row.get("TOPIK_Min", "")))

                b1, b2 = st.columns(2)
                save_clicked = b1.form_submit_button("Save Scholarship Rule", use_container_width=True)
                delete_clicked = b2.form_submit_button("Delete Scholarship Rule", use_container_width=True)

                if save_clicked:
                    updates = {
                        "University": university.strip(),
                        "Program_Rule": program,
                        "Language_Criteria": criteria_text.strip(),
                        "Scholarship_Text": scholarship_text.strip(),
                        "Scholarship_Percent": scholarship_percent.strip(),
                        "IELTS_Min": ielts_min.strip(),
                        "TOEFL_iBT_Min": toefl_min.strip(),
                        "New_TOEFL_Min": new_toefl_min.strip(),
                        "TOPIK_Min": topik_min.strip(),
                    }
                    for k, v in updates.items():
                        df.loc[idx, k] = v
                    df.fillna("").replace(["nan", "NaN", "None", "null", "<NA>"], "").to_csv(sch_file, index=False, encoding="utf-8-sig")
                    reload_data_v49()
                    st.success("Scholarship rule saved.")
                    st.rerun()

                if delete_clicked:
                    df = df.drop(idx).reset_index(drop=True)
                    df.fillna("").replace(["nan", "NaN", "None", "null", "<NA>"], "").to_csv(sch_file, index=False, encoding="utf-8-sig")
                    reload_data_v49()
                    st.warning("Scholarship rule deleted.")
                    st.rerun()

            st.dataframe(clean_df_v50(df), use_container_width=True, hide_index=True)

    close_shell()



# ============================================================
# v61 University filters, map, program apply, and online application
# ============================================================
from urllib.parse import quote_plus

def number_from_text_v61(value):
    text = str(value or "")
    m = re.search(r"([0-9][0-9,]*)", text)
    if not m:
        return 0
    try:
        return int(m.group(1).replace(",", ""))
    except Exception:
        return 0

def application_status_v61(u):
    for key in ["Application_Status", "Applications_Open", "Application_Open", "Status"]:
        val = str(u.get(key, "")).strip()
        if val:
            if val.lower() in ["open", "opened", "yes", "true", "receiving", "available"]:
                return "Open"
            if val.lower() in ["closed", "no", "false", "not receiving", "not available"]:
                return "Closed"
            return val
    return "Open"

def scholarship_max_percent_v61(university):
    df = scholarship_rules()
    if df is None or len(df) == 0 or "University" not in df.columns:
        return 0
    sub = df[df["University"].astype(str).str.lower() == str(university).lower()]
    vals = []
    for _, r in sub.iterrows():
        for key in ["Scholarship_Percent", "Scholarship_Text"]:
            text_val = str(r.get(key, ""))
            nums = re.findall(r"([0-9]+(?:\.[0-9]+)?)", text_val)
            for n in nums:
                try:
                    f = float(n)
                    if 0 < f <= 1:
                        f *= 100
                    if f <= 100:
                        vals.append(f)
                except Exception:
                    pass
    return int(max(vals)) if vals else 0

def map_embed_v61(u):
    maps_url = str(u.get("Maps_URL", "") or u.get("Google_Maps_URL", "")).strip()
    if maps_url and "google" in maps_url.lower() and "output=embed" in maps_url:
        src = maps_url
    else:
        query = maps_url or str(u.get("Address", "") or u.get("Location", "") or u.get("University", ""))
        src = f"https://maps.google.com/maps?q={quote_plus(query)}&output=embed"
    return f"""
    <div class="map-box-v61">
      <iframe src="{src}" loading="lazy" referrerpolicy="no-referrer-when-downgrade"></iframe>
    </div>
    """

def country_flags_html_v61(u):
    raw = str(u.get("Country_Students", "") or u.get("Country_Wise_Students", "") or "").strip()
    flags = {"Nepal":"🇳🇵","Vietnam":"🇻🇳","China":"🇨🇳","India":"🇮🇳","Bangladesh":"🇧🇩",
             "Sri Lanka":"🇱🇰","Myanmar":"🇲🇲","Mongolia":"🇲🇳","Uzbekistan":"🇺🇿",
             "Pakistan":"🇵🇰","Indonesia":"🇮🇩","Korea":"🇰🇷"}
    if not raw:
        return '<div class="country-list-v61"><span>🌏 Country-wise student data can be added by Admin.</span></div>'
    items = []
    for part in re.split(r"[;\n,]+", raw):
        if ":" in part:
            country, count = part.split(":", 1)
        elif "-" in part:
            country, count = part.split("-", 1)
        else:
            continue
        country = country.strip()
        count = count.strip()
        flag = flags.get(country, "🌐")
        items.append(f"<div><b>{flag} {country}</b><span>{count}</span></div>")
    if not items:
        return '<div class="country-list-v61"><span>🌏 Country-wise student data can be added by Admin.</span></div>'
    return '<div class="country-list-v61">' + ''.join(items) + '</div>'

def student_pie_html_v61(u):
    total = number_from_text_v61(u.get("School_Size", "")) or number_from_text_v61(u.get("Total_Students", ""))
    intl = number_from_text_v61(u.get("International_Students", ""))
    if total <= 0:
        return """
        <div class="student-chart-v61">
          <div class="pie-v61" style="background:#E5E7EB;"></div>
          <div><b>Student Composition</b><span>Total student data can be added by Admin.</span></div>
        </div>
        """
    intl = min(intl, total)
    domestic = max(total - intl, 0)
    pct = int((intl / total) * 100) if total else 0
    return f"""
    <div class="student-chart-v61">
      <div class="pie-v61" style="background: conic-gradient(#005BDB 0 {pct}%, #DCE6F4 {pct}% 100%);"></div>
      <div>
        <b>Student Composition</b>
        <span>International: {intl:,} ({pct}%)</span>
        <span>Domestic/Other: {domestic:,}</span>
        <span>Total: {total:,}</span>
      </div>
    </div>
    """

def program_details_html_v61(row):
    req = str(row.get("IELTS_Criteria", "") or row.get("Minimum_IELTS", "") or "Not provided")
    gpa = str(row.get("GPA_Criteria", "") or row.get("Minimum_GPA", "") or "Not provided")
    app_fee = money_text(row.get("Application_Fee_KRW", ""))
    adm_fee = money_text(row.get("Admission_Fee_KRW", ""))
    tuition = money_text(row.get("Tuition_Fee_Per_Semester_KRW", row.get("Tuition_KRW", "")))
    return f"""
    <div class="program-detail-v61">
      <div><b>Major / Department</b><span>{row.get("Major","")}</span></div>
      <div><b>Language Requirement</b><span>{req}</span></div>
      <div><b>GPA / Academic Requirement</b><span>{gpa}</span></div>
      <div><b>Application Fee</b><span>{app_fee}</span></div>
      <div><b>Admission Fee</b><span>{adm_fee}</span></div>
      <div><b>Tuition / Semester</b><span>{tuition}</span></div>
    </div>
    """

def set_application_context_v61(university, program, major):
    st.session_state.application_university = university
    st.session_state.application_program = program
    st.session_state.application_major = major
    set_page("Application Form")

def upload_to_local_v61(uploaded, application_id, label):
    if uploaded is None:
        return ""
    out_dir = BASE / "applications_uploads" / application_id
    out_dir.mkdir(parents=True, exist_ok=True)
    safe_label = re.sub(r"[^a-z0-9_]+", "_", label.lower()).strip("_")
    safe_name = re.sub(r"[^A-Za-z0-9_.-]+", "_", uploaded.name)
    out_path = out_dir / f"{safe_label}_{safe_name}"
    out_path.write_bytes(uploaded.getbuffer())
    return str(out_path.relative_to(BASE)).replace("\\", "/")

def universities_page(public=False):
    if public:
        header()
        st.markdown('<div class="universities-wrap-v32">', unsafe_allow_html=True)
    else:
        dash_shell(["Dashboard","Universities","Eligibility Check","Tuition & Scholarship","Contact Us"])
        st.markdown('<div class="universities-wrap-v32">', unsafe_allow_html=True)

    st.title("Universities Information")
    df = universities().copy()
    if df is None or len(df) == 0:
        st.warning("No university data found.")
        if public:
            footer()
        else:
            close_shell()
        return

    df["__status"] = df.apply(application_status_v61, axis=1)
    df["__scholarship_max"] = df["University"].apply(scholarship_max_percent_v61)

    st.markdown('<div class="filter-panel-v61">', unsafe_allow_html=True)
    c1, c2, c3, c4 = st.columns([1.4, 1.1, 1.1, 1.2])
    with c1:
        search = st.text_input("Search universities by name, location, or major", key="uni_search_v61")
    with c2:
        locations = ["All"] + sorted([x for x in df.get("Location", pd.Series(dtype=str)).dropna().astype(str).unique().tolist() if x.strip()])
        selected_location = st.selectbox("Location / City", locations, key="uni_location_filter_v61")
    with c3:
        status_filter = st.selectbox("Application Status", ["All", "Open", "Closed"], key="uni_status_filter_v61")
    with c4:
        sort_mode = st.selectbox("Sort By", ["Default", "Scholarship High to Low", "University A-Z"], key="uni_sort_v61")
    st.markdown('</div>', unsafe_allow_html=True)

    if search:
        s = search.lower()
        df = df[df.apply(lambda r: s in " ".join(map(str, r.values)).lower(), axis=1)]
    if selected_location != "All" and "Location" in df.columns:
        df = df[df["Location"].astype(str) == selected_location]
    if status_filter != "All":
        df = df[df["__status"].astype(str).str.lower() == status_filter.lower()]
    if sort_mode == "Scholarship High to Low":
        df = df.sort_values("__scholarship_max", ascending=False)
    elif sort_mode == "University A-Z":
        df = df.sort_values("University")

    for _, u in df.iterrows():
        status = application_status_v61(u)
        status_class = "open-v61" if status.lower() == "open" else "closed-v61"
        scholarship_max = scholarship_max_percent_v61(u["University"])
        image_html = asset_img_html(u.get("Image", ""), "uni-wide-v32")

        st.markdown(f"""
        <div class="uni-card-v32 uni-card-extra-v61">
          {image_html}
          <div class="uni-body-v32">
            <div class="uni-title-row-v61">
              <div>
                <h2>{u['University']}</h2>
                <p class="uni-overview-v32">{u.get('Overview','')}</p>
              </div>
              <div class="status-area-v61">
                <span class="status-badge-v61 {status_class}">{status}</span>
                <span class="scholarship-badge-v61">Max scholarship {scholarship_max}%</span>
              </div>
            </div>
            <div class="info-grid-v61">
              <div><b>Location</b><span>{u.get('Location','')}</span></div>
              <div><b>Region</b><span>{u.get('Region','')}</span></div>
              <div><b>School Size</b><span>{u.get('School_Size', u.get('Total_Students',''))}</span></div>
              <div><b>Foreign Students</b><span>{u.get('International_Students','')}</span></div>
              <div><b>Homepage</b><span>{u.get('Homepage','')}</span></div>
              <div><b>Application</b><span>{status}</span></div>
            </div>
            {student_pie_html_v61(u)}
            <h3 class="subhead-v61">Country-wise Student Numbers</h3>
            {country_flags_html_v61(u)}
            <h3 class="subhead-v61">Location View</h3>
            {map_embed_v61(u)}
          </div>
        </div>
        """, unsafe_allow_html=True)

        prog_df = criteria()
        prog_df = prog_df[prog_df["University"].astype(str) == str(u["University"])]
        with st.expander(f"Available departments/programs and application options for {u['University']}", expanded=False):
            if len(prog_df) == 0:
                st.info("No program/department data has been added by Admin yet.")
            else:
                for program_name in sorted(prog_df["Program"].dropna().astype(str).unique()):
                    st.markdown(f"### {program_name}")
                    rows = prog_df[prog_df["Program"].astype(str) == program_name]
                    for i, (_, r) in enumerate(rows.iterrows()):
                        st.markdown(program_details_html_v61(r), unsafe_allow_html=True)
                        if status.lower() == "open":
                            if st.button(f"Apply - {r.get('Major','')}", key=f"apply_v61_{u['University']}_{program_name}_{i}", use_container_width=True):
                                set_application_context_v61(u["University"], program_name, r.get("Major",""))
                        else:
                            st.button(f"Application Closed - {r.get('Major','')}", key=f"closed_v61_{u['University']}_{program_name}_{i}", disabled=True, use_container_width=True)

    if public:
        st.markdown('</div>', unsafe_allow_html=True)
        footer()
    else:
        st.markdown('</div>', unsafe_allow_html=True)
        close_shell()

def application_form_v61():
    if not st.session_state.logged_in:
        header()
        st.markdown('<div class="section"><div class="white-panel"><h2>Partner Access Required</h2><p>Please login with an approved partner account to submit applications.</p></div></div>', unsafe_allow_html=True)
        footer()
        return

    dash_shell(["Dashboard","Universities","Eligibility Check","Tuition & Scholarship","Contact Us"])
    st.subheader("Online Application Submission")

    uni = st.session_state.get("application_university", "")
    program = st.session_state.get("application_program", "")
    major = st.session_state.get("application_major", "")

    st.markdown(f"""
    <div class="application-head-v61">
      <h2>{uni}</h2>
      <p>{program} · {major}</p>
      <span>Application status: Open</span>
    </div>
    """, unsafe_allow_html=True)

    with st.form("application_form_v61"):
        st.markdown("### 1. Student Basic Information")
        c1, c2, c3 = st.columns(3)
        with c1:
            student_name = st.text_input("Student Full Name")
            dob = st.date_input("Date of Birth")
            passport = st.text_input("Passport Number")
            home_contact = st.text_input("Home Country Contact Number")
        with c2:
            student_email = st.text_input("Student Email Address")
            sub_agent_email = st.text_input("Sub-agent / Submitting Agent Email Optional")
            submission_type = st.selectbox("Submission Type", ["Self", st.session_state.agency_name or "Partner", "KIEC", "Realize Education", "Etc."])
            application_level = st.selectbox("Application Level", ["Korean Language Program D4-1", "EAP D4-7", "Undergraduate", "Master", "PhD"])
        with c3:
            high_school_name = st.text_input("High School Name For Undergraduate")
            previous_university = st.text_input("Graduated University Name For Master/PhD")
            passout_year = st.text_input("Passout / Graduation Date YYYY/MM/DD")
            enrolled_period = st.text_input("Enrolled Period YYYY/MM/DD ~ YYYY/MM/DD")

        st.markdown("### 2. Family and Financial Information")
        c4, c5, c6 = st.columns(3)
        with c4:
            family_name = st.text_input("One Family Member Name")
        with c5:
            family_contact = st.text_input("Family Member Contact Number")
        with c6:
            family_occupation = st.text_input("Family Member Occupation")

        st.markdown("### 3. Statement")
        self_intro = st.text_area("Self Introduction Around 500 Words", height=160)
        study_plan = st.text_area("Study Plan Around 500 Words", height=160)

        st.markdown("### 4. Required Attachments")
        st.info("PDF/JPG/PNG accepted. Samples can be added later as downloadable templates.")
        f1, f2, f3 = st.columns(3)
        with f1:
            photo = st.file_uploader("PP Size Photo JPG/PNG", type=["jpg","jpeg","png"])
            passport_file = st.file_uploader("Passport Copy PDF/JPG/PNG", type=["pdf","jpg","jpeg","png"])
            hs_cert = st.file_uploader("High School Certificate PDF", type=["pdf"])
        with f2:
            hs_transcript = st.file_uploader("High School Transcript PDF", type=["pdf"])
            language_cert = st.file_uploader("IELTS/TOEFL/TOPIK Certificate PDF", type=["pdf"])
            family_rel = st.file_uploader("Family Relationship Certificate PDF", type=["pdf"])
        with f3:
            family_id = st.file_uploader("Family Members ID Card Copy Notarized PDF", type=["pdf"])
            bank_cert = st.file_uploader("Bank Certificate PDF", type=["pdf"])
            cv_file = st.file_uploader("CV PDF For Master/PhD", type=["pdf"])
            embassy_docs = st.file_uploader("Embassy Verified / Apostille Academic Documents PDF", type=["pdf"])

        notes = st.text_area("Additional Notes Optional")
        submitted = st.form_submit_button("Submit Application", use_container_width=True)

        if submitted:
            if not student_name.strip() or not passport.strip() or not student_email.strip():
                st.error("Student name, passport number, and student email are required.")
            else:
                app_id = "APP" + datetime.now().strftime("%Y%m%d%H%M%S")
                saved = {
                    "photo_file": upload_to_local_v61(photo, app_id, "photo"),
                    "passport_file": upload_to_local_v61(passport_file, app_id, "passport"),
                    "high_school_certificate_file": upload_to_local_v61(hs_cert, app_id, "high_school_certificate"),
                    "high_school_transcript_file": upload_to_local_v61(hs_transcript, app_id, "high_school_transcript"),
                    "language_certificate_file": upload_to_local_v61(language_cert, app_id, "language_certificate"),
                    "family_relationship_certificate_file": upload_to_local_v61(family_rel, app_id, "family_relationship"),
                    "family_id_cards_file": upload_to_local_v61(family_id, app_id, "family_id_cards"),
                    "bank_certificate_file": upload_to_local_v61(bank_cert, app_id, "bank_certificate"),
                    "cv_file": upload_to_local_v61(cv_file, app_id, "cv"),
                    "embassy_verified_documents_file": upload_to_local_v61(embassy_docs, app_id, "embassy_verified_docs"),
                }
                row = {
                    "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "application_id": app_id,
                    "status": "Submitted",
                    "submitted_by": st.session_state.username,
                    "partner_agency": st.session_state.agency_name,
                    "university": uni,
                    "program": program,
                    "major": major,
                    "student_name": student_name.strip(),
                    "date_of_birth": str(dob),
                    "passport_number": passport.strip(),
                    "application_level": application_level,
                    "previous_university": previous_university.strip(),
                    "high_school_name": high_school_name.strip(),
                    "passout_year": passout_year.strip(),
                    "enrolled_period": enrolled_period.strip(),
                    "home_country_contact": home_contact.strip(),
                    "student_email": student_email.strip(),
                    "sub_agent_email": sub_agent_email.strip(),
                    "submission_type": submission_type,
                    "family_member_name": family_name.strip(),
                    "family_member_contact": family_contact.strip(),
                    "family_member_occupation": family_occupation.strip(),
                    "self_introduction": self_intro.strip(),
                    "study_plan": study_plan.strip(),
                    "notes": notes.strip(),
                }
                row.update(saved)
                add_row(APPLICATIONS, row)
                st.success(f"Application submitted successfully. Application ID: {app_id}")

    close_shell()

def admin_applications_v61():
    dash_shell(["Admin Dashboard","Partner Management","Universities","Eligibility Rules","Tuition Rules","Scholarship Rules","Applications"])
    st.subheader("Submitted Applications")
    apps = read_csv(APPLICATIONS)
    if apps is None or len(apps) == 0:
        st.info("No applications have been submitted yet.")
    else:
        st.dataframe(apps.sort_values("timestamp", ascending=False), use_container_width=True, hide_index=True)
    close_shell()

# Routing
if not st.session_state.logged_in:
    if st.session_state.page == "Partner Sign Up": signup()
    elif st.session_state.page == "Pending": pending()
    elif st.session_state.page == "Login": login()
    elif st.session_state.page == "Universities": universities_page(public=True)
    elif st.session_state.page == "Contact Us": contact()
    elif st.session_state.page == "Application Form":
        application_form_v61()
    elif st.session_state.page in ["Eligibility Check","Tuition & Scholarship"]:
        header()
        st.markdown('<div class="section"><div class="white-panel"><h2>Partner Access Required</h2><p>Please login with an approved partner account to access this feature.</p></div></div>', unsafe_allow_html=True)
        a1, a2, a3 = st.columns([1,1,4])
        with a1:
            if st.button("Go to Login", key="access_login", use_container_width=True): set_page("Login")
        with a2:
            if st.button("Partner Sign Up", key="access_signup", use_container_width=True): set_page("Partner Sign Up")
        footer()
    else:
        home()
else:
    if st.session_state.role == "admin":
        if st.session_state.page == "Partner Management":
            admin_partner_management_v58()
        elif st.session_state.page == "Universities":
            admin_university_management_v49()
        elif st.session_state.page == "Eligibility Rules":
            admin_criteria_edit_v48()
        elif st.session_state.page == "Tuition Rules":
            admin_tuition_edit_v48()
        elif st.session_state.page == "Scholarship Rules":
            admin_scholarship_edit_v48()
        elif st.session_state.page == "Applications":
            admin_applications_v61()
        else:
            admin()
    else:
        if st.session_state.page == "Universities": universities_page()
        elif st.session_state.page == "Eligibility Check": eligibility()
        elif st.session_state.page == "Tuition & Scholarship": tuition()
        elif st.session_state.page == "Contact Us": contact()
        elif st.session_state.page == "Application Form": application_form_v61()
        else:
            partner_dashboard()
