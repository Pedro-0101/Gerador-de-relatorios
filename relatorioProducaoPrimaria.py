import locale
from datetime import datetime, timezone, timedelta
import pandas as pd
import argparse
import io
import numpy as np
import matplotlib.pyplot as plt
from reportlab.lib.pagesizes import A4
from matplotlib.ticker import FuncFormatter
from reportlab.lib.units import cm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas as _canvas
from reportlab.platypus import (
    BaseDocTemplate, Frame, PageTemplate, NextPageTemplate, PageBreak, Image,
    Paragraph, Spacer, Table, TableStyle
)
from reportlab.lib.styles import getSampleStyleSheet

from temas.tema_amarelo_dnp import (
    COR_PRIMARIA, COR_FUNDO, COR_FUNDO_SECUNDARIA,
    COR_TEXTO_PRIMARIO, COR_TEXTO_SECUNDARIO, COR_GRID
)

from db import load_dataframe

# ================= Locale =================
try:
    locale.setlocale(locale.LC_ALL, "pt_BR.utf8")
except:
    pass

# ================= Fontes =================
pdfmetrics.registerFont(TTFont("DejaVu", "assets/fonts/DejaVuSans.ttf"))
pdfmetrics.registerFont(TTFont("DejaVu-bold", "assets/fonts/DejaVuSans-BoldOblique.ttf"))


# ================= Helpers =================
def _center_text(c, text, y, font="DejaVu-bold", size=28, color=COR_TEXTO_PRIMARIO):
    page_w, _ = A4
    c.setFont(font, size)
    c.setFillColor(COR_TEXTO_PRIMARIO)
    tw = c.stringWidth(text, font, size)
    x = (page_w - tw) / 2.0
    c.drawString(x, y, text)


def _draw_bar(c, x, y, w, h, color=COR_TEXTO_PRIMARIO):
    c.setFillColor(color)
    c.setStrokeColor(color)
    c.rect(x, y, w, h, fill=1, stroke=0)


def _watermark(c, text="CONFIDENCIAL", angle=35, font="DejaVu-bold", size=60, color=COR_GRID):
    page_w, page_h = A4
    c.saveState()
    c.setFillColor(color)
    c.setFont(font, size)
    c.translate(page_w / 2, page_h / 2)
    c.rotate(angle)
    tw = c.stringWidth(text, font, size)
    c.drawString(-tw / 2, -size / 2, text)
    c.restoreState()


# ================= Capa (onPage) =================
def onpage_capa(c, doc):
    ctx = getattr(doc, "capa_ctx", {})
    dataInicio = ctx.get("dataInicio")
    dataFinal = ctx.get("dataFinal")
    titulo = ctx.get("titulo", "Relatório de produção primária")
    empresa = ctx.get("empresa", "Pedreira São João")
    gerado_por = ctx.get("gerado_por", "Sistema OSSJ")
    caminho_logo = ctx.get("caminho_logo", "./assets/logos/logo_sao_joao_1024x400.jpeg")
    mostrar_marcadagua = ctx.get("mostrar_marcadagua", False)

    page_w, page_h = A4

    c.setFillColor(COR_FUNDO)
    c.rect(0, 0, page_w, page_h, fill=1, stroke=0)

    if mostrar_marcadagua:
        _watermark(c, text="PRELIMINAR", angle=35, color=COR_FUNDO)

    _draw_bar(c, 0, page_h - 1.2 * cm, page_w, 1.2 * cm, color=COR_PRIMARIA)

    logo_w, logo_h = 5 * cm, 2 * cm
    try:
        c.drawImage(
            caminho_logo,
            page_w - logo_w - 1.5 * cm,
            page_h - logo_h - 0.9 * cm,
            width=logo_w, height=logo_h, mask='auto'
        )
    except Exception:
        pass

    periodo = f"De {dataInicio.strftime('%d/%m/%Y')} à {dataFinal.strftime('%d/%m/%Y')}" if dataInicio and dataFinal else ""
    _center_text(c, titulo, y=page_h / 2 + 2.2 * cm, font="DejaVu-bold", size=28, color=COR_TEXTO_PRIMARIO)
    _center_text(c, periodo, y=page_h / 2 + 0.8 * cm, font="DejaVu", size=16, color=COR_TEXTO_SECUNDARIO)

    c.setFont("DejaVu", 11)
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


# ================= Cabeçalho normal =================
def onpage_normal(c, doc):
    page_w, page_h = A4
    c.setFont("DejaVu", 9)
    c.setFillColor(COR_TEXTO_SECUNDARIO)
    c.drawString(1.5 * cm, page_h - 1.2 * cm, "Produção primária")
    c.drawRightString(page_w - 1.5 * cm, page_h - 1.2 * cm, datetime.now().strftime("%d/%m/%Y %H:%M"))


# ================= Canvas numerado =================
class NumberedCanvas(_canvas.Canvas):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._saved_page_states = []

    def showPage(self):
        self._saved_page_states.append(dict(self.__dict__))
        self._startPage()

    def save(self):
        total_pages = len(self._saved_page_states)
        for state in self._saved_page_states:
            self.__dict__.update(state)
            self.draw_page_number(total_pages)
            super().showPage()
        super().save()

    def draw_page_number(self, total_pages):
        page_num = self._pageNumber
        text = f"{page_num}/{total_pages}"
        self.setFont("DejaVu", 9)
        self.drawRightString(A4[0] - 1.5 * cm, 1 * cm, text)


# ================= Tabelas =================
def tabelas_detalhadas(df: pd.DataFrame, styles, max_linhas: int = 34):
    elementos = []
    det = df.copy()
    det["time"] = pd.to_datetime(det["time"], errors="coerce").dt.strftime("%d/%m/%Y %H:%M")
    det["volume_descarregado"] = pd.to_numeric(det["volume_descarregado"], errors="coerce").fillna(0.0)
    det["volume_descarregado"] = det["volume_descarregado"].map(
        lambda v: f"{v:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    )
    det.insert(0, "Linha", range(1, len(det) + 1))
    cols = ["Linha", "desc_obra", "prefixo_veiculo", "time", "volume_descarregado"]

    for i in range(0, len(det), max_linhas):
        chunk = det.iloc[i:i + max_linhas]
        data = [["#", "Obra", "Prefixo", "Data/Hora", "Volume"]] + chunk[cols].values.tolist()
        tbl = Table(data, colWidths=[1.2 * cm, 6 * cm, 4 * cm, 4.5 * cm, 3 * cm])
        tbl.setStyle(TableStyle([
            ("FONT", (0, 0), (-1, 0), "DejaVu-bold", 10),
            ("BACKGROUND", (0, 0), (-1, 0), COR_FUNDO),
            ("TEXTCOLOR", (0, 0), (-1, 0), COR_TEXTO_SECUNDARIO),
            ("FONT", (0, 1), (-1, -1), "DejaVu", 9),
            ("GRID", (0, 0), (-1, -1), 0.25, COR_GRID),
            ("ALIGN", (0, 0), (0, -1), "CENTER"),
            ("ALIGN", (4, 1), (4, -1), "RIGHT"),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [COR_FUNDO, COR_FUNDO_SECUNDARIA]),
            ("TOPPADDING", (0, 0), (-1, -1), 4),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ]))
        if i == 0:
            elementos.append(Paragraph("Detalhamento de Registros", styles["Heading2"]))
            elementos.append(Spacer(1, 6))
        else:
            elementos.append(PageBreak())
            elementos.append(Paragraph("Detalhamento de Registros (continuação)", styles["Heading2"]))
            elementos.append(Spacer(1, 6))
        elementos.append(tbl)

    if not elementos:
        elementos.append(Paragraph("Sem registros no período.", styles["Normal"]))
    return elementos


# ================= Grafico de produção diaria =================

def graficoProducaoDiaria(ini, fim, df: pd.DataFrame,
                          coluna_data="time",
                          coluna_valor="volume_descarregado",
                          coluna_grupo="prefixo_veiculo") -> io.BytesIO:
    # prepara dados
    df_tmp = df.copy()
    df_tmp[coluna_data] = pd.to_datetime(df_tmp[coluna_data], errors="coerce")
    df_tmp[coluna_valor] = pd.to_numeric(df_tmp[coluna_valor], errors="coerce").fillna(0)
    df_tmp = df_tmp.dropna(subset=[coluna_data])

    # agrega por dia + caminhão
    grup = (
        df_tmp
        .assign(__date=df_tmp[coluna_data].dt.date)
        .groupby(["__date", coluna_grupo], as_index=False)[coluna_valor].sum()
        .rename(columns={"__date": coluna_data})
    )

    # pivota: linhas = dia, colunas = caminhões
    piv = (
        grup
        .assign(**{coluna_data: pd.to_datetime(grup[coluna_data])})
        .pivot_table(index=coluna_data, columns=coluna_grupo, values=coluna_valor, fill_value=0)
        .sort_index()
    )

    # rótulos "dd/mm (Seg)"
    labels = piv.index.strftime("%d/%m (%a)")

    try:
        plt.style.use("seaborn-v0_8-deep")
    except Exception:
        pass

    fig, ax = plt.subplots(figsize=(20, 12))

    if piv.empty:
        ax.text(0.5, 0.5, "Sem dados no período", ha="center", va="center", fontsize=16)
        ax.axis("off")
    else:
        bottom = None
        for col in piv.columns:
            valores = piv[col].values
            ax.bar(labels, valores, bottom=bottom, label=str(col))
            bottom = (valores if bottom is None else bottom + valores)

        # soma diária total
        totais = piv.sum(axis=1).values
        for i, total in enumerate(totais):
            ax.text(i, total, f"{total:.0f}", ha="center", va="bottom", fontsize=16, fontweight="bold")

        # título e eixos
        ax.set_title(f"Produção por dia (empilhado por caminhão): de {ini} à {fim}", fontsize=22)
        ax.set_xlabel("Data", fontsize=16)
        ax.set_ylabel("Volume descarregado (t)", fontsize=16)
        ax.legend(
            title="Caminhão",
            fontsize=16,
            title_fontsize=20,
            ncol=10,
            frameon=False,
            loc="upper center",
            bbox_to_anchor=(0.5, -0.1)
        )
        ax.grid(True, axis="y", linestyle="--", alpha=0.7)
        plt.xticks(rotation=45, ha="right")  # inclina rótulos do eixo X

    buf = io.BytesIO()
    plt.tight_layout()
    plt.savefig(buf, format="PNG")
    plt.close(fig)
    buf.seek(0)
    return buf


def graficoPieCaminhao(df: pd.DataFrame) -> io.BytesIO:
    df_tmp = df.copy()
    df_tmp["volume_descarregado"] = pd.to_numeric(
        df_tmp["volume_descarregado"], errors="coerce"
    ).fillna(0)

    # agrega volume por veículo
    agrupado = df_tmp.groupby("prefixo_veiculo", as_index=False)["volume_descarregado"].sum()

    labels = agrupado["prefixo_veiculo"]
    sizes = agrupado["volume_descarregado"]

    total = sizes.sum()

    # função para exibir valor e percentual
    def formata_autopct(pct, allvals):
        valor = int(round(pct / 100. * total, 0))
        return f"{pct:.1f}%\n{valor:,.0f} t".replace(",", ".")

    plt.style.use("seaborn-v0_8-dark")
    fig, ax = plt.subplots(figsize=(9, 7))
    wedges, texts, autotexts = ax.pie(
        sizes,
        labels=labels,
        autopct=lambda pct: formata_autopct(pct, sizes),
        startangle=90,
        wedgeprops={"linewidth": 1, "edgecolor": "white"}
    )
    # altera fonte dos labels (nomes dos veículos)
    for t in texts:
        t.set_fontsize(12)
        t.set_fontname("DejaVu Sans")
        t.set_color("black")

    # altera fonte dos dados (percentuais/toneladas)
    for at in autotexts:
        at.set_fontsize(11)
        at.set_fontweight("bold")
        at.set_color("black")
        ax.set_title("Distribuição por veículo", fontsize=22)

    ax.tick_params(axis='x', labelsize=16)
    ax.tick_params(axis='y', labelsize=16)

    buf = io.BytesIO()
    plt.tight_layout()
    plt.savefig(buf, format="PNG")
    plt.close(fig)
    buf.seek(0)
    return buf


# ================= Grafico média de produção por dia da semana =================

def grafico_media_semana(
        df: pd.DataFrame,
        coluna_data="time",
        coluna_valor="volume_descarregado",
        ini=None,
        fim=None,
        drop_zeros=False,
        fmt_valor=lambda v: f"{v:.0f}",  # formato dos valores
) -> io.BytesIO:
    df_tmp = df.copy()
    df_tmp[coluna_data] = pd.to_datetime(df_tmp[coluna_data], errors="coerce")
    df_tmp[coluna_valor] = pd.to_numeric(df_tmp[coluna_valor], errors="coerce")
    df_tmp = df_tmp.dropna(subset=[coluna_data, coluna_valor])

    if ini is not None:
        ini = pd.to_datetime(ini);
        df_tmp = df_tmp[df_tmp[coluna_data] >= ini]
    if fim is not None:
        fim = pd.to_datetime(fim);
        df_tmp = df_tmp[df_tmp[coluna_data] <= fim]

    df_tmp["__data"] = df_tmp[coluna_data].dt.date
    diarios = (
        df_tmp.groupby("__data", as_index=False)[coluna_valor]
        .sum().rename(columns={coluna_valor: "total_dia"})
    )
    diarios["dia_semana"] = pd.to_datetime(diarios["__data"]).dt.dayofweek
    if drop_zeros:
        diarios = diarios[diarios["total_dia"] != 0]

    media = diarios.groupby("dia_semana")["total_dia"].mean().reindex(range(7))
    dias = ["Seg", "Ter", "Qua", "Qui", "Sex", "Sáb", "Dom"]

    x = np.arange(7, dtype=float)
    y = media.values.astype(float)

    fig, ax = plt.subplots(figsize=(9, 7))
    ax.plot(x, y, marker="o", linewidth=2, label="Média")
    ax.set_title("Produção Média por Dia da Semana", fontsize=22)
    ax.set_xlabel("Dia da Semana", fontsize=16)
    ax.set_ylabel("Produção Média (soma diária)", fontsize=16)
    ax.set_xticks(x, dias)
    ax.tick_params(axis='x', labelsize=16)
    ax.tick_params(axis='y', labelsize=16)
    ax.grid(True, linestyle="--", alpha=0.6)

    # monta texto com os valores
    legenda_texto = "\n".join(
        f"{d}: {fmt_valor(val) if not np.isnan(val) else '-'} t"
        for d, val in zip(dias, y)
    )

    # insere a "legenda customizada" dentro do gráfico
    ax.text(
        0.02, 0.02, legenda_texto,
        transform=ax.transAxes,  # coordenadas relativas (0 a 1)
        ha="left", va="bottom",
        fontsize=16,
        bbox=dict(facecolor="white", edgecolor="gray", boxstyle="round,pad=0.4", alpha=0.8)
    )

    plt.tight_layout()
    buf = io.BytesIO()
    fig.savefig(buf, format="png")
    plt.close(fig)
    buf.seek(0)
    return buf


# ================ Grafico de tempo trabalhado ==========================
def grafico_janela_diaria(
        df: pd.DataFrame,
        coluna_data="time",  # coluna datetime
        ini=None,  # filtro inicial opcional
        fim=None,  # filtro final opcional
        tz="America/Sao_Paulo",  # ex.: "America/Sao_Paulo" (se quiser converter)
        altura_linha=0.6,  # espessura de cada barra
        min_width_min=3,  # largura mínima (em minutos) p/ dias com 1 único registro
        titulo="Janela de Início e Término por Dia",
) -> io.BytesIO:
    """
    Gera um gráfico de barras horizontais (Gantt-like) com a primeira e última ocorrência por dia.
    Retorna um buffer PNG (io.BytesIO).
    """

    # --- Tratamento de tipos ---
    df_tmp = df.copy()
    df_tmp[coluna_data] = pd.to_datetime(df_tmp[coluna_data], errors="coerce")
    df_tmp = df_tmp.dropna(subset=[coluna_data])

    # (Opcional) timezone
    if tz is not None:
        # Se já tiver tz, converte; senão, localiza como ingênuo -> tz
        if df_tmp[coluna_data].dt.tz is not None:
            df_tmp[coluna_data] = df_tmp[coluna_data].dt.tz_convert(tz)
        else:
            df_tmp[coluna_data] = df_tmp[coluna_data].dt.tz_localize(tz)

    # Filtro por período (inclusivo)
    if ini is not None:
        ini = pd.to_datetime(ini)
        df_tmp = df_tmp[df_tmp[coluna_data] >= ini]
    if fim is not None:
        fim = pd.to_datetime(fim)
        df_tmp = df_tmp[df_tmp[coluna_data] <= fim]

    plt.style.use("seaborn-v0_8-pastel")

    if df_tmp.empty:
        # Gera uma imagem vazia explicativa
        fig, ax = plt.subplots(figsize=(8, 2))
        ax.text(0.5, 0.5, "Sem dados no período selecionado", ha="center", va="center")
        ax.axis("off")
        buf = io.BytesIO()
        fig.savefig(buf, format="png");
        plt.close(fig);
        buf.seek(0)
        return buf

    # --- Agregação por dia ---
    df_tmp["__dia"] = df_tmp[coluna_data].dt.date
    agg = df_tmp.groupby("__dia")[coluna_data].agg(["min", "max"]).reset_index()

    # Converte horários para "minutos desde meia-noite"
    def _to_minutes(dt):
        # Se tiver tz-aware, usa hora local; caso contrário, direto
        return int(dt.hour) * 60 + int(dt.minute) + dt.second / 60.0

    start_min = agg["min"].apply(_to_minutes).astype(float)
    end_min = agg["max"].apply(_to_minutes).astype(float)

    # Largura: garante mínimo para dias com único registro (start == end)
    width_min = (end_min - start_min).where(end_min > start_min, min_width_min)

    # Rótulos (nomes dos dias + data)
    # Ex.: "Seg 2025-08-28"
    dias_semana = ["Seg", "Ter", "Qua", "Qui", "Sex", "Sáb", "Dom"]
    labels = [
        f"{dias_semana[pd.to_datetime(d).dayofweek]} {pd.to_datetime(d).strftime('%d/%m/%Y')}"
        for d in agg["__dia"]
    ]

    # Ordena por data ascendente (opcional)
    order = np.argsort(pd.to_datetime(agg["__dia"]).values)
    start_min = start_min.iloc[order].reset_index(drop=True)
    width_min = width_min.iloc[order].reset_index(drop=True)
    end_min = end_min.iloc[order].reset_index(drop=True)
    labels = [labels[i] for i in order]

    # --- Plot ---
    fig, ax = plt.subplots(figsize=(20, max(2.5, 5 + altura_linha * len(labels))))

    y_pos = np.arange(len(labels))
    ax.barh(y_pos, width_min, left=start_min, height=altura_linha, align="center")

    # Eixo Y com os dias
    ax.set_yticks(y_pos, labels)

    # Formata X (minutos) como HH:MM
    def _fmt_hhmm(x, pos):
        if np.isnan(x):
            return ""
        x = int(round(x))
        h = x // 60
        m = x % 60
        h = h % 24  # segurança
        return f"{h:02d}:{m:02d}"

    ax.xaxis.set_major_formatter(FuncFormatter(_fmt_hhmm))

    # Grade sutil
    ax.grid(True, axis="x", linestyle="--", alpha=0.5)
    ax.set_xlabel("Horário", fontsize=16)
    ax.set_title(titulo, fontsize=22)
    ax.set_ylabel("Dia", fontsize=16)
    ax.tick_params(axis="y", pad=20, right=20)
    ax.tick_params(axis='x', labelsize=16)
    ax.tick_params(axis='y', labelsize=16)
    ax.set_xlim(left=7 * 60, right=19 * 60)
    ax.invert_yaxis()

    # Anotações nos extremos (início e fim)
    for yi, (s, e) in enumerate(zip(start_min, end_min)):
        ax.annotate(_fmt_hhmm(s, None), (s, yi), xytext=(4, 0), textcoords="offset points",
                    ha="left", va="center", fontsize=16)
        ax.annotate(_fmt_hhmm(e, None), (e, yi), xytext=(4, 0), textcoords="offset points",
                    ha="left", va="center", fontsize=16)

    plt.tight_layout()

    # Exporta para buffer
    buf = io.BytesIO()
    fig.savefig(buf, format="png")
    plt.close(fig)
    buf.seek(0)
    return buf


# ================= Grafico de producao media por hora =================
def grafico_media_por_hora(
        df: pd.DataFrame,
        coluna_data="time",
        coluna_valor="volume_descarregado",
        ini=None,
        fim=None,
        hora_ini=7,
        hora_fim=19,  # exclusivo (19 → último intervalo será 18–19)
        incluir_dias_sem_mov=False,
        fmt_valor=lambda v: f"{v:.1f}t",
        titulo="Média de Produção por Hora",
        alpha_preench=0.35,  # transparência do preenchimento
) -> io.BytesIO:
    """
    Gera gráfico de área (preenchido) com a média de produção por hora.
    Retorna um buffer PNG (io.BytesIO).
    """
    df_tmp = df.copy()
    df_tmp[coluna_data] = pd.to_datetime(df_tmp[coluna_data], errors="coerce")
    df_tmp[coluna_valor] = pd.to_numeric(df_tmp[coluna_valor], errors="coerce")
    df_tmp = df_tmp.dropna(subset=[coluna_data, coluna_valor])

    if ini is not None:
        ini = pd.to_datetime(ini);
        df_tmp = df_tmp[df_tmp[coluna_data] >= ini]
    if fim is not None:
        fim = pd.to_datetime(fim);
        df_tmp = df_tmp[df_tmp[coluna_data] <= fim]

    if df_tmp.empty:
        fig, ax = plt.subplots(figsize=(20, 8))
        ax.text(0.5, 0.5, "Sem dados no período selecionado", ha="center", va="center")
        ax.axis("off")
        buf = io.BytesIO();
        fig.savefig(buf, format="png");
        plt.close(fig);
        buf.seek(0)
        return buf

    horas = np.arange(hora_ini, hora_fim, 1)
    labels = [f"{h:02d}–{(h + 1) % 24:02d}" for h in horas]

    df_tmp["__data"] = df_tmp[coluna_data].dt.date
    df_tmp["__hora"] = df_tmp[coluna_data].dt.hour

    por_dia_hora = (
        df_tmp.groupby(["__data", "__hora"], as_index=False)[coluna_valor]
        .sum().rename(columns={coluna_valor: "total_hora"})
    )
    por_dia_hora = por_dia_hora[por_dia_hora["__hora"].between(hora_ini, hora_fim - 1)]

    if incluir_dias_sem_mov:
        dias = pd.Index(sorted(por_dia_hora["__data"].unique()))
        idx = pd.MultiIndex.from_product([dias, horas], names=["__data", "__hora"])
        por_dia_hora = (
            por_dia_hora.set_index(["__data", "__hora"])
            .reindex(idx, fill_value=0)
            .reset_index()
        )

    media_por_hora = (
        por_dia_hora.groupby("__hora")["total_hora"]
        .mean()
        .reindex(horas)
    ).astype(float)

    # --- plot ---
    fig, ax = plt.subplots(figsize=(20, 6))
    x = horas.astype(float)
    y = media_por_hora.values

    # curva em degrau (where="post") + preenchimento
    ax.step(x, y, where="post", linewidth=2, color="#1f77b4")
    ax.fill_between(x, y, step="post", alpha=alpha_preench, color="#1f77b4")

    # rótulos no centro de cada faixa
    for h, v in zip(horas, y):
        if not np.isnan(v):
            ax.annotate(
                fmt_valor(v),
                xy=(h + 0.5, v),
                xytext=(0, -1), textcoords="offset points",
                ha="center", va="bottom", fontsize=16
            )

    ax.set_xticks(horas, labels)
    ax.set_xlim(hora_ini, hora_fim)
    ax.set_title(titulo, fontsize=22)
    ax.set_xlabel("Hora", fontsize=16)
    ax.set_ylabel("Produção média", fontsize=16)
    ax.tick_params(axis='x', labelsize=16)
    ax.tick_params(axis='y', labelsize=16)
    ax.grid(True, axis="y", linestyle="--", alpha=0.5)

    plt.tight_layout()
    buf = io.BytesIO()
    fig.savefig(buf, format="png")
    plt.close(fig)
    buf.seek(0)
    return buf


# ================= Campos total e  media diaria =================

def grafico_total_e_media(
        df: pd.DataFrame,
        coluna_data="time",
        coluna_valor="volume_descarregado",
        ini=None,
        fim=None,
        titulo="Resumo de Produção"
) -> io.BytesIO:
    """
    Gera um 'gráfico' simples com total e média de produção por dia.
    Retorna um buffer PNG (io.BytesIO).
    """

    # --- tratamento ---
    df_tmp = df.copy()
    df_tmp[coluna_data] = pd.to_datetime(df_tmp[coluna_data], errors="coerce")
    df_tmp[coluna_valor] = pd.to_numeric(df_tmp[coluna_valor], errors="coerce")
    df_tmp = df_tmp.dropna(subset=[coluna_data, coluna_valor])

    # filtro de período
    if ini is not None:
        ini = pd.to_datetime(ini);
        df_tmp = df_tmp[df_tmp[coluna_data] >= ini]
    if fim is not None:
        fim = pd.to_datetime(fim);
        df_tmp = df_tmp[df_tmp[coluna_data] <= fim]

    if df_tmp.empty:
        fig, ax = plt.subplots(figsize=(20, 6))
        ax.text(0.5, 0.5, "Sem dados no período", ha="center", va="center")
        ax.axis("off")
        buf = io.BytesIO();
        fig.savefig(buf, format="png");
        plt.close(fig);
        buf.seek(0)
        return buf

    # --- cálculos ---
    total = df_tmp[coluna_valor].sum()
    diarios = df_tmp.groupby(df_tmp[coluna_data].dt.date)[coluna_valor].sum()
    media_dia = diarios.mean()

    # --- layout ---
    fig, ax = plt.subplots(figsize=(8, 3))
    ax.axis("off")
    ax.set_title(titulo, fontsize=18, weight="bold")

    ax.text(0.05, 0.6, "Total no período:", fontsize=14, ha="left", weight="bold")
    ax.text(0.95, 0.6, f"{total:,.0f} t", fontsize=14, ha="right")

    ax.text(0.05, 0.3, "Média por dia:", fontsize=14, ha="left", weight="bold")
    ax.text(0.95, 0.3, f"{media_dia:,.1f} t/dia", fontsize=14, ha="right")

    plt.tight_layout()

    # --- exporta ---
    buf = io.BytesIO()
    fig.savefig(buf, format="png")
    plt.close(fig)
    buf.seek(0)
    return buf


# ================= Build Relatório =================
def build_relatorio(df: pd.DataFrame,
                    dataInicio: datetime,
                    dataFinal: datetime,
                    titulo: str,
                    empresa: str,
                    gerado_por: str,
                    caminho_logo: str,
                    mostrar_marcadagua: bool,
                    gerar_pdf: bool = True):  # <--- novo parâmetro

    stringDataInicio = dataInicio.strftime("%d/%m/%Y")
    stringDataFinal = dataFinal.strftime("%d/%m/%Y")

    # sempre gera os gráficos
    imageGraficoProducaoDiaria = graficoProducaoDiaria(stringDataInicio, stringDataFinal, df, "time",
                                                       "volume_descarregado")
    imageGraficoPieCaminhao = graficoPieCaminhao(df)
    imageGraficoMediaDiaSemana = grafico_media_semana(df)
    imageGraficoTempoTrabalhado = grafico_janela_diaria(df)
    imageGraficoMediaProducaoPorHora = grafico_media_por_hora(df)
    imageTotalMedia = grafico_total_e_media(df)

    # se não for gerar PDF, retorna só os gráficos
    if not gerar_pdf:
        return {
            "graficoProducaoDiaria": imageGraficoProducaoDiaria,
            "graficoPieCaminhao": imageGraficoPieCaminhao,
            "graficoMediaDiaSemana": imageGraficoMediaDiaSemana,
            "graficoTempoTrabalhado": imageGraficoTempoTrabalhado,
            "graficoMediaProducaoPorHora": imageGraficoMediaProducaoPorHora,
        }

    # -----------------------------------
    # parte do PDF só roda se gerar_pdf=True
    # -----------------------------------

    M = 1.5 * cm
    frame_capa = Frame(M, M, A4[0] - 2 * M, A4[1] - 2 * M, id="frame_capa")
    frame_normal = Frame(M, M, A4[0] - 2 * M, A4[1] - 2 * M, id="frame_normal")

    doc = BaseDocTemplate(
        "producaoPrimaria.pdf",
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
        "caminho_logo": caminho_logo,
        "mostrar_marcadagua": mostrar_marcadagua,
    }

    # imagens lado a lado
    img1 = Image(imageGraficoPieCaminhao, width=9 * cm, height=7 * cm, hAlign="LEFT")
    img2 = Image(imageGraficoMediaDiaSemana, width=9 * cm, height=7 * cm, hAlign="RIGHT")
    tabela = Table([[img1, img2]], colWidths=[9 * cm, 7 * cm])

    styles = getSampleStyleSheet()
    styles["Heading2"].fontName = "DejaVu-bold"
    styles["Heading2"].textColor = COR_PRIMARIA
    styles["Normal"].fontName = "DejaVu"

    story = []
    story.append(NextPageTemplate("NORMAL"))
    story.append(PageBreak())
    story.append(Paragraph("Indicadores de produção primária", styles["Heading1"]))
    story.append(Image(imageTotalMedia, width=20 * cm, height=6 * cm))
    story.append(Image(imageGraficoProducaoDiaria, width=20 * cm, height=12 * cm))
    story.append(tabela)
    story.append(Image(imageGraficoMediaProducaoPorHora, width=20 * cm, height=6 * cm))
    story.append(Image(imageGraficoTempoTrabalhado, width=20 * cm, height=20 * cm))
    story.append(NextPageTemplate("NORMAL"))
    story.append(PageBreak())
    story.append(Paragraph("Resumo", styles["Heading2"]))
    story.append(Spacer(1, 6))
    story.extend(tabelas_detalhadas(df, styles, max_linhas=34))

    doc.build(story, canvasmaker=NumberedCanvas)

    return "Relatório gerado com sucesso."


# ================= MAIN =================
def main():
    parser = argparse.ArgumentParser(description="Gerar relatório de produção primária")
    parser.add_argument("--ini", required=True, help="Data inicial (ex: 2025-08-01 00:00:00)")
    parser.add_argument("--fim", required=True, help="Data final (ex: 2025-08-28 23:59:59)")
    parser.add_argument("--obra", required=True, type=int, help="Código da obra")
    args = parser.parse_args()

    # converte datas string -> datetime
    dataInicio = datetime.strptime(args.ini, "%Y-%m-%d %H:%M:%S")
    dataFinal = datetime.strptime(args.fim, "%Y-%m-%d %H:%M:%S")

    # converte codigo_obra para nome da obra
    descObra = load_dataframe("SELECT desc_obra FROM ossj_cad_obra WHERE id = :obra", params={"obra": args.obra})
    stringNomeObra = descObra["desc_obra"].iloc[0]

    sql = """
          SELECT cp.`time`,
                 v.prefixo_veiculo,
                 cp.volume_descarregado,
                 o.desc_obra
          FROM ossj_contador_primario AS cp
                   JOIN ossj_veiculo_sensor_rfid AS v
                        ON cp.user_id_device = v.user_id_sensor
                   JOIN ossj_sensor_rfid AS sr
                        ON cp.device_id = sr.device_id
                   JOIN ossj_cad_obra AS o
                        ON sr.local_instalacao = o.id
          WHERE cp.codigo_planta = :obra
            AND cp.`time` BETWEEN :ini AND :fim
          ORDER BY cp.`time` \
          """
    df = load_dataframe(sql, params={
        "ini": args.ini,
        "fim": args.fim,
        "obra": args.obra
    })

    if df.empty:
        df = pd.DataFrame({
            "desc_obra": ["Obra A", "Obra B", "Obra C", "Obra A", "Obra B"],
            "prefixo_veiculo": ["U1", "U2", "U3", "U4", "U5"],
            "time": pd.date_range("2025-08-01", periods=5, freq="D"),
            "volume_descarregado": [120, 80, 140, 60, 110],
        })

    build_relatorio(
        df=df,
        dataInicio=dataInicio,
        dataFinal=dataFinal,
        titulo="Relatório de Produção Mensal",
        empresa=stringNomeObra,
        gerado_por="Sistema OSSJ",
        caminho_logo="./assets/logos/logo_sao_joao_1024x400.jpeg",
        mostrar_marcadagua=True,
        gerar_pdf=True
    )


if __name__ == "__main__":
    main()
