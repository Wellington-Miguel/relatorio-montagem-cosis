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
    color: #50C878;
    font-weight: 600;
}

/* ── Cards de Métricas (Dashboard e Resumos) ─────────────── */
div[data-testid="metric-container"] {
    background-color: #12141A;
    border: 1px solid rgba(255, 255, 255, 0.05);
    border-radius: 8px;
    padding: 1rem 1.5rem;
    box-shadow: 0 4px 10px rgba(0, 0, 0, 0.2);
    transition: transform 0.2s ease, border-color 0.2s ease;
    border-left: 4px solid #50C878;
}
div[data-testid="metric-container"]:hover {
    transform: translateY(-2px);
    border-color: rgba(80, 200, 120, 0.3);
}
/* Estilo do Rótulo da Métrica */
div[data-testid="metric-container"] label {
    color: #A0AEC0 !important;
    font-weight: 500;
    font-size: 0.85rem !important;
    letter-spacing: 0.5px;
}
/* Estilo do Valor da Métrica */
div[data-testid="metric-container"] div[data-testid="stMetricValue"] {
    color: #FAFAFA !important;
    font-weight: 700;
    font-size: 2rem !important;
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
</style>
"""
