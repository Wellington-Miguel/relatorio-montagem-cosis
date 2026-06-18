"""
database.py  —  Kit Biométrico
Backend PostgreSQL via psycopg2 (Supabase ou qualquer Postgres).
A connection string vem de st.secrets["DATABASE_URL"]
ou da variável de ambiente DATABASE_URL (para rodar localmente).
"""

import os
import psycopg2
import psycopg2.extras
import pandas as pd
import streamlit as st
from datetime import datetime


# ── Conexão ──────────────────────────────────────────────────────────────────

def _get_dsn() -> str:
    """Lê a DATABASE_URL de st.secrets (Streamlit Cloud) ou env (local)."""
    try:
        return st.secrets["DATABASE_URL"]
    except Exception:
        dsn = os.getenv("DATABASE_URL", "")
        if not dsn:
            raise RuntimeError(
                "DATABASE_URL não encontrada.\n"
                "Configure em .streamlit/secrets.toml ou como variável de ambiente."
            )
        return dsn


def get_conn():
    """Abre uma conexão PostgreSQL. Usa pool simples via st.cache_resource."""
    return psycopg2.connect(_get_dsn(), cursor_factory=psycopg2.extras.RealDictCursor)


@st.cache_resource(show_spinner=False)
def _pool():
    """Conexão persistente reutilizada entre reruns (cache_resource)."""
    conn = psycopg2.connect(_get_dsn(), cursor_factory=psycopg2.extras.RealDictCursor)
    conn.autocommit = False
    return conn


def _exec(sql: str, params=(), fetch: str = "none"):
    """Executa SQL no pool. fetch = 'one' | 'all' | 'none'."""
    conn = _pool()
    try:
        with conn.cursor() as cur:
            cur.execute(sql, params)
            if fetch == "all":
                result = [dict(r) for r in cur.fetchall()]
            elif fetch == "one":
                row = cur.fetchone()
                result = dict(row) if row else None
            else:
                result = None
            conn.commit()
            return result
    except Exception:
        conn.rollback()
        raise


# ── Inicialização do schema ───────────────────────────────────────────────────

def init_db():
    """Cria tabelas e índices se não existirem. Idempotente."""
    _exec("""
        CREATE TABLE IF NOT EXISTS registros (
            id          SERIAL PRIMARY KEY,
            tecnico     TEXT    NOT NULL,
            tipo        TEXT    NOT NULL CHECK (tipo IN ('Montagem','Desmontagem')),
            local       TEXT    NOT NULL,
            qtd_kits    INTEGER NOT NULL CHECK (qtd_kits >= 1),
            kits_usados TEXT    NOT NULL DEFAULT '',
            data_evento DATE    NOT NULL,
            observacoes TEXT    NOT NULL DEFAULT '',
            atualizado_em TIMESTAMP,
            criado_em   TIMESTAMP NOT NULL DEFAULT NOW()
        )
    """)
    _exec("""
        CREATE TABLE IF NOT EXISTS itens (
            id            SERIAL PRIMARY KEY,
            registro_id   INTEGER NOT NULL REFERENCES registros(id) ON DELETE CASCADE,
            equipamento   TEXT    NOT NULL,
            consta        BOOLEAN NOT NULL DEFAULT TRUE,
            defeituoso    BOOLEAN NOT NULL DEFAULT FALSE,
            kit_defeito   TEXT    NOT NULL DEFAULT '',
            obs_item      TEXT    NOT NULL DEFAULT ''
        )
    """)
    _exec("ALTER TABLE registros ADD COLUMN IF NOT EXISTS kits_usados TEXT NOT NULL DEFAULT '';")
    _exec("ALTER TABLE registros ADD COLUMN IF NOT EXISTS atualizado_em TIMESTAMP;")
    _exec("CREATE INDEX IF NOT EXISTS idx_reg_data    ON registros(data_evento)")
    _exec("CREATE INDEX IF NOT EXISTS idx_reg_tec     ON registros(tecnico)")
    _exec("CREATE INDEX IF NOT EXISTS idx_itens_def   ON itens(defeituoso)")
    _exec("CREATE INDEX IF NOT EXISTS idx_itens_regid ON itens(registro_id)")


# ── Escrita ───────────────────────────────────────────────────────────────────

def salvar_registro(tecnico, tipo, local, qtd_kits, kits_usados, data_evento, observacoes, itens) -> int:
    conn = _pool()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """INSERT INTO registros (tecnico, tipo, local, qtd_kits, kits_usados, data_evento, observacoes)
                   VALUES (%s, %s, %s, %s, %s, %s, %s) RETURNING id""",
                (tecnico, tipo, local, int(qtd_kits), kits_usados, str(data_evento), observacoes or ""),
            )
            rid = cur.fetchone()["id"]

            psycopg2.extras.execute_values(
                cur,
                """INSERT INTO itens
                   (registro_id, equipamento, consta, defeituoso, kit_defeito, obs_item)
                   VALUES %s""",
                [
                    (rid, i["equipamento"], bool(i["consta"]), bool(i["defeituoso"]),
                     i.get("kit_defeito") or "", i.get("obs_item") or "")
                    for i in itens
                ],
            )
        conn.commit()
        return rid
    except Exception:
        conn.rollback()
        raise


def deletar_registro(rid: int):
    _exec("DELETE FROM registros WHERE id = %s", (rid,))


def atualizar_registro(rid: int, tecnico, tipo, local, qtd_kits, kits_usados, data_evento, observacoes, itens) -> int:
    conn = _pool()
    try:
        with conn.cursor() as cur:
            # 1. Atualiza o registro principal
            cur.execute(
                """UPDATE registros
                   SET tecnico = %s, tipo = %s, local = %s, qtd_kits = %s, kits_usados = %s,
                       data_evento = %s, observacoes = %s, atualizado_em = NOW()
                   WHERE id = %s""",
                (tecnico, tipo, local, int(qtd_kits), kits_usados, str(data_evento), observacoes or "", rid),
            )

            # 2. Apaga os itens antigos
            cur.execute("DELETE FROM itens WHERE registro_id = %s", (rid,))

            # 3. Insere os itens atualizados
            psycopg2.extras.execute_values(
                cur,
                """INSERT INTO itens
                   (registro_id, equipamento, consta, defeituoso, kit_defeito, obs_item)
                   VALUES %s""",
                [
                    (rid, i["equipamento"], bool(i["consta"]), bool(i["defeituoso"]),
                     i.get("kit_defeito") or "", i.get("obs_item") or "")
                    for i in itens
                ],
            )
        conn.commit()
        return rid
    except Exception:
        conn.rollback()
        raise

def atualizar_observacoes(rid: int, texto: str):
    _exec("UPDATE registros SET observacoes = %s WHERE id = %s", (texto, rid))


# ── Leitura ───────────────────────────────────────────────────────────────────
def buscar_registros(tecnico=None, tipo=None, local=None,
                     data_ini=None, data_fim=None) -> list[dict]:
    sql    = "SELECT * FROM registros WHERE TRUE"
    params = []
    if tecnico:
        sql += " AND LOWER(tecnico) LIKE %s"
        params.append(f"%{tecnico.lower()}%")
    if tipo and tipo != "Todos":
        sql += " AND tipo = %s"
        params.append(tipo)
    if local:
        sql += " AND LOWER(local) LIKE %s"
        params.append(f"%{local.lower()}%")
    if data_ini:
        sql += " AND data_evento >= %s"
        params.append(str(data_ini))
    if data_fim:
        sql += " AND data_evento <= %s"
        params.append(str(data_fim))
    sql += " ORDER BY data_evento DESC, id DESC"
    rows = _exec(sql, params, fetch="all") or []
    # Normaliza campos para string (compatibilidade com utils/app)
    for r in rows:
        r["data_evento"] = str(r["data_evento"])
        r["atualizado_em"] = str(r["atualizado_em"]) if r.get("atualizado_em") else None
        r["criado_em"]   = str(r["criado_em"])
    return rows


def buscar_um_registro(rid: int) -> dict | None:
    """Busca um único registro pelo seu ID."""
    row = _exec("SELECT * FROM registros WHERE id = %s", (rid,), fetch="one")
    if row:
        row["data_evento"] = datetime.strptime(str(row["data_evento"]), "%Y-%m-%d").date()
    return row


def buscar_itens(registro_id: int) -> list[dict]:
    rows = _exec(
        "SELECT * FROM itens WHERE registro_id = %s ORDER BY id",
        (registro_id,), fetch="all"
    ) or []
    # Converte bool do Postgres para int (compatibilidade com utils)
    for r in rows:
        r["consta"]     = int(r["consta"])
        r["defeituoso"] = int(r["defeituoso"])
    return rows


def buscar_defeituosos(data_ini=None, data_fim=None,
                       tecnico=None, equipamento=None) -> list[dict]:
    sql = """
        SELECT r.id           AS reg_id,
               r.data_evento,
               r.tipo,
               r.local,
               r.tecnico,
               r.qtd_kits,
               r.kits_usados,
               i.equipamento,
               i.kit_defeito,
               i.obs_item
        FROM itens i
        JOIN registros r ON r.id = i.registro_id
        WHERE i.defeituoso = TRUE
    """
    params = []
    if data_ini:
        sql += " AND r.data_evento >= %s"; params.append(str(data_ini))
    if data_fim:
        sql += " AND r.data_evento <= %s"; params.append(str(data_fim))
    if tecnico:
        sql += " AND LOWER(r.tecnico) LIKE %s"; params.append(f"%{tecnico.lower()}%")
    if equipamento and equipamento != "Todos":
        sql += " AND i.equipamento = %s"; params.append(equipamento)
    sql += " ORDER BY r.data_evento DESC, r.id DESC"
    rows = _exec(sql, params, fetch="all") or []
    for r in rows:
        r["data_evento"] = str(r["data_evento"])
    return rows


def listar_tecnicos() -> list[str]:
    rows = _exec(
        "SELECT DISTINCT tecnico FROM registros ORDER BY tecnico",
        fetch="all"
    ) or []
    return [r["tecnico"] for r in rows]


def listar_locais() -> list[str]:
    rows = _exec(
        "SELECT DISTINCT local FROM registros ORDER BY local",
        fetch="all"
    ) or []
    return [r["local"] for r in rows]


# ── Estatísticas ──────────────────────────────────────────────────────────────

def stats_gerais() -> dict:
    r = _exec("""
        SELECT
            COUNT(*)                                        AS total_registros,
            COUNT(*) FILTER (WHERE tipo='Montagem')         AS total_montagens,
            COUNT(*) FILTER (WHERE tipo='Desmontagem')      AS total_desmontagens,
            COALESCE(SUM(qtd_kits), 0)                      AS total_kits,
            COUNT(DISTINCT tecnico)                         AS total_tecnicos
        FROM registros
    """, fetch="one") or {}

    d = _exec(
        "SELECT COUNT(*) AS total_defeitos FROM itens WHERE defeituoso = TRUE",
        fetch="one"
    ) or {}

    return {
        "total_registros":    int(r.get("total_registros",   0)),
        "total_montagens":    int(r.get("total_montagens",    0)),
        "total_desmontagens": int(r.get("total_desmontagens", 0)),
        "total_kits":         int(r.get("total_kits",         0)),
        "total_tecnicos":     int(r.get("total_tecnicos",     0)),
        "total_defeitos":     int(d.get("total_defeitos",     0)),
    }


def serie_temporal() -> pd.DataFrame:
    rows = _exec("""
        SELECT data_evento::text AS "Data", tipo AS "Tipo", COUNT(*) AS "Qtd"
        FROM registros
        GROUP BY data_evento, tipo
        ORDER BY data_evento
    """, fetch="all") or []
    return pd.DataFrame(rows)


def defeitos_por_equipamento() -> pd.DataFrame:
    rows = _exec("""
        SELECT equipamento AS "Equipamento", COUNT(*) AS "Defeitos"
        FROM itens WHERE defeituoso = TRUE
        GROUP BY equipamento ORDER BY "Defeitos" DESC
    """, fetch="all") or []
    return pd.DataFrame(rows)


def operacoes_por_tecnico() -> pd.DataFrame:
    rows = _exec("""
        SELECT tecnico AS "Técnico", tipo AS "Tipo", COUNT(*) AS "Qtd"
        FROM registros GROUP BY tecnico, tipo ORDER BY tecnico
    """, fetch="all") or []
    return pd.DataFrame(rows)


def ultimos_registros(n: int = 10) -> pd.DataFrame:
    rows = _exec(f"""
        SELECT id AS "ID", data_evento::text AS "Data", tipo AS "Tipo",
               local AS "Local", tecnico AS "Técnico", qtd_kits AS "Kits", kits_usados AS "Kits Usados"
        FROM registros ORDER BY id DESC LIMIT {int(n)}
    """, fetch="all") or []
    return pd.DataFrame(rows)
