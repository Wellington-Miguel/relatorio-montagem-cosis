"""
app.py  ·  Kit Biométrico — Ações Sociais
Sistema de Gestão de Montagem e Desmontagem

Melhorias v1.1:
  - Formulário de edição estável via st.session_state (sem recargas inesperadas)
  - Audit log detalhado com diff campo a campo
  - Timestamps em UTC + exibição em BRT (UTC-3)
  - Interface de consulta compacta com checklist recolhível
"""

import json
import streamlit as st
import pandas as pd
from datetime import date, datetime

from constants import (
    EQUIPAMENTOS, VERIFICACOES_ADICIONAIS, TECNICOS,
    APP_TITLE, APP_ICON, APP_DESC, VERSION,
)
from database import (
    init_db, salvar_registro, deletar_registro, atualizar_registro,
    buscar_um_registro, buscar_registros, buscar_itens, buscar_defeituosos,
    buscar_audit_log, listar_locais,
    stats_gerais, serie_temporal, defeitos_por_equipamento,
    operacoes_por_tecnico, ultimos_registros,
    to_brasilia,
)
from utils import (
    registros_para_dataframe, to_csv_bytes, to_excel_bytes,
    itens_para_df_exibicao, formatar_tipo, formatar_data,
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


# ── Helpers de exibição de timestamp ─────────────────────────────────────────

def formatar_ts(ts_str) -> str:
    """
    Converte timestamp (UTC, vindo do banco) → string legível em BRT (UTC-3).
    Retorna '' se nulo.
    """
    if not ts_str:
        return ""
    dt = to_brasilia(ts_str)
    if dt is None:
        return str(ts_str)[:16]
    return dt.strftime("%d/%m/%Y %H:%M") + " (BRT)"


# ── Sidebar ──────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("## 📂 Menu")
    paginas_visiveis = [
        "Novo Registro",
        "Consultar Registros",
        "Equipamentos Defeituosos",
        "Dashboard",
    ]
    # A página de edição é acessada via query param
    if "page" in st.query_params and st.query_params["page"] == "Editar":
        st.info("✏️ Modo de Edição Ativo")
        if st.button("⬅️ Voltar"):
            st.query_params.clear()
            if "edit_state" in st.session_state:
                del st.session_state["edit_state"]
            st.rerun()
        pagina = "Editar Registro"
    else:
        pagina = st.radio("Navegação", paginas_visiveis, label_visibility="collapsed")
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
    st.caption(f"☁️ Banco: Supabase (PostgreSQL) · Versão {VERSION} /n · by Wellington Miguel")


# ════════════════════════════════════════════════════════════════════════════
# PÁGINA 1 — NOVO REGISTRO
# ════════════════════════════════════════════════════════════════════════════
if pagina == "Novo Registro" and "page" not in st.query_params:

    st.subheader("📋 Registrar Montagem / Desmontagem")

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

    st.markdown("### 1. Dados Gerais")
    col1, col2, col3, col4 = st.columns([2, 1, 1, 2])
    with col1:
        tecnico = st.selectbox("👤 Técnico Responsável *", TECNICOS)
    with col2:
        tipo = st.radio("🔧 Tipo *", ["Montagem", "Desmontagem"], horizontal=False)
    with col3:
        qtd_kits = st.number_input("📦 Qtd. de Kits *", min_value=1, max_value=99, value=1, step=1)
    with col4:
        kits_usados = st.text_input("🧰 Kits Usados *", placeholder="Ex: Kit 01, Kit 03")

    col_loc, col_dt = st.columns([3, 1])
    with col_loc:
        loc_list = [""] + listar_locais()
        loc_novo = st.text_input("📍 Local *", placeholder="Ex: CRAS Norte – Rua das Flores, 123")
        if len(loc_list) > 1:
            loc_sel = st.selectbox("Ou selecione um local já usado:", loc_list,
                                   label_visibility="collapsed")
            local = loc_novo.strip() or loc_sel
        else:
            local = loc_novo.strip()
    with col_dt:
        data_evento = st.date_input("📅 Data *", value=date.today(), format="DD/MM/YYYY")

    st.markdown("---")
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
                    kit_def = st.text_input("Nº Kit", key=f"kitdef_{eq}", placeholder="Ex: 03")
                with c5:
                    obs_item = st.text_input("Descrição do defeito", key=f"obs_{eq}",
                                             placeholder="Descreva brevemente...")
        itens_form.append({
            "equipamento": eq,
            "consta":      consta,
            "defeituoso":  defeituoso,
            "kit_defeito": kit_def,
            "obs_item":    obs_item,
        })

    st.markdown("---")
    st.markdown("### 3. Observações Gerais")
    observacoes = st.text_area(
        "Registre qualquer informação adicional relevante:",
        placeholder="Ex: Cabo do scanner apresentou desgaste. Kit 02 com bateria fraca...",
        height=110, label_visibility="collapsed",
    )
    st.markdown("---")

    n_consta   = sum(1 for i in itens_form if i["consta"])
    n_faltando = sum(1 for i in itens_form if not i["consta"])
    n_defeitos = sum(1 for i in itens_form if i["defeituoso"])

    rc1, rc2, rc3 = st.columns(3)
    with rc1.container(border=True):
        st.metric("✅ Equipamentos presentes", n_consta)
    with rc2.container(border=True):
        st.metric("❌ Equipamentos ausentes", n_faltando)
    with rc3.container(border=True):
        st.metric("⚠️ Com defeito", n_defeitos)

    if st.button("💾 Salvar Registro", type="primary"):
        erros = []
        if not tecnico:
            erros.append("⛔ Nome do técnico é obrigatório.")
        if not kits_usados.strip():
            erros.append("⛔ O preenchimento dos kits usados é obrigatório.")
        if not local:
            erros.append("⛔ Local é obrigatório.")
        if erros:
            for e in erros:
                st.error(e)
        else:
            with st.spinner("Salvando..."):
                rid = salvar_registro(
                    tecnico, tipo, local, qtd_kits, kits_usados.strip(),
                    data_evento, observacoes, itens_form,
                )
            st.success(f"✅ Registro **#{rid}** salvo com sucesso!")
            if n_faltando:
                equip_falt = [i["equipamento"] for i in itens_form if not i["consta"]]
                st.warning(f"⚠️ **{n_faltando} equipamento(s) ausente(s):** " + ", ".join(equip_falt))
            if n_defeitos:
                equip_def = [i["equipamento"] for i in itens_form if i["defeituoso"]]
                st.error(f"🔴 **{n_defeitos} equipamento(s) defeituoso(s):** " + ", ".join(equip_def))
            st.balloons()
            for k in list(st.session_state.keys()):
                if k.startswith(("consta_", "def_", "kitdef_", "obs_", "check_")):
                    del st.session_state[k]


# ════════════════════════════════════════════════════════════════════════════
# PÁGINA 2 — CONSULTAR REGISTROS  (interface compacta)
# ════════════════════════════════════════════════════════════════════════════
elif pagina == "Consultar Registros":

    st.subheader("🔍 Consultar Registros")

    with st.expander("🎛️ Filtros de Busca", expanded=True):
        fc1, fc2, fc3, fc4, fc5 = st.columns([2, 2, 1, 1, 1])
        with fc1:
            f_tec  = st.selectbox("👤 Técnico", ["Todos"] + TECNICOS)
        with fc2:
            f_loc  = st.text_input("📍 Local", placeholder="Parte do local...")
        with fc3:
            f_tipo = st.selectbox("Tipo", ["Todos", "Montagem", "Desmontagem"])
        with fc4:
            f_ini  = st.date_input("📅 De",  value=date(2020, 1, 1), key="ci", format="DD/MM/YYYY")
        with fc5:
            f_fim  = st.date_input("📅 Até", value=date.today(),     key="cf", format="DD/MM/YYYY")

    registros = buscar_registros(
        tecnico=f_tec if f_tec != "Todos" else None,
        tipo=f_tipo,
        local=f_loc or None,
        data_ini=f_ini,
        data_fim=f_fim,
    )

    col_tot, col_exp_all = st.columns([3, 1])
    col_tot.markdown(f"**{len(registros)} registro(s) encontrado(s)**")

    if registros:
        with col_exp_all:
            df_all  = registros_para_dataframe(registros)
            exp_fmt = st.selectbox("Formato", ["CSV", "Excel"], key="fmt_all",
                                   label_visibility="collapsed")
        col_a, _ = st.columns([1, 4])
        with col_a:
            if exp_fmt == "CSV":
                st.download_button("⬇️ Exportar todos", data=to_csv_bytes(df_all),
                                   file_name=f"relatorio_{date.today()}.csv", mime="text/csv")
            else:
                st.download_button("⬇️ Exportar todos", data=to_excel_bytes(df_all),
                                   file_name=f"relatorio_{date.today()}.xlsx",
                                   mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

        st.markdown("---")

        for reg in registros:
            itens  = buscar_itens(reg["id"])
            n_def  = sum(1 for i in itens if i["defeituoso"])
            n_aus  = sum(1 for i in itens if not i["consta"])

            badge_def = f'<span class="badge-err">{n_def} defeito(s)</span>&nbsp;' if n_def else ""
            badge_aus = f'<span class="badge-warn">{n_aus} ausente(s)</span>'       if n_aus else ""
            badges    = (f"{badge_def}{badge_aus}".strip()
                         if (badge_def or badge_aus)
                         else '<span class="badge-ok">Tudo OK</span>')

            # ── Expander com título compacto ──────────────────────────────────
            expander_label = (               
                f"{reg['tipo'].upper()} · {reg['local']} · "
                f"Técnico: {reg['tecnico']} · Kits: {reg['qtd_kits']}"
            )
            with st.expander(expander_label):

                # ── Linha de status + ações (compacta) ───────────────────────
                st.markdown(f"**Status:** {badges}", unsafe_allow_html=True)

                # Linha 1 — métricas essenciais em 4 colunas
                m1, m2, m3, m4 = st.columns(4)
                m1.metric("🧰 Kits Usados",  reg.get("kits_usados") or "—")
                m2.metric("⚠️ Defeitos",     n_def)
                m3.metric("❌ Ausentes",     n_aus)
                m4.metric("📍 Local",        reg["local"])

                # Linha 2 — metadata de tempo compacta
                ts_criado    = formatar_ts(reg["criado_em"])
                ts_editado   = formatar_ts(reg.get("atualizado_em"))
                meta_parts   = [f"Registrado em: **{ts_criado}**"]
                if ts_editado:
                    meta_parts.append(f"Última edição: **{ts_editado}**")
                st.caption(" · ".join(meta_parts))

                if reg["observacoes"]:
                    st.info(f"📝 {reg['observacoes']}")

                st.markdown("---")

                # ── Detalhes secundários em abas (evita expanders aninhados) ──
                audit = buscar_audit_log(reg["id"])
                tab_labels = ["📋 Checklist"]
                if audit:
                    tab_labels.append(f"🕵️ Histórico ({len(audit)})")

                tabs = st.tabs(tab_labels)

                with tabs[0]:
                    st.dataframe(
                        itens_para_df_exibicao(itens),
                        use_container_width=True,
                        hide_index=True,
                    )

                if audit:
                    with tabs[1]:
                        for entrada in audit:
                            dt_brt = entrada.get("alterado_em_brt")
                            ts_str = (dt_brt.strftime("%d/%m/%Y %H:%M") + " (BRT)"
                                      if dt_brt else "—")
                            just   = entrada.get("justificativa") or "*(sem justificativa)*"
                            autor  = entrada.get("alterado_por")  or "*(não informado)*"
                            diff   = entrada.get("diff", {})

                            st.markdown(f"**🕐 {ts_str}** · Autor: {autor}")
                            st.markdown(f"*Justificativa:* {just}")

                            if diff:
                                campos_escalares = {k: v for k, v in diff.items()
                                                    if k != "itens"}
                                if campos_escalares:
                                    st.markdown("**Campos alterados:**")
                                    for campo, vals in campos_escalares.items():
                                        label = campo.replace("_", " ").title()
                                        st.markdown(
                                            f"- **{label}:** "
                                            f"`{vals['antes']}` → `{vals['depois']}`"
                                        )
                                itens_diff = diff.get("itens", {})
                                if itens_diff:
                                    st.markdown("**Checklist alterado:**")
                                    for equip, mudancas in itens_diff.items():
                                        for campo, vals in mudancas.items():
                                            label = campo.replace("_", " ").title()
                                            st.markdown(
                                                f"- **{equip} / {label}:** "
                                                f"`{vals['antes']}` → `{vals['depois']}`"
                                            )
                            else:
                                st.caption("Nenhuma diferença detectada nesta edição.")
                            st.markdown("---")

                # ── Botões de ação ─────────────────────────────────────────────
                btn1, btn2, btn3 = st.columns([1, 1.5, 4])
                with btn1:
                    if st.button("✏️ Editar", key=f"edit_{reg['id']}", use_container_width=True):
                        st.query_params["page"] = "Editar"
                        st.query_params["id"]   = reg["id"]
                        # Limpa estado de edição anterior, se houver
                        if "edit_state" in st.session_state:
                            del st.session_state["edit_state"]
                        st.rerun()
                    with st.popover("🗑️ Excluir"):
                        st.warning("⚠️ Esta ação é irreversível e apagará todos os itens vinculados.")
                        if st.button("✔️ Confirmar Exclusão",
                                     key=f"conf_del_{reg['id']}",
                                     type="primary", use_container_width=True):
                            deletar_registro(reg["id"])
                            st.success("Registro excluído.")
                            st.rerun()
                with btn2:
                    df_reg = registros_para_dataframe([reg])
                    st.download_button("⬇️ Exportar CSV", data=to_csv_bytes(df_reg),
                                       file_name=f"registro_{reg['id']}_{reg['data_evento']}.csv",
                                       mime="text/csv", key=f"csv_{reg['id']}")
    else:
        st.info("Nenhum registro encontrado com os filtros aplicados.")


# ════════════════════════════════════════════════════════════════════════════
# PÁGINA DE EDIÇÃO — (acessada via query params)
# Formulário estável: dados carregados UMA VEZ no session_state.
# Checkboxes e outros inputs não causam recarregamento do banco.
# ════════════════════════════════════════════════════════════════════════════
elif pagina == "Editar Registro" and st.query_params.get("page") == "Editar":

    rid_para_editar = int(st.query_params.get("id", 0))
    if not rid_para_editar:
        st.error("ID de registro inválido para edição.")
        st.stop()

    # ── Carrega dados UMA ÚNICA VEZ no session_state ──────────────────────
    # A chave "edit_state" guarda o snapshot dos dados do banco.
    # Ela é deletada apenas quando o usuário salva ou cancela.
    # Assim, reruns causados por widgets NÃO releem o banco.

    if ("edit_state" not in st.session_state
            or st.session_state["edit_state"].get("rid") != rid_para_editar):

        reg_data   = buscar_um_registro(rid_para_editar)
        itens_data = buscar_itens(rid_para_editar)

        if not reg_data:
            st.error(f"Registro com ID {rid_para_editar} não encontrado.")
            st.stop()

        # Normaliza booleanos
        for item in itens_data:
            item["consta"]     = bool(item["consta"])
            item["defeituoso"] = bool(item["defeituoso"])

        st.session_state["edit_state"] = {
            "rid":       rid_para_editar,
            "reg_data":  reg_data,
            "itens_map": {i["equipamento"]: i for i in itens_data},
        }

    estado     = st.session_state["edit_state"]
    reg_data   = estado["reg_data"]
    itens_map  = estado["itens_map"]

    st.subheader(f"✏️ Editando Registro #{rid_para_editar}")

    # ── Dados gerais ──────────────────────────────────────────────────────
    st.markdown("### 1. Dados Gerais")
    col1, col2, col3, col4 = st.columns([2, 1, 1, 2])
    with col1:
        idx_tec = TECNICOS.index(reg_data["tecnico"]) if reg_data["tecnico"] in TECNICOS else 0
        tecnico = st.selectbox("👤 Técnico Responsável *", TECNICOS, index=idx_tec,
                               key=f"e_tec_{rid_para_editar}")
    with col2:
        idx_tipo = (["Montagem", "Desmontagem"].index(reg_data["tipo"])
                    if reg_data["tipo"] in ["Montagem", "Desmontagem"] else 0)
        tipo = st.radio("🔧 Tipo *", ["Montagem", "Desmontagem"], index=idx_tipo,
                        horizontal=False, key=f"e_tipo_{rid_para_editar}")
    with col3:
        qtd_kits = st.number_input("📦 Qtd. de Kits *", min_value=1, max_value=99,
                                   value=int(reg_data["qtd_kits"]), step=1,
                                   key=f"e_qtd_{rid_para_editar}")
    with col4:
        kits_usados = st.text_input("🧰 Kits Usados *", value=reg_data["kits_usados"],
                                    placeholder="Ex: Kit 01, Kit 03",
                                    key=f"e_kits_{rid_para_editar}")

    col_loc, col_dt = st.columns([3, 1])
    with col_loc:
        local = st.text_input("📍 Local *", value=reg_data["local"],
                              placeholder="Ex: CRAS Norte – Rua das Flores, 123",
                              key=f"e_loc_{rid_para_editar}")
    with col_dt:
        data_evento = st.date_input("📅 Data *", value=reg_data["data_evento"],
                                    format="DD/MM/YYYY", key=f"e_dt_{rid_para_editar}")

    st.markdown("---")

    # ── Checklist ─────────────────────────────────────────────────────────
    st.markdown(f"### 2. Checklist de Equipamentos — {formatar_tipo(tipo)}")

    itens_form = []
    for eq in EQUIPAMENTOS:
        item_ex = itens_map.get(eq, {})
        with st.container(border=True):
            c1, c2, c3, c4, c5 = st.columns([3, 1, 1, 1.5, 2.5])
            with c1:
                st.markdown(f"**{eq}**")
            with c2:
                # Chave única que inclui o RID para não conflitar com outros forms
                consta = st.checkbox("Consta",
                                     value=item_ex.get("consta", True),
                                     key=f"e_consta_{eq}_{rid_para_editar}")
            with c3:
                defeituoso = st.checkbox("Defeito",
                                         value=item_ex.get("defeituoso", False),
                                         key=f"e_def_{eq}_{rid_para_editar}")
            kit_def = obs_item = ""
            if defeituoso:
                with c4:
                    kit_def = st.text_input(
                        "Nº Kit", value=item_ex.get("kit_defeito", ""),
                        key=f"e_kitdef_{eq}_{rid_para_editar}", placeholder="Ex: 03")
                with c5:
                    obs_item = st.text_input(
                        "Descrição do defeito", value=item_ex.get("obs_item", ""),
                        key=f"e_obs_{eq}_{rid_para_editar}", placeholder="Descreva brevemente...")

        itens_form.append({
            "equipamento": eq,
            "consta":      consta,
            "defeituoso":  defeituoso,
            "kit_defeito": kit_def,
            "obs_item":    obs_item,
        })

    st.markdown("---")

    # ── Observações gerais ─────────────────────────────────────────────────
    st.markdown("### 3. Observações Gerais")
    observacoes = st.text_area(
        "Registre qualquer informação adicional relevante:",
        value=reg_data["observacoes"],
        height=110, label_visibility="collapsed",
        key=f"e_obs_gerais_{rid_para_editar}",
    )

    st.markdown("---")

    # ── Campos de auditoria ────────────────────────────────────────────────
    st.markdown("### 4. Auditoria da Edição")
    st.caption(
        "Estes campos são gravados no histórico de alterações para fins de rastreabilidade."
    )
    aud1, aud2 = st.columns([1, 2])
    with aud1:
        idx_aut = TECNICOS.index(reg_data["tecnico"]) if reg_data["tecnico"] in TECNICOS else 0
        alterado_por = st.selectbox("👤 Quem está editando?", TECNICOS, index=idx_aut,
                                    key=f"e_autor_{rid_para_editar}")
    with aud2:
        justificativa = st.text_input(
            "📝 Justificativa da alteração *",
            placeholder="Ex: Correção do local do evento. Atualização de defeito no Kit 02.",
            key=f"e_just_{rid_para_editar}",
        )

    st.markdown("---")

    # ── Histórico de auditoria existente (recolhível) ─────────────────────
    audit_existente = buscar_audit_log(rid_para_editar)
    if audit_existente:
        with st.expander(f"🕵️ Ver Histórico de Alterações Anteriores ({len(audit_existente)})"):
            for entrada in audit_existente:
                dt_brt = entrada.get("alterado_em_brt")
                ts_str = dt_brt.strftime("%d/%m/%Y %H:%M") + " (BRT)" if dt_brt else "—"
                just   = entrada.get("justificativa") or "*(sem justificativa)*"
                autor  = entrada.get("alterado_por")  or "*(não informado)*"
                diff   = entrada.get("diff", {})

                st.markdown(f"**🕐 {ts_str}** · Por: **{autor}**")
                st.markdown(f"*Justificativa:* {just}")

                if diff:
                    campos_escalares = {k: v for k, v in diff.items() if k != "itens"}
                    for campo, vals in campos_escalares.items():
                        label = campo.replace("_", " ").title()
                        st.markdown(f"- **{label}:** `{vals['antes']}` → `{vals['depois']}`")
                    itens_diff = diff.get("itens", {})
                    if itens_diff:
                        for equip, mudancas in itens_diff.items():
                            for campo, vals in mudancas.items():
                                label = campo.replace("_", " ").title()
                                st.markdown(
                                    f"- **{equip} / {label}:** "
                                    f"`{vals['antes']}` → `{vals['depois']}`"
                                )
                else:
                    st.caption("Nenhuma diferença detectada.")
                st.markdown("---")

    # ── Botões de ação ─────────────────────────────────────────────────────
    btn_salvar, btn_cancelar = st.columns(2)

    if btn_salvar.button("💾 Salvar Alterações", type="primary", use_container_width=True):
        erros = []
        if not tecnico:
            erros.append("⛔ Nome do técnico é obrigatório.")
        if not kits_usados.strip():
            erros.append("⛔ O preenchimento dos kits usados é obrigatório.")
        if not local.strip():
            erros.append("⛔ Local é obrigatório.")
        if not justificativa.strip():
            erros.append("⛔ A justificativa da edição é obrigatória para fins de auditoria.")

        if erros:
            for e in erros:
                st.error(e)
        else:
            with st.spinner("Atualizando registro..."):
                atualizar_registro(
                    rid_para_editar, tecnico, tipo, local.strip(), qtd_kits,
                    kits_usados.strip(), data_evento, observacoes, itens_form,
                    justificativa=justificativa.strip(),
                    alterado_por=alterado_por,
                )
            st.success(f"✅ Registro #{rid_para_editar} atualizado com sucesso!")
            st.balloons()
            # Limpa estado e redireciona
            if "edit_state" in st.session_state:
                del st.session_state["edit_state"]
            st.query_params.clear()
            import time; time.sleep(1)
            st.rerun()

    if btn_cancelar.button("❌ Cancelar Edição", use_container_width=True):
        if "edit_state" in st.session_state:
            del st.session_state["edit_state"]
        st.query_params.clear()
        st.rerun()


# ════════════════════════════════════════════════════════════════════════════
# PÁGINA 3 — EQUIPAMENTOS DEFEITUOSOS
# ════════════════════════════════════════════════════════════════════════════
elif pagina == "Equipamentos Defeituosos":

    st.subheader("⚠️ Relatório de Equipamentos Defeituosos")

    with st.expander("🎛️ Filtros", expanded=True):
        d1, d2, d3, d4 = st.columns([2, 1, 1, 2])
        with d1:
            d_tec = st.selectbox("👤 Técnico", ["Todos"] + TECNICOS, key="dtec")
        with d2:
            d_ini = st.date_input("📅 De",  value=date(2020, 1, 1), key="dini", format="DD/MM/YYYY")
        with d3:
            d_fim = st.date_input("📅 Até", value=date.today(),     key="dfim", format="DD/MM/YYYY")
        with d4:
            d_eq = st.selectbox("🔧 Equipamento", ["Todos"] + EQUIPAMENTOS, key="deq")

    defeituosos = buscar_defeituosos(
        data_ini=d_ini, data_fim=d_fim,
        tecnico=d_tec if d_tec != "Todos" else None,
        equipamento=d_eq,
    )

    st.markdown(f"**{len(defeituosos)} ocorrência(s) de defeito encontrada(s)**")

    if not defeituosos:
        st.success("✅ Nenhum equipamento defeituoso encontrado para os filtros aplicados!")
    else:
        df_def = pd.DataFrame(defeituosos).rename(columns={
            "reg_id":      "Reg. ID",
            "data_evento": "Data",
            "tipo":        "Tipo",
            "local":       "Local",
            "tecnico":     "Técnico",
            "qtd_kits":    "Kits",
            "kits_usados": "Kits Usados",
            "equipamento": "Equipamento",
            "kit_defeito": "Nº Kit",
            "obs_item":    "Descrição do Defeito",
        })
        df_def["Data"] = pd.to_datetime(df_def["Data"]).dt.strftime("%d/%m/%Y")
        st.dataframe(df_def, use_container_width=True, hide_index=True)

        st.markdown("---")
        st.markdown("### 📊 Equipamentos com Mais Ocorrências de Defeito")
        freq = df_def["Equipamento"].value_counts().reset_index()
        freq.columns = ["Equipamento", "Ocorrências"]
        st.bar_chart(freq.set_index("Equipamento"))

        st.markdown("---")
        ec1, ec2 = st.columns([1, 4])
        with ec1:
            st.download_button("⬇️ Exportar CSV", data=to_csv_bytes(df_def),
                               file_name=f"defeituosos_{date.today()}.csv", mime="text/csv")
        with ec2:
            st.download_button("⬇️ Exportar Excel", data=to_excel_bytes(df_def),
                               file_name=f"defeituosos_{date.today()}.xlsx",
                               mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")


# ════════════════════════════════════════════════════════════════════════════
# PÁGINA 4 — DASHBOARD
# ════════════════════════════════════════════════════════════════════════════
elif pagina == "Dashboard" and "page" not in st.query_params:

    st.subheader("📊 Dashboard Geral")
    stats = stats_gerais()

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

    gc1, gc2 = st.columns(2)
    with gc1:
        with st.container(border=True):
            st.markdown("### 📅 Registros por Data")
            df_tempo = serie_temporal()
            if not df_tempo.empty:
                df_tempo["Data"] = pd.to_datetime(df_tempo["Data"])
                pivot = df_tempo.pivot(index="Data", columns="Tipo", values="Qtd").fillna(0)
                st.bar_chart(pivot)
            else:
                st.info("Sem dados ainda.")

    with gc2:
        with st.container(border=True):
            st.markdown("### 👤 Registros por Técnico")
            df_tec = operacoes_por_tecnico()
            if not df_tec.empty:
                pivot_tec = df_tec.pivot(index="Técnico", columns="Tipo", values="Qtd").fillna(0)
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

    st.markdown("---")
    with st.container(border=True):
        st.markdown("### 🕐 Últimos 10 Registros")
        df_ult = ultimos_registros(10)
        if df_ult.empty:
            st.info("Nenhum registro encontrado ainda.")
        else:
            df_ult["Data"] = pd.to_datetime(df_ult["Data"]).dt.strftime("%d/%m/%Y")
            st.dataframe(df_ult, use_container_width=True, hide_index=True)

    st.markdown("---")
    if stats["total_registros"] > 0:
        st.markdown("### 📤 Exportar Base Completa")
        todos       = buscar_registros()
        df_completo = registros_para_dataframe(todos)
        ex1, ex2 = st.columns([1, 1])
        with ex1:
            st.download_button("⬇️ Baixar tudo em CSV", data=to_csv_bytes(df_completo),
                               file_name=f"base_completa_{date.today()}.csv", mime="text/csv")
        with ex2:
            st.download_button("⬇️ Baixar tudo em Excel", data=to_excel_bytes(df_completo),
                               file_name=f"base_completa_{date.today()}.xlsx",
                               mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
