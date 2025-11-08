import io
import pandas as pd
import matplotlib.pyplot as plt

def graficoProducaoDiariaPorCaminhao(df: pd.DataFrame) -> io.BytesIO:
    coluna_data = "time"
    coluna_valor = "volume_descarregado"
    coluna_grupo = "prefixo_veiculo"

    df_tmp = df.copy()
    df_tmp[coluna_data] = pd.to_datetime(df_tmp[coluna_data], errors="coerce")
    df_tmp[coluna_valor] = pd.to_numeric(df_tmp[coluna_valor], errors="coerce").fillna(0)
    df_tmp = df_tmp.dropna(subset=[coluna_data])

    # se ficou vazio, devolve imagem “sem dados”
    fig, ax = plt.subplots(figsize=(20, 11))
    if df_tmp.empty:
        ax.text(0.5, 0.5, "Sem dados no período", ha="center", va="center", fontsize=16)
        ax.axis("off")
        buf = io.BytesIO()
        plt.tight_layout()
        plt.savefig(buf, format="PNG")
        plt.close(fig)
        buf.seek(0)
        return buf

    # agrega por dia + caminhão
    grup = (
        df_tmp
        .assign(__date=df_tmp[coluna_data].dt.date)
        .groupby(["__date", coluna_grupo], as_index=False)[coluna_valor].sum()
        .rename(columns={"__date": coluna_data})
    )

    piv = (
        grup
        .assign(**{coluna_data: pd.to_datetime(grup[coluna_data])})
        .pivot_table(index=coluna_data, columns=coluna_grupo, values=coluna_valor, fill_value=0)
        .sort_index()
    )

    labels = piv.index.strftime("%d/%m (%a)")

    # período formatado
    ini = df_tmp[coluna_data].min().strftime("%d/%m/%Y")
    fim = df_tmp[coluna_data].max().strftime("%d/%m/%Y")

    # redesenha o gráfico (reaproveita fig/ax já criado)
    ax.clear()
    
    cores1 = ["#003f5c", "#2f4b7c", "#665191", "#a05195", "#d45087", "#f95d6a", "#ff7c43", "#ffa600"]
    cores2 = ["#003f5b", "#002477", "#3d038e", "#8007a1", "#b70b8a", "#cf0f54", "#e7480e", "#ff9913"]
    cores3 = ["#003f5b", "#01616f", "#02847b", "#059c6b", "#4fb409", "#c3cc0c", "#e6b40f", "#ff9913"]

    if piv.empty:
        ax.text(0.5, 0.5, "Sem dados no período", ha="center", va="center", fontsize=16)
        ax.axis("off")
    else:
        bottom = None
        for i, col in enumerate(piv.columns):
            valores = piv[col].values
            cor = cores1[i % len(cores1)]
            ax.bar(labels, valores, bottom=bottom, label=str(col), color=cor)
            bottom = valores if bottom is None else (bottom + valores)

        # totais por dia (rótulo no topo da pilha)
        totais = piv.sum(axis=1).values
        for i, total in enumerate(totais):
            ax.text(i, total, f"{total:.0f}t", ha="center", va="bottom", fontsize=12, fontweight="light")

        # títulos/eixos
        ax.set_title(f"Produção por dia (empilhado por caminhão): de {ini} a {fim}", fontsize=20)
        ax.set_xlabel("Data", fontsize=14)
        ax.set_ylabel("Volume descarregado (t)", fontsize=14)

        # legenda adaptativa (  máx. 6 colunas)
        ncols = max(1, min(len(piv.columns), 6))
        ax.legend(
            title="Caminhão",
            fontsize=12,
            title_fontsize=13,
            ncol=ncols,
            frameon=False,
            loc="upper center",
            bbox_to_anchor=(0.5, -0.12)
        )

        ax.grid(True, axis="y", linestyle="--", alpha=0.7)
        plt.xticks(rotation=45, ha="right")

        # dá um respiro pra legenda e rótulos
        fig.subplots_adjust(bottom=0.25, top=0.88)

    buf = io.BytesIO()
    plt.tight_layout()
    plt.savefig(buf, format="PNG")
    plt.close(fig)
    buf.seek(0)
    return buf
