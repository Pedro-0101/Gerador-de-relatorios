import os
from pathlib import Path

import pandas as pd
from reportlab.lib import colors
from reportlab.lib.units import cm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import Table, TableStyle, Paragraph, Spacer, PageBreak, Indenter

from temas.tema_amarelo_dnp import (
    COR_FUNDO, COR_GRID, COR_FUNDO_SECUNDARIA
)


def register_win_font(family: str, filename: str) -> str:
    candidates = [
        os.path.join(os.environ.get("LOCALAPPDATA", ""), r"Microsoft\Windows\Fonts", filename),
        os.path.join(os.environ.get("WINDIR", r"C:\Windows"), "Fonts", filename),
    ]
    for p in candidates:
        if os.path.exists(p):
            pdfmetrics.registerFont(TTFont(family, p))
            return family
    raise FileNotFoundError(f"Não achei a fonte: {filename} nas pastas de fontes do Windows.")


FONT = register_win_font("Calibri", "Calibri.ttf")


# helper: coloca iniciais em maiúsculo com regras pt-BR simples
def titlecase_pt(s: str) -> str:
    s = ("" if s is None else str(s)).strip().lower()
    if not s:
        return ""
    minusculas = {"da", "de", "do", "das", "dos", "e", "di", "du", "del", "van", "von", "d"}
    tokens = s.split()

    def cap_word(w: str) -> str:
        # trata hifens: "maria-joao" -> "Maria-Joao"
        w = "-".join(p[:1].upper() + p[1:] if p else p for p in w.split("-"))
        # trata "d'ávila" -> "d'Ávila"
        if len(w) > 2 and w[:2] == "d'":
            w = "d'" + (w[2:3].upper() + w[3:])
        return w

    out = []
    for i, w in enumerate(tokens):
        if i > 0 and w in minusculas:
            out.append(w)
        else:
            out.append(cap_word(w))
    return " ".join(out)


def criarTabelaGeral(df: pd.DataFrame, styles, max_linhas: int = 34):
    elementos = []
    det = df.copy()

    # Garante colunas necessárias
    for col in ("time", "nome", "volume_descarregado", "desc_obra", "prefixo_veiculo"):
        if col not in det.columns:
            det[col] = "" if col != "volume_descarregado" else 0.0

    # Formata data/hora
    det["time"] = pd.to_datetime(det["time"], errors="coerce").dt.strftime("%d/%m/%Y %H:%M")
    det["time"] = det["time"].fillna("")

    # Formata volume como string pt-BR
    det["volume_descarregado"] = pd.to_numeric(det["volume_descarregado"], errors="coerce").fillna(0.0)
    det["volume_descarregado"] = det["volume_descarregado"].map(
        lambda v: f"{v:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    )

    # Formata nome para ter letras maiusculas
    if "nome" in det.columns:
        det["nome"] = det["nome"].map(titlecase_pt)

    # Formata obra para ter letras maiusculas
    if "desc_obra" in det.columns:
        det["desc_obra"] = det["desc_obra"].map(titlecase_pt)

    # Formata prefixo para ter letras maiusculas
    if "prefixo_veiculo" in det.columns:
        det["prefixo_veiculo"] = det["prefixo_veiculo"].map(titlecase_pt)

    # Coluna índice 1..N
    det.insert(0, "Linha", range(1, len(det) + 1))
    cols = ["Linha", "desc_obra", "prefixo_veiculo", "nome", "time", "volume_descarregado"]

    FONT_HDR = "Calibri"
    FONT_BODY = "Calibri"
    HDR_COLOR = colors.HexColor("#666666")  # cinza do cabeçalho

    for i in range(0, len(det), max_linhas):
        chunk = det.iloc[i:i + max_linhas]
        data = [["#", "Obra", "Prefixo", "Motorista", "Data/Hora", "Volume"]] + chunk[cols].values.tolist()

        tbl = Table(data, colWidths=[1.2 * cm, 3 * cm, 3 * cm, 6 * cm, 3 * cm, 3 * cm])
        tbl.setStyle(TableStyle([
            ("FONT", (0, 0), (-1, 0), FONT_HDR, 9),
            ("BACKGROUND", (0, 0), (-1, 0), COR_FUNDO),
            ("TEXTCOLOR", (0, 0), (-1, 0), HDR_COLOR),

            ("FONT", (0, 1), (-1, -1), FONT_BODY, 8),
            ("LINEBELOW", (0, 0), (-1, 0), 0.6, COR_GRID),
            ("LINEBELOW", (0, 1), (-1, -1), 0.25, COR_GRID),

            ("ALIGN", (0, 0), (0, -1), "CENTER"),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),

            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [COR_FUNDO, COR_FUNDO]),
            ("TOPPADDING", (0, 0), (-1, -1), 4),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 5),

            ("REPEATROWS", (0, 0), (-1, 0)),  # repete cabeçalho se a tabela quebrar
        ]))

        if i == 0:
            elementos.append(Paragraph("Detalhamento de Registros", styles["Heading2"]))
            elementos.append(Spacer(1, 0.2 * cm))
        else:
            elementos.append(PageBreak())
            elementos.append(Paragraph("Detalhamento de Registros (continuação)", styles["Heading2"]))
            elementos.append(Spacer(1, 0.2 * cm))

        m = 1.0 * cm  # “margem” lateral adicional apenas para a tabela
        elementos.append(Indenter(left=m, right=m))
        elementos.append(tbl)
        elementos.append(Indenter(left=-m, right=-m))

    if not elementos:
        elementos.append(Paragraph("Sem registros no período.", styles["Normal"]))

    return elementos
