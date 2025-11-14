import pandas as pd
from reportlab.lib.units import cm
from reportlab.lib import colors
from reportlab.platypus import Table, TableStyle, Paragraph, Spacer, PageBreak, Indenter

from temas.tema_amarelo_dnp import (
  COR_FUNDO, COR_GRID, COR_FUNDO_SECUNDARIA
)
FONT = "Helvetica"

# helper: coloca iniciais em maiúsculo com regras pt-BR simples (ajuste sutil)
def titlecase_pt(s: str) -> str:
  s = ("" if s is None else str(s)).strip().lower()
  if not s:
    return ""
  minusculas = {"da", "de", "do", "das", "dos", "e", "di", "du", "del", "van", "von", "d"}
  tokens = s.split()

  def cap_word(w: str) -> str:
    # trata hifens: "maria-joao" -> "Maria-Joao"
    parts = []
    for p in w.split("-"):
      if p == "":
        parts.append(p)
      else:
        # trata "d'ávila" -> "d'Ávila"
        if len(p) > 2 and p[:2] == "d'":
          parts.append("d'" + p[2:3].upper() + p[3:])
        else:
          parts.append(p[:1].upper() + p[1:])
    return "-".join(parts)

  out = []
  for i, w in enumerate(tokens):
    if i > 0 and w in minusculas:
      out.append(w)
    else:
      out.append(cap_word(w))
  return " ".join(out)

def criarTabelaProducaoPorCaminhao(dfViagens: pd.DataFrame, styles, max_linhas: int = 34):
  """
  Gera elementos (list) prontos para inserir no doc ReportLab.
  Mostra: Caminhões | Nº Viagens | Total (t) | Peso Médio (t/viagem)
  """
  elementos = []
  df = dfViagens.copy()

  # Garante as colunas necessarias
  for col in ("time", "nome", "volume_descarregado", "desc_obra", "prefixo_veiculo"):
    if col not in df.columns:
      df[col] = "" if col != "volume_descarregado" else 0.0

  # Converte volume para numerico e preenche NaN com 0.0
  df["volume_descarregado"] = pd.to_numeric(df["volume_descarregado"], errors="coerce")

  # Preenche nulos textuais
  for col in ("nome", "desc_obra", "prefixo_veiculo"):
    if col in df.columns:
      df[col] = df[col].fillna("").astype(str)

  # Agrupamento por caminhao: nº de viagens, total e media por viagem
  df_agrupado = (
    df.groupby("prefixo_veiculo")
    .agg(
      n_viagens=("volume_descarregado", "count"),
      total_descarregado=("volume_descarregado", "sum"),
      peso_medio=("volume_descarregado", "mean"),
    )
    .reset_index()
  )

  # Se não existirem registros, retorna mensagem simples
  if df_agrupado.empty:
    elementos.append(Paragraph("Sem registros no período.", styles["Normal"]))
    return elementos

  # Ordena pelo total e formata numéricos
  df_agrupado = df_agrupado.sort_values("total_descarregado", ascending=False)
  df_agrupado["total_descarregado"] = df_agrupado["total_descarregado"].astype(float).round(2)
  df_agrupado["peso_medio"] = df_agrupado["peso_medio"].fillna(0.0).astype(float).round(2)

  # Formatar separador numerico (pt-BR)
  def fmt_num(v):
    try:
      v = float(v)
    except Exception:
      v = 0.0
    s = f"{v:,.2f}"  # ex: 1,234.56
    s = s.replace(",", "X").replace(".", ",").replace("X", ".")
    return s

  linhas = []
  cabeçalho = ["Caminhão", "N° de Viagens", "Total (t)", "Peso Médio (t/viagem)"]

  for _, r in df_agrupado.iterrows():
    linhas.append([
      str(r["prefixo_veiculo"]),
      str(int(r["n_viagens"])),
      fmt_num(r["total_descarregado"]),
      fmt_num(r["peso_medio"])
    ])

  # quebra em páginas (chunks) mantendo mesmo estilo visual
  FONT_HDR = FONT
  FONT_BODY = FONT
  HDR_COLOR = colors.HexColor("#666666")

  for i in range(0, len(linhas), max_linhas):
    chunk = linhas[i:i + max_linhas]
    data = [cabeçalho] + chunk

    tbl = Table(data, colWidths=[3 * cm, 2.5 * cm, 3 * cm, 4 * cm], repeatRows=1)

    tbl.setStyle(TableStyle([
      ("FONTNAME", (0, 0), (-1, 0), FONT_HDR),
      ("FONTSIZE", (0, 0), (-1, 0), 8),
      ("BACKGROUND", (0, 0), (-1, 0), COR_FUNDO),
      ("TEXTCOLOR", (0, 0), (-1, 0), HDR_COLOR),

      ("FONTNAME", (0, 1), (-1, -1), FONT_BODY),
      ("FONTSIZE", (0, 1), (-1, -1), 7),
      ("LINEBELOW", (0, 0), (-1, 0), 0.6, COR_GRID),
      ("LINEBELOW", (0, 1), (-1, -1), 0.25, COR_GRID),

      ("ALIGN", (0, 0), (0, -1), "CENTER"),
      ("ALIGN", (2, 0), (2, -1), "RIGHT"),
      ("ALIGN", (3, 0), (3, -1), "RIGHT"),  # corrigido aqui
      ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),

      ("ROWBACKGROUNDS", (0, 1), (-1, -1), [COR_FUNDO_SECUNDARIA, COR_FUNDO]),
      ("TOPPADDING", (0, 0), (-1, -1), 2),
      ("BOTTOMPADDING", (0, 0), (-1, -1), 1),
      ("GRID", (0, 0), (-1, -1), 0, colors.transparent),
    ]))

    # Cabeçalho da seção (primeira página vs continuação)
    if i == 0:
      elementos.append(Paragraph("Produção por caminhão", styles["Heading2"]))
      elementos.append(Spacer(1, 0.2 * cm))
    else:
      elementos.append(PageBreak())
      elementos.append(Paragraph("Produção por caminhão (continuação)", styles["Heading2"]))
      elementos.append(Spacer(1, 0.2 * cm))

    # Indenta a tabela como na outra função
    m = 1.0 * cm
    elementos.append(Indenter(left=m, right=m))
    elementos.append(tbl)
    elementos.append(Indenter(left=-m, right=-m))

  return elementos
