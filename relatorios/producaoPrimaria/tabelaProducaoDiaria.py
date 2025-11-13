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


def criarTabelaProducaoDiaria(dfViagens: pd.DataFrame, styles, max_linhas: int = 34):
  """
  Gera elementos (list) prontos para inserir no doc ReportLab,
  com o mesmo estilo visual da função criarTabelaGeral.
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

  # Função auxiliar para obter prefixos únicos na ordem de aparição
  def unique_join_preserve_order(series):
    seen = {}
    res = []
    for v in series:
      s = str(v).strip()
      if s and s not in seen:
        seen[s] = True
        res.append(s)
    return ", ".join(res)

  # Agrupamento por dia: nº de viagens, total e média por viagem
  df_agrupado = (
      df.groupby("data", dropna=False)
      .agg(
        n_viagens=("volume_descarregado", "count"),
        total_descarregado=("volume_descarregado", "sum"),
        peso_medio=("volume_descarregado", "mean"),
        prefixos=("prefixo_veiculo", lambda s: unique_join_preserve_order(s))
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

  def fmt_num(v):
    try:
      v = float(v)
    except Exception:
      v = 0.0
    # Formata com separador pt-BR: "1.234,56"
    s = f"{v:,.2f}"  # ex: 1,234.56
    s = s.replace(",", "X").replace(".", ",").replace("X", ".")
    return s

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
    # repete a primeira linha como cabeçalho usando repeatRows argument
    tbl = Table(data, colWidths=[3.5 * cm, 5 * cm, 2.5 * cm, 3 * cm, 4 * cm], repeatRows=1)
    tbl.setStyle(TableStyle([
      ("FONTNAME", (0, 0), (-1, 0), FONT_HDR),
      ("FONTSIZE", (0, 0), (-1, 0), 9),
      ("BACKGROUND", (0, 0), (-1, 0), COR_FUNDO),
      ("TEXTCOLOR", (0, 0), (-1, 0), HDR_COLOR),

      ("FONTNAME", (0, 1), (-1, -1), FONT_BODY),
      ("FONTSIZE", (0, 1), (-1, -1), 7),
      ("LINEBELOW", (0, 0), (-1, 0), 0.6, COR_GRID),
      ("LINEBELOW", (0, 1), (-1, -1), 0.25, COR_GRID),

      ("ALIGN", (0, 0), (0, -1), "CENTER"),
      # números à direita (melhor legibilidade) - ajuste se preferir center
      ("ALIGN", (2, 0), (2, -1), "RIGHT"),
      ("ALIGN", (3, 0), (4, -1), "RIGHT"),
      ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),

      ("ROWBACKGROUNDS", (0, 1), (-1, -1), [COR_FUNDO_SECUNDARIA, COR_FUNDO]),
      ("TOPPADDING", (0, 0), (-1, -1), 4),
      ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
      ("GRID", (0, 0), (-1, -1), 0, colors.transparent),  # evita grid visível; ajuste se quiser linhas
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
