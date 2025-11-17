import io
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib as mpl

from temas.tema_amarelo_dnp import (
  CORES_VIZ
)

def titlecase_pt(s: str) -> str:
  s = ("" if s is None else str(s)).strip().lower()
  if not s:
    return ""
  minusculas = {"da", "de", "do", "das", "dos", "e", "di", "du", "del", "van", "von", "d"}
  tokens = s.split()

  def cap_word(w: str) -> str:
    parts = []
    for p in w.split("-"):
      if p == "":
        parts.append(p)
      else:
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


def graficoProducaoMotorista(dfViagens: pd.DataFrame, max_chars: int = 25) -> io.BytesIO:
  """
  Retorna BytesIO com PNG do gráfico de produção agrupado por motorista.

  max_chars: comprimento máximo exibido por nome antes de truncar/quebrar.
  """
  coluna_valor = "volume_descarregado"
  coluna_motorista = "nome"
  df = dfViagens.copy()

  fig, ax = plt.subplots(figsize=(20, 11))

  # sem dados
  if df.empty:
    ax.text(0.5, 0.5, "Sem dados no período", ha="center", va="center", fontsize=20)
    ax.axis("off")
    buf = io.BytesIO()
    fig.savefig(buf, format="PNG", bbox_inches="tight")
    plt.close(fig)
    buf.seek(0)
    return buf

  # normaliza
  df[coluna_valor] = pd.to_numeric(df.get(coluna_valor, 0), errors="coerce").fillna(0)
  df[coluna_motorista] = df.get(coluna_motorista, "").fillna("").astype(str)

  # agrega por motorista
  df_group = (
    df.groupby(coluna_motorista)[coluna_valor]
    .sum()
    .reset_index()
    .sort_values(coluna_valor, ascending=False)
  )

  # aplica titlecase
  df_group[coluna_motorista] = df_group[coluna_motorista].apply(titlecase_pt)

  if df_group.empty:
    ax.text(0.5, 0.5, "Sem dados no período", ha="center", va="center", fontsize=20)
    ax.axis("off")
    buf = io.BytesIO()
    fig.savefig(buf, format="PNG", bbox_inches="tight")
    plt.close(fig)
    buf.seek(0)
    return buf

  df_group[coluna_motorista] = (
    df_group[coluna_motorista]
    .fillna("Não definido")
    .replace("", "Não definido")
    .astype(str)
    .apply(titlecase_pt)
  ) 

  nomes = df_group[coluna_motorista].tolist()
  valores = df_group[coluna_valor].astype(float).tolist()

  # evita nomes com comprimento exagerado — quebra em duas linhas ou trunca
  def shorten(name: str) -> str:
    if len(name) <= max_chars:
      return name
    # tenta quebrar por espaço perto do meio
    parts = name.split()
    if len(parts) > 1:
      # junta palavras até alcançar ~max_chars e o restante na 2ª linha
      cur = []
      rest = []
      for p in parts:
        if len(" ".join(cur + [p])) <= max_chars:
          cur.append(p)
        else:
          rest.append(p)
      return " ".join(cur) + "\n" + " ".join(rest)
    # senão trunca com reticências
    return name[: max_chars - 3] + "..."

  nomes_display = [shorten(n) for n in nomes]

  # cores: se CORES_VIZ curto, usa colormap contínuo
  n_barras = len(nomes)
  cores = CORES_VIZ
  if not isinstance(cores, (list, tuple)) or len(cores) < n_barras:
    # usa um cmap (viridis por padrão) para gerar n cores
    cmap = mpl.cm.get_cmap("viridis", n_barras)
    cores = [cmap(i) for i in range(n_barras)]

  # plot
  ax.bar(nomes_display, valores, color=cores)

  # labels e título
  ax.set_ylabel("Total descarregado (t)", fontsize=14, fontweight="bold")
  ax.set_title("Produção por Motorista", fontsize=20, pad=20, fontweight="bold")

  # ajusta ticks do x
  rot = 45
  fontsize_xt = 14
  if n_barras > 20:
    rot = 90
    fontsize_xt = 10
  plt.xticks(rotation=rot, ha="right", fontsize=fontsize_xt)

  # layout e salva
  buf = io.BytesIO()
  fig.savefig(buf, format="PNG", bbox_inches="tight")
  plt.close(fig)
  buf.seek(0)
  return buf
