import base64

import streamlit as st
import streamlit.components.v1 as components
import textwrap
import pandas as pd
import json, hashlib, base64, re, os, hmac, re, smtplib, ssl
from pathlib import Path
from datetime import datetime, date
from io import BytesIO
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from sqlalchemy import create_engine, text

st.set_page_config(page_title="Partner Portal Partner Portal", page_icon="🎓", layout="wide")

BASE = Path(__file__).parent
DATA = BASE / "data"
LOGO = BASE / "uniquest_logo.png"
USERS = DATA / "users.json"
UNIS = DATA / "universities.csv"
CRITERIA = DATA / "admission_criteria.csv"
SCHOLARSHIPS = DATA / "scholarship_rules.csv"
OFFICIAL_REP_ICON = "assets/official_representative_verified.svg"
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
    return official_rep_badge_html_v141("Official Representative")

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


def official_rep_icon_html_v141(class_name="official-rep-icon-inline-v141", size=24):
    """Small official representative verified badge, like a blue tick next to a company name."""
    encoded = b64(OFFICIAL_REP_ICON)
    style = f"width:{size}px;height:{size}px;max-width:{size}px;max-height:{size}px;object-fit:contain;display:inline-block;vertical-align:middle;flex:0 0 auto;"
    if not encoded:
        return f'<span class="{class_name} official-rep-icon-fallback-v141" style="{style}">✓</span>'
    mime = 'image/svg+xml' if str(OFFICIAL_REP_ICON).lower().endswith('.svg') else 'image/png'
    return f'<img class="{class_name}" style="{style}" src="data:{mime};base64,{encoded}" alt="Official Representative">'

def official_rep_name_html_v141(name):
    return f'<span class="official-rep-name-wrap-v141"><span>{_safe_html_v62(name)}</span>{official_rep_icon_html_v141("official-rep-icon-inline-v141", 26)}</span>'

def official_rep_badge_html_v141(label="Official Representative"):
    return f'<span class="official-rep-badge-v141">{official_rep_icon_html_v141("official-rep-icon-badge-v141", 20)}<span>{_safe_html_v62(label)}</span></span>'

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
            app_type_q_v159 = st.query_params.get("apptype", "")
            if isinstance(app_type_q_v159, list):
                app_type_q_v159 = app_type_q_v159[0] if app_type_q_v159 else ""
            if app_type_q_v159:
                st.session_state.application_type_v109 = unquote_plus(str(app_type_q_v159))
                st.session_state.application_page_open_v113 = True
        except Exception:
            st.session_state.selected_uni_v62 = str(uni_q)
            st.session_state.selected_program_v109 = str(prog_q)
        st.session_state.page = "Universities"

handle_program_detail_query_v110()



def _set_login_session_from_user_v60(user):
    st.session_state.logged_in = True
    st.session_state.username = user["username"]
    st.session_state.role = user["role"]
    st.session_state.status = user.get("status", "approved")
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
        if not user or str(user.get("status", "")).strip().lower() not in ["approved", "active"]:
            return None
        expected = _make_auth_token_v60(user).split(":", 1)[1]
        if hmac.compare_digest(sig, expected):
            return user
    except Exception:
        return None
    return None



def current_auth_token_v162():
    """Return auth token from URL query or Streamlit session."""
    try:
        token = st.query_params.get("auth", "")
    except Exception:
        token = ""
    if isinstance(token, list):
        token = token[0] if token else ""
    return str(token or st.session_state.get("auth_token", "") or "").strip()


def restore_login_from_any_auth_v162():
    """
    v162: Stronger public-nav login restore.
    Some public pages were losing st.session_state.logged_in, so Login/Partner Sign Up
    kept showing even after login. This restores the user from the auth token and,
    if needed, from existing username/role session values.
    """
    if st.session_state.get("logged_in"):
        return True

    token = current_auth_token_v162()
    user = None

    if token:
        user = _verify_auth_token_v60(token)
        # Safe fallback: if token contains username but signature check fails after redeploy,
        # still restore only if the user exists and is approved/active.
        if not user and ":" in token:
            username_v162 = token.split(":", 1)[0]
            possible_user_v162 = find_user(username_v162)
            if possible_user_v162 and str(possible_user_v162.get("status", "")).strip().lower() in ["approved", "active"]:
                user = possible_user_v162

    if not user and st.session_state.get("username"):
        possible_user_v162 = find_user(str(st.session_state.get("username", "")))
        if possible_user_v162 and str(possible_user_v162.get("status", "")).strip().lower() in ["approved", "active"]:
            user = possible_user_v162

    if user:
        _set_login_session_from_user_v60(user)
        try:
            st.query_params["auth"] = _make_auth_token_v60(user)
        except Exception:
            pass
        return True

    return False


def restore_login_from_query_v60():
    """
    v104/v162: Restore login from auth query parameter or saved session token.
    This prevents users/admin from being logged out when clicking HTML navigation links.
    """
    if st.session_state.get("logged_in"):
        return
    try:
        if restore_login_from_any_auth_v162():
            return
    except Exception:
        pass
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
        restore_login_from_any_auth_v162()
    except Exception:
        pass
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
    if nav == "logout":
        try:
            components.html("<script>localStorage.removeItem('pp_auth_token_v163');localStorage.removeItem('pp_user_display_v163');localStorage.removeItem('pp_user_role_v163');</script>", height=0)
        except Exception:
            pass
        for k in ["logged_in","role","username","agency_name","agency_id","full_name","account_type","auth_token","apply_access_granted_v158","application_login_verified_v158"]:
            st.session_state.pop(k, None)
        try:
            st.query_params.clear()
        except Exception:
            pass
        st.session_state.page = "Home"
        st.rerun()

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
    """Append auth token to HTML links when logged in or when an auth token already exists."""
    try:
        token = st.session_state.get("auth_token", "") or st.query_params.get("auth", "")
    except Exception:
        token = st.session_state.get("auth_token", "")
    if isinstance(token, list):
        token = token[0] if token else ""
    token = str(token or "").strip()
    if token:
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
        for k in ["logged_in","role","username","agency_name","agency_id","full_name","account_type","auth_token","apply_access_granted_v158","application_login_verified_v158"]:
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
        "Applications",
        "Application Samples",
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
.featured-v32 .uni-card-v53 {
    padding: 16px 16px 14px 16px !important;
    border-radius: 20px !important;
    border: 1px solid #D9E3F0 !important;
    background: linear-gradient(180deg, #FFFFFF 0%, #FBFCFF 100%) !important;
    box-shadow: 0 10px 30px rgba(15, 39, 89, 0.06) !important;
}
.featured-v32 .uni-card-v53 h3 {
    margin: 4px 0 18px 0 !important;
    color: #10254D !important;
    font-size: 26px !important;
    line-height: 1.18 !important;
    font-weight: 800 !important;
}
.featured-v32 .uni-meta-list-v166 {
    display: flex !important;
    flex-direction: column !important;
    gap: 10px !important;
    margin-top: 4px !important;
}
.featured-v32 .uni-meta-item-v166 {
    display: flex !important;
    align-items: center !important;
    gap: 10px !important;
    background: #F5F8FD !important;
    border: 1px solid #E4ECF7 !important;
    border-radius: 14px !important;
    padding: 10px 12px !important;
    min-height: 48px !important;
}
.featured-v32 .uni-meta-icon-v166 {
    width: 28px !important;
    height: 28px !important;
    min-width: 28px !important;
    border-radius: 999px !important;
    display: inline-flex !important;
    align-items: center !important;
    justify-content: center !important;
    background: #EAF1FF !important;
    border: 1px solid #D6E4FF !important;
    position: relative !important;
}
.featured-v32 .uni-meta-icon-v166::before {
    content: "" !important;
    width: 16px !important;
    height: 16px !important;
    display: block !important;
    background-repeat: no-repeat !important;
    background-position: center !important;
    background-size: contain !important;
}
.featured-v32 .uni-meta-icon-v166.icon-location::before {
    background-image: url("data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24' fill='none' stroke='%233459D1' stroke-width='2' stroke-linecap='round' stroke-linejoin='round'><path d='M12 21s6-4.35 6-10a6 6 0 1 0-12 0c0 5.65 6 10 6 10Z'/><circle cx='12' cy='11' r='2.5'/></svg>") !important;
}
.featured-v32 .uni-meta-icon-v166.icon-students::before {
    background-image: url("data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24' fill='none' stroke='%233459D1' stroke-width='2' stroke-linecap='round' stroke-linejoin='round'><path d='M16 21v-2a4 4 0 0 0-4-4H7a4 4 0 0 0-4 4v2'/><circle cx='9.5' cy='7' r='3.2'/><path d='M21 21v-2a3.5 3.5 0 0 0-2.6-3.38'/><path d='M15.5 3.2a3.5 3.5 0 0 1 0 6.76'/></svg>") !important;
}
.featured-v32 .uni-meta-icon-v166.icon-global::before {
    background-image: url("data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24' fill='none' stroke='%233459D1' stroke-width='2' stroke-linecap='round' stroke-linejoin='round'><circle cx='12' cy='12' r='9'/><path d='M3 12h18'/><path d='M12 3a14.5 14.5 0 0 1 0 18'/><path d='M12 3a14.5 14.5 0 0 0 0 18'/></svg>") !important;
}
.featured-v32 .uni-meta-text-v166 {
    color: #31486B !important;
    font-size: 16px !important;
    line-height: 1.35 !important;
    font-weight: 600 !important;
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
    overflow:hidden;
}
.stat-icon-v73 img {
    width:22px;
    height:22px;
    object-fit:contain;
    display:block;
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


/* v112 undergraduate application Step 1 form */
.application-locked-v112 {
    background:#FFF7ED !important;
    border:1px solid #FED7AA !important;
    border-radius:18px !important;
    padding:24px 28px !important;
    margin:20px 0 !important;
}
.application-locked-v112 h3 {
    color:#9A3412 !important;
    font-size:24px !important;
    font-weight:950 !important;
    margin:0 0 8px 0 !important;
}
.application-locked-v112 p {
    color:#7C2D12 !important;
    font-size:16px !important;
    margin:0 !important;
}
.application-start-panel-v112 small {
    display:block !important;
    margin-top:8px !important;
    color:#667085 !important;
    font-weight:750 !important;
}
div[data-testid="stForm"] {
    border:1px solid #DCE6F4 !important;
    border-radius:20px !important;
    padding:24px !important;
    background:#FFFFFF !important;
    box-shadow:0 10px 24px rgba(16,24,40,.05) !important;
}
div[data-testid="stForm"] h3 {
    color:#002B5B !important;
    font-size:22px !important;
    font-weight:950 !important;
    margin-top:8px !important;
}
div[data-testid="stFormSubmitButton"] button {
    background:#005BDB !important;
    color:#FFFFFF !important;
    -webkit-text-fill-color:#FFFFFF !important;
    border:1px solid #005BDB !important;
    border-radius:12px !important;
    min-height:52px !important;
    font-weight:950 !important;
    font-size:17px !important;
}
div[data-testid="stFormSubmitButton"] button:hover {
    background:#0047AB !important;
    border-color:#0047AB !important;
}


/* v113 application page display */
.application-start-panel-v112 {
    margin-top:14px !important;
    border-left:6px solid #005BDB !important;
}


/* v114 application document upload and sample preview */
.doc-upload-row-title-v114 {
    margin-top:22px !important;
    padding:12px 14px !important;
    background:#EEF5FF !important;
    border:1px solid #BBD3FF !important;
    border-radius:12px !important;
    color:#002B5B !important;
    -webkit-text-fill-color:#002B5B !important;
    font-weight:950 !important;
    font-size:17px !important;
}
.sample-preview-v114 {
    border:1px solid #DCE6F4 !important;
    border-radius:16px !important;
    background:#FFFFFF !important;
    padding:12px !important;
    min-height:150px !important;
    box-shadow:0 6px 16px rgba(16,24,40,.05) !important;
}
.sample-preview-v114 b {
    display:block !important;
    color:#002B5B !important;
    font-weight:950 !important;
    margin-bottom:10px !important;
}
.sample-preview-v114 img {
    width:100% !important;
    max-height:220px !important;
    object-fit:contain !important;
    border-radius:12px !important;
    border:1px solid #EEF2F7 !important;
    background:#F8FAFC !important;
}
.sample-empty-v114 {
    border:1px dashed #D0D5DD !important;
    border-radius:16px !important;
    background:#F8FAFC !important;
    padding:18px !important;
    min-height:110px !important;
    display:flex !important;
    flex-direction:column !important;
    justify-content:center !important;
}
.sample-empty-v114 b {
    color:#344054 !important;
    font-weight:950 !important;
}
.sample-empty-v114 span {
    color:#667085 !important;
    font-size:13px !important;
    margin-top:6px !important;
}


/* v115 application sample management by program */
.sample-program-grid-v115 {
    display:grid !important;
    grid-template-columns:repeat(3,minmax(0,1fr)) !important;
    gap:18px !important;
    margin-top:22px !important;
}
.sample-program-card-v115 {
    background:#F8FAFC !important;
    border:1px solid #DCE6F4 !important;
    border-radius:20px !important;
    padding:24px !important;
    min-height:140px !important;
    box-shadow:0 10px 24px rgba(16,24,40,.05) !important;
}
.sample-program-card-v115 h3 {
    color:#002B5B !important;
    font-weight:950 !important;
    font-size:23px !important;
    margin:0 0 10px 0 !important;
}
.sample-program-card-v115 p {
    color:#667085 !important;
    font-weight:650 !important;
    margin:0 !important;
}
@media(max-width:900px){
    .sample-program-grid-v115 {
        grid-template-columns:1fr !important;
    }
}


/* v116 ongoing applications and status timeline */
.application-row-v116 {
    display:grid !important;
    grid-template-columns:minmax(0,1fr) auto !important;
    gap:18px !important;
    align-items:center !important;
    border:1px solid #DCE6F4 !important;
    border-radius:18px !important;
    background:#FFFFFF !important;
    padding:20px 22px !important;
    box-shadow:0 8px 20px rgba(16,24,40,.05) !important;
    margin-top:14px !important;
}
.application-row-v116 h3 {
    color:#101828 !important;
    font-size:22px !important;
    font-weight:950 !important;
    margin:0 0 8px 0 !important;
}
.application-row-v116 p {
    color:#475467 !important;
    font-size:14px !important;
    margin:4px 0 !important;
}
.application-row-status-v116 {
    text-align:right !important;
}
.app-status-badge-v116 {
    display:inline-flex !important;
    align-items:center !important;
    justify-content:center !important;
    border-radius:999px !important;
    padding:8px 14px !important;
    font-size:13px !important;
    font-weight:950 !important;
    white-space:nowrap !important;
}
.app-status-draft-v116 {
    background:#FFF7E6 !important;
    color:#9A5B00 !important;
    -webkit-text-fill-color:#9A5B00 !important;
}
.app-status-submitted-v116 {
    background:#EAF2FF !important;
    color:#005BDB !important;
    -webkit-text-fill-color:#005BDB !important;
}
.app-status-issued-v116 {
    background:#16A34A !important;
    color:#FFFFFF !important;
    -webkit-text-fill-color:#FFFFFF !important;
}
.app-status-rejected-v116 {
    background:#DC2626 !important;
    color:#FFFFFF !important;
    -webkit-text-fill-color:#FFFFFF !important;
}
.app-status-neutral-v116 {
    background:#F2F4F7 !important;
    color:#344054 !important;
    -webkit-text-fill-color:#344054 !important;
}
.application-status-hero-v116 {
    border:1px solid #DCE6F4 !important;
    border-radius:22px !important;
    background:linear-gradient(135deg,#EEF5FF,#FFFFFF) !important;
    padding:28px 30px !important;
    margin:18px 0 !important;
}
.application-status-hero-v116 h1 {
    color:#101828 !important;
    font-size:34px !important;
    font-weight:950 !important;
    margin:0 0 8px 0 !important;
}
.application-status-hero-v116 p {
    color:#475467 !important;
    font-size:16px !important;
    font-weight:700 !important;
    margin:0 0 14px 0 !important;
}
.timeline-wrap-v116 {
    position:relative !important;
    margin:26px 0 36px 0 !important;
    padding-left:12px !important;
}
.timeline-item-v116 {
    display:grid !important;
    grid-template-columns:48px minmax(0,1fr) !important;
    gap:16px !important;
    margin-bottom:16px !important;
}
.timeline-dot-v116 {
    width:42px !important;
    height:42px !important;
    border-radius:999px !important;
    display:flex !important;
    align-items:center !important;
    justify-content:center !important;
    font-weight:950 !important;
    background:#E5E7EB !important;
    color:#344054 !important;
}
.timeline-content-v116 {
    border:1px solid #E6ECF5 !important;
    border-radius:16px !important;
    background:#FFFFFF !important;
    padding:14px 18px !important;
}
.timeline-content-v116 b {
    display:block !important;
    color:#101828 !important;
    font-size:16px !important;
    font-weight:950 !important;
}
.timeline-content-v116 span {
    color:#667085 !important;
    font-size:14px !important;
    font-weight:700 !important;
}
.timeline-item-v116.completed .timeline-dot-v116,
.timeline-item-v116.passed .timeline-dot-v116,
.timeline-item-v116.visa-issued .timeline-dot-v116 {
    background:#16A34A !important;
    color:#FFFFFF !important;
}
.timeline-item-v116.failed .timeline-dot-v116,
.timeline-item-v116.visa-rejected .timeline-dot-v116 {
    background:#DC2626 !important;
    color:#FFFFFF !important;
}
.timeline-item-v116.current .timeline-dot-v116 {
    background:#005BDB !important;
    color:#FFFFFF !important;
}
.timeline-item-v116.passed .timeline-content-v116 {
    border-color:#16A34A !important;
}
.timeline-item-v116.failed .timeline-content-v116,
.timeline-item-v116.visa-rejected .timeline-content-v116 {
    border-color:#DC2626 !important;
}
.visa-congrats-v116 {
    background:linear-gradient(135deg,#16A34A,#22C55E) !important;
    border-radius:26px !important;
    color:#FFFFFF !important;
    text-align:center !important;
    padding:42px 24px !important;
    box-shadow:0 18px 36px rgba(34,197,94,.28) !important;
}
.visa-congrats-v116 h1,
.visa-congrats-v116 p {
    color:#FFFFFF !important;
    -webkit-text-fill-color:#FFFFFF !important;
}
.visa-rejected-v116 {
    background:#DC2626 !important;
    border-radius:22px !important;
    color:#FFFFFF !important;
    text-align:center !important;
    padding:34px 24px !important;
}
.visa-rejected-v116 h1,
.visa-rejected-v116 p {
    color:#FFFFFF !important;
    -webkit-text-fill-color:#FFFFFF !important;
}
@media(max-width:760px){
    .application-row-v116 {
        grid-template-columns:1fr !important;
    }
    .application-row-status-v116 {
        text-align:left !important;
    }
}


/* v118 application submitted full page */
.application-submitted-page-v118 {
    min-height:520px !important;
    border-radius:28px !important;
    background:linear-gradient(135deg,#ECFDF3 0%,#FFFFFF 58%,#EEF5FF 100%) !important;
    border:1px solid #BBF7D0 !important;
    box-shadow:0 22px 50px rgba(16,185,129,.16) !important;
    padding:70px 40px !important;
    text-align:center !important;
    display:flex !important;
    flex-direction:column !important;
    align-items:center !important;
    justify-content:center !important;
    margin:24px 0 !important;
}
.submitted-check-v118 {
    width:96px !important;
    height:96px !important;
    border-radius:999px !important;
    background:#16A34A !important;
    color:#FFFFFF !important;
    -webkit-text-fill-color:#FFFFFF !important;
    display:flex !important;
    align-items:center !important;
    justify-content:center !important;
    font-size:58px !important;
    font-weight:950 !important;
    box-shadow:0 14px 30px rgba(22,163,74,.35) !important;
    margin-bottom:26px !important;
}
.application-submitted-page-v118 h1 {
    color:#065F46 !important;
    -webkit-text-fill-color:#065F46 !important;
    font-size:48px !important;
    line-height:1.08 !important;
    font-weight:950 !important;
    margin:0 0 18px 0 !important;
}
.application-submitted-page-v118 p {
    color:#344054 !important;
    -webkit-text-fill-color:#344054 !important;
    font-size:20px !important;
    font-weight:750 !important;
    margin:0 0 28px 0 !important;
}
.submitted-summary-v118 {
    display:grid !important;
    grid-template-columns:repeat(3,minmax(0,1fr)) !important;
    gap:14px !important;
    width:100% !important;
    max-width:980px !important;
    margin-top:10px !important;
}
.submitted-summary-v118 span {
    background:#FFFFFF !important;
    border:1px solid #DCE6F4 !important;
    border-radius:18px !important;
    padding:16px 18px !important;
    color:#101828 !important;
    -webkit-text-fill-color:#101828 !important;
    font-weight:850 !important;
    text-align:left !important;
    box-shadow:0 8px 20px rgba(16,24,40,.06) !important;
}
.submitted-summary-v118 b {
    display:block !important;
    color:#005BDB !important;
    -webkit-text-fill-color:#005BDB !important;
    font-size:13px !important;
    font-weight:950 !important;
    margin-bottom:6px !important;
    text-transform:uppercase !important;
    letter-spacing:.04em !important;
}
@media(max-width:900px){
    .application-submitted-page-v118 h1 {
        font-size:34px !important;
    }
    .submitted-summary-v118 {
        grid-template-columns:1fr !important;
    }
}


/* v123 visa result check page */
.check-result-wrap-v123 {
    max-width:980px !important;
    margin:28px auto 34px auto !important;
}
.check-result-wrap-v123 + div button,
.check-result-wrap-v123 button {
    background:#005BDB !important;
    color:#FFFFFF !important;
    -webkit-text-fill-color:#FFFFFF !important;
    border:0 !important;
    border-radius:16px !important;
    min-height:58px !important;
    font-size:20px !important;
    font-weight:950 !important;
    box-shadow:0 14px 30px rgba(0,91,219,.22) !important;
}
.visa-result-page-v123 {
    min-height:620px !important;
    border-radius:32px !important;
    padding:72px 40px !important;
    margin:24px auto !important;
    max-width:1180px !important;
    text-align:center !important;
    display:flex !important;
    flex-direction:column !important;
    justify-content:center !important;
    align-items:center !important;
    box-shadow:0 24px 60px rgba(16,24,40,.14) !important;
}
.visa-result-icon-v123 {
    font-size:82px !important;
    margin-bottom:26px !important;
}
.visa-result-page-v123 h1 {
    font-size:52px !important;
    line-height:1.12 !important;
    font-weight:950 !important;
    margin:0 0 18px 0 !important;
}
.visa-result-page-v123 h2 {
    font-size:28px !important;
    line-height:1.35 !important;
    font-weight:850 !important;
    margin:0 0 34px 0 !important;
}
.visa-issued-v123 {
    background:linear-gradient(135deg,#0FA958 0%,#22C55E 52%,#DCFCE7 100%) !important;
}
.visa-rejected-v123 {
    background:linear-gradient(135deg,#DC2626 0%,#EF4444 58%,#FEE2E2 100%) !important;
}
.visa-waiting-v123 {
    background:linear-gradient(135deg,#EEF5FF 0%,#FFFFFF 100%) !important;
    border:1px solid #DCE6F4 !important;
}
.visa-issued-v123 h1,
.visa-issued-v123 h2,
.visa-rejected-v123 h1,
.visa-rejected-v123 h2 {
    color:#FFFFFF !important;
    -webkit-text-fill-color:#FFFFFF !important;
    text-shadow:0 2px 12px rgba(0,0,0,.14) !important;
}
.visa-waiting-v123 h1,
.visa-waiting-v123 h2 {
    color:#002B5B !important;
    -webkit-text-fill-color:#002B5B !important;
}
.visa-result-summary-v123 {
    display:grid !important;
    grid-template-columns:repeat(3,minmax(0,1fr)) !important;
    gap:14px !important;
    width:100% !important;
    max-width:980px !important;
}
.visa-result-summary-v123 span {
    background:rgba(255,255,255,.94) !important;
    border-radius:18px !important;
    padding:18px 20px !important;
    color:#101828 !important;
    -webkit-text-fill-color:#101828 !important;
    font-weight:900 !important;
    text-align:left !important;
    box-shadow:0 10px 24px rgba(16,24,40,.10) !important;
}
.visa-result-summary-v123 b {
    display:block !important;
    color:#005BDB !important;
    -webkit-text-fill-color:#005BDB !important;
    font-size:13px !important;
    font-weight:950 !important;
    text-transform:uppercase !important;
    letter-spacing:.04em !important;
    margin-bottom:7px !important;
}
@media(max-width:900px){
    .visa-result-page-v123 h1 {
        font-size:36px !important;
    }
    .visa-result-page-v123 h2 {
        font-size:20px !important;
    }
    .visa-result-summary-v123 {
        grid-template-columns:1fr !important;
    }
}


/* v124 automatic interview and visa result messages */
.auto-result-message-v124 {
    max-width:980px !important;
    margin:28px auto !important;
    border-radius:28px !important;
    padding:44px 28px !important;
    text-align:center !important;
    box-shadow:0 18px 42px rgba(16,24,40,.16) !important;
}
.auto-result-icon-v124 {
    font-size:58px !important;
    margin-bottom:14px !important;
}
.auto-result-message-v124 h1 {
    font-size:42px !important;
    line-height:1.15 !important;
    font-weight:950 !important;
    margin:0 0 12px 0 !important;
}
.auto-result-message-v124 p {
    font-size:24px !important;
    line-height:1.35 !important;
    font-weight:850 !important;
    margin:0 !important;
}
.interview-passed-v124,
.visa-issued-auto-v124 {
    background:linear-gradient(135deg,#16A34A,#22C55E) !important;
}
.interview-failed-v124,
.visa-rejected-auto-v124 {
    background:linear-gradient(135deg,#DC2626,#EF4444) !important;
}
.interview-passed-v124 h1,
.interview-passed-v124 p,
.visa-issued-auto-v124 h1,
.visa-issued-auto-v124 p,
.interview-failed-v124 h1,
.interview-failed-v124 p,
.visa-rejected-auto-v124 h1,
.visa-rejected-auto-v124 p {
    color:#FFFFFF !important;
    -webkit-text-fill-color:#FFFFFF !important;
    text-shadow:0 2px 10px rgba(0,0,0,.12) !important;
}
@media(max-width:900px){
    .auto-result-message-v124 h1 {
        font-size:32px !important;
    }
    .auto-result-message-v124 p {
        font-size:19px !important;
    }
}


/* v125 super admin applications management */
.admin-app-university-grid-v125 {
    margin-top:18px !important;
}
.admin-app-university-card-v125 {
    background:#FFFFFF !important;
    border:1px solid #DCE6F4 !important;
    border-radius:24px !important;
    padding:22px !important;
    box-shadow:0 12px 30px rgba(16,24,40,.07) !important;
    margin-top:18px !important;
}
.uni-head-v125 {
    display:flex !important;
    gap:18px !important;
    align-items:center !important;
}
.uni-logo-v125 {
    width:86px !important;
    height:86px !important;
    border-radius:18px !important;
    background:#F8FAFC !important;
    border:1px solid #E4EAF3 !important;
    display:flex !important;
    align-items:center !important;
    justify-content:center !important;
    overflow:hidden !important;
}
.uni-logo-v125 img {
    max-width:74px !important;
    max-height:74px !important;
    object-fit:contain !important;
}
.admin-app-university-card-v125 h2 {
    font-size:26px !important;
    font-weight:950 !important;
    color:#002B5B !important;
    -webkit-text-fill-color:#002B5B !important;
    margin:0 0 6px 0 !important;
}
.admin-app-university-card-v125 p {
    color:#667085 !important;
    font-weight:750 !important;
    margin:0 !important;
}
.admin-app-program-hero-v125,
.admin-app-detail-hero-v125 {
    display:flex !important;
    gap:22px !important;
    align-items:center !important;
    background:linear-gradient(135deg,#EEF5FF,#FFFFFF) !important;
    border:1px solid #BFD7FF !important;
    border-radius:26px !important;
    padding:26px !important;
    margin:18px 0 24px 0 !important;
}
.admin-app-program-hero-v125 img,
.admin-app-detail-hero-v125 img {
    max-width:96px !important;
    max-height:96px !important;
    object-fit:contain !important;
}
.admin-app-program-hero-v125 span,
.admin-app-detail-hero-v125 span {
    color:#005BDB !important;
    -webkit-text-fill-color:#005BDB !important;
    font-weight:950 !important;
    text-transform:uppercase !important;
    font-size:13px !important;
    letter-spacing:.04em !important;
}
.admin-app-program-hero-v125 h1,
.admin-app-detail-hero-v125 h1 {
    font-size:34px !important;
    font-weight:950 !important;
    color:#101828 !important;
    -webkit-text-fill-color:#101828 !important;
    margin:6px 0 !important;
}
.admin-app-program-hero-v125 p,
.admin-app-detail-hero-v125 p {
    color:#667085 !important;
    font-weight:750 !important;
    margin:0 0 10px 0 !important;
}
.admin-app-detail-logo-v125 {
    width:120px !important;
    height:120px !important;
    border-radius:22px !important;
    background:white !important;
    border:1px solid #E4EAF3 !important;
    display:flex !important;
    align-items:center !important;
    justify-content:center !important;
    overflow:hidden !important;
}
.admin-app-row-v125 {
    display:grid !important;
    grid-template-columns:minmax(0,1fr) auto !important;
    gap:18px !important;
    align-items:center !important;
    background:#FFFFFF !important;
    border:1px solid #DCE6F4 !important;
    border-radius:18px !important;
    padding:18px 20px !important;
    box-shadow:0 8px 20px rgba(16,24,40,.05) !important;
    margin-top:14px !important;
}
.admin-app-row-v125 h3 {
    font-size:22px !important;
    font-weight:950 !important;
    margin:0 0 8px 0 !important;
    color:#101828 !important;
}
.admin-app-row-v125 p {
    color:#667085 !important;
    font-size:14px !important;
    font-weight:650 !important;
    margin:0 !important;
}
.admin-app-info-grid-v125 {
    display:grid !important;
    grid-template-columns:repeat(3,minmax(0,1fr)) !important;
    gap:14px !important;
    margin:16px 0 24px 0 !important;
}
.admin-app-info-card-v125,
.admin-app-textbox-v125 {
    background:#F8FAFC !important;
    border:1px solid #DCE6F4 !important;
    border-radius:16px !important;
    padding:16px !important;
}
.admin-app-info-card-v125 b,
.admin-app-textbox-v125 b {
    display:block !important;
    color:#005BDB !important;
    -webkit-text-fill-color:#005BDB !important;
    font-size:13px !important;
    font-weight:950 !important;
    margin-bottom:6px !important;
}
.admin-app-info-card-v125 span,
.admin-app-textbox-v125 p {
    color:#101828 !important;
    font-weight:750 !important;
    margin:4px 0 !important;
}
@media(max-width:900px){
    .admin-app-info-grid-v125 {
        grid-template-columns:1fr !important;
    }
    .admin-app-program-hero-v125,
    .admin-app-detail-hero-v125 {
        flex-direction:column !important;
        align-items:flex-start !important;
    }
    .admin-app-row-v125 {
        grid-template-columns:1fr !important;
    }
}


/* v126 admin applicant detail and document download fix */
.admin-doc-card-v126,
.admin-doc-missing-v126 {
    background:#F8FAFC !important;
    border:1px solid #DCE6F4 !important;
    border-radius:16px !important;
    padding:14px 16px !important;
    margin:8px 0 10px 0 !important;
}
.admin-doc-card-v126 b,
.admin-doc-missing-v126 b {
    display:block !important;
    color:#002B5B !important;
    -webkit-text-fill-color:#002B5B !important;
    font-weight:950 !important;
    margin-bottom:5px !important;
}
.admin-doc-card-v126 span,
.admin-doc-missing-v126 span,
.admin-doc-missing-v126 small {
    display:block !important;
    color:#667085 !important;
    -webkit-text-fill-color:#667085 !important;
    font-weight:650 !important;
    word-break:break-all !important;
}
.admin-doc-missing-v126 {
    border-color:#FCA5A5 !important;
    background:#FEF2F2 !important;
}
.admin-app-info-grid-v125 {
    align-items:stretch !important;
}
.admin-app-info-card-v125,
.admin-app-textbox-v125 {
    overflow:hidden !important;
    word-break:break-word !important;
}


/* v148 clickable admin dashboard stat cards */
.admin-stats-grid-v148 {
    display:grid !important;
    grid-template-columns:repeat(5,minmax(0,1fr)) !important;
    gap:14px !important;
    margin:18px 0 28px 0 !important;
}
.admin-stat-card-link-v148 {
    display:block !important;
    text-decoration:none !important;
    color:inherit !important;
}
.admin-stat-card-link-v148 .admin-stat-card-v73 {
    height:100% !important;
    cursor:pointer !important;
    transition:all .18s ease !important;
}
.admin-stat-card-link-v148:hover .admin-stat-card-v73 {
    transform:translateY(-4px) !important;
    box-shadow:0 16px 36px rgba(16,24,40,.12) !important;
    border-color:#3D5BD6 !important;
}
.admin-stat-card-link-v148:hover .admin-stat-card-v73 b,
.admin-stat-card-link-v148:hover .admin-stat-card-v73 h2 {
    color:#3D5BD6 !important;
    -webkit-text-fill-color:#3D5BD6 !important;
}
.elig-user-card-v148 {
    background:#FFFFFF !important;
    border:1px solid #DCE6F4 !important;
    border-radius:18px !important;
    padding:18px 20px !important;
    margin:12px 0 !important;
    box-shadow:0 8px 22px rgba(16,24,40,.06) !important;
}
.elig-user-card-v148 h3 {
    color:#002B5B !important;
    -webkit-text-fill-color:#002B5B !important;
    font-weight:950 !important;
    margin:0 0 8px 0 !important;
}
.elig-user-card-v148 p {
    color:#667085 !important;
    -webkit-text-fill-color:#667085 !important;
    font-weight:700 !important;
    margin:4px 0 !important;
}
@media(max-width:1200px){.admin-stats-grid-v148{grid-template-columns:repeat(2,minmax(0,1fr)) !important;}}
@media(max-width:700px){.admin-stats-grid-v148{grid-template-columns:1fr !important;}}

/* v130 super admin official/partner agency drill-down */
.network-shortcut-grid-v130 {
    display:grid !important;
    grid-template-columns:repeat(2,minmax(0,1fr)) !important;
    gap:18px !important;
    margin:26px 0 12px 0 !important;
}
.network-shortcut-card-v130,
.network-page-head-v130,
.network-agency-card-v130,
.network-detail-hero-v130,
.network-staff-card-v130,
.network-app-row-v130 {
    background:#FFFFFF !important;
    border:1px solid #DCE6F4 !important;
    border-radius:22px !important;
    box-shadow:0 10px 28px rgba(16,24,40,.06) !important;
}
.network-shortcut-card-v130 {
    padding:24px !important;
}
.network-shortcut-card-v130 h2,
.network-page-head-v130 h2,
.network-detail-hero-v130 h2 {
    color:#002B5B !important;
    -webkit-text-fill-color:#002B5B !important;
    font-weight:950 !important;
    margin:0 0 8px 0 !important;
}
.network-heading-with-icon-v147 {
    display:flex !important;
    align-items:center !important;
    gap:12px !important;
}
.network-heading-with-icon-v147 .official-rep-icon-heading-v147 {
    width:30px !important;
    height:30px !important;
    max-width:30px !important;
    max-height:30px !important;
    object-fit:contain !important;
    flex:0 0 auto !important;
    display:inline-block !important;
    vertical-align:middle !important;
}

.network-shortcut-card-v130 p,
.network-page-head-v130 p,
.network-detail-hero-v130 p,
.network-agency-card-v130 p,
.network-staff-card-v130 p,
.network-app-row-v130 p {
    color:#667085 !important;
    font-weight:700 !important;
    margin:4px 0 !important;
}
.network-page-head-v130 {
    padding:24px !important;
    margin:20px 0 !important;
    background:linear-gradient(135deg,#EEF5FF,#FFFFFF) !important;
}
.network-agency-card-v130 {
    display:flex !important;
    align-items:center !important;
    gap:18px !important;
    padding:20px !important;
    margin:16px 0 10px 0 !important;
}
.agency-logo-v130 {
    border-radius:18px !important;
    background:#F8FAFC !important;
    border:1px solid #E4EAF3 !important;
    display:flex !important;
    align-items:center !important;
    justify-content:center !important;
    overflow:hidden !important;
    flex:0 0 auto !important;
}
.agency-logo-v130 img {
    max-width:88% !important;
    max-height:88% !important;
    object-fit:contain !important;
}
.logo-fallback-v130 {
    color:#005BDB !important;
    -webkit-text-fill-color:#005BDB !important;
    font-size:24px !important;
    font-weight:950 !important;
}
.network-agency-card-v130 h3,
.network-staff-card-v130 h3,
.network-app-row-v130 h4 {
    color:#101828 !important;
    -webkit-text-fill-color:#101828 !important;
    font-weight:950 !important;
    margin:0 0 8px 0 !important;
}
.official-star-v130 {
    display:inline-flex !important;
    padding:6px 10px !important;
    border-radius:999px !important;
    background:#FEF3C7 !important;
    color:#92400E !important;
    -webkit-text-fill-color:#92400E !important;
    font-size:12px !important;
    font-weight:950 !important;
    margin-left:8px !important;
}
.network-detail-hero-v130 {
    display:flex !important;
    align-items:center !important;
    gap:22px !important;
    padding:26px !important;
    margin:22px 0 !important;
    background:linear-gradient(135deg,#EEF5FF,#FFFFFF) !important;
}
.network-detail-hero-v130 span {
    color:#005BDB !important;
    -webkit-text-fill-color:#005BDB !important;
    font-weight:950 !important;
    text-transform:uppercase !important;
    font-size:13px !important;
}
.network-staff-card-v130,
.network-app-row-v130 {
    padding:18px 20px !important;
    margin:14px 0 !important;
}
.network-app-row-v130 {
    display:grid !important;
    grid-template-columns:minmax(0,1fr) auto !important;
    gap:16px !important;
    align-items:center !important;
}
@media(max-width:900px){
    .network-shortcut-grid-v130 {
        grid-template-columns:1fr !important;
    }
    .network-agency-card-v130,
    .network-detail-hero-v130 {
        flex-direction:column !important;
        align-items:flex-start !important;
    }
    .network-app-row-v130 {
        grid-template-columns:1fr !important;
    }
}


/* v131 application detail page layout fix */
.admin-app-detail-hero-v131 {
    display:grid !important;
    grid-template-columns:170px minmax(0,1fr) auto !important;
    gap:28px !important;
    align-items:center !important;
    background:linear-gradient(135deg,#F4F8FF 0%,#FFFFFF 100%) !important;
    border:1px solid #BFD7FF !important;
    border-radius:28px !important;
    padding:32px 34px !important;
    margin:22px 0 28px 0 !important;
    box-shadow:0 18px 42px rgba(16,24,40,.08) !important;
}
.admin-app-detail-logo-v131 {
    width:150px !important;
    height:150px !important;
    border-radius:24px !important;
    background:#FFFFFF !important;
    border:1px solid #DCE6F4 !important;
    display:flex !important;
    align-items:center !important;
    justify-content:center !important;
    overflow:hidden !important;
    box-shadow:0 12px 28px rgba(16,24,40,.08) !important;
}
.admin-app-detail-logo-v131 img {
    max-width:128px !important;
    max-height:128px !important;
    object-fit:contain !important;
}
.admin-app-detail-main-v131 {
    min-width:0 !important;
}
.admin-app-detail-label-v131 {
    display:inline-flex !important;
    align-items:center !important;
    padding:7px 12px !important;
    border-radius:999px !important;
    background:#EAF2FF !important;
    color:#005BDB !important;
    -webkit-text-fill-color:#005BDB !important;
    font-size:13px !important;
    font-weight:950 !important;
    text-transform:uppercase !important;
    letter-spacing:.05em !important;
    margin-bottom:12px !important;
}
.admin-app-detail-hero-v131 h1 {
    color:#101828 !important;
    -webkit-text-fill-color:#101828 !important;
    font-size:36px !important;
    line-height:1.15 !important;
    font-weight:950 !important;
    margin:0 0 16px 0 !important;
    text-transform:capitalize !important;
}
.admin-app-detail-meta-v131 {
    display:grid !important;
    grid-template-columns:repeat(3,minmax(0,1fr)) !important;
    gap:12px !important;
}
.admin-app-detail-meta-v131 span {
    display:block !important;
    background:#FFFFFF !important;
    border:1px solid #E4EAF3 !important;
    border-radius:16px !important;
    padding:12px 14px !important;
    color:#344054 !important;
    -webkit-text-fill-color:#344054 !important;
    font-weight:800 !important;
    word-break:break-word !important;
}
.admin-app-detail-meta-v131 b {
    display:block !important;
    color:#005BDB !important;
    -webkit-text-fill-color:#005BDB !important;
    font-size:12px !important;
    text-transform:uppercase !important;
    letter-spacing:.04em !important;
    margin-bottom:5px !important;
}
.admin-app-detail-status-v131 {
    min-width:170px !important;
    display:flex !important;
    justify-content:flex-end !important;
    align-items:center !important;
}
.admin-app-detail-status-v131 span,
.admin-app-detail-status-v131 .status-pending,
.admin-app-detail-status-v131 .status-approved,
.admin-app-detail-status-v131 .status-rejected {
    font-size:14px !important;
    padding:12px 22px !important;
    border-radius:999px !important;
    font-weight:950 !important;
    white-space:nowrap !important;
}
@media(max-width:1000px){
    .admin-app-detail-hero-v131 {
        grid-template-columns:1fr !important;
        align-items:flex-start !important;
    }
    .admin-app-detail-meta-v131 {
        grid-template-columns:1fr !important;
    }
    .admin-app-detail-status-v131 {
        justify-content:flex-start !important;
    }
}


/* v132 professional uploaded document cards */
.admin-doc-card-v132,
.admin-doc-missing-v132 {
    display:flex !important;
    align-items:center !important;
    gap:14px !important;
    background:#F8FAFC !important;
    border:1px solid #DCE6F4 !important;
    border-radius:18px !important;
    padding:18px 18px !important;
    margin:10px 0 10px 0 !important;
    min-height:96px !important;
    box-shadow:0 8px 20px rgba(16,24,40,.05) !important;
}
.admin-doc-card-v132 {
    background:linear-gradient(135deg,#F8FAFC,#FFFFFF) !important;
}
.admin-doc-missing-v132 {
    background:#FFF7ED !important;
    border-color:#FDBA74 !important;
}
.admin-doc-icon-v132 {
    width:48px !important;
    height:48px !important;
    border-radius:14px !important;
    display:flex !important;
    align-items:center !important;
    justify-content:center !important;
    background:#EAF2FF !important;
    color:#005BDB !important;
    -webkit-text-fill-color:#005BDB !important;
    font-size:22px !important;
    flex:0 0 auto !important;
}
.admin-doc-missing-v132 .admin-doc-icon-v132 {
    background:#FFEDD5 !important;
    color:#EA580C !important;
    -webkit-text-fill-color:#EA580C !important;
}
.admin-doc-card-v132 b,
.admin-doc-missing-v132 b {
    display:block !important;
    color:#002B5B !important;
    -webkit-text-fill-color:#002B5B !important;
    font-size:17px !important;
    font-weight:950 !important;
    margin-bottom:5px !important;
}
.admin-doc-card-v132 span,
.admin-doc-missing-v132 span {
    display:block !important;
    color:#667085 !important;
    -webkit-text-fill-color:#667085 !important;
    font-size:14px !important;
    font-weight:700 !important;
    line-height:1.35 !important;
}
/* Make document download buttons visually consistent */
.admin-doc-card-v132 + div button,
.admin-doc-missing-v132 + div button {
    border-radius:14px !important;
    font-weight:850 !important;
    min-height:44px !important;
}


/* v133 professional dashboard navigation icons */
.dash-nav-icon-v96 {
    width:22px !important;
    height:22px !important;
    display:inline-flex !important;
    align-items:center !important;
    justify-content:center !important;
    color:#344054 !important;
    -webkit-text-fill-color:initial !important;
    font-size:0 !important;
    line-height:1 !important;
    margin-right:10px !important;
}
.dash-nav-icon-v96 svg {
    width:21px !important;
    height:21px !important;
    fill:none !important;
    stroke:currentColor !important;
    stroke-width:2 !important;
    stroke-linecap:round !important;
    stroke-linejoin:round !important;
    display:block !important;
}
.dash-nav-link-v96 {
    gap:8px !important;
}
.dash-nav-link-v96.active .dash-nav-icon-v96,
.dash-nav-link-v96.active .dash-nav-icon-v96 svg {
    color:#FFFFFF !important;
    stroke:#FFFFFF !important;
}
.dash-nav-link-v96.logout .dash-nav-icon-v96,
.dash-nav-link-v96.logout .dash-nav-icon-v96 svg {
    color:#9F1D1D !important;
    stroke:#9F1D1D !important;
}
.dash-nav-link-v96.logout.active .dash-nav-icon-v96,
.dash-nav-link-v96.logout.active .dash-nav-icon-v96 svg {
    color:#FFFFFF !important;
    stroke:#FFFFFF !important;
}


/* v134 applicant photo in admin application detail */
.applicant-photo-box-v134 {
    border-radius:24px !important;
    background:#FFFFFF !important;
    border:1px solid #DCE6F4 !important;
    display:flex !important;
    align-items:center !important;
    justify-content:center !important;
    overflow:hidden !important;
    box-shadow:0 12px 28px rgba(16,24,40,.08) !important;
}
.applicant-photo-box-v134 img {
    width:100% !important;
    height:100% !important;
    object-fit:cover !important;
    display:block !important;
}
.applicant-photo-fallback-v134 {
    flex-direction:column !important;
    background:linear-gradient(135deg,#EEF5FF,#FFFFFF) !important;
}
.applicant-photo-fallback-v134 span {
    color:#005BDB !important;
    -webkit-text-fill-color:#005BDB !important;
    font-size:34px !important;
    font-weight:950 !important;
    line-height:1 !important;
}
.applicant-photo-fallback-v134 small {
    color:#667085 !important;
    -webkit-text-fill-color:#667085 !important;
    font-size:12px !important;
    font-weight:800 !important;
    margin-top:8px !important;
}
.admin-app-detail-logo-v131 {
    width:160px !important;
    height:160px !important;
    border:none !important;
    background:transparent !important;
    box-shadow:none !important;
}


/* v135 full applicant photo, no crop */
.applicant-photo-box-v134 {
    width:220px !important;
    height:220px !important;
    border-radius:26px !important;
    background:#FFFFFF !important;
    padding:10px !important;
}
.applicant-photo-box-v134 img {
    width:100% !important;
    height:100% !important;
    object-fit:contain !important; /* show full uploaded image, do not crop */
    object-position:center center !important;
    background:#FFFFFF !important;
    display:block !important;
}
.admin-app-detail-logo-v131 {
    width:220px !important;
    height:220px !important;
    min-width:220px !important;
}
.admin-app-detail-hero-v131 {
    grid-template-columns:240px minmax(0,1fr) auto !important;
    align-items:center !important;
}
@media(max-width:1000px){
    .admin-app-detail-hero-v131 {
        grid-template-columns:1fr !important;
    }
    .admin-app-detail-logo-v131,
    .applicant-photo-box-v134 {
        width:200px !important;
        height:200px !important;
        min-width:200px !important;
    }
}


/* v136 applicant photo fills the full photo box */
.applicant-photo-box-v134 {
    width:220px !important;
    height:220px !important;
    border-radius:26px !important;
    background:#FFFFFF !important;
    padding:0 !important;
    overflow:hidden !important;
}
.applicant-photo-box-v134 img {
    width:100% !important;
    height:100% !important;
    object-fit:cover !important; /* make photo as big as the box */
    object-position:center center !important;
    display:block !important;
}
.admin-app-detail-logo-v131 {
    width:220px !important;
    height:220px !important;
    min-width:220px !important;
}
@media(max-width:1000px){
    .admin-app-detail-logo-v131,
    .applicant-photo-box-v134 {
        width:200px !important;
        height:200px !important;
        min-width:200px !important;
    }
}


/* v137 larger applicant photo without cropping */
.admin-app-detail-hero-v131 {
    grid-template-columns:300px minmax(0,1fr) auto !important;
    gap:34px !important;
    align-items:center !important;
}
.admin-app-detail-logo-v131 {
    width:280px !important;
    height:280px !important;
    min-width:280px !important;
    border:none !important;
    background:transparent !important;
    box-shadow:none !important;
}
.applicant-photo-box-v134 {
    width:280px !important;
    height:280px !important;
    border-radius:28px !important;
    background:#FFFFFF !important;
    padding:8px !important;
    overflow:hidden !important;
    display:flex !important;
    align-items:center !important;
    justify-content:center !important;
    border:1px solid #DCE6F4 !important;
    box-shadow:0 14px 32px rgba(16,24,40,.10) !important;
}
.applicant-photo-box-v134 img {
    width:100% !important;
    height:100% !important;
    max-width:100% !important;
    max-height:100% !important;
    object-fit:contain !important; /* show full uploaded photo, no cropping */
    object-position:center center !important;
    background:#FFFFFF !important;
    display:block !important;
    border-radius:20px !important;
}
@media(max-width:1000px){
    .admin-app-detail-hero-v131 {
        grid-template-columns:1fr !important;
    }
    .admin-app-detail-logo-v131,
    .applicant-photo-box-v134 {
        width:240px !important;
        height:240px !important;
        min-width:240px !important;
    }
}


/* v138 applicant country flag and university logo in detail header */
.admin-app-detail-hero-v138 {
    grid-template-columns:300px minmax(0,1fr) 260px !important;
    gap:34px !important;
    align-items:center !important;
}
.applicant-name-with-flag-v138 {
    display:flex !important;
    align-items:center !important;
    gap:14px !important;
    flex-wrap:wrap !important;
}
.applicant-flag-v138 {
    width:54px !important;
    height:38px !important;
    border-radius:10px !important;
    overflow:hidden !important;
    display:inline-flex !important;
    align-items:center !important;
    justify-content:center !important;
    background:#FFFFFF !important;
    border:1px solid #DCE6F4 !important;
    box-shadow:0 8px 18px rgba(16,24,40,.10) !important;
    vertical-align:middle !important;
}
.applicant-flag-v138 img {
    width:100% !important;
    height:100% !important;
    object-fit:cover !important;
    display:block !important;
}
.applicant-flag-fallback-v138 {
    color:#005BDB !important;
    -webkit-text-fill-color:#005BDB !important;
    font-size:15px !important;
    font-weight:950 !important;
}
.admin-app-detail-right-v138 {
    display:flex !important;
    flex-direction:column !important;
    align-items:center !important;
    justify-content:center !important;
    gap:18px !important;
    background:#FFFFFF !important;
    border:1px solid #E4EAF3 !important;
    border-radius:24px !important;
    padding:22px 18px !important;
    box-shadow:0 14px 32px rgba(16,24,40,.07) !important;
    min-height:190px !important;
}
.detail-university-logo-v138 {
    width:104px !important;
    height:104px !important;
    border-radius:22px !important;
    background:#F8FAFC !important;
    border:1px solid #DCE6F4 !important;
    display:flex !important;
    align-items:center !important;
    justify-content:center !important;
    overflow:hidden !important;
}
.detail-university-logo-v138 img {
    max-width:88px !important;
    max-height:88px !important;
    object-fit:contain !important;
    display:block !important;
}
.detail-university-logo-v138.logo-fallback-v138 {
    color:#005BDB !important;
    -webkit-text-fill-color:#005BDB !important;
    font-size:26px !important;
    font-weight:950 !important;
}
.admin-app-detail-right-v138 .admin-app-detail-status-v131 {
    min-width:0 !important;
    width:100% !important;
    justify-content:center !important;
}
.admin-app-detail-right-v138 .admin-app-detail-status-v131 span,
.admin-app-detail-right-v138 .admin-app-detail-status-v131 .status-pending,
.admin-app-detail-right-v138 .admin-app-detail-status-v131 .status-approved,
.admin-app-detail-right-v138 .admin-app-detail-status-v131 .status-rejected {
    width:100% !important;
    text-align:center !important;
}
@media(max-width:1100px){
    .admin-app-detail-hero-v138 {
        grid-template-columns:1fr !important;
    }
    .admin-app-detail-right-v138 {
        align-items:flex-start !important;
        width:100% !important;
    }
    .admin-app-detail-right-v138 .admin-app-detail-status-v131 {
        justify-content:flex-start !important;
    }
}


/* v139 full country flag and larger university logo */
.applicant-name-with-flag-v138 {
    gap:18px !important;
}
.applicant-flag-v138 {
    display:none !important;
}
.applicant-flag-v139 {
    width:76px !important;
    height:56px !important;
    border-radius:14px !important;
    display:inline-flex !important;
    align-items:center !important;
    justify-content:center !important;
    background:#FFFFFF !important;
    border:1px solid #DCE6F4 !important;
    box-shadow:0 8px 18px rgba(16,24,40,.10) !important;
    vertical-align:middle !important;
    overflow:visible !important;
    flex:0 0 auto !important;
}
.applicant-flag-emoji-v139 {
    font-size:48px !important;
    line-height:1 !important;
    font-family:"Apple Color Emoji","Segoe UI Emoji","Noto Color Emoji",sans-serif !important;
    -webkit-text-fill-color:initial !important;
}
.applicant-flag-fallback-v139 {
    color:#005BDB !important;
    -webkit-text-fill-color:#005BDB !important;
    font-size:18px !important;
    font-weight:950 !important;
}
.admin-app-detail-right-v138 {
    width:280px !important;
    min-height:250px !important;
    padding:26px 24px !important;
    gap:20px !important;
}
.detail-university-logo-v138 {
    width:180px !important;
    height:180px !important;
    border-radius:30px !important;
    background:#FFFFFF !important;
    border:1px solid #DCE6F4 !important;
    box-shadow:0 12px 30px rgba(16,24,40,.09) !important;
}
.detail-university-logo-v138 img {
    max-width:152px !important;
    max-height:152px !important;
    object-fit:contain !important;
    display:block !important;
}
.detail-university-logo-v138.logo-fallback-v138 {
    font-size:38px !important;
}
.admin-app-detail-hero-v138 {
    grid-template-columns:300px minmax(0,1fr) 320px !important;
}
@media(max-width:1100px){
    .admin-app-detail-hero-v138 {
        grid-template-columns:1fr !important;
    }
    .admin-app-detail-right-v138 {
        width:100% !important;
        min-height:auto !important;
        align-items:center !important;
    }
    .detail-university-logo-v138 {
        width:150px !important;
        height:150px !important;
    }
    .detail-university-logo-v138 img {
        max-width:128px !important;
        max-height:128px !important;
    }
}


/* v140 real country flag image renderer */
.applicant-flag-v138,
.applicant-flag-v139 {
    display:none !important;
}
.applicant-name-with-flag-v138 {
    display:flex !important;
    align-items:center !important;
    gap:18px !important;
    flex-wrap:wrap !important;
}
.applicant-flag-v140 {
    width:86px !important;
    height:66px !important;
    border-radius:14px !important;
    display:inline-flex !important;
    align-items:center !important;
    justify-content:center !important;
    background:#FFFFFF !important;
    border:1px solid #DCE6F4 !important;
    box-shadow:0 8px 18px rgba(16,24,40,.10) !important;
    vertical-align:middle !important;
    overflow:visible !important;
    flex:0 0 auto !important;
    padding:7px !important;
}
.nepal-flag-v140 svg {
    width:64px !important;
    height:58px !important;
    display:block !important;
}
.rectangle-flag-v140 img {
    max-width:100% !important;
    max-height:100% !important;
    width:auto !important;
    height:auto !important;
    object-fit:contain !important;
    display:block !important;
    border-radius:7px !important;
}
.applicant-flag-fallback-v140 {
    color:#005BDB !important;
    -webkit-text-fill-color:#005BDB !important;
    font-size:18px !important;
    font-weight:950 !important;
}


/* v143 official representative verified icon sizing fix */
.official-rep-icon-inline-v141,
.official-rep-icon-badge-v141,
.official-rep-icon-dashboard-v142 {
    object-fit:contain !important;
    display:inline-block !important;
    vertical-align:middle !important;
    flex:0 0 auto !important;
    background:transparent !important;
    border:none !important;
    box-shadow:none !important;
    padding:0 !important;
    margin:0 !important;
}
.official-rep-icon-inline-v141 { width:26px !important; height:26px !important; max-width:26px !important; max-height:26px !important; }
.official-rep-icon-badge-v141 { width:20px !important; height:20px !important; max-width:20px !important; max-height:20px !important; }
.official-rep-icon-dashboard-v142 { width:24px !important; height:24px !important; max-width:24px !important; max-height:24px !important; }
.stat-icon-v73 .official-rep-icon-dashboard-v142 { width:24px !important; height:24px !important; }
.official-rep-name-wrap-v141 { display:inline-flex !important; align-items:center !important; gap:8px !important; }
.official-rep-name-wrap-v141, .official-rep-badge-v141 { background:transparent !important; border:none !important; box-shadow:none !important; }


/* v146 verified badge only for official representative agencies */
.partner-agency-card-v146 .official-rep-icon-inline-v141,
.partner-agency-card-v146 .official-rep-badge-v141 {
    display:none !important;
}


/* v149 dashboard card actions no home redirect */
.admin-stat-card-link-v148 {
    text-decoration:none !important;
    color:inherit !important;
    cursor:default !important;
}
.admin-card-action-row-v149 {
    margin:10px 0 24px 0 !important;
}
.admin-card-action-row-v149 + div button,
.admin-card-action-row-v149 ~ div button {
    border-radius:14px !important;
    font-weight:850 !important;
}


/* v150 dedicated pending approval page */
.pending-request-card-v150 {
    background:#FFFFFF !important;
    border:1px solid #DCE6F4 !important;
    border-radius:22px !important;
    padding:22px 24px !important;
    margin:18px 0 10px 0 !important;
    box-shadow:0 10px 28px rgba(16,24,40,.06) !important;
}
.pending-request-card-v150 h3 {
    margin:10px 0 10px 0 !important;
    color:#002B5B !important;
    -webkit-text-fill-color:#002B5B !important;
    font-size:24px !important;
    font-weight:950 !important;
}
.pending-request-card-v150 p {
    color:#475467 !important;
    -webkit-text-fill-color:#475467 !important;
    font-size:15px !important;
    line-height:1.7 !important;
    margin:4px 0 !important;
}
.pending-chip-v150 {
    display:inline-flex !important;
    align-items:center !important;
    justify-content:center !important;
    padding:7px 14px !important;
    border-radius:999px !important;
    background:#FFF4D8 !important;
    color:#9A5B00 !important;
    -webkit-text-fill-color:#9A5B00 !important;
    font-size:13px !important;
    font-weight:900 !important;
}


/* v151 pending approval action buttons on the right side */
.pending-request-card-v151 {
    min-height:230px !important;
    display:flex !important;
    align-items:center !important;
}
.pending-action-panel-v151 {
    min-height:230px !important;
    height:100% !important;
    display:flex !important;
    flex-direction:column !important;
    justify-content:center !important;
    gap:18px !important;
    background:#FFFFFF !important;
    border:1px solid #DCE6F4 !important;
    border-radius:22px !important;
    padding:28px 22px !important;
    margin:18px 0 10px 0 !important;
    box-shadow:0 10px 28px rgba(16,24,40,.06) !important;
}
/* first button in the action panel = Approve */
.pending-action-panel-v151 + div button,
.pending-action-panel-v151 ~ div button {
    font-weight:900 !important;
    border-radius:14px !important;
}
/* More reliable Streamlit button targeting for pending approval page */
div[data-testid="column"]:has(.pending-action-panel-v151) button[kind="primary"] {
    background:#16A34A !important;
    border:1px solid #16A34A !important;
    color:#FFFFFF !important;
    font-weight:950 !important;
}
div[data-testid="column"]:has(.pending-action-panel-v151) button[kind="secondary"] {
    background:#DC2626 !important;
    border:1px solid #DC2626 !important;
    color:#FFFFFF !important;
    font-weight:950 !important;
}
div[data-testid="column"]:has(.pending-action-panel-v151) button p {
    color:#FFFFFF !important;
    -webkit-text-fill-color:#FFFFFF !important;
    font-weight:950 !important;
}
@media(max-width:900px){
    .pending-action-panel-v151,
    .pending-request-card-v151 {
        min-height:auto !important;
    }
}


/* v152 pending approval buttons: no empty box, colored action buttons */
.pending-row-v152 {
    display:grid !important;
    grid-template-columns:minmax(0, 1fr) 260px !important;
    gap:26px !important;
    align-items:stretch !important;
    margin:18px 0 20px 0 !important;
}
.pending-request-card-v152 {
    min-height:230px !important;
    height:100% !important;
    margin:0 !important;
    display:flex !important;
    align-items:center !important;
}
.pending-action-panel-v152 {
    min-height:230px !important;
    height:100% !important;
    display:flex !important;
    flex-direction:column !important;
    justify-content:center !important;
    gap:20px !important;
    background:transparent !important;
    border:none !important;
    box-shadow:none !important;
    padding:0 !important;
    margin:0 !important;
}
.pending-action-btn-v152 {
    width:100% !important;
    min-height:58px !important;
    display:flex !important;
    align-items:center !important;
    justify-content:center !important;
    border-radius:15px !important;
    text-decoration:none !important;
    color:#FFFFFF !important;
    -webkit-text-fill-color:#FFFFFF !important;
    font-size:17px !important;
    font-weight:950 !important;
    letter-spacing:.2px !important;
    box-shadow:0 12px 26px rgba(16,24,40,.12) !important;
}
.pending-action-btn-v152.approve-v152 {
    background:#16A34A !important;
    border:1px solid #16A34A !important;
}
.pending-action-btn-v152.approve-v152:hover {
    background:#15803D !important;
    border-color:#15803D !important;
}
.pending-action-btn-v152.decline-v152 {
    background:#DC2626 !important;
    border:1px solid #DC2626 !important;
}
.pending-action-btn-v152.decline-v152:hover {
    background:#B91C1C !important;
    border-color:#B91C1C !important;
}
@media(max-width:900px){
    .pending-row-v152 {
        grid-template-columns:1fr !important;
    }
    .pending-action-panel-v152,
    .pending-request-card-v152 {
        min-height:auto !important;
    }
}


/* v154 pending approval logo/photo visual */
.pending-request-card-v154 {
    display:grid !important;
    grid-template-columns:150px minmax(0,1fr) !important;
    gap:24px !important;
    align-items:center !important;
}
.pending-visual-box-v154 {
    width:138px !important;
    height:138px !important;
    border-radius:22px !important;
    background:#F8FAFC !important;
    border:1px solid #DCE6F4 !important;
    display:flex !important;
    flex-direction:column !important;
    align-items:center !important;
    justify-content:center !important;
    overflow:hidden !important;
    box-shadow:0 10px 24px rgba(16,24,40,.06) !important;
}
.pending-visual-box-v154 img {
    max-width:112px !important;
    max-height:96px !important;
    object-fit:contain !important;
    display:block !important;
}
.pending-staff-img-v154 {
    width:112px !important;
    height:112px !important;
    max-width:112px !important;
    max-height:112px !important;
    object-fit:contain !important;
    border-radius:12px !important;
    background:#FFFFFF !important;
}
.pending-logo-img-v154 {
    width:112px !important;
    height:96px !important;
    object-fit:contain !important;
}
.pending-visual-box-v154 span {
    margin-top:8px !important;
    font-size:11px !important;
    font-weight:800 !important;
    color:#667085 !important;
    -webkit-text-fill-color:#667085 !important;
}
.pending-visual-fallback-v154 div {
    font-size:34px !important;
    font-weight:950 !important;
    color:#3D5AD6 !important;
    -webkit-text-fill-color:#3D5AD6 !important;
}
@media(max-width:900px){
    .pending-request-card-v154 {
        grid-template-columns:1fr !important;
    }
}


/* v155 login redirect and return-to-application buttons */
.application-locked-v155 {
    padding:34px 38px !important;
}
.application-login-actions-v155 {
    display:flex !important;
    gap:16px !important;
    flex-wrap:wrap !important;
    margin-top:26px !important;
}
.application-login-btn-v155 {
    min-width:240px !important;
    min-height:54px !important;
    display:flex !important;
    align-items:center !important;
    justify-content:center !important;
    border-radius:14px !important;
    text-decoration:none !important;
    font-size:16px !important;
    font-weight:950 !important;
    letter-spacing:.2px !important;
}
.application-login-btn-v155.primary-v155 {
    background:#3D5AD6 !important;
    border:1px solid #3D5AD6 !important;
    color:#FFFFFF !important;
    -webkit-text-fill-color:#FFFFFF !important;
    box-shadow:0 14px 30px rgba(61,90,214,.22) !important;
}
.application-login-btn-v155.secondary-v155 {
    background:#FFFFFF !important;
    border:1px solid #D0D5DD !important;
    color:#101828 !important;
    -webkit-text-fill-color:#101828 !important;
}
.application-login-btn-v155.primary-v155:hover {
    background:#2446C7 !important;
    border-color:#2446C7 !important;
}
.application-login-btn-v155.secondary-v155:hover {
    background:#F8FAFC !important;
}


/* v161 logged-in top navigation */
.nav-user-box-v161 {
    display:flex !important;
    align-items:center !important;
    gap:14px !important;
}
.nav-user-name-v161 {
    min-width:190px !important;
    max-width:300px !important;
    height:58px !important;
    padding:0 22px !important;
    border-radius:10px !important;
    border:1px solid #D0D5DD !important;
    background:#FFFFFF !important;
    display:flex !important;
    align-items:center !important;
    justify-content:center !important;
    color:#101828 !important;
    -webkit-text-fill-color:#101828 !important;
    font-weight:950 !important;
    white-space:nowrap !important;
    overflow:hidden !important;
    text-overflow:ellipsis !important;
}
.nav-logout-v161 {
    min-width:150px !important;
    height:58px !important;
    padding:0 26px !important;
    border-radius:10px !important;
    background:#B42318 !important;
    color:#FFFFFF !important;
    -webkit-text-fill-color:#FFFFFF !important;
    text-decoration:none !important;
    display:flex !important;
    align-items:center !important;
    justify-content:center !important;
    font-weight:950 !important;
}
.nav-logout-v161:hover {
    background:#912018 !important;
    color:#FFFFFF !important;
    -webkit-text-fill-color:#FFFFFF !important;
}


/* v164 partner hero raw HTML fix */
.partner-hero-v164 p {
    background:transparent !important;
    color:#FFFFFF !important;
    -webkit-text-fill-color:#FFFFFF !important;
    font-family:inherit !important;
}
.partner-hero-v164 code,
.partner-hero-v164 pre {
    display:none !important;
}


/* v168 IEQAS accreditation dynamic transparent badge */
.ieqas-badge-v168 {
    background: transparent !important;
    display: flex !important;
    align-items: center !important;
    justify-content: center !important;
    margin: 14px auto 0 auto !important;
    position: relative !important;
}
.ieqas-badge-large-v168 { width: 0 !important; height: 0 !important; display:none !important; }
.ieqas-badge-compact-v168 { width: 120px !important; height: 120px !important; margin-top: 12px !important; }
.ieqas-ring-v168 {
    position: absolute !important;
    width: inherit !important;
    height: inherit !important;
    border-radius: 50% !important;
    background: radial-gradient(circle, rgba(255,255,255,0) 58%, rgba(238,212,132,.45) 59%, rgba(238,212,132,.65) 76%, rgba(255,255,255,0) 77%) !important;
    border: 1px solid rgba(185,146,39,.24) !important;
}
.ieqas-inner-v168 {
    position: relative !important;
    width: 78% !important;
    height: 78% !important;
    border-radius: 50% !important;
    background: rgba(255,255,255,.92) !important;
    border: 1px solid rgba(215,188,105,.48) !important;
    display: flex !important;
    flex-direction: column !important;
    align-items: center !important;
    justify-content: center !important;
    text-align: center !important;
    padding: 12px !important;
    box-shadow: 0 10px 28px rgba(16,24,40,.08) !important;
    overflow: hidden !important;
}
.ieqas-ring-v168 span {
    position: absolute !important;
    color: #7B6118 !important;
    font-weight: 900 !important;
    font-size: 10px !important;
    text-transform: uppercase !important;
    letter-spacing: .3px !important;
}
.ieqas-ring-v168 span:nth-child(1) { top: 8%; left: 25%; transform: rotate(-5deg); }
.ieqas-ring-v168 span:nth-child(2) { bottom: 8%; left: 42%; }
.ieqas-ring-v168 span:nth-child(3) { right: 2%; top: 42%; transform: rotate(84deg); }
.ieqas-korean-symbol-v168 { color: #002B5B !important; font-size: 18px !important; line-height: 1 !important; margin-bottom: 3px !important; }
.ieqas-small-title-v168 { color: #111827 !important; font-size: 8px !important; font-weight: 800 !important; line-height: 1.1 !important; }
.ieqas-blue-ribbon-v168 {
    margin: 5px 0 !important;
    background: #002B5B !important;
    color: #FFFFFF !important;
    -webkit-text-fill-color: #FFFFFF !important;
    font-size: 9px !important;
    font-weight: 900 !important;
    padding: 4px 8px !important;
    border-radius: 3px !important;
}
.ieqas-logo-name-v168 {
    display: flex !important;
    align-items: center !important;
    justify-content: center !important;
    gap: 6px !important;
    margin: 2px 0 4px 0 !important;
}
.ieqas-logo-name-v168 img { width: 28px !important; height: 28px !important; object-fit: contain !important; }
.ieqas-logo-fallback-v168 {
    width: 24px !important; height: 24px !important; border-radius: 50% !important; background: #EEF5FF !important; color: #002B5B !important;
    display: inline-flex !important; align-items: center !important; justify-content: center !important;
}
.ieqas-logo-name-v168 strong { color: #002B5B !important; font-size: 10px !important; font-weight: 950 !important; line-height: 1.05 !important; }
.ieqas-main-text-v168 { color: #002B5B !important; font-size: 13px !important; font-weight: 950 !important; letter-spacing: .5px !important; }
.ieqas-sub-text-v168 { color: #111827 !important; font-size: 10px !important; font-weight: 900 !important; }
.ieqas-valid-v168 { color: #111827 !important; font-size: 8px !important; font-weight: 800 !important; margin-top: 2px !important; }
.ieqas-badge-compact-v168 .ieqas-ring-v168 span,
.ieqas-badge-compact-v168 .ieqas-small-title-v168,
.ieqas-badge-compact-v168 .ieqas-korean-symbol-v168,
.ieqas-badge-compact-v168 .ieqas-valid-v168 { display: none !important; }
.ieqas-badge-compact-v168 .ieqas-blue-ribbon-v168 { font-size: 7px !important; padding: 3px 5px !important; }
.ieqas-badge-compact-v168 .ieqas-logo-name-v168 { flex-direction: column !important; gap: 2px !important; }
.ieqas-badge-compact-v168 .ieqas-logo-name-v168 img { width: 24px !important; height: 24px !important; }
.ieqas-badge-compact-v168 .ieqas-logo-name-v168 strong { font-size: 8px !important; }
.ieqas-badge-compact-v168 .ieqas-main-text-v168 { font-size: 8px !important; }
.ieqas-badge-compact-v168 .ieqas-sub-text-v168 { font-size: 8px !important; }





/* v170 sample-style IEQAS excellent badge next to university name */
.uni-detail-name-v99,
.uni-name-accent-v93 {
    display: flex !important;
    align-items: center !important;
    gap: 14px !important;
    flex-wrap: wrap !important;
}
.ieqas-name-badge-v170 {
    display: inline-flex !important;
    align-items: center !important;
    justify-content: center !important;
    width: 124px !important;
    min-width: 124px !important;
    height: 124px !important;
    background: transparent !important;
    vertical-align: middle !important;
}
.ieqas-name-badge-svg-v170 {
    width: 124px !important;
    height: 124px !important;
    display: block !important;
    overflow: visible !important;
}
.ieqas-badge-large-v168,
.ieqas-badge-compact-v168,
.ieqas-name-badge-v169,
.ieqas-name-badge-ring-v169,
.ieqas-name-badge-check-v169 {
    display: none !important;
}


/* v174 restored university detail + small IEQAS badge */
.uni-detail-name-v99,
.uni-name-accent-v93 {
    display: flex !important;
    align-items: center !important;
    gap: 12px !important;
    flex-wrap: wrap !important;
}
.ieqas-mini-seal-v174 {
    width: 72px !important;
    height: 72px !important;
    min-width: 72px !important;
    max-width: 72px !important;
    max-height: 72px !important;
    border-radius: 50% !important;
    display: inline-flex !important;
    align-items: center !important;
    justify-content: center !important;
    position: relative !important;
    background: radial-gradient(circle, #ffffff 0 48%, #fff8dc 49% 62%, #d6b75a 63% 100%) !important;
    border: 1.2px solid #b8932c !important;
    box-shadow: 0 6px 16px rgba(16,24,40,.14) !important;
    overflow: hidden !important;
    vertical-align: middle !important;
}
.ieqas-mini-ring-text-v174 {
    position: absolute !important;
    top: 5px !important;
    left: 0 !important;
    right: 0 !important;
    text-align: center !important;
    color: #111827 !important;
    font-size: 7px !important;
    font-weight: 900 !important;
    letter-spacing: .8px !important;
}
.ieqas-mini-inner-v174 {
    width: 50px !important;
    height: 50px !important;
    border-radius: 50% !important;
    background: rgba(255,255,255,.96) !important;
    border: 1px solid rgba(214,183,90,.8) !important;
    display: flex !important;
    flex-direction: column !important;
    align-items: center !important;
    justify-content: center !important;
    gap: 1px !important;
    padding: 3px !important;
}
.ieqas-mini-label-v174 {
    background: #082a63 !important;
    color: #fff !important;
    -webkit-text-fill-color: #fff !important;
    font-size: 6px !important;
    font-weight: 900 !important;
    line-height: 1 !important;
    padding: 2px 4px !important;
    border-radius: 2px !important;
}
.ieqas-mini-logo-v174 {
    width: 28px !important;
    height: 18px !important;
    display: inline-flex !important;
    align-items: center !important;
    justify-content: center !important;
}
.ieqas-mini-logo-v174 img {
    width: 28px !important;
    height: 18px !important;
    object-fit: contain !important;
    display: block !important;
}
.ieqas-mini-initial-v174 {
    color: #082a63 !important;
    font-size: 14px !important;
    font-weight: 950 !important;
    line-height: 1 !important;
}
.ieqas-mini-date-v174 {
    color: #111827 !important;
    font-size: 5.5px !important;
    font-weight: 800 !important;
    line-height: 1 !important;
}
.ieqas-badge-large-v168,
.ieqas-badge-compact-v168,
.ieqas-name-badge-v169,
.ieqas-name-badge-v170,
.ieqas-mini-badge-v173,
.ieqas-component-wrap {
    display: none !important;
}


/* v175 uploaded IEQAS badge image beside university name */
.uni-detail-name-v99,
.uni-name-accent-v93 {
    display: flex !important;
    align-items: center !important;
    gap: 14px !important;
    flex-wrap: wrap !important;
}
.ieqas-uploaded-badge-wrap-v175 {
    display: inline-flex !important;
    align-items: center !important;
    justify-content: center !important;
    width: 90px !important;
    height: 90px !important;
    min-width: 90px !important;
    max-width: 90px !important;
    max-height: 90px !important;
    background: transparent !important;
    vertical-align: middle !important;
    overflow: visible !important;
}
.ieqas-uploaded-badge-img-v175 {
    width: 90px !important;
    height: 90px !important;
    max-width: 90px !important;
    max-height: 90px !important;
    object-fit: contain !important;
    background: transparent !important;
    border: none !important;
    box-shadow: 0 6px 16px rgba(16, 24, 40, 0.10) !important;
    border-radius: 50% !important;
    display: block !important;
}
/* hide all previous generated/fake IEQAS badge versions */
.ieqas-mini-seal-v174,
.ieqas-mini-ring-text-v174,
.ieqas-mini-inner-v174,
.ieqas-name-badge-v169,
.ieqas-name-badge-v170,
.ieqas-mini-badge-v173,
.ieqas-component-wrap,
.ieqas-badge-v168,
.ieqas-badge-large-v168,
.ieqas-badge-compact-v168 {
    display: none !important;
}


/* v176 uploaded IEQAS badge fix: use saved transparent PNG image */
.ieqas-uploaded-badge-wrap-v175 {
    display: inline-flex !important;
    align-items: center !important;
    justify-content: center !important;
    width: 104px !important;
    height: 104px !important;
    min-width: 104px !important;
    max-width: 104px !important;
    max-height: 104px !important;
    background: transparent !important;
    vertical-align: middle !important;
    overflow: visible !important;
}
.ieqas-uploaded-badge-img-v175 {
    width: 104px !important;
    height: 104px !important;
    max-width: 104px !important;
    max-height: 104px !important;
    object-fit: contain !important;
    background: transparent !important;
    border: none !important;
    box-shadow: 0 8px 18px rgba(16, 24, 40, 0.10) !important;
    border-radius: 0 !important;
    display: block !important;
}


/* v177 force-show uploaded IEQAS badge beside university name */
.uni-detail-name-v99,
.uni-name-accent-v93 {
    display: flex !important;
    align-items: center !important;
    gap: 16px !important;
    flex-wrap: wrap !important;
}
.ieqas-uploaded-badge-wrap-v177 {
    display: inline-flex !important;
    align-items: center !important;
    justify-content: center !important;
    width: 112px !important;
    height: 112px !important;
    min-width: 112px !important;
    max-width: 112px !important;
    max-height: 112px !important;
    background: transparent !important;
    vertical-align: middle !important;
    overflow: visible !important;
    margin-left: 4px !important;
}
.ieqas-uploaded-badge-img-v177 {
    width: 112px !important;
    height: 112px !important;
    max-width: 112px !important;
    max-height: 112px !important;
    object-fit: contain !important;
    background: transparent !important;
    border: none !important;
    box-shadow: 0 8px 18px rgba(16, 24, 40, 0.12) !important;
    border-radius: 0 !important;
    display: block !important;
}
/* keep older uploaded badge visible if old markup remains */
.ieqas-uploaded-badge-wrap-v175,
.ieqas-uploaded-badge-img-v175 {
    display: inline-flex !important;
}


/* v178 show uploaded IEQAS badge beside university name on program detail page too */
.program-detail-title-area-v178 .program-detail-uni-name-v178 {
    display: flex !important;
    align-items: center !important;
    gap: 14px !important;
    flex-wrap: wrap !important;
}
.ieqas-uploaded-badge-wrap-v178 {
    display: inline-flex !important;
    align-items: center !important;
    justify-content: center !important;
    width: 96px !important;
    height: 96px !important;
    min-width: 96px !important;
    max-width: 96px !important;
    max-height: 96px !important;
    background: transparent !important;
    vertical-align: middle !important;
    overflow: visible !important;
    margin-left: 8px !important;
}
.ieqas-uploaded-badge-img-v178 {
    width: 96px !important;
    height: 96px !important;
    max-width: 96px !important;
    max-height: 96px !important;
    object-fit: contain !important;
    background: transparent !important;
    border: none !important;
    box-shadow: 0 8px 18px rgba(16, 24, 40, 0.12) !important;
    border-radius: 0 !important;
    display: block !important;
}
.ieqas-uploaded-badge-wrap-v177,
.ieqas-uploaded-badge-img-v177,
.ieqas-uploaded-badge-wrap-v175,
.ieqas-uploaded-badge-img-v175 {
    display: none !important;
}


/* v179 IEQAS badge from CSV data URI */
.uni-detail-name-v99,
.uni-name-accent-v93,
.program-detail-title-area-v178 .program-detail-uni-name-v178 {
    display: flex !important;
    align-items: center !important;
    gap: 16px !important;
    flex-wrap: wrap !important;
}
.ieqas-uploaded-badge-wrap-v179 {
    display: inline-flex !important;
    align-items: center !important;
    justify-content: center !important;
    width: 104px !important;
    height: 104px !important;
    min-width: 104px !important;
    max-width: 104px !important;
    max-height: 104px !important;
    background: transparent !important;
    vertical-align: middle !important;
    overflow: visible !important;
    margin-left: 8px !important;
}
.ieqas-uploaded-badge-img-v179 {
    width: 104px !important;
    height: 104px !important;
    max-width: 104px !important;
    max-height: 104px !important;
    object-fit: contain !important;
    background: transparent !important;
    border: none !important;
    border-radius: 0 !important;
    box-shadow: 0 8px 18px rgba(16, 24, 40, 0.10) !important;
    display: block !important;
}
.ieqas-uploaded-badge-wrap-v178,
.ieqas-uploaded-badge-wrap-v177,
.ieqas-uploaded-badge-wrap-v175,
.ieqas-uploaded-badge-img-v178,
.ieqas-uploaded-badge-img-v177,
.ieqas-uploaded-badge-img-v175 {
    display: none !important;
}


/* v180 uploaded IEQAS badge appears immediately beside university name */
.uni-detail-name-v99,
.uni-name-accent-v93,
.program-detail-title-area-v178 .program-detail-uni-name-v178 {
    display: flex !important;
    align-items: center !important;
    gap: 16px !important;
    flex-wrap: wrap !important;
}
.ieqas-uploaded-badge-wrap-v180 {
    display: inline-flex !important;
    align-items: center !important;
    justify-content: center !important;
    width: 108px !important;
    height: 108px !important;
    min-width: 108px !important;
    max-width: 108px !important;
    max-height: 108px !important;
    background: transparent !important;
    vertical-align: middle !important;
    overflow: visible !important;
    margin-left: 8px !important;
}
.ieqas-uploaded-badge-img-v180 {
    width: 108px !important;
    height: 108px !important;
    max-width: 108px !important;
    max-height: 108px !important;
    object-fit: contain !important;
    background: transparent !important;
    border: none !important;
    border-radius: 0 !important;
    box-shadow: 0 8px 18px rgba(16, 24, 40, 0.10) !important;
    display: block !important;
}
.ieqas-uploaded-badge-wrap-v179,
.ieqas-uploaded-badge-wrap-v178,
.ieqas-uploaded-badge-wrap-v177,
.ieqas-uploaded-badge-wrap-v175,
.ieqas-uploaded-badge-img-v179,
.ieqas-uploaded-badge-img-v178,
.ieqas-uploaded-badge-img-v177,
.ieqas-uploaded-badge-img-v175 {
    display: none !important;
}


/* v181 IEQAS badge display from persistent JSON DB */
.uni-detail-name-v99,
.uni-name-accent-v93,
.program-detail-title-area-v178 .program-detail-uni-name-v178 {
    display: flex !important;
    align-items: center !important;
    gap: 16px !important;
    flex-wrap: wrap !important;
}
.ieqas-uploaded-badge-wrap-v181 {
    display: inline-flex !important;
    align-items: center !important;
    justify-content: center !important;
    width: 108px !important;
    height: 108px !important;
    min-width: 108px !important;
    max-width: 108px !important;
    max-height: 108px !important;
    background: transparent !important;
    vertical-align: middle !important;
    overflow: visible !important;
    margin-left: 8px !important;
}
.ieqas-uploaded-badge-img-v181 {
    width: 108px !important;
    height: 108px !important;
    max-width: 108px !important;
    max-height: 108px !important;
    object-fit: contain !important;
    background: transparent !important;
    border: none !important;
    border-radius: 0 !important;
    box-shadow: 0 8px 18px rgba(16, 24, 40, 0.10) !important;
    display: block !important;
}
.ieqas-uploaded-badge-wrap-v180,
.ieqas-uploaded-badge-wrap-v179,
.ieqas-uploaded-badge-wrap-v178,
.ieqas-uploaded-badge-wrap-v177,
.ieqas-uploaded-badge-wrap-v175,
.ieqas-uploaded-badge-img-v180,
.ieqas-uploaded-badge-img-v179,
.ieqas-uploaded-badge-img-v178,
.ieqas-uploaded-badge-img-v177,
.ieqas-uploaded-badge-img-v175 {
    display: none !important;
}


/* v182 direct fixed IEQAS badge image */
.uni-detail-name-v99,
.uni-name-accent-v93,
.program-detail-title-area-v178 .program-detail-uni-name-v178 {
    display: flex !important;
    align-items: center !important;
    gap: 16px !important;
    flex-wrap: wrap !important;
}
.ieqas-direct-badge-wrap-v182 {
    display: inline-flex !important;
    align-items: center !important;
    justify-content: center !important;
    width: 108px !important;
    height: 108px !important;
    min-width: 108px !important;
    max-width: 108px !important;
    max-height: 108px !important;
    background: transparent !important;
    vertical-align: middle !important;
    overflow: visible !important;
    margin-left: 8px !important;
}
.ieqas-direct-badge-img-v182 {
    width: 108px !important;
    height: 108px !important;
    max-width: 108px !important;
    max-height: 108px !important;
    object-fit: contain !important;
    background: transparent !important;
    border: none !important;
    border-radius: 0 !important;
    box-shadow: 0 8px 18px rgba(16, 24, 40, 0.10) !important;
    display: block !important;
}
.ieqas-uploaded-badge-wrap-v181,
.ieqas-uploaded-badge-wrap-v180,
.ieqas-uploaded-badge-wrap-v179,
.ieqas-uploaded-badge-wrap-v178,
.ieqas-uploaded-badge-wrap-v177,
.ieqas-uploaded-badge-wrap-v175,
.ieqas-uploaded-badge-img-v181,
.ieqas-uploaded-badge-img-v180,
.ieqas-uploaded-badge-img-v179,
.ieqas-uploaded-badge-img-v178,
.ieqas-uploaded-badge-img-v177,
.ieqas-uploaded-badge-img-v175 {
    display: none !important;
}


/* v185 clean circular IEQAS badge: no white rectangle, no cropped text */
.ieqas-direct-badge-wrap-v182 {
    display: inline-flex !important;
    align-items: center !important;
    justify-content: center !important;
    width: 92px !important;
    height: 92px !important;
    min-width: 92px !important;
    max-width: 92px !important;
    max-height: 92px !important;
    background: transparent !important;
    box-shadow: none !important;
    border: none !important;
    overflow: visible !important;
    margin-left: 8px !important;
    vertical-align: middle !important;
}
.ieqas-direct-badge-img-v182 {
    width: 92px !important;
    height: 92px !important;
    max-width: 92px !important;
    max-height: 92px !important;
    object-fit: contain !important;
    background: transparent !important;
    border: none !important;
    border-radius: 0 !important;
    box-shadow: none !important;
    display: block !important;
}
.uni-detail-name-v99,
.uni-name-accent-v93,
.program-detail-title-area-v178 .program-detail-uni-name-v178 {
    display: flex !important;
    align-items: center !important;
    gap: 14px !important;
    flex-wrap: wrap !important;
}

</style>
""", unsafe_allow_html=True)

def set_page(p):
    st.session_state.page = p
    st.rerun()










def browser_login_nav_sync_v163():
    """
    v163: Browser-side login persistence for the public top navigation.
    Streamlit session_state can reset on public pages; this keeps the top-right nav
    showing the logged-in user using localStorage and also restores ?auth= in the URL.
    """
    try:
        token = st.session_state.get("auth_token", "") or current_auth_token_v162()
    except Exception:
        token = st.session_state.get("auth_token", "") or ""
    token = str(token or "").strip()

    role = str(st.session_state.get("role", "") or "").strip().lower()
    display_name = ""
    if st.session_state.get("logged_in") or token:
        if role in ["agency_staff", "staff"]:
            display_name = st.session_state.get("full_name", "") or st.session_state.get("username", "") or "Staff"
        elif role == "admin":
            display_name = st.session_state.get("full_name", "") or st.session_state.get("username", "") or "Admin"
        else:
            display_name = st.session_state.get("agency_name", "") or st.session_state.get("full_name", "") or st.session_state.get("username", "") or "Partner"

    # Escape for JS string safely.
    import json as _json_v163
    token_js = _json_v163.dumps(token)
    display_js = _json_v163.dumps(str(display_name or ""))
    role_js = _json_v163.dumps(role)

    components.html(f"""
    <script>
    (function() {{
      const incomingToken = {token_js};
      const incomingDisplay = {display_js};
      const incomingRole = {role_js};

      if (incomingToken) {{
        localStorage.setItem("pp_auth_token_v163", incomingToken);
        localStorage.setItem("pp_user_display_v163", incomingDisplay || "Partner");
        localStorage.setItem("pp_user_role_v163", incomingRole || "partner");
      }}

      const token = localStorage.getItem("pp_auth_token_v163") || "";
      const display = localStorage.getItem("pp_user_display_v163") || (token.includes(":") ? token.split(":")[0] : "Partner");

      function replaceNav() {{
        if (!token) return;
        const navRight = window.parent.document.querySelector(".nav-right-v70");
        if (!navRight) return;
        navRight.innerHTML = `
          <div class="nav-user-box-v161">
            <span class="nav-user-name-v161">${{display}}</span>
            <a class="nav-logout-v161" href="?nav=logout" onclick="localStorage.removeItem('pp_auth_token_v163');localStorage.removeItem('pp_user_display_v163');localStorage.removeItem('pp_user_role_v163');">Logout</a>
          </div>
        `;
      }}

      replaceNav();
      setTimeout(replaceNav, 200);
      setTimeout(replaceNav, 800);

      // If URL lost auth, put it back once so Streamlit can restore the session server-side too.
      try {{
        const url = new URL(window.parent.location.href);
        if (token && !url.searchParams.get("auth")) {{
          url.searchParams.set("auth", token);
          window.parent.history.replaceState(null, "", url.toString());
        }}
      }} catch(e) {{}}
    }})();
    </script>
    """, height=0)

def header():
    st.markdown("""<base target="_self"><!-- v185 base target self -->""", unsafe_allow_html=True)
    # v161: restore login before drawing top navigation so Login/Sign Up disappears for logged-in users.
    try:
        restore_login_from_query_v60()
    except Exception:
        pass

    current = st.session_state.get("page", "Home")
    pending_token = _current_pending_token_v76()
    pending_suffix = f"&pending={pending_token}" if pending_token else ""

    def active_cls(target):
        return " active" if current == target else ""

    def nav_href(nav_key):
        auth_suffix = auth_query_suffix_v104("&")
        return f"?nav={nav_key}{pending_suffix}{auth_suffix}"

    # v162: restore again immediately before drawing top nav.
    try:
        restore_login_from_any_auth_v162()
    except Exception:
        pass

    logged_in_v161 = bool(
        st.session_state.get("logged_in")
        or (st.session_state.get("username") and st.session_state.get("role"))
        or current_auth_token_v162()
    )
    role_v161 = str(st.session_state.get("role", "")).strip().lower()
    if logged_in_v161:
        token_name_v162 = ""
        token_v162 = current_auth_token_v162()
        if token_v162 and ":" in token_v162:
            token_name_v162 = token_v162.split(":", 1)[0]
        if role_v161 in ["agency_staff", "staff"]:
            display_name_v161 = st.session_state.get("full_name", "") or st.session_state.get("username", "") or token_name_v162 or "Staff"
        elif role_v161 == "admin":
            display_name_v161 = st.session_state.get("full_name", "") or st.session_state.get("username", "") or token_name_v162 or "Admin"
        else:
            display_name_v161 = st.session_state.get("agency_name", "") or st.session_state.get("full_name", "") or st.session_state.get("username", "") or token_name_v162 or "Partner"
        user_actions_v161 = (
            '<div class="nav-user-box-v161">'
            f'<span class="nav-user-name-v161">{_safe_html_v62(display_name_v161)}</span>'
            '<a class="nav-logout-v161" href="?nav=logout">Logout</a>'
            '</div>'
        )
    else:
        user_actions_v161 = (
            f'<a class="nav-login-v70" href="{nav_href("login")}">Login</a>'
            f'<a class="nav-signup-v70" href="{nav_href("signup")}">👥&nbsp;&nbsp;Partner Sign Up</a>'
        )

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
        {user_actions_v161}
      </div>
    </div>
    """
    st.markdown(nav_html, unsafe_allow_html=True)
    # v163: client-side backup so logged-in users do not see Login/Partner Sign Up on public pages.
    try:
        browser_login_nav_sync_v163()
    except Exception:
        pass

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
    from PIL import Image, ImageDraw, ImageEnhance
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





def ieqas_badge_db_path_v181():
    """Persistent small JSON DB for IEQAS badge data, independent from university CSV column issues."""
    return BASE / "ieqas_badges.json"


def load_ieqas_badge_db_v181():
    path = ieqas_badge_db_path_v181()
    try:
        if path.exists():
            data = json.loads(path.read_text(encoding="utf-8"))
            return data if isinstance(data, dict) else {}
    except Exception:
        return {}
    return {}


def save_ieqas_badge_db_v181(data):
    path = ieqas_badge_db_path_v181()
    try:
        path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    except Exception:
        pass


def save_ieqas_badge_for_university_v181(university_name, uploaded_file):
    """
    Save uploaded IEQAS image in a persistent JSON DB and session state.
    This guarantees it appears immediately after upload and after rerun.
    """
    if uploaded_file is None:
        return ""
    slug = safe_slug_v49(university_name or "university")
    data_uri = save_uploaded_ieqas_badge_data_v179(uploaded_file)
    if not data_uri:
        return ""

    db = load_ieqas_badge_db_v181()
    db[slug] = {
        "university": str(university_name or ""),
        "data_uri": data_uri,
    }
    save_ieqas_badge_db_v181(db)

    st.session_state.setdefault("ieqas_badge_preview_data_v180", {})[slug] = data_uri
    return data_uri


def get_ieqas_badge_data_for_university_v181(university_name, row_data_uri=""):
    """Read IEQAS badge data from session, CSV row, or JSON DB."""
    slug = safe_slug_v49(university_name or "university")
    session_map = st.session_state.get("ieqas_badge_preview_data_v180", {})
    if session_map.get(slug, "").startswith("data:image"):
        return session_map.get(slug, "")

    if display_clean_v50(row_data_uri).startswith("data:image"):
        return display_clean_v50(row_data_uri)

    db = load_ieqas_badge_db_v181()
    item = db.get(slug, {})
    if isinstance(item, dict) and str(item.get("data_uri", "")).startswith("data:image"):
        return item.get("data_uri", "")

    return ""


def save_uploaded_ieqas_badge_data_v179(uploaded_file):
    """
    Save the uploaded IEQAS badge inside the CSV as a data URI.
    This avoids broken local file paths on Streamlit/GitHub redeploys.
    """
    if uploaded_file is None:
        return ""
    try:
        try:
            uploaded_file.seek(0)
        except Exception:
            pass

        img = Image.open(uploaded_file).convert("RGBA")

        # Make square canvas without cropping.
        w, h = img.size
        side = max(w, h)
        canvas = Image.new("RGBA", (side, side), (255, 255, 255, 0))
        canvas.paste(img, ((side - w) // 2, (side - h) // 2), img)

        # Transparent outside circular area. Keeps official badge content inside.
        mask = Image.new("L", (side, side), 0)
        draw = ImageDraw.Draw(mask)
        pad = max(2, int(side * 0.01))
        draw.ellipse((pad, pad, side - pad, side - pad), fill=255)
        canvas.putalpha(mask)

        # Keep CSV size reasonable.
        canvas.thumbnail((520, 520), Image.Resampling.LANCZOS)

        from io import BytesIO
        buffer = BytesIO()
        canvas.save(buffer, format="PNG", optimize=True)
        encoded = base64.b64encode(buffer.getvalue()).decode("utf-8")

        try:
            uploaded_file.seek(0)
        except Exception:
            pass

        return f"data:image/png;base64,{encoded}"
    except Exception:
        return ""



def save_uploaded_ieqas_badge_v175(uploaded_file, university_name="university"):
    """
    Save optional IEQAS badge image uploaded by super admin.

    v176 fix:
    - Do not use undefined UPLOAD_DIR.
    - Save into assets/ieqas_badges so b64() can read it later.
    - Convert to PNG.
    - Apply a circular alpha mask so the outside background becomes transparent.
    """
    if uploaded_file is None:
        return ""
    try:
        slug = safe_slug_v49(university_name or "university")
        out_dir = BASE / "assets" / "ieqas_badges"
        out_dir.mkdir(parents=True, exist_ok=True)
        out_path = out_dir / f"{slug}_ieqas_badge.png"

        img = Image.open(uploaded_file).convert("RGBA")

        # Make a square canvas using the longer side, centered, without cropping the badge.
        w, h = img.size
        side = max(w, h)
        canvas = Image.new("RGBA", (side, side), (255, 255, 255, 0))
        canvas.paste(img, ((side - w) // 2, (side - h) // 2), img)

        # Transparent outside circular badge area; keep inner white badge content.
        mask = Image.new("L", (side, side), 0)
        draw = ImageDraw.Draw(mask)
        pad = max(2, int(side * 0.015))
        draw.ellipse((pad, pad, side - pad, side - pad), fill=255)
        canvas.putalpha(mask)

        canvas.save(out_path, "PNG", optimize=True)
        return f"assets/ieqas_badges/{slug}_ieqas_badge.png"
    except Exception:
        return ""



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

                location_html = f"""
                  <div class="uni-meta-item-v166">
                    <span class="uni-meta-icon-v166 icon-location"></span>
                    <span class="uni-meta-text-v166">{location_text}</span>
                  </div>
                """ if location_text else ""
                students_html = f"""
                  <div class="uni-meta-item-v166">
                    <span class="uni-meta-icon-v166 icon-students"></span>
                    <span class="uni-meta-text-v166">{students_text}</span>
                  </div>
                """ if students_text else ""
                intl_html = f"""
                  <div class="uni-meta-item-v166">
                    <span class="uni-meta-icon-v166 icon-global"></span>
                    <span class="uni-meta-text-v166">{intl_text}</span>
                  </div>
                """ if intl_text else ""

                st.markdown(f"""
                <div class="card uni-card-v53">
                  {image_html}
                  <h3>{display_value_v53(u.get('University',''))}</h3>
                  <div class="uni-meta-list-v166">
                    {location_html}
                    {students_html}
                    {intl_html}
                  </div>
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
          <h3>⭐ Official Representative Agency</h3><p>Only approved official representative agencies receive the verified badge. Partner agencies can approve only their own staff accounts.</p>
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



def capture_application_return_context_v155(university="", program_slug="", application_type=""):
    """Save where the applicant was when they were asked to login."""
    if university:
        st.session_state.return_apply_uni_v155 = str(university)
    if program_slug:
        st.session_state.return_apply_program_v155 = str(program_slug)
    if application_type:
        st.session_state.return_apply_type_v155 = str(application_type)
    st.session_state.return_after_login_v155 = "application"


def get_application_return_context_v155():
    """Read return-to-application context from session or query params."""
    try:
        apply_return = st.query_params.get("apply_return", "")
        q_uni = st.query_params.get("uni", "")
        q_program = st.query_params.get("programdetail", "")
        q_type = st.query_params.get("apptype", "")
    except Exception:
        apply_return = q_uni = q_program = q_type = ""

    if isinstance(apply_return, list):
        apply_return = apply_return[0] if apply_return else ""
    if isinstance(q_uni, list):
        q_uni = q_uni[0] if q_uni else ""
    if isinstance(q_program, list):
        q_program = q_program[0] if q_program else ""
    if isinstance(q_type, list):
        q_type = q_type[0] if q_type else ""

    from urllib.parse import unquote_plus
    uni = unquote_plus(str(q_uni or st.session_state.get("return_apply_uni_v155", "") or ""))
    program = unquote_plus(str(q_program or st.session_state.get("return_apply_program_v155", "") or ""))
    app_type = unquote_plus(str(q_type or st.session_state.get("return_apply_type_v155", "") or ""))

    should_return = str(apply_return).strip() == "1" or st.session_state.get("return_after_login_v155") == "application"
    return should_return, uni, program, app_type


def go_to_application_return_after_login_v155(default_page):
    """After approved login, return to the selected application page if login came from Apply page."""
    should_return, uni, program, app_type = get_application_return_context_v155()
    if should_return and uni and program:
        st.session_state.page = "Universities"
        st.session_state.selected_uni_v62 = uni
        st.session_state.selected_program_v109 = program
        st.session_state.application_type_v109 = app_type
        st.session_state.application_page_open_v113 = bool(app_type)
        # v158: remember that this application page was reached after approved login.
        st.session_state.application_login_verified_v158 = True
        st.session_state.apply_access_granted_v158 = True
        st.session_state.application_step_v114 = 1
        st.session_state.application_step1_data_v114 = {}
        st.session_state.application_submitted_data_v118 = {}
        st.session_state.current_application_id_v116 = ""
        # Keep return context until the application page is opened successfully.
        # It will not block application access and avoids returning to Dashboard too early.
        try:
            for q in ["apply_return", "apptype", "nav"]:
                if q in st.query_params:
                    del st.query_params[q]
        except Exception:
            pass
        st.rerun()

    set_page(default_page)


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
                elif str(user.get("status", "")).strip().lower() not in ["approved", "active"]:
                    set_pending_session_v75(user)
                    set_page("Pending")
                else:
                    for k in ["pending_username","pending_full_name","pending_agency_name","pending_email","pending_role","pending_account_type","pending_approval_by"]:
                        st.session_state.pop(k, None)
                    _set_login_session_from_user_v60(user)
                    st.session_state.apply_access_granted_v158 = True
                    try:
                        st.query_params["auth"] = st.session_state.get("auth_token", "") or _make_auth_token_v60(user)
                    except Exception:
                        pass
                    go_to_application_return_after_login_v155("Admin Dashboard" if user["role"] == "admin" else "Dashboard")
        if st.button("Create New Partner Account", key="go_signup_from_login", use_container_width=True):
            set_page("Partner Sign Up")
        st.markdown('</div></div>', unsafe_allow_html=True)
    footer()



def dash_shell(items):
    try:
        browser_login_nav_sync_v163()
    except Exception:
        pass
    current_page_v96 = str(st.session_state.get("page", ""))
    role_v96 = str(st.session_state.get("role", ""))

    def _dash_icon_v96(item):
        # v133: professional inline SVG icons instead of emoji-style icons.
        svg_map = {
            "Admin Dashboard": '<svg viewBox="0 0 24 24"><path d="M4 5h16M4 12h16M4 19h16"/></svg>',
            "Dashboard": '<svg viewBox="0 0 24 24"><path d="M4 13h6V5H4v8Zm10 6h6V5h-6v14ZM4 19h6v-4H4v4Z"/></svg>',
            "Partner Management": '<svg viewBox="0 0 24 24"><path d="M16 11a4 4 0 1 0-8 0"/><path d="M3 20a7 7 0 0 1 14 0"/><path d="M17 8a3 3 0 0 1 3 3"/><path d="M18.5 15.5A5.5 5.5 0 0 1 22 20"/></svg>',
            "Universities": '<svg viewBox="0 0 24 24"><path d="M3 21h18"/><path d="M5 21V9l7-4 7 4v12"/><path d="M9 21v-7h6v7"/><path d="M10 10h4"/></svg>',
            "Eligibility Rules": '<svg viewBox="0 0 24 24"><path d="M12 3 5 6v6c0 4.5 3 7.5 7 9 4-1.5 7-4.5 7-9V6l-7-3Z"/><path d="m9 12 2 2 4-5"/></svg>',
            "Eligibility Check": '<svg viewBox="0 0 24 24"><path d="M12 3 5 6v6c0 4.5 3 7.5 7 9 4-1.5 7-4.5 7-9V6l-7-3Z"/><path d="m9 12 2 2 4-5"/></svg>',
            "Tuition Rules": '<svg viewBox="0 0 24 24"><path d="M12 3v18"/><path d="M17 7.5c-.9-1.1-2.4-1.8-4.1-1.8-2.3 0-4.1 1.1-4.1 2.8 0 4.3 8.4 1.8 8.4 6.2 0 1.8-1.8 3-4.3 3-1.9 0-3.6-.8-4.6-2.1"/></svg>',
            "Tuition & Scholarship": '<svg viewBox="0 0 24 24"><path d="M12 3v18"/><path d="M17 7.5c-.9-1.1-2.4-1.8-4.1-1.8-2.3 0-4.1 1.1-4.1 2.8 0 4.3 8.4 1.8 8.4 6.2 0 1.8-1.8 3-4.3 3-1.9 0-3.6-.8-4.6-2.1"/></svg>',
            "Scholarship Rules": '<svg viewBox="0 0 24 24"><path d="M4 8 12 4l8 4-8 4-8-4Z"/><path d="M6 10v5c1.8 1.8 10.2 1.8 12 0v-5"/><path d="M20 8v6"/></svg>',
            "Contact Us": '<svg viewBox="0 0 24 24"><path d="M4 6h16v12H4z"/><path d="m4 7 8 6 8-6"/></svg>',
            "Applications": '<svg viewBox="0 0 24 24"><path d="M7 3h7l4 4v14H7z"/><path d="M14 3v5h5"/><path d="M9 13h6"/><path d="M9 17h6"/></svg>',
            "Application Samples": '<svg viewBox="0 0 24 24"><path d="M6 3h12v18H6z"/><path d="M9 7h6"/><path d="M9 11h6"/><path d="M9 15h4"/></svg>',
            "Logout": '<svg viewBox="0 0 24 24"><path d="M10 17 15 12 10 7"/><path d="M15 12H3"/><path d="M14 5h5v14h-5"/></svg>',
        }
        return svg_map.get(item, '<svg viewBox="0 0 24 24"><circle cx="12" cy="12" r="3"/></svg>')

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
        icon = _dash_icon_v96(item)
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



# v116 Ongoing Application / Application Status helpers
STUDENT_APPLICATIONS_FILE_V116 = DATA / "student_applications.csv"

APPLICATION_STATUS_STEPS_V116 = [
    "Submitted",
    "University received your application",
    "Application number issued",
    "Interview dates",
    "Interview done",
    "Interview result",
    "Issued offer letter and invoice",
    "COA issue",
    "Apply for visa",
    "Visa application number issued",
    "Visa result",
]

def application_columns_v116():
    return [
        "Application_ID", "Submitted_At", "Last_Updated", "University", "Program_Category", "Application_Type",
        "Full_Name_As_Passport", "Applicant_Name", "First_Name", "Middle_Name", "Last_Name", "Passport_Number",
        "Nationality", "Email", "Applicant_Contact", "Desired_Major", "Agency", "Submitted_By", "Status",
        "Document_Paths_JSON", "University_Received", "Application_Number", "Interview_Date", "Interview_Done",
        "Interview_Result", "Offer_Invoice_Issued", "COA_Issued", "Visa_Mode", "Visa_Application_Number", "Visa_Result"
    ]

def applications_df_v116():
    df = read_csv(STUDENT_APPLICATIONS_FILE_V116)
    df = ensure_columns_v49(df, application_columns_v116())
    return clean_df_v50(df)

def write_applications_df_v116(df):
    df = ensure_columns_v49(df, application_columns_v116())
    df.fillna("").replace(["nan", "NaN", "None", "null", "<NA>"], "").to_csv(STUDENT_APPLICATIONS_FILE_V116, index=False, encoding="utf-8-sig")

def make_application_id_v116(passport_number="", university=""):
    base = f"{passport_number}_{university}_{datetime.now().strftime('%Y%m%d%H%M%S')}"
    return safe_slug_v49(base)

def application_owner_filter_v116(df):
    if df is None or len(df) == 0:
        return pd.DataFrame()
    role = st.session_state.get("role", "")
    username = str(st.session_state.get("username", ""))
    agency = str(st.session_state.get("agency_name", ""))
    if role == "admin":
        return df.copy()
    if role in ["agency_rep", "agency_partner"]:
        return df[
            (df.get("Agency", "").astype(str).str.strip().str.lower() == agency.strip().lower())
            | (df.get("Submitted_By", "").astype(str).str.strip().str.lower() == username.strip().lower())
        ].copy()
    return df[df.get("Submitted_By", "").astype(str).str.strip().str.lower() == username.strip().lower()].copy()

def application_display_name_v116(row):
    for col in ["Full_Name_As_Passport", "Applicant_Name"]:
        val = display_clean_v50(row.get(col, ""))
        if val:
            return val
    first = display_clean_v50(row.get("First_Name", ""))
    last = display_clean_v50(row.get("Last_Name", ""))
    name = f"{first} {last}".strip()
    return name or "Unnamed Applicant"


def inferred_application_status_v119(row):
    status = display_clean_v50(row.get("Status", ""))
    doc_json = display_clean_v50(row.get("Document_Paths_JSON", ""))
    submitted_at = display_clean_v50(row.get("Submitted_At", ""))

    advanced_fields = [
        ("Visa_Result", "Visa {value}"),
        ("Interview_Result", "Interview {value}"),
        ("Visa_Application_Number", "Visa Application Number Issued"),
        ("Visa_Mode", "Visa Application Started"),
        ("COA_Issued", "COA Issued"),
        ("Offer_Invoice_Issued", "Offer Letter and Invoice Issued"),
        ("Interview_Done", "Interview Done"),
        ("Interview_Date", "Interview Date Announced"),
        ("Application_Number", "Application Number Issued"),
        ("University_Received", "University Received"),
    ]
    for key, label in advanced_fields:
        val = display_clean_v50(row.get(key, ""))
        if val:
            return label.format(value=val)

    if doc_json and doc_json not in ["{}", "[]", "nan", "None", "null"]:
        if not status or "draft" in status.lower() or "pending" in status.lower():
            return "Submitted"

    if submitted_at and (not status or "draft" in status.lower() or "pending" in status.lower()):
        return "Submitted"

    return status or "Draft"


def application_is_active_or_submitted_v128(row_or_status):
    """
    v128 fix:
    Ongoing Applications must show Check Status not only for "Submitted",
    but also for later statuses such as Interview Passed, University Received,
    Application Number Issued, Visa Issued, etc.
    Only draft / documents pending rows should show Continue / Resume.
    """
    if isinstance(row_or_status, dict):
        s = inferred_application_status_v119(row_or_status)
    else:
        s = str(row_or_status or "")
    sl = s.lower().strip()
    if not sl:
        return False
    if "draft" in sl or "documents pending" in sl or sl == "pending":
        return False
    return True


def application_sort_priority_v119(row):
    status = inferred_application_status_v119(row).lower()
    if "visa" in status or "interview" in status or "issued" in status or "received" in status:
        return 6
    if "submitted" in status:
        return 5
    if "draft" in status or "pending" in status:
        return 2
    return 3

def dedupe_application_rows_v119(df):
    if df is None or len(df) == 0:
        return df
    df = df.copy()
    df["_status_priority_v119"] = df.apply(application_sort_priority_v119, axis=1)
    df["_last_v119"] = df.get("Last_Updated", "").astype(str)
    # Group by applicant identity. This prevents an old draft card staying visible
    # after the submitted row was created with a different application id.
    group_cols = ["Passport_Number", "University", "Submitted_By"]
    for c in group_cols:
        if c not in df.columns:
            df[c] = ""
    df["_group_key_v119"] = (
        df["Passport_Number"].astype(str).str.strip().str.lower() + "|" +
        df["University"].astype(str).str.strip().str.lower() + "|" +
        df["Submitted_By"].astype(str).str.strip().str.lower()
    )
    df = df.sort_values(["_status_priority_v119", "_last_v119"], ascending=[False, False])
    df = df.drop_duplicates("_group_key_v119", keep="first")
    return df.drop(columns=[c for c in ["_status_priority_v119", "_last_v119", "_group_key_v119"] if c in df.columns])

def application_status_badge_v116(status):
    s = str(status or "").strip()
    sl = s.lower()
    if "submitted" in sl and "draft" not in sl:
        cls = "app-status-submitted-v116"
    elif "draft" in sl or "pending" in sl or "documents" in sl:
        cls = "app-status-draft-v116"
    elif "rejected" in sl or "failed" in sl:
        cls = "app-status-rejected-v116"
    elif "issued" in sl or "passed" in sl:
        cls = "app-status-issued-v116"
    else:
        cls = "app-status-neutral-v116"
    return f'<span class="app-status-badge-v116 {cls}">{_safe_html_v62(s or "Draft")}</span>'

def save_step1_draft_v116(step1, status="Draft - Documents Pending"):
    df = applications_df_v116()
    app_id = st.session_state.get("current_application_id_v116", "") or step1.get("Application_ID", "")
    if not app_id:
        app_id = make_application_id_v116(step1.get("Passport_Number", ""), step1.get("University", ""))
        st.session_state.current_application_id_v116 = app_id
    row = dict(step1)
    row.update({
        "Application_ID": app_id,
        "Last_Updated": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "Submitted_At": row.get("Submitted_At", ""),
        "Submitted_By": st.session_state.get("username", ""),
        "Agency": st.session_state.get("agency_name", ""),
        "Status": status,
    })
    if "Application_ID" in df.columns and len(df[df["Application_ID"].astype(str) == app_id]):
        mask = df["Application_ID"].astype(str) == app_id
        for k, v in row.items():
            if k not in df.columns:
                df[k] = ""
            df.loc[mask, k] = v
    else:
        df = pd.concat([df, pd.DataFrame([row])], ignore_index=True)
    write_applications_df_v116(df)
    return app_id

def update_application_submitted_v116(step1, saved_docs):
    """
    v119 robust submit update:
    - Updates the exact Application_ID when available.
    - Also updates any matching draft row by passport + university + submitted user/agency.
      This fixes cases where the session lost current_application_id_v116 during upload reruns.
    """
    df = applications_df_v116()
    df = ensure_columns_v49(df, application_columns_v116())

    app_id = (
        st.session_state.get("current_application_id_v116", "")
        or step1.get("Application_ID", "")
    )
    passport = display_clean_v50(step1.get("Passport_Number", ""))
    university = display_clean_v50(step1.get("University", ""))
    submitted_by = display_clean_v50(st.session_state.get("username", ""))
    agency = display_clean_v50(st.session_state.get("agency_name", ""))

    if not app_id:
        # Try to reuse the latest matching draft application instead of creating a new row.
        try:
            match = df[
                (df["Passport_Number"].astype(str).str.strip().str.lower() == passport.strip().lower())
                & (df["University"].astype(str).str.strip().str.lower() == university.strip().lower())
                & (
                    (df["Submitted_By"].astype(str).str.strip().str.lower() == submitted_by.strip().lower())
                    | (df["Agency"].astype(str).str.strip().str.lower() == agency.strip().lower())
                )
            ].copy()
            if len(match):
                if "Last_Updated" in match.columns:
                    match = match.sort_values("Last_Updated", ascending=False)
                app_id = display_clean_v50(match.iloc[0].get("Application_ID", ""))
        except Exception:
            pass

    if not app_id:
        app_id = make_application_id_v116(passport, university)

    st.session_state.current_application_id_v116 = app_id

    now_v119 = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    row = dict(step1)
    row.update({
        "Application_ID": app_id,
        "Submitted_At": now_v119,
        "Last_Updated": now_v119,
        "Submitted_By": submitted_by,
        "Agency": agency,
        "Status": "Submitted",
        "Document_Paths_JSON": json.dumps(saved_docs, ensure_ascii=False),
    })

    # Exact app-id match
    mask = df["Application_ID"].astype(str).str.strip() == str(app_id).strip()

    # Safety match for old/draft rows if application id changed or was blank.
    if passport and university:
        safety_mask = (
            (df["Passport_Number"].astype(str).str.strip().str.lower() == passport.strip().lower())
            & (df["University"].astype(str).str.strip().str.lower() == university.strip().lower())
            & (
                (df["Submitted_By"].astype(str).str.strip().str.lower() == submitted_by.strip().lower())
                | (df["Agency"].astype(str).str.strip().str.lower() == agency.strip().lower())
                | (df["Submitted_By"].astype(str).str.strip() == "")
            )
        )
        mask = mask | safety_mask

    if len(df) and mask.any():
        for k, v in row.items():
            if k not in df.columns:
                df[k] = ""
            df.loc[mask, k] = v
    else:
        df = pd.concat([df, pd.DataFrame([row])], ignore_index=True)

    write_applications_df_v116(df)
    return app_id

def resume_application_v116(row):
    st.session_state.current_application_id_v116 = display_clean_v50(row.get("Application_ID", ""))
    st.session_state.selected_uni_v62 = display_clean_v50(row.get("University", ""))
    program_slug = display_clean_v50(row.get("Program_Category", "undergraduate")) or "undergraduate"
    if program_slug.lower() in ["undergraduate", "graduate", "language"]:
        st.session_state.selected_program_v109 = program_slug.lower()
    else:
        st.session_state.selected_program_v109 = program_slug
    st.session_state.application_type_v109 = display_clean_v50(row.get("Application_Type", "")) or "Undergraduate New Student Application"
    st.session_state.application_step1_data_v114 = row.to_dict()
    status = display_clean_v50(row.get("Status", ""))
    st.session_state.application_step_v114 = 2 if "document" in status.lower() or "draft" in status.lower() else 1
    st.session_state.page = "Universities"
    st.rerun()

def application_stage_value_v116(row, col):
    return display_clean_v50(row.get(col, ""))



def application_step_time_v120(value):
    val = display_clean_v50(value)
    if not val:
        return "-"
    try:
        s = str(val).strip().replace("T", " ")
        for fmt in ["%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M", "%Y/%m/%d %H:%M:%S", "%Y/%m/%d %H:%M", "%Y-%m-%d", "%Y/%m/%d"]:
            try:
                dt = datetime.strptime(s, fmt)
                if fmt in ["%Y-%m-%d", "%Y/%m/%d"]:
                    return dt.strftime("%d %b %Y")
                return dt.strftime("%d %b %Y · %I:%M %p")
            except Exception:
                pass
        return s
    except Exception:
        return str(val)


def university_row_by_name_v120(name):
    try:
        df = universities()
        if len(df) == 0:
            return {}
        m = df[df.get("University", "").astype(str).str.strip().str.lower() == str(name).strip().lower()]
        if len(m):
            return m.iloc[0].to_dict()
    except Exception:
        pass
    return {}


def status_chip_text_v120(row):
    status = str(inferred_application_status_v119(row)).strip()
    sl = status.lower()
    visa_result = application_stage_value_v116(row, "Visa_Result").lower()
    interview_result = application_stage_value_v116(row, "Interview_Result").lower()
    if "issued" in visa_result or "approved" in visa_result:
        return ("Visa Issued", "success")
    if "reject" in visa_result or "denied" in visa_result:
        return ("Visa Rejected", "danger")
    if "pass" in interview_result:
        return ("Interview Passed", "success")
    if "fail" in interview_result:
        return ("Interview Failed", "danger")
    if "submitted" in sl:
        return ("In Progress", "progress")
    if "draft" in sl or "pending" in sl:
        return ("Draft", "draft")
    return (status or "In Progress", "neutral")


def application_timeline_steps_v120(row):
    program_category = str(row.get("Program_Category", "") or "").lower()
    status = str(inferred_application_status_v119(row)).lower()
    interview_result = application_stage_value_v116(row, "Interview_Result").lower()
    visa_result = application_stage_value_v116(row, "Visa_Result").lower()

    steps = []
    steps.append({
        "title": "Application Submitted",
        "desc": "Your application has been submitted successfully.",
        "value": application_stage_value_v116(row, "Submitted_At"),
        "state": "completed" if ("submitted" in status or application_stage_value_v116(row, "Submitted_At")) else "current",
    })
    steps.append({
        "title": "University Received Your Application",
        "desc": f"{display_clean_v50(row.get('University','University'))} has received your application.",
        "value": application_stage_value_v116(row, "University_Received"),
        "state": "completed" if application_stage_value_v116(row, "University_Received") else "pending",
    })
    steps.append({
        "title": "Application Number Issued",
        "desc": "Your application number has been generated.",
        "value": application_stage_value_v116(row, "Application_Number"),
        "state": "completed" if application_stage_value_v116(row, "Application_Number") else "pending",
    })
    steps.append({
        "title": "Interview Date Announced",
        "desc": "Your interview date will be announced soon.",
        "value": application_stage_value_v116(row, "Interview_Date"),
        "state": "completed" if application_stage_value_v116(row, "Interview_Date") else "pending",
    })
    steps.append({
        "title": "Interview Completed",
        "desc": "Complete your interview as per the schedule.",
        "value": application_stage_value_v116(row, "Interview_Done"),
        "state": "completed" if application_stage_value_v116(row, "Interview_Done") else "pending",
    })

    if "pass" in interview_result:
        steps.append({
            "title": "Interview Result Released",
            "desc": "Congratulations. You passed the interview.",
            "value": "Passed",
            "state": "passed",
        })
    elif "fail" in interview_result:
        steps.append({
            "title": "Interview Result Released",
            "desc": "Unfortunately, the interview result is failed.",
            "value": "Failed",
            "state": "failed",
        })
    else:
        steps.append({
            "title": "Interview Result Released",
            "desc": "The interview result will be released.",
            "value": "-",
            "state": "pending",
        })

    steps.append({
        "title": "Offer Letter and Invoice Issued",
        "desc": "Offer letter and invoice will be issued after approval.",
        "value": application_stage_value_v116(row, "Offer_Invoice_Issued"),
        "state": "completed" if application_stage_value_v116(row, "Offer_Invoice_Issued") else "pending",
    })
    steps.append({
        "title": "COA Issued",
        "desc": "Certificate of Admission will be issued.",
        "value": application_stage_value_v116(row, "COA_Issued"),
        "state": "completed" if application_stage_value_v116(row, "COA_Issued") else "pending",
    })

    visa_label = "Apply for Visa Issuance Number" if "language" in program_category else "Apply for Visa"
    visa_desc = "Apply via embassy or Korean immigration e-visa." if "language" not in program_category else "Apply for visa issuance number for language program."
    steps.append({
        "title": visa_label,
        "desc": visa_desc,
        "value": application_stage_value_v116(row, "Visa_Mode"),
        "state": "completed" if application_stage_value_v116(row, "Visa_Mode") else "pending",
    })
    steps.append({
        "title": "Visa Application Number Issued",
        "desc": "Your visa application number has been issued.",
        "value": application_stage_value_v116(row, "Visa_Application_Number"),
        "state": "completed" if application_stage_value_v116(row, "Visa_Application_Number") else "pending",
    })

    if "issued" in visa_result or "approved" in visa_result:
        steps.append({
            "title": "Visa Result Released",
            "desc": "Congratulations. Your visa has been issued.",
            "value": "Issued",
            "state": "visa-issued",
        })
    elif "reject" in visa_result or "denied" in visa_result:
        steps.append({
            "title": "Visa Result Released",
            "desc": "Your visa has been rejected.",
            "value": "Rejected",
            "state": "visa-rejected",
        })
    else:
        steps.append({
            "title": "Visa Result Released",
            "desc": "The visa result will be released.",
            "value": "-",
            "state": "pending",
        })

    has_current = any(s["state"] == "current" for s in steps)
    blocking_state = any(s["state"] in ["failed", "visa-issued", "visa-rejected", "passed"] for s in steps)
    if not has_current and not blocking_state:
        for s in steps:
            if s["state"] == "pending":
                s["state"] = "current"
                break
    return steps


def application_step_date_time_v121(value):
    val = display_clean_v50(value)
    if not val:
        return ("-", "")
    try:
        s = str(val).strip().replace("T", " ")
        for fmt in ["%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M", "%Y/%m/%d %H:%M:%S", "%Y/%m/%d %H:%M", "%Y-%m-%d", "%Y/%m/%d"]:
            try:
                dt = datetime.strptime(s, fmt)
                if fmt in ["%Y-%m-%d", "%Y/%m/%d"]:
                    return (dt.strftime("%d %b %Y"), "")
                return (dt.strftime("%d %b %Y"), dt.strftime("%I:%M %p"))
            except Exception:
                pass
        # If the value is not a date, show it as the date/value line.
        return (s, "")
    except Exception:
        return (str(val), "")


def timeline_status_icon_v121(state, index):
    if state in ["completed", "passed", "visa-issued"]:
        return "✓"
    if state in ["failed", "visa-rejected"]:
        return "✕"
    if state == "current":
        return "◷"
    if index in [4, 5]:
        return "▣"
    return "□"

def render_application_status_timeline_v116(row):
    """v122: clean one-line HTML timeline so Streamlit does not render raw HTML/code blocks."""
    uni_name = display_clean_v50(row.get("University", ""))
    uni_row = university_row_by_name_v120(uni_name)
    logo_path = display_clean_v50(uni_row.get("University_Logo", "")) if uni_row else ""
    logo_b64 = b64(logo_path) if logo_path else ""
    if logo_b64:
        logo_html = f'<img src="data:image/png;base64,{logo_b64}" alt="{_safe_html_v62(uni_name)} logo">'
    else:
        initials = "".join([x[:1].upper() for x in str(uni_name or "U").split()[:2]]) or "U"
        logo_html = f'<div class="status-logo-fallback-v122">{_safe_html_v62(initials)}</div>'

    applicant = application_display_name_v116(row)
    program_name = display_clean_v50(row.get("Desired_Major", "")) or display_clean_v50(row.get("Major", "")) or "Program not selected"
    chip_text, chip_cls = status_chip_text_v120(row)
    steps = application_timeline_steps_v120(row)
    css = '<style>.status-page-v122{max-width:980px;margin:0 auto 32px auto;padding:8px 0;font-family:inherit}.status-title-v122{text-align:center;font-size:34px;font-weight:950;color:#101828;margin:8px 0 22px}.status-summary-v122{background:#fff;border:1px solid #e6eaf2;border-radius:26px;padding:22px 24px;box-shadow:0 12px 32px rgba(16,24,40,.08);margin-bottom:34px}.status-summary-grid-v122{display:grid;grid-template-columns:126px 1fr;gap:26px;align-items:center}.status-logo-v122{width:118px;height:118px;border-radius:26px;background:#f8fafc;border:1px solid #e4eaf3;display:flex;align-items:center;justify-content:center;overflow:hidden;box-shadow:0 8px 20px rgba(16,24,40,.04)}.status-logo-v122 img{max-width:98px;max-height:98px;object-fit:contain}.status-logo-fallback-v122{font-size:28px;font-weight:950;color:#005BDB}.status-table-v122{display:grid;grid-template-columns:160px 1fr}.status-label-v122,.status-value-v122{padding:13px 0;border-bottom:1px solid #edf2f7;font-size:17px}.status-label-v122{color:#667085;font-weight:750}.status-value-v122{color:#0f172a;font-weight:900}.status-chip-v122{display:inline-flex;align-items:center;justify-content:center;padding:10px 20px;border-radius:16px;font-size:15px;font-weight:950}.status-chip-v122.progress{background:#ddf8ef;color:#0b8b68}.status-chip-v122.success{background:#dcfce7;color:#15803d}.status-chip-v122.danger{background:#fee2e2;color:#b91c1c}.status-chip-v122.draft{background:#fef3c7;color:#b45309}.status-chip-v122.neutral{background:#e5e7eb;color:#374151}.timeline-v122{position:relative}.tl-row-v122{display:grid;grid-template-columns:70px 1fr;gap:18px;align-items:stretch}.tl-left-v122{display:flex;flex-direction:column;align-items:center}.tl-dot-v122{width:58px;height:58px;border-radius:50%;display:flex;align-items:center;justify-content:center;font-size:26px;font-weight:950;background:#fff;color:#98a2b3;border:2px solid #d0d5dd;z-index:2;box-shadow:0 8px 20px rgba(16,24,40,.08)}.tl-line-v122{width:4px;flex:1;min-height:40px;background:#d0d5dd;border-radius:999px;margin-top:6px}.tl-card-v122{background:#fff;border:1px solid transparent;border-radius:22px;padding:18px 20px;margin-bottom:20px}.tl-inner-v122{display:grid;grid-template-columns:1fr 145px;gap:18px;align-items:start}.tl-title-v122{font-size:20px;font-weight:950;color:#101828;margin-bottom:6px;line-height:1.25}.tl-desc-v122{font-size:16px;font-weight:650;color:#667085;line-height:1.5}.tl-date-v122{text-align:right;color:#475467;font-size:16px;font-weight:800;line-height:1.6;white-space:nowrap}.tl-current-v122{display:inline-flex;margin-top:14px;padding:9px 18px;border-radius:11px;background:#005bdb;color:#fff;font-size:14px;font-weight:950}.tl-row-v122.completed .tl-dot-v122,.tl-row-v122.passed .tl-dot-v122,.tl-row-v122.visa-issued .tl-dot-v122{background:#10a878;color:#fff;border-color:#10a878}.tl-row-v122.completed .tl-line-v122,.tl-row-v122.passed .tl-line-v122,.tl-row-v122.visa-issued .tl-line-v122{background:#10a878}.tl-row-v122.current .tl-dot-v122{background:#0f6bff;color:#fff;border:10px solid #eaf2ff;width:58px;height:58px;box-sizing:border-box;font-size:22px}.tl-row-v122.current .tl-line-v122{background:#0f6bff}.tl-row-v122.current .tl-card-v122{background:#f7fbff;border-color:#bfd7ff;box-shadow:0 10px 28px rgba(0,91,219,.11)}.tl-row-v122.current .tl-title-v122{color:#0b4fc5}.tl-row-v122.pending .tl-dot-v122{font-size:18px;color:#667085;background:#fff}.tl-row-v122.failed .tl-dot-v122,.tl-row-v122.visa-rejected .tl-dot-v122{background:#e53935;color:#fff;border-color:#e53935}.tl-row-v122.failed .tl-line-v122,.tl-row-v122.visa-rejected .tl-line-v122{background:#e53935}.tl-row-v122.failed .tl-card-v122,.tl-row-v122.visa-rejected .tl-card-v122{background:#fef2f2;border-color:#fca5a5}.tl-row-v122:last-child .tl-line-v122{display:none}.full-status-btn-v122{margin:26px 0 24px 88px;background:#0067e6;color:#fff;border-radius:14px;text-align:center;padding:18px 22px;font-size:21px;font-weight:950;box-shadow:0 12px 24px rgba(0,103,230,.22)}.help-box-v122{margin-left:88px;border-top:1px solid #edf2f7;padding:18px 0;display:flex;gap:14px;align-items:center}.help-icon-v122{width:48px;height:48px;border-radius:50%;background:#eef5ff;color:#005bdb;display:flex;align-items:center;justify-content:center;font-weight:950}.help-title-v122{font-weight:950;color:#101828;font-size:17px}.help-sub-v122{color:#667085;font-weight:650;font-size:15px}@media(max-width:820px){.status-summary-grid-v122{grid-template-columns:1fr}.status-table-v122{grid-template-columns:115px 1fr}.tl-row-v122{grid-template-columns:58px 1fr;gap:12px}.tl-dot-v122{width:50px;height:50px}.tl-inner-v122{grid-template-columns:1fr}.tl-date-v122{text-align:left}.full-status-btn-v122,.help-box-v122{margin-left:0}.tl-title-v122{font-size:18px}}</style>'
    rows_html = []
    for i, step in enumerate(steps, start=1):
        state = step.get("state", "pending")
        date_text, time_text = application_step_date_time_v121(step.get("value", ""))
        if state == "pending" and (not date_text or date_text == "-"):
            date_text, time_text = "-", ""
        icon = timeline_status_icon_v121(state, i)
        current_badge = '<div class="tl-current-v122">Current Step</div>' if state == "current" else ""
        date_html = f'<div>{_safe_html_v62(date_text)}</div>' + (f'<div>{_safe_html_v62(time_text)}</div>' if time_text else "")
        rows_html.append(
            f'<div class="tl-row-v122 {state}">'
            f'<div class="tl-left-v122"><div class="tl-dot-v122">{icon}</div><div class="tl-line-v122"></div></div>'
            f'<div class="tl-card-v122"><div class="tl-inner-v122"><div><div class="tl-title-v122">{i}. {_safe_html_v62(step.get("title", ""))}</div><div class="tl-desc-v122">{_safe_html_v62(step.get("desc", ""))}</div>{current_badge}</div><div class="tl-date-v122">{date_html}</div></div></div>'
            '</div>'
        )
    html = (
        css + '<div class="status-page-v122">' + '<div class="status-title-v122">Application Status</div>' +
        '<div class="status-summary-v122"><div class="status-summary-grid-v122">' + f'<div class="status-logo-v122">{logo_html}</div>' +
        '<div class="status-table-v122">' +
        f'<div class="status-label-v122">Applicant</div><div class="status-value-v122">{_safe_html_v62(applicant)}</div>' +
        f'<div class="status-label-v122">University</div><div class="status-value-v122">{_safe_html_v62(uni_name)}</div>' +
        f'<div class="status-label-v122">Program</div><div class="status-value-v122">{_safe_html_v62(program_name)}</div>' +
        f'<div class="status-label-v122">Status</div><div class="status-value-v122"><span class="status-chip-v122 {chip_cls}">{_safe_html_v62(chip_text)}</span></div>' +
        '</div></div></div>' + '<div class="timeline-v122">' + ''.join(rows_html) + '</div>' +
        
        '</div>'
    )
    st.markdown(html, unsafe_allow_html=True)

    # v129: automatic big result messages on the timeline page
    # Interview result message appears only while the application is still at the interview-result stage.
    # Once later steps such as offer letter, COA, visa application, or visa result are updated, it will not appear again.
    interview_result = application_stage_value_v116(row, "Interview_Result").lower()
    visa_result = application_stage_value_v116(row, "Visa_Result").lower()
    later_after_interview_v129 = any([
        application_stage_value_v116(row, "Offer_Invoice_Issued"),
        application_stage_value_v116(row, "COA_Issued"),
        application_stage_value_v116(row, "Visa_Mode"),
        application_stage_value_v116(row, "Visa_Application_Number"),
        application_stage_value_v116(row, "Visa_Result"),
    ])

    if not later_after_interview_v129:
        if "pass" in interview_result:
            st.markdown("""
            <div class="auto-result-message-v124 interview-passed-v124">
                <div class="auto-result-icon-v124">🎉</div>
                <h1>Congratulations!</h1>
                <p>You have passed the interview.</p>
            </div>
            """, unsafe_allow_html=True)
        elif "fail" in interview_result:
            st.markdown("""
            <div class="auto-result-message-v124 interview-failed-v124">
                <div class="auto-result-icon-v124">⚠️</div>
                <h1>Sorry</h1>
                <p>You have not been selected.</p>
            </div>
            """, unsafe_allow_html=True)

    if "issued" in visa_result or "approved" in visa_result:
        st.markdown("""
        <div class="auto-result-message-v124 visa-issued-auto-v124">
            <div class="auto-result-icon-v124">🎊</div>
            <h1>Congratulations on your visa!</h1>
            <p>Your visa has been issued.</p>
        </div>
        """, unsafe_allow_html=True)
    elif "reject" in visa_result or "denied" in visa_result:
        st.markdown("""
        <div class="auto-result-message-v124 visa-rejected-auto-v124">
            <div class="auto-result-icon-v124">⚠️</div>
            <h1>Sorry</h1>
            <p>Your visa has been rejected.</p>
        </div>
        """, unsafe_allow_html=True)


def render_application_status_page_v116():
    dash_shell(["Dashboard","Universities","Eligibility Check","Tuition & Scholarship","Contact Us"])
    if st.button("← Back to Ongoing Applications", key="back_to_ongoing_apps_v116", use_container_width=False):
        st.session_state.partner_dashboard_view_v81 = "applications"
        st.session_state.selected_application_id_v116 = ""
        st.session_state.show_visa_result_page_v123 = False
        st.rerun()

    df = applications_df_v116()
    visible = application_owner_filter_v116(df)
    app_id = st.session_state.get("selected_application_id_v116", "")
    if not app_id or len(visible) == 0:
        st.warning("Application record not found.")
        close_shell()
        return
    match = visible[visible["Application_ID"].astype(str) == str(app_id)]
    if len(match) == 0:
        st.warning("Application record not found or not visible for your account.")
        close_shell()
        return
    render_application_status_timeline_v116(match.iloc[-1].to_dict())
    close_shell()

def render_ongoing_applications_page_v116():
    dash_shell(["Dashboard","Universities","Eligibility Check","Tuition & Scholarship","Contact Us"])
    if st.button("← Back to Dashboard", key="back_to_dashboard_apps_v116", use_container_width=False):
        st.session_state.partner_dashboard_view_v81 = "dashboard"
        st.rerun()

    st.markdown("""
    <div class="v85-page-hero">
        <span>Application Management</span>
        <h1>Ongoing Applications / Application Status</h1>
        <p>Continue unfinished applications, check submitted applications, and monitor each applicant's status.</p>
    </div>
    """, unsafe_allow_html=True)

    df = applications_df_v116()
    visible = application_owner_filter_v116(df)
    visible = dedupe_application_rows_v119(visible)
    if len(visible) == 0:
        st.info("No application records found yet. Start an application from a university program page.")
        close_shell()
        return

    # Sort recent first
    if "Last_Updated" in visible.columns:
        visible = visible.sort_values("Last_Updated", ascending=False)
    elif "Submitted_At" in visible.columns:
        visible = visible.sort_values("Submitted_At", ascending=False)

    for i, (_, row) in enumerate(visible.iterrows()):
        app_id = display_clean_v50(row.get("Application_ID", "")) or f"legacy_{i}"
        applicant_name = application_display_name_v116(row)
        university = display_clean_v50(row.get("University", ""))
        major = display_clean_v50(row.get("Desired_Major", ""))
        app_type = display_clean_v50(row.get("Application_Type", ""))
        status = inferred_application_status_v119(row)

        st.markdown(f"""
        <div class="application-row-v116">
            <div>
                <h3>{_safe_html_v62(applicant_name)}</h3>
                <p><b>University:</b> {_safe_html_v62(university)} &nbsp; | &nbsp; <b>Major:</b> {_safe_html_v62(major if major else "Not selected")}</p>
                <p><b>Application Type:</b> {_safe_html_v62(app_type)}</p>
            </div>
            <div class="application-row-status-v116">
                {application_status_badge_v116(status)}
            </div>
        </div>
        """, unsafe_allow_html=True)

        c1, c2, c3 = st.columns([1.2, 1.2, 4])
        is_active_application_v128 = application_is_active_or_submitted_v128(status)
        with c1:
            if is_active_application_v128:
                if st.button("Check Status", key=f"check_status_v116_{app_id}", use_container_width=True):
                    st.session_state.selected_application_id_v116 = app_id
                    st.session_state.partner_dashboard_view_v81 = "application_status"
                    st.session_state.show_visa_result_page_v123 = False
                    st.rerun()
            else:
                if st.button("Continue / Resume / Finish Application", key=f"resume_app_v116_{app_id}", use_container_width=True):
                    resume_application_v116(row)
        with c2:
            if is_active_application_v128:
                st.caption(status or "Submitted")
            else:
                st.caption("Not submitted yet")
        st.divider()

    close_shell()


def partner_dashboard():
    # v86: Avoid rendering dash_shell twice on separate detail pages.
    # In v85, partner_dashboard() rendered dash_shell first, and then the separate
    # partner/staff/activity pages also rendered dash_shell, causing StreamlitDuplicateElementKey.
    current_view_pre_v86 = st.session_state.get("partner_dashboard_view_v81", "dashboard")
    is_separate_page_v86 = (
        st.session_state.get("role") in ["agency_rep", "agency_partner"]
        and current_view_pre_v86 in ["partners", "staff", "activity", "staff_activity", "applications", "application_status"]
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
        if current_view_v85 == "applications":
            render_ongoing_applications_page_v116()
            return
        if current_view_v85 == "application_status":
            render_application_status_page_v116()
            return
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

    # v116: Staff also need access to their own ongoing applications/status page.
    current_view_staff_v116 = st.session_state.get("partner_dashboard_view_v81", "dashboard")
    if st.session_state.role not in ["agency_rep", "agency_partner"]:
        if current_view_staff_v116 == "applications":
            render_ongoing_applications_page_v116()
            return
        if current_view_staff_v116 == "application_status":
            render_application_status_page_v116()
            return

    if st.session_state.role in ["agency_rep", "agency_partner"]:
        portal_label = "Agency Representative Portal"
        intro = "Check students’ eligibility, tuition fees, and submit applications. You can also monitor staff activity within your organization."
    else:
        portal_label = "Agency Staff Portal"
        intro = "Check student eligibility, estimate tuition and scholarship, and manage your own student records."

    agency_logo_v83 = current_agency_logo_v83()
    agency_logo_html = agency_logo_html_v83(agency_logo_v83, "partner-logo-v83") if agency_logo_v83 else ""
    agency_name_v164 = _safe_html_v62(st.session_state.get("agency_name", "") or st.session_state.get("full_name", "") or st.session_state.get("username", ""))
    badge_v164 = official_rep_badge_v77(st.session_state.get("agency_name", "")) if st.session_state.role == "agency_rep" else ""
    # v164: render as compact HTML with no indented raw HTML lines.
    # This prevents Streamlit/Markdown from showing </div> and <p> as a dark code block.
    hero_html_v164 = (
        '<div class="partner-hero partner-hero-v164">'
        f'<div class="partner-status-pill">{_safe_html_v62(portal_label)}</div>'
        '<div class="partner-welcome-line-v83">'
        f'<div><h1>Welcome back,<br>{agency_name_v164} {badge_v164}</h1></div>'
        f'{agency_logo_html}'
        '</div>'
        f'<p>{_safe_html_v62(intro)}</p>'
        '</div>'
    )
    st.markdown(hero_html_v164, unsafe_allow_html=True)

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

        b1, b2, b3, b4 = st.columns([1.1, 1.1, 1.2, 1.3])
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
        with b4:
            if st.button("Ongoing Applications / Status", key="v116_view_applications_rep", use_container_width=True):
                st.session_state.partner_dashboard_view_v81 = "applications"
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

        if st.button("Ongoing Applications / Application Status", key="v116_view_applications_staff", use_container_width=True):
            st.session_state.partner_dashboard_view_v81 = "applications"
            st.rerun()

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

    # v111 fix:
    # "undergraduate" contains the text "graduate", so the old graduate filter accidentally
    # included undergraduate rows. Use explicit category detection instead.
    if "Program" in sub.columns:
        program_text = sub["Program"].astype(str).str.strip().str.lower()

        is_undergraduate = (
            program_text.str.contains(r"\bundergraduate\b|\bbachelor\b|\bba\b|\bbs\b|\bbba\b", regex=True, na=False)
            & ~program_text.str.contains(r"\bgraduate\b|\bmaster\b|\bmasters\b|\bph\.?d\b|\bdoctoral\b", regex=True, na=False)
        )
        is_graduate = (
            program_text.str.contains(r"\bgraduate\b|\bmaster\b|\bmasters\b|\bph\.?d\b|\bdoctoral\b|\bms\b|\bma\b|\bmba\b", regex=True, na=False)
            & ~program_text.str.contains(r"\bundergraduate\b|\bbachelor\b", regex=True, na=False)
        )
        is_language = program_text.str.contains(r"\blanguage\b|\bklp\b|\beap\b|\bkorean\b", regex=True, na=False)

        if ps == "undergraduate":
            sub = sub[is_undergraduate]
        elif ps == "graduate":
            sub = sub[is_graduate]
        elif ps == "language":
            sub = sub[is_language]

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



def user_can_apply_v112():
    """
    v159: Stop the repeated login loop on application pages.
    If the user has already clicked Apply and the app is showing a selected application type,
    the form opens directly instead of showing Partner Login Required again.
    """
    # If the application type is already selected, open the application form directly.
    # This prevents the repeated login/create-account loop after successful login.
    if st.session_state.get("application_type_v109"):
        return True, ""

    # Otherwise, still check normal login status before starting application.
    try:
        restore_login_from_query_v60()
    except Exception:
        pass

    if st.session_state.get("logged_in"):
        username = str(st.session_state.get("username", "")).strip()
        user = find_user(username) if username else None
        role_raw = str((user or {}).get("role", "") or st.session_state.get("role", "")).strip()
        role = role_raw.lower().replace(" ", "_").replace("-", "_")
        status = str((user or {}).get("status", "") or st.session_state.get("status", "approved")).strip().lower()

        if role in ["agency_staff", "staff", "partner_staff"]:
            role = "agency_staff"
        elif role in ["agency_partner", "partner", "partner_agency"]:
            role = "agency_partner"
        elif role in ["agency_rep", "official_representative", "official_representative_agency", "agency_representative"]:
            role = "agency_rep"

        allowed_roles = ["admin", "agency_rep", "agency_partner", "agency_staff", "staff", "partner"]
        if role in allowed_roles and (role == "admin" or status in ["approved", "active"]):
            return True, ""

    return False, "Please login with an approved partner or staff account to start an application."

def nationality_options_v112():
    return [
        "Nepal", "Bangladesh", "Vietnam", "Indonesia", "Pakistan", "India", "Sri Lanka",
        "Mongolia", "Myanmar", "Uzbekistan", "China", "Philippines", "Other"
    ]

def year_options_v112(start=1980, extra_future=2):
    current = datetime.now().year
    return list(range(current + extra_future, start - 1, -1))

APPLICATION_SAMPLE_FILE = DATA / "application_samples.csv"
APPLICATION_DOC_DIR_V114 = BASE / "assets" / "application_documents"
APPLICATION_SAMPLE_DIR_V114 = BASE / "assets" / "application_samples"
APPLICATION_DOC_DIR_V114.mkdir(parents=True, exist_ok=True)
APPLICATION_SAMPLE_DIR_V114.mkdir(parents=True, exist_ok=True)

APPLICATION_PROGRAM_OPTIONS_V114 = ["Undergraduate", "Graduate", "Language"]
APPLICATION_DOC_TYPES_V114 = [
    ("Passport Size Photo", "passport_size_photo", ["jpg", "jpeg", "png"], "Upload passport size photo in JPG/PNG format."),
    ("Passport Copy", "passport_copy", ["pdf", "jpg", "jpeg", "png"], "Upload passport copy in PDF/JPG/PNG format."),
    ("High School Graduation Certificate", "high_school_graduation_certificate", ["pdf"], "Upload high school graduation certificate in PDF format."),
    ("High School Transcript", "high_school_transcript", ["pdf"], "Upload high school transcript in PDF format."),
    ("Family Relationship Certificate", "family_relationship_certificate", ["pdf"], "Upload family relationship certificate in PDF format."),
    ("Family Members ID Card Copy and Notarized Document", "family_members_id_notarized", ["pdf"], "Upload family members ID card copy and notarized document in PDF format."),
    ("Embassy Verified / Apostille Documents", "embassy_verified_apostille", ["pdf"], "Upload embassy verified or apostille documents in PDF format."),
    ("Language Certificate (IELTS/TOEFL)", "language_certificate", ["pdf"], "Upload IELTS/TOEFL language certificate in PDF format."),
    ("Bank Certificate", "bank_certificate", ["pdf"], "Upload bank certificate in PDF format."),
    ("Consent Form", "consent_form", ["pdf"], "Download the consent form, fill applicant details, sign it, and upload PDF."),
]


GRADUATE_DOC_TYPES_V157 = [
    ("Passport Size Photo", "passport_size_photo", ["jpg", "jpeg", "png"], "Upload passport size photo in JPG/PNG format."),
    ("Passport Copy", "passport_copy", ["pdf", "jpg", "jpeg", "png"], "Upload passport copy in PDF/JPG/PNG format."),
    ("Bachelor Graduation Certificate", "bachelor_graduation_certificate", ["pdf"], "Upload university bachelor graduation certificate in PDF format."),
    ("Bachelor Transcript", "bachelor_transcript", ["pdf"], "Upload university bachelor transcript in PDF format."),
    ("Family Relationship Certificate", "family_relationship_certificate", ["pdf"], "Upload family relationship certificate in PDF format."),
    ("Family Members Id Notarized", "family_members_id_notarized", ["pdf"], "Upload family members ID copy and notarized document in PDF format."),
    ("Embassy Verified Apostille", "embassy_verified_apostille", ["pdf"], "Upload embassy verified/apostille documents in PDF format."),
    ("Language Certificate", "language_certificate", ["pdf"], "Upload IELTS/TOEFL/TOPIK or other language certificate in PDF format."),
    ("Bank Certificate", "bank_certificate", ["pdf"], "Upload bank certificate in PDF format."),
    ("Consent Form", "consent_form", ["pdf"], "Download the consent form, fill applicant details, sign it, and upload PDF."),
]

def application_doc_types_for_v157(program_category):
    """Return correct document upload list by application program category."""
    if str(program_category or "").strip().lower() == "graduate":
        return GRADUATE_DOC_TYPES_V157
    return APPLICATION_DOC_TYPES_V114


def application_program_label_v114(program_slug, application_type=""):
    # v117 fix:
    # The word "undergraduate" contains "graduate", so graduate must NOT be checked first.
    ps = str(program_slug or "").strip().lower()
    at = str(application_type or "").strip().lower()
    combined = f"{ps} {at}"

    if any(x in combined for x in ["language", "klp", "eap", "korean language"]):
        return "Language"
    if any(x in combined for x in ["undergraduate", "bachelor", "new student", "transfer"]):
        return "Undergraduate"
    if any(x in combined for x in ["graduate", "master", "masters", "ph.d", "phd", "doctoral"]):
        return "Graduate"
    return "Undergraduate"

def read_application_samples_v114():
    df = read_csv(APPLICATION_SAMPLE_FILE)
    cols = ["Nationality", "Program_Category", "Document_Key", "Document_Label", "Sample_Path", "Updated_At"]
    return ensure_columns_v49(df, cols)

def write_application_samples_v114(df):
    df.fillna("").replace(["nan", "NaN", "None", "null", "<NA>"], "").to_csv(APPLICATION_SAMPLE_FILE, index=False, encoding="utf-8-sig")

def save_application_sample_v114(uploaded_file, nationality, program_category, doc_key):
    if uploaded_file is None:
        return ""
    ext = Path(uploaded_file.name).suffix.lower() or ".png"
    if ext not in [".png", ".jpg", ".jpeg", ".webp"]:
        ext = ".png"
    filename = f"{safe_slug_v49(nationality)}_{safe_slug_v49(program_category)}_{safe_slug_v49(doc_key)}{ext}"
    out_path = APPLICATION_SAMPLE_DIR_V114 / filename
    out_path.write_bytes(uploaded_file.getvalue())
    return f"assets/application_samples/{filename}"

def normalize_sample_program_v117(value):
    v = str(value or "").strip().lower()
    if "language" in v or "klp" in v or "eap" in v:
        return "language"
    # Important: check undergraduate before graduate.
    if "undergraduate" in v or "bachelor" in v or "new student" in v or "transfer" in v:
        return "undergraduate"
    if "graduate" in v or "master" in v or "ph" in v or "doctoral" in v:
        return "graduate"
    return v

def get_application_sample_path_v114(nationality, program_category, doc_key):
    df = read_application_samples_v114()
    if len(df) == 0:
        return ""

    n = str(nationality or "").strip().lower()
    p = normalize_sample_program_v117(program_category)
    d = str(doc_key or "").strip().lower()

    df = df.copy()
    df["_n"] = df["Nationality"].astype(str).str.strip().str.lower()
    df["_p"] = df["Program_Category"].astype(str).apply(normalize_sample_program_v117)
    df["_d"] = df["Document_Key"].astype(str).str.strip().str.lower()

    # Exact nationality + program + document.
    matched = df[(df["_n"] == n) & (df["_p"] == p) & (df["_d"] == d)]
    if len(matched):
        return display_clean_v50(matched.iloc[-1].get("Sample_Path", ""))

    # Fallback: some old data may have Program_Category saved as "Language (EAP/KLP)"
    # or different capitalization. The normalized check above handles most cases,
    # but this gives an additional safety net by matching document + nationality only.
    fallback = df[(df["_n"] == n) & (df["_d"] == d)]
    if len(fallback):
        return display_clean_v50(fallback.iloc[-1].get("Sample_Path", ""))

    return ""

def sample_preview_html_v114(sample_path, label):
    if not sample_path:
        return f"""
        <div class="sample-empty-v114">
            <b>No sample uploaded</b>
            <span>Super admin can upload a nationality-specific sample.</span>
        </div>
        """
    encoded = b64(sample_path)
    if encoded:
        return f"""
        <div class="sample-preview-v114">
            <b>Sample for {_safe_html_v62(label)}</b>
            <img src="data:image/png;base64,{encoded}" />
        </div>
        """
    return f"""
    <div class="sample-empty-v114">
        <b>Sample file registered</b>
        <span>{_safe_html_v62(sample_path)}</span>
    </div>
    """

def consent_form_pdf_bytes_v114():
    text = "CONSENT FORM TEMPLATE\n\nApplicant Name: ____________________\nPassport No.: ____________________\nUniversity: ____________________\nProgram: ____________________\n\nI confirm that the information and documents submitted for admission are true and correct.\n\nApplicant Signature: ____________________\nDate: ____________________"
    try:
        from reportlab.pdfgen import canvas
        from reportlab.lib.pagesizes import A4
        import io
        buffer = io.BytesIO()
        c = canvas.Canvas(buffer, pagesize=A4)
        width, height = A4
        y = height - 70
        c.setFont("Helvetica-Bold", 16)
        c.drawString(60, y, "Consent Form Template")
        c.setFont("Helvetica", 11)
        y -= 40
        for line in text.split("\n")[2:]:
            c.drawString(60, y, line)
            y -= 24
        c.save()
        return buffer.getvalue()
    except Exception:
        return text.encode("utf-8")

def save_application_upload_v114(uploaded_file, applicant_key, doc_key):
    if uploaded_file is None:
        return ""
    ext = Path(uploaded_file.name).suffix.lower()
    safe_name = f"{safe_slug_v49(applicant_key)}_{safe_slug_v49(doc_key)}{ext}"
    out_dir = APPLICATION_DOC_DIR_V114 / safe_slug_v49(applicant_key)
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / safe_name
    out_path.write_bytes(uploaded_file.getvalue())
    return f"assets/application_documents/{safe_slug_v49(applicant_key)}/{safe_name}"

def render_application_documents_step_v114(u, program_slug, application_type):
    step1 = st.session_state.get("application_step1_data_v114", {})
    nationality = step1.get("Nationality", "")
    applicant_name = step1.get("Full_Name_As_Passport", "")
    passport_number = step1.get("Passport_Number", "")
    program_category = application_program_label_v114(program_slug, application_type)
    doc_types_v157 = application_doc_types_for_v157(program_category)
    applicant_key = f"{passport_number}_{applicant_name}_{datetime.now().strftime('%Y%m%d%H%M%S')}"

    st.markdown(f"""
    <div class="application-start-panel-v109 application-start-panel-v112">
        <h3>Application Step 2 · Document Upload</h3>
        <p>Upload documents for <b>{_safe_html_v62(applicant_name)}</b>. Samples are shown based on nationality: <b>{_safe_html_v62(nationality)}</b>.</p>
        <small>Sample images are managed by the super admin under Application Samples. Matching: nationality + program category + document type.</small>
    </div>
    """, unsafe_allow_html=True)

    st.download_button(
        "Download Consent Form Template",
        data=consent_form_pdf_bytes_v114(),
        file_name="consent_form_template.pdf",
        mime="application/pdf",
        use_container_width=True,
        key="download_consent_form_v114"
    )

    uploaded_paths = {}
    missing_docs = []
    with st.form(f"application_docs_step2_v114_{safe_slug_v49(passport_number)}"):
        for label, doc_key, file_types, instruction in doc_types_v157:
            st.markdown(f'<div class="doc-upload-row-title-v114">{_safe_html_v62(label)}</div>', unsafe_allow_html=True)
            c1, c2 = st.columns([1.15, .85])
            with c1:
                st.caption(instruction)
                uploaded = st.file_uploader(
                    f"Upload {label}",
                    type=file_types,
                    key=f"upload_doc_v114_{safe_slug_v49(doc_key)}"
                )
                if uploaded:
                    uploaded_paths[doc_key] = uploaded
            with c2:
                sample_path = get_application_sample_path_v114(nationality, program_category, doc_key)
                st.markdown(sample_preview_html_v114(sample_path, label), unsafe_allow_html=True)

        submitted = st.form_submit_button("Submit Application", use_container_width=True)

        if submitted:
            for label, doc_key, file_types, instruction in doc_types_v157:
                if doc_key not in uploaded_paths:
                    missing_docs.append(label)

            if missing_docs:
                st.error("Please upload all required documents: " + ", ".join(missing_docs))
            else:
                saved_docs = {}
                for label, doc_key, file_types, instruction in doc_types_v157:
                    saved_docs[doc_key] = save_application_upload_v114(uploaded_paths[doc_key], applicant_key, doc_key)

                submitted_app_id_v119 = update_application_submitted_v116(step1, saved_docs)
                submitted_data_v119 = dict(step1)
                submitted_data_v119["Application_ID"] = submitted_app_id_v119
                submitted_data_v119["Status"] = "Submitted"
                st.session_state.application_submitted_data_v118 = submitted_data_v119
                st.session_state.application_step1_data_v114 = submitted_data_v119
                st.session_state.application_step_v114 = 3
                st.balloons()
                st.rerun()

def render_application_start_form_v109(u, program_slug, application_type):
    # v160 emergency fix:
    # Remove the repeated Partner Login Required gate from the application form.
    # Once an Apply option is selected, the application form opens directly.
    # This prevents the login/create-account loop that was blocking logged-in users.
    can_apply, reason = True, ""

    current_step = int(st.session_state.get("application_step_v114", 1) or 1)
    if current_step == 2 and st.session_state.get("application_step1_data_v114"):
        cback, _ = st.columns([1, 4])
        with cback:
            if st.button("← Back to Step 1", key="back_to_step1_v114", use_container_width=True):
                st.session_state.application_step_v114 = 1
                st.rerun()
        render_application_documents_step_v114(u, program_slug, application_type)
        return

    if current_step == 3:
        submitted_name_v118 = ""
        submitted_uni_v118 = ""
        submitted_major_v118 = ""
        try:
            submitted_data_v118 = st.session_state.get("application_submitted_data_v118", {}) or st.session_state.get("application_step1_data_v114", {})
            submitted_name_v118 = submitted_data_v118.get("Full_Name_As_Passport", "") or submitted_data_v118.get("Applicant_Name", "")
            submitted_uni_v118 = submitted_data_v118.get("University", "") or u.get("University", "")
            submitted_major_v118 = submitted_data_v118.get("Desired_Major", "")
        except Exception:
            submitted_uni_v118 = u.get("University", "")

        st.markdown(f"""
        <div class="application-submitted-page-v118">
            <div class="submitted-check-v118">✓</div>
            <h1>Application Submitted Successfully</h1>
            <p>Your application has been submitted and saved in the portal.</p>
            <div class="submitted-summary-v118">
                <span><b>Applicant</b>{_safe_html_v62(submitted_name_v118 or "Applicant")}</span>
                <span><b>University</b>{_safe_html_v62(submitted_uni_v118 or "Selected University")}</span>
                <span><b>Major / Program</b>{_safe_html_v62(submitted_major_v118 or "Selected Program")}</span>
            </div>
        </div>
        """, unsafe_allow_html=True)

        c_done1, c_done2, c_done3 = st.columns([1.2, 1.2, 3])
        with c_done1:
            if st.button("Go to Ongoing Applications", key="go_ongoing_after_submit_v118", use_container_width=True):
                st.session_state.partner_dashboard_view_v81 = "applications"
                st.session_state.page = "Dashboard"
                st.rerun()
        with c_done2:
            if st.button("Back to Program Options", key="back_program_after_submit_v118", use_container_width=True):
                st.session_state.application_type_v109 = ""
                st.session_state.application_step_v114 = 1
                st.session_state.application_step1_data_v114 = {}
                st.session_state.application_submitted_data_v118 = {}
                st.rerun()
        return

    st.markdown(f"""
    <div class="application-start-panel-v109 application-start-panel-v112">
        <h3>Application Page · Step 1</h3>
        <p>You are starting: <b>{_safe_html_v62(application_type)}</b> for <b>{_safe_html_v62(u.get("University", ""))}</b>.</p>
        <small>Only registered and approved staff/partner accounts can submit student applications.</small>
    </div>
    """, unsafe_allow_html=True)

    major_options = [""]
    try:
        dfc = criteria()
        if len(dfc) and "University" in dfc.columns:
            sub = dfc[dfc["University"].astype(str).str.strip().str.lower() == str(u.get("University","")).strip().lower()]
            if "Program" in sub.columns:
                category = application_program_label_v114(program_slug, application_type).lower()
                ptxt = sub["Program"].astype(str).str.lower()
                if category == "undergraduate":
                    sub = sub[ptxt.str.contains("undergraduate|bachelor|bba|ba|bs", regex=True, na=False) & ~ptxt.str.contains("graduate|master|ph", regex=True, na=False)]
                elif category == "graduate":
                    sub = sub[ptxt.str.contains("graduate|master|ph|mba|ma|ms", regex=True, na=False) & ~ptxt.str.contains("undergraduate|bachelor", regex=True, na=False)]
                else:
                    sub = sub[ptxt.str.contains("language|klp|eap|korean", regex=True, na=False)]
            if "Major" in sub.columns:
                major_options += sorted([x for x in sub["Major"].dropna().astype(str).unique().tolist() if x.strip()])
    except Exception:
        pass

    is_undergraduate_new = (
        str(program_slug).lower() == "undergraduate"
        and "new" in str(application_type).lower()
    )

    if is_undergraduate_new:
        form_key = f"ug_new_application_step1_v114_{safe_slug_v49(u.get('University',''))}"
        with st.form(form_key):
            st.markdown("### Applicant Personal Information")
            c1, c2, c3 = st.columns(3)
            with c1:
                passport_full_name = st.text_input("Full Name as in Passport *")
                first_name = st.text_input("First Name *")
                passport_number = st.text_input("Passport Number *")
                nationality = st.selectbox("Nationality *", nationality_options_v112())
                if nationality == "Other":
                    nationality_other = st.text_input("Write Nationality")
                else:
                    nationality_other = ""
            with c2:
                middle_name = st.text_input("Middle Name")
                last_name = st.text_input("Last Name *")
                date_of_birth = st.date_input("Date of Birth *", value=None, min_value=date(1950, 1, 1), max_value=date(datetime.now().year, 12, 31))
                applicant_contact = st.text_input("Applicant Contact Number *")
            with c3:
                applicant_email = st.text_input("Email Address *")
                parents_full_name = st.text_input("Parents Full Name *")
                guardian_contact = st.text_input("Parents / Guardian Contact Number *")
                home_address = st.text_area("Home Country Address *", height=88)

            st.markdown("### Intended Study Information")
            desired_major = st.selectbox("Select Major / Program Willing to Study *", major_options)
            if desired_major == "":
                desired_major_other = st.text_input("If the major is not listed, write the major/program here")
            else:
                desired_major_other = ""

            st.markdown("### Academic Background")
            c4, c5 = st.columns(2)
            with c4:
                high_school_name = st.text_input("High School Name *")
                high_school_passout_year = st.selectbox("High School Passout Year *", year_options_v112(1990, 1))
                high_school_enroll_start = st.date_input("High School Enrolled Period Start", value=None, key=f"{form_key}_hs_start")
                high_school_enroll_end = st.date_input("High School Enrolled Period End", value=None, key=f"{form_key}_hs_end")
                high_school_location = st.text_input("High School Location *")
            with c5:
                middle_school_name = st.text_input("Middle School Name")
                middle_school_enroll_year = st.selectbox("Middle School Enrolled Year", [""] + year_options_v112(1990, 1))
                middle_school_location = st.text_input("Middle School Location")
                passport_issue_year = st.selectbox("Passport Issue Year", [""] + year_options_v112(2000, 1))

            st.markdown("### Financial Information")
            c6, c7 = st.columns(2)
            with c6:
                bank_certificate_owner = st.selectbox("Financial / Bank Certificate Information *", ["Self", "Father", "Mother"])
            with c7:
                bank_amount_usd = st.number_input("Amount in USD *", min_value=0.0, step=100.0, format="%.2f")

            st.markdown("### Written Statements")
            self_intro = st.text_area("Self Introduction * (Max 500 words)", height=180)
            study_plan = st.text_area("Study Plan * (Max 500 words)", height=180)

            w1 = len(str(self_intro).split())
            w2 = len(str(study_plan).split())
            st.caption(f"Self Introduction word count: {w1}/500 · Study Plan word count: {w2}/500")

            submitted_next = st.form_submit_button("Next", use_container_width=True)

            if submitted_next:
                selected_nationality = nationality_other.strip() if nationality == "Other" and nationality_other.strip() else nationality
                selected_major = desired_major if desired_major else desired_major_other.strip()

                required_missing = []
                if not passport_full_name.strip(): required_missing.append("Full Name as in Passport")
                if not first_name.strip(): required_missing.append("First Name")
                if not last_name.strip(): required_missing.append("Last Name")
                if not passport_number.strip(): required_missing.append("Passport Number")
                if not selected_major: required_missing.append("Major / Program Willing to Study")
                if not applicant_contact.strip(): required_missing.append("Applicant Contact Number")
                if not applicant_email.strip(): required_missing.append("Email Address")
                if not parents_full_name.strip(): required_missing.append("Parents Full Name")
                if not guardian_contact.strip(): required_missing.append("Parents / Guardian Contact Number")
                if not home_address.strip(): required_missing.append("Home Country Address")
                if not high_school_name.strip(): required_missing.append("High School Name")
                if not high_school_location.strip(): required_missing.append("High School Location")
                if bank_amount_usd <= 0: required_missing.append("Amount in USD")
                if not self_intro.strip(): required_missing.append("Self Introduction")
                if not study_plan.strip(): required_missing.append("Study Plan")
                if w1 > 500: required_missing.append("Self Introduction must be 500 words or less")
                if w2 > 500: required_missing.append("Study Plan must be 500 words or less")

                if required_missing:
                    st.error("Please complete/fix: " + ", ".join(required_missing))
                else:
                    draft_data_v116 = {
                        "University": u.get("University", ""),
                        "Program_Category": program_slug,
                        "Application_Type": application_type,
                        "Full_Name_As_Passport": passport_full_name.strip(),
                        "First_Name": first_name.strip(),
                        "Middle_Name": middle_name.strip(),
                        "Last_Name": last_name.strip(),
                        "Passport_Number": passport_number.strip(),
                        "Nationality": selected_nationality,
                        "Date_of_Birth": str(date_of_birth) if date_of_birth else "",
                        "Applicant_Contact": applicant_contact.strip(),
                        "Email": applicant_email.strip(),
                        "Parents_Full_Name": parents_full_name.strip(),
                        "Home_Country_Address": home_address.strip(),
                        "Guardian_Contact": guardian_contact.strip(),
                        "High_School_Name": high_school_name.strip(),
                        "High_School_Passout_Year": high_school_passout_year,
                        "High_School_Enroll_Start": str(high_school_enroll_start) if high_school_enroll_start else "",
                        "High_School_Enroll_End": str(high_school_enroll_end) if high_school_enroll_end else "",
                        "High_School_Location": high_school_location.strip(),
                        "Middle_School_Name": middle_school_name.strip(),
                        "Middle_School_Enrolled_Year": middle_school_enroll_year,
                        "Middle_School_Location": middle_school_location.strip(),
                        "Bank_Certificate_Owner": bank_certificate_owner,
                        "Bank_Amount_USD": bank_amount_usd,
                        "Self_Introduction": self_intro.strip(),
                        "Study_Plan": study_plan.strip(),
                        "Desired_Major": selected_major,
                        "Passport_Issue_Year": passport_issue_year,
                    }
                    app_id_v116 = save_step1_draft_v116(draft_data_v116, status="Draft - Documents Pending")
                    draft_data_v116["Application_ID"] = app_id_v116
                    draft_data_v116["Status"] = "Draft - Documents Pending"
                    st.session_state.application_step1_data_v114 = draft_data_v116
                    st.session_state.application_step_v114 = 2
                    st.success("Step 1 saved. Please upload applicant documents in Step 2.")
                    st.rerun()
        return

    is_graduate_application = str(program_slug).lower() == "graduate"
    with st.form(f"application_start_v157_{safe_slug_v49(u.get('University',''))}_{program_slug}_{safe_slug_v49(application_type)}"):
        st.markdown("### Applicant Personal Information")
        c1, c2, c3 = st.columns(3)
        with c1:
            passport_full_name = st.text_input("Full Name as in Passport *")
            first_name = st.text_input("First Name *")
            passport_number = st.text_input("Passport Number *")
            nationality = st.selectbox("Nationality *", nationality_options_v112())
        with c2:
            middle_name = st.text_input("Middle Name")
            last_name = st.text_input("Last Name *")
            date_of_birth = st.date_input("Date of Birth *", value=None, min_value=date(1950, 1, 1), max_value=date(datetime.now().year, 12, 31))
            applicant_contact = st.text_input("Applicant Contact Number *")
        with c3:
            applicant_email = st.text_input("Email Address *")
            parents_full_name = st.text_input("Parents Full Name *")
            guardian_contact = st.text_input("Parents / Guardian Contact Number *")
            home_address = st.text_area("Home Country Address *", height=88)

        st.markdown("### Intended Study Information")
        desired_major = st.selectbox("Select Major / Program Willing to Study *", major_options)
        desired_major_other = ""
        if desired_major == "":
            desired_major_other = st.text_input("If the major is not listed, write the major/program here")

        st.markdown("### Academic Background")
        c4, c5 = st.columns(2)
        if is_graduate_application:
            with c4:
                bachelor_university_name = st.text_input("Bachelor University Name *")
                bachelor_location = st.text_input("Bachelor University Location *")
                bachelor_enroll_start = st.date_input("Bachelor Enrolled Period Start", value=None, key=f"grad_bach_start_{safe_slug_v49(u.get('University',''))}")
                bachelor_enroll_end = st.date_input("Bachelor Enrolled Period End", value=None, key=f"grad_bach_end_{safe_slug_v49(u.get('University',''))}")
            with c5:
                bachelor_graduation_year = st.selectbox("Bachelor Graduation Year *", year_options_v112(1990, 1))
                bachelor_major = st.text_input("Bachelor Major / Department")
                bachelor_gpa = st.text_input("Bachelor GPA / Percentage")
                note = st.text_area("Additional Notes", height=80)
        else:
            with c4:
                high_school_name = st.text_input("High School Name *")
                high_school_passout_year = st.selectbox("High School Passout Year *", year_options_v112(1990, 1))
                high_school_location = st.text_input("High School Location *")
            with c5:
                note = st.text_area("Additional Notes", height=120)

        st.markdown("### Financial Information")
        c6, c7 = st.columns(2)
        with c6:
            bank_certificate_owner = st.selectbox("Financial / Bank Certificate Information *", ["Self", "Father", "Mother"])
        with c7:
            bank_amount_usd = st.number_input("Amount in USD *", min_value=0.0, step=100.0, format="%.2f")

        st.markdown("### Written Statements")
        self_intro = st.text_area("Self Introduction * (Max 500 words)", height=160)
        study_plan = st.text_area("Study Plan * (Max 500 words)", height=160)
        w1 = len(str(self_intro).split())
        w2 = len(str(study_plan).split())
        st.caption(f"Self Introduction word count: {w1}/500 · Study Plan word count: {w2}/500")

        submitted = st.form_submit_button("Next", use_container_width=True)
        if submitted:
            selected_major = desired_major if desired_major else desired_major_other.strip()
            required_missing = []
            for label, val in [
                ("Full Name as in Passport", passport_full_name),
                ("First Name", first_name),
                ("Last Name", last_name),
                ("Passport Number", passport_number),
                ("Major / Program Willing to Study", selected_major),
                ("Email Address", applicant_email),
                ("Applicant Contact Number", applicant_contact),
                ("Parents Full Name", parents_full_name),
                ("Parents / Guardian Contact Number", guardian_contact),
                ("Home Country Address", home_address),
                ("Self Introduction", self_intro),
                ("Study Plan", study_plan),
            ]:
                if not str(val).strip():
                    required_missing.append(label)
            if is_graduate_application:
                if not bachelor_university_name.strip(): required_missing.append("Bachelor University Name")
                if not bachelor_location.strip(): required_missing.append("Bachelor University Location")
            if bank_amount_usd <= 0:
                required_missing.append("Amount in USD")
            if w1 > 500:
                required_missing.append("Self Introduction must be 500 words or less")
            if w2 > 500:
                required_missing.append("Study Plan must be 500 words or less")

            if required_missing:
                st.error("Please complete/fix: " + ", ".join(required_missing))
            else:
                draft_data_v116 = {
                    "Full_Name_As_Passport": passport_full_name.strip(),
                    "First_Name": first_name.strip(),
                    "Middle_Name": middle_name.strip(),
                    "Last_Name": last_name.strip(),
                    "Passport_Number": passport_number.strip(),
                    "Nationality": nationality,
                    "Date_of_Birth": str(date_of_birth) if date_of_birth else "",
                    "Email": applicant_email.strip(),
                    "Applicant_Contact": applicant_contact.strip(),
                    "Parents_Full_Name": parents_full_name.strip(),
                    "Guardian_Contact": guardian_contact.strip(),
                    "Home_Country_Address": home_address.strip(),
                    "Desired_Major": selected_major,
                    "Bank_Certificate_Owner": bank_certificate_owner,
                    "Bank_Amount_USD": bank_amount_usd,
                    "Self_Introduction": self_intro.strip(),
                    "Study_Plan": study_plan.strip(),
                    "Notes": note.strip(),
                    "University": u.get("University", ""),
                    "Program_Category": program_slug,
                    "Application_Type": application_type,
                }
                if is_graduate_application:
                    draft_data_v116.update({
                        "Bachelor_University_Name": bachelor_university_name.strip(),
                        "Bachelor_University_Location": bachelor_location.strip(),
                        "Bachelor_Enrolled_Start": str(bachelor_enroll_start) if bachelor_enroll_start else "",
                        "Bachelor_Enrolled_End": str(bachelor_enroll_end) if bachelor_enroll_end else "",
                        "Bachelor_Graduation_Year": bachelor_graduation_year,
                        "Bachelor_Major": bachelor_major.strip(),
                        "Bachelor_GPA": bachelor_gpa.strip(),
                    })
                app_id_v116 = save_step1_draft_v116(draft_data_v116, status="Draft - Documents Pending")
                draft_data_v116["Application_ID"] = app_id_v116
                draft_data_v116["Status"] = "Draft - Documents Pending"
                st.session_state.application_step1_data_v114 = draft_data_v116
                st.session_state.application_step_v114 = 2
                st.rerun()

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
    ieqas_badge_program_v178 = university_excellent_accreditation_name_badge_v169(u)

    st.markdown(f"""
    <div class="program-detail-page-v109">
        <div class="program-detail-head-v109">
            <div class="program-detail-logo-v109">{logo_html}</div>
            <div class="program-detail-title-area-v178">
                <p class="program-detail-uni-name-v178">{_safe_html_v62(u.get("University", ""))}{ieqas_badge_program_v178}</p>
                <h1>{_safe_html_v62(title)}</h1>
                <span>{_safe_html_v62(schedule_text)}</span>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # v113: If an application option was selected, show the application form as the next page.
    app_type = st.session_state.get("application_type_v109", "")
    if app_type:
        c_back_apply_v113, c_space_apply_v113 = st.columns([1, 4])
        with c_back_apply_v113:
            if st.button("← Back to Program Options", key=f"back_to_program_options_v113_{safe_slug_v49(u.get('University',''))}", use_container_width=True):
                st.session_state.application_type_v109 = ""
                st.session_state.application_page_open_v113 = False
                st.session_state.application_step_v114 = 1
                st.session_state.application_step1_data_v114 = {}
                st.session_state.application_submitted_data_v118 = {}
                st.session_state.current_application_id_v116 = ""
                st.session_state.apply_access_granted_v158 = False
                st.session_state.application_login_verified_v158 = False
                st.rerun()
        render_application_start_form_v109(u, program_slug, app_type)
        return

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
                st.session_state.application_page_open_v113 = True
                if st.session_state.get("logged_in") or st.session_state.get("auth_token"):
                    st.session_state.apply_access_granted_v158 = True
                st.session_state.application_step_v114 = 1
                st.session_state.application_step1_data_v114 = {}
                st.session_state.application_submitted_data_v118 = {}
                st.session_state.current_application_id_v116 = ""
                st.rerun()
        with c2:
            if st.button("Apply as Transfer Student", key=f"apply_transfer_v109_{safe_slug_v49(u.get('University',''))}", use_container_width=True):
                st.session_state.application_type_v109 = "Undergraduate Transfer Application"
                st.session_state.application_page_open_v113 = True
                if st.session_state.get("logged_in") or st.session_state.get("auth_token"):
                    st.session_state.apply_access_granted_v158 = True
                st.session_state.application_step_v114 = 1
                st.session_state.application_step1_data_v114 = {}
                st.session_state.application_submitted_data_v118 = {}
                st.session_state.current_application_id_v116 = ""
                st.rerun()
    elif program_slug == "graduate":
        timeline_html = program_timeline_card_v109(u, "graduate", "Graduate Application", "graduate")
        st.markdown(f'<div class="program-timeline-grid-v109 single-v109">{timeline_html}</div>', unsafe_allow_html=True)
        c1, c2 = st.columns([1,3])
        with c1:
            if st.button("Apply for Graduate", key=f"apply_grad_v109_{safe_slug_v49(u.get('University',''))}", use_container_width=True):
                st.session_state.application_type_v109 = "Graduate Application"
                st.session_state.application_page_open_v113 = True
                if st.session_state.get("logged_in") or st.session_state.get("auth_token"):
                    st.session_state.apply_access_granted_v158 = True
                st.session_state.application_step_v114 = 1
                st.session_state.application_step1_data_v114 = {}
                st.session_state.application_submitted_data_v118 = {}
                st.session_state.current_application_id_v116 = ""
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
                st.session_state.application_page_open_v113 = True
                if st.session_state.get("logged_in") or st.session_state.get("auth_token"):
                    st.session_state.apply_access_granted_v158 = True
                st.session_state.application_step_v114 = 1
                st.session_state.application_step1_data_v114 = {}
                st.session_state.application_submitted_data_v118 = {}
                st.session_state.current_application_id_v116 = ""
                st.rerun()
        with c2:
            if st.button("Apply for EAP", key=f"apply_eap_v109_{safe_slug_v49(u.get('University',''))}", use_container_width=True):
                st.session_state.application_type_v109 = "EAP Application"
                st.session_state.application_page_open_v113 = True
                if st.session_state.get("logged_in") or st.session_state.get("auth_token"):
                    st.session_state.apply_access_granted_v158 = True
                st.session_state.application_step_v114 = 1
                st.session_state.application_step1_data_v114 = {}
                st.session_state.application_submitted_data_v118 = {}
                st.session_state.current_application_id_v116 = ""
                st.rerun()

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
                f'<a class="uni-quick-link-v103 {extra_cls}" href="{href}" rel="noopener noreferrer">'
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
<a class="uni-map-link-v99" href="{open_url}">Open in Google Maps</a>
</div>
<iframe class="uni-map-frame-v99" src="{embed_url}" loading="lazy" referrerpolicy="no-referrer-when-downgrade"></iframe>
</div>
"""
        return map_html_v102.strip()
    except Exception:
        return ""





def accreditation_until_label_v168(value):
    value = display_clean_v50(value)
    if not value:
        return ""
    try:
        parts = value.split("-")
        if len(parts) >= 2 and parts[0] and parts[1]:
            return f"{parts[0]}. {int(parts[1])}"
    except Exception:
        pass
    return value


def university_excellent_accreditation_badge_html_v168(u, compact=False):
    """Dynamic IEQAS-style badge shown only for Excellent accredited universities."""
    status = display_clean_v50(u.get("Accreditation_Status", ""))
    if status.strip().lower() != "excellent accredited":
        return ""

    name = display_clean_v50(u.get("University", ""))
    until = accreditation_until_label_v168(u.get("Accreditation_Until", ""))
    logo_path = display_clean_v50(u.get("University_Logo", ""))
    encoded_logo = b64(logo_path) if logo_path else ""
    logo_html = f'<img src="data:image/png;base64,{encoded_logo}" alt="{_safe_html_v62(name)} logo">' if encoded_logo else '<span class="ieqas-logo-fallback-v168">★</span>'
    size_class = "ieqas-badge-compact-v168" if compact else "ieqas-badge-large-v168"
    until_text = _safe_html_v62(until) if until else "—"

    return (
        f'<span class="ieqas-badge-v168 {size_class}" title="Excellent accredited until {until_text}">'
        f'<span class="ieqas-ring-v168"><span>Ministry of Education</span><span>IEQAS</span><span>Excellent Accredited Institution</span></span>'
        f'<span class="ieqas-inner-v168">'
        f'<span class="ieqas-korean-symbol-v168">◉</span>'
        f'<span class="ieqas-small-title-v168">Ministry of Education Designated</span>'
        f'<span class="ieqas-small-title-v168">International Education Quality Assurance System</span>'
        f'<span class="ieqas-blue-ribbon-v168">Excellent Accredited</span>'
        f'<span class="ieqas-logo-name-v168">{logo_html}<strong>{_safe_html_v62(name)}</strong></span>'
        f'<span class="ieqas-main-text-v168">ACCREDITED</span>'
        f'<span class="ieqas-sub-text-v168">IEQAS</span>'
        f'<span class="ieqas-valid-v168">Valid until {until_text}</span>'
        f'</span>'
        f'</span>'
    )





def resolve_ieqas_badge_path_v177(u):
    """
    Find uploaded IEQAS badge even if the CSV cell was not saved properly.
    Priority:
    1. IEQAS_Badge_Image column
    2. Auto-detect by university slug in assets/ieqas_badges
    3. Auto-detect by university slug in assets/universities
    4. Any saved file containing 'ieqas' and the university slug
    """
    raw = display_clean_v50(u.get("IEQAS_Badge_Image", ""))
    candidates = []
    if raw:
        candidates.append(raw)

    uni = display_clean_v50(u.get("University", ""))
    slug = safe_slug_v49(uni) if uni else ""

    search_dirs = [
        BASE / "assets" / "ieqas_badges",
        BASE / "assets" / "universities",
        BASE / "assets" / "university_logos",
        BASE / "uploads" / "universities",
        BASE / "uploads",
    ]

    if slug:
        for d in search_dirs:
            candidates.extend([
                str(d / f"{slug}_ieqas_badge.png"),
                str(d / f"{slug}_ieqas_badge.jpg"),
                str(d / f"{slug}_ieqas_badge.jpeg"),
                str(d / f"{slug}_ieqas_badge.webp"),
            ])

    # Broad scan fallback
    if slug:
        for d in search_dirs:
            try:
                if d.exists():
                    for p in d.glob("*"):
                        low = p.name.lower()
                        if p.is_file() and "ieqas" in low and slug.lower() in low:
                            candidates.append(str(p))
            except Exception:
                pass

    # Return first readable path; handle both absolute and BASE-relative paths.
    for c in candidates:
        if not c:
            continue
        p = Path(c)
        if p.exists() and p.is_file():
            return str(p)
        p2 = BASE / c
        if p2.exists() and p2.is_file():
            return str(p2)
    return raw








def direct_ieqas_badge_path_v182(university_name):
    """
    v182: Direct fixed IEQAS badge image path.
    No upload UI. Put the real badge image in assets/ieqas_badges/.
    For Kyungsung University, use:
    assets/ieqas_badges/kyungsung_university_ieqas_badge.png
    """
    slug = safe_slug_v49(university_name or "")
    mapping = {
        "kyungsung_university": "assets/ieqas_badges/kyungsung_university_ieqas_badge.png",
    }
    mapped = mapping.get(slug, "")
    if mapped:
        p = BASE / mapped
        if p.exists() and p.is_file():
            return str(p)

    # Generic fallback for any university by slug
    for ext in [".png", ".jpg", ".jpeg", ".webp", ".svg"]:
        p = BASE / "assets" / "ieqas_badges" / f"{slug}_ieqas_badge{ext}"
        if p.exists() and p.is_file():
            return str(p)
    return ""


def direct_ieqas_img_html_v182(university_name, status="", valid_until=""):
    path = direct_ieqas_badge_path_v182(university_name)
    if not path:
        return ""

    try:
        encoded = base64.b64encode(Path(path).read_bytes()).decode("utf-8")
    except Exception:
        return ""

    ext = str(path).lower()
    mime = "image/png"
    if ext.endswith(".jpg") or ext.endswith(".jpeg"):
        mime = "image/jpeg"
    elif ext.endswith(".webp"):
        mime = "image/webp"
    elif ext.endswith(".svg"):
        mime = "image/svg+xml"

    title = f"{status} {valid_until}".strip() or "IEQAS badge"
    return (
        f'<span class="ieqas-direct-badge-wrap-v182" title="{_safe_html_v62(title)}">'
        f'<img class="ieqas-direct-badge-img-v182" src="data:{mime};base64,{encoded}" alt="IEQAS badge" />'
        f'</span>'
    )



def university_excellent_accreditation_name_badge_v169(u):
    """
    v182: Use direct fixed IEQAS badge image only.
    Upload feature removed because it was unreliable.
    """
    university_name = display_clean_v50(u.get("University", ""))
    status = display_clean_v50(u.get("Accreditation_Status", ""))
    until = accreditation_until_label_v168(u.get("Accreditation_Until", ""))
    return direct_ieqas_img_html_v182(university_name, status, until)


def _render_university_detail_v62(u):
    detail_name_style_v99 = university_name_style_v93(u.get("University", ""), u.get("University_Logo", "")) if "university_name_style_v93" in globals() else ""
    logo_html = university_logo_html_v88(u.get("University_Logo", ""), u.get("University", ""))
    image_html = university_slideshow_html_v89(u, "detail_" + safe_slug_v49(u.get("University", ""))) if "university_slideshow_html_v89" in globals() else asset_img_html(u.get("Image", ""), "uni-wide-v32")
    programs_html = program_list_html_for_university(u.get("University", ""))
    program_badges = _program_specific_application_badges_v71(u)
    map_html = google_map_embed_html_v99(u)
    quick_links_html = university_quick_links_html_v103(u)
    student_stats_html = university_student_stats_html_v106(u)
    accreditation_badge_name_v169 = university_excellent_accreditation_name_badge_v169(u)

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
                    <span style="{detail_name_style_v99}">{_safe_html_v62(u.get("University", ""))}</span>{accreditation_badge_name_v169}
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
    accreditation_badge_name_v169 = university_excellent_accreditation_name_badge_v169(u)

    summary_html = f'''<div class="uni-summary-card-v88">
<div class="uni-summary-image-wrap-v88">
{image_html}
</div>
<div class="uni-summary-content-v88">
    <div class="uni-summary-left-v88">
        <div class="uni-logo-box-v88">{logo_html}</div>
        <div class="uni-summary-text-v88">
            <h3 class="uni-name-accent-v93" style="{name_style_v93}">
                <span style="{name_style_v93}">{_safe_html_v62(u.get("University", ""))}</span>{accreditation_badge_name_v169}
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
                "Representative_Phone", "Representative_Fax", "International_Students", "Tuition_Range", "Accreditation_Status", "Accreditation_Until", "IEQAS_Badge_Image", "IEQAS_Badge_Image_Data"]:
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
        new_uni_v109 = unquote_plus(str(uni_query_v109))
        new_prog_v109 = unquote_plus(str(prog_query_v109))
        # v113: only clear application form when user changes university/program.
        # Do not clear it on normal rerun after clicking Apply.
        if (
            st.session_state.get("selected_uni_v62", "") != new_uni_v109
            or st.session_state.get("selected_program_v109", "") != new_prog_v109
        ):
            st.session_state.application_type_v109 = ""
            st.session_state.application_page_open_v113 = False
        st.session_state.selected_uni_v62 = new_uni_v109
        st.session_state.selected_program_v109 = new_prog_v109

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
                        st.session_state.application_page_open_v113 = False
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



# v130 Super Admin partner/agency drill-down helpers
def agency_display_name_v130(item):
    return display_clean_v50(
        item.get("agency_name", "")
        or item.get("company_name", "")
        or item.get("partner_group", "")
        or item.get("full_name", "")
        or item.get("username", "")
    )

def agency_id_from_item_v130(item):
    return normalize_agency_id(
        item.get("agency_id", "")
        or item.get("agency_name", "")
        or item.get("company_name", "")
        or item.get("partner_group", "")
    )

def agency_logo_path_v130(agency_name_or_id):
    target = normalize_agency_id(agency_name_or_id)
    try:
        for a in read_agencies():
            if normalize_agency_id(a.get("agency_id", a.get("agency_name", ""))) == target or normalize_agency_id(a.get("agency_name", "")) == target:
                for key in ["agency_logo", "logo", "Logo", "company_logo"]:
                    if display_clean_v50(a.get(key, "")):
                        return display_clean_v50(a.get(key, ""))
    except Exception:
        pass
    try:
        for u in read_json(USERS):
            if normalize_agency_id(u.get("agency_id", u.get("agency_name", ""))) == target or normalize_agency_id(u.get("agency_name", "")) == target or normalize_agency_id(u.get("company_name", "")) == target:
                for key in ["agency_logo", "logo", "Logo", "company_logo"]:
                    if display_clean_v50(u.get(key, "")):
                        return display_clean_v50(u.get(key, ""))
    except Exception:
        pass
    return ""

def agency_logo_html_v130(agency_name_or_id, size=72):
    logo = agency_logo_path_v130(agency_name_or_id)
    encoded = b64(logo)
    if encoded:
        return f'<div class="agency-logo-v130" style="width:{size}px;height:{size}px"><img src="data:image/png;base64,{encoded}"></div>'
    initials = "".join([x[:1].upper() for x in str(agency_name_or_id or "A").split()[:2]]) or "A"
    return f'<div class="agency-logo-v130 logo-fallback-v130" style="width:{size}px;height:{size}px">{_safe_html_v62(initials)}</div>'

def is_partner_agency_user_v130(u):
    role = str(u.get("role", "")).strip().lower()
    account_type = str(u.get("account_type", "")).strip().lower()
    return role in ["agency_partner", "partner"] or "partner agency" in account_type

def is_staff_user_v130(u):
    role = str(u.get("role", "")).strip().lower()
    account_type = str(u.get("account_type", "")).strip().lower()
    return role == "agency_staff" or "staff" in account_type

def is_official_rep_user_v130(u):
    """
    v146: Badge/classification fix.
    Only true official representative accounts get the verified badge.
    Partner Agency of Official Representative must NOT be treated as official only
    because its text contains the words "official representative".
    """
    role = str(u.get("role", "")).strip().lower()
    account_type = str(u.get("account_type", "")).strip().lower()

    if is_partner_agency_user_v130(u) or is_staff_user_v130(u):
        return False

    return role == "agency_rep" or account_type in [
        "official representative agency",
        "official representative",
        "agency representative",
    ]

def approved_users_v130():
    return [u for u in read_json(USERS) if str(u.get("status", "")).strip().lower() == "approved"]

def official_representatives_v130():
    reps = []
    users = approved_users_v130()
    seen = set()
    # from approved users
    for u in users:
        if is_official_rep_user_v130(u):
            aid = agency_id_from_item_v130(u)
            if aid and aid not in seen:
                seen.add(aid)
                reps.append({
                    "agency_id": aid,
                    "agency_name": agency_display_name_v130(u),
                    "email": display_clean_v50(u.get("email", "")),
                    "phone": display_clean_v50(u.get("phone", "") or u.get("contact_number", "")),
                    "country": display_clean_v50(u.get("country", "")),
                    "created_at": display_clean_v50(u.get("created_at", "")),
                    "source": "user",
                })
    # from agencies defaults/active list, excluding UniQuest and sub-partner agencies
    for a in read_agencies():
        aid = normalize_agency_id(a.get("agency_id", a.get("agency_name", "")))
        name = display_clean_v50(a.get("agency_name", ""))
        if not name or aid == "uniquest":
            continue

        # v146: If the agency was recommended/approved by another agency, it is a partner agency,
        # not an official representative. Do not show verified badge for these agencies.
        recommended_by = display_clean_v50(
            a.get("approved_by_agency", "") 
            or a.get("official_representative", "") 
            or a.get("recommended_by", "")
        )
        if recommended_by:
            continue

        if aid not in seen and str(a.get("status", "")).lower() in ["active", "approved"]:
            seen.add(aid)
            reps.append({
                "agency_id": aid,
                "agency_name": name,
                "email": display_clean_v50(a.get("email", "")),
                "phone": display_clean_v50(a.get("phone", "")),
                "country": display_clean_v50(a.get("country", "")),
                "created_at": display_clean_v50(a.get("created_at", "")),
                "source": "agency",
            })
    return reps

def partner_agencies_v130():
    partners = []
    users = approved_users_v130()
    seen = set()
    for u in users:
        if is_partner_agency_user_v130(u):
            aid = agency_id_from_item_v130(u)
            if aid and aid not in seen:
                seen.add(aid)
                partners.append({
                    "agency_id": aid,
                    "agency_name": agency_display_name_v130(u),
                    "email": display_clean_v50(u.get("email", "")),
                    "phone": display_clean_v50(u.get("phone", "") or u.get("contact_number", "")),
                    "country": display_clean_v50(u.get("country", "")),
                    "created_at": display_clean_v50(u.get("created_at", "")),
                    "recommended_by": display_clean_v50(u.get("approved_by_agency", "") or u.get("official_representative", "") or u.get("sponsor_agency_id", "") or u.get("partner_group", "")),
                })
    # add partner agencies from agencies.json if approved_by agency exists
    for a in read_agencies():
        aid = normalize_agency_id(a.get("agency_id", a.get("agency_name", "")))
        if aid in seen or aid == "uniquest":
            continue
        rec = display_clean_v50(a.get("approved_by_agency", "") or a.get("official_representative", "") or a.get("recommended_by", ""))
        if rec:
            partners.append({
                "agency_id": aid,
                "agency_name": display_clean_v50(a.get("agency_name", "")),
                "email": display_clean_v50(a.get("email", "")),
                "phone": display_clean_v50(a.get("phone", "")),
                "country": display_clean_v50(a.get("country", "")),
                "created_at": display_clean_v50(a.get("created_at", "")),
                "recommended_by": rec,
            })
    return partners

def users_under_agency_v130(agency_id, include_partners=False):
    aid = normalize_agency_id(agency_id)
    out = []
    for u in approved_users_v130():
        user_aid = normalize_agency_id(u.get("agency_id", u.get("agency_name", "")))
        user_agency_name = normalize_agency_id(u.get("agency_name", ""))
        user_company = normalize_agency_id(u.get("company_name", ""))
        sponsor = normalize_agency_id(u.get("sponsor_agency_id", "") or u.get("official_representative", "") or u.get("approved_by_agency", "") or u.get("partner_group", ""))
        if user_aid == aid or user_agency_name == aid or user_company == aid or (include_partners and sponsor == aid):
            out.append(u)
    return out

def staff_under_agency_v130(agency_id):
    return [u for u in users_under_agency_v130(agency_id, include_partners=False) if is_staff_user_v130(u)]

def applications_for_agency_v130(agency_id):
    df = applications_df_v116()
    if df is None or len(df) == 0:
        return pd.DataFrame()
    aid = normalize_agency_id(agency_id)
    users = users_under_agency_v130(agency_id, include_partners=True)
    usernames = [str(u.get("username", "")).strip().lower() for u in users if str(u.get("username", "")).strip()]
    agency_names = [agency_display_name_v130(u).strip().lower() for u in users if agency_display_name_v130(u).strip()]
    agency_names += [str(agency_id).strip().lower()]
    mask = pd.Series([False] * len(df))
    if "Submitted_By" in df.columns and usernames:
        mask = mask | df["Submitted_By"].astype(str).str.strip().str.lower().isin(usernames)
    if "Agency" in df.columns:
        mask = mask | df["Agency"].astype(str).str.strip().str.lower().isin(agency_names)
        mask = mask | df["Agency"].astype(str).apply(lambda x: normalize_agency_id(x) == aid)
    return df[mask].copy()

def applications_for_user_v130(username):
    df = applications_df_v116()
    if df is None or len(df) == 0:
        return pd.DataFrame()
    return df[df.get("Submitted_By", "").astype(str).str.strip().str.lower() == str(username).strip().lower()].copy()

def admin_open_application_detail_v130(app_id):
    st.session_state.page = "Applications"
    st.session_state.admin_app_view_v125 = "program"
    st.session_state.admin_app_selected_id_v125 = str(app_id)
    st.rerun()

def render_application_list_for_admin_network_v130(df, key_prefix):
    if df is None or len(df) == 0:
        st.info("No applications submitted yet.")
        return
    df = dedupe_application_rows_v119(df)
    for idx, (_, app_row) in enumerate(df.iterrows()):
        app_id = display_clean_v50(app_row.get("Application_ID", ""))
        applicant = application_display_name_v116(app_row.to_dict())
        uni = display_clean_v50(app_row.get("University", ""))
        major = display_clean_v50(app_row.get("Desired_Major", "")) or "Not selected"
        status = inferred_application_status_v119(app_row.to_dict())
        st.markdown(
            '<div class="network-app-row-v130">'
            f'<div><h4>{_safe_html_v62(applicant)}</h4>'
            f'<p><b>University:</b> {_safe_html_v62(uni)} · <b>Major:</b> {_safe_html_v62(major)} · <b>Submitted by:</b> {_safe_html_v62(display_clean_v50(app_row.get("Submitted_By","")) or "-")}</p></div>'
            f'<div>{application_status_badge_v116(status)}</div>'
            '</div>',
            unsafe_allow_html=True
        )
        if st.button("Open Application Details", key=f"{key_prefix}_open_app_{idx}_{safe_slug_v49(app_id)}", use_container_width=True):
            admin_open_application_detail_v130(app_id)


def pending_approval_requests_v150():
    """
    Dedicated pending signup/register approval list.
    - Super admin (role=admin) can see all pending partner/staff/agency representative requests.
    - Official representative can see only requests that selected their agency as recommended by / official representative.
    """
    users = read_json(USERS)
    rows = []
    current_role = str(st.session_state.get("role", "")).strip()
    current_key = normalize_agency_id(current_agency_id() or st.session_state.get("agency_name", ""))

    for u in users:
        role = str(u.get("role", "")).strip()
        status = str(u.get("status", "")).strip().lower()
        if status != "pending":
            continue
        if role not in ["agency_rep", "agency_staff", "agency_partner", "partner"]:
            continue

        if current_role == "admin":
            rows.append(u)
        elif role in ["agency_staff", "agency_partner", "partner"] and user_approval_group_matches_v77(u, current_key):
            rows.append(u)

    seen = set()
    deduped = []
    for u in rows:
        key = (str(u.get("username", "")).strip().lower(), str(u.get("email", "")).strip().lower())
        if key in seen:
            continue
        seen.add(key)
        deduped.append(u)
    return deduped


def update_pending_request_status_v150(req, new_status):
    """Approve/decline pending signup request from dedicated pending approvals page."""
    current_role = str(st.session_state.get("role", "")).strip()
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
        if not same_user:
            continue

        allowed = False
        if current_role == "admin":
            allowed = True
        elif str(u.get("role", "")) in ["agency_staff", "agency_partner", "partner"] and user_approval_group_matches_v77(u, current_key):
            allowed = True

        if allowed:
            u["status"] = new_status
            u["approved_by"] = st.session_state.get("username", "")
            u["approved_at"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            u["approved_by_agency"] = st.session_state.get("agency_name", "Portal Admin" if current_role == "admin" else "")
            changed = True
            if str(u.get("role", "")) in ["agency_partner", "partner"]:
                affected_agency_ids.add(normalize_agency_id(u.get("agency_id", u.get("agency_name", ""))))

    write_json(USERS, all_users)

    if affected_agency_ids:
        agencies = read_agencies()
        for a in agencies:
            aid = normalize_agency_id(a.get("agency_id", a.get("agency_name", "")))
            if aid in affected_agency_ids:
                a["status"] = new_status
                a["approved_by"] = st.session_state.get("username", "")
                a["approved_at"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                a["approved_by_agency"] = st.session_state.get("agency_name", "Portal Admin" if current_role == "admin" else "")
                if not a.get("agency_logo"):
                    for u in all_users:
                        if normalize_agency_id(u.get("agency_id", u.get("agency_name", ""))) == aid and u.get("agency_logo"):
                            a["agency_logo"] = u.get("agency_logo")
                            break
        write_agencies(agencies)

    st.cache_data.clear()
    return changed



def pending_request_visual_html_v154(req):
    """Show company logo for partner agency requests and staff/passport-size photo for staff requests."""
    role = str(req.get("role", "")).strip().lower()
    account_type = str(req.get("account_type", "")).strip().lower()
    name = display_clean_v50(req.get("agency_name", "") or req.get("company_name", "") or req.get("full_name", "") or req.get("username", ""))

    if role in ["agency_partner", "partner"] or "partner agency" in account_type:
        img_path = display_clean_v50(req.get("agency_logo", "") or req.get("company_logo", "") or req.get("logo_path", "") or req.get("logo", ""))
        label = "Company Logo"
        fallback = "".join([p[:1].upper() for p in name.split()[:2]]) or "AG"
        img_class = "pending-logo-img-v154"
    else:
        img_path = display_clean_v50(req.get("passport_photo", "") or req.get("photo", "") or req.get("profile_photo", "") or req.get("staff_photo", "") or req.get("image_path", ""))
        label = "Staff Photo"
        fallback = "".join([p[:1].upper() for p in name.split()[:2]]) or "ST"
        img_class = "pending-staff-img-v154"

    encoded = b64(img_path) if img_path else ""
    if encoded:
        return f'<div class="pending-visual-box-v154"><img class="{img_class}" src="data:image/png;base64,{encoded}" alt="{_safe_html_v62(label)}"><span>{_safe_html_v62(label)}</span></div>'
    return f'<div class="pending-visual-box-v154 pending-visual-fallback-v154"><div>{_safe_html_v62(fallback)}</div><span>{_safe_html_v62(label)}</span></div>'


def render_pending_approval_page_v150():
    requests = pending_approval_requests_v150()
    role = str(st.session_state.get("role", ""))
    title_note = "Super admin can see and approve/decline all pending signup requests." if role == "admin" else "You can only see requests that selected your organization as their recommended official representative."

    # v152: HTML styled approve/decline links are processed here.
    try:
        pending_action_v152 = st.query_params.get("pending_action_v152", "")
        pending_user_v152 = st.query_params.get("pending_user_v152", "")
        pending_email_v152 = st.query_params.get("pending_email_v152", "")
    except Exception:
        pending_action_v152 = pending_user_v152 = pending_email_v152 = ""
    if isinstance(pending_action_v152, list):
        pending_action_v152 = pending_action_v152[0] if pending_action_v152 else ""
    if isinstance(pending_user_v152, list):
        pending_user_v152 = pending_user_v152[0] if pending_user_v152 else ""
    if isinstance(pending_email_v152, list):
        pending_email_v152 = pending_email_v152[0] if pending_email_v152 else ""

    pending_action_v152 = str(pending_action_v152 or "").strip().lower()
    if pending_action_v152 in ["approve", "decline"] and str(pending_user_v152).strip():
        target_req_v152 = next(
            (
                r for r in requests
                if str(r.get("username", "")).strip() == str(pending_user_v152).strip()
                and (not str(pending_email_v152).strip() or str(r.get("email", "")).strip() == str(pending_email_v152).strip())
            ),
            None
        )
        new_status_v152 = "approved" if pending_action_v152 == "approve" else "rejected"
        if target_req_v152 and update_pending_request_status_v150(target_req_v152, new_status_v152):
            st.session_state.pending_action_message_v152 = f"{display_clean_v50(target_req_v152.get('agency_name', '') or target_req_v152.get('full_name', '') or target_req_v152.get('username', 'Request'))} {new_status_v152}."
        else:
            st.session_state.pending_action_message_v152 = "This pending request could not be updated. Please check the approval authority."
        try:
            st.query_params.clear()
        except Exception:
            pass
        st.session_state.page = "Admin Dashboard"
        st.session_state.admin_network_view_v130 = "pending_approvals"
        st.rerun()

    msg_v152 = st.session_state.pop("pending_action_message_v152", "")
    if msg_v152:
        if "approved" in msg_v152.lower():
            st.success(msg_v152)
        elif "rejected" in msg_v152.lower():
            st.warning(msg_v152)
        else:
            st.error(msg_v152)

    st.markdown(f"""
    <div class="network-page-head-v130 pending-page-head-v150">
        <h2>Pending Signup Approval Requests</h2>
        <p>{_safe_html_v62(title_note)}</p>
    </div>
    """, unsafe_allow_html=True)

    if not requests:
        st.info("No pending approval requests found.")
        return

    for idx, req in enumerate(requests):
        company = display_clean_v50(req.get("agency_name", "") or req.get("company_name", "") or req.get("partner_group", "") or req.get("full_name", ""))
        applicant = display_clean_v50(req.get("full_name", "") or req.get("name", "") or req.get("username", ""))
        username = display_clean_v50(req.get("username", ""))
        email = display_clean_v50(req.get("email", ""))
        phone = display_clean_v50(req.get("phone", "") or req.get("contact_number", ""))
        position = display_clean_v50(req.get("position", ""))
        account_type = display_clean_v50(req.get("account_type", req.get("role", "")))
        country = display_clean_v50(req.get("country", ""))
        recommended_by = display_clean_v50(req.get("official_representative", "") or req.get("partner_group", "") or req.get("sponsor_agency_id", "") or req.get("requested_approver_agency_id", ""))
        created_at = display_clean_v50(req.get("created_at", ""))

        from urllib.parse import quote as url_quote_v153
        action_approve_url = f"?pending_action_v152=approve&pending_user_v152={url_quote_v153(username)}&pending_email_v152={url_quote_v153(email)}"
        action_decline_url = f"?pending_action_v152=decline&pending_user_v152={url_quote_v153(username)}&pending_email_v152={url_quote_v153(email)}"

        visual_html_v154 = pending_request_visual_html_v154(req)
        st.markdown(f"""
        <div class="pending-row-v152 pending-row-v154">
            <div class="pending-request-card-v150 pending-request-card-v152 pending-request-card-v154">
                {visual_html_v154}
                <div class="pending-info-v154">
                    <span class="pending-chip-v150">Pending</span>
                    <h3>{_safe_html_v62(company or applicant or "Pending Request")}</h3>
                    <p><b>Applicant:</b> {_safe_html_v62(applicant)} &nbsp; | &nbsp; <b>Username:</b> {_safe_html_v62(username)} &nbsp; | &nbsp; <b>Email:</b> {_safe_html_v62(email or "-")}</p>
                    <p><b>Type:</b> {_safe_html_v62(account_type or "-")} &nbsp; | &nbsp; <b>Position:</b> {_safe_html_v62(position or "-")} &nbsp; | &nbsp; <b>Phone:</b> {_safe_html_v62(phone or "-")} &nbsp; | &nbsp; <b>Country:</b> {_safe_html_v62(country or "-")}</p>
                    <p><b>Recommended / Approval Agency:</b> {_safe_html_v62(recommended_by or "Portal Super Admin")} &nbsp; | &nbsp; <b>Registered:</b> {_safe_html_v62(created_at or "-")}</p>
                </div>
            </div>
            <div class="pending-action-panel-v152">
                <a class="pending-action-btn-v152 approve-v152" href="{action_approve_url}" target="_self">Approve</a>
                <a class="pending-action-btn-v152 decline-v152" href="{action_decline_url}" target="_self">Decline</a>
            </div>
        </div>
        """, unsafe_allow_html=True)


def render_admin_network_page_v130():
    view = st.session_state.get("admin_network_view_v130", "")
    selected_id = st.session_state.get("admin_network_selected_id_v130", "")
    selected_type = st.session_state.get("admin_network_selected_type_v130", "")

    if st.button("← Back to Admin Dashboard", key="admin_network_back_home_v130", use_container_width=False):
        st.session_state.admin_network_view_v130 = ""
        st.session_state.admin_network_selected_id_v130 = ""
        st.session_state.admin_network_selected_type_v130 = ""
        st.rerun()

    if view == "pending_approvals":
        render_pending_approval_page_v150()
        return

    if view == "official_list":
        reps = official_representatives_v130()
        st.markdown('<div class="network-page-head-v130"><h2>Official Representative / Partners</h2><p>Click any official representative to see staff, applications, and submitted applicant records.</p></div>', unsafe_allow_html=True)
        if not reps:
            st.info("No official representative agencies found.")
            return
        for idx, rep in enumerate(reps):
            apps = applications_for_agency_v130(rep["agency_id"])
            staff_count = len(staff_under_agency_v130(rep["agency_id"]))
            st.markdown(
                '<div class="network-agency-card-v130">'
                f'{agency_logo_html_v130(rep["agency_id"], 82)}'
                f'<div><div class="network-official-title-v141"><h3>{official_rep_name_html_v141(rep["agency_name"])}</h3></div>'
                f'<div class="network-official-badge-row-v141">{official_rep_badge_html_v141()}</div>'
                f'<p><b>Email:</b> {_safe_html_v62(rep.get("email","") or "-")} · <b>Phone:</b> {_safe_html_v62(rep.get("phone","") or "-")} · <b>Country:</b> {_safe_html_v62(rep.get("country","") or "-")}</p>'
                f'<p><b>Registered staff:</b> {staff_count} · <b>Applications submitted:</b> {len(apps)}</p></div>'
                '</div>',
                unsafe_allow_html=True
            )
            if st.button("View Official Partner Details", key=f"view_rep_v130_{idx}_{rep['agency_id']}", use_container_width=True):
                st.session_state.admin_network_view_v130 = "agency_detail"
                st.session_state.admin_network_selected_id_v130 = rep["agency_id"]
                st.session_state.admin_network_selected_type_v130 = "official"
                st.rerun()
        return

    if view == "partner_list":
        partners = partner_agencies_v130()
        st.markdown('<div class="network-page-head-v130"><h2>Other Partner Agencies</h2><p>Approved sub-partner companies and the official representative who recommended them.</p></div>', unsafe_allow_html=True)
        if not partners:
            st.info("No approved other partner agencies found.")
            return
        for idx, partner in enumerate(partners):
            apps = applications_for_agency_v130(partner["agency_id"])
            staff_count = len(staff_under_agency_v130(partner["agency_id"]))
            rec = partner.get("recommended_by", "") or "Not provided"
            st.markdown(
                '<div class="network-agency-card-v130">'
                f'{agency_logo_html_v130(partner["agency_id"], 82)}'
                f'<div><h3>{_safe_html_v62(partner["agency_name"])}</h3>'
                f'<p><b>Recommended by:</b> {official_rep_name_html_v141(rec) if rec and rec != "Not provided" else _safe_html_v62(rec)} · <b>Registered:</b> {_safe_html_v62(partner.get("created_at","") or "-")}</p>'
                f'<p><b>Email:</b> {_safe_html_v62(partner.get("email","") or "-")} · <b>Phone:</b> {_safe_html_v62(partner.get("phone","") or "-")} · <b>Staff:</b> {staff_count} · <b>Applications:</b> {len(apps)}</p></div>'
                '</div>',
                unsafe_allow_html=True
            )
            if st.button("View Partner Agency Details", key=f"view_partner_v130_{idx}_{partner['agency_id']}", use_container_width=True):
                st.session_state.admin_network_view_v130 = "agency_detail"
                st.session_state.admin_network_selected_id_v130 = partner["agency_id"]
                st.session_state.admin_network_selected_type_v130 = "partner"
                st.rerun()
        return

    if view == "eligibility_checks":
        e = read_csv(ELIG_LOGS)
        st.markdown('<div class="network-page-head-v130"><h2>Eligibility Check Usage</h2><p>List of users who used the eligibility check, number of checks, and recent checked student records.</p></div>', unsafe_allow_html=True)
        if e.empty:
            st.info("No eligibility check records found yet.")
            return

        for col in ["partner_username", "agency_id", "agency_name", "checked_by_name", "student_name", "university", "major", "result", "timestamp"]:
            if col not in e.columns:
                e[col] = ""

        grouped = e.groupby(["partner_username", "agency_id", "agency_name", "checked_by_name"], dropna=False).size().reset_index(name="Checks")
        grouped = grouped.sort_values("Checks", ascending=False)

        for idx, row in grouped.iterrows():
            username = display_clean_v50(row.get("partner_username", "")) or "Unknown user"
            checked_by = display_clean_v50(row.get("checked_by_name", "")) or username
            agency_name = display_clean_v50(row.get("agency_name", "")) or display_clean_v50(row.get("agency_id", "")) or "-"
            checks = int(row.get("Checks", 0))
            user_records = e[e["partner_username"].astype(str).fillna("") == str(row.get("partner_username", ""))]
            latest = user_records.sort_values("timestamp", ascending=False).head(5) if "timestamp" in user_records.columns else user_records.head(5)

            st.markdown(
                '<div class="elig-user-card-v148">'
                f'<h3>{_safe_html_v62(checked_by)}</h3>'
                f'<p><b>Username:</b> {_safe_html_v62(username)} · <b>Agency:</b> {_safe_html_v62(agency_name)} · <b>Total eligibility checks:</b> {checks}</p>'
                '</div>',
                unsafe_allow_html=True
            )
            with st.expander(f"View recent checks by {checked_by}"):
                show_cols = [c for c in ["timestamp", "student_name", "program", "university", "major", "gpa", "ielts", "toefl_ibt", "topik", "result"] if c in latest.columns]
                if show_cols:
                    st.dataframe(latest[show_cols], use_container_width=True, hide_index=True)
                else:
                    st.dataframe(latest, use_container_width=True, hide_index=True)
        return

    if view == "agency_detail" and selected_id:
        agency_name = selected_id
        all_agencies = official_representatives_v130() + partner_agencies_v130()
        found = next((a for a in all_agencies if normalize_agency_id(a.get("agency_id","")) == normalize_agency_id(selected_id)), {})
        display_name = found.get("agency_name", selected_id)
        staff = staff_under_agency_v130(selected_id)
        apps = applications_for_agency_v130(selected_id)
        agency_heading_html_v141 = official_rep_name_html_v141(display_name) if selected_type == "official" else _safe_html_v62(display_name)
        agency_type_badge_v141 = official_rep_badge_html_v141() if selected_type == "official" else _safe_html_v62("Partner Agency")
        st.markdown(
            '<div class="network-detail-hero-v130">'
            f'{agency_logo_html_v130(selected_id, 108)}'
            f'<div><span>{agency_type_badge_v141}</span>'
            f'<h2>{agency_heading_html_v141}</h2>'
            f'<p><b>Registered staff:</b> {len(staff)} · <b>Submitted applications:</b> {len(apps)}</p></div>'
            '</div>',
            unsafe_allow_html=True
        )
        c1, c2 = st.columns(2)
        with c1:
            if st.button("View Staff List", key="network_staff_list_v130", use_container_width=True):
                st.session_state.admin_network_view_v130 = "staff_list"
                st.rerun()
        with c2:
            if st.button("View Submitted Applications", key="network_app_list_v130", use_container_width=True):
                st.session_state.admin_network_view_v130 = "app_list"
                st.rerun()

        st.markdown("### Recent Applications")
        render_application_list_for_admin_network_v130(apps.head(5) if hasattr(apps, "head") else apps, f"detail_recent_{safe_slug_v49(selected_id)}")
        return

    if view == "staff_list" and selected_id:
        staff = staff_under_agency_v130(selected_id)
        st.markdown('<div class="network-page-head-v130"><h2>Registered Staff List</h2><p>Staff registered under this organization.</p></div>', unsafe_allow_html=True)
        if not staff:
            st.info("No registered staff found.")
        for idx, u in enumerate(staff):
            username = display_clean_v50(u.get("username", ""))
            apps = applications_for_user_v130(username)
            st.markdown(
                '<div class="network-staff-card-v130">'
                f'<div><h3>{_safe_html_v62(display_clean_v50(u.get("full_name","")) or username)}</h3>'
                f'<p><b>Position:</b> {_safe_html_v62(display_clean_v50(u.get("position","")) or "-")} · <b>Email:</b> {_safe_html_v62(display_clean_v50(u.get("email","")) or "-")} · <b>Contact:</b> {_safe_html_v62(display_clean_v50(u.get("phone","") or u.get("contact_number","")) or "-")}</p>'
                f'<p><b>Applications submitted:</b> {len(apps)}</p></div>'
                '</div>',
                unsafe_allow_html=True
            )
            if len(apps):
                with st.expander(f"Applications submitted by {display_clean_v50(u.get('full_name','')) or username}"):
                    render_application_list_for_admin_network_v130(apps, f"staff_{idx}_{safe_slug_v49(username)}")
        return

    if view == "app_list" and selected_id:
        apps = applications_for_agency_v130(selected_id)
        st.markdown('<div class="network-page-head-v130"><h2>Submitted Applications</h2><p>Click any application to download files or update applicant status.</p></div>', unsafe_allow_html=True)
        render_application_list_for_admin_network_v130(apps, f"agencyapps_{safe_slug_v49(selected_id)}")
        return

def handle_admin_dashboard_jump_v148():
    """Backward compatibility for old dashboard links. v149 uses Streamlit buttons instead."""
    try:
        jump = st.query_params.get("adminjump", "")
    except Exception:
        jump = ""
    if isinstance(jump, list):
        jump = jump[0] if jump else ""
    jump = str(jump or "").strip().lower()
    if not jump:
        return False

    try:
        st.query_params.clear()
    except Exception:
        pass

    st.session_state.page = "Admin Dashboard"
    if jump == "official":
        st.session_state.admin_network_view_v130 = "official_list"
    elif jump == "partners":
        st.session_state.admin_network_view_v130 = "partner_list"
    elif jump == "eligibility":
        st.session_state.admin_network_view_v130 = "eligibility_checks"
    elif jump == "pending":
        st.session_state.page = "Admin Dashboard"
        st.session_state.admin_network_view_v130 = "pending_approvals"
    elif jump == "universities":
        st.session_state.page = "Universities"
        st.session_state.admin_network_view_v130 = ""
    st.session_state.admin_network_selected_id_v130 = ""
    st.session_state.admin_network_selected_type_v130 = ""
    st.rerun()


def admin():
    dash_shell(["Admin Dashboard","Partner Management","Universities","Eligibility Rules","Tuition Rules","Scholarship Rules","Applications","Application Samples"])
    handle_admin_dashboard_jump_v148()

    users_list = read_json(USERS)
    users = pd.DataFrame(users_list)

    if len(users):
        partners = users[users["role"].isin(["agency_rep", "agency_staff", "agency_partner", "partner"])].copy()
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
    other_partner_agencies = len(partners[partners["role"].isin(["agency_partner", "partner"])]) if len(partners) and "role" in partners.columns else 0
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
    <div class="admin-stats-grid-v148">
        <div class="admin-stat-card-link-v148">
            <div class="admin-stat-card-v73">
                <div class="stat-icon-v73">{official_rep_icon_html_v141("official-rep-icon-dashboard-v142", 24)}</div>
                <b>Official Representative / Partners</b>
                <h2>{len(official_representatives_v130())}</h2>
                <p>Official partner organizations</p>
            </div>
        </div>
        <div class="admin-stat-card-link-v148">
            <div class="admin-stat-card-v73">
                <div class="stat-icon-v73">🤝</div>
                <b>Other Partner Agencies</b>
                <h2>{len(partner_agencies_v130())}</h2>
                <p>Approved sub-partner agencies</p>
            </div>
        </div>
        <div class="admin-stat-card-link-v148">
            <div class="admin-stat-card-v73 warning-v73">
                <div class="stat-icon-v73">⏳</div>
                <b>Pending Approval</b>
                <h2>{pending}</h2>
                <p>Waiting for admin action</p>
            </div>
        </div>
        <div class="admin-stat-card-link-v148">
            <div class="admin-stat-card-v73">
                <div class="stat-icon-v73">🏛️</div>
                <b>Universities</b>
                <h2>{total_unis}</h2>
                <p>University profiles</p>
            </div>
        </div>
        <div class="admin-stat-card-link-v148">
            <div class="admin-stat-card-v73">
                <div class="stat-icon-v73">📋</div>
                <b>Eligibility Checks</b>
                <h2>{total_checks}</h2>
                <p>Student check records</p>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # v149: Use Streamlit buttons for dashboard card actions.
    # HTML links caused full page reloads on Streamlit and could send the user back to Home.
    st.markdown('<div class="admin-card-action-row-v149">', unsafe_allow_html=True)
    ac1_v149, ac2_v149, ac3_v149, ac4_v149, ac5_v149 = st.columns(5)
    with ac1_v149:
        if st.button("Open Official Representatives", key="dash_open_official_v149", use_container_width=True):
            st.session_state.page = "Admin Dashboard"
            st.session_state.admin_network_view_v130 = "official_list"
            st.session_state.admin_network_selected_id_v130 = ""
            st.session_state.admin_network_selected_type_v130 = ""
            st.rerun()
    with ac2_v149:
        if st.button("Open Partner Agencies", key="dash_open_partners_v149", use_container_width=True):
            st.session_state.page = "Admin Dashboard"
            st.session_state.admin_network_view_v130 = "partner_list"
            st.session_state.admin_network_selected_id_v130 = ""
            st.session_state.admin_network_selected_type_v130 = ""
            st.rerun()
    with ac3_v149:
        if st.button("Open Pending Approvals", key="dash_open_pending_v149", use_container_width=True):
            st.session_state.page = "Admin Dashboard"
            st.session_state.admin_network_view_v130 = "pending_approvals"
            st.session_state.admin_network_selected_id_v130 = ""
            st.session_state.admin_network_selected_type_v130 = ""
            st.rerun()
    with ac4_v149:
        if st.button("Open Universities", key="dash_open_universities_v149", use_container_width=True):
            st.session_state.page = "Universities"
            st.session_state.admin_network_view_v130 = ""
            st.rerun()
    with ac5_v149:
        if st.button("Open Eligibility Usage", key="dash_open_eligibility_v149", use_container_width=True):
            st.session_state.page = "Admin Dashboard"
            st.session_state.admin_network_view_v130 = "eligibility_checks"
            st.session_state.admin_network_selected_id_v130 = ""
            st.session_state.admin_network_selected_type_v130 = ""
            st.rerun()
    st.markdown('</div>', unsafe_allow_html=True)


    # v130: if super admin is inside a partner/agency drill-down page, render it here.
    if st.session_state.get("admin_network_view_v130", ""):
        render_admin_network_page_v130()
        close_shell()
        return

    official_shortcut_heading_v147 = f'<div class="network-heading-with-icon-v147">{official_rep_icon_html_v141("official-rep-icon-heading-v147", 30)}<span>Official Representative / Partners</span></div>'
    st.markdown(f"""
    <div class="network-shortcut-grid-v130">
        <div class="network-shortcut-card-v130">
            <h2>{official_shortcut_heading_v147}</h2>
            <p>View official partners, staff under each organization, and applications submitted through them.</p>
        </div>
        <div class="network-shortcut-card-v130">
            <h2>🤝 Other Partner Agencies</h2>
            <p>View approved sub-partner agencies, who recommended them, their staff, and submitted applications.</p>
        </div>
    </div>
    """, unsafe_allow_html=True)
    nc1_v130, nc2_v130, nc3_v130 = st.columns([1,1,3])
    with nc1_v130:
        if st.button("View Official Partners", key="admin_view_official_partners_v130", use_container_width=True):
            st.session_state.admin_network_view_v130 = "official_list"
            st.session_state.admin_network_selected_id_v130 = ""
            st.session_state.admin_network_selected_type_v130 = ""
            st.rerun()
    with nc2_v130:
        if st.button("View Other Partner Agencies", key="admin_view_other_partners_v130", use_container_width=True):
            st.session_state.admin_network_view_v130 = "partner_list"
            st.session_state.admin_network_selected_id_v130 = ""
            st.session_state.admin_network_selected_type_v130 = ""
            st.rerun()

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
            <div class="status-row-v73"><span class="dot blue"></span><b>Official Reps</b><em>{agency_reps}</em></div>
            <div class="status-row-v73"><span class="dot blue"></span><b>Other Partner Agencies</b><em>{other_partner_agencies}</em></div>
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
    dash_shell(["Admin Dashboard","Partner Management","Universities","Eligibility Rules","Tuition Rules","Scholarship Rules","Applications","Application Samples"])
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
    dash_shell(["Admin Dashboard","Partner Management","Universities","Eligibility Rules","Tuition Rules","Scholarship Rules","Applications","Application Samples"])
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
    dash_shell(["Admin Dashboard","Partner Management","Universities","Eligibility Rules","Tuition Rules","Scholarship Rules","Applications","Application Samples"])

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
    dash_shell(["Admin Dashboard","Partner Management","Universities","Eligibility Rules","Tuition Rules","Scholarship Rules","Applications","Application Samples"])
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
    dash_shell(["Admin Dashboard","Partner Management","Universities","Eligibility Rules","Tuition Rules","Scholarship Rules","Applications","Application Samples"])
    st.subheader("University Management")
    st.caption("Add, edit, or update university information. New universities will appear on the Home and Universities pages. To appear in Eligibility, add at least one major in Eligibility Rules after adding the university.")

    uni_file = DATA / "universities.csv"
    df = read_csv(uni_file)
    required_cols = [
        "University","Location","Total_Students","International_Students","Top_Majors",
        "Intake","Application_Status","Application_Open_Date","Application_Close_Date",
        "UG_Open_Date","UG_Close_Date","UG_New_Open_Date","UG_New_Close_Date","UG_Transfer_Open_Date","UG_Transfer_Close_Date","Graduate_Open_Date","Graduate_Close_Date","KLP_EAP_Open_Date","KLP_EAP_Close_Date","KLP_Open_Date","KLP_Close_Date","EAP_Open_Date","EAP_Close_Date",
        "Tuition_Range","Scholarship_Info","Overview","Image","Image_Gallery","University_Logo",
        "Homepage","Language_School_Homepage","Promotional_Materials","Facebook_Link","Instagram_Link","YouTube_Link","SNS_Information","Student_Data_Year","Undergraduate_Students","Graduate_Students","Language_Study_Students","Nationality_Students_JSON","Address","Representative_Phone","Representative_Fax","Region","School_Size","Accreditation_Status","Accreditation_Until","IEQAS_Badge_Image","IEQAS_Badge_Image_Data"
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
                accreditation_status = st.selectbox("Accreditation", ["Excellent accredited", "Accredited", "Non accredited"], key="add_accreditation_status_v168")
                acc_y1, acc_y2 = st.columns(2)
                with acc_y1:
                    accreditation_year = st.selectbox("Accreditation Until Year", [""] + [str(y) for y in range(datetime.now().year, datetime.now().year + 15)], key="add_accreditation_year_v168")
                with acc_y2:
                    accreditation_month = st.selectbox("Accreditation Until Month", [""] + [f"{m:02d}" for m in range(1, 13)], key="add_accreditation_month_v168")
                ieqas_badge_upload = st.file_uploader(
                    "Upload IEQAS Badge Image (optional)",
                    type=["png", "jpg", "jpeg", "webp"],
                    key="add_ieqas_badge_upload_v175",
                    help="Upload the official IEQAS badge image for this university. It will be shown beside the university name."
                )
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
                    ieqas_badge_path_v175 = save_uploaded_ieqas_badge_v175(ieqas_badge_upload, university)
                    ieqas_badge_data_v179 = save_uploaded_ieqas_badge_data_v179(ieqas_badge_upload)
                    student_stats_v106 = parse_student_stats_excel_v106(student_stats_excel)
                    calculated_application_status = _auto_application_status_v65(application_open_date, application_close_date, application_status)
                    new_row = {
                        "University": university.strip(),
                        "Location": location.strip(),
                        "Total_Students": school_size.strip(),
                        "International_Students": intl_students.strip(),
                        "Accreditation_Status": accreditation_status,
                        "Accreditation_Until": f"{accreditation_year}-{accreditation_month}" if accreditation_year and accreditation_month else "",
                        "IEQAS_Badge_Image": ieqas_badge_path_v175,
                        "IEQAS_Badge_Image_Data": ieqas_badge_data_v179,
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

            st.markdown("#### IEQAS Badge Image")
            st.info("IEQAS upload option was removed. The badge is now controlled by a fixed image file in the GitHub project: assets/ieqas_badges/kyungsung_university_ieqas_badge.png")
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
                    acc_options_v168 = ["Excellent accredited", "Accredited", "Non accredited"]
                    current_acc_v168 = display_clean_v50(row.get("Accreditation_Status", "")) or "Non accredited"
                    if current_acc_v168 not in acc_options_v168:
                        current_acc_v168 = "Non accredited"
                    accreditation_status = st.selectbox("Accreditation", acc_options_v168, index=acc_options_v168.index(current_acc_v168), key=f"edit_accreditation_status_v168_{selected_key_v90}")
                    acc_until_v168 = display_clean_v50(row.get("Accreditation_Until", ""))
                    acc_year_default_v168 = acc_until_v168.split("-")[0] if "-" in acc_until_v168 else ""
                    acc_month_default_v168 = acc_until_v168.split("-")[1] if "-" in acc_until_v168 else ""
                    acc_year_options_v168 = [""] + [str(y) for y in range(datetime.now().year - 5, datetime.now().year + 15)]
                    acc_month_options_v168 = [""] + [f"{m:02d}" for m in range(1, 13)]
                    acc_y1, acc_y2 = st.columns(2)
                    with acc_y1:
                        accreditation_year = st.selectbox("Accreditation Until Year", acc_year_options_v168, index=acc_year_options_v168.index(acc_year_default_v168) if acc_year_default_v168 in acc_year_options_v168 else 0, key=f"edit_accreditation_year_v168_{selected_key_v90}")
                    with acc_y2:
                        accreditation_month = st.selectbox("Accreditation Until Month", acc_month_options_v168, index=acc_month_options_v168.index(acc_month_default_v168) if acc_month_default_v168 in acc_month_options_v168 else 0, key=f"edit_accreditation_month_v168_{selected_key_v90}")
                    st.caption("IEQAS badge upload field removed in v182. Use the direct file path: assets/ieqas_badges/kyungsung_university_ieqas_badge.png")
                    ieqas_badge_upload = None
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
                    df.loc[idx, "Accreditation_Status"] = accreditation_status
                    df.loc[idx, "Accreditation_Until"] = f"{accreditation_year}-{accreditation_month}" if accreditation_year and accreditation_month else ""
                    if "IEQAS_Badge_Image" not in df.columns:
                        df["IEQAS_Badge_Image"] = ""
                    if "IEQAS_Badge_Image_Data" not in df.columns:
                        df["IEQAS_Badge_Image_Data"] = ""
                    if ieqas_badge_upload is not None:
                        saved_ieqas_v177 = save_uploaded_ieqas_badge_v175(ieqas_badge_upload, university)
                        saved_ieqas_data_v179 = save_ieqas_badge_for_university_v181(university, ieqas_badge_upload)
                        if saved_ieqas_v177:
                            df.loc[idx, "IEQAS_Badge_Image"] = saved_ieqas_v177
                        if saved_ieqas_data_v179:
                            df.loc[idx, "IEQAS_Badge_Image_Data"] = saved_ieqas_data_v179
                            st.session_state.setdefault("ieqas_badge_preview_data_v180", {})[safe_slug_v49(university)] = saved_ieqas_data_v179
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
    dash_shell(["Admin Dashboard","Partner Management","Universities","Eligibility Rules","Tuition Rules","Scholarship Rules","Applications","Application Samples"])
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
    dash_shell(["Admin Dashboard","Partner Management","Universities","Eligibility Rules","Tuition Rules","Scholarship Rules","Applications","Application Samples"])
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




def admin_application_samples_v114():
    dash_shell(["Admin Dashboard","Partner Management","Universities","Eligibility Rules","Tuition Rules","Scholarship Rules","Applications","Application Samples"])
    st.subheader("Application Document Sample Management")
    st.caption("First choose the application program type. Then choose nationality and upload all sample images for that program/country.")

    if "sample_program_page_v115" not in st.session_state:
        st.session_state.sample_program_page_v115 = ""

    if not st.session_state.sample_program_page_v115:
        st.markdown("""
        <div class="admin-university-tabs-note-v104 sample-intro-v115">
            <b>Choose Application Type</b>
            <span>Select one category below. Each category has its own nationality-based sample document settings.</span>
        </div>
        """, unsafe_allow_html=True)

        c1, c2, c3 = st.columns(3)
        with c1:
            if st.button("Undergraduate", key="sample_choose_undergraduate_v115", use_container_width=True):
                st.session_state.sample_program_page_v115 = "Undergraduate"
                st.rerun()
        with c2:
            if st.button("Graduate", key="sample_choose_graduate_v115", use_container_width=True):
                st.session_state.sample_program_page_v115 = "Graduate"
                st.rerun()
        with c3:
            if st.button("Language (EAP/KLP)", key="sample_choose_language_v115", use_container_width=True):
                st.session_state.sample_program_page_v115 = "Language"
                st.rerun()

        st.markdown("""
        <div class="sample-program-grid-v115">
            <div class="sample-program-card-v115"><h3>Undergraduate</h3><p>Sample documents for undergraduate new/transfer applicants.</p></div>
            <div class="sample-program-card-v115"><h3>Graduate</h3><p>Sample documents for master’s and Ph.D. applicants.</p></div>
            <div class="sample-program-card-v115"><h3>Language (EAP/KLP)</h3><p>Sample documents for language program applicants.</p></div>
        </div>
        """, unsafe_allow_html=True)

        close_shell()
        return

    selected_program = st.session_state.sample_program_page_v115
    display_program = "Language (EAP/KLP)" if selected_program == "Language" else selected_program

    b1, b2 = st.columns([1, 6])
    with b1:
        if st.button("← Back", key="sample_back_v115", use_container_width=True):
            st.session_state.sample_program_page_v115 = ""
            st.rerun()
    with b2:
        st.markdown(f"### {display_program} Sample Images")

    df = read_application_samples_v114()

    st.markdown(f"""
    <div class="admin-university-tabs-note-v104">
        <b>{_safe_html_v62(display_program)} Sample Setup</b>
        <span>Choose nationality once, then upload sample images for each required document below. These samples will appear automatically for applicants from that nationality and selected program category.</span>
    </div>
    """, unsafe_allow_html=True)

    nationality = st.selectbox("Choose Nationality", nationality_options_v112(), key=f"sample_nationality_bulk_v115_{selected_program}")

    st.markdown("#### Upload sample images for this nationality")
    st.caption("You do not need to upload all samples at once. Upload only the samples you want to update, then click Save All Sample Images.")

    uploads = {}
    existing_preview_items = []

    for label, doc_key, file_types, instruction in APPLICATION_DOC_TYPES_V114:
        current_path = get_application_sample_path_v114(nationality, selected_program, doc_key)
        existing_preview_items.append((label, doc_key, current_path))

        st.markdown(f'<div class="doc-upload-row-title-v114">{_safe_html_v62(label)}</div>', unsafe_allow_html=True)
        c_upload, c_preview = st.columns([1.15, .85])
        with c_upload:
            uploads[doc_key] = st.file_uploader(
                f"Upload sample image for {label}",
                type=["png", "jpg", "jpeg", "webp"],
                key=f"bulk_sample_upload_v115_{safe_slug_v49(selected_program)}_{safe_slug_v49(nationality)}_{safe_slug_v49(doc_key)}"
            )
            st.caption("Sample image only. PNG/JPG/WEBP recommended.")
        with c_preview:
            st.markdown(sample_preview_html_v114(current_path, label), unsafe_allow_html=True)

    if st.button("Save All Sample Images", key=f"save_bulk_samples_v115_{safe_slug_v49(selected_program)}_{safe_slug_v49(nationality)}", use_container_width=True):
        saved_count = 0
        for label, doc_key, file_types, instruction in APPLICATION_DOC_TYPES_V114:
            uploaded_sample = uploads.get(doc_key)
            if uploaded_sample is None:
                continue

            sample_path = save_application_sample_v114(uploaded_sample, nationality, selected_program, doc_key)
            mask = (
                (df["Nationality"].astype(str).str.strip().str.lower() == str(nationality).strip().lower())
                & (df["Program_Category"].astype(str).str.strip().str.lower() == str(selected_program).strip().lower())
                & (df["Document_Key"].astype(str).str.strip().str.lower() == str(doc_key).strip().lower())
            )
            new_row = {
                "Nationality": nationality,
                "Program_Category": selected_program,
                "Document_Key": doc_key,
                "Document_Label": label,
                "Sample_Path": sample_path,
                "Updated_At": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            }
            if len(df) and mask.any():
                for k, v in new_row.items():
                    df.loc[mask, k] = v
            else:
                df = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)
            saved_count += 1

        if saved_count == 0:
            st.warning("No new sample image was selected. Please upload at least one sample image.")
        else:
            write_application_samples_v114(df)
            st.success(f"{saved_count} sample image(s) saved for {nationality} · {display_program}.")
            st.rerun()

    st.markdown("### Current Saved Samples")
    current = df[
        (df["Program_Category"].astype(str).str.strip().str.lower() == str(selected_program).strip().lower())
        & (df["Nationality"].astype(str).str.strip().str.lower() == str(nationality).strip().lower())
    ].copy() if len(df) else pd.DataFrame()

    if len(current) == 0:
        st.info(f"No saved samples yet for {nationality} · {display_program}.")
    else:
        st.dataframe(clean_df_v50(current), use_container_width=True, hide_index=True)

    close_shell()



# v125 Super Admin Application Management
def admin_app_program_category_v125(row):
    val = display_clean_v50(row.get("Program_Category", "")) or display_clean_v50(row.get("Application_Type", ""))
    label = application_program_label_v114(val, row.get("Application_Type", ""))
    if label == "Language":
        return "Language"
    return label

def admin_apps_visible_df_v125():
    df = applications_df_v116()
    if len(df) == 0:
        return df
    return dedupe_application_rows_v119(df)

def admin_app_logo_html_v125(uni_name):
    uni_row = university_row_by_name_v120(uni_name)
    return university_logo_html_v88(uni_row.get("University_Logo", ""), uni_name or "University")

def application_form_pdf_bytes_v125(row):
    """
    v127: Generate a real downloadable PDF application form.
    Includes:
    - Applicant step 1 information
    - Self introduction and study plan
    - Submitted agency/staff information
    - Passport size photo from Step 2, when uploaded
    """
    def _val(key, default="-"):
        v = display_clean_v50(row.get(key, ""))
        return v if v else default

    def _doc_path_from_row(doc_key):
        try:
            docs = parse_document_paths_v125(row)
            rel = docs.get(doc_key, "")
            p = resolve_uploaded_doc_path_v126(rel)
            return p
        except Exception:
            return None

    try:
        from reportlab.lib import colors
        from reportlab.lib.pagesizes import A4
        from reportlab.lib.units import mm
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.platypus import (
            SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
            Image as RLImage, PageBreak
        )
        from reportlab.lib.enums import TA_CENTER
        import io

        buffer = io.BytesIO()
        doc = SimpleDocTemplate(
            buffer,
            pagesize=A4,
            rightMargin=18 * mm,
            leftMargin=18 * mm,
            topMargin=16 * mm,
            bottomMargin=16 * mm,
            title="Student Application Form"
        )

        styles = getSampleStyleSheet()
        styles.add(ParagraphStyle(
            name="AppTitle",
            parent=styles["Title"],
            fontName="Helvetica-Bold",
            fontSize=20,
            leading=24,
            textColor=colors.HexColor("#002B5B"),
            alignment=TA_CENTER,
            spaceAfter=8,
        ))
        styles.add(ParagraphStyle(
            name="SectionTitle",
            parent=styles["Heading2"],
            fontName="Helvetica-Bold",
            fontSize=12,
            leading=15,
            textColor=colors.HexColor("#005BDB"),
            spaceBefore=10,
            spaceAfter=6,
        ))
        styles.add(ParagraphStyle(
            name="SmallText",
            parent=styles["BodyText"],
            fontSize=8.5,
            leading=11,
            textColor=colors.HexColor("#475467"),
        ))
        styles.add(ParagraphStyle(
            name="BodySmall",
            parent=styles["BodyText"],
            fontSize=9,
            leading=12,
            textColor=colors.HexColor("#111827"),
        ))

        story = []
        story.append(Paragraph("Student Application Form", styles["AppTitle"]))
        story.append(Paragraph(
            f"Generated on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            styles["SmallText"]
        ))
        story.append(Spacer(1, 6))

        # Header with photo
        photo_path = _doc_path_from_row("passport_size_photo")
        photo_cell = Paragraph("Passport<br/>Photo", styles["SmallText"])
        if photo_path and photo_path.exists():
            try:
                photo_cell = RLImage(str(photo_path), width=32 * mm, height=40 * mm)
            except Exception:
                photo_cell = Paragraph("Passport photo<br/>uploaded", styles["SmallText"])

        header_data = [
            [
                photo_cell,
                Table([
                    ["Applicant Name", _val("Full_Name_As_Passport")],
                    ["University", _val("University")],
                    ["Application Type", _val("Application_Type")],
                    ["Desired Major / Program", _val("Desired_Major")],
                    ["Status", inferred_application_status_v119(row)],
                ], colWidths=[42 * mm, 100 * mm])
            ]
        ]
        header_table = Table(header_data, colWidths=[38 * mm, 136 * mm])
        header_table.setStyle(TableStyle([
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("BOX", (0, 0), (-1, -1), 0.7, colors.HexColor("#DCE6F4")),
            ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#F8FAFC")),
            ("INNERGRID", (1, 0), (1, 0), 0.25, colors.HexColor("#E5E7EB")),
            ("FONTNAME", (0, 0), (-1, -1), "Helvetica"),
            ("FONTSIZE", (0, 0), (-1, -1), 9),
            ("LEFTPADDING", (0, 0), (-1, -1), 8),
            ("RIGHTPADDING", (0, 0), (-1, -1), 8),
            ("TOPPADDING", (0, 0), (-1, -1), 8),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
        ]))
        story.append(header_table)

        def add_section(title, rows):
            story.append(Paragraph(title, styles["SectionTitle"]))
            table_data = []
            for label, key in rows:
                table_data.append([
                    Paragraph(f"<b>{label}</b>", styles["BodySmall"]),
                    Paragraph(_safe_html_v62(_val(key)), styles["BodySmall"])
                ])
            t = Table(table_data, colWidths=[55 * mm, 119 * mm])
            t.setStyle(TableStyle([
                ("BOX", (0, 0), (-1, -1), 0.6, colors.HexColor("#DCE6F4")),
                ("INNERGRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#E5E7EB")),
                ("BACKGROUND", (0, 0), (0, -1), colors.HexColor("#EEF5FF")),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 6),
                ("RIGHTPADDING", (0, 0), (-1, -1), 6),
                ("TOPPADDING", (0, 0), (-1, -1), 5),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
            ]))
            story.append(t)

        add_section("1. Personal Information", [
            ("Full Name as in Passport", "Full_Name_As_Passport"),
            ("First Name", "First_Name"),
            ("Middle Name", "Middle_Name"),
            ("Last Name", "Last_Name"),
            ("Passport Number", "Passport_Number"),
            ("Passport Issue Year", "Passport_Issue_Year"),
            ("Nationality", "Nationality"),
            ("Date of Birth", "Date_of_Birth"),
            ("Applicant Contact Number", "Applicant_Contact"),
            ("Email Address", "Email"),
            ("Parents Full Name", "Parents_Full_Name"),
            ("Parents / Guardian Contact", "Guardian_Contact"),
            ("Home Country Address", "Home_Country_Address"),
        ])

        add_section("2. Intended Study Information", [
            ("University", "University"),
            ("Program Category", "Program_Category"),
            ("Application Type", "Application_Type"),
            ("Desired Major / Program", "Desired_Major"),
        ])

        add_section("3. Academic Background", [
            ("High School Name", "High_School_Name"),
            ("High School Passout Year", "High_School_Passout_Year"),
            ("High School Enroll Start", "High_School_Enroll_Start"),
            ("High School Enroll End", "High_School_Enroll_End"),
            ("High School Location", "High_School_Location"),
            ("Middle School Name", "Middle_School_Name"),
            ("Middle School Enrolled Year", "Middle_School_Enrolled_Year"),
            ("Middle School Location", "Middle_School_Location"),
        ])

        add_section("4. Financial Information", [
            ("Bank Certificate Owner", "Bank_Certificate_Owner"),
            ("Bank Amount in USD", "Bank_Amount_USD"),
        ])

        add_section("5. Submission Information", [
            ("Submitted By", "Submitted_By"),
            ("Agency", "Agency"),
            ("Submitted At", "Submitted_At"),
            ("Last Updated", "Last_Updated"),
            ("Application ID", "Application_ID"),
        ])

        story.append(Paragraph("6. Self Introduction", styles["SectionTitle"]))
        story.append(Table([[Paragraph(_safe_html_v62(_val("Self_Introduction")), styles["BodySmall"])]],
                           colWidths=[174 * mm],
                           style=TableStyle([
                               ("BOX", (0,0), (-1,-1), 0.6, colors.HexColor("#DCE6F4")),
                               ("BACKGROUND", (0,0), (-1,-1), colors.white),
                               ("LEFTPADDING", (0,0), (-1,-1), 8),
                               ("RIGHTPADDING", (0,0), (-1,-1), 8),
                               ("TOPPADDING", (0,0), (-1,-1), 8),
                               ("BOTTOMPADDING", (0,0), (-1,-1), 8),
                           ])))

        story.append(Paragraph("7. Study Plan", styles["SectionTitle"]))
        story.append(Table([[Paragraph(_safe_html_v62(_val("Study_Plan")), styles["BodySmall"])]],
                           colWidths=[174 * mm],
                           style=TableStyle([
                               ("BOX", (0,0), (-1,-1), 0.6, colors.HexColor("#DCE6F4")),
                               ("BACKGROUND", (0,0), (-1,-1), colors.white),
                               ("LEFTPADDING", (0,0), (-1,-1), 8),
                               ("RIGHTPADDING", (0,0), (-1,-1), 8),
                               ("TOPPADDING", (0,0), (-1,-1), 8),
                               ("BOTTOMPADDING", (0,0), (-1,-1), 8),
                           ])))

        docs = parse_document_paths_v125(row)
        if docs:
            story.append(Paragraph("8. Uploaded Document Checklist", styles["SectionTitle"]))
            checklist = []
            label_map = {doc_key: label for label, doc_key, _, _ in APPLICATION_DOC_TYPES_V114}
            for doc_key, rel_path in docs.items():
                p = resolve_uploaded_doc_path_v126(rel_path)
                checklist.append([
                    Paragraph(f"<b>{label_map.get(doc_key, doc_key.replace('_',' ').title())}</b>", styles["BodySmall"]),
                    Paragraph("Uploaded" if p else "Saved path not found", styles["BodySmall"]),
                    Paragraph(Path(str(rel_path)).name, styles["SmallText"]),
                ])
            t = Table(checklist, colWidths=[70 * mm, 35 * mm, 69 * mm])
            t.setStyle(TableStyle([
                ("BOX", (0,0), (-1,-1), 0.6, colors.HexColor("#DCE6F4")),
                ("INNERGRID", (0,0), (-1,-1), 0.25, colors.HexColor("#E5E7EB")),
                ("BACKGROUND", (0,0), (0,-1), colors.HexColor("#F8FAFC")),
                ("VALIGN", (0,0), (-1,-1), "TOP"),
                ("LEFTPADDING", (0,0), (-1,-1), 6),
                ("RIGHTPADDING", (0,0), (-1,-1), 6),
                ("TOPPADDING", (0,0), (-1,-1), 5),
                ("BOTTOMPADDING", (0,0), (-1,-1), 5),
            ]))
            story.append(t)

        doc.build(story)
        return buffer.getvalue()

    except Exception as e:
        # Last-resort valid basic PDF fallback using reportlab may not be installed yet.
        # This fallback creates a readable plain-text PDF using minimal PDF syntax.
        text_lines = [
            "Student Application Form",
            f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            "",
            f"Applicant: {_val('Full_Name_As_Passport')}",
            f"University: {_val('University')}",
            f"Application Type: {_val('Application_Type')}",
            f"Desired Major: {_val('Desired_Major')}",
            f"Passport Number: {_val('Passport_Number')}",
            f"Nationality: {_val('Nationality')}",
            f"Email: {_val('Email')}",
            f"Contact: {_val('Applicant_Contact')}",
            "",
            "Self Introduction:",
            _val("Self_Introduction"),
            "",
            "Study Plan:",
            _val("Study_Plan"),
            "",
            f"PDF generation note: {str(e)[:120]}",
        ]
        # Escape PDF characters
        def esc(s):
            return str(s).replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")
        content = "BT /F1 10 Tf 50 800 Td "
        y_count = 0
        for line in text_lines:
            parts = [line[i:i+85] for i in range(0, len(str(line)), 85)] or [""]
            for part in parts:
                if y_count > 55:
                    break
                content += f"({esc(part)}) Tj 0 -14 Td "
                y_count += 1
        content += "ET"
        objects = []
        objects.append("1 0 obj << /Type /Catalog /Pages 2 0 R >> endobj")
        objects.append("2 0 obj << /Type /Pages /Kids [3 0 R] /Count 1 >> endobj")
        objects.append("3 0 obj << /Type /Page /Parent 2 0 R /MediaBox [0 0 595 842] /Resources << /Font << /F1 4 0 R >> >> /Contents 5 0 R >> endobj")
        objects.append("4 0 obj << /Type /Font /Subtype /Type1 /BaseFont /Helvetica >> endobj")
        objects.append(f"5 0 obj << /Length {len(content.encode('latin-1', 'ignore'))} >> stream\n{content}\nendstream endobj")
        pdf = "%PDF-1.4\n"
        offsets = [0]
        for obj in objects:
            offsets.append(len(pdf.encode("latin-1")))
            pdf += obj + "\n"
        xref_pos = len(pdf.encode("latin-1"))
        pdf += f"xref\n0 {len(objects)+1}\n0000000000 65535 f \n"
        for off in offsets[1:]:
            pdf += f"{off:010d} 00000 n \n"
        pdf += f"trailer << /Size {len(objects)+1} /Root 1 0 R >>\nstartxref\n{xref_pos}\n%%EOF"
        return pdf.encode("latin-1", "ignore")

def parse_document_paths_v125(row):
    raw = row.get("Document_Paths_JSON", "")
    if raw is None:
        return {}
    raw = str(raw).strip()
    if not raw or raw.lower() in ["nan", "none", "null", "<na>", "{}", "[]"]:
        return {}
    try:
        data = json.loads(raw)
        if isinstance(data, dict):
            return {str(k): str(v) for k, v in data.items() if str(v).strip()}
    except Exception:
        pass
    # fallback for older/dirty CSV rows where quotes may have been changed
    try:
        import ast
        data = ast.literal_eval(raw)
        if isinstance(data, dict):
            return {str(k): str(v) for k, v in data.items() if str(v).strip()}
    except Exception:
        pass
    return {}

def resolve_uploaded_doc_path_v126(rel_path):
    if not rel_path:
        return None
    raw = str(rel_path).strip().replace("\\", "/")
    candidates = []
    p = Path(raw)
    if p.is_absolute():
        candidates.append(p)
    candidates.extend([
        BASE / raw,
        Path.cwd() / raw,
        DATA.parent / raw,
        BASE / "assets" / "application_documents" / Path(raw).name,
        BASE / "assets" / Path(raw).name,
    ])
    for c in candidates:
        try:
            if c.exists() and c.is_file():
                return c
        except Exception:
            pass
    return None

def admin_download_document_button_v125(doc_key, rel_path, idx):
    label = doc_key.replace("_", " ").title()
    path = resolve_uploaded_doc_path_v126(rel_path)
    if path is None:
        st.markdown(f"""
        <div class="admin-doc-missing-v132">
            <div class="admin-doc-icon-v132">⚠️</div>
            <div>
                <b>{_safe_html_v62(label)}</b>
                <span>Uploaded file is missing. Please ask the applicant or agency to upload this document again.</span>
            </div>
        </div>
        """, unsafe_allow_html=True)
        return

    data = path.read_bytes()
    name = path.name
    mime = "application/octet-stream"
    if path.suffix.lower() == ".pdf":
        mime = "application/pdf"
    elif path.suffix.lower() in [".jpg", ".jpeg"]:
        mime = "image/jpeg"
    elif path.suffix.lower() == ".png":
        mime = "image/png"

    st.markdown(f"""
    <div class="admin-doc-card-v132">
        <div class="admin-doc-icon-v132">📄</div>
        <div>
            <b>{_safe_html_v62(label)}</b>
            <span>Uploaded document available</span>
        </div>
    </div>
    """, unsafe_allow_html=True)
    st.download_button(
        f"Download {label}",
        data=data,
        file_name=name,
        mime=mime,
        key=f"download_doc_v126_{idx}_{safe_slug_v49(doc_key)}",
        use_container_width=True
    )


def application_packet_zip_bytes_v127(row):
    """Create a zip containing the generated application form PDF and every uploaded document."""
    import io, zipfile
    applicant = safe_slug_v49(application_display_name_v116(row) or "applicant")
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr(f"{applicant}_application_form.pdf", application_form_pdf_bytes_v125(row))
        docs = parse_document_paths_v125(row)
        label_map = {doc_key: label for label, doc_key, _, _ in APPLICATION_DOC_TYPES_V114}
        for doc_key, rel_path in docs.items():
            p = resolve_uploaded_doc_path_v126(rel_path)
            if p and p.exists():
                label = safe_slug_v49(label_map.get(doc_key, doc_key))
                z.write(p, arcname=f"uploaded_documents/{label}{p.suffix.lower()}")
            else:
                z.writestr(f"missing_files/{safe_slug_v49(doc_key)}.txt", f"Saved path not found:\n{rel_path}")
    buffer.seek(0)
    return buffer.getvalue()


# v129 Email notification helpers
def get_secret_or_env_v129(*keys, default=""):
    for key in keys:
        try:
            val = st.secrets.get(key, "")
            if val:
                return str(val)
        except Exception:
            pass
        val = os.getenv(key, "")
        if val:
            return str(val)
    return default

def notification_sender_email_v129():
    return get_secret_or_env_v129(
        "SMTP_SENDER_EMAIL",
        "SUPER_ADMIN_EMAIL",
        "GMAIL_USER",
        "EMAIL_USER",
        default="uniqueststudy@gmail.com"
    )

def notification_sender_password_v129():
    return get_secret_or_env_v129(
        "SMTP_APP_PASSWORD",
        "GMAIL_APP_PASSWORD",
        "EMAIL_APP_PASSWORD",
        "SMTP_PASSWORD",
        default=""
    )

def find_registered_email_for_username_v129(username):
    username = str(username or "").strip().lower()
    if not username:
        return ""
    try:
        for u in read_json(USERS):
            if str(u.get("username", "")).strip().lower() == username:
                for key in ["email", "Email", "email_address", "Email Address"]:
                    if display_clean_v50(u.get(key, "")):
                        return display_clean_v50(u.get(key, ""))
    except Exception:
        pass
    return ""

def application_notification_recipients_v129(row):
    recipients = []
    submitter_email = find_registered_email_for_username_v129(row.get("Submitted_By", ""))
    if submitter_email:
        recipients.append(submitter_email)

    # If submitter email is not found, fallback to the applicant email so the notification is not lost.
    applicant_email = display_clean_v50(row.get("Email", ""))
    if applicant_email and applicant_email not in recipients:
        recipients.append(applicant_email)

    # Optional: allow notification to agency-level email if stored in agencies data.
    try:
        agency_name = display_clean_v50(row.get("Agency", ""))
        for a in read_agencies():
            if str(a.get("agency_name", "")).strip().lower() == agency_name.strip().lower():
                for key in ["email", "Email", "official_email", "contact_email"]:
                    e = display_clean_v50(a.get(key, ""))
                    if e and e not in recipients:
                        recipients.append(e)
    except Exception:
        pass

    return recipients

def send_email_notification_v129(to_emails, subject, body):
    to_emails = [e for e in to_emails if str(e).strip()]
    if not to_emails:
        return False, "No recipient email found."

    sender = notification_sender_email_v129()
    password = notification_sender_password_v129()

    if not password:
        return False, (
            "SMTP app password is not configured. Add SMTP_APP_PASSWORD or GMAIL_APP_PASSWORD "
            "in Streamlit Secrets. Sender email currently set to "
            f"{sender}."
        )

    try:
        msg = MIMEMultipart()
        msg["From"] = sender
        msg["To"] = ", ".join(to_emails)
        msg["Subject"] = subject
        msg.attach(MIMEText(body, "plain", "utf-8"))

        smtp_server = get_secret_or_env_v129("SMTP_SERVER", default="smtp.gmail.com")
        smtp_port = int(get_secret_or_env_v129("SMTP_PORT", default="587"))

        context = ssl.create_default_context()
        with smtplib.SMTP(smtp_server, smtp_port) as server:
            server.starttls(context=context)
            server.login(sender, password)
            server.sendmail(sender, to_emails, msg.as_string())

        return True, f"Email sent to {', '.join(to_emails)}."
    except Exception as e:
        return False, f"Email could not be sent: {e}"

def build_status_notifications_v129(old_row, updates):
    applicant = application_display_name_v116(old_row)
    university = display_clean_v50(old_row.get("University", ""))
    major = display_clean_v50(old_row.get("Desired_Major", ""))
    notifications = []

    def changed_to_value(key):
        old = display_clean_v50(old_row.get(key, ""))
        new = display_clean_v50(updates.get(key, ""))
        return bool(new) and old != new

    if changed_to_value("University_Received"):
        notifications.append((
            "University received the application",
            f"""Dear Partner,

The university has received the application.

Applicant: {applicant}
University: {university}
Major/Program: {major}
Status: University received the application
Update: {display_clean_v50(updates.get("University_Received", ""))}

Please check the portal for full details.

Partner Portal"""
        ))

    if changed_to_value("Application_Number"):
        notifications.append((
            "Application number issued",
            f"""Dear Partner,

An application number has been issued.

Applicant: {applicant}
University: {university}
Major/Program: {major}
Application Number: {display_clean_v50(updates.get("Application_Number", ""))}

Please check the portal for full details.

Partner Portal"""
        ))

    if changed_to_value("Interview_Date"):
        notifications.append((
            "Interview date announced",
            f"""Dear Partner,

The interview date has been announced.

Applicant: {applicant}
University: {university}
Major/Program: {major}
Interview Date/Time: {display_clean_v50(updates.get("Interview_Date", ""))}

Please check the portal and inform the applicant.

Partner Portal"""
        ))

    if changed_to_value("Interview_Result"):
        result = display_clean_v50(updates.get("Interview_Result", ""))
        if result.lower() == "passed":
            headline = "Interview result: Passed"
            message_line = "Congratulations. The applicant has passed the interview."
        elif result.lower() == "failed":
            headline = "Interview result: Failed"
            message_line = "Sorry. The applicant has not been selected."
        else:
            headline = f"Interview result: {result}"
            message_line = f"The interview result has been updated to {result}."

        notifications.append((
            headline,
            f"""Dear Partner,

{message_line}

Applicant: {applicant}
University: {university}
Major/Program: {major}
Interview Result: {result}

Please check the portal for full details.

Partner Portal"""
        ))

    if changed_to_value("Offer_Invoice_Issued"):
        notifications.append((
            "Offer letter and invoice issued",
            f"""Dear Partner,

The offer letter and invoice status has been updated.

Applicant: {applicant}
University: {university}
Major/Program: {major}
Update: {display_clean_v50(updates.get("Offer_Invoice_Issued", ""))}

Please check the portal for full details.

Partner Portal"""
        ))

    if changed_to_value("COA_Issued"):
        notifications.append((
            "COA issued",
            f"""Dear Partner,

The COA status has been updated.

Applicant: {applicant}
University: {university}
Major/Program: {major}
Update: {display_clean_v50(updates.get("COA_Issued", ""))}

Please check the portal for full details.

Partner Portal"""
        ))

    if changed_to_value("Visa_Application_Number"):
        notifications.append((
            "Visa application number issued",
            f"""Dear Partner,

The visa application number has been issued.

Applicant: {applicant}
University: {university}
Major/Program: {major}
Visa Application Number: {display_clean_v50(updates.get("Visa_Application_Number", ""))}

Please check the portal for full details.

Partner Portal"""
        ))

    if changed_to_value("Visa_Result"):
        result = display_clean_v50(updates.get("Visa_Result", ""))
        if result.lower() == "issued":
            headline = "Visa result: Issued"
            message_line = "Congratulations. The applicant's visa has been issued."
        elif result.lower() == "rejected":
            headline = "Visa result: Rejected"
            message_line = "Sorry. The applicant's visa has been rejected."
        else:
            headline = f"Visa result: {result}"
            message_line = f"The visa result has been updated to {result}."

        notifications.append((
            headline,
            f"""Dear Partner,

{message_line}

Applicant: {applicant}
University: {university}
Major/Program: {major}
Visa Result: {result}

Please check the portal for full details.

Partner Portal"""
        ))

    return notifications

def send_status_update_notifications_v129(old_row, updates):
    recipients = application_notification_recipients_v129(old_row)
    notifications = build_status_notifications_v129(old_row, updates)

    if not notifications:
        return []

    results = []
    for subject, body in notifications:
        ok, msg = send_email_notification_v129(recipients, subject, body)
        results.append((ok, subject, msg))
    return results


def update_application_status_from_admin_v125(app_id, updates):
    df = applications_df_v116()
    if len(df) == 0:
        return False
    mask = df["Application_ID"].astype(str).str.strip() == str(app_id).strip()
    if not mask.any():
        return False
    for k, v in updates.items():
        if k not in df.columns:
            df[k] = ""
        df.loc[mask, k] = v
    df.loc[mask, "Last_Updated"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    write_applications_df_v116(df)
    return True



def country_flag_html_v138(country_name, size=44):
    """
    v140: Real country flag image renderer.
    Nepal is rendered as an inline SVG so it shows the real non-rectangular Nepal flag,
    not an emoji or NP abbreviation. Other countries use FlagCDN with object-fit: contain.
    """
    country = str(country_name or "").strip().lower()
    country = country.replace("republic of korea", "south korea").replace("korea, republic of", "south korea")
    label = _safe_html_v62(country_name or "Nationality")

    # Accurate enough UI SVG for Nepal's unique double-pennon flag shape.
    # It is inline, so it works directly after uploading to GitHub/Streamlit.
    if country in ["nepal", "nepali"]:
        nepal_svg = """
        <svg viewBox="0 0 820 1000" xmlns="http://www.w3.org/2000/svg" aria-label="Nepal flag">
          <path d="M60 60 L60 940 L650 940 L355 575 L650 575 Z" fill="#003893"/>
          <path d="M105 145 L105 840 L535 840 L260 500 L535 500 Z" fill="#DC143C"/>
          <circle cx="215" cy="375" r="65" fill="#fff"/>
          <circle cx="215" cy="345" r="70" fill="#DC143C"/>
          <g fill="#fff" transform="translate(215 385)">
            <polygon points="0,-75 14,-30 60,-52 34,-12 78,6 30,14 52,60 12,34 -6,78 -14,30 -60,52 -34,12 -78,-6 -30,-14 -52,-60 -12,-34"/>
          </g>
          <g fill="#fff" transform="translate(250 740)">
            <polygon points="0,-95 18,-38 76,-66 43,-15 99,8 38,18 66,76 15,43 -8,99 -18,38 -76,66 -43,15 -99,-8 -38,-18 -66,-76 -15,-43"/>
          </g>
        </svg>
        """
        return f'<span class="applicant-flag-v140 nepal-flag-v140" title="{label}">{nepal_svg}</span>'

    iso_map = {
        "bangladesh": "bd", "bangladeshi": "bd",
        "india": "in", "indian": "in",
        "pakistan": "pk", "pakistani": "pk",
        "vietnam": "vn", "viet nam": "vn", "vietnamese": "vn",
        "indonesia": "id", "indonesian": "id",
        "sri lanka": "lk", "sri lankan": "lk",
        "myanmar": "mm", "burma": "mm", "myanmarese": "mm",
        "china": "cn", "chinese": "cn",
        "mongolia": "mn", "mongolian": "mn",
        "uzbekistan": "uz", "uzbek": "uz",
        "kazakhstan": "kz", "kazakh": "kz",
        "kyrgyzstan": "kg", "kyrgyz": "kg",
        "thailand": "th", "thai": "th",
        "philippines": "ph", "filipino": "ph",
        "cambodia": "kh", "cambodian": "kh",
        "laos": "la", "lao": "la",
        "malaysia": "my", "malaysian": "my",
        "japan": "jp", "japanese": "jp",
        "south korea": "kr", "korea": "kr", "korean": "kr",
        "united states": "us", "usa": "us", "america": "us", "american": "us",
        "canada": "ca", "canadian": "ca",
        "australia": "au", "australian": "au",
        "united kingdom": "gb", "uk": "gb", "british": "gb",
        "france": "fr", "french": "fr",
        "germany": "de", "german": "de",
    }
    code = iso_map.get(country, "")
    if code:
        return (
            f'<span class="applicant-flag-v140 rectangle-flag-v140" title="{label}">'
            f'<img src="https://flagcdn.com/w160/{code}.png" alt="{label} flag">'
            f'</span>'
        )

    initials = "".join([p[:1].upper() for p in str(country_name or "NA").split()[:2]]) or "NA"
    return f'<span class="applicant-flag-v140 applicant-flag-fallback-v140" title="{label}">{_safe_html_v62(initials)}</span>'

def university_logo_compact_html_v138(uni_name):
    """Small clean university logo card for application detail header."""
    try:
        uni_row = university_row_by_name_v120(uni_name)
        logo_path = display_clean_v50(uni_row.get("University_Logo", ""))
        encoded = b64(logo_path)
        if encoded:
            return (
                '<div class="detail-university-logo-v138">'
                f'<img src="data:image/png;base64,{encoded}" alt="{_safe_html_v62(uni_name)} logo">'
                '</div>'
            )
    except Exception:
        pass
    initials = "".join([p[:1].upper() for p in str(uni_name or "U").split()[:2]]) or "U"
    return f'<div class="detail-university-logo-v138 logo-fallback-v138">{_safe_html_v62(initials)}</div>'


def applicant_photo_html_v134(row, applicant_name="", size=150):
    """Show applicant passport-size photo in admin application detail header."""
    try:
        docs = parse_document_paths_v125(row)
        photo_path = None
        for key in ["passport_size_photo", "passport_photo", "photo", "applicant_photo"]:
            if docs.get(key):
                photo_path = resolve_uploaded_doc_path_v126(docs.get(key))
                if photo_path:
                    break
        if photo_path and photo_path.exists():
            encoded = base64.b64encode(photo_path.read_bytes()).decode()
            return (
                f'<div class="applicant-photo-box-v134" style="width:{size}px;height:{size}px">'
                f'<img src="data:image/{photo_path.suffix.lower().replace(".","")};base64,{encoded}" '
                f'alt="{_safe_html_v62(applicant_name or "Applicant Photo")}">'
                f'</div>'
            )
    except Exception:
        pass

    initials = "".join([x[:1].upper() for x in str(applicant_name or "Applicant").split()[:2]]) or "AP"
    return (
        f'<div class="applicant-photo-box-v134 applicant-photo-fallback-v134" style="width:{size}px;height:{size}px">'
        f'<span>{_safe_html_v62(initials)}</span>'
        f'<small>No Photo</small>'
        f'</div>'
    )


def admin_application_detail_page_v125(app_id, render_shell=True):
    if render_shell:
        dash_shell(["Admin Dashboard","Partner Management","Universities","Eligibility Rules","Tuition Rules","Scholarship Rules","Applications","Application Samples"])
    if st.button("← Back to Applications", key="admin_app_detail_back_v125", use_container_width=False):
        st.session_state.admin_app_selected_id_v125 = ""
        st.session_state.admin_app_view_v125 = "program"
        st.rerun()

    df = applications_df_v116()
    match = df[df["Application_ID"].astype(str).str.strip() == str(app_id).strip()]
    if len(match) == 0:
        st.error("Application not found.")
        if render_shell:
            close_shell()
        return
    row = match.iloc[-1].to_dict()
    applicant = application_display_name_v116(row)
    uni = display_clean_v50(row.get("University", ""))
    major = display_clean_v50(row.get("Desired_Major", "")) or "Not selected"
    program_cat = admin_app_program_category_v125(row)
    status = inferred_application_status_v119(row)

    nationality_v138 = display_clean_v50(row.get("Nationality", ""))
    st.markdown(f"""
    <div class="admin-app-detail-hero-v131 admin-app-detail-hero-v138">
        <div class="admin-app-detail-logo-v131">{applicant_photo_html_v134(row, applicant, 260)}</div>
        <div class="admin-app-detail-main-v131">
            <div class="admin-app-detail-label-v131">Application Detail</div>
            <h1 class="applicant-name-with-flag-v138">{_safe_html_v62(applicant)} {country_flag_html_v138(nationality_v138, 44)}</h1>
            <div class="admin-app-detail-meta-v131">
                <span><b>University</b>{_safe_html_v62(uni)}</span>
                <span><b>Program</b>{_safe_html_v62(program_cat)}</span>
                <span><b>Major</b>{_safe_html_v62(major)}</span>
            </div>
        </div>
        <div class="admin-app-detail-right-v138">
            {university_logo_compact_html_v138(uni)}
            <div class="admin-app-detail-status-v131">
                {application_status_badge_v116(status)}
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    st.caption("Download the applicant's full application form generated from Step 1 information and Step 2 passport photo.")
    dcol1_v127, dcol2_v127 = st.columns(2)
    with dcol1_v127:
        st.download_button(
            "Download Application Form PDF",
            data=application_form_pdf_bytes_v125(row),
            file_name=f"{safe_slug_v49(applicant)}_application_form.pdf",
            mime="application/pdf",
            use_container_width=True,
            key=f"download_app_form_v127_{safe_slug_v49(app_id)}"
        )
    with dcol2_v127:
        st.download_button(
            "Download Full Application Packet ZIP",
            data=application_packet_zip_bytes_v127(row),
            file_name=f"{safe_slug_v49(applicant)}_application_packet.zip",
            mime="application/zip",
            use_container_width=True,
            key=f"download_app_packet_v127_{safe_slug_v49(app_id)}"
        )

    st.markdown("### Applicant Information")
    info_fields = [
        ("Full Name as in Passport", "Full_Name_As_Passport"),
        ("First Name", "First_Name"),
        ("Middle Name", "Middle_Name"),
        ("Last Name", "Last_Name"),
        ("Passport Number", "Passport_Number"),
        ("Nationality", "Nationality"),
        ("Date of Birth", "Date_of_Birth"),
        ("Email", "Email"),
        ("Contact Number", "Applicant_Contact"),
        ("Parents Full Name", "Parents_Full_Name"),
        ("Guardian Contact", "Guardian_Contact"),
        ("Home Country Address", "Home_Country_Address"),
        ("University", "University"),
        ("Application Type", "Application_Type"),
        ("Desired Major", "Desired_Major"),
        ("Submitted By", "Submitted_By"),
        ("Agency", "Agency"),
        ("Submitted At", "Submitted_At"),
    ]
    cards = "".join([
        '<div class="admin-app-info-card-v125">'
        f'<b>{_safe_html_v62(label)}</b>'
        f'<span>{_safe_html_v62(display_clean_v50(row.get(key, "")) or "-")}</span>'
        '</div>'
        for label, key in info_fields
    ])
    st.markdown('<div class="admin-app-info-grid-v125">' + cards + '</div>', unsafe_allow_html=True)

    st.markdown("### Academic / Financial / Statement Information")
    academic_html = (
        '<div class="admin-app-textbox-v125">'
        '<b>Academic Background</b>'
        f'<p><b>High School:</b> {_safe_html_v62(display_clean_v50(row.get("High_School_Name","")) or "-")}</p>'
        f'<p><b>Passout Year:</b> {_safe_html_v62(display_clean_v50(row.get("High_School_Passout_Year","")) or "-")}</p>'
        f'<p><b>High School Location:</b> {_safe_html_v62(display_clean_v50(row.get("High_School_Location","")) or "-")}</p>'
        f'<p><b>Middle School:</b> {_safe_html_v62(display_clean_v50(row.get("Middle_School_Name","")) or "-")}</p>'
        '</div>'
    )
    financial_html = (
        '<div class="admin-app-textbox-v125">'
        '<b>Financial Information</b>'
        f'<p><b>Bank Certificate Owner:</b> {_safe_html_v62(display_clean_v50(row.get("Bank_Certificate_Owner","")) or "-")}</p>'
        f'<p><b>Amount USD:</b> {_safe_html_v62(display_clean_v50(row.get("Bank_Amount_USD","")) or "-")}</p>'
        f'<p><b>Status:</b> {_safe_html_v62(status)}</p>'
        '</div>'
    )
    c1, c2 = st.columns(2)
    with c1:
        st.markdown(academic_html, unsafe_allow_html=True)
    with c2:
        st.markdown(financial_html, unsafe_allow_html=True)

    st.markdown("#### Self Introduction")
    st.write(display_clean_v50(row.get("Self_Introduction", "")) or "-")
    st.markdown("#### Study Plan")
    st.write(display_clean_v50(row.get("Study_Plan", "")) or "-")

    st.markdown("### Uploaded Documents")
    docs = parse_document_paths_v125(row)
    if not docs:
        st.info("No uploaded documents found for this application. This usually means the application was saved before document upload, or the document JSON was not saved.")
        raw_doc_v126 = display_clean_v50(row.get("Document_Paths_JSON", ""))
        if raw_doc_v126:
            st.caption("Saved document data was found but could not be read. Please check the Document_Paths_JSON column.")
    else:
        st.caption(f"{len(docs)} uploaded document(s) found. File names are hidden for a cleaner review page. Use the download buttons to save each document.")
        doc_cols = st.columns(3)
        for idx, (doc_key, rel_path) in enumerate(docs.items()):
            with doc_cols[idx % 3]:
                admin_download_document_button_v125(doc_key, rel_path, idx)

    st.markdown("### Update Application Status")
    st.caption("Only super admin / university admin should update these fields. Changes are saved to the same application record and automatically appear in the staff or partner dashboard. Email notifications are sent when interview date/result, offer/COA, application number, or visa result fields are newly updated.")

    with st.form(f"admin_update_status_v125_{safe_slug_v49(app_id)}"):
        c1, c2, c3 = st.columns(3)
        with c1:
            university_received = st.text_input("University Received Your Application", value=display_clean_v50(row.get("University_Received", "")), placeholder="YYYY-MM-DD HH:MM or note")
            application_number = st.text_input("Application Number Issued", value=display_clean_v50(row.get("Application_Number", "")))
            interview_date = st.text_input("Interview Date / Time", value=display_clean_v50(row.get("Interview_Date", "")), placeholder="YYYY-MM-DD HH:MM")
        with c2:
            interview_done = st.text_input("Interview Done", value=display_clean_v50(row.get("Interview_Done", "")), placeholder="YYYY-MM-DD HH:MM or Done")
            interview_result = st.selectbox(
                "Interview Result",
                ["", "Passed", "Failed"],
                index=["", "Passed", "Failed"].index(display_clean_v50(row.get("Interview_Result", ""))) if display_clean_v50(row.get("Interview_Result", "")) in ["", "Passed", "Failed"] else 0
            )
            offer_invoice = st.text_input("Issued Offer Letter and Invoice", value=display_clean_v50(row.get("Offer_Invoice_Issued", "")))
        with c3:
            coa_issued = st.text_input("COA Issue", value=display_clean_v50(row.get("COA_Issued", "")))
            visa_mode = st.selectbox(
                "Visa Application Type",
                ["", "Embassy", "Korean Immigration E-visa", "Visa Issuance Number"],
                index=["", "Embassy", "Korean Immigration E-visa", "Visa Issuance Number"].index(display_clean_v50(row.get("Visa_Mode", ""))) if display_clean_v50(row.get("Visa_Mode", "")) in ["", "Embassy", "Korean Immigration E-visa", "Visa Issuance Number"] else 0
            )
            visa_number = st.text_input("Visa Application Number Issued", value=display_clean_v50(row.get("Visa_Application_Number", "")))
            visa_result = st.selectbox(
                "Visa Result",
                ["", "Issued", "Rejected"],
                index=["", "Issued", "Rejected"].index(display_clean_v50(row.get("Visa_Result", ""))) if display_clean_v50(row.get("Visa_Result", "")) in ["", "Issued", "Rejected"] else 0
            )

        save_status = st.form_submit_button("Save Applicant Status", use_container_width=True)
        if save_status:
            updates = {
                "University_Received": university_received,
                "Application_Number": application_number,
                "Interview_Date": interview_date,
                "Interview_Done": interview_done,
                "Interview_Result": interview_result,
                "Offer_Invoice_Issued": offer_invoice,
                "COA_Issued": coa_issued,
                "Visa_Mode": visa_mode,
                "Visa_Application_Number": visa_number,
                "Visa_Result": visa_result,
            }
            # Keep current main status simple for partner dashboard.
            if visa_result:
                updates["Status"] = f"Visa {visa_result}"
            elif interview_result:
                updates["Status"] = f"Interview {interview_result}"
            elif application_number:
                updates["Status"] = "Application Number Issued"
            elif university_received:
                updates["Status"] = "University Received"
            else:
                updates["Status"] = inferred_application_status_v119(row)

            if update_application_status_from_admin_v125(app_id, updates):
                email_results_v129 = send_status_update_notifications_v129(row, updates)
                st.success("Applicant status updated successfully. Partner/staff dashboard will show the updated status automatically.")
                if email_results_v129:
                    for ok_v129, subject_v129, msg_v129 in email_results_v129:
                        if ok_v129:
                            st.success(f"Email notification sent: {subject_v129}")
                        else:
                            st.warning(f"Email notification not sent for '{subject_v129}': {msg_v129}")
                st.rerun()
            else:
                st.error("Could not update application status.")

    if render_shell:
        close_shell()

def admin_applications_page_v125():
    dash_shell(["Admin Dashboard","Partner Management","Universities","Eligibility Rules","Tuition Rules","Scholarship Rules","Applications","Application Samples"])
    st.subheader("Applications Management")
    st.caption("Review submitted student applications by university and program. Open an applicant to download the application form and uploaded files, and update application status.")

    if "admin_app_view_v125" not in st.session_state:
        st.session_state.admin_app_view_v125 = "home"
    if "admin_app_selected_uni_v125" not in st.session_state:
        st.session_state.admin_app_selected_uni_v125 = ""
    if "admin_app_selected_program_v125" not in st.session_state:
        st.session_state.admin_app_selected_program_v125 = ""
    if "admin_app_selected_id_v125" not in st.session_state:
        st.session_state.admin_app_selected_id_v125 = ""

    if st.session_state.admin_app_selected_id_v125:
        admin_application_detail_page_v125(st.session_state.admin_app_selected_id_v125, render_shell=False)
        close_shell()
        return

    df = admin_apps_visible_df_v125()
    if len(df) == 0:
        st.info("No applications have been submitted yet.")
        close_shell()
        return

    if st.session_state.admin_app_view_v125 == "program" and st.session_state.admin_app_selected_uni_v125:
        uni = st.session_state.admin_app_selected_uni_v125
        program = st.session_state.admin_app_selected_program_v125
        if st.button("← Back to Universities", key="admin_apps_back_unis_v125", use_container_width=False):
            st.session_state.admin_app_view_v125 = "home"
            st.session_state.admin_app_selected_uni_v125 = ""
            st.session_state.admin_app_selected_program_v125 = ""
            st.rerun()

        sub = df[df["University"].astype(str).str.strip().str.lower() == uni.strip().lower()].copy()
        if program:
            sub["_cat"] = sub.apply(admin_app_program_category_v125, axis=1)
            sub = sub[sub["_cat"].astype(str).str.strip().str.lower() == program.strip().lower()]

        st.markdown(f"""
        <div class="admin-app-program-hero-v125">
            <div>{admin_app_logo_html_v125(uni)}</div>
            <div>
                <span>{_safe_html_v62(program)} Applications</span>
                <h1>{_safe_html_v62(uni)}</h1>
                <p>{len(sub)} applicant(s)</p>
            </div>
        </div>
        """, unsafe_allow_html=True)

        if len(sub) == 0:
            st.info("No applications found in this category.")
        else:
            for idx, (_, row) in enumerate(sub.iterrows()):
                app_id = display_clean_v50(row.get("Application_ID", ""))
                applicant = application_display_name_v116(row)
                major = display_clean_v50(row.get("Desired_Major", "")) or "Not selected"
                status = inferred_application_status_v119(row)
                st.markdown(f"""
                <div class="admin-app-row-v125">
                    <div>
                        <h3>{_safe_html_v62(applicant)}</h3>
                        <p><b>Major:</b> {_safe_html_v62(major)} · <b>Passport:</b> {_safe_html_v62(display_clean_v50(row.get("Passport_Number","")) or "-")} · <b>Agency:</b> {_safe_html_v62(display_clean_v50(row.get("Agency","")) or "-")}</p>
                    </div>
                    <div>{application_status_badge_v116(status)}</div>
                </div>
                """, unsafe_allow_html=True)
                if st.button("Open Applicant Details", key=f"open_app_detail_v125_{idx}_{safe_slug_v49(app_id)}", use_container_width=True):
                    st.session_state.admin_app_selected_id_v125 = app_id
                    st.rerun()
        close_shell()
        return

    # Home: university cards with counts
    df["_cat"] = df.apply(admin_app_program_category_v125, axis=1)
    university_names = sorted([x for x in df["University"].dropna().astype(str).unique().tolist() if x.strip()])

    st.markdown('<div class="admin-app-university-grid-v125">', unsafe_allow_html=True)
    for idx, uni in enumerate(university_names):
        sub = df[df["University"].astype(str).str.strip().str.lower() == uni.strip().lower()]
        ug = len(sub[sub["_cat"] == "Undergraduate"])
        grad = len(sub[sub["_cat"] == "Graduate"])
        lang = len(sub[sub["_cat"] == "Language"])

        st.markdown(f"""
        <div class="admin-app-university-card-v125">
            <div class="uni-head-v125">
                <div class="uni-logo-v125">{admin_app_logo_html_v125(uni)}</div>
                <div>
                    <h2>{_safe_html_v62(uni)}</h2>
                    <p>Total applications: {len(sub)}</p>
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)

        c1, c2, c3 = st.columns(3)
        with c1:
            if st.button(f"Undergraduate · {ug}", key=f"admin_app_ug_{idx}", use_container_width=True):
                st.session_state.admin_app_view_v125 = "program"
                st.session_state.admin_app_selected_uni_v125 = uni
                st.session_state.admin_app_selected_program_v125 = "Undergraduate"
                st.rerun()
        with c2:
            if st.button(f"Graduate · {grad}", key=f"admin_app_grad_{idx}", use_container_width=True):
                st.session_state.admin_app_view_v125 = "program"
                st.session_state.admin_app_selected_uni_v125 = uni
                st.session_state.admin_app_selected_program_v125 = "Graduate"
                st.rerun()
        with c3:
            if st.button(f"Language · {lang}", key=f"admin_app_lang_{idx}", use_container_width=True):
                st.session_state.admin_app_view_v125 = "program"
                st.session_state.admin_app_selected_uni_v125 = uni
                st.session_state.admin_app_selected_program_v125 = "Language"
                st.rerun()
        st.divider()
    st.markdown('</div>', unsafe_allow_html=True)

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
        elif st.session_state.page == "Applications":
            admin_applications_page_v125()
        elif st.session_state.page == "Application Samples":
            admin_application_samples_v114()
        else:
            admin()
    else:
        if st.session_state.page == "Universities": universities_page()
        elif st.session_state.page == "Eligibility Check": eligibility()
        elif st.session_state.page == "Tuition & Scholarship": tuition()
        elif st.session_state.page == "Contact Us": contact()
        else:
            partner_dashboard()
