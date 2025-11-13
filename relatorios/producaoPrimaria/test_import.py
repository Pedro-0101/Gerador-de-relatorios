import importlib
try:
    m = importlib.import_module("relatorios.producaoPrimaria.cardsIndicadores")
    print("Import OK — funções disponíveis:", [n for n in dir(m) if n.startswith("criar") or n.startswith("calcular")])
except Exception as e:
    import traceback
    traceback.print_exc()