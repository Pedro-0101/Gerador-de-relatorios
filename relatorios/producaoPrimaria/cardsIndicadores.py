# cards_indicadores.py
import math
import io
from typing import Optional, Dict, Any

import pandas as pd
from reportlab.platypus import Table, TableStyle, Paragraph, Spacer, Flowable
from reportlab.lib import colors
from reportlab.lib.units import cm
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet

# ---- helper: titlecase_pt (reaproveitado / compatível) ----
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


# ---- util: formatador pt-BR para números ----
def fmt_num_pt(v: float, decimals: int = 2) -> str:
  if v is None or (isinstance(v, float) and (math.isnan(v) or math.isinf(v))):
    return "0,00"
  fmt = f"{{:,.{decimals}f}}".format(v)
  return fmt.replace(",", "X").replace(".", ",").replace("X", ".")


# ---- função que cria um "card" colorido como Table ----
def _card_table(title: str, value: str, width: float = 6 * cm, height: float = 2.2 * cm,
              bgcolor: str = "#ff9913", title_style: Optional[ParagraphStyle] = None,
              value_style: Optional[ParagraphStyle] = None) -> Table:
  # cria Paragraphs
  if title_style is None:
    title_style = ParagraphStyle("card_title", fontSize=9, alignment=1, textColor=colors.white)
  if value_style is None:
    value_style = ParagraphStyle("card_value", fontSize=10, alignment=1, textColor=colors.white)

  data = [[Paragraph(f"<b>{title}</b>", title_style), Paragraph(f"<b>{value}</b>", value_style)]]
  tbl = Table(data, colWidths=[width * 0.6, width * 0.4], rowHeights=[height])
  tbl.setStyle(TableStyle([
    ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor(bgcolor)),
    ("BOX", (0, 0), (-1, -1), 0.8, colors.HexColor(bgcolor)),
    ("INNERGRID", (0, 0), (-1, -1), 0.2, colors.HexColor(bgcolor)),
    ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
    ("LEFTPADDING", (0, 0), (-1, -1), 6),
    ("RIGHTPADDING", (0, 0), (-1, -1), 6),
  ]))
  return tbl


# ---- cálculo dos KPIs a partir do DataFrame ----
def calcular_indicadores(df: pd.DataFrame) -> Dict[str, Any]:
    """
    Espera df com colunas: 'time' (datetime-like), 'volume_descarregado' (numérico),
    'prefixo_veiculo' (str) e 'nome' (motorista) — adapta quando colunas faltarem.
    """
    df = df.copy()
    # garante colunas
    for col in ("time", "volume_descarregado", "prefixo_veiculo", "nome"):
      if col not in df.columns:
        df[col] = None

    # converte time
    df["time"] = pd.to_datetime(df["time"], errors="coerce")
    df["volume_descarregado"] = pd.to_numeric(df["volume_descarregado"], errors="coerce").fillna(0.0)

    # producao total no período
    producao_total = float(df["volume_descarregado"].sum())

    # numero total de viagens (contagem de registros onde volume > 0)
    num_viagens = int(df.shape[0])

    # caminhão mais produtivo (por soma de volume)
    if df["prefixo_veiculo"].notna().any():
      cam_prod = (
        df.groupby("prefixo_veiculo")["volume_descarregado"]
          .sum()
          .sort_values(ascending=False)
      )
      caminhao_mais_prod = cam_prod.index[0] if not cam_prod.empty else ""
    else:
      caminhao_mais_prod = ""

    # motorista mais produtivo
    if df["nome"].notna().any():
      mot_prod = (
        df.groupby("nome")["volume_descarregado"]
        .sum()
        .sort_values(ascending=False)
      )
      motorista_mais_prod = mot_prod.index[0] if not mot_prod.empty else ""
    else:
      motorista_mais_prod = ""

    # produção média por dia (considera dias com pelo menos um registro)
    df["data"] = df["time"].dt.date
    dias_ativos = df["data"].nunique()
    producao_media_dia = (producao_total / dias_ativos) if dias_ativos > 0 else 0.0

    # dia com maior e menor produção (menor > 0)
    agrup_dias = df.groupby("data")["volume_descarregado"].sum().dropna()
    dia_mais = None
    dia_menos = None
    if not agrup_dias.empty:
      dia_mais = agrup_dias.idxmax()
      # menor produção não-zero:
      agrup_pos = agrup_dias[agrup_dias > 0]
      if not agrup_pos.empty:
        dia_menos = agrup_pos.idxmin()
      else:
        dia_menos = None

    # normaliza strings com titlecase_pt (aplica se não vazio)
    caminhao_mais_prod = titlecase_pt(caminhao_mais_prod) if caminhao_mais_prod else ""
    motorista_mais_prod = titlecase_pt(motorista_mais_prod) if motorista_mais_prod else ""

    return dict(
      producao_total=producao_total,
      num_viagens=num_viagens,
      caminhao_mais_prod=caminhao_mais_prod,
      motorista_mais_prod=motorista_mais_prod,
      producao_media_dia=producao_media_dia,
      dia_mais=dia_mais,
      dia_menos=dia_menos,
      dias_ativos=dias_ativos
    )


# ---- função pública que monta os cards (retorna lista de Flowables) ----
def criar_cards_indicadores(df: pd.DataFrame, styles: Optional[Dict[str, ParagraphStyle]] = None,
                          tema: Optional[Dict[str, str]] = None):
  """
  df: DataFrame com dados
  styles: dicionário de ParagraphStyle (ex: styles do seu documento) ou None para defaults
  tema: dicionário opcional com cores (hex) para os cards. Ex:
    {
      "bg_card1": "#ff8c00",
      "bg_card2": "#007bff",
      "bg_card3": "#28a745",
      "bg_card4": "#6f42c1",
      "bg_card5": "#17a2b8",
      "bg_card6": "#e83e8c",
    }
  Retorna: lista de Flowable (Paragraph, Spacer, Table...) para inserir no Story.
  """
  if styles is None:
      styles = getSampleStyleSheet()

  # tema padrão (cores)
  tema_padrao = {
    "bg_card1": "#003f5c",
    "bg_card2": "#2f4b7c",
    "bg_card3": "#ff7c43",
    "bg_card4": "#28a745",
    "bg_card5": "#f95d6a",
    "bg_card6": "#6f42c1",
  }
  if tema:
    tema_padrao.update(tema)

  ind = calcular_indicadores(df)

  # prepara textos
  producao_total_txt = fmt_num_pt(ind["producao_total"], 2)
  num_viagens_txt = f"{ind['num_viagens']}"
  caminhao_txt = ind["caminhao_mais_prod"] or "-"
  motorista_txt = ind["motorista_mais_prod"] or "-"
  media_dia_txt = fmt_num_pt(ind["producao_media_dia"], 2)
  dia_mais_txt = ind["dia_mais"].strftime("%d/%m/%Y") if ind["dia_mais"] is not None else "-"
  dia_menos_txt = ind["dia_menos"].strftime("%d/%m/%Y") if ind["dia_menos"] is not None else "-"

  # cria cards
  elementos = []
  elementos.append(Paragraph("Principais Indicadores", styles["Heading2"]))
  elementos.append(Spacer(1, 0.2 * cm))

  # criamos 6 cards (2 linhas x 3 colunas preferencialmente)
  c1 = _card_table("Produção total do período (t)", producao_total_txt, bgcolor=tema_padrao["bg_card1"])
  c2 = _card_table("Número total de viagens", num_viagens_txt, bgcolor=tema_padrao["bg_card2"])
  c3 = _card_table("Caminhão mais produtivo", caminhao_txt, bgcolor=tema_padrao["bg_card3"])
  c4 = _card_table("Motorista mais produtivo", motorista_txt, bgcolor=tema_padrao["bg_card4"])
  c5 = _card_table("Produção média por dia (t)", media_dia_txt, bgcolor=tema_padrao["bg_card5"])
  c6 = _card_table("Maior / Menor dia (não zero)", f"{dia_mais_txt}\n{dia_menos_txt}", bgcolor=tema_padrao["bg_card6"])

  # organiza em tabela 3x2 (cada célula é um card Table)
  linha1 = [c1, c2, c3]
  linha2 = [c4, c5, c6]

  tabela_cards = Table([linha1, linha2], colWidths=[6.4 * cm, 6.4 * cm, 6.4 * cm], hAlign="LEFT")
  tabela_cards.setStyle(TableStyle([("LEFTPADDING", (0, 0), (-1, -1), 0),
                                    ("RIGHTPADDING", (0, 0), (-1, -1), 0),
                                    ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
                                    ("TOPPADDING", (0, 0), (-1, -1), 6)]))

  elementos.append(tabela_cards)
  elementos.append(Spacer(1, 0.4 * cm))
  return elementos


# ----------------- teste rápido -----------------
if __name__ == "__main__":
  # gera dados fictícios
  rng = pd.date_range("2025-10-01 06:00", periods=40, freq="8H")
  exemplo = pd.DataFrame({
    "time": rng,
    "nome": pd.np.random.choice(["joao", "carlos", "maria", "ana"], size=len(rng)),
    "volume_descarregado": pd.np.random.randint(18, 36, size=len(rng)),
    "prefixo_veiculo": pd.np.random.choice(["TRK-100", "TRK-200", "TRK-300"], size=len(rng))
  })

  # cria styles mínimos
  st = getSampleStyleSheet()
  elems = criar_cards_indicadores(exemplo, styles=st)
  # Para testar visualmente salve em PDF: comentar se for apenas importado
  from reportlab.platypus import SimpleDocTemplate
  doc = SimpleDocTemplate("teste_cards.pdf", leftMargin=2 * cm, rightMargin=2 * cm, topMargin=2 * cm, bottomMargin=2 * cm)
  doc.build(elems)
  print("PDF teste_cards.pdf gerado.")
