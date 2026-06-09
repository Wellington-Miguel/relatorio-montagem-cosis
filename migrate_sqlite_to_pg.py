"""
migrate_sqlite_to_pg.py
Migra dados de um banco SQLite existente para o PostgreSQL/Supabase.
Execute UMA vez após o deploy inicial se você já tiver dados no SQLite.

Uso:
    DATABASE_URL="postgresql://..." python migrate_sqlite_to_pg.py [caminho_do.db]

O caminho padrão do SQLite é  data/biometrico.db
"""
import os, sys, sqlite3, psycopg2, psycopg2.extras

SQLITE_PATH = sys.argv[1] if len(sys.argv) > 1 else "data/biometrico.db"
PG_DSN      = os.getenv("DATABASE_URL", "")

if not PG_DSN:
    print("❌  Defina DATABASE_URL antes de executar.")
    sys.exit(1)

if not os.path.exists(SQLITE_PATH):
    print(f"❌  Arquivo SQLite não encontrado: {SQLITE_PATH}")
    sys.exit(1)

print(f"📂  Lendo SQLite em: {SQLITE_PATH}")
src = sqlite3.connect(SQLITE_PATH)
src.row_factory = sqlite3.Row

registros = [dict(r) for r in src.execute("SELECT * FROM registros ORDER BY id").fetchall()]
itens     = [dict(r) for r in src.execute("SELECT * FROM itens     ORDER BY id").fetchall()]
src.close()

print(f"   → {len(registros)} registro(s), {len(itens)} item(ns)")

print("🔌  Conectando ao PostgreSQL...")
dst = psycopg2.connect(PG_DSN, cursor_factory=psycopg2.extras.RealDictCursor)

with dst:
    with dst.cursor() as cur:
        id_map = {}  # SQLite id → PostgreSQL id
        for r in registros:
            cur.execute(
                """INSERT INTO registros (tecnico, tipo, local, qtd_kits, data_evento, observacoes, criado_em)
                   VALUES (%s,%s,%s,%s,%s,%s,%s) RETURNING id""",
                (r["tecnico"], r["tipo"], r["local"], r["qtd_kits"],
                 r["data_evento"], r.get("observacoes",""), r["criado_em"]),
            )
            id_map[r["id"]] = cur.fetchone()["id"]

        rows_itens = [
            (id_map[i["registro_id"]], i["equipamento"],
             bool(i["consta"]), bool(i["defeituoso"]),
             i.get("kit_defeito","") or "", i.get("obs_item","") or "")
            for i in itens if i["registro_id"] in id_map
        ]
        if rows_itens:
            psycopg2.extras.execute_values(
                cur,
                """INSERT INTO itens (registro_id, equipamento, consta, defeituoso, kit_defeito, obs_item)
                   VALUES %s""",
                rows_itens,
            )

dst.close()
print(f"✅  Migração concluída — {len(registros)} registro(s) e {len(rows_itens)} item(ns) importados.")
