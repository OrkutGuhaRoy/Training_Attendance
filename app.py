"""
KGR Training Portal
====================
NO service account. NO complex auth. Just two URLs in secrets.toml:

  STUDENTS_CSV_URL   — public CSV export URL of your Students sheet
  ATTENDANCE_SCRIPT_URL — Google Apps Script Web App URL (for writing)

See SETUP.md for how to get these two URLs in 5 minutes.
"""

import streamlit as st
import pandas as pd
import requests
from datetime import date, datetime

st.set_page_config(page_title="KGR Training Portal", page_icon="🎓", layout="centered")

# ── Dark gold theme ──────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Playfair+Display:wght@700&family=Inter:wght@400;500;600&display=swap');

/* Base */
html, body, [class*="css"] {
  font-family: 'Inter', sans-serif;
  background: #0d1117 !important;
  color: #f0f6fc !important;
  font-size: 16px !important;
}
.main .block-container { max-width: 900px; padding: 2rem 1.8rem; }
#MainMenu, footer, header { visibility: hidden; }

/* Headings */
h1, h2, h3 { font-family: 'Playfair Display', serif; color: #f0c040 !important; }

/* Cards */
.card {
  background: #1c2230;
  border: 1px solid #3a4150;
  border-radius: 12px;
  padding: 1.5rem 1.8rem;
  margin-bottom: 1.1rem;
}
.card-gold { border-top: 3px solid #f0c040; }

/* Info rows inside cards */
.label {
  font-size: 0.78rem;
  text-transform: uppercase;
  letter-spacing: 0.8px;
  color: #8b9ab0;
  margin-bottom: 3px;
}
.value {
  font-size: 1.05rem;
  font-weight: 600;
  color: #f0f6fc;
}
.value-gold  { color: #f0c040; }
.value-green { color: #4cc76e; }
.value-red   { color: #ff6b6b; }

.row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 0.65rem 0;
  border-bottom: 1px solid #2a3140;
  gap: 1rem;
}
.row:last-child { border-bottom: none; }
.row .label { min-width: 160px; margin-bottom: 0; }

/* Streamlit inputs */
.stTextInput > div > div > input,
.stTextArea textarea,
.stSelectbox > div > div {
  background: #1c2230 !important;
  border: 1px solid #3a4150 !important;
  color: #f0f6fc !important;
  border-radius: 8px !important;
  font-size: 1rem !important;
}
.stTextInput > div > div > input:focus,
.stTextArea textarea:focus {
  border-color: #f0c040 !important;
  box-shadow: 0 0 0 2px rgba(240,192,64,0.15) !important;
}

/* Labels on inputs */
label, p, .stMarkdown p {
  color: #c9d5e0 !important;
  font-size: 0.95rem !important;
}

/* Buttons */
.stButton > button {
  background: linear-gradient(135deg, #f0c040, #b8902a) !important;
  color: #0d1117 !important;
  font-weight: 700 !important;
  font-size: 1rem !important;
  border: none !important;
  border-radius: 8px !important;
  padding: 0.55rem 1.5rem !important;
  width: 100%;
}
.stButton > button:hover { opacity: 0.9 !important; }

/* Tabs */
.stTabs [data-baseweb="tab-list"] {
  background: #1c2230 !important;
  border: 1px solid #3a4150 !important;
  border-radius: 10px !important;
  padding: 4px !important;
  gap: 4px;
}
.stTabs [data-baseweb="tab"] {
  background: transparent !important;
  color: #8b9ab0 !important;
  border-radius: 7px !important;
  font-size: 0.95rem !important;
  font-weight: 500 !important;
  padding: 0.4rem 1.1rem !important;
}
.stTabs [aria-selected="true"] {
  background: #f0c040 !important;
  color: #0d1117 !important;
  font-weight: 700 !important;
}

/* Alerts */
.stSuccess { background: rgba(76,199,110,0.12) !important; border: 1px solid rgba(76,199,110,0.4) !important; color: #4cc76e !important; }
.stError   { background: rgba(255,107,107,0.12) !important; border: 1px solid rgba(255,107,107,0.4) !important; color: #ff6b6b !important; }
.stInfo    { background: rgba(88,166,255,0.1)  !important; border: 1px solid rgba(88,166,255,0.3)  !important; }

/* Metrics */
[data-testid="metric-container"] {
  background: #1c2230;
  border: 1px solid #3a4150;
  border-radius: 10px;
  padding: 1rem 1.2rem;
}
[data-testid="metric-container"] label { color: #8b9ab0 !important; font-size: 0.85rem !important; }
[data-testid="metric-container"] [data-testid="metric-value"] { color: #f0f6fc !important; font-size: 1.6rem !important; font-weight: 700 !important; }

/* Dataframe */
.stDataFrame { border: 1px solid #3a4150 !important; border-radius: 10px !important; overflow: hidden; }
[data-testid="stDataFrameResizable"] th { background: #252d3d !important; color: #c9d5e0 !important; font-size: 0.85rem !important; }
[data-testid="stDataFrameResizable"] td { color: #f0f6fc !important; font-size: 0.92rem !important; }

/* Slider */
.stSlider label { color: #c9d5e0 !important; font-size: 0.95rem !important; }
</style>
""", unsafe_allow_html=True)


# ── Read config from secrets ─────────────────────────────────────────────────
try:
    STUDENTS_CSV_URL      = st.secrets["STUDENTS_CSV_URL"]
    ATTENDANCE_SCRIPT_URL = st.secrets["ATTENDANCE_SCRIPT_URL"]
except Exception:
    st.error("⚠️ Missing secrets. Add STUDENTS_CSV_URL and ATTENDANCE_SCRIPT_URL to .streamlit/secrets.toml")
    st.stop()


# ── Data helpers ─────────────────────────────────────────────────────────────
@st.cache_data(ttl=60)   # refresh every 60 seconds
def load_students():
    try:
        df = pd.read_csv(STUDENTS_CSV_URL)
    except Exception as e:
        raise RuntimeError(
            f"Could not fetch the sheet. Make sure you used File → Share → "
            f"Publish to web → CSV (NOT the regular share link). Error: {e}"
        )
    # Strip whitespace from column names and values
    df.columns = df.columns.str.strip()
    # Drop completely empty rows
    df = df.dropna(how="all")
    # Debug: show columns if Email missing
    if "Email" not in df.columns:
        raise RuntimeError(
            f"'Email' column not found. Columns in your sheet: {list(df.columns)}\n"
            f"Make sure Row 1 has exactly: Email, Password, Name, Phone, ..."
        )
    df["Email"] = df["Email"].astype(str).str.strip().str.lower()
    return df

@st.cache_data(ttl=30)
def load_attendance():
    url = st.secrets.get("ATTENDANCE_CSV_URL", "")
    if not url:
        return pd.DataFrame()
    try:
        df = pd.read_csv(url)
        if df.empty or len(df.columns) == 0:
            return pd.DataFrame()
        df.columns = df.columns.str.strip()
        return df
    except Exception:
        return pd.DataFrame()

def submit_attendance(data: dict) -> bool:
    """POST to Google Apps Script Web App which appends a row."""
    try:
        r = requests.post(ATTENDANCE_SCRIPT_URL, json=data, timeout=10)
        return r.status_code == 200
    except Exception as e:
        st.error(f"Submission error: {e}")
        return False


# ── Session state ────────────────────────────────────────────────────────────
for k, v in {"logged_in": False, "student": None}.items():
    if k not in st.session_state:
        st.session_state[k] = v


# ════════════════════════════════════════════════════════════════════════════
# LOGIN
# ════════════════════════════════════════════════════════════════════════════
if not st.session_state.logged_in:

    st.markdown("""
    <div style="text-align:center;padding:2rem 0 1.5rem">
      <div style="font-size:3rem">🎓</div>
      <h1 style="margin:0.3rem 0 0.1rem">KGR Training Portal</h1>
      <p style="color:#8b9ab0;font-size:0.9rem;letter-spacing:1.5px;text-transform:uppercase">
        eTendering · DSC · Taxation · IT Skills
      </p>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("""
    <div class="card" style="border-left:4px solid #d4a843;margin-bottom:1.5rem;">
      <div style="display:flex;gap:1rem;align-items:center;">
        <div style="font-size:2.5rem">👩‍⚖️</div>
        <div>
          <div style="font-family:'Playfair Display',serif;color:#f0c040;font-size:1.05rem;font-weight:700">
            Ms Kavita Guha Roy
          </div>
          <div style="font-size:0.82rem;color:#8b9ab0;text-transform:uppercase;letter-spacing:1px;margin-bottom:0.4rem">
            Advocate & Technical Consultant · Head Instructor
          </div>
          <div style="font-size:0.95rem;color:#c9d5e0;font-style:italic">
            "Welcome! These skills will open real doors for you.
            Give your best every session — we are here to guide you."
          </div>
        </div>
      </div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown('<div class="card card-gold">', unsafe_allow_html=True)
    st.markdown("**Sign in to your account**")
    email    = st.text_input("Email", placeholder="your@email.com")
    password = st.text_input("Password", type="password", placeholder="••••••••")
    login_btn = st.button("Sign In →")
    st.markdown("</div>", unsafe_allow_html=True)

    if login_btn:
        if not email or not password:
            st.error("Please enter both email and password.")
        else:
            try:
                df = load_students()
                match = df[df["Email"] == email.strip().lower()]
                if match.empty:
                    st.error("No account found with that email.")
                elif str(match.iloc[0]["Password"]).strip() != password.strip():
                    st.error("Incorrect password.")
                else:
                    st.session_state.logged_in = True
                    st.session_state.student = match.iloc[0].to_dict()
                    st.rerun()
            except RuntimeError as e:
                st.error(str(e))
            except Exception as e:
                st.error(f"Could not load data: {e}")

    st.markdown("""
    <div style="text-align:center;margin-top:2rem;color:#8b9ab0;font-size:0.95rem;">
      Training by Ms Kavita Guha Roy & her team · Happy Learning!
    </div>
    """, unsafe_allow_html=True)


# ════════════════════════════════════════════════════════════════════════════
# DASHBOARD
# ════════════════════════════════════════════════════════════════════════════
else:
    s = st.session_state.student
    def g(key, fallback="—"):
        v = s.get(key, fallback)
        return v if str(v) not in ("", "nan", "None", "NaT") else fallback

    try:
        total_fees = float(str(g("Total_Fees","0")).replace(",","").replace("₹",""))
        fees_paid  = float(str(g("Fees_Paid","0")).replace(",","").replace("₹",""))
        fees_due   = max(total_fees - fees_paid, 0)
    except:
        total_fees = fees_paid = fees_due = 0

    try:
        hrs_total = float(g("Duration_hrs", 0))
        hrs_done  = float(g("Hours_Completed", 0))
        hrs_left  = max(hrs_total - hrs_done, 0)
        pct       = int(hrs_done / hrs_total * 100) if hrs_total else 0
    except:
        hrs_total = hrs_done = hrs_left = pct = 0

    # ── Header ──
    st.markdown(f"""
    <div class="card card-gold">
      <div style="display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:0.5rem;">
        <div>
          <h2 style="margin:0">Welcome, {g('Name').split()[0]}! 👋</h2>
          <p style="margin:0.2rem 0 0;color:#c9d5e0;font-size:0.95rem">Happy Learning! · {g('Training_Plan')}</p>
        </div>
        <div style="text-align:right;">
          <div style="color:#f0c040;font-weight:700">{datetime.now().strftime('%d %b %Y')}</div>
          <div style="color:#8b9ab0;font-size:0.9rem">{datetime.now().strftime('%A')}</div>
        </div>
      </div>
    </div>
    """, unsafe_allow_html=True)

    # ── Instructor card ──
    st.markdown("""
    <div class="card" style="border-left:4px solid #d4a843;">
      <div style="font-size:0.65rem;text-transform:uppercase;letter-spacing:1.5px;color:#8b9ab0;margin-bottom:0.4rem">From the Head Instructor's Desk</div>
      <div style="display:flex;gap:1rem;align-items:center;">
        <div style="font-size:2.2rem">👩‍⚖️</div>
        <div>
          <div style="font-family:'Playfair Display',serif;color:#f0c040;font-weight:700">Ms Kavita Guha Roy</div>
          <div style="font-size:0.82rem;color:#8b9ab0;text-transform:uppercase;letter-spacing:1px;margin-bottom:0.3rem">Advocate & Technical Consultant</div>
          <div style="font-size:0.92rem;color:#c9d5e0;font-style:italic">"Consistency is the key. Show up, stay curious, and you will excel."</div>
        </div>
      </div>
    </div>
    """, unsafe_allow_html=True)

    tab1, tab2, tab3 = st.tabs(["📊 My Info", "📋 Submit Attendance", "📂 Attendance Log"])

    # ── TAB 1 ────────────────────────────────────────────────────────────────
    with tab1:
        col1, col2 = st.columns(2)
        with col1:
            st.markdown('<div class="card">', unsafe_allow_html=True)
            st.markdown('<div style="font-family:\'Playfair Display\',serif;color:#f0c040;margin-bottom:0.8rem">Personal Details</div>', unsafe_allow_html=True)
            for lbl, val in [("Full Name", g("Name")), ("Email", g("Email")), ("Phone", g("Phone")), ("Batch", g("Batch"))]:
                st.markdown(f'<div class="row"><div class="label">{lbl}</div><div class="value">{val}</div></div>', unsafe_allow_html=True)
            st.markdown("</div>", unsafe_allow_html=True)

        with col2:
            st.markdown('<div class="card">', unsafe_allow_html=True)
            st.markdown('<div style="font-family:\'Playfair Display\',serif;color:#f0c040;margin-bottom:0.8rem">Training Details</div>', unsafe_allow_html=True)
            for lbl, val in [("Training Plan", g("Training_Plan")), ("Admission Date", g("Admission_Date")),
                              ("Completion Date", g("Completion_Date")), ("Total Duration", f"{hrs_total:.0f} hrs")]:
                st.markdown(f'<div class="row"><div class="label">{lbl}</div><div class="value">{val}</div></div>', unsafe_allow_html=True)
            st.markdown("</div>", unsafe_allow_html=True)

        st.markdown(f"""
        <div class="card">
          <div style="display:flex;justify-content:space-between;margin-bottom:0.6rem;">
            <div><div class="label">Training Progress</div><div class="value">{hrs_done:.0f} / {hrs_total:.0f} hrs</div></div>
            <div style="text-align:right"><div class="label">Remaining</div><div class="value value-gold">{hrs_left:.0f} hrs</div></div>
          </div>
          <div style="background:#21262d;border-radius:20px;height:8px;overflow:hidden;">
            <div style="width:{pct}%;height:100%;background:linear-gradient(90deg,#8a6e2a,#d4a843);border-radius:20px;"></div>
          </div>
          <div style="font-size:0.82rem;color:#8b9ab0;margin-top:0.3rem">{pct}% complete</div>
        </div>
        """, unsafe_allow_html=True)

        st.markdown(f"""
        <div class="card">
          <div style="font-family:'Playfair Display',serif;color:#f0c040;margin-bottom:0.8rem">Fees Summary</div>
          <div class="row"><div class="label">Total Fees</div><div class="value">₹{total_fees:,.0f}</div></div>
          <div class="row"><div class="label">Fees Paid</div><div class="value value-green">₹{fees_paid:,.0f}</div></div>
          <div class="row"><div class="label">Fees Due</div><div class="value {'value-red' if fees_due > 0 else 'value-green'}">₹{fees_due:,.0f}</div></div>
          <div class="row"><div class="label">Due Date</div><div class="value">{g('Due_Date')}</div></div>
        </div>
        """, unsafe_allow_html=True)

    # ── TAB 2 ────────────────────────────────────────────────────────────────
    with tab2:
        st.markdown('<div class="card card-gold">', unsafe_allow_html=True)
        st.markdown("**Daily Attendance Form**")
        col_a, col_b = st.columns(2)
        with col_a:
            att_date   = st.date_input("Attendance Date", value=date.today())
            class_date = st.date_input("Class Date", value=date.today())
            arrival    = st.time_input("Arrival Time",   value=datetime.strptime("09:00","%H:%M").time())
            departure  = st.time_input("Departure Time", value=datetime.strptime("13:00","%H:%M").time())
        with col_b:
            instructor = st.text_input("Class Conducted By", placeholder="e.g. Ms Kavita Guha Roy")
            topics     = st.text_area("Topics Taught Today", placeholder="Topics covered today…", height=100)
            remarks    = st.text_area("Your Remarks", placeholder="Feedback or comments…", height=60)

        rating = st.select_slider("Rate Today's Session",
                    options=[1,2,3,4,5], value=4,
                    format_func=lambda x: f"{'★'*x}{'☆'*(5-x)} ({x}/5)")

        if st.button("✅ Submit Attendance"):
            if not instructor.strip() or not topics.strip():
                st.error("Please fill in Instructor name and Topics.")
            else:
                payload = {
                    "Student_Email":   g("Email"),
                    "Student_Name":    g("Name"),
                    "Attendance_Date": str(att_date),
                    "Class_Date":      str(class_date),
                    "Arrival_Time":    str(arrival),
                    "Departure_Time":  str(departure),
                    "Instructor":      instructor.strip(),
                    "Topics":          topics.strip(),
                    "Trainee_Remarks": remarks.strip(),
                    "Rating":          rating,
                    "Submitted_At":    datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                }
                with st.spinner("Saving…"):
                    ok = submit_attendance(payload)
                if ok:
                    st.success("✅ Attendance submitted successfully!")
                    st.balloons()
                    load_attendance.clear()
                else:
                    st.error("❌ Submission failed. Please try again.")

        st.markdown("</div>", unsafe_allow_html=True)

    # ── TAB 3 ────────────────────────────────────────────────────────────────
    with tab3:
        df_att = load_attendance()
        if df_att.empty:
            st.info("No attendance records yet, or ATTENDANCE_CSV_URL not set in secrets.")
        else:
            my = df_att[df_att["Student_Email"].astype(str).str.lower() == g("Email").lower()]
            if my.empty:
                st.info("No attendance records found for your account yet.")
            else:
                col_m1, col_m2 = st.columns(2)
                col_m1.metric("Total Sessions", len(my))
                if "Rating" in my.columns:
                    col_m2.metric("Avg Rating", f"{pd.to_numeric(my['Rating'], errors='coerce').mean():.1f} / 5")
                show = [c for c in ["Attendance_Date","Arrival_Time","Departure_Time","Instructor","Topics","Rating"] if c in my.columns]
                st.dataframe(my[show].sort_values("Attendance_Date", ascending=False).reset_index(drop=True),
                             use_container_width=True, hide_index=True)

    st.markdown("<br>", unsafe_allow_html=True)
    if st.button("Sign Out"):
        st.session_state.logged_in = False
        st.session_state.student = None
        st.rerun()

    st.markdown("""
    <div style="text-align:center;margin-top:2rem;color:#8b9ab0;font-size:0.95rem;border-top:1px solid #21262d;padding-top:1rem;">
      KGR Training Portal · Training by Ms Kavita Guha Roy (Advocate & Technical Consultant) & her team
    </div>
    """, unsafe_allow_html=True)
