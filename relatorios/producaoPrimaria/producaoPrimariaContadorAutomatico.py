import argparse
import sys
from pathlib import Path
from datetime import datetime, timedelta
from typing import Optional

# Adiciona o diretório raiz do projeto ao sys.path
# Isso garante que o módulo 'db' seja encontrado independentemente de onde o script é executado
project_root = Path(__file__).resolve().parent.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from db import load_dataframe
from .criarPdfRelatorio import criarPdf

FMT = "%Y-%m-%d %H:%M:%S"


def parse_dt(value: Optional[str], *, default: Optional[datetime] = None) -> datetime:
    if value:
        return datetime.strptime(value, FMT)
    if default is not None:
        return default
    raise ValueError("Data inválida: forneça no formato YYYY-MM-DD HH:MM:SS")


def main():
    parser = argparse.ArgumentParser(
        description="Gerar relatório de produção primária",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument("--ini", help='Data inicial (ex: "2025-08-01 00:00:00")')
    parser.add_argument("--fim", help='Data final (ex: "2025-08-28 23:59:59")')
    parser.add_argument("--obra", type=int, help="Código da obra (ex: 41)")
    parser.add_argument("--ajuda", action="store_true", help="Mostrar exemplos de uso")
    parser.add_argument("--out", help='Caminho para o arquivo de saída (ex: "relatorio.pdf")')
    args = parser.parse_args()

    if args.ajuda:
        print("Comandos úteis para gerar relatório")
        print('--ini: Data inicial (ex: "2025-09-01 00:00:00")')
        print('--fim: Data final (ex: "2025-09-30 23:59:59")')
        print("--obra: Código da obra (ex: 41)")
        print("--out: Caminho para o arquivo de saída (ex: \"relatorio.pdf\")")
        print(
            'Exemplo: python -m relatorios.producaoPrimaria.producaoPrimariaContadorAutomatico --ini "2025-09-01 00:00:00" --fim "2025-09-30 23:59:59" --obra 41 --out "./relatorio_producao.pdf"'
        )
        return

    if args.obra is None:
        parser.error("o argumento --obra é obrigatório (use --ajuda para exemplos)")

    # Defaults para mês corrente
    now = datetime.now()
    start_default = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    next_month = (start_default.replace(day=28) + timedelta(days=4)).replace(day=1)
    end_default = next_month - timedelta(seconds=1)

    data_inicio = parse_dt(args.ini, default=start_default)
    data_final = parse_dt(args.fim, default=end_default)

    # Nome da obra
    df_nome_obra = load_dataframe(
        "SELECT desc_obra FROM ossj_cad_obra WHERE id = :obra",
        params={"obra": args.obra},
    )
    nome_obra = df_nome_obra["desc_obra"].iloc[0] if not df_nome_obra.empty else f"Obra {args.obra}"

    query_sql = """
                SELECT cp.`time`,
                       v.prefixo_veiculo,
                       f.nome,
                       cp.volume_descarregado,
                       o.desc_obra
                FROM ossj_contador_primario AS cp
                         JOIN ossj_veiculo_sensor_rfid AS v
                              ON cp.user_id_device = v.user_id_sensor
                         JOIN ossj_sensor_rfid AS sr
                              ON sr.device_id = cp.device_id
                         JOIN ossj_cad_obra AS o
                              ON o.id = sr.local_instalacao
                         LEFT JOIN ossj_motoristas_rocha AS mr
                                   ON mr.id = cp.motorista
                         LEFT JOIN ossj_cad_func AS f
                                   ON f.id = mr.id_motorista
                WHERE cp.codigo_planta = :obra
                  AND cp.`time` BETWEEN :ini AND :fim
                ORDER BY cp.`time` \
                """

    df = load_dataframe(
        query_sql,
        params={"ini": data_inicio, "fim": data_final, "obra": args.obra},
    )

    print(f"Relatório: {nome_obra} | Período: {data_inicio.strftime(FMT)} a {data_final.strftime(FMT)}")

    criarPdf(df, data_inicio, data_final, nome_obra, args.out)


if __name__ == "__main__":
    main()
