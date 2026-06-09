"""
init_db.py
Inicializa o schema PostgreSQL (cria tabelas se não existirem).
Execute uma vez antes do primeiro deploy, ou deixe app.py chamar init_db().

Uso:
    DATABASE_URL="postgresql://..." python init_db.py
"""
import os, sys
sys.path.insert(0, os.path.dirname(__file__))

# Simula st.secrets via variável de ambiente para rodar fora do Streamlit
dsn = os.getenv("DATABASE_URL", "")
if not dsn:
    print("❌  Defina a variável de ambiente DATABASE_URL antes de executar.")
    print("    Exemplo: DATABASE_URL='postgresql://...' python init_db.py")
    sys.exit(1)

# Injeta um st.secrets falso para database.py funcionar sem o Streamlit
import types, unittest.mock as mock
st_mock = types.ModuleType("streamlit")
st_mock.secrets = {"DATABASE_URL": dsn}
st_mock.cache_resource = lambda **kw: (lambda f: f)  # decorator no-op
sys.modules.setdefault("streamlit", st_mock)

from database import init_db
init_db()
print("✅  Schema PostgreSQL inicializado com sucesso.")
