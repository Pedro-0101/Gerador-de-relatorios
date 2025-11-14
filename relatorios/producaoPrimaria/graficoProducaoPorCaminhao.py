import io
import pandas as pd
import matplotlib.pyplot as plt

from temas.tema_amarelo_dnp import (
  CORES_VIZ
)

def graficoProducaoCaminhao(dfViagens: pd.DataFrame) -> io.BytesIO:
  coluna_valor = "volume_descarregado"
  coluna_caminhao = "prefixo_veiculo"
  df = dfViagens.copy()

  # cria figura
  fig, ax = plt.subplots(figsize=(20, 11))

  # caso não tenha dados
  if df.empty:
    ax.text(0.5, 0.5, "Sem dados no período", ha="center", va="center", fontsize=20)
    ax.axis("off")

    buf = io.BytesIO()
    plt.tight_layout()
    plt.savefig(buf, format="PNG")
    plt.close(fig)
    buf.seek(0)
    return buf

  # garante tipos corretos
  df[coluna_valor] = pd.to_numeric(df[coluna_valor], errors="coerce").fillna(0)

  # agrega
  df_group = (
    df.groupby(coluna_caminhao)[coluna_valor]
    .sum()
    .reset_index()
    .sort_values(coluna_valor, ascending=False)
  )

  # plot
  ax.bar(df_group[coluna_caminhao], df_group[coluna_valor], color=CORES_VIZ)

  # labels
  ax.set_ylabel("Total descarregado (t)", fontsize=14, fontweight='bold')
  ax.set_title("Produção por Caminhão", fontsize=20, pad=20, fontweight='bold')

  # rotaciona o eixo X para não sobrepor
  plt.xticks(rotation=45, ha="right", fontsize=14)

  # salva
  buf = io.BytesIO()
  plt.tight_layout()
  plt.savefig(buf, format="PNG")
  plt.close(fig)
  buf.seek(0)
  return buf
  