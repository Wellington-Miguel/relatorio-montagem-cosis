# 🖥️ Kit Biométrico — Ações Sociais

Sistema de gestão de **montagem e desmontagem** de kits biométricos.
Stack: **Python · Streamlit · PostgreSQL (Supabase)**

---

## 📁 Estrutura do projeto

```
kit-biometrico/
├── app.py                      ← Entrypoint Streamlit (4 páginas)
├── database.py                 ← Todas as operações PostgreSQL
├── constants.py                ← Lista de equipamentos e constantes
├── styles.py                   ← CSS do app
├── utils.py                    ← Exportação CSV/Excel e helpers
├── init_db.py                  ← Cria as tabelas no banco (rode 1x)
├── migrate_sqlite_to_pg.py     ← Migração de dados SQLite → Postgres
├── requirements.txt            ← Dependências Python
├── .gitignore                  ← Exclui secrets e arquivos locais
└── .streamlit/
    ├── config.toml             ← Tema e configurações
    └── secrets.toml            ← ⚠️ NÃO versionar — sua DATABASE_URL vai aqui
```

---

## 🚀 Passo a passo completo: do zero ao deploy

### 1. Criar o banco no Supabase (gratuito)

1. Acesse **[supabase.com](https://supabase.com)** → **Start your project**
2. Crie uma conta (GitHub, Google ou e-mail)
3. Clique em **New project**
   - Escolha um nome (ex: `kit-biometrico`)
   - Defina uma **senha forte** para o banco — **anote essa senha**
   - Selecione a região mais próxima (ex: *South America (São Paulo)*)
   - Clique **Create new project** e aguarde ~2 min
4. No painel do projeto, vá em **Settings → Database**
5. Role até **Connection string → URI**
6. Copie a string. Ela tem o formato:
   ```
   postgresql://postgres:[YOUR-PASSWORD]@db.xxxxxxxxxxxx.supabase.co:5432/postgres
   ```
7. **Substitua `[YOUR-PASSWORD]`** pela senha que você definiu no passo 3

---

### 2. Configurar o arquivo de segredos (local)

Edite o arquivo `.streamlit/secrets.toml`:

```toml
DATABASE_URL = "postgresql://postgres:SUA_SENHA@db.xxxxxxxxxxxx.supabase.co:5432/postgres"
```

> ⚠️ Este arquivo está no `.gitignore` e **nunca deve ser commitado**.

---

### 3. Criar as tabelas no banco

Com o `secrets.toml` preenchido, execute **uma única vez**:

```bash
pip install -r requirements.txt
streamlit run app.py
```

O próprio app chama `init_db()` na inicialização e cria as tabelas automaticamente.

Ou, se preferir rodar manualmente via terminal:

```bash
DATABASE_URL="postgresql://postgres:SENHA@db.xxxx.supabase.co:5432/postgres" python init_db.py
```

---

### 4. Subir para o GitHub

```bash
git init
git add .
git commit -m "feat: sistema kit biométrico v1.0"
git remote add origin https://github.com/SEU-USUARIO/kit-biometrico.git
git push -u origin main
```

> O `.gitignore` já garante que `secrets.toml` e arquivos SQLite **não sejam enviados**.

---

### 5. Deploy no Streamlit Cloud

1. Acesse **[share.streamlit.io](https://share.streamlit.io)**
2. Clique em **New app**
3. Selecione o repositório, branch `main`, arquivo `app.py`
4. Clique em **Advanced settings** antes de fazer o deploy
5. Na aba **Secrets**, cole exatamente:
   ```toml
   DATABASE_URL = "postgresql://postgres:SUA_SENHA@db.xxxx.supabase.co:5432/postgres"
   ```
6. Clique **Save** e depois **Deploy** ✅

---

## 💾 Por que os dados não são perdidos?

Os dados ficam no **Supabase (PostgreSQL na nuvem)**, completamente separado do Streamlit Cloud.
Mesmo que:
- O app hiberne por inatividade
- Você faça um novo deploy
- O servidor do Streamlit reinicie

…os dados continuam intactos no Supabase, que tem backup automático no plano gratuito.

---

## 🛠️ Equipamentos do kit

Scanner + Fonte + USB · Notebook · Ring Light · Suporte Ring Light ·
Câmera · USB da Câmera · Mouse · Pad de Assinatura ·
Leitor Biométrico · Banner · Hub · Filtro de Linha

---

## 📄 Licença

Uso interno — Ações Sociais.
