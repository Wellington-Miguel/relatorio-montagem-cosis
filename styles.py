"""
styles.py
CSS de Decoração Minimalista Moderna (Dark & Green Theme)
"""

CSS = """
<style>
/* ── Ajustes Globais Minimalistas ────────────────────────── */

/* Customização do Título Principal */
h1 {
    font-weight: 300 !important;
    letter-spacing: -1px;
}
h1 span {
    font-weight: 600;
}

/* ── Expanders ───────────────────────────────────────────── */
div[data-testid="stExpander"] {
    background-color: #12141A;
    border: 1px solid rgba(255, 255, 255, 0.05) !important;
    border-radius: 8px !important;
}
div[data-testid="stExpander"] summary p {
    color: #FAFAFA !important;
    font-weight: 500 !important;
    font-size: 0.95rem !important;
}
div[data-testid="stExpander"]:hover {
    border-color: rgba(80, 200, 120, 0.3) !important;
}

/* ── Badges Minimalistas (Status) ────────────────────────── */
.badge-ok, .badge-warn, .badge-err {
    padding: 0.2rem 0.6rem;
    border-radius: 4px;
    font-size: 0.75rem;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.5px;
}
.badge-ok { background: rgba(80, 200, 120, 0.1); color: #50C878; border: 1px solid rgba(80, 200, 120, 0.2); }
.badge-warn { background: rgba(245, 158, 11, 0.1); color: #F59E0B; border: 1px solid rgba(245, 158, 11, 0.2); }
.badge-err { background: rgba(239, 68, 68, 0.1); color: #EF4444; border: 1px solid rgba(239, 68, 68, 0.2); }

/* ── Inputs e Selectboxes Focados ────────────────────────── */
div[data-baseweb="input"] > div, div[data-baseweb="select"] > div {
    background-color: #12141A !important;
    border: 1px solid rgba(255, 255, 255, 0.1) !important;
    border-radius: 6px;
    transition: border-color 0.2s;
}
div[data-baseweb="input"] > div:focus-within, div[data-baseweb="select"] > div:focus-within {
    border-color: #50C878 !important;
    box-shadow: none !important;
}

/* ── Linhas separadoras sutis ────────────────────────────── */
hr { border-color: rgba(255, 255, 255, 0.05) !important; margin: 2rem 0; }

/* ── Navegação Lateral (botões) ──────────────────────────── */
section[data-testid="stSidebar"] .stButton > button {
    text-align: left !important;
    justify-content: flex-start !important;
    border-radius: 8px !important;
    font-size: 0.88em !important;
    font-weight: 500 !important;
    padding: 0.45rem 0.85rem !important;
    transition: background 0.15s ease, color 0.15s ease,
                border-color 0.15s ease !important;
    box-shadow: none !important;
    width: 100% !important;
    margin-bottom: 2px !important;
}
section[data-testid="stSidebar"] .stButton > button[kind="secondary"] {
    background: transparent !important;
    border: 1px solid transparent !important;
    color: #9CA3AF !important;
}
section[data-testid="stSidebar"] .stButton > button[kind="secondary"]:hover {
    background: rgba(255, 255, 255, 0.05) !important;
    color: #E5E7EB !important;
    border-color: rgba(255, 255, 255, 0.07) !important;
}
section[data-testid="stSidebar"] .stButton > button[kind="primary"] {
    background: rgba(80, 200, 120, 0.1) !important;
    border: 1px solid rgba(80, 200, 120, 0.28) !important;
    color: #50C878 !important;
}
section[data-testid="stSidebar"] .stButton > button[kind="primary"]:hover {
    background: rgba(80, 200, 120, 0.17) !important;
}

/* ── Histórico de Auditoria — Diff Visual ────────────────── */
.diff-row {
    display: flex;
    align-items: center;
    gap: 8px;
    padding: 5px 10px;
    border-radius: 6px;
    background: rgba(255,255,255,0.025);
    margin-bottom: 3px;
}
.diff-label {
    min-width: 170px;
    font-size: 0.82em;
    color: #9CA3AF;
    font-weight: 500;
    flex-shrink: 0;
}
.diff-antes {
    background: rgba(239, 68, 68, 0.12);
    color: #F87171;
    padding: 2px 9px;
    border-radius: 4px;
    font-family: monospace;
    font-size: 0.82em;
    text-decoration: line-through;
    opacity: 0.85;
}
.diff-depois {
    background: rgba(80, 200, 120, 0.12);
    color: #50C878;
    padding: 2px 9px;
    border-radius: 4px;
    font-family: monospace;
    font-size: 0.82em;
    font-weight: 600;
}
.diff-arrow { color: #4B5563; font-size: 0.9em; }
.diff-equip-header {
    font-size: 0.73em;
    font-weight: 700;
    color: #6B7280;
    text-transform: uppercase;
    letter-spacing: 0.07em;
    margin: 12px 0 4px 0 !important;
}
.diff-equip-name {
    font-size: 0.83em;
    font-weight: 600;
    color: #D1D5DB;
    padding: 4px 6px 2px;
    margin: 0 !important;
}
</style>
"""
