from datetime import timezone, timedelta, datetime
from pathlib import Path
from typing import Optional

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
from .criarTabelaGeral import criarTabelaGeral
from .producaoDiariaPorCaminhao import graficoLinhaProducaoDiaria

from temas.tema_amarelo_dnp import (
    COR_PRIMARIA, COR_FUNDO,
    COR_TEXTO_PRIMARIO, COR_TEXTO_SECUNDARIO, COR_GRID, COR_FUNDO_SECUNDARIA,
)

# --------- paths robustos (fonte/logo) ----------
HERE = Path(__file__).resolve()
PKG_ROOT = HERE.parents[2]
PROJECT_ROOT = PKG_ROOT.parent
FONT_DIRS = [
    PROJECT_ROOT / "assets" / "fonts",
    PKG_ROOT / "assets" / "fonts",
]
LOGOS = PROJECT_ROOT / "assets" / "logos"


def _register_ttf_safe(internal_name: str, candidate_files: list[str]) -> str:
    for base in FONT_DIRS:
        for fname in candidate_files:
            p = base / fname
            if p.exists():
                pdfmetrics.registerFont(TTFont(internal_name, str(p)))
                return internal_name
    # fallback para fontes embutidas do ReportLab
    return "Helvetica-Bold" if "bold" in internal_name.lower() else "Helvetica"


FONT_REGULAR = _register_ttf_safe("DejaVu", ["DejaVuSans.ttf", "DejaVuSans-Regular.ttf"])
FONT_BOLD = _register_ttf_safe("DejaVu-bold", ["DejaVuSans-Bold.ttf", "DejaVuSans-BoldOblique.ttf"])


def _draw_bar(c, x, y, w, h, color=COR_TEXTO_PRIMARIO):
    c.setFillColor(color)
    c.setStrokeColor(color)
    c.rect(x, y, w, h, fill=1, stroke=0)


def _center_text(c, text, y, font=FONT_BOLD, size=28, color=COR_TEXTO_PRIMARIO):
    page_w, _ = A4
    c.setFont(font, size)
    c.setFillColor(color)
    tw = c.stringWidth(text, font, size)
    x = (page_w - tw) / 2.0
    c.drawString(x, y, text)


def onpage_capa(c, doc):
    ctx = getattr(doc, "capa_ctx", {})
    dataInicio = ctx.get("dataInicio")
    dataFinal = ctx.get("dataFinal")
    titulo = ctx.get("titulo", "Relatório de produção primária")
    empresa = ctx.get("empresa", "Pedreira São João")
    gerado_por = ctx.get("gerado_por", "Sistema OSSJ")
    caminho_logo: Optional[Path] = Path(ctx.get("caminho_logo", LOGOS / "logo_sao_joao_1024x400.jpeg"))

    page_w, page_h = A4

    c.setFillColor(COR_FUNDO)
    c.rect(0, 0, page_w, page_h, fill=1, stroke=0)

    _draw_bar(c, 0, page_h - 1.2 * cm, page_w, 1.2 * cm, color=COR_PRIMARIA)

    # Logo (se existir)
    logo_w, logo_h = 5 * cm, 2 * cm
    try:
        if caminho_logo and Path(caminho_logo).exists():
            c.drawImage(
                str(caminho_logo),
                page_w - logo_w - 1.5 * cm,
                page_h - logo_h - 0.9 * cm,
                width=logo_w, height=logo_h, mask='auto'
            )
    except Exception:
        pass

    periodo = (
        f"De {dataInicio.strftime('%d/%m/%Y')} à {dataFinal.strftime('%d/%m/%Y')}"
        if dataInicio and dataFinal else ""
    )
    _center_text(c, titulo, y=page_h / 2 + 2.2 * cm, font=FONT_BOLD, size=28, color=COR_TEXTO_PRIMARIO)
    _center_text(c, periodo, y=page_h / 2 + 0.8 * cm, font=FONT_REGULAR, size=16, color=COR_TEXTO_SECUNDARIO)

    c.setFont(FONT_REGULAR, 11)
    c.setFillColor(COR_TEXTO_SECUNDARIO)
    fuso = timezone(timedelta(hours=-3))
    dt_br = datetime.now().astimezone(fuso).strftime('%d/%m/%Y %H:%M')
    linhas = [
        f"Empresa: {empresa}",
        f"Gerado por: {gerado_por}",
        f"Gerado em: {dt_br}",
    ]
    x0, y0 = 0.8 * cm, 4 * cm
    for i, linha in enumerate(linhas):
        c.drawString(x0, y0 - i * 0.6 * cm, linha)

    _draw_bar(c, 0, 2.2 * cm, page_w, 0.15 * cm, color=COR_PRIMARIA)


def onpage_normal(c, doc):
    page_w, page_h = A4
    c.setFont(FONT_REGULAR, 6)
    c.setFillColor(COR_TEXTO_SECUNDARIO)

    M = doc.bottomMargin
    tz = timezone(timedelta(hours=-3))  # America/Sao_Paulo
    agora = str(datetime.now(tz).strftime('%d/%m/%Y %H:%M'))

    c.drawString(doc.leftMargin, M * 0.5, agora)
    c.drawCentredString((page_w / 2.0)-2.0, M / 2.0, "Sistema OSSJ")

def build_relatorio(
        df: pd.DataFrame,
        dataInicio: datetime,
        dataFinal: datetime,
        titulo: str,
        empresa: str,
        gerado_por: str,
        caminho_logo: str | Path,
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

    doc.capa_ctx = {
        "dataInicio": dataInicio,
        "dataFinal": dataFinal,
        "titulo": titulo,
        "empresa": empresa,
        "gerado_por": gerado_por,
        "caminho_logo": str(caminho_logo),
        "mostrar_marcadagua": mostrar_marcadagua,
    }

    styles = getSampleStyleSheet()
    styles["Heading1"].fontName = FONT_BOLD
    styles["Heading1"].textColor = COR_PRIMARIA
    styles["Heading2"].fontName = FONT_BOLD
    styles["Heading2"].textColor = COR_PRIMARIA
    styles["Normal"].fontName = FONT_REGULAR

    story = [
        NextPageTemplate("NORMAL"),
        PageBreak(),
        Image(graficoLinhaProducaoDiaria(df), width=20 * cm, height=12 * cm),
        PageBreak(),
    ]
    story.extend(criarTabelaProducaoDiaria(df, styles, 38))

    doc.build(story)
    return f"Relatório gerado em: {Path(output_path).resolve()}"


def criarPdf(df, dataInicio, dataFinal, stringNomeObra) -> str:
    out = PROJECT_ROOT / "producaoPrimaria.pdf"
    return build_relatorio(
        df=df,
        dataInicio=dataInicio,
        dataFinal=dataFinal,
        titulo="Relatório de Produção Mensal",
        empresa=stringNomeObra,
        gerado_por="Sistema OSSJ",
        caminho_logo=LOGOS / "logo_sao_joao_1024x400.jpeg",
        mostrar_marcadagua=True,
        output_path=out,
    )
