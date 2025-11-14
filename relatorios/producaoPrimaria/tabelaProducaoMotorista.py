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

def criarTabelaProducaoPorMotorista(dfViagens: pd.DataFrame, styles, max_linhas: int = 34):
  """
  Gera elementos (list) prontos para inserir no doc ReportLab.
  Mostra: Motorista | Nº Viagens | Total (t) | Peso Médio (t/viagem)
  """
  
  elementos = []
  df = dfViagens.copy()

  # Garante as colunas necessárias
  for col in ("time", "nome", "volume_descarregado", "desc_obra", "prefixo_veiculo"):
    if col not in df.columns:
      df[col] = "" if col != "volume_descarregado" else 0.0

  # Converte volume para número
  df["volume_descarregado"] = pd.to_numeric(df["volume_descarregado"], errors="coerce")

  # Preenche textos
  df["nome"] = df["nome"].fillna("").astype(str)
  df["nome"] = df["nome"].apply(titlecase_pt)

  # Agrupa por motorista
  df_agrupado = (
    df.groupby("nome")
    .agg(
      n_viagens=("volume_descarregado", "count"),
      total_descarregado=("volume_descarregado", "sum"),
      peso_medio=("volume_descarregado", "mean"),
    )
    .reset_index()
  )
  
  # Se não existirem registros
  if df_agrupado.empty:
    elementos.append(Paragraph("Sem registros no período.", styles["Normal"]))
    return elementos

  # Ordena pelo total (maior → menor)
  df_agrupado = df_agrupado.sort_values("total_descarregado", ascending=False)

  # Formata números
  df_agrupado["total_descarregado"] = df_agrupado["total_descarregado"].astype(float).round(2)
  df_agrupado["peso_medio"] = df_agrupado["peso_medio"].fillna(0.0).astype(float).round(2)

  # Formato pt-BR
  def fmt_num(v):
    try:
      v = float(v)
    except:
      v = 0.0
    s = f"{v:,.2f}"
    return s.replace(",", "X").replace(".", ",").replace("X", ".")

  # Constrói as linhas
  linhas = []
  cabeçalho = ["Motorista", "N° de Viagens", "Total (t)", "Peso Médio (t/viagem)"]

  for _, r in df_agrupado.iterrows():
    linhas.append([
      titlecase_pt(r["nome"]),
      str(int(r["n_viagens"])),
      fmt_num(r["total_descarregado"]),
      fmt_num(r["peso_medio"])
    ])

  # Estilos
  FONT_HDR = FONT
  FONT_BODY = FONT
  HDR_COLOR = colors.HexColor("#666666")

  # Paginar
  for i in range(0, len(linhas), max_linhas):
    chunk = linhas[i:i + max_linhas]
    data = [cabeçalho] + chunk

    tbl = Table(
      data,
      colWidths=[8 * cm, 2.5 * cm, 3 * cm, 4 * cm],
      repeatRows=1
    )

    tbl.setStyle(TableStyle([
      ("FONTNAME", (0, 0), (-1, 0), FONT_HDR),
      ("FONTSIZE", (0, 0), (-1, 0), 9),
      ("BACKGROUND", (0, 0), (-1, 0), COR_FUNDO),
      ("TEXTCOLOR", (0, 0), (-1, 0), HDR_COLOR),

      ("FONTNAME", (0, 1), (-1, -1), FONT_BODY),
      ("FONTSIZE", (0, 1), (-1, -1), 7),
      ("LINEBELOW", (0, 0), (-1, 0), 0.6, COR_GRID),
      ("LINEBELOW", (0, 1), (-1, -1), 0.25, COR_GRID),

      ("ALIGN", (0, 0), (0, -1), "LEFT"),
      ("ALIGN", (2, 0), (2, -1), "RIGHT"),
      ("ALIGN", (3, 0), (3, -1), "RIGHT"),
      ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),

      ("ROWBACKGROUNDS", (0, 1), (-1, -1), [COR_FUNDO_SECUNDARIA, COR_FUNDO]),
      ("TOPPADDING", (0, 0), (-1, -1), 4),
      ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
      ("GRID", (0, 0), (-1, -1), 0, colors.transparent),
    ]))

    # Cabeçalho
    if i == 0:
      elementos.append(Paragraph("Produção por motorista", styles["Heading2"]))
      elementos.append(Spacer(1, 0.2 * cm))
    else:
      elementos.append(PageBreak())
      elementos.append(Paragraph("Produção por motorista (continuação)", styles["Heading2"]))
      elementos.append(Spacer(1, 0.2 * cm))

    m = 1.0 * cm
    elementos.append(Indenter(left=m, right=m))
    elementos.append(tbl)
    elementos.append(Indenter(left=-m, right=-m))

  return elementos
