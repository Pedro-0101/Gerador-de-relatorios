from datetime import timezone, timedelta, datetime
from pathlib import Path

import pandas as pd
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (
    Frame, BaseDocTemplate, PageTemplate, NextPageTemplate,
    PageBreak, Paragraph, Spacer, Image
)

from .tabelaProducaoDiaria import criarTabelaProducaoDiaria
from .graficoProducaoDiaria import graficoLinhaProducaoDiaria
from .cardsIndicadores import criar_cards_indicadores
from .graficoProducaoPorCaminhao import graficoProducaoCaminhao
from .tabelaProducaoCaminhao import criarTabelaProducaoPorCaminhao
from .graficoProducaoPorMotorista import graficoProducaoMotorista
from .tabelaProducaoMotorista import criarTabelaProducaoPorMotorista

from temas.tema_amarelo_dnp import (
    COR_PRIMARIA,
    COR_FUNDO,
    COR_TEXTO_PRIMARIO,
    COR_TEXTO_SECUNDARIO,
    FONT_PADRAO
)

# ---------------------------------------------------------------------
# Constantes globais
# ---------------------------------------------------------------------

TZ_BR = timezone(timedelta(hours=-3))

# pasta do arquivo atual: .../relatorios/producaoPrimaria
_THIS_DIR = Path(__file__).resolve().parent
# raiz do projeto: sobe 2 níveis -> .../
PROJECT_ROOT = _THIS_DIR.parents[1]

# ---------------------------------------------------------------------
# Caminhos logos
# ---------------------------------------------------------------------

DEFAULT_LOGO_PATH_SJ = PROJECT_ROOT / "assets" / "logos" / "logo_sao_joao_1024x400.jpeg"
DEFAULT_LOGO_PATH_P = PROJECT_ROOT / "assets" / "logos" / "logo_pinhal_1024x400.jpeg"

# ---------------------------------------------------------------------
# Helpers de desenho
# ---------------------------------------------------------------------

def _draw_bar(c, x, y, w, h, color=COR_TEXTO_PRIMARIO):
    c.setFillColor(color)
    c.setStrokeColor(color)
    c.rect(x, y, w, h, fill=1, stroke=0)


def _center_text(c, text, y, font=FONT_PADRAO, size=28, color=COR_TEXTO_PRIMARIO):
    page_w, _ = A4
    c.setFont(font, size)
    c.setFillColor(color)
    tw = c.stringWidth(text, font, size)
    x = (page_w - tw) / 2.0
    c.drawString(x, y, text)


# ---------------------------------------------------------------------
# Callbacks de página
# ---------------------------------------------------------------------

def onpage_capa(c, doc):
    ctx = getattr(doc, "capa_ctx", {})

    dataInicio = ctx.get("dataInicio")
    dataFinal = ctx.get("dataFinal")
    titulo = ctx.get("titulo", "Relatório de produção primária")
    empresa = ctx.get("empresa", "Pedreira São João")
    gerado_por = ctx.get("gerado_por", "Sistema OSSJ")

    # pode vir string ou Path; se não vier nada, usa DEFAULT_LOGO_PATH
    caminho_logo_ctx = ctx.get("caminho_logo")
    if caminho_logo_ctx:
        caminho_logo = Path(caminho_logo_ctx)
    else:
        caminho_logo = DEFAULT_LOGO_PATH_SJ

    page_w, page_h = A4

    # fundo
    c.setFillColor(COR_FUNDO)
    c.rect(0, 0, page_w, page_h, fill=1, stroke=0)

    # faixa superior
    _draw_bar(c, 0, page_h - 1.2 * cm, page_w, 1.2 * cm, color=COR_PRIMARIA)

    # Logo (se existir)
    logo_w, logo_h = 5 * cm, 2 * cm
    try:
        if caminho_logo.is_file():
            c.drawImage(
                str(caminho_logo),
                page_w - logo_w - 1.5 * cm,
                page_h - logo_h - 0.9 * cm,
                width=logo_w, height=logo_h, mask='auto'
            )
    except Exception:
        # se der erro, não quebrar o relatório
        pass

    # Período
    if dataInicio and dataFinal:
        periodo = f"De {dataInicio:%d/%m/%Y} a {dataFinal:%d/%m/%Y}"
    else:
        periodo = ""

    _center_text(
        c, titulo,
        y=page_h / 2 + 2.2 * cm,
        font=FONT_PADRAO, size=28, color=COR_TEXTO_PRIMARIO
    )
    _center_text(
        c, periodo,
        y=page_h / 2 + 0.8 * cm,
        font=FONT_PADRAO, size=16, color=COR_TEXTO_SECUNDARIO
    )

    # Bloco com dados da empresa
    c.setFont(FONT_PADRAO, 11)
    c.setFillColor(COR_TEXTO_SECUNDARIO)
    dt_br = datetime.now(TZ_BR).strftime('%d/%m/%Y %H:%M')
    linhas = [
        f"Empresa: {empresa}",
        f"Gerado por: {gerado_por}",
        f"Gerado em: {dt_br}",
    ]
    x0, y0 = 0.8 * cm, 4 * cm
    for i, linha in enumerate(linhas):
        c.drawString(x0, y0 - i * 0.6 * cm, linha)

    # barra inferior
    _draw_bar(c, 0, 2.2 * cm, page_w, 0.15 * cm, color=COR_PRIMARIA)


def onpage_normal(c, doc):
    page_w, page_h = A4
    c.setFont(FONT_PADRAO, 6)
    c.setFillColor(COR_TEXTO_SECUNDARIO)

    M = doc.bottomMargin
    agora = datetime.now(TZ_BR).strftime('%d/%m/%Y %H:%M')

    # esquerda: data/hora
    c.drawString(doc.leftMargin, M * 0.5, agora)

    # centro: sistema
    c.drawCentredString(page_w / 2.0, M * 0.5, "Sistema OSSJ")

    # direita: número da página
    numero_pagina = f"Página {doc.page}"
    c.drawRightString(page_w - doc.rightMargin, M * 0.5, numero_pagina)


# ---------------------------------------------------------------------
# Montagem do relatório
# ---------------------------------------------------------------------

def build_relatorio(
        df: pd.DataFrame,
        dataInicio: datetime,
        dataFinal: datetime,
        titulo: str,
        empresa: str,
        gerado_por: str,
        caminho_logo: str | Path | None,
        mostrar_marcadagua: bool,
        output_path: str | Path = "producaoPrimaria.pdf",
) -> str:
    M = 1.0 * cm
    frame_capa = Frame(M, M, A4[0] - 2 * M, A4[1] - 2 * M, id="frame_capa")
    frame_normal = Frame(M, M, A4[0] - 2 * M, A4[1] - 2 * M, id="frame_normal")

    doc = BaseDocTemplate(
        str(output_path),
        pagesize=A4,
        leftMargin=M, rightMargin=M, topMargin=M, bottomMargin=M,
        title="Relatório Gerencial: Produção primária"
    )

    pt_capa = PageTemplate(id="CAPA", frames=[frame_capa], onPage=onpage_capa)
    pt_norm = PageTemplate(id="NORMAL", frames=[frame_normal], onPage=onpage_normal)
    doc.addPageTemplates([pt_capa, pt_norm])

    # se não vier caminho_logo, usa o default resolvido pelo arquivo
    caminho_logo_final = Path(caminho_logo) if caminho_logo else DEFAULT_LOGO_PATH_SJ

    doc.capa_ctx = {
        "dataInicio": dataInicio,
        "dataFinal": dataFinal,
        "titulo": titulo,
        "empresa": empresa,
        "gerado_por": gerado_por,
        "caminho_logo": str(caminho_logo_final),
        "mostrar_marcadagua": mostrar_marcadagua,
    }

    styles = getSampleStyleSheet()
    styles["Heading1"].fontName = FONT_PADRAO
    styles["Heading1"].textColor = COR_PRIMARIA
    styles["Heading2"].fontName = FONT_PADRAO
    styles["Heading2"].textColor = COR_PRIMARIA
    styles["Normal"].fontName = FONT_PADRAO

    story = []
    story.append(NextPageTemplate("NORMAL"))
    story.append(PageBreak())

    # cartões / gráfico produção diária
    story.append(Paragraph("Geral", styles["Heading1"]))
    story.extend(criar_cards_indicadores(df, styles))
    story.append(Spacer(1, 0.8 * cm))
    story.append(Paragraph("Produção diária", styles["Heading2"]))
    story.append(Image(graficoLinhaProducaoDiaria(df), width=20 * cm, height=12 * cm))

    # tabela produção diária
    story.append(PageBreak())
    story.extend(criarTabelaProducaoDiaria(df, styles, 48))
    story.append(Spacer(1, 0.8 * cm))

    # caminhões
    story.append(PageBreak())
    story.append(Paragraph("Caminhões", styles["Heading2"]))
    story.append(Image(graficoProducaoCaminhao(df), width=20 * cm, height=12 * cm))
    story.append(Spacer(1, 0.4 * cm))
    story.extend(criarTabelaProducaoPorCaminhao(df, styles, 38))

    # motoristas
    story.append(PageBreak())
    story.append(Paragraph("Motoristas", styles["Heading2"]))
    story.append(Image(graficoProducaoMotorista(df), width=20 * cm, height=12 * cm))
    story.append(Spacer(1, 0.4 * cm))
    story.extend(criarTabelaProducaoPorMotorista(df, styles, 38))

    doc.build(story)
    return f"Relatório gerado em: {Path(output_path).resolve()}"


def criarPdf(df, dataInicio, dataFinal, stringNomeObra) -> str:
    out = "producaoPrimaria.pdf"
    obra = df["desc_obra"][0]
    if obra == "SÃO JOÃO":
        caminho_logo = DEFAULT_LOGO_PATH_SJ
    else:
        caminho_logo = DEFAULT_LOGO_PATH_P
        
    return build_relatorio(
        df=df,
        dataInicio=dataInicio,
        dataFinal=dataFinal,
        titulo="Relatório de Produção Mensal",
        empresa=stringNomeObra,
        gerado_por="Sistema OSSJ",
        caminho_logo=caminho_logo,
        mostrar_marcadagua=True,
        output_path=out,
    )
