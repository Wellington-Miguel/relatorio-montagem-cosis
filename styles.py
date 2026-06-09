"""
styles.py
CSS injetado globalmente no Streamlit.
"""

CSS = """
<style>
/* ── Header principal ─────────────────────────────────────── */
.main-header {
    background: linear-gradient(135deg, #1e3a5f 0%, #2d6a9f 100%);
    color: white;
    padding: 1.4rem 2rem;
    border-radius: 14px;
    margin-bottom: 1.6rem;
    text-align: center;
    box-shadow: 0 4px 16px rgba(45,106,159,.35);
}
.main-header h1 { margin: 0; font-size: 1.9rem; letter-spacing: .5px; }
.main-header p  { margin: .35rem 0 0; opacity: .88; font-size: .95rem; }

/* ── Caixas de alerta ─────────────────────────────────────── */
.alerta-box {
    background: #fff8e1;
    border-left: 6px solid #f9a825;
    border-radius: 10px;
    padding: 1rem 1.4rem;
    margin-bottom: 1.2rem;
    box-shadow: 0 2px 8px rgba(249,168,37,.15);
}
.alerta-box h4     { color: #6d4c00; margin: 0 0 .6rem; font-size: 1rem; }
.alerta-box ul     { margin: 0; padding-left: 1.3rem; }
.alerta-box ul li  { color: #5d4200; margin-bottom: .35rem; font-size: .93rem; }

/* ── Cards de estatísticas ────────────────────────────────── */
.stat-card {
    background: #fff;
    border: 1px solid #dce6f4;
    border-radius: 12px;
    padding: 1.1rem .8rem;
    text-align: center;
    box-shadow: 0 2px 8px rgba(30,58,95,.07);
    transition: transform .15s;
}
.stat-card:hover { transform: translateY(-2px); }
.stat-card .val   { font-size: 2.1rem; font-weight: 700; color: #1e3a5f; }
.stat-card .lbl   { font-size: .78rem; color: #6b7a8d; margin-top: .25rem; text-transform: uppercase; letter-spacing: .5px; }

/* ── Linha de equipamento ─────────────────────────────────── */
.equip-row {
    background: #f7f9fc;
    border: 1px solid #e0e8f4;
    border-radius: 10px;
    padding: .65rem 1.1rem;
    margin-bottom: .5rem;
    transition: background .1s;
}
.equip-row:hover { background: #edf3fb; }

/* ── Badges ───────────────────────────────────────────────── */
.badge-def { background: #dc3545; color: #fff; border-radius: 5px; padding: 2px 8px; font-size: .74rem; font-weight: 700; }
.badge-ok  { background: #198754; color: #fff; border-radius: 5px; padding: 2px 8px; font-size: .74rem; font-weight: 700; }
.badge-tip { background: #0d6efd; color: #fff; border-radius: 5px; padding: 2px 8px; font-size: .74rem; font-weight: 700; }

/* ── Expanders ────────────────────────────────────────────── */
div[data-testid="stExpander"] {
    border: 1px solid #dce6f4 !important;
    border-radius: 10px !important;
    margin-bottom: .5rem;
}

/* ── Sidebar ──────────────────────────────────────────────── */
section[data-testid="stSidebar"] { background: #1e3a5f; }
section[data-testid="stSidebar"] * { color: #e8f0fa !important; }
section[data-testid="stSidebar"] .stRadio label { font-size: .95rem; }

/* ── Botão primário ───────────────────────────────────────── */
div.stButton > button[kind="primary"] {
    background: linear-gradient(135deg, #1e3a5f, #2d6a9f);
    border: none;
    color: white;
    border-radius: 8px;
    font-weight: 600;
}
div.stButton > button[kind="primary"]:hover {
    background: linear-gradient(135deg, #2d6a9f, #1e3a5f);
}

/* ── Divisor ──────────────────────────────────────────────── */
hr { border-color: #dce6f4; }
</style>
"""
