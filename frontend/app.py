import os
import html
import requests
import streamlit as st
from datetime import date, timedelta
from fpdf import FPDF

# Requires Streamlit >= 1.40 (icon= on buttons and Material icons in markdown)

# -------------------- Configuration --------------------
API_BASE_URL = os.getenv(
    "TRIPWEAVER_API_URL", "https://tripweaver-backend-vain.onrender.com"
)
PLAN_URL = f"{API_BASE_URL.rstrip('/')}/api/v1/plan-trip"
AIRPORTS_URL = f"{API_BASE_URL.rstrip('/')}/api/v1/airports"
FALLBACK_AIRPORTS = ["Islamabad (ISB)", "Dubai (DXB)"]

st.set_page_config(
    page_title="TripWeaver | AI Travel Planner",
    page_icon="✈️",
    layout="wide",
    initial_sidebar_state="collapsed",
)

ss = st.session_state
ss.setdefault("result", None)
ss.setdefault("req", {})

# -------------------- Icon set (one consistent line-icon family) --------------------
ICON_PATHS = {
    "plane": '<path d="M17.8 19.2 16 11l3.5-3.5C21 6 21.5 4 21 3c-1-.5-3 0-4.5 1.5L13 8 4.8 6.2c-.5-.1-.9.1-1.1.5l-.3.5c-.2.5-.1 1 .3 1.3L9 12l-2 3H4l-1 1 3 2 2 3 1-1v-3l3-2 3.5 5.3c.3.4.8.5 1.3.3l.5-.2c.4-.3.6-.7.5-1.2z"/>',
    "bed": '<path d="M2 20v-8a2 2 0 0 1 2-2h16a2 2 0 0 1 2 2v8"/><path d="M4 10V6a2 2 0 0 1 2-2h12a2 2 0 0 1 2 2v4"/><path d="M12 4v6"/><path d="M2 18h20"/>',
    "ticket": '<path d="M2 9a3 3 0 0 1 0 6v2a2 2 0 0 0 2 2h16a2 2 0 0 0 2-2v-2a3 3 0 0 1 0-6V7a2 2 0 0 0-2-2H4a2 2 0 0 0-2 2Z"/><path d="M13 5v2"/><path d="M13 17v2"/><path d="M13 11v2"/>',
    "pin": '<path d="M20 10c0 6-8 12-8 12s-8-6-8-12a8 8 0 0 1 16 0Z"/><circle cx="12" cy="10" r="3"/>',
    "calendar": '<rect width="18" height="18" x="3" y="4" rx="2"/><path d="M16 2v4"/><path d="M8 2v4"/><path d="M3 10h18"/>',
    "wallet": '<path d="M19 7V4a1 1 0 0 0-1-1H5a2 2 0 0 0 0 4h15a1 1 0 0 1 1 1v4h-3a2 2 0 0 0 0 4h3a1 1 0 0 0 1-1v-2a1 1 0 0 0-1-1"/><path d="M3 5v14a2 2 0 0 0 2 2h15a1 1 0 0 0 1-1v-4"/>',
    "star": '<polygon points="12 2 15.09 8.26 22 9.27 17 14.14 18.18 21.02 12 17.77 5.82 21.02 7 14.14 2 9.27 8.91 8.26 12 2"/>',
    "clock": '<circle cx="12" cy="12" r="10"/><polyline points="12 6 12 12 16 14"/>',
    "sparkles": '<path d="m12 3-1.9 5.8a2 2 0 0 1-1.3 1.3L3 12l5.8 1.9a2 2 0 0 1 1.3 1.3L12 21l1.9-5.8a2 2 0 0 1 1.3-1.3L21 12l-5.8-1.9a2 2 0 0 1-1.3-1.3Z"/>',
    "users": '<path d="M16 21v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2"/><circle cx="9" cy="7" r="4"/><path d="M22 21v-2a4 4 0 0 0-3-3.87"/><path d="M16 3.13a4 4 0 0 1 0 7.75"/>',
    "check": '<circle cx="12" cy="12" r="10"/><path d="m9 12 2 2 4-4"/>',
    "alert": '<path d="m21.73 18-8-14a2 2 0 0 0-3.48 0l-8 14A2 2 0 0 0 4 21h16a2 2 0 0 0 1.73-3"/><path d="M12 9v4"/><path d="M12 17h.01"/>',
    "arrow": '<path d="M5 12h14"/><path d="m12 5 7 7-7 7"/>',
    "moon": '<path d="M12 3a6 6 0 0 0 9 9 9 9 0 1 1-9-9Z"/>',
}


def icon(name, size=18, color="currentColor", fill=False):
    f = color if fill else "none"
    return (
        f'<svg width="{size}" height="{size}" viewBox="0 0 24 24" fill="{f}" stroke="{color}" '
        f'stroke-width="2" stroke-linecap="round" stroke-linejoin="round" '
        f'style="flex-shrink:0; vertical-align:-3px;">{ICON_PATHS[name]}</svg>'
    )


# Section themes: (icon color, tinted background)
THEMES = {
    "flights": ("#2563EB", "#DBEAFE"),
    "hotels": ("#7C3AED", "#EDE9FE"),
    "activities": ("#D97706", "#FEF3C7"),
    "itinerary": ("#059669", "#D1FAE5"),
    "budget": ("#0F172A", "#E2E8F0"),
}

# -------------------- Placeholder content for the landing page --------------------
# Sample values only. Replace with real data when you have it.
POPULAR_TRIPS = [
    ("Dubai", "DXB", "5 nights", "320,000"),
    ("Istanbul", "IST", "5 nights", "290,000"),
    ("Bangkok", "BKK", "7 nights", "410,000"),
    ("Rome", "FCO", "4 nights", "380,000"),
]
AGENTS = [
    ("plane", "flights", "Flight Agent", "Compares fares and times for your dates."),
    ("bed", "hotels", "Stay Agent", "Finds hotels that match your comfort level."),
    (
        "ticket",
        "activities",
        "Activity Agent",
        "Builds a day-by-day plan around your interests.",
    ),
    ("wallet", "budget", "Budget Agent", "Checks every cost against your PKR budget."),
]
SAMPLE_DAYS = [
    ("Day 1", ["Old town walking tour", "Dinner at a local favourite"]),
    ("Day 2", ["Historic district and museum", "Street-food tasting"]),
    ("Day 3", ["Markets and shopping", "Sunset at the waterfront"]),
]

# -------------------- Custom CSS --------------------
st.markdown(
    """
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');
html, body, [class*="css"] { font-family: 'Inter', sans-serif; }
.stApp { background-color: #F8FAFC; }

/* --- STREAMLIT RESET (flush to top, full width) --- */
#MainMenu, footer, header, [data-testid="stHeader"], [data-testid="stDecoration"], [data-testid="stToolbar"] { display: none !important; }
[data-testid="stAppViewContainer"], [data-testid="stMain"] { overflow-x: hidden; padding-top: 0 !important; }
.block-container, [data-testid="stMainBlockContainer"] {
    padding: 0 24px 56px 24px !important;
    max-width: 1500px !important;
    margin: 0 auto;
}

/* --- FULL-BLEED HERO --- */
.hero-wrapper {
    width: 100vw; margin-left: calc(50% - 50vw); margin-bottom: -64px;
    padding: 24px 20px 92px 20px; text-align: center; color: white;
    background: linear-gradient(135deg, rgba(15, 23, 42, 0.8) 0%, rgba(30, 58, 138, 0.8) 100%),
                url('https://images.unsplash.com/photo-1436491865332-7a61a109cc05?q=80&w=2074&auto=format&fit=crop');
    background-size: cover; background-position: center;
    border-radius: 0 0 32px 32px; box-shadow: 0 20px 40px rgba(0,0,0,0.1);
}
.logo-container { display: flex; justify-content: center; align-items: center; gap: 10px; margin-bottom: 14px; }
.logo-text { font-size: 1.7rem; font-weight: 800; letter-spacing: -0.5px; margin: 0; padding: 0; color: white; }
.hero-title {
    font-size: clamp(1.6rem, 4vw, 2.6rem); font-weight: 800; letter-spacing: -1px; margin-bottom: 8px;
    display: flex; justify-content: center; align-items: center; gap: 14px;
}
.hero-subtitle { font-size: 1rem; color: #CBD5E1; max-width: 760px; margin: 0 auto; }
@keyframes float { 0% { transform: translateY(0) rotate(0deg); } 50% { transform: translateY(-8px) rotate(5deg); } 100% { transform: translateY(0) rotate(0deg); } }
.animated-plane { animation: float 4s ease-in-out infinite; display: inline-flex; }
@media (prefers-reduced-motion: reduce) { .animated-plane { animation: none; } }

/* --- SEARCH FORM (centered card overlapping the hero) --- */
[data-testid="stForm"] {
    background-color: white; padding: 22px 28px 24px 28px; border-radius: 20px; border: none;
    box-shadow: 0 15px 35px rgba(0, 0, 0, 0.1);
    position: relative; z-index: 10; margin: 0 auto; width: 100%; max-width: 1200px;
}
.stTextInput > div > div > input, .stDateInput > div > div > input, .stNumberInput > div > div > input, .stSelectbox > div > div {
    border-radius: 12px; border: 1px solid #E2E8F0; background-color: #F8FAFC; font-weight: 500;
}
.stTextInput label, .stDateInput label, .stNumberInput label, .stSelectbox label, .stMultiSelect label {
    font-size: 0.75rem; font-weight: 700; color: #64748B; text-transform: uppercase; margin-bottom: 2px;
}
.stFormSubmitButton > button, [data-testid="stFormSubmitButton"] > button {
    background-color: #0F172A; color: #FFFFFF; border-radius: 50px; height: 46px; padding: 0 16px;
    font-weight: 700; font-size: 0.95rem; border: none; width: 100%; margin-top: 27px; transition: all 0.2s ease;
}
.stFormSubmitButton > button:hover, [data-testid="stFormSubmitButton"] > button:hover { background-color: #1E3A8A; color: #fff; box-shadow: 0 8px 20px rgba(30,58,138,0.3); }

/* --- SHARED --- */
.band, .results { max-width: 1200px; margin: 40px auto 0 auto; }
.band-title { font-size: 1.3rem; font-weight: 800; color: #0F172A; margin-bottom: 4px; }
.band-sub { font-size: 0.9rem; color: #64748B; margin-bottom: 16px; }
.grid-4 { display: grid; grid-template-columns: repeat(auto-fit, minmax(220px, 1fr)); gap: 16px; }
.mini-card { background: #fff; border: 1px solid #E2E8F0; border-radius: 14px; padding: 18px; }
.mini-title { font-size: 1.05rem; font-weight: 700; color: #0F172A; }
.mini-text { font-size: 0.88rem; color: #64748B; margin-top: 4px; }
.mini-meta { font-size: 0.8rem; color: #64748B; margin-top: 2px; }
.mini-price { font-size: 1rem; font-weight: 700; color: #1E3A8A; margin-top: 10px; }

.icon-badge { display: inline-flex; align-items: center; justify-content: center; border-radius: 12px; flex-shrink: 0; }

/* --- RESULTS: SUMMARY BAR --- */
.bar { display: flex; align-items: center; gap: 10px 20px; flex-wrap: wrap; background: #fff; border: 1px solid #E2E8F0; border-radius: 14px; padding: 14px 20px; margin: 36px 0 18px 0; }
.bar-route { display: inline-flex; align-items: center; gap: 10px; font-size: 1.1rem; font-weight: 800; color: #0F172A; }
.bar-meta { display: inline-flex; align-items: center; gap: 6px; font-size: 0.92rem; color: #475569; }
.bar-total { margin-left: auto; display: flex; align-items: center; gap: 28px; padding-left: 24px; border-left: 1px solid #E2E8F0; }
.bar-stat { text-align: right; }
.bar-stat .l { font-size: 0.75rem; font-weight: 600; color: #64748B; }
.bar-stat .v { font-size: 1.15rem; font-weight: 800; color: #0F172A; white-space: nowrap; }
.chip { display: inline-block; background: #EEF2FF; color: #3730A3; padding: 3px 10px; border-radius: 12px; font-size: 0.78rem; font-weight: 600; margin: 2px 4px 2px 0; }

/* --- RESULTS: BUDGET PANEL --- */
.panel { background: #fff; border: 1px solid #E2E8F0; border-radius: 16px; padding: 18px 20px; }
.panel-head { display: flex; align-items: center; gap: 10px; font-size: 1rem; font-weight: 700; color: #0F172A; margin-bottom: 12px; }
.kv { display: flex; justify-content: space-between; font-size: 0.9rem; color: #334155; padding: 4px 0; }
.kv strong { color: #0F172A; }
.bar-track { display: flex; height: 12px; border-radius: 8px; overflow: hidden; background: #E2E8F0; margin: 10px 0 14px 0; }
.bar-track span { display: block; height: 100%; }
.legend-row { display: flex; align-items: center; justify-content: space-between; gap: 12px; font-size: 0.88rem; color: #334155; padding: 3px 0; }
.legend-row span:last-child { white-space: nowrap; }
.legend-dot { display: inline-block; width: 10px; height: 10px; border-radius: 50%; margin-right: 8px; }
.remaining { display: flex; justify-content: space-between; align-items: baseline; gap: 12px; border-top: 1px solid #E2E8F0; margin-top: 10px; padding-top: 10px; font-weight: 700; color: #0F172A; }
.remaining .amount { font-size: 1.3rem; white-space: nowrap; }

/* --- RESULTS: RECOMMENDED COMBO + STATUS --- */
.combo { background: linear-gradient(135deg, #0F172A 0%, #1E3A8A 100%); color: #fff; border-radius: 16px; padding: 20px 24px; margin-bottom: 14px; }
.combo-tag { display: inline-flex; align-items: center; gap: 8px; font-size: 0.85rem; font-weight: 700; color: #93C5FD; margin-bottom: 10px; }
.combo-body { display: flex; flex-wrap: wrap; align-items: center; gap: 8px 14px; font-size: 1.1rem; font-weight: 700; }
.combo-body .item { display: inline-flex; align-items: center; gap: 8px; }
.combo-body .plus { color: #93C5FD; font-weight: 500; }
.combo-meta { font-size: 0.9rem; color: #CBD5E1; margin-top: 10px; }
.status { display: flex; align-items: center; gap: 10px; border-radius: 14px; padding: 12px 16px; font-size: 0.92rem; font-weight: 600; margin-bottom: 14px; }
.status.ok { background: #D1FAE5; color: #065F46; }
.status.warn { background: #FEE2E2; color: #991B1B; }

/* --- RESULTS: SECTIONS --- */
.sec-head { display: flex; align-items: center; gap: 14px; margin: 8px 0 14px 0; }
.sec-head .icon-badge { width: 44px; height: 44px; }
.sec-title { font-size: 1.25rem; font-weight: 800; color: #0F172A; line-height: 1.2; }
.sec-count { font-size: 0.8rem; font-weight: 700; color: #64748B; background: #E2E8F0; border-radius: 10px; padding: 2px 9px; margin-left: 8px; vertical-align: 2px; }
.sec-sub { font-size: 0.88rem; color: #64748B; margin-top: 2px; }
.sec-divider { height: 1px; background: #E2E8F0; margin: 34px 0 22px 0; }
.cards-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(340px, 1fr)); gap: 16px; }
.cards-grid.tight { grid-template-columns: repeat(auto-fill, minmax(280px, 1fr)); }

/* --- CARDS --- */
.result-card { background: #FFFFFF; border-radius: 16px; padding: 20px 22px; box-shadow: 0 4px 15px rgba(0, 0, 0, 0.03); border: 1px solid #F1F5F9; transition: box-shadow 0.2s ease, border-color 0.2s ease; }
.result-card:hover { box-shadow: 0 12px 25px rgba(0, 0, 0, 0.08); border-color: #CBD5E1; }
.card-header { display: flex; justify-content: space-between; align-items: flex-start; gap: 12px; margin-bottom: 12px; }
.airline-name { font-size: 1.1rem; font-weight: 700; color: #0F172A; }
.price-tag { font-size: 1.25rem; font-weight: 800; color: #EF4444; white-space: nowrap; }
.badges { display: flex; align-items: center; flex-wrap: wrap; gap: 6px; margin-top: 6px; }
.badge-mock, .badge-real, .badge-best { display: inline-flex; align-items: center; gap: 4px; padding: 4px 10px; border-radius: 12px; font-size: 0.7rem; font-weight: 700; text-transform: uppercase; }
.badge-mock { background-color: #FEF3C7; color: #D97706; }
.badge-real { background-color: #D1FAE5; color: #059669; }
.badge-best { background-color: #DBEAFE; color: #2563EB; }
.flight-path { display: flex; align-items: center; justify-content: space-between; margin: 16px 0 2px 0; }
.path-point { text-align: center; }
.path-time { font-size: 1.2rem; font-weight: 700; color: #0F172A; }
.path-city { font-size: 0.85rem; color: #64748B; font-weight: 600; }
.path-line { flex-grow: 1; margin: 0 16px; border-bottom: 2px dashed #CBD5E1; position: relative; height: 0; }
.path-plane { position: absolute; top: -13px; left: 50%; transform: translateX(-50%) rotate(45deg); background: #FFFFFF; padding: 0 8px; display: inline-flex; }
.card-sub { font-size: 0.85rem; color: #64748B; }
.stat-row { display: flex; justify-content: space-between; align-items: center; font-size: 0.9rem; color: #334155; margin-top: 8px; }
.stat-row .inline { display: inline-flex; align-items: center; gap: 6px; }

/* --- ACTIVITY CARDS --- */
.act-card { display: flex; align-items: center; gap: 14px; background: #fff; border: 1px solid #F1F5F9; border-radius: 16px; padding: 14px 18px; box-shadow: 0 4px 15px rgba(0,0,0,0.03); }
.act-card .icon-badge { width: 40px; height: 40px; }
.act-body { flex-grow: 1; min-width: 0; }
.act-name { font-size: 1rem; font-weight: 700; color: #0F172A; }
.act-meta { display: flex; align-items: center; gap: 12px; font-size: 0.83rem; color: #64748B; margin-top: 3px; }
.act-meta .inline { display: inline-flex; align-items: center; gap: 4px; }

/* --- DAY CARDS --- */
.day-card { background: #fff; border: 1px solid #E2E8F0; border-radius: 16px; padding: 16px 18px; }
.day-head { display: flex; align-items: center; justify-content: space-between; gap: 10px; margin-bottom: 10px; }
.day-num { font-size: 1rem; font-weight: 800; color: #0F172A; }
.day-date { display: inline-flex; align-items: center; gap: 6px; font-size: 0.82rem; color: #059669; font-weight: 600; }
.timeline-activity { background: #F8FAFC; padding: 10px 12px; border-radius: 10px; margin-top: 8px; border: 1px solid #E2E8F0; }
.timeline-activity .t { display: flex; align-items: center; gap: 8px; font-weight: 700; color: #0F172A; font-size: 0.92rem; }
.timeline-activity .m { font-size: 0.8rem; color: #64748B; margin: 2px 0 0 24px; }
.timeline-activity.free { color: #94A3B8; font-style: italic; }

/* --- LANDING SAMPLE TIMELINE --- */
.timeline { border-left: 3px solid #E2E8F0; padding-left: 20px; margin-left: 10px; }
.timeline-item { position: relative; margin-bottom: 22px; }
.timeline-dot { position: absolute; left: -29px; top: 4px; width: 14px; height: 14px; border-radius: 50%; background: #1E3A8A; border: 3px solid #FFFFFF; box-shadow: 0 0 0 2px #1E3A8A; }
.timeline-date { font-size: 0.85rem; font-weight: 700; color: #1E3A8A; text-transform: uppercase; }
</style>
""",
    unsafe_allow_html=True,
)


# -------------------- Helpers --------------------
def html_block(s):
    """Render an HTML string. Lines are joined so Streamlit never mistakes indented HTML for a code block."""
    st.markdown(
        "".join(line.strip() for line in s.strip().splitlines()), unsafe_allow_html=True
    )


def iata(label):
    return label.rsplit("(", 1)[-1].rstrip(")").strip()


def city(label):
    return label.split(" (")[0].strip()


def num(x):
    try:
        return float(x)
    except (TypeError, ValueError):
        return 0.0


def plural(n, word):
    return f"{n} {word}" if n == 1 else f"{n} {word}s"


def fmt_range(d1, d2):
    if d1.month == d2.month:
        return f"{d1.strftime('%b %d')}–{d2.strftime('%d')}"
    return f"{d1.strftime('%b %d')} – {d2.strftime('%b %d')}"


def source_badge(source):
    return (
        '<span class="badge-mock">Mock Data</span>'
        if "Mock" in (source or "")
        else '<span class="badge-real">Live Data</span>'
    )


def badge(name, theme, size=44, icon_size=22):
    fg, bg = THEMES[theme]
    return f'<span class="icon-badge" style="width:{size}px;height:{size}px;background:{bg};color:{fg};">{icon(name, icon_size, fg)}</span>'


def section_header(name, theme, title, count, sub):
    return (
        f'<div class="sec-head">{badge(name, theme)}'
        f'<div><div class="sec-title">{title}<span class="sec-count">{count}</span></div>'
        f'<div class="sec-sub">{sub}</div></div></div>'
    )


def load_airports():
    if "airport_list" not in ss:
        try:
            res = requests.get(AIRPORTS_URL, timeout=5)
            ss["airport_list"] = res.json() if res.ok else FALLBACK_AIRPORTS
        except Exception:
            ss["airport_list"] = FALLBACK_AIRPORTS
    return ss["airport_list"]


# -------------------- PDF GENERATOR --------------------
def generate_pdf(data):
    pdf = FPDF()
    pdf.add_page()

    pdf.set_font("helvetica", "B", 24)
    pdf.set_text_color(15, 23, 42)
    pdf.cell(0, 15, "TripWeaver: Travel Plan", ln=True, align="C")

    pdf.set_font("helvetica", "", 12)
    pdf.set_text_color(100, 116, 139)
    dest = data["trip_request"]["destination"]
    dates = (
        f"{data['trip_request']['start_date']} to {data['trip_request']['end_date']}"
    )
    pdf.cell(
        0,
        10,
        f"Destination: {dest}  |  Dates: {dates}  |  Travelers: {data['trip_request']['travelers']}",
        ln=True,
        align="C",
    )
    pdf.ln(10)

    pdf.set_font("helvetica", "B", 16)
    pdf.set_text_color(15, 23, 42)
    pdf.cell(0, 10, "Budget Breakdown", ln=True)
    pdf.set_font("helvetica", "", 12)
    budget = data["budget"]
    pdf.cell(0, 8, f"Total Estimated: PKR {budget['grand_total']:,.2f}", ln=True)
    pdf.cell(0, 8, f"Remaining Budget: PKR {budget['remaining_budget']:,.2f}", ln=True)
    pdf.ln(10)

    pdf.set_font("helvetica", "B", 16)
    pdf.cell(0, 10, "Day-by-Day Plan", ln=True)

    for day in [d for d in data["itinerary"]["days"] if d.get("activities")]:
        pdf.set_font("helvetica", "B", 12)
        pdf.set_text_color(30, 58, 138)
        pdf.cell(0, 8, f"Day {day['day_number']} - {day['date']}", ln=True)
        pdf.set_font("helvetica", "", 11)
        pdf.set_text_color(0, 0, 0)
        for act in day.get("activities", []):
            pdf.cell(
                0,
                6,
                f"  - {act['name']} ({act['estimated_duration_hours']} hours)",
                ln=True,
            )
        pdf.ln(4)

    return bytes(pdf.output())


# -------------------- Card builders (return HTML strings) --------------------
def flight_card(f, is_best, o_code, d_code):
    best = (
        f'<span class="badge-best">{icon("star", 12, "#2563EB", fill=True)} Best value</span>'
        if is_best
        else ""
    )
    return f"""
<div class="result-card">
<div class="card-header">
<div><div class="airline-name">{html.escape(f.get("airline", "Airline"))}</div>
<div class="badges">{source_badge(f.get("source", "Unknown"))}{best}</div></div>
<div class="price-tag">USD {num(f.get("price")):,.2f}</div>
</div>
<div class="flight-path">
<div class="path-point"><div class="path-time">{html.escape(str(f.get("departure_time", ""))[11:16])}</div><div class="path-city">{o_code}</div></div>
<div class="path-line"><span class="path-plane">{icon("plane", 20, "#1E3A8A")}</span></div>
<div class="path-point"><div class="path-time">{html.escape(str(f.get("arrival_time", ""))[11:16])}</div><div class="path-city">{d_code}</div></div>
</div>
</div>
"""


def stay_card(s, is_best):
    best = (
        f'<span class="badge-best">{icon("star", 12, "#2563EB", fill=True)} Best value</span>'
        if is_best
        else ""
    )
    return f"""
<div class="result-card">
<div class="card-header">
<div><div class="airline-name">{html.escape(s.get("property_name", "Hotel"))}</div>
<div class="card-sub">{html.escape(s.get("room_type", "Room"))}</div>
<div class="badges">{source_badge(s.get("source", "Unknown"))}{best}</div></div>
<div class="price-tag">USD {num(s.get("total_stay_cost")):,.2f}</div>
</div>
<div class="stat-row">
<span class="inline">{icon("star", 15, "#F59E0B", fill=True)} Rating {html.escape(str(s.get("rating", "N/A")))}</span>
<span class="inline">{icon("moon", 15, "#7C3AED")} USD {num(s.get("nightly_rate")):,.2f} per night</span>
</div>
</div>
"""


def day_card(day):
    acts = (
        "".join(
            f'<div class="timeline-activity"><div class="t">{icon("pin", 16, "#D97706")} {html.escape(a.get("name", "Activity"))}</div>'
            f'<div class="m">{html.escape(a.get("category", "General"))} · {a.get("estimated_duration_hours")} hours</div></div>'
            for a in day.get("activities", [])
        )
        or '<div class="timeline-activity free">Free time / Travel day</div>'
    )
    return (
        f'<div class="day-card"><div class="day-head"><span class="day-num">Day {day.get("day_number")}</span>'
        f'<span class="day-date">{icon("calendar", 14, "#059669")} {html.escape(str(day.get("date")))}</span></div>{acts}</div>'
    )


# -------------------- Search form --------------------
def render_search():
    req = ss.get("req", {})
    airports = load_airports()

    html_block(
        f"""
<div class="hero-wrapper">
<div class="logo-container">
{icon("plane", 34, "#FFFFFF", fill=True)}
<h1 class="logo-text">TripWeaver</h1>
</div>
<div class="hero-title">LET'S PLAN YOUR JOURNEY <span class="animated-plane">{icon("plane", 38, "#93C5FD")}</span></div>
<div class="hero-subtitle">Discover a new place. Our multi-agent AI will find the best flights, hotels, and activities that fit your budget.</div>
</div>
"""
    )

    def idx(label, fallback):
        return airports.index(label) if label in airports else fallback

    default_dest = next((i for i, x in enumerate(airports) if "(DXB)" in x), 0)

    with st.form("search_form"):
        c1, c2, c3, c4 = st.columns([2, 2, 1.5, 1.5])
        origin_sel = c1.selectbox(
            "FROM", airports, index=idx(req.get("origin_label"), 0)
        )
        dest_sel = c2.selectbox(
            "TO", airports, index=idx(req.get("dest_label"), default_dest)
        )
        departure_date = c3.date_input(
            "DEPARTURE", value=req.get("start", date.today() + timedelta(days=30))
        )
        return_date = c4.date_input(
            "RETURN", value=req.get("end", date.today() + timedelta(days=35))
        )

        c5, c6, c7, c8, c9 = st.columns([1.2, 1.4, 2.2, 1.6, 1.4])
        travelers = c5.number_input(
            "PASSENGERS", min_value=1, max_value=10, value=req.get("travelers", 2)
        )
        levels = ["Budget", "Mid-range", "Luxury"]
        accommodation = c6.selectbox(
            "ACCOMMODATION",
            levels,
            index=levels.index(req.get("accommodation", "Mid-range")),
        )
        interests = c7.multiselect(
            "INTERESTS",
            ["cultural", "food", "shopping", "adventure", "nature"],
            default=req.get("interests", ["cultural", "food"]),
        )
        budget = c8.number_input(
            "BUDGET (PKR)", min_value=10000, value=req.get("budget", 350000), step=10000
        )
        with c9:
            submitted = st.form_submit_button("Search trips", icon=":material/search:")

    if not submitted:
        return

    if return_date <= departure_date:
        st.error("Return date must be after the departure date.")
        return

    payload = {
        "origin": iata(origin_sel),
        "destination": iata(dest_sel),
        "start_date": departure_date.isoformat(),
        "end_date": return_date.isoformat(),
        "travelers": travelers,
        "budget_amount": budget,
        "budget_currency": "PKR",
        "accommodation_level": accommodation.lower(),
        "interests": interests,
        "pace": "moderate",
        "constraints": [],
    }
    data = None
    with st.status("Your agents are working…", expanded=True) as status:
        st.write(":material/flight: Flight Agent: searching fares")
        st.write(":material/hotel: Stay Agent: matching hotels")
        st.write(
            ":material/local_activity: Activity Agent: drafting your day-by-day plan"
        )
        st.write(
            ":material/account_balance_wallet: Budget Agent: checking costs against your budget"
        )
        try:
            response = requests.post(PLAN_URL, json=payload, timeout=180)
            response.raise_for_status()
            data = response.json()
            status.update(label="Your plan is ready", state="complete", expanded=False)
        except Exception as e:
            status.update(label="Something went wrong", state="error")
            st.error(f"API error: {e}")

    if data:
        ss["result"] = data
        ss["req"] = {
            "origin_label": origin_sel,
            "dest_label": dest_sel,
            "origin": iata(origin_sel),
            "destination": iata(dest_sel),
            "start": departure_date,
            "end": return_date,
            "travelers": travelers,
            "accommodation": accommodation,
            "interests": interests,
            "budget": budget,
        }


# -------------------- Landing content (only before the first search) --------------------
def render_landing_bands():
    trips = "".join(
        f'<div class="mini-card"><div class="mini-title">{c}</div><div class="mini-meta">{code} · {n}</div><div class="mini-price">From PKR {p}</div></div>'
        for c, code, n, p in POPULAR_TRIPS
    )
    agents = "".join(
        f'<div class="mini-card">{badge(i, th, 44, 22)}<div class="mini-title" style="margin-top:10px;">{t}</div><div class="mini-text">{d}</div></div>'
        for i, th, t, d in AGENTS
    )
    sample = "".join(
        f'<div class="timeline-item"><div class="timeline-dot"></div><div class="timeline-date">{d}</div>'
        + "".join(
            f'<div class="timeline-activity"><div class="t">{icon("pin", 16, "#D97706")} {a}</div></div>'
            for a in acts
        )
        + "</div>"
        for d, acts in SAMPLE_DAYS
    )
    html_block(
        f"""
<div class="band"><div class="band-title">Popular trips from Aalborg</div><div class="band-sub">Sample budgets for 2 travelers, mid-range stay.</div><div class="grid-4">{trips}</div></div>
<div class="band"><div class="band-title">Four agents, one plan</div><div class="band-sub">Each one handles a part of your trip, then they check each other's work.</div><div class="grid-4">{agents}</div></div>
<div class="band"><div class="band-title">What you will get</div><div class="band-sub">A sample day-by-day plan.</div><div class="timeline">{sample}</div></div>
"""
    )


# -------------------- Results (rendered directly under the search form) --------------------
def render_results():
    req = ss["req"]
    result = ss["result"]
    bd = result.get("budget", {})
    validation = result.get("validation", {})
    itinerary = result.get("itinerary", {})
    agent_messages = result.get("agent_messages", [])

    def get_agent_data(name):
        for msg in agent_messages:
            if msg.get("agent_name") == name:
                return msg.get("data")
        return None

    flights = get_agent_data("FlightAgent") or []
    stays = get_agent_data("StayAgent") or []
    days = itinerary.get("days", [])
    activities = [
        (d.get("day_number"), act) for d in days for act in d.get("activities", [])
    ]

    o_code = html.escape(req["origin"].upper())
    d_code = html.escape(req["destination"].upper())
    start, end = req["start"], req["end"]
    nights = (end - start).days
    total_budget = req["budget"]

    segments = [
        ("Flights", num(bd.get("flights_total")), "#2563EB"),
        ("Hotel", num(bd.get("stay_total")), "#7C3AED"),
        ("Activities", num(bd.get("activities_total")), "#F59E0B"),
        (
            "Food and other",
            num(bd.get("food_estimate"))
            + num(bd.get("transport_estimate"))
            + num(bd.get("misc_estimate")),
            "#94A3B8",
        ),
    ]
    grand_total = num(bd.get("grand_total", sum(s[1] for s in segments)))
    remaining = num(bd.get("remaining_budget", total_budget - grand_total))
    rem_color = "#EF4444" if remaining < 0 else "#10B981"
    fits = validation.get("status") != "FAIL"

    # ---- Summary bar ----
    chips = "".join(
        f'<span class="chip">{html.escape(i)}</span>' for i in req["interests"]
    )
    html_block(
        f"""
<div class="bar">
<span class="bar-route">{html.escape(city(req["origin_label"]))} {icon("arrow", 18, "#1E3A8A")} {html.escape(city(req["dest_label"]))}</span>
<span class="bar-meta">{icon("calendar", 16, "#64748B")} {fmt_range(start, end)} · {plural(nights, "night")}</span>
<span class="bar-meta">{icon("users", 16, "#64748B")} {plural(req["travelers"], "passenger")}</span>
<span class="bar-meta">{icon("bed", 16, "#64748B")} {html.escape(req["accommodation"])} stay</span>
<span>{chips}</span>
<div class="bar-total">
<div class="bar-stat"><div class="l">Estimated total</div><div class="v">PKR {grand_total:,.0f}</div></div>
<div class="bar-stat"><div class="l">{"Over budget" if remaining < 0 else "Remaining"}</div><div class="v" style="color:{rem_color};">PKR {abs(remaining):,.0f}</div></div>
</div>
</div>
"""
    )

    # ---- Overview: recommendation + budget ----
    left, right = st.columns([1.6, 1], gap="large")
    with left:
        if flights or stays:
            parts = []
            if flights:
                parts.append(
                    f'<span class="item">{icon("plane", 20, "#93C5FD")} {html.escape(flights[0].get("airline", "Airline"))}</span>'
                )
            if stays:
                parts.append(
                    f'<span class="item">{icon("bed", 20, "#93C5FD")} {html.escape(stays[0].get("property_name", "Hotel"))}</span>'
                )
            verdict = "fits your budget" if fits else "is over your budget"
            html_block(
                f"""
<div class="combo"><div class="combo-tag">{icon("sparkles", 16, "#93C5FD")} Recommended combination</div>
<div class="combo-body">{'<span class="plus">+</span>'.join(parts)}</div>
<div class="combo-meta">Estimated total <strong>PKR {grand_total:,.0f}</strong> for the whole trip, which {verdict}.</div></div>
"""
            )
        if fits:
            html_block(
                f'<div class="status ok">{icon("check", 20, "#059669")} This plan fits within your budget.</div>'
            )
        else:
            issue = html.escape(str((validation.get("issues") or ["Unknown issue"])[0]))
            html_block(
                f'<div class="status warn">{icon("alert", 20, "#DC2626")} <span><strong>Budget alert:</strong> {issue}</span></div>'
            )
        st.download_button(
            label="Download PDF plan",
            data=generate_pdf(result),
            file_name=f"TripWeaver_{req['origin']}_{req['destination']}.pdf",
            mime="application/pdf",
            icon=":material/download:",
        )

    with right:
        scale = max(total_budget, grand_total) or 1
        bar = "".join(
            f'<span style="width:{v / scale * 100:.2f}%; background:{c};"></span>'
            for _, v, c in segments
        )
        legend = "".join(
            f'<div class="legend-row"><span><span class="legend-dot" style="background:{c};"></span>{n}</span><span>PKR {v:,.0f}</span></div>'
            for n, v, c in segments
        )
        html_block(
            f"""
<div class="panel"><div class="panel-head">{badge("wallet", "budget", 36, 18)} Budget tracker</div>
<div class="kv"><span>Total budget</span><strong>PKR {total_budget:,.0f}</strong></div>
<div class="bar-track">{bar}</div>
{legend}
<div class="remaining"><span>{"Over budget" if remaining < 0 else "Remaining"}</span><span class="amount" style="color:{rem_color};">PKR {abs(remaining):,.0f}</span></div></div>
"""
        )

    # ---- Flights ----
    html_block('<div class="sec-divider"></div>')
    h, s = st.columns([3, 1], vertical_alignment="center")
    with h:
        html_block(
            section_header(
                "plane",
                "flights",
                "Flights",
                len(flights),
                f"{o_code} to {d_code}, one way fares",
            )
        )
    with s:
        flight_sort = st.selectbox(
            "Sort flights",
            ["Best value", "Lowest price", "Earliest departure"],
            key="flight_sort",
            label_visibility="collapsed",
        )
    indexed_flights = list(enumerate(flights))
    if flight_sort == "Lowest price":
        indexed_flights.sort(key=lambda t: num(t[1].get("price")))
    elif flight_sort == "Earliest departure":
        indexed_flights.sort(key=lambda t: str(t[1].get("departure_time", "")))
    if indexed_flights:
        cards = "".join(
            flight_card(f, i == 0, o_code, d_code) for i, f in indexed_flights
        )
        html_block(f'<div class="cards-grid">{cards}</div>')
    else:
        st.info("No flights found.")

    # ---- Hotels ----
    html_block('<div class="sec-divider"></div>')
    h, s = st.columns([3, 1], vertical_alignment="center")
    with h:
        html_block(
            section_header(
                "bed",
                "hotels",
                "Hotels",
                len(stays),
                f"{plural(nights, 'night')} in {html.escape(city(req['dest_label']))}",
            )
        )
    with s:
        hotel_sort = st.selectbox(
            "Sort hotels",
            ["Best value", "Highest rated", "Lowest price"],
            key="hotel_sort",
            label_visibility="collapsed",
        )
    indexed_stays = list(enumerate(stays))
    if hotel_sort == "Highest rated":
        indexed_stays.sort(key=lambda t: -num(t[1].get("rating")))
    elif hotel_sort == "Lowest price":
        indexed_stays.sort(key=lambda t: num(t[1].get("total_stay_cost")))
    if indexed_stays:
        cards = "".join(stay_card(s_, i == 0) for i, s_ in indexed_stays)
        html_block(f'<div class="cards-grid">{cards}</div>')
    else:
        st.info("No hotels found.")

    # ---- Day-by-day plan (only days that have activities) ----
    html_block('<div class="sec-divider"></div>')
    planned_days = [d for d in days if d.get("activities")]
    html_block(
        section_header(
            "ticket",
            "activities",
            "Day-by-day plan",
            len(planned_days),
            f"{plural(len(activities), 'activity')} across {plural(len(planned_days), 'day')}, matched to your interests",
        )
    )
    if planned_days:
        cards = "".join(day_card(d) for d in planned_days)
        html_block(f'<div class="cards-grid tight">{cards}</div>')
    else:
        st.info("No activities planned.")


# -------------------- Page --------------------
render_search()

if ss.get("result") and ss.get("req"):
    render_results()
else:
    render_landing_bands()
