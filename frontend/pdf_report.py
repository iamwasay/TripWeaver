"""Professional PDF export for TripWeaver (fpdf2, built-in fonts only).

Usage in app.py:
    from pdf_report import generate_pdf
    pdf_bytes = generate_pdf(result, req)   # req (the stored search form values) is optional
"""

from datetime import date, datetime

from fpdf import FPDF

# -------------------- Theme (matches the web app) --------------------
NAVY = (15, 23, 42)
BLUE = (30, 58, 138)
ACCENT = (37, 99, 235)
SLATE = (51, 65, 85)
MUTED = (100, 116, 139)
BORDER = (226, 232, 240)
LIGHT = (248, 250, 252)
WHITE = (255, 255, 255)
GREEN = (5, 150, 105)
RED = (220, 38, 38)
PURPLE = (124, 58, 237)
AMBER = (217, 119, 6)
SKY = (147, 197, 253)

LEFT = 15  # left/right margin (mm)
WIDTH = 180  # usable width on A4 (mm)
TOP = 22  # first y on continuation pages
BOTTOM = 20  # space kept free for the footer
LINE_H = 4.6

CATEGORY_COLORS = [
    (37, 99, 235),
    (124, 58, 237),
    (245, 158, 11),
    (16, 185, 129),
    (100, 116, 139),
    (148, 163, 184),
]

_REPLACE = {
    "\u2013": "-",
    "\u2014": "-",
    "\u2018": "'",
    "\u2019": "'",
    "\u201c": '"',
    "\u201d": '"',
    "\u2022": "-",
    "\u2026": "...",
    "\u00a0": " ",
    "\u2192": "to",
}


# -------------------- Small helpers --------------------
def clean_text(text):
    """Built-in PDF fonts only support Latin-1, so swap common symbols and drop the rest."""
    s = "" if text is None else str(text)
    for k, v in _REPLACE.items():
        s = s.replace(k, v)
    return s.encode("latin-1", "ignore").decode("latin-1")


def num(x):
    try:
        return float(x)
    except (TypeError, ValueError):
        return 0.0


def pkr(x):
    return f"PKR {num(x):,.0f}"


def usd(x):
    return f"USD {num(x):,.2f}"


def plural(n, word, many=None):
    return f"{n} {word}" if n == 1 else f"{n} {many or word + 's'}"


def city(label):
    return str(label).split(" (")[0].strip()


def to_date(x):
    if isinstance(x, datetime):
        return x.date()
    if isinstance(x, date):
        return x
    try:
        return datetime.strptime(str(x)[:10], "%Y-%m-%d").date()
    except ValueError:
        return None


def fmt_dt(s):
    try:
        return datetime.strptime(
            str(s or "").replace("T", " ")[:16], "%Y-%m-%d %H:%M"
        ).strftime("%d %b, %H:%M")
    except ValueError:
        return str(s)[:16] if s else "-"


def fmt_day(s):
    d = to_date(s)
    return d.strftime("%a, %d %b %Y") if d else str(s)


def source_label(source):
    return "Sample" if "Mock" in (source or "") else "Live"


# -------------------- Page furniture --------------------
class TripPDF(FPDF):
    def __init__(self, route_label, prepared):
        super().__init__(orientation="P", unit="mm", format="A4")
        self.route_label = route_label
        self.prepared = prepared
        self.set_auto_page_break(auto=False)
        self.set_margins(LEFT, 15, LEFT)
        self.alias_nb_pages()

    def header(self):
        if self.page_no() == 1:
            return  # page 1 has the full banner
        self.set_font("helvetica", "B", 8.5)
        self.set_text_color(*MUTED)
        self.set_xy(LEFT, 9)
        self.cell(WIDTH / 2, 5, "TripWeaver  |  " + self.route_label)
        self.set_font("helvetica", "", 8.5)
        self.set_xy(LEFT + WIDTH / 2, 9)
        self.cell(WIDTH / 2, 5, "Prepared " + self.prepared, align="R")
        self.set_draw_color(*BORDER)
        self.line(LEFT, 15, LEFT + WIDTH, 15)

    def footer(self):
        self.set_draw_color(*BORDER)
        self.line(LEFT, self.h - 16, LEFT + WIDTH, self.h - 16)
        self.set_font("helvetica", "", 8)
        self.set_text_color(*MUTED)
        self.set_xy(LEFT, self.h - 13)
        self.cell(
            WIDTH - 30,
            5,
            "TripWeaver AI Travel Planner  |  Prices are estimates; confirm with providers before booking.",
        )
        self.set_xy(LEFT + WIDTH - 30, self.h - 13)
        self.cell(30, 5, "Page " + str(self.page_no()) + " of {nb}", align="R")


def ensure_space(pdf, h):
    if pdf.get_y() + h > pdf.h - BOTTOM:
        pdf.add_page()
        pdf.set_y(TOP)


def wrap(pdf, text, max_w):
    """Word-wrap text to max_w using the current font. Breaks very long words."""
    lines = []
    for para in str(text).split("\n"):
        cur = ""
        for word in para.split(" "):
            trial = (cur + " " + word).strip()
            if pdf.get_string_width(trial) <= max_w:
                cur = trial
                continue
            if cur:
                lines.append(cur)
                cur = ""
            while pdf.get_string_width(word) > max_w and len(word) > 1:
                k = len(word)
                while k > 1 and pdf.get_string_width(word[:k]) > max_w:
                    k -= 1
                lines.append(word[:k])
                word = word[k:]
            cur = word
        lines.append(cur)
    return lines or [""]


def fit(pdf, text, max_w, size, style="B", min_size=7):
    """Shrink the font (then truncate) so text fits on one line."""
    while size > min_size:
        pdf.set_font("helvetica", style, size)
        if pdf.get_string_width(text) <= max_w:
            return text
        size -= 0.5
    pdf.set_font("helvetica", style, min_size)
    while len(text) > 1 and pdf.get_string_width(text) > max_w:
        text = text[:-4] + "..." if len(text) > 4 else text[:-1]
    return text


def section(pdf, title, subtitle, color):
    ensure_space(pdf, 28)
    y = pdf.get_y() + 3
    pdf.set_fill_color(*color)
    pdf.rect(LEFT, y, 3, 9, "F")
    pdf.set_font("helvetica", "B", 14)
    pdf.set_text_color(*NAVY)
    pdf.set_xy(LEFT + 6, y)
    pdf.cell(90, 9, clean_text(title))
    if subtitle:
        pdf.set_font("helvetica", "", 9)
        pdf.set_text_color(*MUTED)
        pdf.set_xy(LEFT + 90, y)
        pdf.cell(WIDTH - 90, 9, clean_text(subtitle), align="R")
    pdf.set_y(y + 13)


def tile_row(pdf, items):
    """items: list of (label, value, value_color)."""
    n, gap, h = len(items), 4, 19
    w = (WIDTH - gap * (n - 1)) / n
    ensure_space(pdf, h + 4)
    y = pdf.get_y()
    for i, (label, value, color) in enumerate(items):
        x = LEFT + i * (w + gap)
        pdf.set_fill_color(*LIGHT)
        pdf.set_draw_color(*BORDER)
        pdf.rect(x, y, w, h, "DF")
        pdf.set_font("helvetica", "B", 7)
        pdf.set_text_color(*MUTED)
        pdf.set_xy(x + 3, y + 3)
        pdf.cell(w - 6, 4, clean_text(label).upper())
        text = fit(pdf, clean_text(value), w - 6, 12)
        pdf.set_text_color(*color)
        pdf.set_xy(x + 3, y + 9)
        pdf.cell(w - 6, 7, text)
    pdf.set_y(y + h + 4)


def table(pdf, cols, rows, head_color):
    """cols: list of (title, width, align). First data row is highlighted as the recommended pick."""
    ensure_space(pdf, 7.5 + 14)

    def head():
        y = pdf.get_y()
        pdf.set_fill_color(*head_color)
        pdf.rect(LEFT, y, WIDTH, 7.5, "F")
        pdf.set_font("helvetica", "B", 8)
        pdf.set_text_color(*WHITE)
        x = LEFT
        for title, w, al in cols:
            pdf.set_xy(x + 2, y + 1.5)
            pdf.cell(w - 4, 4.5, title, align=al)
            x += w
        pdf.set_y(y + 7.5)

    head()
    for r, row in enumerate(rows):
        cells = []
        for c, (_, w, _) in enumerate(cols):
            pdf.set_font("helvetica", "B" if c == 0 else "", 8.8)
            cells.append(wrap(pdf, clean_text(row[c]), w - 4))
        h = max(len(c) for c in cells) * LINE_H + 4
        if pdf.get_y() + h > pdf.h - BOTTOM:
            pdf.add_page()
            pdf.set_y(TOP)
            head()
        y = pdf.get_y()
        fill = (239, 246, 255) if r == 0 else (LIGHT if r % 2 else WHITE)
        pdf.set_fill_color(*fill)
        pdf.rect(LEFT, y, WIDTH, h, "F")
        pdf.set_draw_color(*BORDER)
        pdf.line(LEFT, y + h, LEFT + WIDTH, y + h)
        x = LEFT
        for c, ((_, w, al), lines) in enumerate(zip(cols, cells)):
            pdf.set_font("helvetica", "B" if c == 0 else "", 8.8)
            pdf.set_text_color(*(NAVY if c == 0 else SLATE))
            for k, line in enumerate(lines):
                pdf.set_xy(x + 2, y + 2 + k * LINE_H)
                pdf.cell(w - 4, LINE_H, line, align=al)
            x += w
        pdf.set_y(y + h)
    pdf.set_y(pdf.get_y() + 6)


def callout(pdf, headline, lines, color, bg):
    """Tinted box with a colored accent bar, a bold headline and wrapped detail lines."""
    pdf.set_font("helvetica", "", 9)
    body = []
    for ln in lines:
        body += wrap(pdf, clean_text(ln), WIDTH - 16)
    h = 10 + len(body) * LINE_H + (2 if body else 0)
    ensure_space(pdf, h + 4)
    y = pdf.get_y()
    pdf.set_fill_color(*bg)
    pdf.rect(LEFT, y, WIDTH, h, "F")
    pdf.set_fill_color(*color)
    pdf.rect(LEFT, y, 2.5, h, "F")
    pdf.set_font("helvetica", "B", 10)
    pdf.set_text_color(*color)
    pdf.set_xy(LEFT + 8, y + 3)
    pdf.cell(WIDTH - 16, 5, clean_text(headline))
    pdf.set_font("helvetica", "", 9)
    pdf.set_text_color(*SLATE)
    for k, ln in enumerate(body):
        pdf.set_xy(LEFT + 8, y + 9.5 + k * LINE_H)
        pdf.cell(WIDTH - 16, LINE_H, ln)
    pdf.set_y(y + h + 4)


def combo_box(pdf, items):
    """Dark 'recommended combination' box. items: list of (label, text)."""
    pdf.set_font("helvetica", "", 9.5)
    blocks = [(lab, wrap(pdf, clean_text(t), WIDTH - 34)) for lab, t in items]
    h = 14 + sum(len(lines) * 4.8 + 2 for _, lines in blocks)
    ensure_space(pdf, h + 4)
    y = pdf.get_y()
    pdf.set_fill_color(*NAVY)
    pdf.rect(LEFT, y, WIDTH, h, "F")
    pdf.set_fill_color(*ACCENT)
    pdf.rect(LEFT, y, 2.5, h, "F")
    pdf.set_font("helvetica", "B", 7.5)
    pdf.set_text_color(*SKY)
    pdf.set_xy(LEFT + 8, y + 4)
    pdf.cell(100, 4, "RECOMMENDED COMBINATION")
    yy = y + 10.5
    for label, lines in blocks:
        pdf.set_font("helvetica", "B", 9)
        pdf.set_text_color(*SKY)
        pdf.set_xy(LEFT + 8, yy)
        pdf.cell(16, 4.8, label)
        pdf.set_font("helvetica", "", 9.5)
        pdf.set_text_color(*WHITE)
        for k, line in enumerate(lines):
            pdf.set_xy(LEFT + 26, yy + k * 4.8)
            pdf.cell(WIDTH - 34, 4.8, line)
        yy += len(lines) * 4.8 + 2
    pdf.set_y(y + h + 5)


# -------------------- Sections --------------------
def budget_section(pdf, bd, total_budget, fits, issues):
    cats = [
        ("Flights", num(bd.get("flights_total"))),
        ("Accommodation", num(bd.get("stay_total"))),
        ("Activities", num(bd.get("activities_total"))),
        ("Food (estimate)", num(bd.get("food_estimate"))),
        ("Local transport (estimate)", num(bd.get("transport_estimate"))),
        ("Miscellaneous (estimate)", num(bd.get("misc_estimate"))),
    ]
    grand = num(bd.get("grand_total", sum(v for _, v in cats)))
    remaining = num(bd.get("remaining_budget", total_budget - grand))
    scale = max(total_budget, grand) or 1

    section(pdf, "Budget breakdown", "All amounts in PKR", NAVY)
    ensure_space(pdf, 12 + 7.5 * (len(cats) + 3) + 30)

    # Stacked usage bar
    y = pdf.get_y()
    pdf.set_fill_color(*BORDER)
    pdf.rect(LEFT, y, WIDTH, 7, "F")
    x = LEFT
    for i, (_, v) in enumerate(cats):
        w = v / scale * WIDTH
        if w > 0:
            pdf.set_fill_color(*CATEGORY_COLORS[i])
            pdf.rect(x, y, w, 7, "F")
            x += w
    used = (grand / total_budget * 100) if total_budget else 0
    pdf.set_font("helvetica", "", 8.5)
    pdf.set_text_color(*MUTED)
    pdf.set_xy(LEFT, y + 9)
    pdf.cell(
        WIDTH,
        5,
        f"Estimated cost {pkr(grand)} of {pkr(total_budget)} budget ({used:.0f}% used)",
    )
    pdf.set_y(y + 18)

    # Category rows
    for i, (name, v) in enumerate(cats):
        y = pdf.get_y()
        if i % 2:
            pdf.set_fill_color(*LIGHT)
            pdf.rect(LEFT, y, WIDTH, 7.5, "F")
        pdf.set_fill_color(*CATEGORY_COLORS[i])
        pdf.rect(LEFT + 3, y + 2.3, 3, 3, "F")
        pdf.set_font("helvetica", "", 9.5)
        pdf.set_text_color(*SLATE)
        pdf.set_xy(LEFT + 9, y + 1.2)
        pdf.cell(68, 5, name)
        share = v / grand if grand else 0
        pdf.set_fill_color(*BORDER)
        pdf.rect(LEFT + 80, y + 2.6, 44, 2.4, "F")
        pdf.set_fill_color(*CATEGORY_COLORS[i])
        pdf.rect(LEFT + 80, y + 2.6, 44 * share, 2.4, "F")
        pdf.set_text_color(*NAVY)
        pdf.set_xy(LEFT + 126, y + 1.2)
        pdf.cell(34, 5, f"{v:,.0f}", align="R")
        pdf.set_text_color(*MUTED)
        pdf.set_xy(LEFT + 160, y + 1.2)
        pdf.cell(18, 5, f"{share * 100:.0f}%", align="R")
        pdf.set_y(y + 7.5)

    # Totals
    y = pdf.get_y() + 1
    pdf.set_draw_color(*NAVY)
    pdf.line(LEFT, y, LEFT + WIDTH, y)
    totals = [
        ("Total estimated cost", pkr(grand), NAVY, "B"),
        ("Your budget", pkr(total_budget), SLATE, ""),
        (
            "Over budget by" if remaining < 0 else "Remaining budget",
            pkr(abs(remaining)),
            RED if remaining < 0 else GREEN,
            "B",
        ),
    ]
    pdf.set_y(y + 1)
    for label, value, color, style in totals:
        y = pdf.get_y()
        pdf.set_font("helvetica", style, 10)
        pdf.set_text_color(*color)
        pdf.set_xy(LEFT + 9, y + 1)
        pdf.cell(100, 5.5, label)
        pdf.set_xy(LEFT + 100, y + 1)
        pdf.cell(78, 5.5, value, align="R")
        pdf.set_y(y + 7)
    pdf.set_y(pdf.get_y() + 3)

    if fits:
        callout(
            pdf,
            "This plan fits within your budget",
            [f"You would have about {pkr(remaining)} left over for extras."],
            GREEN,
            (236, 253, 245),
        )
    else:
        callout(
            pdf,
            "Budget alert",
            [str(i) for i in (issues or ["This plan exceeds your budget."])],
            RED,
            (254, 242, 242),
        )


def day_block(pdf, day):
    acts = day.get("activities", []) or []
    pdf.set_font("helvetica", "B", 9.5)
    items = []
    for a in acts:
        name_lines = wrap(pdf, clean_text(a.get("name", "Activity")), WIDTH - 20)
        meta = f"{str(a.get('category', 'General')).title()}  |  {a.get('estimated_duration_hours', '-')} hours"
        items.append((name_lines, clean_text(meta)))
    h = 10 + sum(len(nl) * 4.8 + 4.4 + 2.6 for nl, _ in items) + 1
    ensure_space(pdf, h + 4)
    y = pdf.get_y()

    pdf.set_fill_color(236, 253, 245)
    pdf.rect(LEFT, y, WIDTH, 8.5, "F")
    pdf.set_draw_color(*BORDER)
    pdf.rect(LEFT, y, WIDTH, h, "D")
    pdf.set_font("helvetica", "B", 10)
    pdf.set_text_color(*NAVY)
    label = f"Day {day.get('day_number')}"
    pdf.set_xy(LEFT + 4, y + 1.7)
    pdf.cell(18, 5, label)
    pdf.set_font("helvetica", "", 9)
    pdf.set_text_color(*GREEN)
    pdf.set_xy(LEFT + 4 + pdf.get_string_width(label) + 4, y + 1.9)
    pdf.cell(80, 5, clean_text(fmt_day(day.get("date"))))
    hours = sum(num(a.get("estimated_duration_hours")) for a in acts)
    pdf.set_text_color(*MUTED)
    pdf.set_xy(LEFT + WIDTH - 54, y + 1.9)
    pdf.cell(50, 5, f"{hours:.1f} hrs planned", align="R")

    yy = y + 10.5
    for name_lines, meta in items:
        pdf.set_fill_color(*AMBER)
        pdf.rect(LEFT + 5, yy + 1.4, 2, 2, "F")
        pdf.set_font("helvetica", "B", 9.5)
        pdf.set_text_color(*NAVY)
        for k, line in enumerate(name_lines):
            pdf.set_xy(LEFT + 10, yy + k * 4.8)
            pdf.cell(WIDTH - 20, 4.8, line)
        yy += len(name_lines) * 4.8
        pdf.set_font("helvetica", "", 8.5)
        pdf.set_text_color(*MUTED)
        pdf.set_xy(LEFT + 10, yy)
        pdf.cell(WIDTH - 20, 4.4, meta)
        yy += 4.4 + 2.6
    pdf.set_y(y + h + 4)


# -------------------- Public entry point --------------------
def generate_pdf(data, req=None):
    req = req or {}
    tr = data.get("trip_request") or {}
    bd = data.get("budget") or {}
    validation = data.get("validation") or {}
    days = (data.get("itinerary") or {}).get("days") or []
    msgs = data.get("agent_messages") or []

    def agent(name):
        for m in msgs:
            if m.get("agent_name") == name:
                return m.get("data") or []
        return []

    flights, stays = agent("FlightAgent"), agent("StayAgent")

    o_code = clean_text(req.get("origin") or tr.get("origin") or "").upper()
    d_code = clean_text(req.get("destination") or tr.get("destination") or "").upper()
    o_city = (
        clean_text(city(req["origin_label"])) if req.get("origin_label") else o_code
    )
    d_city = clean_text(city(req["dest_label"])) if req.get("dest_label") else d_code
    start = to_date(req.get("start") or tr.get("start_date"))
    end = to_date(req.get("end") or tr.get("end_date"))
    nights = (end - start).days if start and end else 0
    travelers = int(num(req.get("travelers") or tr.get("travelers") or 1))
    stay_level = clean_text(
        req.get("accommodation")
        or str(tr.get("accommodation_level", "")).title()
        or "-"
    )
    interests = req.get("interests") or tr.get("interests") or []

    cats_total = sum(
        num(bd.get(k))
        for k in (
            "flights_total",
            "stay_total",
            "activities_total",
            "food_estimate",
            "transport_estimate",
            "misc_estimate",
        )
    )
    grand = num(bd.get("grand_total", cats_total))
    remaining = num(bd.get("remaining_budget", 0))
    total_budget = num(
        req.get("budget") or tr.get("budget_amount") or (grand + remaining)
    )
    fits = validation.get("status") != "FAIL"

    prepared = date.today().strftime("%d %b %Y")
    route_label = f"{o_city} to {d_city}" if o_city else d_city
    date_str = f"{start:%d %b} - {end:%d %b %Y}" if start and end else "Dates not set"

    pdf = TripPDF(route_label, prepared)
    pdf.set_title(clean_text(f"TripWeaver travel plan: {route_label}"))
    pdf.set_author("TripWeaver")
    pdf.set_creator("TripWeaver AI Travel Planner")
    pdf.add_page()

    # ---- Banner ----
    pdf.set_fill_color(*NAVY)
    pdf.rect(0, 0, pdf.w, 46, "F")
    pdf.set_fill_color(*ACCENT)
    pdf.rect(0, 46, pdf.w, 2, "F")
    pdf.set_font("helvetica", "B", 9)
    pdf.set_text_color(*SKY)
    pdf.set_xy(LEFT, 11)
    pdf.cell(100, 5, "TRIPWEAVER  |  AI TRAVEL PLAN")
    pdf.set_font("helvetica", "", 9)
    pdf.set_xy(LEFT + 80, 11)
    pdf.cell(WIDTH - 80, 5, "Prepared " + prepared, align="R")
    pdf.set_text_color(*WHITE)
    pdf.set_xy(LEFT, 20)
    title = fit(pdf, route_label, WIDTH, 26)
    pdf.cell(WIDTH, 12, title)
    pdf.set_font("helvetica", "", 11)
    pdf.set_text_color(203, 213, 225)
    pdf.set_xy(LEFT, 34)
    pdf.cell(
        WIDTH,
        6,
        f"{date_str}   |   {plural(nights, 'night')}   |   {plural(travelers, 'traveler')}",
    )
    pdf.set_y(57)

    # ---- At a glance ----
    rem_label = "Over budget by" if remaining < 0 else "Remaining"
    tile_row(
        pdf,
        [
            ("Route", f"{o_code} to {d_code}" if o_code else d_code, NAVY),
            ("Dates", f"{start:%d %b} - {end:%d %b}" if start and end else "-", NAVY),
            ("Duration", plural(nights, "night"), NAVY),
            ("Travelers", str(travelers), NAVY),
        ],
    )
    tile_row(
        pdf,
        [
            ("Stay level", stay_level, NAVY),
            ("Budget", pkr(total_budget), NAVY),
            ("Estimated total", pkr(grand), NAVY),
            (rem_label, pkr(abs(remaining)), RED if remaining < 0 else GREEN),
        ],
    )
    if interests:
        pdf.set_font("helvetica", "B", 9)
        pdf.set_text_color(*NAVY)
        pdf.set_xy(LEFT, pdf.get_y())
        pdf.cell(20, 5, "Interests:")
        pdf.set_font("helvetica", "", 9)
        pdf.set_text_color(*SLATE)
        pdf.cell(WIDTH - 20, 5, clean_text(", ".join(str(i) for i in interests)))
        pdf.set_y(pdf.get_y() + 8)

    # ---- Recommended combination ----
    picks = []
    if flights:
        f = flights[0]
        picks.append(
            (
                "Flight",
                f"{f.get('airline', 'Airline')}  |  {o_code} {fmt_dt(f.get('departure_time'))} to {d_code} {fmt_dt(f.get('arrival_time'))}  |  {usd(f.get('price'))}",
            )
        )
    if stays:
        s = stays[0]
        picks.append(
            (
                "Hotel",
                f"{s.get('property_name', 'Hotel')}  |  {s.get('room_type', 'Room')}  |  {usd(s.get('total_stay_cost'))} for {plural(nights, 'night')}",
            )
        )
    if picks:
        combo_box(pdf, picks)

    # ---- Budget ----
    budget_section(pdf, bd, total_budget, fits, validation.get("issues"))

    # ---- Flights ----
    section(
        pdf,
        "Flights",
        f"{o_code} to {d_code}  |  {plural(len(flights), 'option')}  |  prices in USD",
        ACCENT,
    )
    if flights:
        rows = []
        for i, f in enumerate(flights):
            rows.append(
                [
                    f"{f.get('airline', 'Airline')}"
                    + ("  (Best value)" if i == 0 else ""),
                    fmt_dt(f.get("departure_time")),
                    fmt_dt(f.get("arrival_time")),
                    usd(f.get("price")),
                    source_label(f.get("source")),
                ]
            )
        table(
            pdf,
            [
                ("Airline", 58, "L"),
                ("Departs", 38, "L"),
                ("Arrives", 38, "L"),
                ("Price", 28, "R"),
                ("Data", 18, "L"),
            ],
            rows,
            ACCENT,
        )
    else:
        callout(
            pdf,
            "No flights found",
            ["No flight options were returned for this search."],
            MUTED,
            LIGHT,
        )

    # ---- Hotels ----
    section(
        pdf,
        "Hotels",
        f"{d_city}  |  {plural(nights, 'night')}  |  {plural(len(stays), 'option')}  |  prices in USD",
        PURPLE,
    )
    if stays:
        rows = []
        for i, s in enumerate(stays):
            rows.append(
                [
                    f"{s.get('property_name', 'Hotel')}"
                    + ("  (Best value)" if i == 0 else ""),
                    s.get("room_type", "Room"),
                    f"{s.get('rating', 'N/A')}",
                    usd(s.get("nightly_rate")),
                    usd(s.get("total_stay_cost")),
                    source_label(s.get("source")),
                ]
            )
        table(
            pdf,
            [
                ("Property", 58, "L"),
                ("Room", 34, "L"),
                ("Rating", 14, "L"),
                ("Per night", 28, "R"),
                ("Total stay", 28, "R"),
                ("Data", 18, "L"),
            ],
            rows,
            PURPLE,
        )
    else:
        callout(
            pdf,
            "No hotels found",
            ["No hotel options were returned for this search."],
            MUTED,
            LIGHT,
        )

    # ---- Day-by-day plan ----
    planned = [d for d in days if d.get("activities")]
    free = [d for d in days if not d.get("activities")]
    n_acts = sum(len(d.get("activities", [])) for d in planned)
    section(
        pdf,
        "Day-by-day plan",
        f"{plural(n_acts, 'activity', 'activities')} across {plural(len(planned), 'day')}",
        AMBER,
    )
    if planned:
        for d in planned:
            day_block(pdf, d)
        if free:
            names = ", ".join(f"Day {d.get('day_number')}" for d in free)
            callout(
                pdf,
                "Open days",
                [
                    f"No activities are scheduled on {names}. Use them to rest, explore freely, or travel."
                ],
                MUTED,
                LIGHT,
            )
    else:
        callout(
            pdf,
            "No activities planned",
            ["No activities were scheduled for this trip."],
            MUTED,
            LIGHT,
        )

    # ---- Good to know ----
    all_listings = list(flights) + list(stays)
    sample = sum(1 for x in all_listings if "Mock" in (x.get("source") or ""))
    notes = [
        "Prices are estimates and can change. Confirm availability and final cost with the airline or hotel before paying."
    ]
    if sample:
        notes.append(
            f"{plural(sample, 'listing')} marked Sample use demonstration data and cannot be booked as shown."
        )
    elif all_listings:
        notes.append("All flight and hotel listings in this plan are marked Live.")
    notes.append(
        "Flight and hotel prices are listed in USD. Budget figures are in PKR."
    )
    if d_city:
        notes.append(
            f"Check passport validity and visa or entry rules for {d_city} well before you travel."
        )
    notes.append(
        "Consider travel insurance, and confirm baggage allowances and check-in times with your airline."
    )
    section(pdf, "Good to know", "", MUTED)
    callout(pdf, "Before you book", ["- " + n for n in notes], ACCENT, (239, 246, 255))

    return bytes(pdf.output())
