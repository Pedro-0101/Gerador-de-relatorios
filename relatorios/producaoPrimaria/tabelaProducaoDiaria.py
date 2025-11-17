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
)

def criarTabelaProducaoDiaria(dfViagens: pd.DataFrame, styles, max_linhas: int = 34):
  """
  Gera elementos (list) prontos para inserir no doc ReportLab.
  Mostra: Data | Caminhões | Nº Viagens | Total (t) | Peso Médio (t/viagem)
  Melhorias:
  - converte volume_descarregado para numérico de forma segura
  - preserva ordem de prefixos (aparecimento) ao juntar
  - corrige uso de TableStyle (FONTNAME / FONTSIZE) e usa repeatRows
  - formatação numérica robusta
  """
  elementos = []
  df = dfViagens.copy()

  # Garante colunas necessárias
  for col in ("time", "nome", "volume_descarregado", "desc_obra", "prefixo_veiculo"):
    if col not in df.columns:
      df[col] = "" if col != "volume_descarregado" else 0.0

  # Converte a coluna de tempo para datetime (mantém para cálculos)
  df["time"] = pd.to_datetime(df["time"], errors="coerce")

  # Converte volume para numérico (caso venha como string) e preenche NaN com 0.0
  df["volume_descarregado"] = pd.to_numeric(df["volume_descarregado"], errors="coerce").fillna(0.0)

  # Preenche nulos textuais
  for col in ("nome", "desc_obra", "prefixo_veiculo"):
    if col in df.columns:
      df[col] = df[col].fillna("").astype(str)

  # Cria coluna 'data' apenas com date para agrupar por dia
  df["data"] = df["time"].dt.date

  # Função auxiliar para obter prefixos únicos na ordem alfabetica
  def unique_join_order(series):
    res = sorted({str(v).strip() for v in series if str(v).strip()}, key=str.lower)
    return ", ".join(res)

  # Agrupamento por dia: nº de viagens, total e média por viagem
  df_agrupado = (
    df.groupby("data", dropna=False)
    .agg(
      n_viagens=("volume_descarregado", "count"),
      total_descarregado=("volume_descarregado", "sum"),
      peso_medio=("volume_descarregado", "mean"),
      prefixos=("prefixo_veiculo", lambda s: unique_join_order(s)),
      hora_primeira_viagem=("time", "min"),
      hora_ultima_viagem=("time", "max"),
    )
    .reset_index()
  )
  


  # Remove linhas com data NaT (se quiser excluir registros sem data)
  df_agrupado = df_agrupado[df_agrupado["data"].notna()]

  # Se não existirem registros, retorna mensagem simples
  if df_agrupado.empty:
    elementos.append(Paragraph("Sem registros no período.", styles["Normal"]))
    return elementos

  # Formatação das colunas para exibição (pt-BR)
  df_agrupado["data_str"] = df_agrupado["data"].apply(lambda d: d.strftime("%d/%m/%Y"))
  df_agrupado["total_descarregado"] = df_agrupado["total_descarregado"].astype(float).round(2)
  df_agrupado["peso_medio"] = df_agrupado["peso_medio"].fillna(0.0).astype(float).round(2)
  df_agrupado["hora_primeira_viagem"] = df_agrupado["hora_primeira_viagem"].dt.strftime("%H:%M")
  df_agrupado["hora_ultima_viagem"]  = df_agrupado["hora_ultima_viagem"].dt.strftime("%H:%M")

  def fmt_num(v):
    try:
      v = float(v)
    except Exception:
      v = 0.0
    # Formata com separador pt-BR: "1.234,56"
    s = f"{v:,.2f}" 
    s = s.replace(",", "X").replace(".", ",").replace("X", ".")
    return s

  # Monta linhas da tabela
  linhas = []
  cabeçalho = ["Data", "Caminhões", "Nº Viagens", "Total (t)", "t/Viagen", "Primeira viagem", "Última viagem"]
  for _, r in df_agrupado.iterrows():
    linhas.append([
      r["data_str"],
      r["prefixos"] if r["prefixos"] else "-",            # coloca '-' se vazio
      f"{int(r['n_viagens'])}",
      fmt_num(r["total_descarregado"]),
      fmt_num(r["peso_medio"]),
      r["hora_primeira_viagem"],
      r["hora_ultima_viagem"],
    ])

  # quebra em páginas (chunks) mantendo mesmo estilo visual
  for i in range(0, len(linhas), max_linhas):
    chunk = linhas[i:i + max_linhas]
    data = [cabeçalho] + chunk

    # colWidths: Data | Caminhões | Nº Viagens | Total | Peso Médio | Primeira viagem | Ultima viagem
    # repete a primeira linha como cabeçalho usando repeatRows argument
    tbl = Table(data, colWidths=[2.5 * cm, 4 * cm, 2.5 * cm, 2 * cm, 2 * cm, 3 * cm, 3 * cm], repeatRows=1)
    tbl.setStyle(TableStyle([
      # Cabeçalho
      ("FONTNAME", (0, 0), (-1, 0), FONT_TABLE_HEADER),
      ("FONTSIZE", (0, 0), (-1, 0), FONTSIZE_HEADER_TABLE),
      ("BACKGROUND", (0, 0), (-1, 0), COR_FUNDO),
      ("TEXTCOLOR", (0, 0), (-1, 0), COR_BACKGROUND_HEADER),
      ("LINEBELOW", (0, 0), (-1, 0), LINE_BELLOW_HEADER, COR_GRID),
      ("ALIGN", (0, 0), (0, -1), "CENTER"),

      # Tabela completa
      ("FONTNAME", (0, 1), (-1, -1), FONT_TABLE_BODY),
      ("FONTSIZE", (0, 1), (-1, -1), FONTSIZE_CONTENT_TABLE),
      ("LINEBELOW", (0, 1), (-1, -1), LINE_BELLOW_HEADER_GRID, COR_GRID),
      ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
      ("ROWBACKGROUNDS", (0, 1), (-1, -1), [COR_FUNDO_SECUNDARIA, COR_FUNDO]),

      # Formatar colunas
      ("ALIGN", (2, 0), (2, -1), "RIGHT"),
      ("ALIGN", (3, 0), (3, -1), "RIGHT"),
      ("ALIGN", (4, 0), (4, -1), "RIGHT"),
      ("ALIGN", (5, 0), (5, -1), "CENTER"),
      ("ALIGN", (6, 0), (6, -1), "CENTER"),

      # Top e bottom
      ("TOPPADDING", (0, 0), (-1, -1), 2),
      ("BOTTOMPADDING", (0, 0), (-1, -1), 1),

      ("GRID", (0, 0), (-1, -1), 0, colors.transparent),
    ]))
    
    # período formatado
    ini = df["time"].min().strftime("%d/%m/%Y")
    fim = df["time"].max().strftime("%d/%m/%Y")

    # Cabeçalho da seção (primeira página vs continuação)
    if i == 0:
      elementos.append(Paragraph(f"Produção Diária: de {ini} a {fim}", styles["Heading2"]))
      elementos.append(Spacer(1, 0.2 * cm))
    else:
      elementos.append(PageBreak())
      elementos.append(Paragraph(f"Produção Diária (continuação): de {ini} a {fim}", styles["Heading2"]))
      elementos.append(Spacer(1, 0.2 * cm))

    # Indenta a tabela como na outra função
    m = 1.0 * cm
    elementos.append(Indenter(left=m, right=m))
    elementos.append(tbl)
    elementos.append(Indenter(left=-m, right=-m))

  return elementos
