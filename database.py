"""
database.py  —  Kit Biométrico
Backend PostgreSQL via psycopg2 (Supabase ou qualquer Postgres).
A connection string vem de st.secrets["DATABASE_URL"]
ou da variável de ambiente DATABASE_URL (para rodar localmente).

Melhorias v1.1:
  - Todos os timestamps armazenados em UTC (NOW() AT TIME ZONE 'UTC')
  - Tabela audit_log com diff detalhado campo a campo
  - Helper _to_brasilia() para exibição no fuso BRT (UTC-3)
"""

import os
import psycopg2
import psycopg2.extras
import pandas as pd
import streamlit as st
from datetime import datetime, timezone, timedelta


# ── Fuso horário ──────────────────────────────────────────────────────────────

_BRT = timezone(timedelta(hours=-3))


def utc_now() -> datetime:
    """Retorna o instante atual em UTC (timezone-aware)."""
    return datetime.now(timezone.utc)


def to_brasilia(dt) -> datetime | None:
    """Converte um datetime (ou string ISO) para BRT (UTC-3)."""
    if dt is None:
        return None
    if isinstance(dt, str):
        dt = dt.strip()
        if not dt or dt == "None":
            return None
        # Tenta parsear com ou sem timezone
        for fmt in ("%Y-%m-%d %H:%M:%S.%f%z", "%Y-%m-%d %H:%M:%S%z",
                    "%Y-%m-%d %H:%M:%S.%f", "%Y-%m-%d %H:%M:%S",
                    "%Y-%m-%dT%H:%M:%S.%f%z", "%Y-%m-%dT%H:%M:%S%z"):
            try:
                dt = datetime.strptime(dt, fmt)
                break
            except ValueError:
                continue
        else:
            return None
    if isinstance(dt, datetime):
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(_BRT)
    return None


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
            id            SERIAL PRIMARY KEY,
            tecnico       TEXT    NOT NULL,
            tipo          TEXT    NOT NULL CHECK (tipo IN ('Montagem','Desmontagem')),
            local         TEXT    NOT NULL,
            qtd_kits      INTEGER NOT NULL CHECK (qtd_kits >= 1),
            kits_usados   TEXT    NOT NULL DEFAULT '',
            data_evento   DATE    NOT NULL,
            observacoes   TEXT    NOT NULL DEFAULT '',
            atualizado_em TIMESTAMPTZ,
            criado_em     TIMESTAMPTZ NOT NULL DEFAULT (NOW() AT TIME ZONE 'UTC')
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
    # Tabela de auditoria detalhada (v1.1)
    _exec("""
        CREATE TABLE IF NOT EXISTS audit_log (
            id            SERIAL PRIMARY KEY,
            registro_id   INTEGER NOT NULL REFERENCES registros(id) ON DELETE CASCADE,
            alterado_em   TIMESTAMPTZ NOT NULL DEFAULT (NOW() AT TIME ZONE 'UTC'),
            alterado_por  TEXT    NOT NULL DEFAULT '',
            justificativa TEXT    NOT NULL DEFAULT '',
            diff_json     TEXT    NOT NULL DEFAULT '{}'
        )
    """)
    # Migrações seguras para bancos mais antigos
    _exec("ALTER TABLE registros ADD COLUMN IF NOT EXISTS kits_usados TEXT NOT NULL DEFAULT '';")
    _exec("ALTER TABLE registros ADD COLUMN IF NOT EXISTS atualizado_em TIMESTAMPTZ;")
    _exec("ALTER TABLE itens ADD COLUMN IF NOT EXISTS num_chamado TEXT NOT NULL DEFAULT '';")
    # Índices
    _exec("CREATE INDEX IF NOT EXISTS idx_reg_data      ON registros(data_evento)")
    _exec("CREATE INDEX IF NOT EXISTS idx_reg_tec       ON registros(tecnico)")
    _exec("CREATE INDEX IF NOT EXISTS idx_itens_def     ON itens(defeituoso)")
    _exec("CREATE INDEX IF NOT EXISTS idx_itens_regid   ON itens(registro_id)")
    _exec("CREATE INDEX IF NOT EXISTS idx_audit_regid   ON audit_log(registro_id)")


# ── Escrita ───────────────────────────────────────────────────────────────────

def salvar_registro(tecnico, tipo, local, qtd_kits, kits_usados,
                    data_evento, observacoes, itens) -> int:
    conn = _pool()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """INSERT INTO registros
                   (tecnico, tipo, local, qtd_kits, kits_usados, data_evento,
                    observacoes, criado_em)
                   VALUES (%s,%s,%s,%s,%s,%s,%s, NOW() AT TIME ZONE 'UTC')
                   RETURNING id""",
                (tecnico, tipo, local, int(qtd_kits), kits_usados,
                 str(data_evento), observacoes or ""),
            )
            rid = cur.fetchone()["id"]
            psycopg2.extras.execute_values(
                cur,
                """INSERT INTO itens
                   (registro_id, equipamento, consta, defeituoso,
                    kit_defeito, obs_item, num_chamado)
                   VALUES %s""",
                [
                    (rid, i["equipamento"], bool(i["consta"]), bool(i["defeituoso"]),
                     i.get("kit_defeito") or "", i.get("obs_item") or "",
                     i.get("num_chamado") or "")
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


def _build_diff(reg_antigo: dict, itens_antigos: list[dict],
                reg_novo: dict, itens_novos: list[dict]) -> dict:
    """
    Compara dois estados de um registro e retorna um dicionário com as
    diferenças campo a campo, no formato:
        { "campo": {"antes": valor_antigo, "depois": valor_novo}, ... }
    """
    import json

    diff: dict = {}

    # Campos escalares do registro principal
    campos_principais = ["tecnico", "tipo", "local", "qtd_kits",
                         "kits_usados", "data_evento", "observacoes"]
    for campo in campos_principais:
        antes = str(reg_antigo.get(campo, ""))
        depois = str(reg_novo.get(campo, ""))
        if antes != depois:
            diff[campo] = {"antes": antes, "depois": depois}

    # Checklist de itens — compara por equipamento
    mapa_antigo = {i["equipamento"]: i for i in itens_antigos}
    mapa_novo   = {i["equipamento"]: i for i in itens_novos}

    itens_diff: dict = {}
    for eq in set(list(mapa_antigo.keys()) + list(mapa_novo.keys())):
        ant = mapa_antigo.get(eq, {})
        nov = mapa_novo.get(eq, {})
        campos_item = ["consta", "defeituoso", "kit_defeito", "obs_item", "num_chamado"]
        item_ch: dict = {}
        for c in campos_item:
            if c in ("consta", "defeituoso"):
                # buscar_itens retorna int (0/1); form retorna bool → normaliza os dois
                va = "True" if ant.get(c) else "False"
                vn = "True" if nov.get(c) else "False"
            else:
                va = str(ant.get(c) or "")
                vn = str(nov.get(c) or "")
            if va != vn:
                item_ch[c] = {"antes": va, "depois": vn}
        if item_ch:
            itens_diff[eq] = item_ch

    if itens_diff:
        diff["itens"] = itens_diff

    return diff


def atualizar_registro(rid: int, tecnico, tipo, local, qtd_kits, kits_usados,
                       data_evento, observacoes, itens,
                       justificativa: str = "", alterado_por: str = "") -> int:
    import json

    # Captura estado anterior para o diff
    reg_antigo    = buscar_um_registro(rid) or {}
    itens_antigos = buscar_itens(rid)

    # Normaliza data para string comparável
    if hasattr(reg_antigo.get("data_evento"), "strftime"):
        reg_antigo["data_evento"] = reg_antigo["data_evento"].strftime("%Y-%m-%d")

    reg_novo_dict = {
        "tecnico":     tecnico,
        "tipo":        tipo,
        "local":       local,
        "qtd_kits":    qtd_kits,
        "kits_usados": kits_usados,
        "data_evento": str(data_evento),
        "observacoes": observacoes or "",
    }

    diff = _build_diff(reg_antigo, itens_antigos, reg_novo_dict, itens)

    conn = _pool()
    try:
        with conn.cursor() as cur:
            # 1. Atualiza o registro principal (timestamp em UTC)
            cur.execute(
                """UPDATE registros
                   SET tecnico=%s, tipo=%s, local=%s, qtd_kits=%s, kits_usados=%s,
                       data_evento=%s, observacoes=%s,
                       atualizado_em=(NOW() AT TIME ZONE 'UTC')
                   WHERE id=%s""",
                (tecnico, tipo, local, int(qtd_kits), kits_usados,
                 str(data_evento), observacoes or "", rid),
            )
            # 2. Apaga itens antigos e insere os novos
            cur.execute("DELETE FROM itens WHERE registro_id = %s", (rid,))
            psycopg2.extras.execute_values(
                cur,
                """INSERT INTO itens
                   (registro_id, equipamento, consta, defeituoso,
                    kit_defeito, obs_item, num_chamado)
                   VALUES %s""",
                [
                    (rid, i["equipamento"], bool(i["consta"]), bool(i["defeituoso"]),
                     i.get("kit_defeito") or "", i.get("obs_item") or "",
                     i.get("num_chamado") or "")
                    for i in itens
                ],
            )
            # 3. Grava entrada de auditoria com o diff
            cur.execute(
                """INSERT INTO audit_log
                   (registro_id, alterado_em, alterado_por, justificativa, diff_json)
                   VALUES (%s, NOW() AT TIME ZONE 'UTC', %s, %s, %s)""",
                (rid, alterado_por or "", justificativa or "",
                 json.dumps(diff, ensure_ascii=False)),
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
    for r in rows:
        r["data_evento"]  = str(r["data_evento"])
        r["atualizado_em"] = str(r["atualizado_em"]) if r.get("atualizado_em") else None
        r["criado_em"]    = str(r["criado_em"])
    return rows


def buscar_um_registro(rid: int) -> dict | None:
    """Busca um único registro pelo seu ID."""
    row = _exec("SELECT * FROM registros WHERE id = %s", (rid,), fetch="one")
    if row:
        from datetime import date as _date
        val = row["data_evento"]
        if isinstance(val, str):
            row["data_evento"] = datetime.strptime(val[:10], "%Y-%m-%d").date()
        elif not isinstance(val, _date):
            row["data_evento"] = val
    return row


def buscar_itens(registro_id: int) -> list[dict]:
    rows = _exec(
        "SELECT * FROM itens WHERE registro_id = %s ORDER BY id",
        (registro_id,), fetch="all"
    ) or []
    for r in rows:
        r["consta"]     = int(r["consta"])
        r["defeituoso"] = int(r["defeituoso"])
    return rows


def buscar_audit_log(registro_id: int) -> list[dict]:
    """Retorna o histórico de auditoria de um registro, do mais recente ao mais antigo."""
    import json
    rows = _exec(
        """SELECT id, alterado_em, alterado_por, justificativa, diff_json
           FROM audit_log
           WHERE registro_id = %s
           ORDER BY alterado_em DESC""",
        (registro_id,), fetch="all"
    ) or []
    for r in rows:
        r["alterado_em_brt"] = to_brasilia(r.get("alterado_em"))
        try:
            r["diff"] = json.loads(r["diff_json"]) if r.get("diff_json") else {}
        except Exception:
            r["diff"] = {}
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
               i.obs_item,
               i.num_chamado
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


def buscar_chamados(data_ini=None, data_fim=None,
                    tecnico=None, equipamento=None, num_chamado=None) -> list[dict]:
    """Retorna itens defeituosos que possuem Nº Chamado preenchido."""
    sql = """
        SELECT r.id           AS reg_id,
               r.data_evento,
               r.tipo,
               r.local,
               r.tecnico,
               r.kits_usados,
               i.equipamento,
               i.kit_defeito,
               i.obs_item,
               i.num_chamado
        FROM itens i
        JOIN registros r ON r.id = i.registro_id
        WHERE i.defeituoso = TRUE
          AND i.num_chamado != ''
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
    if num_chamado:
        sql += " AND LOWER(i.num_chamado) LIKE %s"; params.append(f"%{num_chamado.lower()}%")
    sql += " ORDER BY r.data_evento DESC, r.id DESC"
    rows = _exec(sql, params, fetch="all") or []
    for r in rows:
        r["data_evento"] = str(r["data_evento"])
    return rows


def listar_tecnicos() -> list[str]:
    rows = _exec(
        "SELECT DISTINCT tecnico FROM registros ORDER BY tecnico", fetch="all"
    ) or []
    return [r["tecnico"] for r in rows]


def listar_locais() -> list[str]:
    rows = _exec(
        "SELECT DISTINCT local FROM registros ORDER BY local", fetch="all"
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
               local AS "Local", tecnico AS "Técnico",
               qtd_kits AS "Kits", kits_usados AS "Kits Usados"
        FROM registros ORDER BY id DESC LIMIT {int(n)}
    """, fetch="all") or []
    return pd.DataFrame(rows)
