"""Módulo obsoleto (mantido apenas como stub para compatibilidade).

Todas as funções de geração de PDF foram removidas. Não utilizar.
"""

def __getattr__(name):  # pragma: no cover
    raise AttributeError("PDF removido. Use exportações CSV/HTML.")
