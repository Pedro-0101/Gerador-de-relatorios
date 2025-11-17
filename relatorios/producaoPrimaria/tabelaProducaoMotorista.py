import pandas as pd
from reportlab.lib.units import cm
from reportlab.lib import colors
from reportlab.platypus import Table, TableStyle, Paragraph, Spacer, PageBreak, Indenter
from utils.primeiraLetraMaiuscula import titlecase_pt

from temas.tema_amarelo_dnp import (
  COR_FUNDO, COR_GRID, 
  COR_FUNDO_SECUNDARIA, 
  FONTSIZE_HEADER_TABLE, 
  FONTSIZE_CONTENT_TABLE, 
  LINE_BELLOW_HEADER, 
  LINE_BELLOW_HEADER_GRID,
  FONT_TABLE_HEADER,
  FONT_TABLE_BODY,
  COR_BACKGROUND_HEADER,
  TOP_PADDING_TABLE,
  BOTTOM_PADDING_TABLE,
)

def criarTabelaProducaoPorMotorista(dfViagens: pd.DataFrame, styles, max_linhas: int = 34):
  """
  Gera elementos (list) prontos para inserir no doc ReportLab.
  Mostra: Motorista | Nº Viagens | Total (t) | Peso Médio (t/viagem) | Média (t/dia)
  """
  elementos = []
  df = dfViagens.copy()

  # Garante as colunas necessárias
  for col in ("time", "nome", "volume_descarregado", "desc_obra", "prefixo_veiculo"):
    if col not in df.columns:
      df[col] = "" if col != "volume_descarregado" else 0.0

  # Converte volume para número
  df["volume_descarregado"] = pd.to_numeric(df["volume_descarregado"], errors="coerce")

  # Converte tempo para datetime (para conseguir extrair dia)
  df["time"] = pd.to_datetime(df["time"], errors="coerce")
    
  df["nome"] = df["nome"].fillna("não definido").astype(str)
  df["nome"] = df["nome"].replace("", "não definido")
  df["nome"] = df["nome"].apply(titlecase_pt)

  # Agrupa por motorista (viagens, total e peso médio)
  df_agrupado = (
    df.groupby("nome")
    .agg(
      n_viagens=("volume_descarregado", "count"),   # se quiser contar TODAS as linhas, use "size"
      total_descarregado=("volume_descarregado", "sum"),
      peso_medio=("volume_descarregado", "mean"),
    )
    .reset_index()
  )

  # Calcula quantidade de dias com produção (>0) por motorista
  df_valid = df[df["volume_descarregado"] > 0].copy()
  df_valid["dia"] = df_valid["time"].dt.date

  df_dias = (
    df_valid.groupby("nome")["dia"]
    .nunique()
    .reset_index(name="dias_com_producao")
  )

  # Junta dias_com_producao à tabela agrupada
  df_agrupado = df_agrupado.merge(df_dias, on="nome", how="left")
  df_agrupado["dias_com_producao"] = df_agrupado["dias_com_producao"].fillna(0).astype(int)

  # Se não existirem registros
  if df_agrupado.empty:
    elementos.append(Paragraph("Sem registros no período.", styles["Normal"]))
    return elementos

  # Ordena pelo total (maior → menor)
  df_agrupado = df_agrupado.sort_values("total_descarregado", ascending=False)

  # Formata números e calcula média por dia
  df_agrupado["total_descarregado"] = df_agrupado["total_descarregado"].astype(float).round(2)
  df_agrupado["peso_medio"] = df_agrupado["peso_medio"].fillna(0.0).astype(float).round(2)

  # média por dia: total / dias_com_producao (quando dias > 0)
  df_agrupado["media_por_dia"] = 0.0
  mask_dias = df_agrupado["dias_com_producao"] > 0
  df_agrupado.loc[mask_dias, "media_por_dia"] = (
    df_agrupado.loc[mask_dias, "total_descarregado"]
    / df_agrupado.loc[mask_dias, "dias_com_producao"]
  )
  df_agrupado["media_por_dia"] = df_agrupado["media_por_dia"].round(2)

  # Formato pt-BR
  def fmt_num(v):
    try:
      v = float(v)
    except Exception:
      v = 0.0
    s = f"{v:,.2f}"
    return s.replace(",", "X").replace(".", ",").replace("X", ".")

  # Constrói as linhas
  linhas = []
  cabeçalho = [
    "Motorista",
    "N° de Viagens",
    "Total (t)",
    "Peso Médio (t/viagem)",
    "Média (t/dia)",
  ]

  for _, r in df_agrupado.iterrows():
    # Só mostra média por dia quando não for 0 (senão, string vazia)
    media_dia_str = fmt_num(r["media_por_dia"]) if r["media_por_dia"] > 0 else ""

    linhas.append([
      r["nome"],  # já está em titlecase
      str(int(r["n_viagens"])),
      fmt_num(r["total_descarregado"]),
      fmt_num(r["peso_medio"]),
      media_dia_str,
    ])

  # Paginar
  for i in range(0, len(linhas), max_linhas):
    chunk = linhas[i:i + max_linhas]
    data = [cabeçalho] + chunk

    tbl = Table(
      data,
      colWidths=[7 * cm, 2.5 * cm, 3 * cm, 3.5 * cm, 3 * cm],
      repeatRows=1
    )

    tbl.setStyle(TableStyle([
      # Cabeçalho
      ("FONTNAME", (0, 0), (-1, 0), FONT_TABLE_HEADER),
      ("FONTSIZE", (0, 0), (-1, 0), FONTSIZE_HEADER_TABLE),
      ("BACKGROUND", (0, 0), (-1, 0), COR_FUNDO),
      ("TEXTCOLOR", (0, 0), (-1, 0), COR_BACKGROUND_HEADER),

      # Corpo
      ("FONTNAME", (0, 1), (-1, -1), FONT_TABLE_BODY),
      ("FONTSIZE", (0, 1), (-1, -1), FONTSIZE_CONTENT_TABLE),

      # Linhas
      ("LINEBELOW", (0, 0), (-1, 0), LINE_BELLOW_HEADER, COR_GRID),
      ("LINEBELOW", (0, 1), (-1, -1), LINE_BELLOW_HEADER_GRID, COR_GRID),

      # Alinhamentos
      ("ALIGN", (0, 0), (0, -1), "LEFT"),
      ("ALIGN", (2, 0), (2, -1), "RIGHT"),
      ("ALIGN", (3, 0), (3, -1), "RIGHT"),
      ("ALIGN", (4, 0), (4, -1), "RIGHT"),
      ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),

      # Zebra
      ("ROWBACKGROUNDS", (0, 1), (-1, -1), [COR_FUNDO_SECUNDARIA, COR_FUNDO]),

      # Espaçamentos
      ("TOPPADDING", (0, 0), (-1, -1), TOP_PADDING_TABLE),
      ("BOTTOMPADDING", (0, 0), (-1, -1), BOTTOM_PADDING_TABLE),

      # Remove grid
      ("GRID", (0, 0), (-1, -1), 0, colors.transparent),
    ]))
    
    # período formatado
    ini = df["time"].min().strftime("%d/%m/%Y")
    fim = df["time"].max().strftime("%d/%m/%Y")

    # Cabeçalho
    if i == 0:
      elementos.append(Paragraph(f"Produção por motorista: de {ini} a {fim}", styles["Heading2"]))
      elementos.append(Spacer(1, 0.2 * cm))
    else:
      elementos.append(PageBreak())
      elementos.append(Paragraph(f"Produção por motorista (continuação): de {ini} a {fim}", styles["Heading2"]))
      elementos.append(Spacer(1, 0.2 * cm))

    m = 1.0 * cm
    elementos.append(Indenter(left=m, right=m))
    elementos.append(tbl)
    elementos.append(Indenter(left=-m, right=-m))

  return elementos
