"""
utils.py
Funções auxiliares: exportação, formatação, etc.
"""

import io
from datetime import datetime
import pandas as pd
from database import buscar_itens


def registros_para_dataframe(registros: list[dict]) -> pd.DataFrame:
    """Expande registros + itens em um DataFrame plano para exportação."""
    rows = []
    for reg in registros:
        for item in buscar_itens(reg["id"]):
            rows.append({
                "ID":                   reg["id"],
                "Data":                 formatar_data(reg["data_evento"]),
                "Tipo":                 reg["tipo"],
                "Técnico":              reg["tecnico"],
                "Local":                reg["local"],
                "Qtd. Kits":            reg["qtd_kits"],
                "Observações Gerais":   reg["observacoes"],
                "Equipamento":          item["equipamento"],
                "Consta":               "Sim" if item["consta"]     else "Não",
                "Defeituoso":           "Sim" if item["defeituoso"] else "Não",
                "Nº Kit Defeituoso":    item["kit_defeito"],
                "Obs. Equipamento":     item["obs_item"],
                "Registrado em":        formatar_data(reg["criado_em"]),
            })
    return pd.DataFrame(rows)

def formatar_data(data_str: str) -> str:
    """Converte YYYY-MM-DD HH:MM:SS ou YYYY-MM-DD para o padrão brasileiro"""
    if not data_str: return ""
    try:
        val = str(data_str)
        if " " in val:
            dt = datetime.strptime(val[:19], "%Y-%m-%d %H:%M:%S")
            return dt.strftime("%d/%m/%Y %H:%M")
        else:
            dt = datetime.strptime(val[:10], "%Y-%m-%d")
            return dt.strftime("%d/%m/%Y")
    except ValueError:
        return str(data_str)

def to_csv_bytes(df: pd.DataFrame) -> bytes:
    return df.to_csv(index=False).encode("utf-8-sig")


def to_excel_bytes(df: pd.DataFrame) -> bytes:
    buf = io.BytesIO()
    with pd.ExcelWriter(buf, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name="Relatório")
        ws = writer.sheets["Relatório"]
        # Ajusta largura das colunas automaticamente
        for col_cells in ws.columns:
            max_len = max((len(str(c.value or "")) for c in col_cells), default=10)
            ws.column_dimensions[col_cells[0].column_letter].width = min(max_len + 4, 50)
    return buf.getvalue()


def formatar_tipo(tipo: str) -> str:
    icons = {"Montagem": "🔧", "Desmontagem": "📦"}
    return f"{icons.get(tipo, '')} {tipo}"


def itens_para_df_exibicao(itens: list[dict]) -> pd.DataFrame:
    df = pd.DataFrame(itens)[
        ["equipamento", "consta", "defeituoso", "kit_defeito", "obs_item"]
    ].rename(columns={
        "equipamento": "Equipamento",
        "consta":      "Consta",
        "defeituoso":  "Defeituoso",
        "kit_defeito": "Nº Kit",
        "obs_item":    "Obs. Equipamento",
    })
    df["Consta"]     = df["Consta"].map({1: "✅ Sim", 0: "❌ Não"})
    df["Defeituoso"] = df["Defeituoso"].map({1: "⚠️ Sim", 0: "—"})
    return df
