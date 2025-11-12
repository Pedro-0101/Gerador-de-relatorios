import io
import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.colors import to_rgba
from matplotlib.patches import Polygon as MplPolygon

def graficoLinhaProducaoDiaria(dfViagens: pd.DataFrame) -> io.BytesIO:
    print('Gerando gráfico com gradiente Spectral invertido')

    coluna_data = "time"
    coluna_valor = "volume_descarregado"
    df = dfViagens.copy()
    
    # limpeza de dados
    df[coluna_data] = pd.to_datetime(df[coluna_data], errors="coerce")
    df[coluna_valor] = pd.to_numeric(df[coluna_valor], errors="coerce").fillna(0)
    df = df.dropna(subset=[coluna_data])
    
    fig, ax = plt.subplots(figsize=(20, 11))
    if df.empty:
        ax.text(0.5, 0.5, "Sem dados no período", ha="center", va="center", fontsize=16)
        ax.axis("off")
        buf = io.BytesIO()
        plt.tight_layout()
        plt.savefig(buf, format="PNG")
        plt.close(fig)
        buf.seek(0)
        return buf
    
    # agrupa por dia e soma o volume
    df_diario = (
        df.groupby(df[coluna_data].dt.date)[coluna_valor]
        .sum()
        .reset_index()
        .sort_values(coluna_data)
    )
    
    # período formatado
    ini = df_diario[coluna_data].min().strftime("%d/%m/%Y")
    fim = df_diario[coluna_data].max().strftime("%d/%m/%Y")
    
    # dados
    x = np.arange(len(df_diario))
    y = df_diario[coluna_valor].to_numpy()

    ymin, ymax = 0, max(y) * 1.05
    xmin, xmax = -0.5, len(x) - 0.5

    # usa colormap invertido (Spectral_r)
    cmap = plt.get_cmap("Blues_r")

    # cria gradiente invertido (de cima para baixo)
    gradient = np.linspace(1, 0, 256).reshape(-1, 1)
    img = ax.imshow(
        gradient,
        extent=[xmin, xmax, ymin, ymax],
        origin='lower',
        aspect='auto',
        cmap=cmap,
        alpha=1.0,
        zorder=1
    )

    # cria o polígono da área sob a curva
    verts = np.vstack([
        np.column_stack([x, y]),
        [x[-1], ymin],
        [x[0], ymin]
    ])
    poly = MplPolygon(verts, closed=True, transform=ax.transData)

    # aplica o recorte (clip)
    img.set_clip_path(poly)

    # camada de contraste suave
    ax.fill_between(x, y, color=to_rgba("#000000", 0.08), zorder=2)

    # linha e pontos sobre o gradiente
    ax.plot(
        x, y,
        '-o',
        color="#333333",
        linewidth=2,
        markersize=8,
        markerfacecolor="#ffffff",
        markeredgecolor="#333333",
        zorder=3
    )

    # adiciona valores sobre os pontos
    for xi, yi in zip(x, y):
        ax.text(
            xi, yi + (yi * 0.025),
            f"{yi:,.0f}",
            ha="center", va="bottom",
            fontsize=10, color="#222", weight="bold", zorder=4
        )

    # títulos e eixos
    ax.set_title(f"Produção diária: de {ini} a {fim}", fontsize=20, pad=20)
    ax.set_xlabel("Data", fontsize=14)
    ax.set_ylabel("Volume descarregado (t)", fontsize=14)

    # formata eixo X
    ax.set_xticks(x)
    ax.set_xticklabels(df_diario[coluna_data].astype(str), rotation=45, ha="right")
    ax.set_xlim(xmin, xmax)
    ax.set_ylim(ymin, ymax)

    plt.tight_layout()
    buf = io.BytesIO()
    plt.savefig(buf, format="PNG", dpi=120)
    plt.close(fig)
    buf.seek(0)
    return buf
