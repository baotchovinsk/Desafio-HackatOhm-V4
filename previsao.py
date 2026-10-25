"""Previsões opcionais para a safra futura. Cada uma usa o arquivo da pasta 'dados', se existir,
ou o valor digitado no app.

  precos_conab.csv      tendência do preço até o ano da colheita (ou crescimento digitado)
  mercado_futuro.csv    colunas: produto, vencimento (AAAA-MM), preco (R$/saca); ou cotação digitada
  previsao_sazonal.csv  coluna: prob_abaixo (0 a 1); ou chance digitada (chuva abaixo do normal, CPTEC/INPE)
"""
import numpy as np
import pandas as pd

def preco_tendencia(s, ano_alvo):
    """Reta no log do preço (série com índice de datas). Devolve (preço no ano-alvo, incerteza em log).
    A incerteza cresce com o tempo entre o último dado e a colheita."""
    s = s.dropna()
    s = s[s > 0]
    if len(s) < 24:
        return None
    t = np.asarray((s.index - s.index[0]).days, dtype=float) / 365.25
    y = np.log(s.values.astype(float))
    b, a = np.polyfit(t, y, 1)
    resid_sd = float(np.std(y - (a + b * t), ddof=2))
    t_alvo = (pd.Timestamp(year=ano_alvo, month=6, day=1) - s.index[0]).days / 365.25
    h = max(0.0, t_alvo - t[-1])
    return float(np.exp(a + b * t_alvo)), float(np.clip(resid_sd * np.sqrt(1 + h), .05, .8))


def preco_futuro(df, produto, ano_alvo):
    """Cotação mais recente do contrato com vencimento no ano da colheita. None se não houver."""
    if df is None or "vencimento" not in df:
        return None
    m = df[df["produto"].str.startswith(produto) & df["vencimento"].astype(str).str.startswith(str(ano_alvo))]
    v = m["preco"].dropna()
    return float(v.iloc[-1]) if len(v) else None


def preco_manual(preco, variacao):
    """Preço atual ajustado pela variação digitada até a colheita de 2027 (0.05 = +5%)."""
    return float(preco * (1 + variacao))


def fator_sazonal(df, manual=None):
    """Chance de chuva abaixo do normal dividida pela chance normal (1/3). 1.0 se não houver dado."""
    if df is not None and "prob_abaixo" in df and df["prob_abaixo"].notna().any():
        p = float(df["prob_abaixo"].dropna().iloc[0])
    elif manual:
        p = float(manual)
    else:
        return 1.0
    return float(np.clip(p * 3, .2, 3.0))
