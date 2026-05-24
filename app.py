
import streamlit as st
import textwrap
import pandas as pd
import json, hashlib, base64, re, os, hmac, re
from pathlib import Path
from datetime import datetime
from io import BytesIO
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
DATABASE_URL_KEY = "DATABASE_URL"

CSV_TABLE_MAP = {
    "universities.csv": "universities",
    "admission_criteria.csv": "admission_criteria",
    "scholarship_rules.csv": "scholarship_rules",
    "eligibility_logs.csv": "eligibility_logs",
    "tuition_logs.csv": "tuition_logs",
    "inquiries.csv": "inquiries",
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
    raw = str(name or "").lower().strip()
    # v76: aliases so Realize / Realize Education and KIEC variants match correctly.
    if "realize" in raw:
        return "realize_education"
    if "kiec" in raw:
        return "kiec"
    base = re.sub(r"[^a-z0-9]+", "_", raw).strip("_")
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



def official_agency_options_v77():
    """
    Organizations shown in signup.
    v82: includes official representative agencies and approved sub-partner agencies,
    so staff of Edukorea or other approved partner agencies can select their own organization.
    """
    defaults = ["KIEC", "Realize Education"]
    try:
        users = read_json(USERS)
        orgs = []
        for u in users:
            if str(u.get("status", "")) == "approved" and str(u.get("role", "")) in ["agency_rep", "agency_partner"]:
                name = str(u.get("agency_name", "") or u.get("company_name", "") or u.get("partner_group", "")).strip()
                if name and name not in orgs:
                    orgs.append(name)
        for x in orgs:
            if x not in defaults:
                defaults.append(x)
    except Exception:
        pass
    return defaults

def official_rep_badge_v77(agency_name):
    return f'<span class="official-rep-badge-v77">⭐ Official Representative</span>'

def approval_agency_id_v77(user):
    return normalize_agency_id(
        user.get("sponsor_agency_id", "")
        or user.get("official_representative", "")
        or user.get("requested_approver_agency_id", "")
        or user.get("agency_id", "")
        or user.get("agency_name", "")
        or user.get("partner_group", "")
    )

def user_approval_group_matches_v77(user, current_key):
    candidates = [
        user.get("sponsor_agency_id", ""),
        user.get("official_representative", ""),
        user.get("requested_approver_agency_id", ""),
        user.get("partner_group", ""),
        user.get("agency_id", ""),
        user.get("agency_name", ""),
    ]
    return any(normalize_agency_id(x) == normalize_agency_id(current_key) for x in candidates if str(x).strip())



def approve_or_reject_partner_request_v80(req, new_status):
    """
    v80: Official representative approval fix.
    For partner agencies, the applicant's own agency_id is their company name,
    so we must approve by sponsor/official representative group, not by applicant agency_id.
    """
    current_key = normalize_agency_id(current_agency_id() or st.session_state.get("agency_name", ""))
    req_username = str(req.get("username", "")).strip()
    req_email = str(req.get("email", "")).strip()

    all_users = read_json(USERS)
    changed = False
    affected_agency_ids = set()

    for u in all_users:
        same_user = (
            str(u.get("username", "")).strip() == req_username
            and (not req_email or str(u.get("email", "")).strip() == req_email)
        )
        if same_user and user_approval_group_matches_v77(u, current_key):
            u["status"] = new_status
            u["approved_by"] = st.session_state.get("username", "")
            u["approved_at"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            u["approved_by_agency"] = st.session_state.get("agency_name", "")
            changed = True
            if str(u.get("role", "")) == "agency_partner":
                affected_agency_ids.add(normalize_agency_id(u.get("agency_id", u.get("agency_name", ""))))

    write_json(USERS, all_users)

    # If the request is a partner agency, also update the agency list status.
    if affected_agency_ids:
        agencies = read_agencies()
        for a in agencies:
            if normalize_agency_id(a.get("agency_id", a.get("agency_name", ""))) in affected_agency_ids:
                a["status"] = new_status
                a["approved_by"] = st.session_state.get("username", "")
                a["approved_at"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                a["approved_by_agency"] = st.session_state.get("agency_name", "")
                if not a.get("agency_logo"):
                    for u in all_users:
                        if normalize_agency_id(u.get("agency_id", u.get("agency_name", ""))) == normalize_agency_id(a.get("agency_id", a.get("agency_name", ""))) and u.get("agency_logo"):
                            a["agency_logo"] = u.get("agency_logo")
                            break
        write_agencies(agencies)

    st.cache_data.clear()
    return changed


def get_current_user():
    if not st.session_state.get("username"):
        return None
    return find_user(st.session_state.username)

def current_agency_id():
    user = get_current_user()
    if not user:
        return ""
    return user.get("agency_id", normalize_agency_id(user.get("agency_name","")))



def approved_reps_for_agency_v75(agency_id):
    reps = []
    target = normalize_agency_id(agency_id)
    for u in read_json(USERS):
        user_agency_id = normalize_agency_id(u.get("agency_id", u.get("agency_name", "")))
        user_agency_name_id = normalize_agency_id(u.get("agency_name", ""))
        user_company_id = normalize_agency_id(u.get("company_name", ""))
        if (
            (user_agency_id == target or user_agency_name_id == target or user_company_id == target)
            and str(u.get("role", "")) in ["agency_rep", "agency_partner"]
            and str(u.get("status", "")) == "approved"
        ):
            reps.append(u)
    return reps


def approval_authority_text_v75(user):
    agency_name = str(user.get("official_representative", "") or user.get("partner_group", "") or user.get("agency_name", "your agency") or "your agency")
    approval_id = approval_agency_id_v77(user)
    if str(user.get("approval_scope", "")) == "agency" and approved_reps_for_agency_v75(approval_id):
        return f"the official representative of {agency_name}"
    return "the portal super admin"



def _make_pending_token_v76(user):
    """Signed token for preserving pending-user message across top-nav clicks."""
    try:
        data = f'{user.get("username","")}|{user.get("password_hash","")}|{user.get("status","")}|{user.get("agency_id","")}|{user.get("email","")}'
        secret = get_database_url()
        sig = hmac.new(secret.encode("utf-8"), data.encode("utf-8"), hashlib.sha256).hexdigest()[:40]
        return f'{user.get("username","")}:{sig}'
    except Exception:
        return ""

def _verify_pending_token_v76(token):
    try:
        username, sig = str(token).split(":", 1)
        user = find_user(username)
        if not user or str(user.get("status","")) == "approved":
            return None
        expected = _make_pending_token_v76(user).split(":", 1)[1]
        if hmac.compare_digest(sig, expected):
            return user
    except Exception:
        return None
    return None

def _current_pending_token_v76():
    token = ""
    try:
        token = st.query_params.get("pending", "")
    except Exception:
        token = ""
    if isinstance(token, list):
        token = token[0] if token else ""
    if token:
        return token
    username = st.session_state.get("pending_username", "")
    if username:
        user = find_user(username)
        if user:
            return _make_pending_token_v76(user)
    return ""

def restore_pending_from_query_v76():
    if st.session_state.get("pending_username"):
        return
    try:
        token = st.query_params.get("pending", "")
    except Exception:
        token = ""
    if isinstance(token, list):
        token = token[0] if token else ""
    if token:
        user = _verify_pending_token_v76(token)
        if user:
            set_pending_session_v75(user, update_query=False)


def set_pending_session_v75(user, update_query=True):
    st.session_state.pending_username = user.get("username", "")
    st.session_state.pending_full_name = user.get("full_name", user.get("username", ""))
    st.session_state.pending_agency_name = user.get("agency_name", user.get("partner_group", ""))
    st.session_state.pending_email = user.get("email", "")
    st.session_state.pending_role = user.get("role", "")
    st.session_state.pending_account_type = user.get("account_type", "")
    st.session_state.pending_approval_by = approval_authority_text_v75(user)
    if update_query:
        try:
            st.query_params["pending"] = _make_pending_token_v76(user)
        except Exception:
            pass


def pending_user_from_session_v75():
    username = st.session_state.get("pending_username", "")
    if username:
        user = find_user(username)
        if user:
            return user
    return {
        "username": st.session_state.get("pending_username", ""),
        "full_name": st.session_state.get("pending_full_name", ""),
        "agency_name": st.session_state.get("pending_agency_name", ""),
        "email": st.session_state.get("pending_email", ""),
        "role": st.session_state.get("pending_role", ""),
        "account_type": st.session_state.get("pending_account_type", ""),
    }


def pending_access_required_v75(feature_name="this service"):
    header()
    user = pending_user_from_session_v75()
    full_name = str(user.get("full_name", "Partner") or "Partner")
    agency_name = str(user.get("agency_name", "your agency") or "your agency")
    approver = approval_authority_text_v75(user)
    st.markdown(f"""
    <div class="pending-access-card-v75">
        <div class="pending-pill-v75">Approval Pending</div>
        <h1>Dear {full_name},</h1>
        <p>You will only be able to use <b>{feature_name}</b> after your account is approved by <b>{approver}</b>.</p>
        <p class="pending-muted-v75">Your selected partner agency is <b>{agency_name}</b>. If this is incorrect, please create a new account or contact the portal administrator.</p>
    </div>
    """, unsafe_allow_html=True)
    a1, a2, a3 = st.columns([1.1,1.2,4])
    with a1:
        if st.button("Go to Login", key=f"pending_access_login_{feature_name}", use_container_width=True):
            set_page("Login")
    with a2:
        if st.button("View Pending Status", key=f"pending_access_status_{feature_name}", use_container_width=True):
            set_page("Pending")
    footer()

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
if "auth_token" not in st.session_state: st.session_state.auth_token = ""
restore_pending_from_query_v76()


# v110: If a user clicks a university program card link, keep them on Universities page.
# Without this, the app can route to Home after query-param navigation.
def handle_program_detail_query_v110():
    try:
        uni_q = st.query_params.get("uni", "")
        prog_q = st.query_params.get("programdetail", "")
    except Exception:
        uni_q, prog_q = "", ""
    if isinstance(uni_q, list):
        uni_q = uni_q[0] if uni_q else ""
    if isinstance(prog_q, list):
        prog_q = prog_q[0] if prog_q else ""
    if uni_q and prog_q:
        try:
            from urllib.parse import unquote_plus
            st.session_state.selected_uni_v62 = unquote_plus(str(uni_q))
            st.session_state.selected_program_v109 = unquote_plus(str(prog_q))
        except Exception:
            st.session_state.selected_uni_v62 = str(uni_q)
            st.session_state.selected_program_v109 = str(prog_q)
        st.session_state.page = "Universities"

handle_program_detail_query_v110()



def _set_login_session_from_user_v60(user):
    st.session_state.logged_in = True
    st.session_state.username = user["username"]
    st.session_state.role = user["role"]
    st.session_state.agency_name = user.get("agency_name", "")
    st.session_state.agency_id = user.get("agency_id", normalize_agency_id(user.get("agency_name", "")))
    st.session_state.full_name = user.get("full_name", "")
    st.session_state.account_type = user.get("account_type", user.get("role", ""))
    try:
        st.session_state.auth_token = _make_auth_token_v60(user)
    except Exception:
        st.session_state.auth_token = ""

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
    """
    v104: Restore login from auth query parameter or saved session token.
    This prevents users/admin from being logged out when clicking HTML navigation links.
    """
    if st.session_state.get("logged_in"):
        return
    try:
        token = st.query_params.get("auth", "")
    except Exception:
        token = ""
    if isinstance(token, list):
        token = token[0] if token else ""
    if not token:
        token = st.session_state.get("auth_token", "") or ""
    if token:
        user = _verify_auth_token_v60(token)
        if user:
            _set_login_session_from_user_v60(user)
            try:
                st.query_params["auth"] = _make_auth_token_v60(user)
            except Exception:
                pass
            if st.session_state.page in ["Home", "Login", "Partner Sign Up"]:
                st.session_state.page = "Admin Dashboard" if user["role"] == "admin" else "Dashboard"


restore_login_from_query_v60()


# v69: HTML hero buttons use query parameters, so this connects them to Streamlit pages.
def handle_home_query_navigation_v69():
    try:
        go = st.query_params.get("go", "")
    except Exception:
        go = ""
    if isinstance(go, list):
        go = go[0] if go else ""
    if go == "signup":
        st.session_state.page = "Partner Sign Up"
        try:
            del st.query_params["go"]
        except Exception:
            pass
    elif go == "universities":
        st.session_state.page = "Universities"
        try:
            del st.query_params["go"]
        except Exception:
            pass

handle_home_query_navigation_v69()


# v70: Top navigation uses HTML links styled like the reference image.
def handle_top_nav_query_v70():
    restore_pending_from_query_v76()
    try:
        nav = st.query_params.get("nav", "")
    except Exception:
        nav = ""
    if isinstance(nav, list):
        nav = nav[0] if nav else ""

    nav_map = {
        "home": "Home",
        "universities": "Universities",
        "eligibility": "Eligibility Check",
        "tuition": "Tuition & Scholarship",
        "contact": "Contact Us",
        "mou": "Contact Us",
        "login": "Login",
        "signup": "Partner Sign Up",
    }
    if nav in nav_map:
        requested_page = nav_map[nav]
        # v110: Program detail links use nav=Universities + uni/programdetail.
        # Keep the page as Universities and let handle_program_detail_query_v110 select the program.
        if st.session_state.get("logged_in") and requested_page in ["Home", "Login", "Partner Sign Up"]:
            requested_page = "Admin Dashboard" if st.session_state.get("role") == "admin" else "Dashboard"
        st.session_state.page = requested_page
        try:
            del st.query_params["nav"]
        except Exception:
            pass

handle_top_nav_query_v70()



def auth_query_suffix_v104(prefix="&"):
    """Append auth token to HTML links when logged in."""
    try:
        token = st.session_state.get("auth_token", "") or st.query_params.get("auth", "")
    except Exception:
        token = st.session_state.get("auth_token", "")
    if isinstance(token, list):
        token = token[0] if token else ""
    if st.session_state.get("logged_in") and token:
        return f"{prefix}auth={token}"
    return ""


# v96: Dashboard navigation uses HTML links so the active page can be styled blue.
def handle_dash_nav_query_v96():
    try:
        dashnav = st.query_params.get("dashnav", "")
    except Exception:
        dashnav = ""
    if isinstance(dashnav, list):
        dashnav = dashnav[0] if dashnav else ""

    if not dashnav:
        return

    if dashnav == "Logout":
        for k in ["logged_in","role","username","agency_name","agency_id","full_name","account_type","auth_token"]:
            st.session_state[k] = False if k == "logged_in" else None
        try:
            st.query_params.clear()
        except Exception:
            pass
        st.session_state.page = "Home"
        return

    allowed_pages = [
        "Admin Dashboard",
        "Partner Management",
        "Universities",
        "Eligibility Rules",
        "Tuition Rules",
        "Scholarship Rules",
        "Dashboard",
        "Eligibility Check",
        "Tuition & Scholarship",
        "Contact Us",
    ]
    if dashnav in allowed_pages:
        st.session_state.page = dashnav
        # keep auth query param, remove only dashnav
        try:
            del st.query_params["dashnav"]
        except Exception:
            pass

handle_dash_nav_query_v96()





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


/* v61 University filter panel */
.filter-panel-v61 {
    background: #FFFFFF;
    border: 1px solid #DCE6F4;
    border-radius: 18px;
    padding: 18px 18px 6px 18px;
    margin: 16px 0 18px 0;
    box-shadow: 0 10px 26px rgba(16,24,40,.05);
}
.filter-summary-v61 {
    background: #F6F8FC;
    border: 1px solid #E3EAF5;
    border-radius: 12px;
    padding: 12px 16px;
    margin: 10px 0 18px 0;
    color: #101828 !important;
}
.filter-summary-v61 span {
    color: #667085 !important;
    margin-left: 8px;
}
.uni-title-row-v61 {
    display: flex;
    justify-content: space-between;
    gap: 20px;
    align-items: flex-start;
}
.uni-badges-v61 {
    min-width: 220px;
    display: flex;
    flex-direction: column;
    gap: 8px;
}
.uni-badges-v61 span {
    display: inline-flex;
    justify-content: center;
    align-items: center;
    background: #EEF5FF;
    color: #002B5B !important;
    border: 1px solid #CFE0FF;
    border-radius: 999px;
    padding: 8px 12px;
    font-weight: 800;
    font-size: 13px;
    text-align: center;
}
@media(max-width:900px){
    .uni-title-row-v61 {
        flex-direction: column;
    }
    .uni-badges-v61 {
        width: 100%;
        min-width: 0;
    }
}


/* v62 summary/detail card corrections */
.uni-summary-card-v62 {
    background:#FFFFFF;
    border:1px solid #DCE6F4;
    border-radius:18px;
    overflow:hidden;
    margin:20px 0 8px 0;
    box-shadow:0 10px 26px rgba(16,24,40,.06);
}
.uni-summary-photo-v62 {
    width:100%!important;
    height:260px!important;
    object-fit:cover!important;
    object-position:center!important;
    display:block!important;
    border:0!important;
    border-radius:0!important;
    margin:0!important;
}
.uni-summary-body-v62 {
    padding:24px 28px 26px 28px;
}
.uni-summary-body-v62 h3 {
    margin:0 0 10px 0!important;
    color:#101828!important;
    font-size:28px!important;
}
.uni-summary-body-v62 p {
    color:#344054!important;
    margin:0 0 16px 0!important;
}
.uni-summary-meta-v62 {
    display:flex;
    flex-wrap:wrap;
    gap:10px;
}
.uni-summary-meta-v62 span {
    background:#F6F8FC;
    border:1px solid #DCE6F4;
    border-radius:999px;
    padding:8px 12px;
    font-weight:700;
    color:#002B5B!important;
}
.detail-card-v62 {
    margin-top:14px!important;
}


/* v63 application status badge colors */
.app-status-open-v63 {
    background:#16A34A !important;
    color:#FFFFFF !important;
    border-color:#15803D !important;
    -webkit-text-fill-color:#FFFFFF !important;
}
.app-status-closed-v63 {
    background:#DC2626 !important;
    color:#FFFFFF !important;
    border-color:#B91C1C !important;
    -webkit-text-fill-color:#FFFFFF !important;
}
.app-status-soon-v63 {
    background:#FACC15 !important;
    color:#111827 !important;
    border-color:#EAB308 !important;
    -webkit-text-fill-color:#111827 !important;
}
.app-status-none-v63 {
    background:#E5E7EB !important;
    color:#374151 !important;
    border-color:#D1D5DB !important;
    -webkit-text-fill-color:#374151 !important;
}


/* v64 program badges for university detail area */
.program-badge-v64 {
    background:#EEF5FF !important;
    color:#002B5B !important;
    border:1px solid #CFE0FF !important;
    -webkit-text-fill-color:#002B5B !important;
}


/* v66 auto-linked application date/status helper */
.app-status-open-v63 {
    background:#16A34A !important;
    color:#FFFFFF !important;
    border-color:#15803D !important;
    -webkit-text-fill-color:#FFFFFF !important;
}
.app-status-closed-v63 {
    background:#DC2626 !important;
    color:#FFFFFF !important;
    border-color:#B91C1C !important;
    -webkit-text-fill-color:#FFFFFF !important;
}
.app-status-soon-v63 {
    background:#FACC15 !important;
    color:#111827 !important;
    border-color:#EAB308 !important;
    -webkit-text-fill-color:#111827 !important;
}


/* v67 program badges */
.program-badge-v64 {
    display:inline-flex;
    justify-content:center;
    align-items:center;
    background:#EEF5FF;
    color:#002B5B !important;
    border:1px solid #CFE0FF;
    border-radius:999px;
    padding:8px 12px;
    font-weight:800;
    font-size:13px;
    text-align:center;
}


/* v69 reference-style home hero */
.hero-reference-v69 {
    min-height: 500px !important;
    background-color: #002B5B !important;
    background-size: cover !important;
    background-position: center right !important;
    position: relative !important;
    overflow: hidden !important;
    display: flex !important;
    align-items: center !important;
    margin: 0 !important;
    border-radius: 0 !important;
}
.hero-reference-v69::before {
    content:"";
    position:absolute;
    inset:0;
    background:
      radial-gradient(circle at 22% 16%, rgba(0,91,219,.22), transparent 28%),
      linear-gradient(90deg, rgba(0,30,70,.78), rgba(0,30,70,.28) 62%, rgba(0,30,70,.05));
    z-index:1;
    pointer-events:none;
}
.hero-dots-v69 {
    position:absolute;
    left: 420px;
    top: 22px;
    width: 390px;
    height: 210px;
    opacity:.22;
    background-image: radial-gradient(rgba(255,255,255,.85) 1.35px, transparent 1.35px);
    background-size: 13px 13px;
    mask-image: radial-gradient(ellipse at center, #000 45%, transparent 76%);
    -webkit-mask-image: radial-gradient(ellipse at center, #000 45%, transparent 76%);
    z-index:2;
}
.hero-inner-v69 {
    position:relative !important;
    z-index:3 !important;
    margin-left:56px !important;
    width:min(720px, 52vw) !important;
}
.hero-step-v69 {
    display:inline-flex !important;
    align-items:center !important;
    gap:10px !important;
    background:rgba(255,255,255,.13) !important;
    border:1px solid rgba(255,255,255,.24) !important;
    border-radius:999px !important;
    padding:7px 15px !important;
    margin-bottom:18px !important;
    backdrop-filter:blur(4px);
}
.hero-step-v69 span {
    background:rgba(255,255,255,.18) !important;
    color:#FFFFFF !important;
    -webkit-text-fill-color:#FFFFFF !important;
    border-radius:999px !important;
    padding:2px 10px !important;
    font-size:12px !important;
    font-weight:900 !important;
}
.hero-step-v69 b {
    color:#FFFFFF !important;
    -webkit-text-fill-color:#FFFFFF !important;
    font-size:13px !important;
    letter-spacing:.2px !important;
}
.hero-reference-v69 h1,
.hero-reference-v69 h1 *,
.hero-inner-v69 h1,
.hero-inner-v69 h1 * {
    color:#FFFFFF !important;
    -webkit-text-fill-color:#FFFFFF !important;
    font-size:54px !important;
    line-height:1.14 !important;
    font-weight:950 !important;
    margin:0 0 20px 0 !important;
    letter-spacing:-.65px !important;
    text-shadow:0 3px 20px rgba(0,0,0,.28) !important;
}
.hero-lead-v69 {
    color:rgba(255,255,255,.96) !important;
    -webkit-text-fill-color:rgba(255,255,255,.96) !important;
    font-size:17px !important;
    line-height:1.55 !important;
    max-width:640px !important;
    margin:0 0 18px 0 !important;
    text-shadow:0 2px 12px rgba(0,0,0,.22) !important;
}
.hero-buttons-v69 {
    display:flex !important;
    gap:18px !important;
    align-items:center !important;
    margin:18px 0 16px 0 !important;
    flex-wrap:wrap !important;
}
.hero-buttons-v69 a {
    display:inline-flex !important;
    align-items:center !important;
    justify-content:center !important;
    min-width:235px !important;
    height:54px !important;
    border-radius:7px !important;
    font-weight:900 !important;
    font-size:15px !important;
    text-decoration:none !important;
    box-shadow:0 14px 28px rgba(0,0,0,.18) !important;
    transition:all .16s ease !important;
}
.hero-btn-primary-v69 {
    background:#005BDB !important;
    border:1px solid #005BDB !important;
    color:#FFFFFF !important;
    -webkit-text-fill-color:#FFFFFF !important;
}
.hero-btn-outline-v69 {
    background:rgba(255,255,255,.07) !important;
    border:1px solid rgba(255,255,255,.76) !important;
    color:#FFFFFF !important;
    -webkit-text-fill-color:#FFFFFF !important;
    backdrop-filter:blur(3px);
}
.hero-buttons-v69 a:hover {
    transform:translateY(-1px) !important;
    filter:brightness(1.07) !important;
}
.hero-lock-v69 {
    color:rgba(255,255,255,.95) !important;
    -webkit-text-fill-color:rgba(255,255,255,.95) !important;
    font-size:14px !important;
    font-weight:800 !important;
    margin:0 !important;
    text-shadow:0 2px 10px rgba(0,0,0,.25) !important;
}
.featured-v32 {
    padding-top: 28px !important;
}
@media(max-width:1000px){
    .hero-reference-v69 {
        min-height:560px !important;
        background-position:center !important;
    }
    .hero-inner-v69 {
        margin-left:28px !important;
        margin-right:28px !important;
        width:auto !important;
    }
    .hero-reference-v69 h1,
    .hero-inner-v69 h1 {
        font-size:40px !important;
    }
    .hero-buttons-v69 {
        flex-direction:column !important;
        align-items:stretch !important;
        max-width:320px !important;
    }
    .hero-buttons-v69 a {
        width:100% !important;
        min-width:0 !important;
    }
}


/* v70 reference-style top navigation */
.top-nav-reference-v70 {
    width: 100% !important;
    min-height: 68px !important;
    background: #FFFFFF !important;
    border-bottom: 1px solid #E7EEF8 !important;
    display: flex !important;
    align-items: center !important;
    justify-content: space-between !important;
    padding: 0 34px !important;
    margin: 0 !important;
    box-sizing: border-box !important;
    position: relative !important;
    z-index: 200 !important;
}
.nav-left-v70,
.nav-right-v70 {
    display: flex !important;
    align-items: center !important;
    gap: 34px !important;
}
.nav-right-v70 {
    gap: 16px !important;
}
.nav-link-v70 {
    color: #101828 !important;
    -webkit-text-fill-color: #101828 !important;
    text-decoration: none !important;
    font-weight: 850 !important;
    font-size: 15px !important;
    line-height: 68px !important;
    height: 68px !important;
    display: inline-flex !important;
    align-items: center !important;
    position: relative !important;
}
.nav-link-v70:hover {
    color: #005BDB !important;
    -webkit-text-fill-color: #005BDB !important;
}
.nav-link-v70.active {
    color: #005BDB !important;
    -webkit-text-fill-color: #005BDB !important;
}
.nav-link-v70.active::after {
    content: "" !important;
    position: absolute !important;
    left: 0 !important;
    right: 0 !important;
    bottom: 0 !important;
    height: 3px !important;
    background: #005BDB !important;
    border-radius: 999px 999px 0 0 !important;
}
.nav-login-v70,
.nav-signup-v70 {
    height: 46px !important;
    min-width: 112px !important;
    padding: 0 22px !important;
    border-radius: 7px !important;
    display: inline-flex !important;
    align-items: center !important;
    justify-content: center !important;
    text-decoration: none !important;
    font-size: 15px !important;
    font-weight: 900 !important;
    box-sizing: border-box !important;
}
.nav-login-v70 {
    background: #FFFFFF !important;
    color: #101828 !important;
    -webkit-text-fill-color: #101828 !important;
    border: 1px solid #AEB8C8 !important;
}
.nav-login-v70:hover {
    background: #F8FAFC !important;
    color: #005BDB !important;
    -webkit-text-fill-color: #005BDB !important;
    border-color: #005BDB !important;
}
.nav-signup-v70 {
    background: #005BDB !important;
    color: #FFFFFF !important;
    -webkit-text-fill-color: #FFFFFF !important;
    border: 1px solid #005BDB !important;
    min-width: 188px !important;
}
.nav-signup-v70:hover {
    background: #004FC0 !important;
    color: #FFFFFF !important;
    -webkit-text-fill-color: #FFFFFF !important;
    border-color: #004FC0 !important;
}
@media(max-width:1100px){
    .top-nav-reference-v70 {
        padding: 10px 20px !important;
        min-height: auto !important;
        flex-direction: column !important;
        align-items: stretch !important;
        gap: 12px !important;
    }
    .nav-left-v70 {
        gap: 18px !important;
        overflow-x: auto !important;
        white-space: nowrap !important;
        padding-bottom: 2px !important;
    }
    .nav-link-v70 {
        height: 42px !important;
        line-height: 42px !important;
        font-size: 14px !important;
    }
    .nav-right-v70 {
        justify-content: flex-end !important;
    }
}


/* v71 program-specific application date cards */
.uni-badges-v61 {
    min-width: 300px !important;
}
.program-date-card-v71 {
    background:#F6F8FC !important;
    border:1px solid #DCE6F4 !important;
    border-radius:14px !important;
    padding:10px 12px !important;
    display:flex !important;
    flex-direction:column !important;
    gap:6px !important;
    color:#101828 !important;
}
.program-date-card-v71 b {
    color:#002B5B !important;
    font-size:13px !important;
    font-weight:900 !important;
}
.program-date-card-v71 span {
    border-radius:999px !important;
    padding:7px 10px !important;
    text-align:center !important;
    font-weight:900 !important;
    font-size:12px !important;
}
.program-date-card-v71 small {
    color:#475467 !important;
    font-size:12px !important;
    font-weight:700 !important;
}
.uni-summary-meta-v62 .program-date-card-v71 {
    min-width: 210px !important;
}


/* v72 admin button color fix: blue boxes with bold white text */
div[data-testid="stFormSubmitButton"] button,
div[data-testid="stFormSubmitButton"] button[kind="secondary"],
div[data-testid="stFormSubmitButton"] button[kind="primary"] {
    background: #005BDB !important;
    color: #FFFFFF !important;
    -webkit-text-fill-color: #FFFFFF !important;
    border: 1px solid #005BDB !important;
    border-radius: 10px !important;
    font-weight: 900 !important;
    box-shadow: 0 8px 18px rgba(0,91,219,.18) !important;
}
div[data-testid="stFormSubmitButton"] button *,
div[data-testid="stFormSubmitButton"] button p,
div[data-testid="stFormSubmitButton"] button span {
    color: #FFFFFF !important;
    -webkit-text-fill-color: #FFFFFF !important;
    font-weight: 900 !important;
}
div[data-testid="stFormSubmitButton"] button:hover {
    background: #004FC0 !important;
    border-color: #004FC0 !important;
    color: #FFFFFF !important;
    -webkit-text-fill-color: #FFFFFF !important;
}

/* v72 regular admin action buttons: keep readable */
.admin-action-blue-v72 .stButton > button,
div[data-testid="stButton"] button[title="Save Changes"],
div[data-testid="stButton"] button[title="Delete University"] {
    background: #005BDB !important;
    color: #FFFFFF !important;
    -webkit-text-fill-color: #FFFFFF !important;
    font-weight: 900 !important;
}


/* v72 upload button readability */
section[data-testid="stFileUploader"] button {
    background: #FFFFFF !important;
    color: #101828 !important;
    -webkit-text-fill-color: #101828 !important;
    font-weight: 800 !important;
}
section[data-testid="stFileUploader"] button * {
    color: #101828 !important;
    -webkit-text-fill-color: #101828 !important;
}


/* v73 premium admin dashboard */
.admin-title-row-v73 {
    display:flex;
    align-items:flex-start;
    gap:18px;
    margin: 6px 0 20px 0;
}
.admin-step-pill-v73 {
    background:#005BDB;
    color:#FFFFFF !important;
    -webkit-text-fill-color:#FFFFFF !important;
    border-radius:8px;
    padding:13px 23px;
    font-weight:950;
    box-shadow:0 8px 18px rgba(0,91,219,.25);
}
.admin-title-row-v73 h1 {
    margin:0 !important;
    color:#101828 !important;
    font-size:31px !important;
    font-weight:950 !important;
}
.admin-title-row-v73 p {
    margin:5px 0 0 0 !important;
    color:#475467 !important;
    font-weight:700 !important;
}
.admin-stats-grid-v73 {
    display:grid;
    grid-template-columns:repeat(5,minmax(0,1fr));
    gap:14px;
    margin:14px 0 22px 0;
}
.admin-stat-card-v73 {
    background:#FFFFFF;
    border:1px solid #DCE6F4;
    border-radius:14px;
    padding:18px 18px 16px 18px;
    box-shadow:0 8px 20px rgba(16,24,40,.05);
}
.admin-stat-card-v73 b {
    color:#344054 !important;
    font-size:13px;
}
.admin-stat-card-v73 h2 {
    color:#005BDB !important;
    margin:8px 0 3px 0 !important;
    font-size:32px !important;
    font-weight:950 !important;
}
.admin-stat-card-v73 p {
    color:#667085 !important;
    margin:0 !important;
    font-size:12px !important;
    font-weight:700 !important;
}
.stat-icon-v73 {
    width:36px;
    height:36px;
    border-radius:50%;
    background:#EEF5FF;
    display:flex;
    align-items:center;
    justify-content:center;
    margin-bottom:10px;
}
.admin-stat-card-v73.warning-v73 h2 {color:#B54708 !important;}
.admin-stat-card-v73.success-v73 h2 {color:#067647 !important;}
.admin-panel-v73, .admin-side-panel-v73, .admin-rules-card-v73 {
    background:#FFFFFF;
    border:1px solid #DCE6F4;
    border-radius:16px;
    padding:18px 20px;
    box-shadow:0 10px 24px rgba(16,24,40,.06);
    margin-bottom:14px;
}
.admin-panel-head-v73 {
    display:flex;
    justify-content:space-between;
    align-items:flex-start;
    gap:12px;
}
.admin-panel-head-v73 h2, .admin-side-panel-v73 h2, .admin-rules-card-v73 h2 {
    margin:0 0 5px 0 !important;
    color:#101828 !important;
    font-size:19px !important;
    font-weight:950 !important;
}
.admin-panel-head-v73 p, .admin-side-panel-v73 p, .admin-rules-card-v73 p {
    margin:0 !important;
    color:#667085 !important;
    font-weight:650 !important;
}
.admin-badge-yellow-v73 {
    background:#FFF4D6;
    color:#B54708 !important;
    -webkit-text-fill-color:#B54708 !important;
    border-radius:999px;
    padding:8px 13px;
    font-weight:950;
}
.approval-card-premium-v73 {
    background:#FFFFFF;
    border:1px solid #DCE6F4;
    border-radius:16px;
    padding:18px 20px;
    box-shadow:0 8px 20px rgba(16,24,40,.05);
    margin:12px 0 10px 0;
}
.approval-card-top-v73 {
    display:flex;
    justify-content:space-between;
    align-items:center;
    gap:12px;
    margin-bottom:12px;
}
.approval-card-top-v73 h3 {
    margin:0 !important;
    color:#002B5B !important;
    font-size:23px !important;
    font-weight:950 !important;
}
.approval-grid-v73 {
    display:grid;
    grid-template-columns:repeat(2,minmax(0,1fr));
    gap:10px;
}
.approval-grid-v73 div {
    background:#F6F8FC;
    border:1px solid #E3EAF5;
    border-radius:12px;
    padding:12px 14px;
}
.approval-grid-v73 b {
    display:block;
    color:#002B5B !important;
    margin-bottom:5px;
    font-size:13px;
}
.approval-grid-v73 span {
    color:#101828 !important;
    font-weight:700;
    word-break:break-word;
}
.approval-action-gap-v73 {
    height:14px;
}
.admin-empty-card-v73 {
    background:#FFFFFF;
    border:1px dashed #C9D4E5;
    border-radius:16px;
    padding:26px;
    margin:12px 0 20px 0;
    text-align:center;
}
.admin-empty-card-v73 h3 {
    color:#101828 !important;
    margin:0 0 8px 0 !important;
}
.admin-empty-card-v73 p {
    color:#667085 !important;
    margin:0 !important;
}
.admin-panel-margin-v73 {
    margin-top:22px;
}
.status-row-v73 {
    display:flex;
    align-items:center;
    gap:10px;
    background:#F6F8FC;
    border:1px solid #E3EAF5;
    border-radius:12px;
    padding:12px 13px;
    margin:10px 0;
}
.status-row-v73 b {
    flex:1;
    color:#101828 !important;
}
.status-row-v73 em {
    font-style:normal;
    background:#FFFFFF;
    color:#002B5B !important;
    border:1px solid #DCE6F4;
    border-radius:8px;
    padding:4px 9px;
    font-weight:950;
}
.dot {
    width:11px;
    height:11px;
    border-radius:50%;
    display:inline-block;
}
.dot.yellow {background:#F7C948;}
.dot.green {background:#12B76A;}
.dot.red {background:#F04438;}
.dot.blue {background:#005BDB;}
.quick-row-v73 {
    background:#F6F8FC;
    border:1px solid #E3EAF5;
    border-radius:12px;
    padding:12px 13px;
    margin:9px 0;
}
.quick-row-v73 b {
    display:block;
    color:#002B5B !important;
    margin-bottom:3px;
}
.quick-row-v73 span {
    color:#667085 !important;
    font-weight:650;
}
.admin-bottom-features-v73 {
    display:grid;
    grid-template-columns:repeat(4,minmax(0,1fr));
    gap:14px;
    margin:26px 0 4px 0;
    background:#EEF5FF;
    border:1px solid #DCE6F4;
    border-radius:16px;
    padding:18px 20px;
}
.admin-bottom-features-v73 div {
    display:flex;
    align-items:center;
    gap:12px;
}
.admin-bottom-features-v73 span {
    background:#FFFFFF;
    color:#005BDB !important;
    border-radius:50%;
    width:42px;
    height:42px;
    display:flex;
    align-items:center;
    justify-content:center;
    font-size:20px;
}
.admin-bottom-features-v73 b {
    display:block;
    color:#101828 !important;
}
.admin-bottom-features-v73 p {
    margin:2px 0 0 0 !important;
    color:#667085 !important;
    font-size:12px !important;
}
.main .stButton>button,
div[data-testid="stFormSubmitButton"] button {
    background:#005BDB !important;
    color:#FFFFFF !important;
    -webkit-text-fill-color:#FFFFFF !important;
    border:1px solid #005BDB !important;
    border-radius:10px !important;
    font-weight:950 !important;
}
.main .stButton>button *,
div[data-testid="stFormSubmitButton"] button * {
    color:#FFFFFF !important;
    -webkit-text-fill-color:#FFFFFF !important;
    font-weight:950 !important;
}
@media(max-width:1100px){
    .admin-stats-grid-v73,.admin-bottom-features-v73{grid-template-columns:1fr 1fr;}
    .approval-grid-v73{grid-template-columns:1fr;}
}
@media(max-width:700px){
    .admin-stats-grid-v73,.admin-bottom-features-v73{grid-template-columns:1fr;}
}


/* v74 university-wise admin rule editor */
.university-filter-panel-v74 {
    background:#FFFFFF;
    border:1px solid #DCE6F4;
    border-radius:16px;
    padding:16px 18px 6px 18px;
    box-shadow:0 8px 20px rgba(16,24,40,.05);
    margin:16px 0 14px 0;
}
.selected-university-banner-v74 {
    background:#EEF5FF;
    border:1px solid #CFE0FF;
    border-radius:14px;
    padding:14px 16px;
    margin:12px 0 16px 0;
    display:flex;
    flex-direction:column;
    gap:4px;
}
.selected-university-banner-v74 b {
    color:#002B5B !important;
    font-size:20px !important;
    font-weight:950 !important;
}
.selected-university-banner-v74 span {
    color:#475467 !important;
    font-weight:700 !important;
}
/* Make data editor easier to read where browser theme turns it too dark */
div[data-testid="stDataFrame"],
div[data-testid="stDataEditor"] {
    border-radius:14px !important;
    overflow:hidden !important;
}


/* v75 pending approval and agency representative approval panel */
.pending-hero-v75 {background: linear-gradient(90deg,#002B5B,#053B7A);border-radius:0 0 22px 22px;padding:54px 56px;margin:0 0 28px 0;}
.pending-hero-v75 * { color:#FFFFFF !important; -webkit-text-fill-color:#FFFFFF !important; }
.pending-step-v75 {display:inline-block;background:rgba(255,255,255,.16);border:1px solid rgba(255,255,255,.28);border-radius:999px;padding:8px 16px;font-weight:900;margin-bottom:16px;}
.pending-hero-v75 h1 {font-size:46px!important;line-height:1.15!important;margin:0 0 14px 0!important;font-weight:950!important;}
.pending-hero-v75 p {font-size:18px!important;max-width:850px!important;line-height:1.55!important;}
.pending-access-card-v75 {background:#FFFFFF;border:1px solid #DCE6F4;border-radius:18px;padding:34px 36px;margin:34px 52px 24px 52px;box-shadow:0 16px 34px rgba(16,24,40,.08);}
.pending-access-card-v75 h1 {color:#101828!important;margin:8px 0 12px 0!important;}
.pending-access-card-v75 p {color:#344054!important;font-size:17px!important;line-height:1.55!important;}
.pending-pill-v75 {display:inline-block;background:#FFF4D6;color:#B54708!important;-webkit-text-fill-color:#B54708!important;border-radius:999px;padding:8px 15px;font-weight:950;}
.pending-muted-v75 {color:#667085!important;}
.pending-staff-panel-v75 {margin-top:20px!important;}
.pending-staff-panel-v75 h2 {color:#101828!important;margin:0 0 6px 0!important;}
.pending-staff-panel-v75 p {color:#667085!important;margin:0!important;}
.staff-request-card-v75 {background:#FFFFFF;border:1px solid #DCE6F4;border-radius:16px;padding:18px 20px;margin:12px 0 10px 0;box-shadow:0 8px 20px rgba(16,24,40,.05);}
.staff-request-card-v75 h3 {color:#002B5B!important;margin:0 0 8px 0!important;font-weight:950!important;}
.staff-request-card-v75 p {color:#101828!important;margin:5px 0!important;}


/* v76 pending approval personalized message */
.pending-access-card-v75 {
    background:#FFFFFF;
    border:1px solid #DCE6F4;
    border-radius:18px;
    padding:32px 34px;
    margin:34px 52px 22px 52px;
    box-shadow:0 12px 30px rgba(16,24,40,.08);
}
.pending-access-card-v75 h1 {
    color:#002B5B !important;
    font-size:36px !important;
    font-weight:950 !important;
    margin:10px 0 14px 0 !important;
}
.pending-access-card-v75 p {
    color:#101828 !important;
    font-size:17px !important;
    line-height:1.55 !important;
}
.pending-pill-v75 {
    display:inline-flex;
    background:#FFF4D6;
    color:#B54708 !important;
    -webkit-text-fill-color:#B54708 !important;
    border-radius:999px;
    padding:8px 14px;
    font-weight:950;
}
.pending-muted-v75 {
    color:#667085 !important;
}


/* v77 official representative and signup improvements */
.official-rep-badge-v77 {
    display:inline-flex;
    align-items:center;
    justify-content:center;
    background:#FFF4D6;
    color:#B54708 !important;
    -webkit-text-fill-color:#B54708 !important;
    border:1px solid #FEC84B;
    border-radius:999px;
    padding:6px 12px;
    font-size:13px;
    font-weight:950;
    vertical-align:middle;
    margin-left:8px;
}
.staff-request-card-v75 {
    background:#FFFFFF;
    border:1px solid #DCE6F4;
    border-radius:16px;
    padding:18px 20px;
    margin:12px 0 10px 0;
    box-shadow:0 8px 20px rgba(16,24,40,.05);
}
.staff-request-card-v75 h3 {
    color:#002B5B !important;
    font-size:23px !important;
    font-weight:950 !important;
    margin:0 0 10px 0 !important;
}
.pending-staff-panel-v75 {
    margin-top:18px;
}


/* v78 dynamic signup category note */
.signup-category-note-v78 {
    background:#EEF5FF;
    border:1px solid #CFE0FF;
    border-radius:14px;
    padding:13px 16px;
    margin:12px 0 18px 0;
}
.signup-category-note-v78 p, .signup-category-note-v78 strong {
    color:#002B5B !important;
    -webkit-text-fill-color:#002B5B !important;
    font-weight:850 !important;
}


/* v81 official representative dashboard detail cards */
.partner-stat-grid-v81 {
    grid-template-columns: repeat(5, minmax(0, 1fr)) !important;
}
.clickable-stat-v81 {
    border-color:#BBD3FF !important;
    box-shadow:0 12px 28px rgba(0,91,219,.08) !important;
}
.v81-detail-panel {
    margin-top:18px !important;
}
.v81-detail-panel h2 {
    color:#002B5B !important;
    font-weight:950 !important;
    margin-bottom:6px !important;
}
.v81-detail-panel p {
    color:#667085 !important;
    font-weight:650 !important;
    margin:0 !important;
}
@media(max-width:1200px){
    .partner-stat-grid-v81 {
        grid-template-columns: repeat(2, minmax(0, 1fr)) !important;
    }
}
@media(max-width:700px){
    .partner-stat-grid-v81 {
        grid-template-columns: 1fr !important;
    }
}


/* v84 bigger and clearer partner logo */
.partner-welcome-line-v83 {
    display:flex;
    align-items:center;
    gap:28px;
    flex-wrap:wrap;
}
.partner-welcome-line-v83 h1 {
    margin-bottom:0 !important;
}
.partner-logo-v83 {
    width:140px !important;
    height:140px !important;
    object-fit:contain !important;
    background:#FFFFFF !important;
    border:2px solid rgba(255,255,255,.72) !important;
    border-radius:26px !important;
    padding:14px !important;
    box-shadow:0 18px 34px rgba(0,0,0,.22) !important;
}
@media(max-width:800px){
    .partner-logo-v83 {
        width:110px !important;
        height:110px !important;
        border-radius:22px !important;
    }
}


/* v84 partner hero spacing for bigger logo */
.partner-hero {
    min-height: 330px !important;
    padding-top: 58px !important;
    padding-bottom: 58px !important;
}


/* v85 separate staff/partner pages and activity buttons */
.v85-page-hero {
    background: linear-gradient(135deg, #002B5B, #1F3D7A);
    color:#FFFFFF !important;
    border-radius:24px;
    padding:34px 38px;
    margin:18px 0 24px 0;
    box-shadow:0 18px 36px rgba(0,43,91,.16);
}
.v85-page-hero span {
    display:inline-flex;
    background:rgba(255,255,255,.14);
    border:1px solid rgba(255,255,255,.28);
    border-radius:999px;
    padding:7px 13px;
    color:#FFFFFF !important;
    -webkit-text-fill-color:#FFFFFF !important;
    font-weight:900;
    margin-bottom:16px;
}
.v85-page-hero h1 {
    color:#FFFFFF !important;
    -webkit-text-fill-color:#FFFFFF !important;
    font-size:38px !important;
    font-weight:950 !important;
    margin:0 0 10px 0 !important;
}
.v85-page-hero p,
.v85-page-hero b {
    color:#FFFFFF !important;
    -webkit-text-fill-color:#FFFFFF !important;
    font-size:16px !important;
}
.v85-list-card {
    background:#FFFFFF;
    border:1px solid #DCE6F4;
    border-radius:18px;
    padding:22px 26px;
    margin:14px 0 8px 0;
    box-shadow:0 10px 24px rgba(16,24,40,.06);
}
.v85-list-card h3 {
    color:#002B5B !important;
    font-size:25px !important;
    font-weight:950 !important;
    margin:0 0 10px 0 !important;
}
.v85-list-card p {
    color:#344054 !important;
    margin:6px 0 !important;
    font-size:15px !important;
}
.v85-list-card b {
    color:#101828 !important;
    font-weight:900 !important;
}
.v85-mini-stat-grid {
    display:grid;
    grid-template-columns:repeat(3,minmax(0,1fr));
    gap:16px;
    margin:18px 0 24px 0;
}
.v85-mini-stat-grid div {
    background:#FFFFFF;
    border:1px solid #DCE6F4;
    border-radius:18px;
    padding:22px 24px;
    box-shadow:0 10px 24px rgba(16,24,40,.06);
}
.v85-mini-stat-grid b {
    display:block;
    color:#005BDB !important;
    font-size:34px !important;
    font-weight:950 !important;
    margin-bottom:5px;
}
.v85-mini-stat-grid span {
    color:#475467 !important;
    font-weight:800 !important;
}
button[kind="secondary"],
.stButton > button {
    font-weight:900 !important;
}
.stButton > button:has(p) {
    border-radius:10px !important;
}
@media(max-width:900px){
    .v85-mini-stat-grid {
        grid-template-columns:1fr;
    }
}


/* v87 staff-only activity privacy note */
.v87-privacy-note {
    background:#EEF5FF;
    border:1px solid #CFE0FF;
    border-radius:14px;
    padding:14px 16px;
    color:#002B5B !important;
    font-weight:800 !important;
}


/* v88 university summary layout with logo + right-side program cards */
.uni-summary-card-v88 {
    background:#FFFFFF !important;
    border:1px solid #DCE6F4 !important;
    border-radius:18px !important;
    overflow:hidden !important;
    box-shadow:0 10px 28px rgba(16,24,40,.06) !important;
    margin:22px 0 12px 0 !important;
}
.uni-summary-image-wrap-v88 {
    width:100% !important;
}
.uni-summary-image-wrap-v88 .uni-summary-photo-v62 {
    width:100% !important;
    height:315px !important;
    object-fit:cover !important;
    border-radius:0 !important;
    display:block !important;
}
.uni-summary-content-v88 {
    display:grid !important;
    grid-template-columns: 1.05fr 1fr !important;
    gap:28px !important;
    align-items:stretch !important;
    padding:34px 36px !important;
}
.uni-summary-left-v88 {
    display:grid !important;
    grid-template-columns: 190px 1fr !important;
    gap:24px !important;
    align-items:center !important;
}
.uni-logo-box-v88 {
    width:190px !important;
    height:190px !important;
    border:1px solid #DCE6F4 !important;
    border-radius:24px !important;
    background:#F8FAFC !important;
    display:flex !important;
    align-items:center !important;
    justify-content:center !important;
    padding:18px !important;
    box-shadow:0 10px 24px rgba(16,24,40,.07) !important;
}
.uni-logo-v88 {
    width:100% !important;
    height:100% !important;
    object-fit:contain !important;
    display:block !important;
}
.uni-logo-placeholder-v88 {
    width:100% !important;
    height:100% !important;
    display:flex !important;
    flex-direction:column !important;
    align-items:center !important;
    justify-content:center !important;
    text-align:center !important;
    color:#002B5B !important;
    font-size:18px !important;
    font-weight:950 !important;
    line-height:1.2 !important;
}
.uni-logo-placeholder-v88 span {
    color:#667085 !important;
    font-size:14px !important;
    margin-top:6px !important;
}
.uni-summary-text-v88 h3 {
    color:#101828 !important;
    font-size:34px !important;
    line-height:1.12 !important;
    font-weight:950 !important;
    margin:0 0 16px 0 !important;
}
.uni-summary-text-v88 p {
    color:#344054 !important;
    font-size:17px !important;
    line-height:1.6 !important;
    margin:0 !important;
}
.uni-summary-programs-v88 {
    display:grid !important;
    grid-template-columns: repeat(3, minmax(0,1fr)) !important;
    gap:16px !important;
    align-content:center !important;
    justify-content:stretch !important;
}
.uni-summary-programs-v88 .program-date-card-v71 {
    min-height:150px !important;
    padding:18px 18px !important;
    border-radius:18px !important;
    background:#F6F8FC !important;
    border:1px solid #DCE6F4 !important;
}
.uni-summary-programs-v88 .program-date-card-v71 b {
    font-size:15px !important;
    color:#002B5B !important;
}
.uni-summary-programs-v88 .program-date-card-v71 span {
    font-size:13px !important;
    padding:10px 14px !important;
}
.uni-summary-programs-v88 .program-date-card-v71 small {
    font-size:13px !important;
    color:#344054 !important;
}
@media(max-width:1200px){
    .uni-summary-content-v88 {
        grid-template-columns:1fr !important;
    }
    .uni-summary-programs-v88 {
        grid-template-columns:repeat(3, minmax(0,1fr)) !important;
    }
}
@media(max-width:760px){
    .uni-summary-left-v88 {
        grid-template-columns:1fr !important;
    }
    .uni-logo-box-v88 {
        width:150px !important;
        height:150px !important;
    }
    .uni-summary-programs-v88 {
        grid-template-columns:1fr !important;
    }
}


/* v89 university auto slideshow */
.uni-slideshow-v89 {
    position:relative !important;
    width:100% !important;
    height:315px !important;
    overflow:hidden !important;
    background:#F2F4F7 !important;
}
.uni-slide-img-v89 {
    position:absolute !important;
    inset:0 !important;
    width:100% !important;
    height:100% !important;
    object-fit:cover !important;
    opacity:0 !important;
    animation-name: uniFadeSlideV89 !important;
    animation-timing-function:ease-in-out !important;
    animation-iteration-count:infinite !important;
    transform:scale(1.03) !important;
}
.uni-slide-img-v89.active {
    opacity:1;
}
.uni-slide-gradient-v89 {
    position:absolute !important;
    inset:0 !important;
    background:linear-gradient(180deg, rgba(0,0,0,0) 45%, rgba(0,43,91,.16) 100%) !important;
    pointer-events:none !important;
}
.uni-slide-dots-v89 {
    position:absolute !important;
    right:18px !important;
    bottom:14px !important;
    display:flex !important;
    gap:7px !important;
    z-index:3 !important;
}
.uni-slide-dots-v89 span {
    width:8px !important;
    height:8px !important;
    background:rgba(255,255,255,.75) !important;
    border-radius:999px !important;
    box-shadow:0 2px 5px rgba(0,0,0,.18) !important;
}
@keyframes uniFadeSlideV89 {
    0% { opacity:0; transform:scale(1.03); }
    6% { opacity:1; transform:scale(1.00); }
    28% { opacity:1; transform:scale(1.00); }
    34% { opacity:0; transform:scale(1.02); }
    100% { opacity:0; transform:scale(1.03); }
}
.uni-summary-image-wrap-v88 .uni-slideshow-v89 {
    border-radius:0 !important;
}


/* v91 university name color automatically follows uploaded logo accent */
.uni-summary-text-v88 h3 {
    transition: color .25s ease-in-out !important;
}


/* v92 force university name to use extracted logo accent */
.uni-name-accent-v92,
.uni-name-accent-v92 span {
    font-weight: 950 !important;
    transition: color .25s ease-in-out !important;
}
.uni-summary-text-v88 .uni-name-accent-v92,
.uni-summary-text-v88 .uni-name-accent-v92 span {
    color: inherit;
}


/* v93 final force for university name accent color */
.uni-summary-text-v88 h3.uni-name-accent-v93,
.uni-summary-text-v88 h3.uni-name-accent-v93 span,
h3.uni-name-accent-v93,
h3.uni-name-accent-v93 span {
    font-weight:950 !important;
    transition:color .25s ease-in-out !important;
}


/* v94 admin rules UI matching sample */
.admin-rule-title-v94 {
    margin: 8px 0 16px 0;
}
.admin-rule-title-v94 h1 {
    color:#101828 !important;
    font-size:30px !important;
    line-height:1.15 !important;
    font-weight:950 !important;
    margin:0 0 8px 0 !important;
}
.admin-rule-title-v94 p {
    color:#667085 !important;
    font-size:15px !important;
    font-weight:650 !important;
    margin:0 !important;
}
.rule-selector-panel-v94 {
    background:#FFFFFF;
    border:1px solid #DCE6F4;
    border-radius:14px;
    padding:16px 18px 10px 18px;
    margin:12px 0 16px 0;
    box-shadow:0 8px 22px rgba(16,24,40,.05);
}
.selected-rule-uni-card-v94 {
    display:flex;
    align-items:center;
    gap:18px;
    background:#F3F8FF;
    border:1px solid #BBD3FF;
    border-radius:14px;
    padding:18px 22px;
    margin:8px 0 22px 0;
}
.selected-rule-logo-v94 {
    width:58px;
    height:58px;
    border-radius:999px;
    background:#005BDB;
    display:flex;
    align-items:center;
    justify-content:center;
    overflow:hidden;
    flex:0 0 auto;
    padding:7px;
}
.selected-rule-logo-v94 img,
.selected-rule-logo-v94 .uni-logo-v88 {
    width:100% !important;
    height:100% !important;
    object-fit:contain !important;
    background:#FFFFFF !important;
    border-radius:999px !important;
    padding:3px !important;
}
.selected-rule-logo-v94 .uni-logo-placeholder-v88 {
    color:#FFFFFF !important;
    font-size:10px !important;
    line-height:1.05 !important;
}
.selected-rule-uni-card-v94 h2 {
    color:#002B5B !important;
    font-size:20px !important;
    font-weight:950 !important;
    margin:0 0 4px 0 !important;
}
.selected-rule-uni-card-v94 p {
    color:#475467 !important;
    font-size:14px !important;
    margin:0 !important;
    font-weight:650 !important;
}
.rules-table-heading-v94 {
    color:#101828 !important;
    font-size:20px !important;
    font-weight:950 !important;
    margin:7px 0 0 0 !important;
}
.rules-table-wrap-v94 {
    background:#FFFFFF;
    border:1px solid #EAECF0;
    border-radius:16px;
    padding:0;
    margin-top:12px;
    overflow:hidden;
    box-shadow:0 10px 24px rgba(16,24,40,.06);
}
.rules-result-count-v94 {
    color:#667085 !important;
    font-size:14px !important;
    margin:14px 0 0 0 !important;
    font-weight:650 !important;
}


/* v96 active navigation for all dashboard users/admin */
.dash-nav-v96 {
    display:grid !important;
    grid-template-columns:repeat(auto-fit, minmax(150px, 1fr)) !important;
    gap:12px !important;
    margin:0 0 24px 0 !important;
}
.dash-nav-link-v96 {
    display:flex !important;
    align-items:center !important;
    justify-content:center !important;
    gap:9px !important;
    min-height:48px !important;
    padding:10px 14px !important;
    background:#FFFFFF !important;
    color:#101828 !important;
    -webkit-text-fill-color:#101828 !important;
    border:1px solid #D9E2F1 !important;
    border-radius:10px !important;
    text-decoration:none !important;
    font-weight:850 !important;
    box-shadow:0 6px 14px rgba(16,24,40,.03) !important;
    transition:all .18s ease-in-out !important;
}
.dash-nav-link-v96 span,
.dash-nav-link-v96 .dash-nav-icon-v96 {
    color:inherit !important;
    -webkit-text-fill-color:inherit !important;
}
.dash-nav-link-v96:hover {
    border-color:#005BDB !important;
    color:#005BDB !important;
    -webkit-text-fill-color:#005BDB !important;
    transform:translateY(-1px) !important;
}
.dash-nav-link-v96.active {
    background:#005BDB !important;
    border-color:#005BDB !important;
    color:#FFFFFF !important;
    -webkit-text-fill-color:#FFFFFF !important;
    box-shadow:0 10px 24px rgba(0,91,219,.22) !important;
}
.dash-nav-link-v96.active span,
.dash-nav-link-v96.active .dash-nav-icon-v96 {
    color:#FFFFFF !important;
    -webkit-text-fill-color:#FFFFFF !important;
}
.dash-nav-link-v96.logout {
    color:#B42318 !important;
    -webkit-text-fill-color:#B42318 !important;
}
.dash-nav-link-v96.logout.active {
    background:#B42318 !important;
    border-color:#B42318 !important;
    color:#FFFFFF !important;
    -webkit-text-fill-color:#FFFFFF !important;
}
.dash-nav-icon-v96 {
    font-size:17px !important;
    line-height:1 !important;
}
@media(max-width:760px){
    .dash-nav-v96 {
        grid-template-columns:1fr 1fr !important;
    }
}


/* v97 reliable university slideshow display */
.uni-slideshow-single-v97 {
    position:relative !important;
    width:100% !important;
    height:315px !important;
    overflow:hidden !important;
    background:#F2F4F7 !important;
}
.uni-slide-img-single-v97 {
    width:100% !important;
    height:100% !important;
    object-fit:cover !important;
    display:block !important;
    opacity:1 !important;
    animation:none !important;
    transform:none !important;
}
.uni-slide-img-v97 {
    position:absolute !important;
    inset:0 !important;
    width:100% !important;
    height:100% !important;
    object-fit:cover !important;
    opacity:0;
    animation-timing-function:ease-in-out !important;
    animation-iteration-count:infinite !important;
}
.uni-slideshow-missing-v97 {
    height:315px !important;
    background:linear-gradient(135deg,#F2F4F7,#E4E8EF) !important;
    display:flex !important;
    flex-direction:column !important;
    align-items:center !important;
    justify-content:center !important;
    text-align:center !important;
    gap:8px !important;
    color:#475467 !important;
}
.uni-slideshow-missing-v97 b {
    color:#002B5B !important;
    font-size:20px !important;
    font-weight:950 !important;
}
.uni-slideshow-missing-v97 span {
    color:#667085 !important;
    font-size:14px !important;
    max-width:520px !important;
}


/* v98 cleaned logo display */
.uni-logo-box-v88 {
    background:#FFFFFF !important;
    padding:10px !important;
}
.uni-logo-v88 {
    width:100% !important;
    height:100% !important;
    object-fit:contain !important;
}
.partner-logo-v83 {
    object-fit:contain !important;
    background:#FFFFFF !important;
}
.selected-rule-logo-v94 {
    background:#FFFFFF !important;
}
.selected-rule-logo-v94 img,
.selected-rule-logo-v94 .uni-logo-v88 {
    background:transparent !important;
    padding:0 !important;
}


/* v99 compact university detail page + Google map */
.detail-card-v99 {
    background:#FFFFFF !important;
    border:1px solid #DCE6F4 !important;
    border-radius:22px !important;
    overflow:hidden !important;
    box-shadow:0 14px 32px rgba(16,24,40,.07) !important;
    margin:18px 0 24px 0 !important;
}
.detail-photo-v99 .uni-slideshow-v89,
.detail-photo-v99 .uni-slideshow-single-v97,
.detail-photo-v99 .uni-wide-v32,
.detail-photo-v99 img {
    height:270px !important;
    width:100% !important;
    object-fit:cover !important;
    border-radius:0 !important;
    display:block !important;
}
.detail-main-v99 {
    display:grid !important;
    grid-template-columns:minmax(0,1.35fr) minmax(320px,.75fr) !important;
    gap:26px !important;
    padding:34px 38px 24px 38px !important;
    align-items:center !important;
}
.detail-left-v99 {
    display:grid !important;
    grid-template-columns:170px minmax(0,1fr) !important;
    gap:26px !important;
    align-items:center !important;
}
.detail-logo-box-v99 {
    width:170px !important;
    height:170px !important;
    border:1px solid #DCE6F4 !important;
    border-radius:24px !important;
    background:#FFFFFF !important;
    display:flex !important;
    align-items:center !important;
    justify-content:center !important;
    padding:10px !important;
    box-shadow:0 10px 24px rgba(16,24,40,.06) !important;
}
.detail-logo-box-v99 img,
.detail-logo-box-v99 .uni-logo-v88 {
    width:100% !important;
    height:100% !important;
    object-fit:contain !important;
}
.detail-title-copy-v99 h2 {
    font-size:42px !important;
    line-height:1.1 !important;
    font-weight:950 !important;
    margin:0 0 18px 0 !important;
}
.detail-title-copy-v99 p {
    font-size:19px !important;
    line-height:1.65 !important;
    color:#344054 !important;
    max-width:780px !important;
    margin:0 !important;
}
.detail-program-side-v99 {
    display:grid !important;
    grid-template-columns:1fr !important;
    gap:12px !important;
}
.detail-program-side-v99 .program-date-card-v71 {
    min-height:116px !important;
    padding:16px 18px !important;
    border-radius:18px !important;
    background:#F6F8FC !important;
    border:1px solid #DCE6F4 !important;
}
.detail-program-side-v99 .program-date-card-v71 span {
    padding:10px 16px !important;
}
.detail-info-grid-v99 {
    display:grid !important;
    grid-template-columns:repeat(4,minmax(0,1fr)) !important;
    gap:14px !important;
    padding:0 38px 30px 38px !important;
}
.uni-map-card-v99 {
    border-top:1px solid #E6ECF5 !important;
    padding:28px 38px 34px 38px !important;
    background:#FBFCFF !important;
}
.uni-map-header-v99 {
    display:flex !important;
    align-items:center !important;
    justify-content:space-between !important;
    gap:18px !important;
    margin-bottom:16px !important;
}
.uni-map-header-v99 h3 {
    font-size:24px !important;
    font-weight:950 !important;
    margin:0 0 6px 0 !important;
    color:#101828 !important;
}
.uni-map-header-v99 p {
    font-size:15px !important;
    color:#667085 !important;
    margin:0 !important;
}
.uni-map-link-v99 {
    display:inline-flex !important;
    align-items:center !important;
    justify-content:center !important;
    padding:12px 18px !important;
    background:#005BDB !important;
    color:#FFFFFF !important;
    -webkit-text-fill-color:#FFFFFF !important;
    text-decoration:none !important;
    border-radius:10px !important;
    font-weight:900 !important;
    white-space:nowrap !important;
}
.uni-map-frame-v99 {
    width:100% !important;
    height:360px !important;
    border:0 !important;
    border-radius:18px !important;
    box-shadow:0 10px 22px rgba(16,24,40,.08) !important;
}
.detail-programs-v99 {
    padding:0 38px 38px 38px !important;
}
@media(max-width:1100px){
    .detail-main-v99 {
        grid-template-columns:1fr !important;
    }
    .detail-info-grid-v99 {
        grid-template-columns:repeat(2,minmax(0,1fr)) !important;
    }
}
@media(max-width:760px){
    .detail-left-v99 {
        grid-template-columns:1fr !important;
    }
    .detail-logo-box-v99 {
        width:140px !important;
        height:140px !important;
    }
    .detail-title-copy-v99 h2 {
        font-size:32px !important;
    }
    .detail-info-grid-v99 {
        grid-template-columns:1fr !important;
    }
    .uni-map-header-v99 {
        align-items:flex-start !important;
        flex-direction:column !important;
    }
}


/* v103 university detail quick links */
.uni-quick-links-card-v103 {
    margin:0 38px 28px 38px !important;
    padding:24px 26px !important;
    border:1px solid #E6ECF5 !important;
    border-radius:18px !important;
    background:#FFFFFF !important;
    box-shadow:0 8px 20px rgba(16,24,40,.04) !important;
}
.uni-quick-links-card-v103 h3 {
    color:#101828 !important;
    font-size:24px !important;
    font-weight:950 !important;
    margin:0 0 14px 0 !important;
}
.uni-quick-links-grid-v103 {
    display:grid !important;
    grid-template-columns:repeat(3,minmax(0,1fr)) !important;
    gap:12px !important;
}
.uni-quick-link-v103 {
    display:flex !important;
    align-items:center !important;
    gap:12px !important;
    min-height:58px !important;
    padding:14px 16px !important;
    border:1px solid #DCE6F4 !important;
    border-radius:14px !important;
    background:#F8FAFC !important;
    color:#101828 !important;
    -webkit-text-fill-color:#101828 !important;
    text-decoration:none !important;
    font-size:16px !important;
    font-weight:900 !important;
    transition:all .18s ease-in-out !important;
}
.uni-quick-link-v103:hover {
    border-color:#005BDB !important;
    background:#EEF5FF !important;
    color:#005BDB !important;
    -webkit-text-fill-color:#005BDB !important;
    transform:translateY(-1px) !important;
}
.uni-quick-icon-v103 {
    display:inline-flex !important;
    align-items:center !important;
    justify-content:center !important;
    width:32px !important;
    height:32px !important;
    border-radius:999px !important;
    background:#EAF2FF !important;
    color:#005BDB !important;
    -webkit-text-fill-color:#005BDB !important;
    font-weight:950 !important;
    flex:0 0 auto !important;
}

.uni-quick-icon-v103 svg {
    width:20px !important;
    height:20px !important;
    display:block !important;
}
.uni-quick-icon-v103.facebook-link-v105 {
    background:#E7F0FF !important;
    color:#1877F2 !important;
    -webkit-text-fill-color:#1877F2 !important;
}
.uni-quick-icon-v103.instagram-link-v105 {
    background:#F4F0FF !important;
    color:#962FBF !important;
    -webkit-text-fill-color:#962FBF !important;
}
.uni-quick-icon-v103.youtube-link-v105 {
    background:#FFF0F0 !important;
    color:#FF0000 !important;
    -webkit-text-fill-color:#FF0000 !important;
}
.uni-quick-icon-v103.home-link-v105,
.uni-quick-icon-v103.language-link-v105,
.uni-quick-icon-v103.promo-link-v105 {
    font-size:16px !important;
}
.uni-emoji-icon-v105 {
    display:inline-flex !important;
    align-items:center !important;
    justify-content:center !important;
    line-height:1 !important;
}
.sns-svg-v105 {
    overflow:visible !important;
}

.uni-external-v103 {
    margin-left:auto !important;
    color:#667085 !important;
    -webkit-text-fill-color:#667085 !important;
    font-weight:950 !important;
}
.uni-sns-note-v103 {
    margin-top:14px !important;
    padding-top:14px !important;
    border-top:1px dashed #D9E2F1 !important;
}
.uni-sns-note-v103 b {
    color:#101828 !important;
    font-size:17px !important;
    font-weight:950 !important;
}
.uni-sns-note-v103 p {
    color:#475467 !important;
    font-size:15px !important;
    line-height:1.6 !important;
    margin:8px 0 0 0 !important;
}
@media(max-width:900px){
    .uni-quick-links-grid-v103 {
        grid-template-columns:1fr 1fr !important;
    }
}
@media(max-width:640px){
    .uni-quick-links-card-v103 {
        margin:0 20px 24px 20px !important;
    }
    .uni-quick-links-grid-v103 {
        grid-template-columns:1fr !important;
    }
}


/* v104 admin university tabs note + persistent-login nav helpers */
.admin-university-tabs-note-v104 {
    display:flex !important;
    align-items:center !important;
    justify-content:space-between !important;
    gap:16px !important;
    background:#EEF5FF !important;
    border:1px solid #BBD3FF !important;
    border-radius:14px !important;
    padding:16px 18px !important;
    margin:18px 0 12px 0 !important;
}
.admin-university-tabs-note-v104 b {
    color:#002B5B !important;
    font-weight:950 !important;
}
.admin-university-tabs-note-v104 span {
    color:#344054 !important;
    font-weight:700 !important;
}


/* v106 student enrollment and nationality statistics */
.student-stats-card-v106 { margin:0 38px 28px 38px !important; padding:26px !important; border:1px solid #E6ECF5 !important; border-radius:20px !important; background:linear-gradient(180deg,#FFFFFF,#F8FAFF) !important; box-shadow:0 10px 24px rgba(16,24,40,.05) !important; }
.student-stats-head-v106 { display:flex !important; align-items:flex-start !important; justify-content:space-between !important; gap:18px !important; margin-bottom:20px !important; }
.student-stats-head-v106 h3 { color:#101828 !important; font-size:24px !important; font-weight:950 !important; margin:0 0 6px 0 !important; }
.student-stats-head-v106 p { color:#667085 !important; font-size:14px !important; font-weight:700 !important; margin:0 !important; }
.student-total-pill-v106 { padding:10px 14px !important; background:#EEF5FF !important; color:#005BDB !important; -webkit-text-fill-color:#005BDB !important; border:1px solid #BBD3FF !important; border-radius:999px !important; font-weight:950 !important; white-space:nowrap !important; }
.student-stats-grid-v106 { display:grid !important; grid-template-columns:1fr 1fr !important; gap:24px !important; }
.student-program-chart-v106, .nationality-chart-v106 { background:#FFFFFF !important; border:1px solid #E6ECF5 !important; border-radius:16px !important; padding:20px !important; }
.student-program-chart-v106 h4, .nationality-chart-v106 h4 { color:#101828 !important; font-size:18px !important; font-weight:950 !important; margin:0 0 18px 0 !important; }
.student-stat-row-v106 { margin-bottom:16px !important; }
.student-stat-label-v106 { display:flex !important; align-items:center !important; justify-content:space-between !important; gap:12px !important; margin-bottom:7px !important; }
.student-stat-label-v106 span, .nationality-main-v106 span { color:#344054 !important; font-weight:850 !important; }
.student-stat-label-v106 b, .nationality-item-v106 b { color:#101828 !important; font-weight:950 !important; }
.student-stat-bar-v106, .nationality-bar-v106 { width:100% !important; height:12px !important; background:#EAECF0 !important; border-radius:999px !important; overflow:hidden !important; }
.student-stat-bar-v106 div, .nationality-bar-v106 div { height:100% !important; border-radius:999px !important; }
.nationality-bar-v106 div { background:#005BDB !important; }
.nationality-item-v106 { display:grid !important; grid-template-columns:minmax(0,1fr) auto !important; gap:8px 14px !important; align-items:center !important; margin-bottom:14px !important; }
.nationality-main-v106 { display:flex !important; align-items:center !important; gap:10px !important; min-width:0 !important; }
.flag-v106 { font-size:24px !important; line-height:1 !important; display:inline-flex !important; align-items:center !important; justify-content:center !important; width:34px !important; height:34px !important; border-radius:999px !important; background:#F2F4F7 !important; flex:0 0 auto !important; }
.student-muted-v106 { color:#667085 !important; font-weight:700 !important; margin:0 !important; }
@media(max-width:900px){ .student-stats-grid-v106 { grid-template-columns:1fr !important; } .student-stats-card-v106 { margin:0 20px 24px 20px !important; } .student-stats-head-v106 { flex-direction:column !important; } }


/* v107 student statistics Excel upload explanation and template download */
.student-stats-upload-info-v107 {
    background:#F8FAFF !important;
    border:1px solid #BBD3FF !important;
    border-radius:14px !important;
    padding:15px 16px !important;
    margin:18px 0 12px 0 !important;
}
.student-stats-upload-info-v107 b {
    color:#002B5B !important;
    font-size:16px !important;
    font-weight:950 !important;
}
.student-stats-upload-info-v107 p {
    color:#344054 !important;
    font-size:14px !important;
    line-height:1.55 !important;
    margin:7px 0 8px 0 !important;
}
.student-stats-upload-info-v107 ul {
    margin:8px 0 0 18px !important;
    padding:0 !important;
}
.student-stats-upload-info-v107 li {
    color:#475467 !important;
    font-size:13px !important;
    line-height:1.55 !important;
    margin:3px 0 !important;
}
.excel-template-download-v107 {
    display:flex !important;
    align-items:center !important;
    justify-content:center !important;
    gap:9px !important;
    min-height:52px !important;
    padding:12px 14px !important;
    border-radius:12px !important;
    background:#005BDB !important;
    border:1px solid #005BDB !important;
    color:#FFFFFF !important;
    -webkit-text-fill-color:#FFFFFF !important;
    text-decoration:none !important;
    font-weight:950 !important;
    box-shadow:0 8px 18px rgba(0,91,219,.18) !important;
    margin-top:28px !important;
}
.excel-template-download-v107 span,
.excel-template-download-v107 b {
    color:#FFFFFF !important;
    -webkit-text-fill-color:#FFFFFF !important;
}
.excel-template-download-v107:hover {
    background:#004BB8 !important;
    border-color:#004BB8 !important;
    transform:translateY(-1px) !important;
}
.excel-template-download-v107.disabled {
    background:#98A2B3 !important;
    border-color:#98A2B3 !important;
}


/* v108 automatic country flag images in nationality chart */
.flag-img-wrap-v108 {
    width:40px !important;
    height:40px !important;
    border-radius:999px !important;
    background:#FFFFFF !important;
    border:1px solid #D9E2F1 !important;
    box-shadow:0 4px 10px rgba(16,24,40,.08) !important;
    display:inline-flex !important;
    align-items:center !important;
    justify-content:center !important;
    overflow:hidden !important;
    flex:0 0 auto !important;
}
.flag-img-v108 {
    width:100% !important;
    height:100% !important;
    object-fit:cover !important;
    display:block !important;
}
.flag-fallback-v108 {
    width:40px !important;
    height:40px !important;
    border-radius:999px !important;
    background:#F2F4F7 !important;
    color:#344054 !important;
    -webkit-text-fill-color:#344054 !important;
    display:inline-flex !important;
    align-items:center !important;
    justify-content:center !important;
    font-weight:950 !important;
    font-size:15px !important;
    flex:0 0 auto !important;
}
.nationality-main-v106 {
    gap:12px !important;
}


/* v109 clickable program cards and program detail/application pages */
.program-click-card-v109 {
    text-decoration:none !important;
    color:inherit !important;
    -webkit-text-fill-color:inherit !important;
    cursor:pointer !important;
    transition:all .18s ease-in-out !important;
    display:flex !important;
    flex-direction:column !important;
}
.program-click-card-v109:hover {
    transform:translateY(-3px) !important;
    border-color:#005BDB !important;
    box-shadow:0 14px 28px rgba(0,91,219,.15) !important;
}
.program-click-card-v109 em {
    color:#005BDB !important;
    -webkit-text-fill-color:#005BDB !important;
    font-size:12px !important;
    font-style:normal !important;
    font-weight:950 !important;
    margin-top:8px !important;
}
.program-detail-page-v109 {
    background:#FFFFFF !important;
    border:1px solid #DCE6F4 !important;
    border-radius:22px !important;
    padding:30px 34px !important;
    box-shadow:0 12px 30px rgba(16,24,40,.07) !important;
    margin:18px 0 22px 0 !important;
}
.program-detail-head-v109 {
    display:grid !important;
    grid-template-columns:120px minmax(0,1fr) !important;
    gap:22px !important;
    align-items:center !important;
}
.program-detail-logo-v109 {
    width:120px !important;
    height:120px !important;
    border-radius:20px !important;
    border:1px solid #DCE6F4 !important;
    background:#FFFFFF !important;
    display:flex !important;
    align-items:center !important;
    justify-content:center !important;
    padding:10px !important;
}
.program-detail-logo-v109 img,
.program-detail-logo-v109 .uni-logo-v88 {
    width:100% !important;
    height:100% !important;
    object-fit:contain !important;
}
.program-detail-head-v109 p {
    color:#005BDB !important;
    font-size:15px !important;
    font-weight:950 !important;
    margin:0 0 8px 0 !important;
}
.program-detail-head-v109 h1 {
    color:#101828 !important;
    font-size:38px !important;
    font-weight:950 !important;
    line-height:1.1 !important;
    margin:0 0 14px 0 !important;
}
.program-detail-head-v109 span {
    color:#344054 !important;
    font-size:17px !important;
    line-height:1.65 !important;
    font-weight:650 !important;
}
.program-timeline-grid-v109 {
    display:grid !important;
    grid-template-columns:repeat(2,minmax(0,1fr)) !important;
    gap:16px !important;
    margin:18px 0 !important;
}
.program-timeline-grid-v109.single-v109 {
    grid-template-columns:minmax(0,1fr) !important;
    max-width:560px !important;
}
.program-timeline-card-v109 {
    background:#F6F8FC !important;
    border:1px solid #DCE6F4 !important;
    border-radius:18px !important;
    padding:18px 20px !important;
}
.program-timeline-card-v109 b {
    color:#002B5B !important;
    font-size:17px !important;
    font-weight:950 !important;
    display:block !important;
    margin-bottom:10px !important;
}
.program-timeline-card-v109 span {
    display:inline-flex !important;
    align-items:center !important;
    justify-content:center !important;
    min-width:180px !important;
    padding:10px 16px !important;
    border-radius:999px !important;
    font-weight:950 !important;
    margin-bottom:12px !important;
}
.program-timeline-card-v109 small {
    display:block !important;
    color:#344054 !important;
    font-weight:850 !important;
    margin-top:6px !important;
}
.program-major-section-v109 {
    margin:26px 0 !important;
    background:#FFFFFF !important;
    border:1px solid #E6ECF5 !important;
    border-radius:20px !important;
    padding:24px !important;
}
.program-major-section-v109 h3 {
    color:#101828 !important;
    font-size:24px !important;
    font-weight:950 !important;
    margin:0 0 16px 0 !important;
}
.program-major-grid-v109 {
    display:grid !important;
    grid-template-columns:repeat(2,minmax(0,1fr)) !important;
    gap:14px !important;
}
.program-major-card-v109 {
    background:#F8FAFC !important;
    border:1px solid #DCE6F4 !important;
    border-radius:14px !important;
    padding:16px !important;
}
.program-major-card-v109 b {
    color:#101828 !important;
    font-size:16px !important;
    font-weight:950 !important;
    display:block !important;
    margin-bottom:6px !important;
}
.program-major-card-v109 span {
    color:#005BDB !important;
    font-size:13px !important;
    font-weight:900 !important;
    display:block !important;
    margin-bottom:7px !important;
}
.program-major-card-v109 small,
.program-muted-v109 {
    color:#667085 !important;
    font-size:13px !important;
    font-weight:650 !important;
}
.application-start-panel-v109 {
    background:#EEF5FF !important;
    border:1px solid #BBD3FF !important;
    border-radius:18px !important;
    padding:22px 24px !important;
    margin:22px 0 14px 0 !important;
}
.application-start-panel-v109 h3 {
    color:#002B5B !important;
    font-size:24px !important;
    font-weight:950 !important;
    margin:0 0 8px 0 !important;
}
.application-start-panel-v109 p {
    color:#344054 !important;
    font-size:15px !important;
    margin:0 !important;
}
@media(max-width:900px){
    .program-detail-head-v109,
    .program-timeline-grid-v109,
    .program-major-grid-v109 {
        grid-template-columns:1fr !important;
    }
}

</style>
""", unsafe_allow_html=True)

def set_page(p):
    st.session_state.page = p
    st.rerun()









def header():
    current = st.session_state.get("page", "Home")
    pending_token = _current_pending_token_v76()
    pending_suffix = f"&pending={pending_token}" if pending_token else ""

    def active_cls(target):
        return " active" if current == target else ""

    def nav_href(nav_key):
        auth_suffix = auth_query_suffix_v104("&")
        return f"?nav={nav_key}{pending_suffix}{auth_suffix}"

    nav_html = f"""
    <div class="top-nav-reference-v70">
      <div class="nav-left-v70">
        <a class="nav-link-v70{active_cls('Home')}" href="{nav_href('home')}">Home</a>
        <a class="nav-link-v70{active_cls('Universities')}" href="{nav_href('universities')}">Universities</a>
        <a class="nav-link-v70{active_cls('Eligibility Check')}" href="{nav_href('eligibility')}">Eligibility Check</a>
        <a class="nav-link-v70{active_cls('Tuition & Scholarship')}" href="{nav_href('tuition')}">Tuition Fees</a>
        <a class="nav-link-v70{active_cls('Contact Us')}" href="{nav_href('contact')}">Contact Us</a>
        <a class="nav-link-v70" href="{nav_href('mou')}">MoU Contact</a>
      </div>
      <div class="nav-right-v70">
        <a class="nav-login-v70" href="{nav_href('login')}">Login</a>
        <a class="nav-signup-v70" href="{nav_href('signup')}">👥&nbsp;&nbsp;Partner Sign Up</a>
      </div>
    </div>
    """
    st.markdown(nav_html, unsafe_allow_html=True)


def footer():

    st.markdown("""
    <div class="features">
      <div class="feature"><div class="icon">✓</div><div><b>Trusted Partnerships</b><br><span class="muted">Work with verified universities</span></div></div>
      <div class="feature"><div class="icon">i</div><div><b>Accurate Information</b><br><span class="muted">Up-to-date admission & fee details</span></div></div>
      <div class="feature"><div class="icon">✓</div><div><b>Eligibility Made Easy</b><br><span class="muted">Quick checks for better guidance</span></div></div>
      <div class="feature"><div class="icon">☆</div><div><b>Scholarship Support</b><br><span class="muted">Maximize opportunities for students</span></div></div>
    </div>

    <div class="footer-lite-v27">
      <div class="footer-lite-grid-v27">
        <div>
          <h3>Partner Portal for<br>University Recruitment</h3>
          <p>Empowering global education partnerships.</p>
        </div>
        <div class="footer-contact-row-v27">
          <span>☎ +82 51 711 2773</span>
          <span>✉ uniqueststudy@gmail.com</span>
          <span>📍 Busan, Republic of Korea</span>
        </div>
      </div>
      <hr>
      <p class="copyright-v27">© 2026 Partner Portal for University Recruitment. All rights reserved.</p>
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



def save_uploaded_university_logo_v88(uploaded_file, university_name):
    """Save university logo after auto-cleaning unnecessary outside background/margins."""
    if uploaded_file is None:
        return ""
    slug = safe_slug_v49(university_name)
    out_dir = BASE / "assets" / "university_logos"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / f"{slug}_logo.png"

    cleaned = clean_logo_image_v98(uploaded_file, canvas_size=900, padding_ratio=0.08)
    cleaned.save(out_path, "PNG", optimize=True)
    return f"assets/university_logos/{slug}_logo.png"


def university_logo_accent_color_v91(path, university_name="", fallback="#002B5B"):
    """
    v93: Deterministic university-name color with automatic logo extraction fallback.
    Some logos contain black/navy text around the seal, so pure dominant-color extraction
    can pick dark navy/black instead of the visual brand accent. For known universities,
    use the visible brand accent directly. For all new universities, extract from logo.
    """
    name_l = str(university_name or "").lower()

    # Deterministic known university colors.
    # This fixes Kyungsung and Jeonbuk even when logo extraction picks dark text pixels.
    if "kyungsung" in name_l or "kyung sung" in name_l:
        return "#C89B2B"  # Kyungsung gold/yellow
    if "jeonbuk" in name_l or "chonbuk" in name_l or "jeonbuk national" in name_l:
        return "#7A2E83"  # Jeonbuk purple

    try:
        from PIL import Image

        p = Path(str(path or ""))
        if not str(path or "").strip():
            return fallback
        if not p.is_absolute():
            p = BASE / p
        if not p.exists():
            return fallback

        img = Image.open(p).convert("RGBA")
        img.thumbnail((180, 180), Image.Resampling.LANCZOS)

        buckets = {}
        for r, g, b, a in img.getdata():
            if a < 120:
                continue

            maxc, minc = max(r, g, b), min(r, g, b)
            saturation = maxc - minc
            brightness = (r + g + b) / 3

            # Ignore background/neutral colors.
            if brightness > 238 or brightness < 42:
                continue
            if saturation < 38:
                continue

            # Prefer visible brand accents over dark text.
            is_yellow_gold = (r > 145 and g > 105 and b < 115)
            is_purple = (r > 70 and b > 85 and g < 115)
            is_red = (r > 145 and g < 100 and b < 100)
            is_green = (g > 120 and r < 130 and b < 130)
            is_blue = (b > 120 and r < 120)

            boost = 1.0
            if is_yellow_gold:
                boost = 3.2
            elif is_purple:
                boost = 2.8
            elif is_red:
                boost = 2.2
            elif is_green:
                boost = 1.8
            elif is_blue:
                boost = 1.35

            # Penalize very dark navy/black text-like pixels.
            if brightness < 75:
                boost *= 0.25

            qr = int(round(r / 20) * 20)
            qg = int(round(g / 20) * 20)
            qb = int(round(b / 20) * 20)
            key = (min(255, qr), min(255, qg), min(255, qb))

            score = (saturation * 1.4 + (255 - abs(145 - brightness)) * 0.35) * boost
            buckets.setdefault(key, [0, 0.0])
            buckets[key][0] += 1
            buckets[key][1] += score

        if not buckets:
            return fallback

        best = max(buckets.items(), key=lambda item: item[1][1] + item[1][0] * 0.7)[0]
        r, g, b = best

        # Make light colors readable on white.
        brightness = (r + g + b) / 3
        if brightness > 178:
            factor = 0.68
            r, g, b = int(r * factor), int(g * factor), int(b * factor)

        return f"#{r:02X}{g:02X}{b:02X}"
    except Exception:
        return fallback

def university_name_style_v93(university_name, logo_path=""):
    color = university_logo_accent_color_v91(logo_path, university_name)
    return f"color:{color}!important;-webkit-text-fill-color:{color}!important;text-shadow:none!important;"


def university_logo_html_v88(path, name="University"):
    encoded = b64(path)
    if not encoded:
        return f'<div class="uni-logo-placeholder-v88">{_safe_html_v62(name)}<br><span>Logo</span></div>'
    return f'<img class="uni-logo-v88" src="data:image/png;base64,{encoded}"/>'



def save_uploaded_university_gallery_v89(uploaded_files, university_name):
    """Save multiple university slideshow photos and return pipe-separated paths."""
    if not uploaded_files:
        return ""
    from PIL import Image, ImageEnhance
    slug = safe_slug_v49(university_name)
    out_dir = BASE / "assets" / "universities" / f"{slug}_gallery"
    out_dir.mkdir(parents=True, exist_ok=True)

    saved = []
    for idx, uploaded_file in enumerate(uploaded_files, start=1):
        try:
            out_path = out_dir / f"{slug}_slide_{idx}.jpg"
            img = Image.open(uploaded_file).convert("RGB")
            target_size = (1800, 760)
            target_ratio = target_size[0] / target_size[1]
            w, h = img.size
            ratio = w / h

            if ratio > target_ratio:
                new_w = int(h * target_ratio)
                left = max(0, (w - new_w) // 2)
                img = img.crop((left, 0, left + new_w, h))
            else:
                new_h = int(w / target_ratio)
                top = max(0, (h - new_h) // 2)
                img = img.crop((0, top, w, top + new_h))

            img = img.resize(target_size, Image.Resampling.LANCZOS)
            img = ImageEnhance.Sharpness(img).enhance(1.08)
            img.save(out_path, quality=94, optimize=True)
            saved.append(f"assets/universities/{slug}_gallery/{slug}_slide_{idx}.jpg")
        except Exception:
            pass
    return "|".join(saved)

def gallery_paths_v89(u):
    """Return gallery paths. If no gallery is set, use the main Image as fallback."""
    raw = display_clean_v50(u.get("Image_Gallery", ""))
    paths = [p.strip() for p in raw.split("|") if p.strip()] if raw else []
    main_img = display_clean_v50(u.get("Image", ""))
    if not paths and main_img:
        paths = [main_img]
    return paths


def university_slideshow_html_v89(u, key_suffix=""):
    """
    v97: reliable university hero image/slideshow.
    Fixes the gray empty block issue caused by single-image CSS animation becoming opacity:0.
    - 1 image: shows a normal fixed image, no animation.
    - 2+ images: uses CSS fade slideshow with no long blank period.
    """
    paths = gallery_paths_v89(u)
    if not paths:
        return '<div class="uni-summary-photo-v62 uni-photo-placeholder-v52">No image</div>'

    paths = paths[:8]
    encoded_imgs = []
    for path in paths:
        encoded = b64(path)
        if encoded:
            encoded_imgs.append(encoded)

    if not encoded_imgs:
        return """<div class="uni-slideshow-v89 uni-slideshow-missing-v97">
            <b>No campus image found</b>
            <span>Please re-upload slideshow images in Admin → Universities → Edit Existing Universities, then Save Changes.</span>
        </div>"""

    if len(encoded_imgs) == 1:
        return f"""<div class="uni-slideshow-v89 uni-slideshow-single-v97">
            <img class="uni-slide-img-single-v97" src="data:image/jpeg;base64,{encoded_imgs[0]}"/>
        </div>"""

    n = len(encoded_imgs)
    duration = max(12, n * 4)
    unique = re.sub(r"[^A-Za-z0-9_]+", "_", str(key_suffix or u.get("University", "uni")))

    visible_until = max(6, (100 / n) - 2)
    fade_until = min(5, max(2, visible_until * 0.25))
    keyframe_name = f"uniFadeSlideV97_{unique}_{n}"
    style_block = f"""
    <style>
    @keyframes {keyframe_name} {{
        0% {{ opacity:0; transform:scale(1.03); }}
        {fade_until:.2f}% {{ opacity:1; transform:scale(1.00); }}
        {visible_until:.2f}% {{ opacity:1; transform:scale(1.00); }}
        {(visible_until + fade_until):.2f}% {{ opacity:0; transform:scale(1.02); }}
        100% {{ opacity:0; transform:scale(1.03); }}
    }}
    </style>
    """

    imgs = []
    for i, encoded in enumerate(encoded_imgs):
        delay = -(duration / n) * i
        imgs.append(
            f'<img class="uni-slide-img-v97" style="animation-name:{keyframe_name}; animation-delay:{delay:.2f}s; animation-duration:{duration}s;" src="data:image/jpeg;base64,{encoded}"/>'
        )

    dots = "".join(["<span></span>" for _ in encoded_imgs])
    return f"""{style_block}
    <div class="uni-slideshow-v89 uni-slideshow-multi-v97">
        {''.join(imgs)}
        <div class="uni-slide-gradient-v89"></div>
        <div class="uni-slide-dots-v89">{dots}</div>
    </div>"""

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
        bg = (
            "background-image:"
            "linear-gradient(90deg, rgba(0,31,72,.98) 0%, rgba(0,43,91,.92) 43%, rgba(0,55,115,.58) 70%, rgba(0,31,72,.16) 100%),"
            "url('" + hero_img + "');"
        )

    st.markdown(f"""
    <section class="hero-reference-v69" style="{bg}">
      <div class="hero-dots-v69"></div>
      <div class="hero-inner-v69">
        <div class="hero-step-v69"><span>Step 1</span><b>Home Page</b></div>
        <h1>Partner Portal for<br>University Recruitment</h1>
        <p class="hero-lead-v69">Approved partner agencies can access university details, application requirements, eligibility checking, and tuition/scholarship calculation.</p>
        <div class="hero-buttons-v69">
          <a class="hero-btn-primary-v69" href="?go=signup">👤&nbsp;&nbsp;Apply for Partner Access</a>
          <a class="hero-btn-outline-v69" href="?go=universities">🏛️&nbsp;&nbsp;Explore Universities</a>
        </div>
        <p class="hero-lock-v69">🔒 Detailed information is available only for approved partners.</p>
      </div>
    </section>
    """, unsafe_allow_html=True)

    st.markdown('<div class="section featured-v32"><h2>Featured Universities</h2>', unsafe_allow_html=True)
    unis = universities().reset_index(drop=True)
    uni_records = list(unis.iterrows())

    for row_idx, row_items in enumerate(chunk_records_v53(uni_records, 5)):
        cols = st.columns(5, gap="medium")
        for col_idx, (i, u) in enumerate(row_items):
            with cols[col_idx]:
                image_html = asset_img_html(u.get("Image", ""), "uni-photo")
                location_text = display_value_v53(u.get("Location", ""))
                students_text = student_count_v53(u)
                intl_text = intl_count_v53(u)

                students_html = f"<p>👥 {students_text}</p>" if students_text else ""
                intl_html = f"<p>🌏 {intl_text}</p>" if intl_text else ""

                st.markdown(f"""
                <div class="card uni-card-v53">
                  {image_html}
                  <h3>{display_value_v53(u.get('University',''))}</h3>
                  <p class="muted">📍 {location_text}</p>
                  {students_html}
                  {intl_html}
                </div>
                """, unsafe_allow_html=True)

                if st.button("View Details", key=f"view_v53_{i}", use_container_width=True):
                    st.session_state.selected_uni = u["University"]
                    set_page("Universities")
        if row_idx < (len(uni_records) - 1) // 5:
            st.markdown('<div class="home-row-gap-v53"></div>', unsafe_allow_html=True)

    st.markdown('</div>', unsafe_allow_html=True)

    footer()







def clean_logo_image_v98(uploaded_or_path, canvas_size=900, padding_ratio=0.10):
    """
    Auto-clean uploaded logos:
    - Removes outside white/near-white background.
    - Crops unnecessary empty margins.
    - Centers the logo on a transparent square canvas.
    - Keeps transparent PNG output for a clean shape in cards.
    """
    from PIL import Image, ImageEnhance
    import numpy as np

    img = Image.open(uploaded_or_path).convert("RGBA")
    arr = np.array(img)

    r = arr[:, :, 0].astype(int)
    g = arr[:, :, 1].astype(int)
    b = arr[:, :, 2].astype(int)
    a = arr[:, :, 3].astype(int)

    # Detect background-like pixels. This removes white boxes around logos.
    near_white = (r > 238) & (g > 238) & (b > 238)
    near_gray_bg = (np.abs(r-g) < 8) & (np.abs(g-b) < 8) & (r > 228) & (g > 228) & (b > 228)
    transparent = a < 25

    bg_mask = transparent | near_white | near_gray_bg

    # Foreground includes colored/dark logo parts.
    fg_mask = (~bg_mask) & (a > 25)

    if fg_mask.any():
        ys, xs = np.where(fg_mask)
        x1, x2 = xs.min(), xs.max()
        y1, y2 = ys.min(), ys.max()

        # Add small safety padding before crop.
        w, h = img.size
        pad = max(8, int(max(x2 - x1 + 1, y2 - y1 + 1) * 0.05))
        x1 = max(0, x1 - pad)
        y1 = max(0, y1 - pad)
        x2 = min(w - 1, x2 + pad)
        y2 = min(h - 1, y2 + pad)

        # Make background transparent in original image.
        arr[:, :, 3] = np.where(bg_mask, 0, a)
        img = Image.fromarray(arr, "RGBA").crop((x1, y1, x2 + 1, y2 + 1))
    else:
        # If foreground cannot be detected, just trim alpha bbox or use original.
        bbox = img.getbbox()
        if bbox:
            img = img.crop(bbox)

    # Resize into transparent square canvas.
    target_inner = int(canvas_size * (1 - padding_ratio * 2))
    img.thumbnail((target_inner, target_inner), Image.Resampling.LANCZOS)

    canvas = Image.new("RGBA", (canvas_size, canvas_size), (255, 255, 255, 0))
    x = (canvas_size - img.width) // 2
    y = (canvas_size - img.height) // 2
    canvas.alpha_composite(img, (x, y))

    # Slight sharpening after resize.
    canvas = ImageEnhance.Sharpness(canvas).enhance(1.15)
    return canvas



def save_partner_logo_v83(uploaded_file, agency_id):
    """Save uploaded agency logo after auto-cleaning background and margins."""
    if not uploaded_file:
        return ""
    try:
        safe_id = re.sub(r"[^A-Za-z0-9_]+", "_", str(agency_id or "agency_logo")).strip("_")
        logo_dir = Path("assets") / "partner_logos"
        logo_dir.mkdir(parents=True, exist_ok=True)
        logo_path = logo_dir / f"{safe_id}.png"

        cleaned = clean_logo_image_v98(uploaded_file, canvas_size=900, padding_ratio=0.08)
        cleaned.save(logo_path, "PNG", optimize=True)

        return str(logo_path).replace("\\", "/")
    except Exception:
        return ""


def current_agency_logo_v83():
    """Find logo for the currently logged-in agency/user."""
    try:
        username = st.session_state.get("username", "")
        user = find_user(username) if username else None
        if user and user.get("agency_logo"):
            return user.get("agency_logo", "")
        current_key = normalize_agency_id(current_agency_id() or st.session_state.get("agency_name", ""))
        for u in read_json(USERS):
            if (
                normalize_agency_id(u.get("agency_id", u.get("agency_name", ""))) == current_key
                or normalize_agency_id(u.get("agency_name", "")) == current_key
                or normalize_agency_id(u.get("company_name", "")) == current_key
            ):
                if u.get("agency_logo"):
                    return u.get("agency_logo", "")
        for a in read_agencies():
            if (
                normalize_agency_id(a.get("agency_id", a.get("agency_name", ""))) == current_key
                or normalize_agency_id(a.get("agency_name", "")) == current_key
            ):
                if a.get("agency_logo"):
                    return a.get("agency_logo", "")
    except Exception:
        pass
    return ""

def agency_logo_html_v83(logo_path, class_name="partner-logo-v83"):
    """Render a small agency logo image from a saved local asset path."""
    if not logo_path:
        return ""
    try:
        return asset_img_html(logo_path, class_name)
    except Exception:
        return ""


def signup():
    header()
    left, right = st.columns([0.95, 1.35], gap="large")

    with left:
        st.markdown("""
        <div class="public-left-box navy">
          <h1 style="font-size:44px;line-height:1.12;">Partner Sign Up /<br>Agency Registration</h1>
          <p style="font-size:17px;">Create the correct account type based on your relationship with an official representative agency.</p>
          <hr style="border-color:rgba(255,255,255,.25);">
          <h3>⭐ Official Representative Agency</h3><p>Approved official representatives and approved partner agencies can approve their own staff accounts.</p>
          <h3>👤 Staff Account</h3><p>For employees working inside an official representative agency.</p>
          <h3>🤝 Partner Agency Account</h3><p>For sub-partner companies recommended by an official representative agency.</p>
        </div>
        """, unsafe_allow_html=True)

    with right:
        st.markdown('<div class="public-form-wrap"><div class="white-panel">', unsafe_allow_html=True)
        st.subheader("Create Your Partner Account")
        st.caption("Please select the correct account category and fill in the required information.")

        official_options = official_agency_options_v77()

        # IMPORTANT v78:
        # This selector is OUTSIDE the form so the form fields change immediately when the user changes account category.
        account_category = st.selectbox(
            "Account Category",
            [
                "Staff of Official Representative Agency",
                "Partner Agency of Official Representative",
                "Official Representative Agency"
            ],
            key="signup_account_category_v78",
            help="Choose Staff if you work inside KIEC/Realize. Choose Partner Agency if your company was recommended by KIEC/Realize. Choose Official Representative only for main official partner agencies."
        )

        st.markdown('<div class="signup-category-note-v78">', unsafe_allow_html=True)
        if account_category == "Staff of Official Representative Agency":
            st.markdown("**Staff account**: Your organization will confirm your account.")
        elif account_category == "Partner Agency of Official Representative":
            st.markdown("**Partner agency account**: The official partner you select will review and approve your company account.")
        else:
            st.markdown("**Official representative agency**: This account is reviewed by the portal super admin.")
        st.markdown('</div>', unsafe_allow_html=True)

        with st.form("signup"):
            official_representative = ""
            company_name = ""
            staff_org = ""
            ceo_name = ""
            head_name = ""
            position = ""
            logo_upload = None

            if account_category == "Staff of Official Representative Agency":
                st.markdown("##### Staff Information")
                c1, c2 = st.columns(2)
                with c1:
                    staff_org = st.selectbox("Your Organization / Agency", official_options)
                    name = st.text_input("Staff Full Name")
                    position = st.text_input("Position / Job Title")
                    phone = st.text_input("Contact Number / WhatsApp")
                with c2:
                    email = st.text_input("Email Address")
                    country = st.selectbox("Country", ["Nepal","South Korea","India","Bangladesh","Sri Lanka","Vietnam","Other"])
                    username = st.text_input("Create Username")
                    password = st.text_input("Create Password", type="password")
                confirm = st.text_input("Confirm Password", type="password")
                official_representative = staff_org
                agency_name_clean = staff_org
                role = "agency_staff"
                account_type = "Agency Staff"

            elif account_category == "Partner Agency of Official Representative":
                st.markdown("##### Partner Agency Information")
                c1, c2 = st.columns(2)
                with c1:
                    company_name = st.text_input("Your Organization / Company Name")
                    ceo_name = st.text_input("CEO / Representative Name")
                    head_name = st.text_input("Main Contact Person Name")
                    position = st.text_input("Your Position")
                with c2:
                    official_representative = st.selectbox("Select Official Partner / Recommended By", official_options)
                    email = st.text_input("Email Address")
                    phone = st.text_input("Contact Number / WhatsApp")
                    country = st.selectbox("Country", ["Nepal","South Korea","India","Bangladesh","Sri Lanka","Vietnam","Other"])
                logo_upload = st.file_uploader("Upload Company Logo Image", type=["png", "jpg", "jpeg", "webp"], key="partner_logo_upload_v83")
                u1, u2 = st.columns(2)
                with u1:
                    username = st.text_input("Create Username")
                    password = st.text_input("Create Password", type="password")
                with u2:
                    confirm = st.text_input("Confirm Password", type="password")
                name = head_name or ceo_name
                agency_name_clean = company_name
                role = "agency_partner"
                account_type = "Partner Agency"

            else:
                st.markdown("##### Official Representative Agency Information")
                c1, c2 = st.columns(2)
                with c1:
                    company_name = st.text_input("Official Agency / Company Name")
                    ceo_name = st.text_input("CEO / Representative Name")
                    head_name = st.text_input("Main Contact Person Name")
                    position = st.text_input("Your Position")
                with c2:
                    email = st.text_input("Email Address")
                    phone = st.text_input("Contact Number / WhatsApp")
                    country = st.selectbox("Country", ["Nepal","South Korea","India","Bangladesh","Sri Lanka","Vietnam","Other"])
                    username = st.text_input("Create Username")
                logo_upload = st.file_uploader("Upload Company Logo Image", type=["png", "jpg", "jpeg", "webp"], key="official_logo_upload_v83")
                u1, u2 = st.columns(2)
                with u1:
                    password = st.text_input("Create Password", type="password")
                with u2:
                    confirm = st.text_input("Confirm Password", type="password")
                name = head_name or ceo_name
                official_representative = company_name
                agency_name_clean = company_name
                role = "agency_rep"
                account_type = "Official Representative Agency"

            agree = st.checkbox("I agree to the portal's Terms of Use and Privacy Policy.")

            if st.form_submit_button("Submit for Approval", use_container_width=True):
                required = [agency_name_clean, name, email, phone, username, password, confirm, position]
                if account_category == "Partner Agency of Official Representative":
                    required += [official_representative, company_name, ceo_name]
                if account_category == "Official Representative Agency":
                    required += [company_name, ceo_name]
                if not all([str(x).strip() for x in required]):
                    st.error("Please complete all required fields.")
                elif password != confirm:
                    st.error("Passwords do not match.")
                elif find_user(username):
                    st.error("This username already exists.")
                elif not agree:
                    st.error("Please agree to the terms.")
                else:
                    users = read_json(USERS)
                    agencies = read_agencies()

                    agency_id = normalize_agency_id(agency_name_clean)
                    sponsor_agency_id = normalize_agency_id(official_representative)
                    agency_logo_path = save_partner_logo_v83(logo_upload, agency_id) if logo_upload else ""

                    existing_agency = find_agency_by_name(agency_name_clean)
                    if existing_agency:
                        agency_id = existing_agency.get("agency_id", agency_id)
                    else:
                        agencies.append({
                            "agency_id": agency_id,
                            "agency_name": agency_name_clean,
                            "agency_type": account_category,
                            "official_representative": official_representative,
                            "sponsor_agency_id": sponsor_agency_id if role in ["agency_staff", "agency_partner"] else "",
                            "status": "pending",
                            "agency_logo": agency_logo_path,
                            "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                        })
                        write_agencies(agencies)

                    if role in ["agency_staff", "agency_partner"]:
                        has_approved_rep = bool(approved_reps_for_agency_v75(sponsor_agency_id))
                        approval_scope = "agency" if has_approved_rep else "admin"
                        requested_approver_agency_id = sponsor_agency_id if has_approved_rep else ""
                    else:
                        approval_scope = "admin"
                        requested_approver_agency_id = ""

                    new_user = {
                        "username": username.strip(),
                        "full_name": name.strip(),
                        "agency_name": agency_name_clean.strip(),
                        "agency_id": agency_id,
                        "company_name": company_name.strip() if company_name else agency_name_clean.strip(),
                        "ceo_name": ceo_name.strip(),
                        "head_representative_name": head_name.strip(),
                        "position": position.strip(),
                        "email": email.strip(),
                        "phone": phone.strip(),
                        "agency_logo": agency_logo_path,
                        "country": country,
                        "partner_group": official_representative.strip(),
                        "official_representative": official_representative.strip(),
                        "sponsor_agency_id": sponsor_agency_id if role in ["agency_staff", "agency_partner"] else "",
                        "account_category": account_category,
                        "account_type": account_type,
                        "password_hash": hash_pw(password),
                        "role": role,
                        "status": "pending",
                        "approval_scope": approval_scope,
                        "requested_approver_agency_id": requested_approver_agency_id,
                        "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    }
                    users.append(new_user)
                    write_json(USERS, users)
                    st.session_state.signup_success_v78 = True
                    set_pending_session_v75(new_user)
                    set_page("Pending")
        st.markdown('</div></div>', unsafe_allow_html=True)
    footer()



def pending():
    header()
    user = pending_user_from_session_v75()
    full_name = str(user.get("full_name", "Partner") or "Partner")
    agency_name = str(user.get("agency_name", "your agency") or "your agency")
    email = str(user.get("email", "") or "")
    approver = approval_authority_text_v75(user)

    just_signed_up = st.session_state.pop("signup_success_v78", False)
    thank_title = "Thank you for signing up" if just_signed_up else "Approval Pending"

    st.markdown(f"""
    <div class="pending-hero-v75">
      <span class="pending-step-v75">Step 3 &nbsp; Approval Pending</span>
      <h1>{thank_title},<br>{full_name}</h1>
      <p>Your account is under review and will be confirmed by <b>{approver}</b>.</p>
      <p>You may also contact your selected official partner organization to approve your account faster.</p>
    </div>
    """, unsafe_allow_html=True)
    st.markdown('<div class="section"><div class="two">', unsafe_allow_html=True)
    st.markdown(f"""
    <div class="white-panel"><h2>Application Timeline</h2>
    <p>✅ <b>Application Submitted</b><br><span class="muted">Your registration details have been submitted.</span></p>
    <p>🔵 <b>Under Review</b><br><span class="muted">Approval is pending with {approver}.</span></p>
    <p>⚪ <b>Access Full Platform</b><br><span class="muted">Eligibility check, tuition calculation, and partner dashboard access will open after approval.</span></p></div>
    <div class="white-panel"><h2 style="color:#B54708!important;">Pending Approval</h2>
    <p><b>Agency / Company:</b> {agency_name}</p>
    <p><b>Email:</b> {email}</p>
    <p>Dear {full_name}, your account is under review. You will only be able to use partner services after your account is approved by <b>{approver}</b>.</p>
    <p class="muted">If you selected an official partner such as KIEC or Realize Education, you may contact that organization and ask them to approve your account.</p></div>
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
            password = st.text_input("Password", type="password")
            if st.form_submit_button("Login", use_container_width=True):
                user = find_user(username)
                if not user or user["password_hash"] != hash_pw(password):
                    st.error("Invalid username or password.")
                elif user["status"] != "approved":
                    set_pending_session_v75(user)
                    set_page("Pending")
                else:
                    for k in ["pending_username","pending_full_name","pending_agency_name","pending_email","pending_role","pending_account_type","pending_approval_by"]:
                        st.session_state.pop(k, None)
                    _set_login_session_from_user_v60(user)
                    try:
                        st.query_params["auth"] = st.session_state.get("auth_token", "") or _make_auth_token_v60(user)
                    except Exception:
                        pass
                    set_page("Admin Dashboard" if user["role"] == "admin" else "Dashboard")
        if st.button("Create New Partner Account", key="go_signup_from_login", use_container_width=True):
            set_page("Partner Sign Up")
        st.markdown('</div></div>', unsafe_allow_html=True)
    footer()



def dash_shell(items):
    current_page_v96 = str(st.session_state.get("page", ""))
    role_v96 = str(st.session_state.get("role", ""))

    def _dash_icon_v96(item):
        icon_map = {
            "Admin Dashboard": "☷",
            "Dashboard": "☷",
            "Partner Management": "👥",
            "Universities": "🏛",
            "Eligibility Rules": "🛡",
            "Eligibility Check": "🛡",
            "Tuition Rules": "💲",
            "Tuition & Scholarship": "💲",
            "Scholarship Rules": "🎓",
            "Contact Us": "✉",
        }
        return icon_map.get(item, "•")

    def _dash_href_v96(item):
        auth_suffix = auth_query_suffix_v104("&")
        return "?dashnav=" + str(item).replace(" ", "%20").replace("&", "%26") + auth_suffix

    st.markdown('<div class="dash">', unsafe_allow_html=True)
    st.markdown('<div class="side navy"><h2>Partner Portal</h2></div>', unsafe_allow_html=True)
    with st.container():
        pass
    st.markdown('<div class="main">', unsafe_allow_html=True)

    nav_items_v96 = list(items) + ["Logout"]
    nav_html_parts = ['<div class="dash-nav-v96">']
    for item in nav_items_v96:
        is_active = (current_page_v96 == item)
        if item == "Admin Dashboard" and current_page_v96 in ["Admin Dashboard", ""]:
            is_active = True
        if item == "Dashboard" and current_page_v96 in ["Dashboard", ""]:
            is_active = True
        active_class = " active" if is_active else ""
        logout_class = " logout" if item == "Logout" else ""
        icon = "↪" if item == "Logout" else _dash_icon_v96(item)
        href = _dash_href_v96(item)
        nav_html_parts.append(
            f'<a class="dash-nav-link-v96{active_class}{logout_class}" href="{href}"><span class="dash-nav-icon-v96">{icon}</span><span>{item}</span></a>'
        )
    nav_html_parts.append("</div>")
    st.markdown("".join(nav_html_parts), unsafe_allow_html=True)




admin_shell = dash_shell

def close_shell():
    st.markdown('</div></div>', unsafe_allow_html=True)




def _agency_related_users_v81(users_df, include_pending=True):
    """Return users connected to the current official representative agency."""
    if users_df is None or len(users_df) == 0:
        return pd.DataFrame()
    df = users_df.fillna("").copy()
    current_key = normalize_agency_id(current_agency_id() or st.session_state.get("agency_name", ""))

    related = df[
        (
            df.get("agency_id", "").astype(str).apply(normalize_agency_id).eq(current_key)
            | df.get("agency_name", "").astype(str).apply(normalize_agency_id).eq(current_key)
            | df.get("partner_group", "").astype(str).apply(normalize_agency_id).eq(current_key)
            | df.get("official_representative", "").astype(str).apply(normalize_agency_id).eq(current_key)
            | df.get("sponsor_agency_id", "").astype(str).apply(normalize_agency_id).eq(current_key)
            | df.get("requested_approver_agency_id", "").astype(str).apply(normalize_agency_id).eq(current_key)
        )
        & (df.get("role", "").isin(["agency_staff", "agency_partner"]))
    ].copy()

    if not include_pending:
        related = related[related.get("status", "") == "approved"].copy()

    if len(related):
        related = related.drop_duplicates(subset=["username", "email"], keep="last")
    return related


def _agency_partner_users_v81(users_df, status="approved"):
    related = _agency_related_users_v81(users_df, include_pending=True)
    if len(related) == 0:
        return related
    out = related[related.get("role", "") == "agency_partner"].copy()
    if status:
        out = out[out.get("status", "") == status].copy()
    return out


def _agency_staff_users_v81(users_df, status="approved"):
    related = _agency_related_users_v81(users_df, include_pending=True)
    if len(related) == 0:
        return related
    out = related[related.get("role", "") == "agency_staff"].copy()
    if status:
        out = out[out.get("status", "") == status].copy()
    return out


def _activity_counts_v81(username, elig_df, tuition_df):
    """Counts activity for a partner user. Applications lodged is estimated only if application log columns exist."""
    uname = str(username or "")
    elig_count = 0
    tuition_count = 0
    application_count = 0

    if elig_df is not None and len(elig_df):
        if "partner_username" in elig_df.columns:
            elig_count = len(elig_df[elig_df["partner_username"].astype(str) == uname])
        # If future versions add application status/type columns, count lodged applications here.
        possible_app_cols = [c for c in elig_df.columns if c.lower() in ["application_lodged", "application_status", "lodged", "application"]]
        if possible_app_cols and "partner_username" in elig_df.columns:
            sub = elig_df[elig_df["partner_username"].astype(str) == uname]
            for c in possible_app_cols:
                application_count += sub[c].astype(str).str.lower().isin(["yes", "lodged", "submitted", "applied", "true", "1"]).sum()

    if tuition_df is not None and len(tuition_df):
        if "partner_username" in tuition_df.columns:
            tuition_count = len(tuition_df[tuition_df["partner_username"].astype(str) == uname])

    return int(elig_count), int(tuition_count), int(application_count)


def _user_detail_table_v81(df, elig_df, tuition_df, kind="staff"):
    rows = []
    if df is None or len(df) == 0:
        return pd.DataFrame(rows)

    for _, u in df.iterrows():
        uname = u.get("username", "")
        elig_count, tuition_count, application_count = _activity_counts_v81(uname, elig_df, tuition_df)

        if kind == "partner":
            rows.append({
                "Partner Agency": u.get("agency_name", u.get("company_name", "")),
                "CEO / Representative": u.get("ceo_name", ""),
                "Main Contact": u.get("full_name", u.get("head_representative_name", "")),
                "Position": u.get("position", ""),
                "Contact Number": u.get("phone", ""),
                "Email": u.get("email", ""),
                "Username": uname,
                "Status": u.get("status", ""),
                "Students Counselled / Eligibility Checks": elig_count,
                "Tuition Estimates": tuition_count,
                "Applications Lodged": application_count,
            })
        else:
            rows.append({
                "Staff Name": u.get("full_name", ""),
                "Position": u.get("position", ""),
                "Contact Number": u.get("phone", ""),
                "Email": u.get("email", ""),
                "Username": uname,
                "Status": u.get("status", ""),
                "Students Counselled / Eligibility Checks": elig_count,
                "Tuition Estimates": tuition_count,
                "Applications Lodged": application_count,
            })
    return pd.DataFrame(rows)





def _back_to_partner_dashboard_v85():
    if st.button("← Back to Dashboard", key="v85_back_to_partner_dashboard", use_container_width=False):
        st.session_state.partner_dashboard_view_v81 = "dashboard"
        st.session_state.selected_activity_user_v85 = ""
        st.rerun()


def _activity_data_for_user_v85(username, elig_df, tuition_df):
    uname = str(username or "")
    elig = pd.DataFrame()
    tuition = pd.DataFrame()

    if elig_df is not None and len(elig_df) and "partner_username" in elig_df.columns:
        elig = elig_df[elig_df["partner_username"].astype(str) == uname].copy()

    if tuition_df is not None and len(tuition_df) and "partner_username" in tuition_df.columns:
        tuition = tuition_df[tuition_df["partner_username"].astype(str) == uname].copy()

    return elig, tuition


def _render_single_activity_page_v85(user_row, elig_df, tuition_df, title_prefix="Staff"):
    dash_shell(["Dashboard","Universities","Eligibility Check","Tuition & Scholarship","Contact Us"])
    _back_to_partner_dashboard_v85()

    username = str(user_row.get("Username", "") or user_row.get("username", ""))
    name = str(user_row.get("Staff Name", "") or user_row.get("Partner Agency", "") or user_row.get("full_name", "") or username)
    position = str(user_row.get("Position", "") or user_row.get("position", ""))
    email = str(user_row.get("Email", "") or user_row.get("email", ""))
    phone = str(user_row.get("Contact Number", "") or user_row.get("phone", ""))

    elig, tuition = _activity_data_for_user_v85(username, elig_df, tuition_df)

    st.markdown(f"""
    <div class="v85-page-hero">
        <span>Activity Performance</span>
        <h1>{_safe_html_v62(name)}</h1>
        <p><b>Position:</b> {_safe_html_v62(position if position else "Not provided")} &nbsp; | &nbsp;
        <b>Email:</b> {_safe_html_v62(email if email else "Not provided")} &nbsp; | &nbsp;
        <b>Contact:</b> {_safe_html_v62(phone if phone else "Not provided")}</p>
    </div>
    """, unsafe_allow_html=True)

    elig_count = len(elig)
    tuition_count = len(tuition)
    app_count = int(user_row.get("Applications Lodged", 0) or 0)

    st.markdown(f"""
    <div class="v85-mini-stat-grid">
        <div><b>{elig_count}</b><span>Students Counselled / Eligibility Checks</span></div>
        <div><b>{tuition_count}</b><span>Tuition Estimates</span></div>
        <div><b>{app_count}</b><span>Applications Lodged</span></div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("### Eligibility Check Activity Log")
    if len(elig):
        show_cols = [c for c in elig.columns if c not in ["password_hash"]]
        st.dataframe(elig[show_cols].sort_values("timestamp", ascending=False) if "timestamp" in elig.columns else elig[show_cols], use_container_width=True, hide_index=True)
    else:
        st.info("No eligibility check activity found for this user yet.")

    st.markdown("### Tuition & Scholarship Activity Log")
    if len(tuition):
        show_cols = [c for c in tuition.columns if c not in ["password_hash"]]
        st.dataframe(tuition[show_cols].sort_values("timestamp", ascending=False) if "timestamp" in tuition.columns else tuition[show_cols], use_container_width=True, hide_index=True)
    else:
        st.info("No tuition estimate activity found for this user yet.")

    close_shell()


def _render_staff_list_page_v85(staff_users, elig_df, tuition_df):
    dash_shell(["Dashboard","Universities","Eligibility Check","Tuition & Scholarship","Contact Us"])
    _back_to_partner_dashboard_v85()

    staff_table = _user_detail_table_v81(staff_users, elig_df, tuition_df, kind="staff")
    st.markdown("""
    <div class="v85-page-hero">
        <span>Staff Management</span>
        <h1>Confirmed Staff List</h1>
        <p>View staff contact information and open each staff member's activity/performance log.</p>
    </div>
    """, unsafe_allow_html=True)

    if len(staff_table) == 0:
        st.info("No approved staff accounts yet.")
        close_shell()
        return

    for idx, row in staff_table.iterrows():
        st.markdown(f"""
        <div class="v85-list-card">
            <div>
                <h3>{_safe_html_v62(row.get("Staff Name", ""))}</h3>
                <p><b>Position:</b> {_safe_html_v62(row.get("Position", ""))} &nbsp; | &nbsp;
                <b>Email:</b> {_safe_html_v62(row.get("Email", ""))} &nbsp; | &nbsp;
                <b>Contact:</b> {_safe_html_v62(row.get("Contact Number", ""))}</p>
                <p><b>Username:</b> {_safe_html_v62(row.get("Username", ""))} &nbsp; | &nbsp;
                <b>Status:</b> {_safe_html_v62(row.get("Status", ""))} &nbsp; | &nbsp;
                <b>Eligibility Checks:</b> {row.get("Students Counselled / Eligibility Checks", 0)} &nbsp; | &nbsp;
                <b>Applications Lodged:</b> {row.get("Applications Lodged", 0)}</p>
            </div>
        </div>
        """, unsafe_allow_html=True)

        c1, c2 = st.columns([1, 5])
        with c1:
            if st.button("Activity", key=f"v85_staff_activity_{idx}_{row.get('Username','')}", use_container_width=True):
                st.session_state.partner_dashboard_view_v81 = "staff_activity"
                st.session_state.selected_activity_user_v85 = row.get("Username", "")
                st.rerun()

    close_shell()



def _render_partner_agency_list_page_v85(partner_users, elig_df, tuition_df):
    """
    v87: Official representatives can see confirmed partner agency contact/list details only.
    They cannot view partner agency activity/performance. Only super admin should access partner agency activity.
    """
    dash_shell(["Dashboard","Universities","Eligibility Check","Tuition & Scholarship","Contact Us"])
    _back_to_partner_dashboard_v85()

    partner_table = _user_detail_table_v81(partner_users, elig_df, tuition_df, kind="partner")
    st.markdown("""
    <div class="v85-page-hero">
        <span>Partner Agency Network</span>
        <h1>Confirmed Co-Partner Agencies</h1>
        <p>View approved partner agencies and their contact details. Partner agency activity is visible only to the portal super admin.</p>
    </div>
    """, unsafe_allow_html=True)

    if len(partner_table) == 0:
        st.info("No approved co-partner agencies yet.")
        close_shell()
        return

    # Hide activity/performance columns from official representative view.
    hidden_activity_cols = [
        "Students Counselled / Eligibility Checks",
        "Tuition Estimates",
        "Applications Lodged",
        "Username"
    ]
    display_cols = [c for c in partner_table.columns if c not in hidden_activity_cols]
    st.dataframe(partner_table[display_cols], use_container_width=True, hide_index=True)

    st.info("For privacy and role separation, partner agency performance/activity can be checked only by the portal super admin.")

    close_shell()



def _find_user_activity_row_v85(username, staff_users, partner_users, elig_df, tuition_df):
    """
    v87: Activity lookup for official representative dashboards is staff-only.
    Partner agency activity is reserved for super admin.
    """
    staff_table = _user_detail_table_v81(staff_users, elig_df, tuition_df, kind="staff")
    if len(staff_table):
        match = staff_table[staff_table["Username"].astype(str) == str(username)]
        if len(match):
            return match.iloc[0].to_dict(), "Staff"
    return {}, "User"


def partner_dashboard():
    # v86: Avoid rendering dash_shell twice on separate detail pages.
    # In v85, partner_dashboard() rendered dash_shell first, and then the separate
    # partner/staff/activity pages also rendered dash_shell, causing StreamlitDuplicateElementKey.
    current_view_pre_v86 = st.session_state.get("partner_dashboard_view_v81", "dashboard")
    is_separate_page_v86 = (
        st.session_state.get("role") in ["agency_rep", "agency_partner"]
        and current_view_pre_v86 in ["partners", "staff", "activity", "staff_activity"]
    )
    if not is_separate_page_v86:
        dash_shell(["Dashboard","Universities","Eligibility Check","Tuition & Scholarship","Contact Us"])

    e = read_csv(ELIG_LOGS)
    t = read_csv(TUIT_LOGS)
    users_df = pd.DataFrame(read_json(USERS)).fillna("")

    visible_e = visible_logs(e)
    visible_t = visible_logs(t)

    total_unis = len(universities())
    total_checks = len(visible_e)
    pass_count = len(visible_e[visible_e["result"] == "Eligible"]) if len(visible_e) and "result" in visible_e.columns else 0
    fail_count = len(visible_e[visible_e["result"] == "FAIL"]) if len(visible_e) and "result" in visible_e.columns else 0

    partner_agencies_v81 = _agency_partner_users_v81(users_df, status="approved") if st.session_state.role in ["agency_rep", "agency_partner"] else pd.DataFrame()
    staff_users_v81 = _agency_staff_users_v81(users_df, status="approved") if st.session_state.role in ["agency_rep", "agency_partner"] else pd.DataFrame()
    co_partner_count_v81 = len(partner_agencies_v81)
    staff_count_v81 = len(staff_users_v81)

    # v85: separate detail pages for staff list, partner agency list, and activity.
    if st.session_state.role in ["agency_rep", "agency_partner"]:
        current_view_v85 = st.session_state.get("partner_dashboard_view_v81", "dashboard")
        if current_view_v85 == "staff":
            _render_staff_list_page_v85(staff_users_v81, e, t)
            return
        if current_view_v85 == "partners":
            _render_partner_agency_list_page_v85(partner_agencies_v81, e, t)
            return
        if current_view_v85 == "activity":
            dash_shell(["Dashboard","Universities","Eligibility Check","Tuition & Scholarship","Contact Us"])
            _back_to_partner_dashboard_v85()
            st.markdown("""
            <div class="v85-page-hero">
                <span>Staff Activity</span>
                <h1>All Staff Activity</h1>
                <p>Review staff performance summaries, including student counselling, eligibility checks, tuition estimates, and application counts.</p>
            </div>
            """, unsafe_allow_html=True)
            staff_table_v85 = _user_detail_table_v81(staff_users_v81, e, t, kind="staff")
            if len(staff_table_v85):
                st.markdown("### Staff Activity Summary")
                st.dataframe(staff_table_v85, use_container_width=True, hide_index=True)
            else:
                st.info("No staff activity records yet.")
            close_shell()
            return
        if current_view_v85 == "staff_activity":
            selected_username_v85 = st.session_state.get("selected_activity_user_v85", "")
            row_v85, kind_v85 = _find_user_activity_row_v85(selected_username_v85, staff_users_v81, partner_agencies_v81, e, t)
            if row_v85:
                _render_single_activity_page_v85(row_v85, e, t, kind_v85)
                return
            else:
                st.session_state.partner_dashboard_view_v81 = "dashboard"
                st.warning("The selected staff activity record could not be found.")
                st.rerun()
        if current_view_v85 == "partner_activity":
            # v87: block old/deprecated partner activity route.
            st.session_state.partner_dashboard_view_v81 = "partners"
            st.warning("Partner agency activity is available only to the portal super admin.")
            st.rerun()


    if st.session_state.role in ["agency_rep", "agency_partner"]:
        portal_label = "Agency Representative Portal"
        intro = "Monitor co-partner agency lists, staff activity, eligibility checks, tuition estimates, and student application activity within your organization."
    else:
        portal_label = "Agency Staff Portal"
        intro = "Check student eligibility, estimate tuition and scholarship, and manage your own student records."

    agency_logo_v83 = current_agency_logo_v83()
    agency_logo_html = agency_logo_html_v83(agency_logo_v83, "partner-logo-v83") if agency_logo_v83 else ""
    st.markdown(f"""
    <div class="partner-hero">
        <div class="partner-status-pill">{portal_label}</div>
        <div class="partner-welcome-line-v83">
            <div>
                <h1>Welcome back,<br>{st.session_state.agency_name} {official_rep_badge_v77(st.session_state.agency_name) if st.session_state.role == "agency_rep" else ""}</h1>
            </div>
            {agency_logo_html}
        </div>
        <p>{intro}</p>
    </div>
    """, unsafe_allow_html=True)

    if st.session_state.role in ["agency_rep", "agency_partner"]:
        st.markdown(f"""
        <div class="partner-stat-grid partner-stat-grid-v81">
            <div class="partner-stat-card clickable-stat-v81">
                <h3>Confirmed Co-Partner Agencies</h3>
                <h2>{co_partner_count_v81}</h2>
                <p class="muted">Approved partner agencies</p>
            </div>
            <div class="partner-stat-card clickable-stat-v81">
                <h3>Confirmed Staff</h3>
                <h2>{staff_count_v81}</h2>
                <p class="muted">Approved staff accounts</p>
            </div>
            <div class="partner-stat-card">
                <h3>Eligibility Checks</h3>
                <h2>{total_checks}</h2>
                <p class="muted">Agency-wide records</p>
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

        b1, b2, b3, b4 = st.columns([1.1, 1.1, 1.2, 3.2])
        with b1:
            if st.button("View Partner Agencies", key="v81_view_partner_agencies", use_container_width=True):
                st.session_state.partner_dashboard_view_v81 = "partners"
                st.rerun()
        with b2:
            if st.button("View Staff List", key="v81_view_staff_list", use_container_width=True):
                st.session_state.partner_dashboard_view_v81 = "staff"
                st.rerun()
        with b3:
            if st.button("View Staff Activity", key="v81_view_all_activity", use_container_width=True):
                st.session_state.partner_dashboard_view_v81 = "activity"
                st.rerun()
    else:
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
                <p class="muted">Your records</p>
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

    # Pending approval requests for official representative accounts
    if st.session_state.role in ["agency_rep", "agency_partner"]:
        users_all_v75 = pd.DataFrame(read_json(USERS)).fillna("")
        if len(users_all_v75):
            current_key_v76 = normalize_agency_id(current_agency_id() or st.session_state.get("agency_name", ""))
            pending_staff_v75 = users_all_v75[
                (
                    users_all_v75.get("agency_id", "").astype(str).apply(normalize_agency_id).eq(current_key_v76)
                    | users_all_v75.get("agency_name", "").astype(str).apply(normalize_agency_id).eq(current_key_v76)
                    | users_all_v75.get("partner_group", "").astype(str).apply(normalize_agency_id).eq(current_key_v76)
                    | users_all_v75.get("official_representative", "").astype(str).apply(normalize_agency_id).eq(current_key_v76)
                    | users_all_v75.get("sponsor_agency_id", "").astype(str).apply(normalize_agency_id).eq(current_key_v76)
                    | users_all_v75.get("requested_approver_agency_id", "").astype(str).apply(normalize_agency_id).eq(current_key_v76)
                )
                & (users_all_v75.get("role", "").isin(["agency_staff", "agency_partner"]))
                & (users_all_v75.get("status", "") == "pending")
            ].copy()
            if len(pending_staff_v75):
                pending_staff_v75 = pending_staff_v75.drop_duplicates(subset=["username", "email"], keep="last")
        else:
            pending_staff_v75 = pd.DataFrame()

        if len(pending_staff_v75):
            st.markdown("""
            <div class="partner-panel pending-staff-panel-v75">
                <h2>Staff & Sub-Partner Approval Requests</h2>
                <p>These users selected your agency as their official representative. Please approve only if they are your staff or recommended sub-partner agency.</p>
            </div>
            """, unsafe_allow_html=True)
            for req_idx, (_, req) in enumerate(pending_staff_v75.iterrows()):
                st.markdown(f"""
                <div class="staff-request-card-v75">
                    <h3>{req.get('agency_name','') or req.get('company_name','') or req.get('full_name','')}</h3>
                    <p><b>Applicant:</b> {req.get('full_name','')} &nbsp; | &nbsp; <b>Username:</b> {req.get('username','')} &nbsp; | &nbsp; <b>Email:</b> {req.get('email','')}</p>
                    <p><b>Type:</b> {req.get('account_type', req.get('role',''))} &nbsp; | &nbsp; <b>Position:</b> {req.get('position','')} &nbsp; | &nbsp; <b>Status:</b> <span class="status-pending">pending</span></p>
                </div>
                """, unsafe_allow_html=True)
                ac1, ac2, ac3 = st.columns([1,1,4])
                with ac1:
                    if st.button("Approve Request", key=_unique_admin_key_v72("agency_staff_approve", req_idx, req), use_container_width=True):
                        changed = approve_or_reject_partner_request_v80(req, "approved")
                        if changed:
                            st.success(f"{req.get('agency_name','') or req.get('company_name','') or req.get('full_name','Request')} approved.")
                        else:
                            st.error("This request could not be approved. Please check whether this user selected your agency as the official representative.")
                        st.rerun()
                with ac2:
                    if st.button("Reject Request", key=_unique_admin_key_v72("agency_staff_reject", req_idx, req), use_container_width=True):
                        changed = approve_or_reject_partner_request_v80(req, "rejected")
                        if changed:
                            st.warning(f"{req.get('agency_name','') or req.get('company_name','') or req.get('full_name','Request')} rejected.")
                        else:
                            st.error("This request could not be rejected. Please check whether this user selected your agency as the official representative.")
                        st.rerun()

    # Detailed partner/staff panels for official representatives
    if st.session_state.role in ["agency_rep", "agency_partner"]:
        view_v81 = st.session_state.get("partner_dashboard_view_v81", "partners")

        if view_v81 == "partners":
            st.markdown('<div class="partner-panel v81-detail-panel"><h2>Confirmed Co-Partner Agencies</h2><p>Approved sub-partner agencies confirmed under your official representative account.</p></div>', unsafe_allow_html=True)
            partner_table = _user_detail_table_v81(partner_agencies_v81, e, t, kind="partner")
            if len(partner_table):
                st.dataframe(partner_table, use_container_width=True, hide_index=True)
            else:
                st.info("No approved co-partner agencies yet.")

        elif view_v81 == "staff":
            st.markdown('<div class="partner-panel v81-detail-panel"><h2>Confirmed Staff List</h2><p>Approved staff accounts under your organization, with contact information and activity counts.</p></div>', unsafe_allow_html=True)
            staff_table = _user_detail_table_v81(staff_users_v81, e, t, kind="staff")
            if len(staff_table):
                st.dataframe(staff_table, use_container_width=True, hide_index=True)
            else:
                st.info("No approved staff accounts yet.")

        elif view_v81 == "activity":
            st.markdown('<div class="partner-panel v81-detail-panel"><h2>Agency Network Activity Log</h2><p>Combined activity for staff and co-partner agencies. Applications Lodged will show values when application tracking data is added.</p></div>', unsafe_allow_html=True)
            all_related = pd.concat([staff_users_v81, partner_agencies_v81], ignore_index=True) if len(staff_users_v81) or len(partner_agencies_v81) else pd.DataFrame()
            activity_staff = _user_detail_table_v81(staff_users_v81, e, t, kind="staff")
            activity_partner = _user_detail_table_v81(partner_agencies_v81, e, t, kind="partner")
            if len(activity_staff) or len(activity_partner):
                if len(activity_staff):
                    st.markdown("#### Staff Activity")
                    st.dataframe(activity_staff, use_container_width=True, hide_index=True)
                if len(activity_partner):
                    st.markdown("#### Co-Partner Agency Activity")
                    st.dataframe(activity_partner, use_container_width=True, hide_index=True)
            else:
                st.info("No agency network activity yet.")

    left, right = st.columns([1.25, .9], gap="large")

    with left:
        st.markdown('<div class="partner-panel">', unsafe_allow_html=True)
        st.subheader("Recent Student Eligibility Checks")
        if len(visible_e):
            st.dataframe(visible_e.sort_values("timestamp", ascending=False).head(12), use_container_width=True, hide_index=True)
        else:
            st.info("No eligibility checks yet.")
        st.markdown('</div>', unsafe_allow_html=True)

        if st.session_state.role in ["agency_rep", "agency_partner"]:
            st.markdown('<br>', unsafe_allow_html=True)
            st.markdown('<div class="partner-panel">', unsafe_allow_html=True)
            st.subheader("Staff Activity Summary")
            staff_table = _user_detail_table_v81(staff_users_v81, e, t, kind="staff")
            partner_table = _user_detail_table_v81(partner_agencies_v81, e, t, kind="partner")
            if len(staff_table):
                temp = staff_table.copy()
                temp.insert(0, "Type", "Staff")
                st.dataframe(temp, use_container_width=True, hide_index=True)
            else:
                st.info("No approved staff accounts found yet.")
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





def _scholarship_percent_to_number_v62(value):
    s = str(value or "").strip()
    if not s or s.lower() in ["nan", "none", "null", "<na>"]:
        return 0.0
    try:
        x = float(s)
        if 0 < x <= 1:
            return x * 100
        return x
    except Exception:
        pass
    m = re.search(r"(\d+(?:\.\d+)?)\s*%", s)
    if m:
        try:
            return float(m.group(1))
        except Exception:
            return 0.0
    m = re.search(r"\b0\.(\d+)\b", s)
    if m:
        try:
            return float("0." + m.group(1)) * 100
        except Exception:
            return 0.0
    return 0.0


@st.cache_data(ttl=300, show_spinner=False)
def university_max_scholarship_map_v62():
    sch = scholarship_rules()
    if sch is None or len(sch) == 0 or "University" not in sch.columns:
        return {}

    values = {}
    for _, r in sch.iterrows():
        uni = str(r.get("University", "")).strip()
        if not uni:
            continue
        pct_candidates = [
            _scholarship_percent_to_number_v62(r.get("Scholarship_Percent", "")),
            _scholarship_percent_to_number_v62(r.get("Scholarship_Text", "")),
            _scholarship_percent_to_number_v62(r.get("Language_Criteria", "")),
        ]
        pct = max(pct_candidates)
        values[uni] = max(values.get(uni, 0.0), pct)
    return values


def _location_value_v62(row):
    parts = []
    for col in ["Location", "Region"]:
        v = display_clean_v50(row.get(col, ""))
        if v:
            parts.append(v)
    return " / ".join(parts)



def _parse_date_v64(value):
    try:
        s = str(value or "").strip()
        if not s or s.lower() in ["nan", "none", "null", "<na>"]:
            return None
        return pd.to_datetime(s).date()
    except Exception:
        return None


def _auto_application_status_v65(open_date_value=None, close_date_value=None, fallback_status=""):
    """
    Automatic application status rule:
    - Before open date: Application Opens Soon
    - From open date until close date: Application Open
    - After close date: Application Closed
    - If dates are missing, use selected/fallback status.
    """
    today = datetime.now().date()
    open_date = _parse_date_v64(open_date_value)
    close_date = _parse_date_v64(close_date_value)
    fallback = str(fallback_status or "").strip()

    if open_date and today < open_date:
        return "Application Opens Soon"
    if close_date and today > close_date:
        return "Application Closed"
    if open_date and today >= open_date:
        return "Application Open"
    if close_date and today <= close_date:
        return "Application Open"
    if fallback in ["Application Open", "Application Closed", "Application Opens Soon"]:
        return fallback
    return "Application Status Not Provided"


def _application_status_v64_from_row(row):
    """
    Supports admin-managed Application_Status, Application_Open_Date, and Application_Close_Date.
    Dates have priority so the website status changes automatically.
    """
    raw = str(row.get("Application_Status", "") or row.get("Application Status Auto Calculated", "") or "").strip()
    intake = str(row.get("Intake", "") or "").strip().lower()
    open_date = row.get("Application_Open_Date", "") or row.get("Application Open Date", "")
    close_date = row.get("Application_Close_Date", "") or row.get("Application Close Date", "")

    auto_status = _auto_application_status_v65(open_date, close_date, raw)
    if auto_status != "Application Status Not Provided":
        return auto_status

    source = intake
    if any(x in source for x in ["closed", "close", "not open", "not opened"]):
        return "Application Closed"
    if any(x in source for x in ["soon", "upcoming", "coming"]):
        return "Application Opens Soon"
    if any(x in source for x in ["march", "september", "spring", "fall", "open", "opened"]):
        return "Application Open"

    return "Application Status Not Provided"



def _parse_date_v66(value):
    """Parse common date formats from admin fields."""
    s = str(value or "").strip()
    if not s or s.lower() in ["nan", "none", "null", "<na>"]:
        return None
    for fmt in ["%Y/%m/%d", "%Y-%m-%d", "%Y.%m.%d", "%m/%d/%Y", "%d/%m/%Y"]:
        try:
            return datetime.strptime(s, fmt).date()
        except Exception:
            pass
    try:
        return pd.to_datetime(s, errors="coerce").date()
    except Exception:
        return None


def _format_date_v66(value):
    d = _parse_date_v66(value)
    return d.strftime("%Y/%m/%d") if d else ""


def _calculate_application_status_v66(open_date_value, close_date_value="", fallback_status=""):
    """
    Status is directly linked with dates:
    - today < open date: Application Opens Soon
    - open date <= today <= close date: Application Open
    - today > close date: Application Closed
    If no dates are entered, fallback status can still be used.
    """
    today = datetime.now().date()
    open_d = _parse_date_v66(open_date_value)
    close_d = _parse_date_v66(close_date_value)

    if open_d and today < open_d:
        return "Application Opens Soon"
    if close_d and today > close_d:
        return "Application Closed"
    if open_d and today >= open_d:
        return "Application Open"
    if close_d and today <= close_d:
        return "Application Open"

    fs = str(fallback_status or "").strip()
    if fs in ["Application Open", "Application Closed", "Application Opens Soon"]:
        return fs
    return "Application Status Not Provided"


def _application_status_v66_from_row(row):
    return _calculate_application_status_v66(
        row.get("Application_Open_Date", row.get("Application Open Date", "")),
        row.get("Application_Close_Date", row.get("Application Close Date", "")),
        row.get("Application_Status", row.get("Application Status Auto Calculated", "")),
    )


def _application_status_class_v63(status):
    s = str(status or "").lower()
    if "closed" in s:
        return "app-status-closed-v63"
    if "soon" in s:
        return "app-status-soon-v63"
    if "open" in s:
        return "app-status-open-v63"
    return "app-status-none-v63"


def _intake_is_open_v62(value):
    s = str(value or "").strip().lower()
    if not s:
        return False
    if any(x in s for x in ["closed", "not open", "not opened"]):
        return False
    return True


def _application_status_v62(value):
    return "Application Open" if _intake_is_open_v62(value) else "Application Status Not Provided"


def _safe_html_v62(value):
    return str(value or "").replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")



def _program_badges_html_v64(university_name):
    """
    Build program badges for university cards/details.
    Prevents NameError and shows program availability instead of location/intake/scholarship badges.
    """
    try:
        crit = criteria()
        uni = str(university_name or "").strip()
        subset = pd.DataFrame()
        if crit is not None and len(crit) and "University" in crit.columns:
            subset = crit[crit["University"].astype(str).str.strip() == uni]

        text_blob = " ".join(map(str, subset.values.flatten())).lower() if len(subset) else ""

        badges = []
        if "undergraduate" in text_blob or "bachelor" in text_blob:
            badges.append("Undergraduate")
        if "graduate" in text_blob or "master" in text_blob or "ph.d" in text_blob or "phd" in text_blob:
            badges.append("Graduate (Masters/Ph.D.)")
        if "korean language" in text_blob or "klp" in text_blob or "eap" in text_blob:
            badges.append("KLP/EAP")

        # If criteria text is incomplete, keep the three requested program categories visible.
        if not badges:
            badges = ["Undergraduate", "Graduate (Masters/Ph.D.)", "KLP/EAP"]

        return "".join([f'<span class="program-badge-v64">{_safe_html_v62(b)}</span>' for b in badges])
    except Exception:
        return (
            '<span class="program-badge-v64">Undergraduate</span>'
            '<span class="program-badge-v64">Graduate (Masters/Ph.D.)</span>'
            '<span class="program-badge-v64">KLP/EAP</span>'
        )





def program_slug_v109(label):
    label_l = str(label or "").lower()
    if "undergraduate" in label_l:
        return "undergraduate"
    if "graduate" in label_l:
        return "graduate"
    if "klp" in label_l or "eap" in label_l or "language" in label_l:
        return "language"
    return re.sub(r"[^a-z0-9]+", "-", label_l).strip("-") or "program"

def program_detail_href_v109(row, label):
    from urllib.parse import quote_plus
    uni = quote_plus(str(row.get("University", "")))
    program = quote_plus(program_slug_v109(label))
    auth = ""
    try:
        auth = auth_query_suffix_v104("&")
    except Exception:
        auth = ""
    return f"?nav=Universities&uni={uni}&programdetail={program}{auth}"

def _program_specific_application_badges_v71(row):
    """
    v109: Shows Undergraduate, Graduate, and KLP/EAP as clickable application cards.
    Clicking a card opens a program-specific detail and application page.
    """
    general_open = row.get("Application_Open_Date", "")
    general_close = row.get("Application_Close_Date", "")

    programs = [
        ("Undergraduate", "UG_Open_Date", "UG_Close_Date"),
        ("Graduate (Masters/Ph.D.)", "Graduate_Open_Date", "Graduate_Close_Date"),
        ("KLP/EAP", "KLP_EAP_Open_Date", "KLP_EAP_Close_Date"),
    ]

    html = ""
    for label, open_col, close_col in programs:
        open_date = row.get(open_col, "") or general_open
        close_date = row.get(close_col, "") or general_close
        status = _calculate_application_status_v66(open_date, close_date, row.get("Application_Status", ""))
        status_class = _application_status_class_v63(status)
        open_txt = _format_date_v66(open_date) or "Not set"
        close_txt = _format_date_v66(close_date) or "Not set"
        href = program_detail_href_v109(row, label)
        html += (
            f'<a class="program-date-card-v71 program-click-card-v109" href="{href}">'
            f'<b>{_safe_html_v62(label)}</b>'
            f'<span class="{status_class}">{_safe_html_v62(status)}</span>'
            f'<small>Open: {_safe_html_v62(open_txt)}</small>'
            f'<small>Close: {_safe_html_v62(close_txt)}</small>'
            f'<em>View Details & Apply →</em>'
            f'</a>'
        )
    return html

def get_program_dates_v109(u, program_slug, application_type=""):
    general_open = u.get("Application_Open_Date", "")
    general_close = u.get("Application_Close_Date", "")
    program_slug = str(program_slug or "").lower()
    application_type = str(application_type or "").lower()

    if program_slug == "undergraduate":
        if "transfer" in application_type:
            open_date = u.get("UG_Transfer_Open_Date", "") or u.get("UG_Open_Date", "") or general_open
            close_date = u.get("UG_Transfer_Close_Date", "") or u.get("UG_Close_Date", "") or general_close
        elif "new" in application_type:
            open_date = u.get("UG_New_Open_Date", "") or u.get("UG_Open_Date", "") or general_open
            close_date = u.get("UG_New_Close_Date", "") or u.get("UG_Close_Date", "") or general_close
        else:
            open_date = u.get("UG_Open_Date", "") or general_open
            close_date = u.get("UG_Close_Date", "") or general_close
    elif program_slug == "graduate":
        open_date = u.get("Graduate_Open_Date", "") or general_open
        close_date = u.get("Graduate_Close_Date", "") or general_close
    elif program_slug == "language":
        if "eap" in application_type:
            open_date = u.get("EAP_Open_Date", "") or u.get("KLP_EAP_Open_Date", "") or general_open
            close_date = u.get("EAP_Close_Date", "") or u.get("KLP_EAP_Close_Date", "") or general_close
        elif "klp" in application_type:
            open_date = u.get("KLP_Open_Date", "") or u.get("KLP_EAP_Open_Date", "") or general_open
            close_date = u.get("KLP_Close_Date", "") or u.get("KLP_EAP_Close_Date", "") or general_close
        else:
            open_date = u.get("KLP_EAP_Open_Date", "") or general_open
            close_date = u.get("KLP_EAP_Close_Date", "") or general_close
    else:
        open_date, close_date = general_open, general_close

    status = _calculate_application_status_v66(open_date, close_date, u.get("Application_Status", ""))
    return open_date, close_date, status

def program_class_schedule_text_v109(program_slug):
    program_slug = str(program_slug or "").lower()
    if program_slug == "undergraduate":
        return ("First-semester undergraduate students usually attend classes around 3–4 days per week. "
                "From the second semester, students can register credits by themselves and arrange class days "
                "around 2, 3, or 4 days per week depending on course availability and the official timetable.")
    if program_slug == "graduate":
        return ("Graduate students usually attend classes around 1–2 days per week, depending on the department, "
                "course schedule, and thesis/research requirements.")
    if program_slug == "language":
        return ("Korean language or EAP students usually attend classes 5 days per week because language study "
                "programs are normally intensive and follow a regular weekday schedule.")
    return ""

def program_major_list_html_v109(university, program_slug):
    df = criteria()
    if df is None or len(df) == 0 or "University" not in df.columns:
        return '<p class="program-muted-v109">No program or major information has been registered yet.</p>'
    sub = df[df["University"].astype(str).str.strip().str.lower() == str(university).strip().lower()].copy()
    if len(sub) == 0:
        return '<p class="program-muted-v109">No program or major information has been registered yet.</p>'

    ps = str(program_slug or "").lower()
    if "Program" in sub.columns:
        if ps == "undergraduate":
            sub = sub[sub["Program"].astype(str).str.lower().str.contains("undergraduate|bachelor", regex=True, na=False)]
        elif ps == "graduate":
            sub = sub[sub["Program"].astype(str).str.lower().str.contains("graduate|master|ph|ph.d|phd", regex=True, na=False)]
        elif ps == "language":
            sub = sub[sub["Program"].astype(str).str.lower().str.contains("language|klp|eap|korean", regex=True, na=False)]
    if len(sub) == 0:
        return '<p class="program-muted-v109">No specific major list is available for this category yet.</p>'

    items = []
    for _, r in sub.head(30).iterrows():
        major = display_clean_v50(r.get("Major", ""))
        program = display_clean_v50(r.get("Program", ""))
        ielts = display_clean_v50(r.get("IELTS_Criteria", r.get("Minimum_IELTS", "")))
        gpa = display_clean_v50(r.get("GPA_Criteria", r.get("Minimum_GPA", "")))
        fee = display_clean_v50(r.get("Application_Fee_KRW", ""))
        detail_bits = []
        if ielts: detail_bits.append(f"Language: {_safe_html_v62(ielts)}")
        if gpa: detail_bits.append(f"GPA: {_safe_html_v62(gpa)}")
        if fee: detail_bits.append(f"Application fee: KRW {_safe_html_v62(str(fee))}")
        detail_text = " · ".join(detail_bits)
        items.append(
            f'<div class="program-major-card-v109">'
            f'<b>{_safe_html_v62(major or program or "Program")}</b>'
            f'<span>{_safe_html_v62(program)}</span>'
            f'<small>{detail_text}</small>'
            f'</div>'
        )
    return "".join(items)

def program_timeline_card_v109(u, program_slug, label, application_type=""):
    open_date, close_date, status = get_program_dates_v109(u, program_slug, application_type)
    status_class = _application_status_class_v63(status)
    return (
        f'<div class="program-timeline-card-v109">'
        f'<b>{_safe_html_v62(label)}</b>'
        f'<span class="{status_class}">{_safe_html_v62(status)}</span>'
        f'<small>Open: {_safe_html_v62(_format_date_v66(open_date) or "Not set")}</small>'
        f'<small>Close: {_safe_html_v62(_format_date_v66(close_date) or "Not set")}</small>'
        f'</div>'
    )

def render_application_start_form_v109(u, program_slug, application_type):
    st.markdown(f"""
    <div class="application-start-panel-v109">
        <h3>Start Application</h3>
        <p>You are starting: <b>{_safe_html_v62(application_type)}</b> for <b>{_safe_html_v62(u.get("University", ""))}</b>.</p>
    </div>
    """, unsafe_allow_html=True)

    with st.form(f"application_start_v109_{safe_slug_v49(u.get('University',''))}_{program_slug}_{safe_slug_v49(application_type)}"):
        c1, c2 = st.columns(2)
        with c1:
            applicant_name = st.text_input("Applicant Full Name")
            email = st.text_input("Email Address")
            nationality = st.text_input("Nationality")
        with c2:
            phone = st.text_input("Phone / WhatsApp")
            passport = st.text_input("Passport Number")
            desired_major = st.text_input("Desired Major / Program")
        note = st.text_area("Additional Notes", height=90)
        submitted = st.form_submit_button("Submit Application Request", use_container_width=True)
        if submitted:
            if not applicant_name.strip() or not email.strip():
                st.error("Applicant name and email are required.")
            else:
                try:
                    app_file = DATA / "student_applications.csv"
                    existing = read_csv(app_file)
                    new_row = {
                        "Submitted_At": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                        "University": u.get("University", ""),
                        "Program_Category": program_slug,
                        "Application_Type": application_type,
                        "Applicant_Name": applicant_name.strip(),
                        "Email": email.strip(),
                        "Phone": phone.strip(),
                        "Nationality": nationality.strip(),
                        "Passport_Number": passport.strip(),
                        "Desired_Major": desired_major.strip(),
                        "Notes": note.strip(),
                        "Submitted_By": st.session_state.get("username", "public"),
                        "Agency": st.session_state.get("agency_name", ""),
                        "Status": "New Request",
                    }
                    existing = pd.concat([existing, pd.DataFrame([new_row])], ignore_index=True)
                    write_csv(app_file, existing)
                    st.success("Application request submitted. The portal team or partner agency can follow up with the applicant.")
                except Exception as e:
                    st.success("Application request submitted.")
                    st.caption(f"Note: application log could not be saved automatically: {e}")

def render_program_detail_page_v109(u, program_slug):
    program_slug = str(program_slug or "undergraduate").lower()
    program_title_map = {
        "undergraduate": "Undergraduate Programs",
        "graduate": "Graduate Programs (Masters/Ph.D.)",
        "language": "KLP/EAP Language Programs",
    }
    title = program_title_map.get(program_slug, "Program Details")
    logo_html = university_logo_html_v88(u.get("University_Logo", ""), u.get("University", ""))
    schedule_text = program_class_schedule_text_v109(program_slug)
    majors_html = program_major_list_html_v109(u.get("University", ""), program_slug)

    st.markdown(f"""
    <div class="program-detail-page-v109">
        <div class="program-detail-head-v109">
            <div class="program-detail-logo-v109">{logo_html}</div>
            <div>
                <p>{_safe_html_v62(u.get("University", ""))}</p>
                <h1>{_safe_html_v62(title)}</h1>
                <span>{_safe_html_v62(schedule_text)}</span>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # Timeline cards and application options
    if program_slug == "undergraduate":
        timeline_html = (
            program_timeline_card_v109(u, "undergraduate", "New Student Application", "new")
            + program_timeline_card_v109(u, "undergraduate", "Transfer Application", "transfer")
        )
        st.markdown(f'<div class="program-timeline-grid-v109">{timeline_html}</div>', unsafe_allow_html=True)
        c1, c2, c3 = st.columns([1,1,2])
        with c1:
            if st.button("Apply as New Student", key=f"apply_new_v109_{safe_slug_v49(u.get('University',''))}", use_container_width=True):
                st.session_state.application_type_v109 = "Undergraduate New Student Application"
                st.rerun()
        with c2:
            if st.button("Apply as Transfer Student", key=f"apply_transfer_v109_{safe_slug_v49(u.get('University',''))}", use_container_width=True):
                st.session_state.application_type_v109 = "Undergraduate Transfer Application"
                st.rerun()
    elif program_slug == "graduate":
        timeline_html = program_timeline_card_v109(u, "graduate", "Graduate Application", "graduate")
        st.markdown(f'<div class="program-timeline-grid-v109 single-v109">{timeline_html}</div>', unsafe_allow_html=True)
        c1, c2 = st.columns([1,3])
        with c1:
            if st.button("Apply for Graduate", key=f"apply_grad_v109_{safe_slug_v49(u.get('University',''))}", use_container_width=True):
                st.session_state.application_type_v109 = "Graduate Application"
                st.rerun()
    elif program_slug == "language":
        timeline_html = (
            program_timeline_card_v109(u, "language", "KLP Application", "klp")
            + program_timeline_card_v109(u, "language", "EAP Application", "eap")
        )
        st.markdown(f'<div class="program-timeline-grid-v109">{timeline_html}</div>', unsafe_allow_html=True)
        c1, c2, c3 = st.columns([1,1,2])
        with c1:
            if st.button("Apply for KLP", key=f"apply_klp_v109_{safe_slug_v49(u.get('University',''))}", use_container_width=True):
                st.session_state.application_type_v109 = "KLP Application"
                st.rerun()
        with c2:
            if st.button("Apply for EAP", key=f"apply_eap_v109_{safe_slug_v49(u.get('University',''))}", use_container_width=True):
                st.session_state.application_type_v109 = "EAP Application"
                st.rerun()

    app_type = st.session_state.get("application_type_v109", "")
    if app_type:
        render_application_start_form_v109(u, program_slug, app_type)

    st.markdown(f"""
    <div class="program-major-section-v109">
        <h3>Programs / Majors</h3>
        <div class="program-major-grid-v109">{majors_html}</div>
    </div>
    """, unsafe_allow_html=True)




# v106 student enrollment / nationality statistics helpers
COUNTRY_ISO_OVERRIDES_V108 = {
    # Common countries for international student data
    "nepal": "np", "bangladesh": "bd", "vietnam": "vn", "viet nam": "vn",
    "indonesia": "id", "pakistan": "pk", "india": "in", "sri lanka": "lk",
    "china": "cn", "people's republic of china": "cn", "pr china": "cn",
    "mongolia": "mn", "myanmar": "mm", "burma": "mm", "uzbekistan": "uz",
    "kazakhstan": "kz", "kyrgyzstan": "kg", "tajikistan": "tj",
    "philippines": "ph", "the philippines": "ph", "japan": "jp",
    "thailand": "th", "malaysia": "my", "cambodia": "kh", "laos": "la",
    "taiwan": "tw", "hong kong": "hk", "singapore": "sg",

    # Korea and common western countries
    "korea": "kr", "south korea": "kr", "republic of korea": "kr",
    "usa": "us", "u.s.a.": "us", "united states": "us", "united states of america": "us",
    "canada": "ca", "australia": "au", "new zealand": "nz",
    "uk": "gb", "u.k.": "gb", "united kingdom": "gb", "england": "gb",
    "france": "fr", "germany": "de", "italy": "it", "spain": "es",
    "russia": "ru", "russian federation": "ru",

    # Middle East / Africa / Latin America common cases
    "iran": "ir", "iraq": "iq", "saudi arabia": "sa", "turkey": "tr",
    "egypt": "eg", "nigeria": "ng", "ghana": "gh", "kenya": "ke",
    "ethiopia": "et", "south africa": "za", "brazil": "br", "mexico": "mx",
}

def country_iso_code_v108(country):
    """Return ISO-2 code from country name in uploaded Excel. Case-insensitive and accepts common aliases."""
    name = str(country or "").strip().lower()
    name = re.sub(r"\\s+", " ", name)
    name = name.replace("&", "and")
    if name in COUNTRY_ISO_OVERRIDES_V108:
        return COUNTRY_ISO_OVERRIDES_V108[name]

    # Handle names that include extra text, e.g., "Nepalese / Nepal", "Vietnam students".
    for key, iso in COUNTRY_ISO_OVERRIDES_V108.items():
        if key and (name == key or key in name):
            return iso
    return ""

def country_flag_html_v108(country):
    """Return an actual country flag image automatically from country name."""
    iso = country_iso_code_v108(country)
    safe_country = _safe_html_v62(country)
    if iso:
        return (
            f'<span class="flag-img-wrap-v108" title="{safe_country}">'
            f'<img class="flag-img-v108" src="https://flagcdn.com/w80/{iso}.png" alt="{safe_country} flag" loading="lazy" />'
            f'</span>'
        )

    # Fallback when country name is not mapped: show first two letters, not a fake country flag.
    initials = "".join([w[:1] for w in re.findall(r"[A-Za-z]+", str(country or ""))[:2]]).upper() or "🌐"
    return f'<span class="flag-fallback-v108" title="{safe_country}">{_safe_html_v62(initials)}</span>'

def _to_int_v106(value):
    try:
        s = str(value or "").replace(",", "").strip()
        if s == "" or s.lower() in ["nan", "none", "null", "<na>"]:
            return 0
        return int(float(s))
    except Exception:
        return 0

def student_stats_template_bytes_v106():
    """Excel template for admin upload. Requires openpyxl in requirements."""
    output = BytesIO()
    summary = pd.DataFrame([{
        "Data_Year": "2026",
        "Undergraduate_Students": 1200,
        "Graduate_Students": 450,
        "Language_Study_Students": 180,
    }])
    nationality = pd.DataFrame([
        {"Country": "Nepal", "Number_of_Students": 120},
        {"Country": "Vietnam", "Number_of_Students": 95},
        {"Country": "China", "Number_of_Students": 80},
        {"Country": "Bangladesh", "Number_of_Students": 65},
        {"Country": "India", "Number_of_Students": 45},
    ])
    instructions = pd.DataFrame([
        {"Instruction": "Fill the Summary sheet with one row only."},
        {"Instruction": "Fill Data_Year as the year or semester of the data, for example 2026 or 2026 Spring."},
        {"Instruction": "Fill Undergraduate_Students, Graduate_Students, and Language_Study_Students as numbers."},
        {"Instruction": "Fill the Nationality sheet with Country and Number_of_Students. Type normal country names such as Nepal, Bangladesh, Vietnam, Indonesia, Pakistan. Flags will be added automatically."},
        {"Instruction": "The system will automatically show the top 5 nationality groups on the university detail page."},
        {"Instruction": "This upload is optional. If no file is uploaded, no graph will be shown."},
    ])
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        summary.to_excel(writer, sheet_name="Summary", index=False)
        nationality.to_excel(writer, sheet_name="Nationality", index=False)
        instructions.to_excel(writer, sheet_name="Instructions", index=False)
    output.seek(0)
    return output.getvalue()


def student_stats_template_download_html_v107():
    """HTML download link for the student statistics Excel template.
    This can be placed next to file_uploader inside Streamlit forms.
    """
    try:
        encoded = base64.b64encode(student_stats_template_bytes_v106()).decode("utf-8")
        mime = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        return f"""
        <a class="excel-template-download-v107" href="data:{mime};base64,{encoded}" download="university_student_statistics_template.xlsx">
            <span>📥</span><b>Download Excel Format</b>
        </a>
        """
    except Exception:
        return '<div class="excel-template-download-v107 disabled"><span>📥</span><b>Template unavailable</b></div>'

def student_stats_upload_info_html_v107():
    return """
    <div class="student-stats-upload-info-v107">
        <b>What is this Excel upload for?</b>
        <p>This optional file creates the student statistics section in the university detail page. It shows a graph of enrolled students by program level and the top 5 international student nationalities with country flags.</p>
        <ul>
            <li><b>Summary sheet:</b> Data_Year, Undergraduate_Students, Graduate_Students, Language_Study_Students</li>
            <li><b>Nationality sheet:</b> Country, Number_of_Students. Type country names normally; flags are added automatically.</li>
            <li>If you do not upload this file, the student graph will simply not appear.</li>
        </ul>
    </div>
    """

def parse_student_stats_excel_v106(uploaded_file):
    """Parse optional student statistics Excel upload."""
    result = {
        "Student_Data_Year": "",
        "Undergraduate_Students": "",
        "Graduate_Students": "",
        "Language_Study_Students": "",
        "Nationality_Students_JSON": "[]",
    }
    if uploaded_file is None:
        return result
    try:
        sheets = pd.read_excel(uploaded_file, sheet_name=None, keep_default_na=False)
        summary_df = None
        nationality_df = None
        for name, sdf in sheets.items():
            lname = str(name).lower().strip()
            if "summary" in lname or "student" in lname:
                summary_df = sdf
            if "national" in lname or "country" in lname:
                nationality_df = sdf
        if summary_df is None and sheets:
            summary_df = list(sheets.values())[0]
        if nationality_df is None and len(sheets) > 1:
            nationality_df = list(sheets.values())[1]

        if summary_df is not None and len(summary_df) > 0:
            row = summary_df.iloc[0]
            lower_cols = {str(c).strip().lower(): c for c in summary_df.columns}
            def get_col(*names):
                for n in names:
                    if n.lower() in lower_cols:
                        return row.get(lower_cols[n.lower()], "")
                for lc, orig in lower_cols.items():
                    for n in names:
                        if n.lower() in lc:
                            return row.get(orig, "")
                return ""
            result["Student_Data_Year"] = str(get_col("Data_Year", "Year", "Data Until Year")).strip()
            result["Undergraduate_Students"] = str(_to_int_v106(get_col("Undergraduate_Students", "Undergraduate", "Undergraduate Students")))
            result["Graduate_Students"] = str(_to_int_v106(get_col("Graduate_Students", "Graduate", "Graduate Students")))
            result["Language_Study_Students"] = str(_to_int_v106(get_col("Language_Study_Students", "Language Study", "Language", "KLP", "EAP")))

        nationalities = []
        if nationality_df is not None and len(nationality_df) > 0:
            cols = {str(c).strip().lower(): c for c in nationality_df.columns}
            country_col = cols.get("country") or cols.get("nationality")
            count_col = cols.get("number_of_students") or cols.get("students") or cols.get("number") or cols.get("count")
            if country_col is None:
                for lc, orig in cols.items():
                    if "country" in lc or "national" in lc:
                        country_col = orig
                        break
            if count_col is None:
                for lc, orig in cols.items():
                    if "student" in lc or "number" in lc or "count" in lc:
                        count_col = orig
                        break
            if country_col is not None and count_col is not None:
                for _, r in nationality_df.iterrows():
                    country = str(r.get(country_col, "")).strip()
                    count = _to_int_v106(r.get(count_col, ""))
                    if country and count > 0:
                        nationalities.append({"country": country, "count": count})
        nationalities = sorted(nationalities, key=lambda x: x["count"], reverse=True)
        result["Nationality_Students_JSON"] = json.dumps(nationalities, ensure_ascii=False)
        return result
    except Exception as e:
        st.error(f"Could not read student statistics Excel file: {e}")
        return result

def nationality_list_v106(value):
    try:
        data = json.loads(str(value or "[]"))
        if isinstance(data, list):
            clean = []
            for item in data:
                if isinstance(item, dict):
                    country = str(item.get("country", "")).strip()
                    count = _to_int_v106(item.get("count", 0))
                    if country and count > 0:
                        clean.append({"country": country, "count": count})
            return sorted(clean, key=lambda x: x["count"], reverse=True)
    except Exception:
        pass
    return []

def university_student_stats_html_v106(u):
    year = display_clean_v50(u.get("Student_Data_Year", "")).strip()
    ug = _to_int_v106(u.get("Undergraduate_Students", ""))
    grad = _to_int_v106(u.get("Graduate_Students", ""))
    lang = _to_int_v106(u.get("Language_Study_Students", ""))
    nationalities = nationality_list_v106(u.get("Nationality_Students_JSON", ""))[:5]
    if ug <= 0 and grad <= 0 and lang <= 0 and not nationalities:
        return ""
    total_program = max(ug + grad + lang, 1)
    program_items = [("Undergraduate", ug, "#005BDB"), ("Graduate", grad, "#7A2E83"), ("Language Study", lang, "#F59E0B")]
    program_html = ""
    for label, val, color in program_items:
        pct = max(3, min(100, round((val / total_program) * 100, 1))) if val > 0 else 3
        program_html += f"""
        <div class="student-stat-row-v106">
            <div class="student-stat-label-v106"><span>{label}</span><b>{val:,}</b></div>
            <div class="student-stat-bar-v106"><div style="width:{pct}%; background:{color};"></div></div>
        </div>
        """
    nationality_html = ""
    if nationalities:
        max_country = max([x["count"] for x in nationalities] + [1])
        for item in nationalities:
            country = item["country"]
            count = item["count"]
            pct = max(8, min(100, round((count / max_country) * 100, 1)))
            nationality_html += f"""
            <div class="nationality-item-v106">
                <div class="nationality-main-v106">{country_flag_html_v108(country)}<span>{_safe_html_v62(country)}</span></div>
                <b>{count:,}</b>
                <div class="nationality-bar-v106"><div style="width:{pct}%;"></div></div>
            </div>
            """
    else:
        nationality_html = '<p class="student-muted-v106">No nationality data uploaded.</p>'
    year_label = f"Data year: {_safe_html_v62(year)}" if year else "Uploaded student data"
    return f"""
    <div class="student-stats-card-v106">
        <div class="student-stats-head-v106">
            <div>
                <h3>Student Enrollment Information</h3>
                <p>{year_label}</p>
            </div>
            <div class="student-total-pill-v106">Total shown: {(ug + grad + lang):,}</div>
        </div>
        <div class="student-stats-grid-v106">
            <div class="student-program-chart-v106">
                <h4>Students by Program Level</h4>
                {program_html}
            </div>
            <div class="nationality-chart-v106">
                <h4>Top 5 Nationalities</h4>
                {nationality_html}
            </div>
        </div>
    </div>
    """.strip()

def normalize_url_v103(url):
    """Return a clickable URL. Adds https:// if admin typed only domain."""
    url = display_clean_v50(url).strip()
    if not url:
        return ""
    if url.lower().startswith(("http://", "https://", "mailto:", "tel:")):
        return url
    return "https://" + url

def university_quick_links_html_v103(u):
    """Optional university detail click links. Only shown when admin entered URLs/info.
    v105: use clearer official-style SNS icons for Facebook / Instagram / YouTube.
    """
    links = []

    def add_link(label, icon_html, value, extra_cls=""):
        href = normalize_url_v103(value)
        if href:
            links.append(
                f'<a class="uni-quick-link-v103 {extra_cls}" href="{href}" target="_blank" rel="noopener noreferrer">'
                f'<span class="uni-quick-icon-v103 {extra_cls}">{icon_html}</span>'
                f'<span>{_safe_html_v62(label)}</span>'
                f'<span class="uni-external-v103">↗</span>'
                f'</a>'
            )

    home_icon = '<span class="uni-emoji-icon-v105">🏠</span>'
    globe_icon = '<span class="uni-emoji-icon-v105">🌐</span>'
    doc_icon = '<span class="uni-emoji-icon-v105">📄</span>'

    facebook_icon = """
<svg viewBox="0 0 24 24" aria-hidden="true" class="sns-svg-v105 facebook-svg-v105">
  <path fill="currentColor" d="M13.5 22v-8h2.7l.4-3h-3.1V9.1c0-.9.3-1.6 1.6-1.6h1.7V4.8c-.3 0-1.3-.1-2.5-.1-2.5 0-4.2 1.5-4.2 4.3V11H8v3h2.4v8h3.1z"/>
</svg>
"""
    instagram_icon = """
<svg viewBox="0 0 24 24" aria-hidden="true" class="sns-svg-v105 instagram-svg-v105">
  <defs>
    <linearGradient id="igGradientV105" x1="0%" y1="100%" x2="100%" y2="0%">
      <stop offset="0%" stop-color="#FEDA75"/>
      <stop offset="30%" stop-color="#FA7E1E"/>
      <stop offset="60%" stop-color="#D62976"/>
      <stop offset="85%" stop-color="#962FBF"/>
      <stop offset="100%" stop-color="#4F5BD5"/>
    </linearGradient>
  </defs>
  <rect x="3" y="3" width="18" height="18" rx="5" fill="url(#igGradientV105)"/>
  <circle cx="12" cy="12" r="4.2" fill="none" stroke="#fff" stroke-width="1.9"/>
  <circle cx="17.2" cy="6.9" r="1.1" fill="#fff"/>
</svg>
"""
    youtube_icon = """
<svg viewBox="0 0 24 24" aria-hidden="true" class="sns-svg-v105 youtube-svg-v105">
  <rect x="2.2" y="5.5" width="19.6" height="13" rx="4.2" fill="#FF0000"/>
  <path d="M10 9.1l5.2 2.9L10 14.9V9.1z" fill="#fff"/>
</svg>
"""

    add_link("Homepage", home_icon, u.get("Homepage", ""), "home-link-v105")
    add_link("Language School Homepage", globe_icon, u.get("Language_School_Homepage", ""), "language-link-v105")
    add_link("Promotional Materials", doc_icon, u.get("Promotional_Materials", ""), "promo-link-v105")
    add_link("Facebook", facebook_icon, u.get("Facebook_Link", ""), "facebook-link-v105")
    add_link("Instagram", instagram_icon, u.get("Instagram_Link", ""), "instagram-link-v105")
    add_link("YouTube", youtube_icon, u.get("YouTube_Link", ""), "youtube-link-v105")

    sns_text = display_clean_v50(u.get("SNS_Information", "")).strip()

    if not links and not sns_text:
        return ""

    sns_html = ""
    if sns_text:
        sns_html = f'<div class="uni-sns-note-v103"><b>SNS Information</b><p>{_safe_html_v62(sns_text)}</p></div>'

    return f"""
<div class="uni-quick-links-card-v103">
    <h3>Useful Links</h3>
    <div class="uni-quick-links-grid-v103">
        {''.join(links)}
    </div>
    {sns_html}
</div>
""".strip()


def google_map_embed_html_v99(u):
    """Create a Google Maps embed and open-map button from university address/location."""
    try:
        from urllib.parse import quote_plus
        uni = display_clean_v50(u.get("University", ""))
        address = display_clean_v50(u.get("Address", ""))
        location = display_clean_v50(u.get("Location", ""))
        region = display_clean_v50(u.get("Region", ""))
        query = " ".join([x for x in [uni, address, location, region, "Korea"] if x]).strip()
        if not query:
            return ""
        q = quote_plus(query)
        embed_url = f"https://www.google.com/maps?q={q}&output=embed"
        open_url = f"https://www.google.com/maps/search/?api=1&query={q}"
        map_html_v102 = f"""
<div class="uni-map-card-v99">
<div class="uni-map-header-v99">
<div>
<h3>University Location</h3>
<p>{_safe_html_v62(address if address else query)}</p>
</div>
<a class="uni-map-link-v99" href="{open_url}" target="_blank">Open in Google Maps</a>
</div>
<iframe class="uni-map-frame-v99" src="{embed_url}" loading="lazy" referrerpolicy="no-referrer-when-downgrade"></iframe>
</div>
"""
        return map_html_v102.strip()
    except Exception:
        return ""



def _render_university_detail_v62(u):
    detail_name_style_v99 = university_name_style_v93(u.get("University", ""), u.get("University_Logo", "")) if "university_name_style_v93" in globals() else ""
    logo_html = university_logo_html_v88(u.get("University_Logo", ""), u.get("University", ""))
    image_html = university_slideshow_html_v89(u, "detail_" + safe_slug_v49(u.get("University", ""))) if "university_slideshow_html_v89" in globals() else asset_img_html(u.get("Image", ""), "uni-wide-v32")
    programs_html = program_list_html_for_university(u.get("University", ""))
    program_badges = _program_specific_application_badges_v71(u)
    map_html = google_map_embed_html_v99(u)
    quick_links_html = university_quick_links_html_v103(u)
    student_stats_html = university_student_stats_html_v106(u)

    detail_html = f"""
<div class="detail-card-v99">
    <div class="detail-photo-v99">
        {image_html}
    </div>

    <div class="detail-main-v99">
        <div class="detail-left-v99">
            <div class="detail-logo-box-v99">{logo_html}</div>
            <div class="detail-title-copy-v99">
                <h2 class="uni-detail-name-v99" style="{detail_name_style_v99}">
                    <span style="{detail_name_style_v99}">{_safe_html_v62(u.get("University", ""))}</span>
                </h2>
                <p>{_safe_html_v62(u.get("Overview", ""))}</p>
            </div>
        </div>

        <div class="detail-program-side-v99">
            {program_badges}
        </div>
    </div>

    {quick_links_html}

    {student_stats_html}

    <div class="detail-info-grid-v99">
        <div class="info-box-v32"><b>Homepage</b><span>{_safe_html_v62(u.get("Homepage", ""))}</span></div>
        <div class="info-box-v32"><b>Region</b><span>{_safe_html_v62(u.get("Region", ""))}</span></div>
        <div class="info-box-v32"><b>Address</b><span>{_safe_html_v62(u.get("Address", ""))}</span></div>
        <div class="info-box-v32"><b>School Size</b><span>{_safe_html_v62(u.get("School_Size", ""))}</span></div>
        <div class="info-box-v32"><b>Representative Phone</b><span>{_safe_html_v62(u.get("Representative_Phone", ""))}</span></div>
        <div class="info-box-v32"><b>Representative Fax</b><span>{_safe_html_v62(u.get("Representative_Fax", ""))}</span></div>
        <div class="info-box-v32"><b>Foreign Students</b><span>{_safe_html_v62(display_clean_v50(u.get("International_Students", "")))}</span></div>
        <div class="info-box-v32"><b>Tuition Range</b><span>{_safe_html_v62(u.get("Tuition_Range", ""))}</span></div>
    </div>

    {map_html}

    <div class="detail-programs-v99">
        <h3 class="available-title-v41">Available Programs & Majors</h3>
        {programs_html}
    </div>
</div>
"""
    clean_detail_html_v102 = "\n".join(
        line.lstrip() for line in textwrap.dedent(detail_html).strip().splitlines()
    )
    st.markdown(clean_detail_html_v102, unsafe_allow_html=True)


def _render_university_summary_v62(u, key_suffix):
    image_html = university_slideshow_html_v89(u, key_suffix)
    logo_html = university_logo_html_v88(u.get("University_Logo", ""), u.get("University", ""))
    name_style_v93 = university_name_style_v93(u.get("University", ""), u.get("University_Logo", ""))
    program_badges_inline = _program_specific_application_badges_v71(u)

    summary_html = f'''<div class="uni-summary-card-v88">
<div class="uni-summary-image-wrap-v88">
{image_html}
</div>
<div class="uni-summary-content-v88">
    <div class="uni-summary-left-v88">
        <div class="uni-logo-box-v88">{logo_html}</div>
        <div class="uni-summary-text-v88">
            <h3 class="uni-name-accent-v93" style="{name_style_v93}">
                <span style="{name_style_v93}">{_safe_html_v62(u.get("University", ""))}</span>
            </h3>
            <p>{_safe_html_v62(u.get("Overview", ""))}</p>
        </div>
    </div>
    <div class="uni-summary-programs-v88">
        {program_badges_inline}
    </div>
</div>
</div>'''
    st.markdown(summary_html, unsafe_allow_html=True)

    if st.button("View Details", key=f"view_details_v62_{key_suffix}", use_container_width=True):
        st.session_state.selected_uni_v62 = str(u.get("University", ""))
        st.rerun()


def universities_page(public=False):
    if public:
        header()
        st.markdown('<div class="universities-wrap-v32">', unsafe_allow_html=True)
    else:
        dash_shell(["Dashboard","Universities","Eligibility Check","Tuition & Scholarship","Contact Us"])
        st.markdown('<div class="universities-wrap-v32">', unsafe_allow_html=True)

    st.title("Universities Information")
    st.caption("Filter universities by location/city, application status, intake, and scholarship level.")

    df = universities().copy()
    if df is None or len(df) == 0:
        st.info("No university data found.")
        st.markdown('</div>', unsafe_allow_html=True)
        if public:
            footer()
        else:
            close_shell()
        return

    for col in ["University", "Location", "Region", "Intake", "Application_Status", "Application_Open_Date", "Application_Close_Date", "UG_Open_Date", "UG_Close_Date", "UG_New_Open_Date", "UG_New_Close_Date", "UG_Transfer_Open_Date", "UG_Transfer_Close_Date", "Graduate_Open_Date", "Graduate_Close_Date", "KLP_EAP_Open_Date", "KLP_EAP_Close_Date", "KLP_Open_Date", "KLP_Close_Date", "EAP_Open_Date", "EAP_Close_Date", "Overview", "Image", "Image_Gallery", "University_Logo", "Homepage", "Language_School_Homepage", "Promotional_Materials", "Facebook_Link", "Instagram_Link", "YouTube_Link", "SNS_Information", "Address", "School_Size",
                "Representative_Phone", "Representative_Fax", "International_Students", "Tuition_Range"]:
        if col not in df.columns:
            df[col] = ""

    scholarship_map = university_max_scholarship_map_v62()
    df["_Max_Scholarship"] = df["University"].astype(str).map(lambda x: scholarship_map.get(x.strip(), 0.0))
    df["_Location_Filter"] = df.apply(_location_value_v62, axis=1)

    st.markdown('<div class="filter-panel-v61">', unsafe_allow_html=True)
    f1, f2, f3, f4 = st.columns([1.25, 1.0, 1.25, 1.55], gap="medium")

    with f1:
        search = st.text_input("Search", placeholder="University, city, major, keyword")
    with f2:
        location_values = sorted([
            x for x in set(
                list(df["Location"].dropna().astype(str).str.strip()) +
                list(df["Region"].dropna().astype(str).str.strip())
            )
            if x and x.lower() not in ["nan", "none", "null"]
        ])
        location_filter = st.selectbox("Location / City", ["All"] + location_values)
    with f3:
        intake_filter = st.selectbox(
            "Application Status / Intake",
            ["All", "Application Open", "Application Closed", "Application Opens Soon", "March Intake", "September Intake", "Spring Intake", "Fall Intake"]
        )
    with f4:
        sort_filter = st.selectbox(
            "Sort",
            ["Default", "Scholarship High to Low", "Scholarship Low to High", "University Name A-Z"]
        )

    st.markdown('</div>', unsafe_allow_html=True)

    filtered = df.copy()

    if search:
        s = search.lower()
        crit = criteria()
        major_text = {}
        if crit is not None and len(crit) and "University" in crit.columns:
            for uni, group in crit.groupby("University"):
                major_text[str(uni)] = " ".join(map(str, group.values.flatten())).lower()

        filtered = filtered[
            filtered.apply(
                lambda r: (
                    s in " ".join(map(str, r.values)).lower()
                    or s in major_text.get(str(r.get("University", "")), "")
                ),
                axis=1
            )
        ]

    if location_filter != "All":
        lf = location_filter.lower()
        filtered = filtered[
            filtered.apply(
                lambda r: lf in str(r.get("Location", "")).lower() or lf in str(r.get("Region", "")).lower(),
                axis=1
            )
        ]

    if intake_filter != "All":
        if intake_filter in ["Application Open", "Application Closed", "Application Opens Soon"]:
            filtered = filtered[
                filtered.apply(lambda r: _application_status_v66_from_row(r) == intake_filter, axis=1)
            ]
        elif intake_filter == "March Intake":
            filtered = filtered[filtered["Intake"].astype(str).str.lower().str.contains("march", na=False)]
        elif intake_filter == "September Intake":
            filtered = filtered[filtered["Intake"].astype(str).str.lower().str.contains("september", na=False)]
        elif intake_filter == "Spring Intake":
            filtered = filtered[filtered["Intake"].astype(str).str.lower().str.contains("spring|march", regex=True, na=False)]
        elif intake_filter == "Fall Intake":
            filtered = filtered[filtered["Intake"].astype(str).str.lower().str.contains("fall|september", regex=True, na=False)]

    if sort_filter == "Scholarship High to Low":
        filtered = filtered.sort_values(["_Max_Scholarship", "University"], ascending=[False, True])
    elif sort_filter == "Scholarship Low to High":
        filtered = filtered.sort_values(["_Max_Scholarship", "University"], ascending=[True, True])
    elif sort_filter == "University Name A-Z":
        filtered = filtered.sort_values("University", ascending=True)

    st.markdown(
        f'''<div class="filter-summary-v61">
Showing <b>{len(filtered)}</b> of <b>{len(df)}</b> universities
<span>· Application status can be managed as Open, Closed, or Opens Soon. Scholarship sort uses the highest scholarship percentage in Scholarship Rules.</span>
</div>''',
        unsafe_allow_html=True,
    )

    if len(filtered) == 0:
        st.warning("No universities match the selected filters. Please adjust the filter options.")

    # v109: open program detail page from clickable Undergraduate/Graduate/KLP-EAP cards.
    try:
        uni_query_v109 = st.query_params.get("uni", "")
        prog_query_v109 = st.query_params.get("programdetail", "")
    except Exception:
        uni_query_v109, prog_query_v109 = "", ""
    if isinstance(uni_query_v109, list):
        uni_query_v109 = uni_query_v109[0] if uni_query_v109 else ""
    if isinstance(prog_query_v109, list):
        prog_query_v109 = prog_query_v109[0] if prog_query_v109 else ""
    if uni_query_v109 and prog_query_v109:
        from urllib.parse import unquote_plus
        st.session_state.selected_uni_v62 = unquote_plus(str(uni_query_v109))
        st.session_state.selected_program_v109 = unquote_plus(str(prog_query_v109))
        st.session_state.application_type_v109 = ""

    selected = st.session_state.get("selected_uni_v62", "")
    program_selected_v109 = st.session_state.get("selected_program_v109", "")
    if selected:
        selected_rows = df[df["University"].astype(str) == str(selected)]
        if len(selected_rows):
            c_back, c_title = st.columns([1, 7])
            with c_back:
                back_label_v109 = "← Back to University Details" if program_selected_v109 else "← Back to List"
                if st.button(back_label_v109, key="back_to_uni_list_v62", use_container_width=True):
                    if program_selected_v109:
                        st.session_state.selected_program_v109 = ""
                        st.session_state.application_type_v109 = ""
                    else:
                        st.session_state.selected_uni_v62 = ""
                    try:
                        for q in ["uni", "programdetail"]:
                            if q in st.query_params:
                                del st.query_params[q]
                    except Exception:
                        pass
                    st.rerun()
            with c_title:
                if program_selected_v109:
                    st.markdown(f"### Program Details for {selected}")
                else:
                    st.markdown(f"### Details for {selected}")
            if program_selected_v109:
                render_program_detail_page_v109(selected_rows.iloc[0], program_selected_v109)
            else:
                _render_university_detail_v62(selected_rows.iloc[0])
        else:
            st.session_state.selected_uni_v62 = ""
            st.rerun()
    else:
        for i, (_, u) in enumerate(filtered.iterrows()):
            _render_university_summary_v62(u, i)

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



def _unique_admin_key_v72(prefix, idx, user):
    """Create a safe unique key for repeated admin buttons."""
    try:
        username = str(user.get("username", "")).strip()
        email = str(user.get("email", "")).strip()
        agency = str(user.get("agency_name", "")).strip()
    except Exception:
        username, email, agency = "", "", ""
    raw = f"{prefix}_{idx}_{username}_{email}_{agency}"
    return re.sub(r"[^A-Za-z0-9_]+", "_", raw)[:180]


def admin():
    dash_shell(["Admin Dashboard","Partner Management","Universities","Eligibility Rules","Tuition Rules","Scholarship Rules"])

    users_list = read_json(USERS)
    users = pd.DataFrame(users_list)

    if len(users):
        partners = users[users["role"].isin(["agency_rep", "agency_staff", "partner"])].copy()
    else:
        partners = pd.DataFrame()

    e = read_csv(ELIG_LOGS)
    inquiries = read_csv(INQUIRIES)
    unis_df = universities()

    pending_partners = partners[partners["status"]=="pending"].copy() if len(partners) and "status" in partners.columns else pd.DataFrame()
    approved_partners = partners[partners["status"]=="approved"].copy() if len(partners) and "status" in partners.columns else pd.DataFrame()
    rejected_partners = partners[partners["status"]=="rejected"].copy() if len(partners) and "status" in partners.columns else pd.DataFrame()

    pending = len(pending_partners)
    approved = len(approved_partners)
    rejected = len(rejected_partners)
    agency_reps = len(partners[partners["role"]=="agency_rep"]) if len(partners) and "role" in partners.columns else 0
    agency_staff = len(partners[partners["role"]=="agency_staff"]) if len(partners) and "role" in partners.columns else 0
    total_checks = len(e)
    total_unis = len(unis_df)
    total_inquiries = len(inquiries)

    st.markdown("""
    <div class="admin-title-row-v73">
        <div class="admin-step-pill-v73">Step 1</div>
        <div>
            <h1>Admin Dashboard</h1>
            <p>Manage partner approvals, monitor platform activity, and review recent student records.</p>
        </div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown(f"""
    <div class="admin-stats-grid-v73">
        <div class="admin-stat-card-v73">
            <div class="stat-icon-v73">👥</div>
            <b>Total Partner Users</b>
            <h2>{len(partners)}</h2>
            <p>Registered agency users</p>
        </div>
        <div class="admin-stat-card-v73 warning-v73">
            <div class="stat-icon-v73">⏳</div>
            <b>Pending Approval</b>
            <h2>{pending}</h2>
            <p>Waiting for admin action</p>
        </div>
        <div class="admin-stat-card-v73 success-v73">
            <div class="stat-icon-v73">✅</div>
            <b>Approved</b>
            <h2>{approved}</h2>
            <p>Active partner users</p>
        </div>
        <div class="admin-stat-card-v73">
            <div class="stat-icon-v73">🏛️</div>
            <b>Universities</b>
            <h2>{total_unis}</h2>
            <p>University profiles</p>
        </div>
        <div class="admin-stat-card-v73">
            <div class="stat-icon-v73">📋</div>
            <b>Eligibility Checks</b>
            <h2>{total_checks}</h2>
            <p>Student check records</p>
        </div>
    </div>
    """, unsafe_allow_html=True)

    left, right = st.columns([1.55, .85], gap="large")

    with left:
        st.markdown("""
        <div class="admin-panel-v73">
            <div class="admin-panel-head-v73">
                <div>
                    <h2>Partner Approval Requests</h2>
                    <p>Approve or reject new agency accounts.</p>
                </div>
                <span class="admin-badge-yellow-v73">Pending</span>
            </div>
        </div>
        """, unsafe_allow_html=True)

        if len(pending_partners):
            for p_idx, (_, p) in enumerate(pending_partners.iterrows()):
                st.markdown(f"""
                <div class="approval-card-premium-v73">
                    <div class="approval-card-top-v73">
                        <h3>{p.get('agency_name','')}</h3>
                        <span class="status-pending">pending</span>
                    </div>
                    <div class="approval-grid-v73">
                        <div><b>Name</b><span>{p.get('full_name','')}</span></div>
                        <div><b>Username</b><span>{p.get('username','')}</span></div>
                        <div><b>Account Type</b><span>{p.get('account_type', p.get('role',''))}</span></div>
                        <div><b>Email</b><span>{p.get('email','')}</span></div>
                        <div><b>Country</b><span>{p.get('country','')}</span></div>
                        <div><b>Role</b><span>{p.get('role','')}</span></div>
                    </div>
                </div>
                """, unsafe_allow_html=True)

                c1, c2, c3 = st.columns([1,1,4.5])
                with c1:
                    if st.button("Approve", key=_unique_admin_key_v72("approve", p_idx, p), use_container_width=True):
                        all_users = read_json(USERS)
                        for u in all_users:
                            if u.get("username") == p.get("username") and u.get("email") == p.get("email"):
                                u["status"] = "approved"
                            elif u.get("username") == p.get("username") and not p.get("email"):
                                u["status"] = "approved"
                        write_json(USERS, all_users)
                        st.success(f"{p.get('username')} approved.")
                        st.rerun()
                with c2:
                    if st.button("Reject", key=_unique_admin_key_v72("reject", p_idx, p), use_container_width=True):
                        all_users = read_json(USERS)
                        for u in all_users:
                            if u.get("username") == p.get("username") and u.get("email") == p.get("email"):
                                u["status"] = "rejected"
                            elif u.get("username") == p.get("username") and not p.get("email"):
                                u["status"] = "rejected"
                        write_json(USERS, all_users)
                        st.warning(f"{p.get('username')} rejected.")
                        st.rerun()
                st.markdown('<div class="approval-action-gap-v73"></div>', unsafe_allow_html=True)
        else:
            st.markdown("""
            <div class="admin-empty-card-v73">
                <h3>No pending partner approval requests</h3>
                <p>New agency applications will appear here for review.</p>
            </div>
            """, unsafe_allow_html=True)

        st.markdown("""
        <div class="admin-panel-v73 admin-panel-margin-v73">
            <div class="admin-panel-head-v73">
                <div>
                    <h2>Recent Eligibility Check History</h2>
                    <p>Latest student eligibility activity from partner agencies.</p>
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)

        if len(e):
            e_display = e.sort_values("timestamp", ascending=False) if "timestamp" in e.columns else e
            st.dataframe(e_display.head(15), use_container_width=True, hide_index=True)
        else:
            st.info("No eligibility checks yet.")

    with right:
        st.markdown(f"""
        <div class="admin-side-panel-v73">
            <h2>Partner Approval Status</h2>
            <p class="muted">Current account review summary</p>
            <div class="status-row-v73"><span class="dot yellow"></span><b>Pending Approval</b><em>{pending}</em></div>
            <div class="status-row-v73"><span class="dot green"></span><b>Approved</b><em>{approved}</em></div>
            <div class="status-row-v73"><span class="dot red"></span><b>Rejected</b><em>{rejected}</em></div>
            <hr>
            <div class="status-row-v73"><span class="dot blue"></span><b>Agency Reps</b><em>{agency_reps}</em></div>
            <div class="status-row-v73"><span class="dot blue"></span><b>Agency Staff</b><em>{agency_staff}</em></div>
        </div>
        """, unsafe_allow_html=True)

        st.markdown("""
        <div class="admin-rules-card-v73">
            <h2>Quick Admin Actions</h2>
            <p>Use the top menu to manage detailed data.</p>
            <div class="quick-row-v73"><b>Universities</b><span>Add/edit university profiles</span></div>
            <div class="quick-row-v73"><b>Eligibility Rules</b><span>Manage admission criteria</span></div>
            <div class="quick-row-v73"><b>Tuition Rules</b><span>Manage fee information</span></div>
            <div class="quick-row-v73"><b>Scholarship Rules</b><span>Manage scholarship ranges</span></div>
        </div>
        """, unsafe_allow_html=True)

        st.markdown("""
        <div class="admin-rules-card-v73">
            <h2>Recent Contact Inquiries</h2>
        </div>
        """, unsafe_allow_html=True)
        if len(inquiries):
            inquiries_display = inquiries.sort_values("timestamp", ascending=False) if "timestamp" in inquiries.columns else inquiries
            st.dataframe(inquiries_display.head(8), use_container_width=True, hide_index=True)
        else:
            st.info("No contact inquiries yet.")

    st.markdown("""
    <div class="admin-bottom-features-v73">
      <div><span>🛡️</span><b>Trusted Partnerships</b><p>Work with verified universities</p></div>
      <div><span>📄</span><b>Accurate Information</b><p>Up-to-date admission & fee details</p></div>
      <div><span>✅</span><b>Eligibility Made Easy</b><p>Quick checks for better guidance</p></div>
      <div><span>🎓</span><b>Scholarship Support</b><p>Maximize opportunities for students</p></div>
    </div>
    """, unsafe_allow_html=True)

    close_shell()


def update_user_record_v58(old_username, new_row):
    users = read_json(USERS)
    updated = []
    for u_idx, u in enumerate(users):
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
    dash_shell(["Admin Dashboard","Partner Management","Universities","Eligibility Rules","Tuition Rules","Scholarship Rules"])
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
            role_options = ["admin", "agency_rep", "agency_staff", "agency_partner", "partner"]
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
            new_role = st.selectbox("New Role", ["agency_rep", "agency_staff", "agency_partner", "partner"], key="new_role_v58")
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
    dash_shell(["Admin Dashboard","Partner Management","Universities","Eligibility Rules","Tuition Rules","Scholarship Rules"])
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
    """
    v94: Modern admin rules table UI.
    Used by Eligibility Rules, Tuition Rules, and Scholarship Rules.
    Shows university name with logo, selected-university-only records, Add New Rule, search, filters, and clean table format.
    """
    dash_shell(["Admin Dashboard","Partner Management","Universities","Eligibility Rules","Tuition Rules","Scholarship Rules"])

    is_eligibility = "eligibility" in str(title).lower() or "criteria" in str(title).lower()
    is_tuition = "tuition" in str(title).lower()
    is_scholarship = "scholarship" in str(title).lower()

    if is_eligibility:
        page_title = "Eligibility Criteria / Program & Major Management"
        page_caption = "Select one university first, then edit only that university's program level, major, GPA, and language criteria."
        table_title = "Program & Major Eligibility Rules"
        add_label = "+ Add New Rule"
        search_placeholder = "Search by major or program..."
    elif is_tuition:
        page_title = "Tuition Rules Management"
        page_caption = "Select one university first, then edit only that university's application fee, admission fee, and tuition fee values."
        table_title = "Tuition Fee Rules"
        add_label = "+ Add New Tuition Rule"
        search_placeholder = "Search by program or major..."
    elif is_scholarship:
        page_title = "Scholarship Rules Management"
        page_caption = "Select one university first, then edit only that university's scholarship criteria by program and IELTS range."
        table_title = "Scholarship Rules"
        add_label = "+ Add New Scholarship Rule"
        search_placeholder = "Search by program or criteria..."
    else:
        page_title = title
        page_caption = help_text
        table_title = "Rules"
        add_label = "+ Add New Rule"
        search_placeholder = "Search..."

    st.markdown(f"""
    <div class="admin-rule-title-v94">
        <h1>{page_title}</h1>
        <p>{page_caption}</p>
    </div>
    """, unsafe_allow_html=True)

    df = read_csv(path)
    if len(df) == 0:
        st.warning("No data found. A blank table will be created after you add rows.")
        if "University" not in df.columns:
            df["University"] = ""

    if "University" not in df.columns:
        df["University"] = ""

    # University options from university table first, then this rule table.
    try:
        uni_df = read_csv(UNIS)
        university_options = sorted([x for x in uni_df.get("University", pd.Series(dtype=str)).dropna().astype(str).str.strip().unique().tolist() if x])
    except Exception:
        uni_df = pd.DataFrame()
        university_options = []

    rule_unis = sorted([x for x in df["University"].dropna().astype(str).str.strip().unique().tolist() if x])
    for u_name in rule_unis:
        if u_name not in university_options:
            university_options.append(u_name)

    if not university_options:
        selected_uni = st.text_input("Select University to Manage", key=f"{key}_manual_university_v94")
        if not selected_uni:
            st.info("Please enter a university name first.")
            close_shell()
            return
    else:
        st.markdown('<div class="rule-selector-panel-v94">', unsafe_allow_html=True)
        selected_uni = st.selectbox(
            "Select University to Manage",
            university_options,
            key=f"{key}_university_filter_v94"
        )
        st.markdown('</div>', unsafe_allow_html=True)

    selected_uni = str(selected_uni).strip()

    # Selected university logo card.
    logo_path = ""
    if len(uni_df):
        uni_match = uni_df[uni_df.get("University", pd.Series(dtype=str)).astype(str).str.strip() == selected_uni]
        if len(uni_match):
            logo_path = str(uni_match.iloc[0].get("University_Logo", "") or "")
    logo_html = university_logo_html_v88(logo_path, selected_uni) if "university_logo_html_v88" in globals() else ""
    st.markdown(
        f"""
        <div class="selected-rule-uni-card-v94">
            <div class="selected-rule-logo-v94">{logo_html}</div>
            <div>
                <h2>{_safe_html_v62(selected_uni)}</h2>
                <p>Editing only this university's records. Other universities will not be shown or changed.</p>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # Filter subset to selected university.
    mask = df["University"].astype(str).str.strip() == selected_uni
    subset = df[mask].copy().reset_index(drop=True)

    if len(subset) == 0:
        blank = {c: "" for c in df.columns}
        blank["University"] = selected_uni
        subset = pd.DataFrame([blank])

    # Keep University first and prefilled.
    cols = list(subset.columns)
    if "University" in cols:
        subset = subset[["University"] + [c for c in cols if c != "University"]]
    subset["University"] = selected_uni

    # Add new row button state. Data editor itself remains dynamic too.
    c_title, c_add, c_search, c_filter = st.columns([2.2, .9, 1.9, .75])
    with c_title:
        st.markdown(f'<h3 class="rules-table-heading-v94">{table_title}</h3>', unsafe_allow_html=True)
    with c_add:
        if st.button(add_label, key=f"{key}_add_row_v94", use_container_width=True):
            blank = {c: "" for c in subset.columns}
            blank["University"] = selected_uni
            subset = pd.concat([subset, pd.DataFrame([blank])], ignore_index=True)
            st.session_state[f"{key}_local_rows_v95_{safe_slug_v49(selected_uni)}"] = subset.to_dict("records")
            st.rerun()
    with c_search:
        search_query = st.text_input("Search", placeholder=search_placeholder, label_visibility="collapsed", key=f"{key}_search_v94")
    with c_filter:
        st.button("Filters", key=f"{key}_filter_btn_v94", use_container_width=True)

    # Use added rows from session for this selected university if present.
    local_rows = st.session_state.get(f"{key}_local_rows_v95_{safe_slug_v49(selected_uni)}")
    if local_rows:
        try:
            local_df = pd.DataFrame(local_rows)
            if "University" in local_df.columns and len(local_df) and str(local_df["University"].iloc[0]).strip() == selected_uni:
                subset = local_df.copy()
        except Exception:
            pass

    display_subset = subset.copy()
    if search_query:
        q = str(search_query).lower().strip()
        searchable_cols = [c for c in display_subset.columns if c.lower() in ["program", "major", "ielts_criteria", "gpa_criteria", "criteria", "scholarship_text"]]
        if not searchable_cols:
            searchable_cols = [c for c in display_subset.columns if c != "University"]
        display_mask = display_subset[searchable_cols].astype(str).apply(lambda row: any(q in str(v).lower() for v in row), axis=1)
        display_subset = display_subset[display_mask].copy()

    # Column ordering/labels matching sample style.
    preferred_cols = []
    if is_eligibility:
        preferred_cols = ["University", "Program", "Major", "IELTS_Criteria", "Minimum_IELTS", "GPA_Criteria", "Minimum_GPA", "Application_Fee_KRW"]
    elif is_tuition:
        preferred_cols = ["University", "Program", "Major", "Application_Fee_KRW", "Admission_Fee_KRW", "Tuition_Fee_Per_Semester_KRW"]
    elif is_scholarship:
        preferred_cols = ["University", "Program", "IELTS_Min", "IELTS_Max", "Scholarship_Percent", "Scholarship_Text", "Criteria"]
    ordered_cols = [c for c in preferred_cols if c in display_subset.columns] + [c for c in display_subset.columns if c not in preferred_cols]
    display_subset = display_subset[ordered_cols]

    # Add fake action columns for visual similarity; real editing is directly inside table.
    if "Actions" not in display_subset.columns:
        display_subset["Actions"] = "✎  ⋮"

    # v95 fix: Streamlit can raise StreamlitAPIException when TextColumn is applied
    # to numeric/mixed dtype columns. Convert the editable view to strings first.
    display_subset = display_subset.fillna("").astype(str)

    column_config = {}
    if "University" in display_subset.columns:
        column_config["University"] = st.column_config.TextColumn("University", disabled=True)
    if "Actions" in display_subset.columns:
        column_config["Actions"] = st.column_config.TextColumn("Actions", disabled=True, width="small")
    for c in display_subset.columns:
        label = c.replace("_", " ")
        if c == "Minimum_IELTS":
            label = "Minimum IELTS"
        elif c == "Minimum_GPA":
            label = "Minimum GPA"
        elif c == "Application_Fee_KRW":
            label = "Application Fee (KRW)"
        elif c == "Tuition_Fee_Per_Semester_KRW":
            label = "Tuition Fee / Semester (KRW)"
        elif c == "Admission_Fee_KRW":
            label = "Admission Fee (KRW)"
        elif c not in column_config:
            column_config[c] = st.column_config.TextColumn(label)

    st.markdown('<div class="rules-table-wrap-v94">', unsafe_allow_html=True)
    edited_display = st.data_editor(
        display_subset,
        num_rows="dynamic",
        use_container_width=True,
        hide_index=True,
        key=f"{key}_editor_v95_{safe_slug_v49(selected_uni)}",
        column_config=column_config
    )
    st.markdown('</div>', unsafe_allow_html=True)

    # Remove visual-only Actions column before saving.
    edited_to_save = edited_display.copy()
    if "Actions" in edited_to_save.columns:
        edited_to_save = edited_to_save.drop(columns=["Actions"])
    edited_to_save["University"] = selected_uni

    # Ensure any columns hidden by search are not lost: if searching, user should save visible filtered rows only.
    # To avoid accidental deletion during search, warn and disable save while search is active.
    if search_query:
        st.warning("Search filter is active. Clear the search box before saving changes to avoid saving only filtered rows.")

    c1, c2 = st.columns([1, 4])
    with c1:
        if st.button("Save Changes", key=f"save_{key}_v94", use_container_width=True, disabled=bool(search_query)):
            edited = edited_to_save.copy()
            if "University" not in edited.columns:
                edited["University"] = selected_uni
            edited["University"] = selected_uni

            non_uni_cols = [c for c in edited.columns if c != "University"]
            if non_uni_cols:
                edited = edited[
                    edited[non_uni_cols].astype(str).apply(
                        lambda row: any(str(v).strip() not in ["", "nan", "None", "<NA>"] for v in row),
                        axis=1
                    )
                ].copy()

            # Add missing original columns back if the edited display didn't include them.
            for c in df.columns:
                if c not in edited.columns:
                    edited[c] = ""

            remaining = df[df["University"].astype(str).str.strip() != selected_uni].copy()
            merged = pd.concat([remaining, edited[df.columns]], ignore_index=True)
            safe_write_csv_v48(path, merged)
            reload_data_v49()
            st.session_state.pop(f"{key}_local_rows_v95_{safe_slug_v49(selected_uni)}", None)
            st.success(f"{table_title} saved for {selected_uni}.")
            st.rerun()
    with c2:
        st.info("You can edit cells directly, add new rows, or delete rows in the table above. Click Save Changes when finished.")

    st.markdown(f'<p class="rules-result-count-v94">Showing {len(display_subset)} of {len(subset)} results</p>', unsafe_allow_html=True)

    close_shell()



def admin_universities_edit_v48():
    dash_shell(["Admin Dashboard","Partner Management","Universities","Eligibility Rules","Tuition Rules","Scholarship Rules"])
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
        "Select one university first, then edit only that university's program level, major, GPA, and language criteria."
    )

def admin_scholarship_edit_v48():
    editable_table_v48(
        "Scholarship Rules Management",
        SCHOLARSHIPS,
        "scholarship_editor_v48",
        "Select one university first, then edit only that university's scholarship criteria by program and IELTS range."
    )

def admin_tuition_edit_v48():
    editable_table_v48(
        "Tuition Rules Management",
        CRITERIA,
        "tuition_editor_v48",
        "Select one university first, then edit only that university's application fee, admission fee, and tuition fee values."
    )


def admin_university_management_v49():
    dash_shell(["Admin Dashboard","Partner Management","Universities","Eligibility Rules","Tuition Rules","Scholarship Rules"])
    st.subheader("University Management")
    st.caption("Add, edit, or update university information. New universities will appear on the Home and Universities pages. To appear in Eligibility, add at least one major in Eligibility Rules after adding the university.")

    uni_file = DATA / "universities.csv"
    df = read_csv(uni_file)
    required_cols = [
        "University","Location","Total_Students","International_Students","Top_Majors",
        "Intake","Application_Status","Application_Open_Date","Application_Close_Date",
        "UG_Open_Date","UG_Close_Date","UG_New_Open_Date","UG_New_Close_Date","UG_Transfer_Open_Date","UG_Transfer_Close_Date","Graduate_Open_Date","Graduate_Close_Date","KLP_EAP_Open_Date","KLP_EAP_Close_Date","KLP_Open_Date","KLP_Close_Date","EAP_Open_Date","EAP_Close_Date",
        "Tuition_Range","Scholarship_Info","Overview","Image","Image_Gallery","University_Logo",
        "Homepage","Language_School_Homepage","Promotional_Materials","Facebook_Link","Instagram_Link","YouTube_Link","SNS_Information","Student_Data_Year","Undergraduate_Students","Graduate_Students","Language_Study_Students","Nationality_Students_JSON","Address","Representative_Phone","Representative_Fax","Region","School_Size"
    ]
    df = ensure_columns_v49(df, required_cols)

    st.markdown("""
    <div class="admin-university-tabs-note-v104">
        <b>University Editing Options</b>
        <span>Use the two tabs below: <b>Add New University</b> or <b>Edit Existing Universities</b>.</span>
    </div>
    """, unsafe_allow_html=True)

    tab_add, tab_edit = st.tabs(["Add New University", "Edit Existing Universities"])

    with tab_add:
        st.markdown("### Add New University")
        st.download_button("Download Student Statistics Excel Format", data=student_stats_template_bytes_v106(), file_name="university_student_statistics_template.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", use_container_width=True)
        st.caption("Optional student statistics file: use this template for enrollment numbers and top nationality data. The same template download is also shown next to the Excel upload field below.")
        with st.form("add_university_v49"):
            c1, c2 = st.columns(2)
            with c1:
                university = st.text_input("University Name")
                location = st.text_input("Location")
                region = st.text_input("Region")
                homepage = st.text_input("Homepage")
                language_school_homepage = st.text_input("Language School Homepage (optional)")
                promotional_materials = st.text_input("Promotional Materials Link (optional)")
                facebook_link = st.text_input("Facebook Link (optional)")
                instagram_link = st.text_input("Instagram Link (optional)")
                youtube_link = st.text_input("YouTube Link (optional)")
                sns_information = st.text_area("SNS Information / Notes (optional)", height=70)
                phone = st.text_input("Representative Phone")
                fax = st.text_input("Representative Fax")
                school_size = st.text_input("School Size")
                intl_students = st.text_input("Foreign / International Students")
            with c2:
                address = st.text_area("Address", height=92)
                overview = st.text_area("Overview", height=120)
                intake = st.text_input("Intake", value="March, September")
                application_status = st.selectbox(
                    "Application Status Auto Calculated",
                    ["Application Open", "Application Closed", "Application Opens Soon"],
                    key="add_application_status_v64"
                )
                st.markdown("##### General Application Period")
                application_open_date = st.date_input("General Application Open Date", value=None, key="add_application_open_date_v64")
                application_close_date = st.date_input("General Application Close Date", value=None, key="add_application_close_date_v65")

                st.markdown("##### Program-Specific Application Periods")
                d1, d2 = st.columns(2)
                with d1:
                    ug_open_date = st.date_input("Undergraduate Open Date", value=None, key="add_ug_open_date_v71")
                    grad_open_date = st.date_input("Graduate (Masters/Ph.D.) Open Date", value=None, key="add_grad_open_date_v71")
                    klp_open_date = st.date_input("KLP/EAP Open Date", value=None, key="add_klp_open_date_v71")
                with d2:
                    ug_close_date = st.date_input("Undergraduate Close Date", value=None, key="add_ug_close_date_v71")
                    grad_close_date = st.date_input("Graduate (Masters/Ph.D.) Close Date", value=None, key="add_grad_close_date_v71")
                    klp_close_date = st.date_input("KLP/EAP Close Date", value=None, key="add_klp_close_date_v71")

                st.caption("Each program status is calculated from its own open/close dates. If a program date is empty, the general application period is used as fallback.")

                st.markdown("##### Detailed Application Periods (optional)")
                st.caption("Use these only if new/transfer or KLP/EAP dates are different. If empty, the main program dates above will be used.")
                ad1, ad2 = st.columns(2)
                with ad1:
                    ug_new_open_date = st.date_input("Undergraduate New Student Open Date", value=None, key="add_ug_new_open_date_v109")
                    ug_transfer_open_date = st.date_input("Undergraduate Transfer Open Date", value=None, key="add_ug_transfer_open_date_v109")
                    klp_specific_open_date = st.date_input("KLP Open Date", value=None, key="add_klp_specific_open_date_v109")
                    eap_specific_open_date = st.date_input("EAP Open Date", value=None, key="add_eap_specific_open_date_v109")
                with ad2:
                    ug_new_close_date = st.date_input("Undergraduate New Student Close Date", value=None, key="add_ug_new_close_date_v109")
                    ug_transfer_close_date = st.date_input("Undergraduate Transfer Close Date", value=None, key="add_ug_transfer_close_date_v109")
                    klp_specific_close_date = st.date_input("KLP Close Date", value=None, key="add_klp_specific_close_date_v109")
                    eap_specific_close_date = st.date_input("EAP Close Date", value=None, key="add_eap_specific_close_date_v109")

                tuition_range = st.text_input("Tuition Range")
                scholarship_info = st.text_input("Scholarship Info")
                top_majors = st.text_area("Top Majors / Summary", height=80)
                photo = st.file_uploader("University Main Photo", type=["png","jpg","jpeg"], key="add_uni_photo_v49")
                gallery_photos = st.file_uploader("Upload Slideshow Images", type=["png","jpg","jpeg"], accept_multiple_files=True, key="add_uni_gallery_v89")
                logo = st.file_uploader("Upload Logo of University", type=["png","jpg","jpeg","webp"], key="add_uni_logo_v88")
                st.markdown(student_stats_upload_info_html_v107(), unsafe_allow_html=True)
                excel_dl_col_v107, excel_up_col_v107 = st.columns([0.42, 1.58])
                with excel_dl_col_v107:
                    st.markdown(student_stats_template_download_html_v107(), unsafe_allow_html=True)
                with excel_up_col_v107:
                    student_stats_excel = st.file_uploader("Upload Student Statistics Excel (optional)", type=["xlsx"], key="add_student_stats_excel_v106")
                st.caption("You can upload several campus photos. They will automatically slide/change on the university card. Uploaded logos are automatically cropped and cleaned. Student statistics Excel is optional and only used for the student graph/top nationality section.")

            # v104 safe optional university link defaults
            language_school_homepage = locals().get("language_school_homepage", "")
            promotional_materials = locals().get("promotional_materials", "")
            facebook_link = locals().get("facebook_link", "")
            instagram_link = locals().get("instagram_link", "")
            youtube_link = locals().get("youtube_link", "")
            sns_information = locals().get("sns_information", "")
            submitted = st.form_submit_button("Add University", use_container_width=True)
            if submitted:
                if not university.strip():
                    st.error("University Name is required.")
                elif university.strip() in df["University"].astype(str).str.strip().tolist():
                    st.error("This university already exists. Please use Edit Existing Universities.")
                else:
                    image_path = save_uploaded_university_photo_v49(photo, university)
                    gallery_path = save_uploaded_university_gallery_v89(gallery_photos, university)
                    if not image_path and gallery_path:
                        image_path = gallery_path.split("|")[0]
                    logo_path = save_uploaded_university_logo_v88(logo, university)
                    student_stats_v106 = parse_student_stats_excel_v106(student_stats_excel)
                    calculated_application_status = _auto_application_status_v65(application_open_date, application_close_date, application_status)
                    new_row = {
                        "University": university.strip(),
                        "Location": location.strip(),
                        "Total_Students": school_size.strip(),
                        "International_Students": intl_students.strip(),
                        "Top_Majors": top_majors.strip(),
                        "Intake": intake.strip(),
                        "Application_Status": calculated_application_status,
                        "Application_Open_Date": str(application_open_date) if application_open_date else "",
                        "Application_Close_Date": str(application_close_date) if application_close_date else "",
                        "UG_Open_Date": str(ug_open_date) if ug_open_date else "",
                        "UG_Close_Date": str(ug_close_date) if ug_close_date else "",
                        "UG_New_Open_Date": str(ug_new_open_date) if ug_new_open_date else "",
                        "UG_New_Close_Date": str(ug_new_close_date) if ug_new_close_date else "",
                        "UG_Transfer_Open_Date": str(ug_transfer_open_date) if ug_transfer_open_date else "",
                        "UG_Transfer_Close_Date": str(ug_transfer_close_date) if ug_transfer_close_date else "",
                        "Graduate_Open_Date": str(grad_open_date) if grad_open_date else "",
                        "Graduate_Close_Date": str(grad_close_date) if grad_close_date else "",
                        "KLP_EAP_Open_Date": str(klp_open_date) if klp_open_date else "",
                        "KLP_EAP_Close_Date": str(klp_close_date) if klp_close_date else "",
                        "KLP_Open_Date": str(klp_specific_open_date) if klp_specific_open_date else "",
                        "KLP_Close_Date": str(klp_specific_close_date) if klp_specific_close_date else "",
                        "EAP_Open_Date": str(eap_specific_open_date) if eap_specific_open_date else "",
                        "EAP_Close_Date": str(eap_specific_close_date) if eap_specific_close_date else "",
                        "Tuition_Range": tuition_range.strip(),
                        "Scholarship_Info": scholarship_info.strip(),
                        "Overview": overview.strip(),
                        "Image": image_path,
                        "Image_Gallery": gallery_path,
                        "University_Logo": logo_path,
                        "Homepage": homepage.strip(),
                        "Language_School_Homepage": language_school_homepage.strip(),
                        "Promotional_Materials": promotional_materials.strip(),
                        "Facebook_Link": facebook_link.strip(),
                        "Instagram_Link": instagram_link.strip(),
                        "YouTube_Link": youtube_link.strip(),
                        "SNS_Information": sns_information.strip(),
                        "Student_Data_Year": student_stats_v106.get("Student_Data_Year", ""),
                        "Undergraduate_Students": student_stats_v106.get("Undergraduate_Students", ""),
                        "Graduate_Students": student_stats_v106.get("Graduate_Students", ""),
                        "Language_Study_Students": student_stats_v106.get("Language_Study_Students", ""),
                        "Nationality_Students_JSON": student_stats_v106.get("Nationality_Students_JSON", "[]"),
                        "Address": address.strip(),
                        "Representative_Phone": phone.strip(),
                        "Representative_Fax": fax.strip(),
                        "Region": region.strip(),
                        "School_Size": school_size.strip(),
                        "Total_Students": school_size.strip(),
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
            university_list_v90 = df["University"].dropna().astype(str).tolist()
            selected = st.selectbox(
                "Select University to Edit",
                university_list_v90,
                key="edit_uni_select_v90"
            )
            # v90 important: every field key includes the selected university.
            # This prevents Jeonbuk values/files from remaining when admin selects another university.
            selected_key_v90 = safe_slug_v49(selected)
            idx = df.index[df["University"].astype(str) == str(selected)][0]
            row = df.loc[idx]

            st.markdown(
                f"""
                <div class="selected-university-banner-v74">
                    <b>Editing: {selected}</b>
                    <span>The form below is refreshed for this university only. Uploaded files are also separated by university.</span>
                </div>
                """,
                unsafe_allow_html=True,
            )

            st.download_button("Download Student Statistics Excel Format", data=student_stats_template_bytes_v106(), file_name="university_student_statistics_template.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", use_container_width=True, key=f"download_student_stats_template_v106_{selected_key_v90}")
            st.caption("Optional student statistics file: use this template for enrollment numbers and top nationality data. The same template download is also shown next to the Excel upload field below.")

            with st.form(f"edit_university_v90_{selected_key_v90}"):
                c1, c2 = st.columns(2)
                with c1:
                    university = st.text_input("University Name", value=display_clean_v50(row.get("University", "")), key=f"edit_uni_name_{selected_key_v90}")
                    location = st.text_input("Location", value=display_clean_v50(row.get("Location", "")), key=f"edit_uni_location_{selected_key_v90}")
                    region = st.text_input("Region", value=display_clean_v50(row.get("Region", "")), key=f"edit_uni_region_{selected_key_v90}")
                    homepage = st.text_input("Homepage", value=display_clean_v50(row.get("Homepage", "")), key=f"edit_uni_homepage_{selected_key_v90}")
                    language_school_homepage = st.text_input("Language School Homepage (optional)", value=display_clean_v50(row.get("Language_School_Homepage", "")), key=f"edit_uni_language_homepage_{selected_key_v90}")
                    promotional_materials = st.text_input("Promotional Materials Link (optional)", value=display_clean_v50(row.get("Promotional_Materials", "")), key=f"edit_uni_promo_materials_{selected_key_v90}")
                    facebook_link = st.text_input("Facebook Link (optional)", value=display_clean_v50(row.get("Facebook_Link", "")), key=f"edit_uni_facebook_{selected_key_v90}")
                    instagram_link = st.text_input("Instagram Link (optional)", value=display_clean_v50(row.get("Instagram_Link", "")), key=f"edit_uni_instagram_{selected_key_v90}")
                    youtube_link = st.text_input("YouTube Link (optional)", value=display_clean_v50(row.get("YouTube_Link", "")), key=f"edit_uni_youtube_{selected_key_v90}")
                    sns_information = st.text_area("SNS Information / Notes (optional)", value=display_clean_v50(row.get("SNS_Information", "")), height=70, key=f"edit_uni_sns_info_{selected_key_v90}")
                    phone = st.text_input("Representative Phone", value=display_clean_v50(row.get("Representative_Phone", "")), key=f"edit_uni_phone_{selected_key_v90}")
                    fax = st.text_input("Representative Fax", value=display_clean_v50(row.get("Representative_Fax", "")), key=f"edit_uni_fax_{selected_key_v90}")
                    school_size = st.text_input("School Size", value=display_clean_v50(row.get("School_Size", "")), key=f"edit_uni_school_size_{selected_key_v90}")
                    intl_students = st.text_input("Foreign / International Students", value=display_clean_v50(row.get("International_Students", "")), key=f"edit_uni_intl_students_{selected_key_v90}")
                with c2:
                    address = st.text_area("Address", value=display_clean_v50(row.get("Address", "")), height=92, key=f"edit_uni_address_{selected_key_v90}")
                    overview = st.text_area("Overview", value=display_clean_v50(row.get("Overview", "")), height=120, key=f"edit_uni_overview_{selected_key_v90}")
                    intake = st.text_input("Intake", value=display_clean_v50(row.get("Intake", "")), key=f"edit_uni_intake_{selected_key_v90}")
                    status_options_v64 = ["Application Open", "Application Closed", "Application Opens Soon"]
                    current_status_v64 = _application_status_v64_from_row(row) if _application_status_v64_from_row(row) in status_options_v64 else (display_clean_v50(row.get("Application_Status", "")) or "Application Open")
                    application_status = st.selectbox(
                        "Application Status Auto Calculated",
                        status_options_v64,
                        index=status_options_v64.index(current_status_v64) if current_status_v64 in status_options_v64 else 0,
                        key=f"edit_application_status_v90_{selected_key_v90}"
                    )
                    current_open_date_v64 = _parse_date_v64(row.get("Application_Open_Date", ""))
                    current_close_date_v65 = _parse_date_v64(row.get("Application_Close_Date", ""))
                    st.markdown("##### General Application Period")
                    application_open_date = st.date_input("General Application Open Date", value=current_open_date_v64, key=f"edit_application_open_date_v90_{selected_key_v90}")
                    application_close_date = st.date_input("General Application Close Date", value=current_close_date_v65, key=f"edit_application_close_date_v90_{selected_key_v90}")

                    st.markdown("##### Program-Specific Application Periods")
                    d1, d2 = st.columns(2)
                    with d1:
                        ug_open_date = st.date_input("Undergraduate Open Date", value=_parse_date_v64(row.get("UG_Open_Date", "")), key=f"edit_ug_open_date_v90_{selected_key_v90}")
                        grad_open_date = st.date_input("Graduate (Masters/Ph.D.) Open Date", value=_parse_date_v64(row.get("Graduate_Open_Date", "")), key=f"edit_grad_open_date_v90_{selected_key_v90}")
                        klp_open_date = st.date_input("KLP/EAP Open Date", value=_parse_date_v64(row.get("KLP_EAP_Open_Date", "")), key=f"edit_klp_open_date_v90_{selected_key_v90}")
                    with d2:
                        ug_close_date = st.date_input("Undergraduate Close Date", value=_parse_date_v64(row.get("UG_Close_Date", "")), key=f"edit_ug_close_date_v90_{selected_key_v90}")
                        grad_close_date = st.date_input("Graduate (Masters/Ph.D.) Close Date", value=_parse_date_v64(row.get("Graduate_Close_Date", "")), key=f"edit_grad_close_date_v90_{selected_key_v90}")
                        klp_close_date = st.date_input("KLP/EAP Close Date", value=_parse_date_v64(row.get("KLP_EAP_Close_Date", "")), key=f"edit_klp_close_date_v90_{selected_key_v90}")

                    st.caption("Each program status is calculated from its own open/close dates. If a program date is empty, the general application period is used as fallback.")

                    st.markdown("##### Detailed Application Periods (optional)")
                    st.caption("Use these only if new/transfer or KLP/EAP dates are different. If empty, the main program dates above will be used.")
                    ed1, ed2 = st.columns(2)
                    with ed1:
                        ug_new_open_date = st.date_input("Undergraduate New Student Open Date", value=_parse_date_v64(row.get("UG_New_Open_Date", "")), key=f"edit_ug_new_open_date_v109_{selected_key_v90}")
                        ug_transfer_open_date = st.date_input("Undergraduate Transfer Open Date", value=_parse_date_v64(row.get("UG_Transfer_Open_Date", "")), key=f"edit_ug_transfer_open_date_v109_{selected_key_v90}")
                        klp_specific_open_date = st.date_input("KLP Open Date", value=_parse_date_v64(row.get("KLP_Open_Date", "")), key=f"edit_klp_specific_open_date_v109_{selected_key_v90}")
                        eap_specific_open_date = st.date_input("EAP Open Date", value=_parse_date_v64(row.get("EAP_Open_Date", "")), key=f"edit_eap_specific_open_date_v109_{selected_key_v90}")
                    with ed2:
                        ug_new_close_date = st.date_input("Undergraduate New Student Close Date", value=_parse_date_v64(row.get("UG_New_Close_Date", "")), key=f"edit_ug_new_close_date_v109_{selected_key_v90}")
                        ug_transfer_close_date = st.date_input("Undergraduate Transfer Close Date", value=_parse_date_v64(row.get("UG_Transfer_Close_Date", "")), key=f"edit_ug_transfer_close_date_v109_{selected_key_v90}")
                        klp_specific_close_date = st.date_input("KLP Close Date", value=_parse_date_v64(row.get("KLP_Close_Date", "")), key=f"edit_klp_specific_close_date_v109_{selected_key_v90}")
                        eap_specific_close_date = st.date_input("EAP Close Date", value=_parse_date_v64(row.get("EAP_Close_Date", "")), key=f"edit_eap_specific_close_date_v109_{selected_key_v90}")

                    tuition_range = st.text_input("Tuition Range", value=display_clean_v50(row.get("Tuition_Range", "")), key=f"edit_uni_tuition_{selected_key_v90}")
                    scholarship_info = st.text_input("Scholarship Info", value=display_clean_v50(row.get("Scholarship_Info", "")), key=f"edit_uni_scholarship_{selected_key_v90}")
                    top_majors = st.text_area("Top Majors / Summary", value=display_clean_v50(row.get("Top_Majors", "")), height=80, key=f"edit_uni_top_majors_{selected_key_v90}")

                    current_img = st.text_input("Current Main Photo Path", value=display_clean_v50(row.get("Image", "")), key=f"edit_current_img_{selected_key_v90}")
                    current_gallery = st.text_area("Current Slideshow Image Paths", value=display_clean_v50(row.get("Image_Gallery", "")), height=70, key=f"edit_current_gallery_{selected_key_v90}")
                    current_logo = st.text_input("Current University Logo Path", value=display_clean_v50(row.get("University_Logo", "")), key=f"edit_current_logo_{selected_key_v90}")

                    st.markdown("##### Optional Student Statistics")
                    current_student_year = st.text_input("Current Student Data Year", value=display_clean_v50(row.get("Student_Data_Year", "")), key=f"edit_student_year_v106_{selected_key_v90}")
                    current_ug_students = st.text_input("Current Undergraduate Students", value=display_clean_v50(row.get("Undergraduate_Students", "")), key=f"edit_ug_students_v106_{selected_key_v90}")
                    current_grad_students = st.text_input("Current Graduate Students", value=display_clean_v50(row.get("Graduate_Students", "")), key=f"edit_grad_students_v106_{selected_key_v90}")
                    current_lang_students = st.text_input("Current Language Study Students", value=display_clean_v50(row.get("Language_Study_Students", "")), key=f"edit_lang_students_v106_{selected_key_v90}")
                    current_nat_json = st.text_area("Current Nationality Students JSON", value=display_clean_v50(row.get("Nationality_Students_JSON", "[]")), height=80, key=f"edit_nat_json_v106_{selected_key_v90}")

                    photo = st.file_uploader("Upload New Main Photo", type=["png","jpg","jpeg"], key=f"edit_uni_photo_v90_{selected_key_v90}")
                    gallery_photos = st.file_uploader("Upload New Slideshow Images", type=["png","jpg","jpeg"], accept_multiple_files=True, key=f"edit_uni_gallery_v90_{selected_key_v90}")
                    logo = st.file_uploader("Upload New University Logo", type=["png","jpg","jpeg","webp"], key=f"edit_uni_logo_v90_{selected_key_v90}")
                    st.markdown(student_stats_upload_info_html_v107(), unsafe_allow_html=True)
                    excel_dl_col_v107, excel_up_col_v107 = st.columns([0.42, 1.58])
                    with excel_dl_col_v107:
                        st.markdown(student_stats_template_download_html_v107(), unsafe_allow_html=True)
                    with excel_up_col_v107:
                        student_stats_excel = st.file_uploader("Upload New Student Statistics Excel (optional)", type=["xlsx"], key=f"edit_student_stats_excel_v106_{selected_key_v90}")
                    st.caption("If you upload new slideshow images, they will replace only this selected university's slideshow images. Uploaded logos are automatically cropped and cleaned. Student statistics Excel is optional and only used for the student graph/top nationality section.")

                b1, b2 = st.columns(2)
                save_clicked = b1.form_submit_button("Save Changes", use_container_width=True)
                delete_clicked = b2.form_submit_button("Delete University", use_container_width=True)

                if save_clicked:
                    image_path = save_uploaded_university_photo_v49(photo, university) if photo else current_img
                    gallery_path = save_uploaded_university_gallery_v89(gallery_photos, university) if gallery_photos else current_gallery
                    if not image_path and gallery_path:
                        image_path = gallery_path.split("|")[0]
                    logo_path = save_uploaded_university_logo_v88(logo, university) if logo else current_logo
                    student_stats_v106 = parse_student_stats_excel_v106(student_stats_excel) if student_stats_excel else {
                        "Student_Data_Year": current_student_year,
                        "Undergraduate_Students": current_ug_students,
                        "Graduate_Students": current_grad_students,
                        "Language_Study_Students": current_lang_students,
                        "Nationality_Students_JSON": current_nat_json or "[]",
                    }
                    calculated_application_status = _auto_application_status_v65(application_open_date, application_close_date, application_status)

                    df.loc[idx, "University"] = university.strip()
                    df.loc[idx, "Location"] = location.strip()
                    df.loc[idx, "Region"] = region.strip()
                    df.loc[idx, "Homepage"] = homepage.strip()
                    df.loc[idx, "Language_School_Homepage"] = language_school_homepage.strip()
                    df.loc[idx, "Promotional_Materials"] = promotional_materials.strip()
                    df.loc[idx, "Facebook_Link"] = facebook_link.strip()
                    df.loc[idx, "Instagram_Link"] = instagram_link.strip()
                    df.loc[idx, "YouTube_Link"] = youtube_link.strip()
                    df.loc[idx, "SNS_Information"] = sns_information.strip()
                    df.loc[idx, "Student_Data_Year"] = student_stats_v106.get("Student_Data_Year", "")
                    df.loc[idx, "Undergraduate_Students"] = student_stats_v106.get("Undergraduate_Students", "")
                    df.loc[idx, "Graduate_Students"] = student_stats_v106.get("Graduate_Students", "")
                    df.loc[idx, "Language_Study_Students"] = student_stats_v106.get("Language_Study_Students", "")
                    df.loc[idx, "Nationality_Students_JSON"] = student_stats_v106.get("Nationality_Students_JSON", "[]")
                    df.loc[idx, "Address"] = address.strip()
                    df.loc[idx, "Representative_Phone"] = phone.strip()
                    df.loc[idx, "Representative_Fax"] = fax.strip()
                    df.loc[idx, "School_Size"] = school_size.strip()
                    df.loc[idx, "Total_Students"] = school_size.strip()
                    df.loc[idx, "International_Students"] = intl_students.strip()
                    df.loc[idx, "Overview"] = overview.strip()
                    df.loc[idx, "Intake"] = intake.strip()
                    df.loc[idx, "Application_Status"] = calculated_application_status
                    df.loc[idx, "Application_Open_Date"] = str(application_open_date) if application_open_date else ""
                    df.loc[idx, "Application_Close_Date"] = str(application_close_date) if application_close_date else ""
                    df.loc[idx, "UG_Open_Date"] = str(ug_open_date) if ug_open_date else ""
                    df.loc[idx, "UG_Close_Date"] = str(ug_close_date) if ug_close_date else ""
                    df.loc[idx, "UG_New_Open_Date"] = str(ug_new_open_date) if ug_new_open_date else ""
                    df.loc[idx, "UG_New_Close_Date"] = str(ug_new_close_date) if ug_new_close_date else ""
                    df.loc[idx, "UG_Transfer_Open_Date"] = str(ug_transfer_open_date) if ug_transfer_open_date else ""
                    df.loc[idx, "UG_Transfer_Close_Date"] = str(ug_transfer_close_date) if ug_transfer_close_date else ""
                    df.loc[idx, "Graduate_Open_Date"] = str(grad_open_date) if grad_open_date else ""
                    df.loc[idx, "Graduate_Close_Date"] = str(grad_close_date) if grad_close_date else ""
                    df.loc[idx, "KLP_EAP_Open_Date"] = str(klp_open_date) if klp_open_date else ""
                    df.loc[idx, "KLP_EAP_Close_Date"] = str(klp_close_date) if klp_close_date else ""
                    df.loc[idx, "KLP_Open_Date"] = str(klp_specific_open_date) if klp_specific_open_date else ""
                    df.loc[idx, "KLP_Close_Date"] = str(klp_specific_close_date) if klp_specific_close_date else ""
                    df.loc[idx, "EAP_Open_Date"] = str(eap_specific_open_date) if eap_specific_open_date else ""
                    df.loc[idx, "EAP_Close_Date"] = str(eap_specific_close_date) if eap_specific_close_date else ""
                    df.loc[idx, "Tuition_Range"] = tuition_range.strip()
                    df.loc[idx, "Scholarship_Info"] = scholarship_info.strip()
                    df.loc[idx, "Top_Majors"] = top_majors.strip()
                    df.loc[idx, "Image"] = image_path
                    df.loc[idx, "Image_Gallery"] = gallery_path
                    df.loc[idx, "University_Logo"] = logo_path

                    write_csv(uni_file, df)
                    reload_data_v49()
                    st.success(f"{university.strip()} information saved.")
                    st.rerun()

                if delete_clicked:
                    df = df[df["University"].astype(str) != str(selected)].copy()
                    write_csv(uni_file, df)
                    reload_data_v49()
                    st.warning(f"{selected} has been deleted.")
                    st.rerun()

            st.markdown("### Current University Data")
            st.dataframe(clean_df_v50(df), use_container_width=True, hide_index=True)

    close_shell()


def admin_criteria_management_v49():
    dash_shell(["Admin Dashboard","Partner Management","Universities","Eligibility Rules","Tuition Rules","Scholarship Rules"])
    st.subheader("Eligibility Criteria / Program & Major Management")
    st.caption("Select one university first, then edit only that university’s program level, major, GPA, and language criteria.")

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
    dash_shell(["Admin Dashboard","Partner Management","Universities","Eligibility Rules","Tuition Rules","Scholarship Rules"])
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


# Routing
if not st.session_state.logged_in:
    if st.session_state.page == "Partner Sign Up": signup()
    elif st.session_state.page == "Pending": pending()
    elif st.session_state.page == "Login": login()
    elif st.session_state.page == "Universities": universities_page(public=True)
    elif st.session_state.page == "Contact Us": contact()
    elif st.session_state.page in ["Eligibility Check","Tuition & Scholarship"]:
        restore_pending_from_query_v76()
        if st.session_state.get("pending_username"):
            pending_access_required_v75(st.session_state.page)
        else:
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
        else:
            admin()
    else:
        if st.session_state.page == "Universities": universities_page()
        elif st.session_state.page == "Eligibility Check": eligibility()
        elif st.session_state.page == "Tuition & Scholarship": tuition()
        elif st.session_state.page == "Contact Us": contact()
        else:
            partner_dashboard()
