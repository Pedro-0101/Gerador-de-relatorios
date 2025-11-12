import pandas as pd
from reportlab.lib.units import cm
from reportlab.lib import colors
from reportlab.platypus import Table, TableStyle
from reportlab.platypus import Table, TableStyle, Paragraph, Spacer, PageBreak, Indenter

from temas.tema_amarelo_dnp import (
  COR_FUNDO, COR_GRID, COR_FUNDO_SECUNDARIA
)
FONT = "Calibri"

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

def criarTabelaProducaoDiaria(dfViagens: pd.DataFrame, styles, max_linhas: int = 34):
  """
  Gera elementos (list) prontos para inserir no doc ReportLab,
  com o mesmo estilo visual da função criarTabelaGeral.
  Mostra: Data | Caminhões | Nº Viagens | Total (t) | Peso Médio (t/viagem)
  """
  elementos = []
  df = dfViagens.copy()

  # Garante colunas necessárias
  for col in ("time", "nome", "volume_descarregado", "desc_obra", "prefixo_veiculo"):
    if col not in df.columns:
      df[col] = "" if col != "volume_descarregado" else 0.0

  # Converte a coluna de tempo para datetime (mantém para cálculos)
  df["time"] = pd.to_datetime(df["time"], errors="coerce")

  # Preenche nulos textuais
  for col in ("nome", "desc_obra", "prefixo_veiculo"):
    if col in df.columns:
      df[col] = df[col].fillna("").astype(str)

  # Cria coluna 'data' apenas com date para agrupar por dia
  df["data"] = df["time"].dt.date
  
  # Função auxiliar para obter prefixos únicos na ordem de aparição
  def unique_join_preserve_order(s):
    validos = sorted({str(v).strip() for v in s if v and str(v).strip()})
    return ", ".join(validos)

  # Agrupamento por dia: nº de viagens, total e média por viagem
  df_agrupado = (
      df.groupby("data")
      .agg(
        n_viagens=("volume_descarregado", "count"),
        total_descarregado=("volume_descarregado", "sum"),
        peso_medio=("volume_descarregado", "mean"),
        prefixos=("prefixo_veiculo", lambda s: unique_join_preserve_order(s))
      )
      .reset_index()
    )

  # Se não existirem registros, retorna mensagem simples
  if df_agrupado.empty:
    elementos.append(Paragraph("Sem registros no período.", styles["Normal"]))
    return elementos

  # Formatação das colunas para exibição (pt-BR)
  df_agrupado["data_str"] = df_agrupado["data"].apply(lambda d: d.strftime("%d/%m/%Y"))
  df_agrupado["total_descarregado"] = df_agrupado["total_descarregado"].fillna(0.0).astype(float).round(2)
  df_agrupado["peso_medio"] = df_agrupado["peso_medio"].fillna(0.0).astype(float).round(2)

  def fmt_num(v):
    return f"{v:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

  # Monta linhas da tabela
  linhas = []
  cabeçalho = ["Data", "Caminhões", "Nº Viagens", "Total (t)", "Peso Médio (t/viagem)"]
  for _, r in df_agrupado.iterrows():
    linhas.append([
      r["data_str"],
      r["prefixos"] if r["prefixos"] else "-",            # coloca '-' se vazio
      f"{int(r['n_viagens'])}",
      fmt_num(r["total_descarregado"]),
      fmt_num(r["peso_medio"]),
    ])

  # quebra em páginas (chunks) mantendo mesmo estilo visual
  FONT_HDR = FONT 
  FONT_BODY = FONT
  HDR_COLOR = colors.HexColor("#666666")

  for i in range(0, len(linhas), max_linhas):
    chunk = linhas[i:i + max_linhas]
    data = [cabeçalho] + chunk

    # colWidths: Data | Caminhões | Nº Viagens | Total | Peso Médio
    tbl = Table(data, colWidths=[3.5 * cm, 5 * cm, 2.5 * cm, 3 * cm, 4 * cm])
    tbl.setStyle(TableStyle([
      ("FONT", (0, 0), (-1, 0), FONT_HDR, 9),
      ("BACKGROUND", (0, 0), (-1, 0), COR_FUNDO),
      ("TEXTCOLOR", (0, 0), (-1, 0), HDR_COLOR),

      ("FONT", (0, 1), (-1, -1), FONT_BODY, 8),
      ("LINEBELOW", (0, 0), (-1, 0), 0.6, COR_GRID),
      ("LINEBELOW", (0, 1), (-1, -1), 0.25, COR_GRID),

      ("ALIGN", (0, 0), (0, -1), "CENTER"),
      ("ALIGN", (2, 0), (-1, -1), "CENTER"),
      ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),

      ("ROWBACKGROUNDS", (0, 1), (-1, -1), [COR_FUNDO_SECUNDARIA, COR_FUNDO]),
      ("TOPPADDING", (0, 0), (-1, -1), 4),
      ("BOTTOMPADDING", (0, 0), (-1, -1), 5),

      ("REPEATROWS", (0, 0), (-1, 0)),
    ]))

    # Cabeçalho da seção (primeira página vs continuação)
    if i == 0:
      elementos.append(Paragraph("Produção Diária", styles["Heading2"]))
      elementos.append(Spacer(1, 0.2 * cm))
    else:
      elementos.append(PageBreak())
      elementos.append(Paragraph("Produção Diária (continuação)", styles["Heading2"]))
      elementos.append(Spacer(1, 0.2 * cm))

    # Indenta a tabela como na outra função
    m = 1.0 * cm
    elementos.append(Indenter(left=m, right=m))
    elementos.append(tbl)
    elementos.append(Indenter(left=-m, right=-m))

  return elementos
