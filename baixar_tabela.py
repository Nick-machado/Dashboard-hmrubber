import pandas as pd
import datetime
from functions.query import run_query as query
from functions.query import gerar_soma

df = query("2025-06-11", "2025-06-12", empresa_id=2, flag_tipo='V')

df.to_excel("Filial.xlsx", index=False)