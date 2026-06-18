"""
app.py  ·  Kit Biométrico — Ações Sociais
Sistema de Gestão de Montagem e Desmontagem
"""

import streamlit as st
import pandas as pd
from datetime import date, datetime

from constants import (
    EQUIPAMENTOS, VERIFICACOES_ADICIONAIS,
    APP_TITLE, APP_ICON, APP_DESC, VERSION,
)
from database import (
    init_db, salvar_registro, deletar_registro,
    buscar_registros, buscar_registro_por_id, buscar_itens, buscar_defeituosos,
    listar_tecnicos, listar_locais,
    stats_gerais, serie_temporal, defeitos_por_equipamento,
    operacoes_por_tecnico, ultimos_registros,
)
from utils import (
    registros_para_dataframe, to_csv_bytes, to_excel_bytes,
    itens_para_df_exibicao, formatar_tipo, formatar_data
)
from styles import CSS

# ── Setup ────────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title=APP_TITLE,
    page_icon=APP_ICON,
    layout="wide",
    initial_sidebar_state="auto",
)
init_db()
st.markdown(CSS, unsafe_allow_html=True)

# ── Header ───────────────────────────────────────────────────────────────────
st.markdown(f"<h1>{APP_ICON} <span>{APP_TITLE}</span></h1>", unsafe_allow_html=True)
st.caption(f"{APP_DESC}  ·  v{VERSION}")

# ── Sidebar ──────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("## 📂 Menu")
    pagina = st.radio(
        "Navegação",
        [
            "Novo Registro",
            "Consultar Registros",
            "Equipamentos Defeituosos",
            "Dashboard",
        ],
        label_visibility="collapsed",
    )
    st.markdown("---")
    stats = stats_gerais()
    st.markdown(f"""
    **📈 Resumo Rápido**
    - Registros: **{stats['total_registros']}**
    - Montagens: **{stats['total_montagens']}**
    - Desmontagens: **{stats['total_desmontagens']}**
    - Defeitos: **{stats['total_defeitos']}**
    - Kits movimentados: **{stats['total_kits']}**
    """)
    st.markdown("---")
    st.caption(f"☁️ Banco de Dados: Supabase (PostgreSQL)\nVersão {VERSION}")


# ════════════════════════════════════════════════════════════════════════════
# PÁGINA 1 — NOVO REGISTRO
# ════════════════════════════════════════════════════════════════════════════
if pagina == "Novo Registro":

    st.subheader("📋 Registrar Montagem / Desmontagem")

    # ── Verificações adicionais ──────────────────────────────────────────────
    st.warning(
        "⚠️ Verificações Adicionais — Leia com atenção antes de preencher!\n\n"
        + "\n".join(f"- {v}" for v in VERIFICACOES_ADICIONAIS)
    )

    confirmou = st.checkbox(
        "Confirmo que li e realizei todas as verificações adicionais acima.",
        key="check_verificacoes",
    )
    if not confirmou:
        st.info("☝️ Marque a confirmação acima para liberar o formulário.")
        st.stop()

    st.markdown("---")

    # ── Dados gerais ─────────────────────────────────────────────────────────
    st.markdown("### 1. Dados Gerais")
    col1, col2, col3 = st.columns([3, 1, 1])
    with col1:
        tec_list = [""] + listar_tecnicos()
        tec_novo = st.text_input(
            "👤 Técnico Responsável *",
            placeholder="Digite o nome ou escolha abaixo",
        )
        if len(tec_list) > 1:
            tec_sel = st.selectbox(
                "Ou selecione um técnico já cadastrado:",
                tec_list,
                label_visibility="collapsed",
            )
            tecnico = tec_novo.strip() or tec_sel
        else:
            tecnico = tec_novo.strip()

    with col2:
        tipo = st.radio("🔧 Tipo *", ["Montagem", "Desmontagem"], horizontal=False)

    with col3:
        qtd_kits = st.number_input(
            "📦 Qtd. de Kits *", min_value=1, max_value=99, value=1, step=1
        )

    col4, col5 = st.columns([3, 1])
    with col4:
        loc_list = [""] + listar_locais()
        loc_novo = st.text_input(
            "📍 Local *",
            placeholder="Ex: CRAS Norte – Rua das Flores, 123",
        )
        if len(loc_list) > 1:
            loc_sel = st.selectbox(
                "Ou selecione um local já usado:",
                loc_list,
                label_visibility="collapsed",
            )
            local = loc_novo.strip() or loc_sel
        else:
            local = loc_novo.strip()

    with col5:
        data_evento = st.date_input("📅 Data *", value=date.today(), format="DD/MM/YYYY")

    st.markdown("---")

    # ── Checklist de equipamentos ─────────────────────────────────────────────
    st.markdown(f"### 2. Checklist de Equipamentos — {formatar_tipo(tipo)}")
    st.caption(
        "Para cada equipamento: marque **Consta** se ele está presente, "
        "**Defeituoso** se há alguma falha, e informe o Nº do kit e a descrição do defeito."
    )

    itens_form = []
    for eq in EQUIPAMENTOS:
        with st.container(border=True):
            c1, c2, c3, c4, c5 = st.columns([3, 1, 1, 1.5, 2.5])
            with c1:
                st.markdown(f"**{eq}**")
            with c2:
                consta = st.checkbox("Consta", key=f"consta_{eq}", value=True)
            with c3:
                defeituoso = st.checkbox("Defeito", key=f"def_{eq}")
            kit_def = obs_item = ""
            if defeituoso:
                with c4:
                    kit_def = st.text_input(
                        "Nº Kit", key=f"kitdef_{eq}", placeholder="Ex: 03"
                    )
                with c5:
                    obs_item = st.text_input(
                        "Descrição do defeito", key=f"obs_{eq}",
                        placeholder="Descreva brevemente..."
                    )

        itens_form.append({
            "equipamento": eq,
            "consta":      consta,
            "defeituoso":  defeituoso,
            "kit_defeito": kit_def,
            "obs_item":    obs_item,
        })

    st.markdown("---")

    # ── Observações gerais ────────────────────────────────────────────────────
    st.markdown("### 3. Observações Gerais")
    observacoes = st.text_area(
        "Registre qualquer informação adicional relevante:",
        placeholder="Ex: Cabo do scanner apresentou desgaste. Kit 02 com bateria fraca...",
        height=110,
        label_visibility="collapsed",
    )

    st.markdown("---")

    # ── Resumo antes de salvar ────────────────────────────────────────────────
    n_consta    = sum(1 for i in itens_form if i["consta"])
    n_faltando  = sum(1 for i in itens_form if not i["consta"])
    n_defeitos  = sum(1 for i in itens_form if i["defeituoso"])

    rc1, rc2, rc3 = st.columns(3)
    with rc1.container(border=True):
        st.metric("✅ Equipamentos presentes", n_consta)
    with rc2.container(border=True):
        st.metric("❌ Equipamentos ausentes",  n_faltando)
    with rc3.container(border=True):
        st.metric("⚠️ Com defeito",            n_defeitos)

    salvar_btn = st.button("💾 Salvar Registro", type="primary", use_container_width=False)

    if salvar_btn:
        erros = []
        if not tecnico:
            erros.append("⛔ Nome do técnico é obrigatório.")
        if not local:
            erros.append("⛔ Local é obrigatório.")
        if erros:
            for e in erros:
                st.error(e)
        else:
            with st.spinner("Salvando..."):
                rid = salvar_registro(
                    tecnico, tipo, local, qtd_kits,
                    data_evento, observacoes, itens_form,
                )
            st.success(f"✅ Registro **#{rid}** salvo com sucesso!")
            if n_faltando:
                equip_falt = [i["equipamento"] for i in itens_form if not i["consta"]]
                st.warning(
                    f"⚠️ **{n_faltando} equipamento(s) ausente(s):** "
                    + ", ".join(equip_falt)
                )
            if n_defeitos:
                equip_def = [i["equipamento"] for i in itens_form if i["defeituoso"]]
                st.error(
                    f"🔴 **{n_defeitos} equipamento(s) defeituoso(s):** "
                    + ", ".join(equip_def)
                )
            st.balloons()
            # Limpa estado dos checkboxes
            for k in list(st.session_state.keys()):
                if k.startswith(("consta_", "def_", "kitdef_", "obs_", "check_")):
                    del st.session_state[k]


# ════════════════════════════════════════════════════════════════════════════
# PÁGINA 2 — CONSULTAR REGISTROS
# ════════════════════════════════════════════════════════════════════════════
elif pagina == "Consultar Registros":

    st.subheader("🔍 Consultar Registros")

    with st.expander("🎛️ Filtros de Busca", expanded=True):
        fc1, fc2, fc3, fc4, fc5 = st.columns([2, 2, 1, 1, 1])
        with fc1:
            f_tec = st.text_input("👤 Técnico", placeholder="Parte do nome...")
        with fc2:
            f_loc = st.text_input("📍 Local", placeholder="Parte do local...")
        with fc3:
            f_tipo = st.selectbox("Tipo", ["Todos", "Montagem", "Desmontagem"])
        with fc4:
            f_ini = st.date_input("📅 De",  value=date(2020, 1, 1), key="ci", format="DD/MM/YYYY")
        with fc5:
            f_fim = st.date_input("📅 Até", value=date.today(),     key="cf", format="DD/MM/YYYY")

    registros = buscar_registros(
        tecnico=f_tec or None,
        tipo=f_tipo,
        local=f_loc or None,
        data_ini=f_ini,
        data_fim=f_fim,
    )

    col_tot, col_exp_all = st.columns([3, 1])
    col_tot.markdown(f"**{len(registros)} registro(s) encontrado(s)**")

    if registros:
        # Exportação em lote
        with col_exp_all:
            df_all = registros_para_dataframe(registros)
            exp_fmt = st.selectbox("Formato", ["CSV", "Excel"], key="fmt_all",
                                   label_visibility="collapsed")

        col_a, col_b = st.columns([1, 4])
        with col_a:
            if exp_fmt == "CSV":
                st.download_button(
                    "⬇️ Exportar todos",
                    data=to_csv_bytes(df_all),
                    file_name=f"relatorio_{date.today()}.csv",
                    mime="text/csv",
                )
            else:
                st.download_button(
                    "⬇️ Exportar todos",
                    data=to_excel_bytes(df_all),
                    file_name=f"relatorio_{date.today()}.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                )

        st.markdown("---")

        for reg in registros:
            itens = buscar_itens(reg["id"])
            n_def = sum(1 for i in itens if i["defeituoso"])
            n_aus = sum(1 for i in itens if not i["consta"])

            badge_def = f'<span class="badge-err">{n_def} defeito(s)</span>&nbsp;' if n_def else ""
            badge_aus = f'<span class="badge-warn">{n_aus} ausente(s)</span>' if n_aus else ""
            badges    = f"{badge_def}{badge_aus}".strip() if (badge_def or badge_aus) else '<span class="badge-ok">Tudo OK</span>'

            with st.expander(
                f"#{reg['id']} · {formatar_data(reg['data_evento'])} · "
                f"{reg['tipo'].upper()} · {reg['local']} · "
                f"Técnico: {reg['tecnico']} · Kits: {reg['qtd_kits']}"
            ):
                st.markdown(f"**Status:** {badges}", unsafe_allow_html=True)
                st.markdown("")

                m1, m2, m3, m4, m5 = st.columns(5)
                m1.metric("Técnico",  reg["tecnico"])
                m2.metric("Tipo",     reg["tipo"])
                m3.metric("Kits",     reg["qtd_kits"])
                m4.metric("Data",     formatar_data(reg["data_evento"]))
                m5.metric("Defeitos", n_def)

                st.markdown(f"**📍 Local:** {reg['local']}")

                st.markdown("**📋 Checklist:**")
                st.dataframe(
                    itens_para_df_exibicao(itens),
                    use_container_width=True,
                    hide_index=True,
                )

                if reg["observacoes"]:
                    st.info(f"📝 **Observações:** {reg['observacoes']}")

                st.caption(f"Registrado em: {formatar_data(reg['criado_em'])}")

                btn1, btn2, btn3, btn4 = st.columns([1, 1.5, 1.5, 4])
                with btn1:
                    with st.popover("🗑️ Excluir"):
                        st.warning("⚠️ **Atenção:** Esta ação é irreversível e apagará todos os itens vinculados a este registro.")
                        if st.button("✔️ Confirmar Exclusão", key=f"conf_del_{reg['id']}", type="primary", use_container_width=True):
                            deletar_registro(reg["id"])
                            st.success("Registro excluído.")
                            st.rerun()
                
                with btn2:
                    df_reg = registros_para_dataframe([reg])
                    st.download_button(
                        "⬇️ Exportar CSV",
                        data=to_csv_bytes(df_reg),
                        file_name=f"registro_{reg['id']}_{reg['data_evento']}.csv",
                        mime="text/csv",
                        key=f"csv_{reg['id']}",
                    )

                with btn3:
                    with st.popover("✏️ Editar", use_container_width=True):
                        st.markdown(f"#### Editando Registro #{reg['id']}")
                        reg_edit = buscar_registro_por_id(reg['id'])
                        if reg_edit:
                            with st.form(key=f"edit_form_{reg['id']}"):
                                edit_tecnico = st.text_input("Técnico", value=reg_edit['tecnico'])
                                edit_tipo = st.radio("Tipo", ["Montagem", "Desmontagem"], index=["Montagem", "Desmontagem"].index(reg_edit['tipo']))
                                edit_local = st.text_input("Local", value=reg_edit['local'])
                                edit_qtd_kits = st.number_input("Qtd. de Kits", min_value=1, value=reg_edit['qtd_kits'])
                                edit_data = st.date_input("Data", value=datetime.strptime(reg_edit['data_evento'], "%Y-%m-%d").date(), format="DD/MM/YYYY")
                                edit_obs = st.text_area("Observações", value=reg_edit['observacoes'])

                                if st.form_submit_button("💾 Salvar Alterações", type="primary", use_container_width=True):
                                    from database import atualizar_registro
                                    atualizar_registro(
                                        reg['id'], edit_tecnico, edit_tipo, edit_local,
                                        edit_qtd_kits, edit_data, edit_obs
                                    )
                                    st.success(f"Registro #{reg['id']} atualizado!")
                                    st.rerun()
                        else:
                            st.error("Registro não encontrado para edição.")
    else:
        st.info("Nenhum registro encontrado com os filtros aplicados.")


# ════════════════════════════════════════════════════════════════════════════
# PÁGINA 3 — EQUIPAMENTOS DEFEITUOSOS
# ════════════════════════════════════════════════════════════════════════════
elif pagina == "Equipamentos Defeituosos":

    st.subheader("⚠️ Relatório de Equipamentos Defeituosos")

    with st.expander("🎛️ Filtros", expanded=True):
        d1, d2, d3, d4 = st.columns([2, 1, 1, 2])
        with d1:
            d_tec = st.text_input("👤 Técnico", key="dtec")
        with d2:
            d_ini = st.date_input("📅 De",  value=date(2020, 1, 1), key="dini", format="DD/MM/YYYY")
        with d3:
            d_fim = st.date_input("📅 Até", value=date.today(),     key="dfim", format="DD/MM/YYYY")
        with d4:
            d_eq = st.selectbox("🔧 Equipamento", ["Todos"] + EQUIPAMENTOS, key="deq")

    defeituosos = buscar_defeituosos(
        data_ini=d_ini, data_fim=d_fim,
        tecnico=d_tec or None,
        equipamento=d_eq,
    )

    st.markdown(f"**{len(defeituosos)} ocorrência(s) de defeito encontrada(s)**")

    if not defeituosos:
        st.success("✅ Nenhum equipamento defeituoso encontrado para os filtros aplicados!")
    else:
        df_def = pd.DataFrame(defeituosos).rename(columns={
            "reg_id":       "Reg. ID",
            "data_evento":  "Data",
            "tipo":         "Tipo",
            "local":        "Local",
            "tecnico":      "Técnico",
            "qtd_kits":     "Kits",
            "equipamento":  "Equipamento",
            "kit_defeito":  "Nº Kit",
            "obs_item":     "Descrição do Defeito",
        })

        df_def["Data"] = pd.to_datetime(df_def["Data"]).dt.strftime("%d/%m/%Y")
        st.dataframe(df_def, use_container_width=True, hide_index=True)

        # Gráfico
        st.markdown("---")
        st.markdown("### 📊 Equipamentos com Mais Ocorrências de Defeito")
        freq = df_def["Equipamento"].value_counts().reset_index()
        freq.columns = ["Equipamento", "Ocorrências"]
        st.bar_chart(freq.set_index("Equipamento"))

        # Exportação
        st.markdown("---")
        ec1, ec2 = st.columns([1, 4])
        with ec1:
            st.download_button(
                "⬇️ Exportar CSV",
                data=to_csv_bytes(df_def),
                file_name=f"defeituosos_{date.today()}.csv",
                mime="text/csv",
            )
        with ec2:
            st.download_button(
                "⬇️ Exportar Excel",
                data=to_excel_bytes(df_def),
                file_name=f"defeituosos_{date.today()}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            )


# ════════════════════════════════════════════════════════════════════════════
# PÁGINA 4 — DASHBOARD
# ════════════════════════════════════════════════════════════════════════════
elif pagina == "Dashboard":

    st.subheader("📊 Dashboard Geral")

    stats = stats_gerais()

    # ── Cards ────────────────────────────────────────────────────────────────
    met1, met2, met3 = st.columns(3)
    with met1.container(border=True):
        st.metric("📋 Total de Registros", stats["total_registros"])
    with met2.container(border=True):
        st.metric("🔧 Montagens", stats["total_montagens"])
    with met3.container(border=True):
        st.metric("📦 Desmontagens", stats["total_desmontagens"])
    
    met4, met5, met6 = st.columns(3)
    with met4.container(border=True):
        st.metric("⚠️ Itens com Defeito", stats["total_defeitos"])
    with met5.container(border=True):
        st.metric("🗃️ Kits Movimentados", stats["total_kits"])
    with met6.container(border=True):
        st.metric("👤 Técnicos", stats["total_tecnicos"])

    st.markdown("---")

    # ── Gráficos ──────────────────────────────────────────────────────────────
    gc1, gc2 = st.columns(2)

    with gc1:
        with st.container(border=True):
            st.markdown("### 📅 Registros por Data")
            df_tempo = serie_temporal()
            if not df_tempo.empty:
                df_tempo["Data"] = pd.to_datetime(df_tempo["Data"])
                pivot = df_tempo.pivot(
                    index="Data", columns="Tipo", values="Qtd"
                ).fillna(0)
                st.bar_chart(pivot)
            else:
                st.info("Sem dados ainda.")

    with gc2:
        with st.container(border=True):
            st.markdown("### 👤 Registros por Técnico")
            df_tec = operacoes_por_tecnico()
            if not df_tec.empty:
                pivot_tec = df_tec.pivot(
                    index="Técnico", columns="Tipo", values="Qtd"
                ).fillna(0)
                st.bar_chart(pivot_tec)
            else:
                st.info("Sem dados ainda.")

    with st.container(border=True):
        st.markdown("### ⚠️ Equipamentos com Mais Defeitos")
        df_def_eq = defeitos_por_equipamento()
        if not df_def_eq.empty:
            st.bar_chart(df_def_eq.set_index("Equipamento"))
        else:
            st.success("✅ Nenhum defeito registrado até o momento!")

    # ── Tabela recente ────────────────────────────────────────────────────────
    st.markdown("---")
    with st.container(border=True):
        st.markdown("### 🕐 Últimos 10 Registros")
        df_ult = ultimos_registros(10)
        if df_ult.empty:
            st.info("Nenhum registro encontrado ainda.")
        else:
            df_ult["Data"] = pd.to_datetime(df_ult["Data"]).dt.strftime("%d/%m/%Y")
            st.dataframe(df_ult, use_container_width=True, hide_index=True)

    # ── Botão exportação completa ─────────────────────────────────────────────
    st.markdown("---")
    if stats["total_registros"] > 0:
        st.markdown("### 📤 Exportar Base Completa")
        todos = buscar_registros()
        df_completo = registros_para_dataframe(todos)
        ex1, ex2 = st.columns([1, 1])
        with ex1:
            st.download_button(
                "⬇️ Baixar tudo em CSV",
                data=to_csv_bytes(df_completo),
                file_name=f"base_completa_{date.today()}.csv",
                mime="text/csv",
            )
        with ex2:
            st.download_button(
                "⬇️ Baixar tudo em Excel",
                data=to_excel_bytes(df_completo),
                file_name=f"base_completa_{date.today()}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            )
