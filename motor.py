"""
Motor de decisão: qual cultura e nível de insumo escolher para uma área no Cerrado.

Cada alternativa (cultura x manejo) é simulada milhares de vezes com preço, produtividade
e clima incertos. O produtor vê uma distribuição de resultados, não um número único:
o resultado esperado, o pior 10% dos anos e a chance de prejuízo.

Premissas marcadas com (P) são estimativas. Calibre com Conab, Embrapa e ZARC.

Arquivos opcionais na pasta "dados" (sem eles, o motor usa premissas):
  precos_conab.csv  colunas: produto, data, preco             (R$/saca, ponto decimal)
  zarc.csv          colunas: codigo_ibge, cultura, risco_pct  (risco da época, em %)
  chuva.csv         colunas: data, precipitacao_mm            (ex.: estação do INMET/BDMEP)
"""
import os

import numpy as np
import pandas as pd

import previsao

AREA_REF = 100   # (P) área de referência do custo fixo (ha)
BETA = 0.4       # (P) economia de escala: custo fixo/ha = fixo * (AREA_REF / área) ** BETA
JUROS = 0.125    # (P) custo do capital ao ano: Plano Safra 2026/27, custeio de 8% a 12,5% a.a. conforme a linha (usado 12,5%; confirmar a linha)

# Produtividade média estadual (sacas/ha), safra 2026/27, estimativa Conab (out/2026).
# Chave = dois primeiros dígitos do código IBGE da UF. Substitui o SIDRA/PAM municipal.
PROD_UF = {
    "31": {"Soja": 64.4, "Milho verão": 117.5, "Milho safrinha": 93.8, "Sorgo": 61.9, "Feijão": 26.5},  # MG
    "52": {"Soja": 65.1, "Milho verão": 175.0, "Milho safrinha": 96.2, "Sorgo": 63.2, "Feijão": 41.0},  # GO
    "51": {"Soja": 64.8, "Milho verão": 144.2, "Milho safrinha": 120.4, "Sorgo": 60.5, "Feijão": 25.6},  # MT
    "29": {"Soja": 67.8, "Milho verão": 80.9, "Milho safrinha": 56.0, "Sorgo": 55.5, "Feijão": 11.2},  # BA
}
CV = 0.10        # (P) variação aleatória da produtividade
P_ADV = 0.25     # (P) chance de ano adverso quando não há dados de clima

# ideal: plantio ideal (mês, dia) | ciclo: dias | meses: duração do ciclo (para os juros)
# coe: custo variável R$/ha | fixo: custo fixo R$/ha na área de referência
# preco: R$/saca | prod: sc/ha | sigma: volatilidade do preço (log)
# perda: queda de produtividade em ano adverso | perda_sem: queda por semana de atraso
# chuva: mm mínimos no ciclo | sidra: código do produto na tabela 1712 do IBGE (confirme)
CULTURAS = {
    "Soja": dict(ideal=(10, 15), ciclo=120, meses=4, coe=3600, fixo=350, preco=125, prod=58,
                 sigma=.15, perda=(.25, .50), perda_sem=.02, chuva=450, sidra="2713"),
    "Milho verão": dict(ideal=(10, 15), ciclo=130, meses=5, coe=4600, fixo=400, preco=60, prod=120,
                        sigma=.18, perda=(.30, .60), perda_sem=.025, chuva=500, sidra="2711"),
    "Milho safrinha": dict(ideal=(1, 20), ciclo=110, meses=4, coe=3400, fixo=400, preco=60, prod=95,
                           sigma=.18, perda=(.30, .60), perda_sem=.03, chuva=350, sidra="2711"),
    "Sorgo": dict(ideal=(11, 1), ciclo=120, meses=4, coe=2300, fixo=300, preco=45, prod=70,
                  sigma=.20, perda=(.15, .40), perda_sem=.015, chuva=300, sidra="2716"),
    "Feijão": dict(ideal=(10, 15), ciclo=90, meses=3, coe=6000, fixo=500, preco=280, prod=45,
                   sigma=.30, perda=(.30, .60), perda_sem=.03, chuva=300, sidra="2701"),
}

# nível de insumo: (fator de produtividade, fator de custo variável) (P)
MANEJO = {
    "Baixo insumo": (0.88, 0.85),
    "Médio insumo": (1.00, 1.00),
    "Alto insumo": (1.10, 1.20),
}

# cenários de choque: (fator de preço, fator de produtividade, semanas extras de atraso)
CENARIOS = {
    "Base": (1.0, 1.0, 0),
    "Preço −20%": (0.8, 1.0, 0),
    "Seca (produção −30%)": (1.0, 0.7, 0),
    "Atraso de 3 semanas": (1.0, 1.0, 3),
    "Combinado": (0.8, 0.7, 3),
}


IRRIG_FIXO = 800    # (P) R$/ha/ano: energia, manutenção e depreciação da irrigação
IRRIG_FATOR = 0.35  # (P) fator sobre a chance de ano seco quando há irrigação
IRRIG_PROD = 1.10   # (P) produtividade média com irrigação, em relação ao sequeiro
# Solo (P): efeito sobre produtividade, custo de correção/adubação e chance de seca
SOLO = {
    "latossolo": dict(prod=1.00, custo=1.00, seca=1.00),  # (P) referência: profundo e bem drenado
    "argissolo": dict(prod=1.03, custo=1.03, seca=0.90),  # (P) mais argiloso: retém mais água
    "neossolo": dict(prod=0.85, custo=1.12, seca=1.30),   # (P) arenoso: pouca água e fertilidade
}


def custo_ha(c, nivel, area, irrigado=False, fator_custo=1.0):
    """Custo por hectare: variável + juros do capital + custo fixo rateado pela área."""
    k, cm = CULTURAS[c], MANEJO[nivel][1]
    return k["coe"] * cm * (1 + JUROS * k["meses"] / 12) * fator_custo + k["fixo"] * (AREA_REF / area) ** BETA + (IRRIG_FIXO if irrigado else 0)


def prob_adversidade(chuva, c, atraso=0, ideal=None):
    """Fração dos anos históricos em que a chuva do ciclo fica abaixo do mínimo da cultura."""
    k = CULTURAS[c]
    mes, dia = ideal or k["ideal"]
    anos = []
    for ano in sorted(set(chuva.index.year)):
        ini = pd.Timestamp(year=ano, month=mes, day=dia) + pd.Timedelta(weeks=atraso)
        serie = chuva[ini: ini + pd.Timedelta(days=k["ciclo"] - 1)]
        if serie.notna().sum() >= 0.9 * k["ciclo"]:
            anos.append(serie.sum() < k["chuva"])
    return max(0.05, float(np.mean(anos))) if anos else None


def simular(c, nivel, ctx, area, atraso=0, cenario=(1.0, 1.0, 0), n=10_000, com_receita=False):
    """Distribuição do resultado total (R$) da área para uma alternativa.
    A semente é fixa: todas as alternativas usam os mesmos sorteios, o que reduz o ruído
    nas comparações."""
    fp, fq, extra = cenario
    rng = np.random.default_rng(1)
    k, d = CULTURAS[c], ctx[c]
    semanas = atraso + extra
    p_adv = d["p_adv"][min(semanas, 8)]
    perda = np.where(rng.random(n) < p_adv, rng.uniform(*k["perda"], n), 0.0)
    ruido = np.clip(rng.normal(1, CV, n), 0.3, None)
    y = d["y"] * MANEJO[nivel][0] * fq * (1 - min(0.9, k["perda_sem"] * semanas)) * (1 - perda) * ruido
    preco = rng.lognormal(np.log(d["preco"] * fp), d["sigma"], n)
    res = (y * preco - custo_ha(c, nivel, area, d.get("irrigado", False), d.get("fator_custo", 1.0))) * area
    return (res, y * preco * area) if com_receita else res  # receita = arrecadação total da área


def avaliar(ctx, area, atraso=0, lam=0.5, zarc=None, credito_max=None, n=10_000):
    """Alternativas ordenadas pelo score: (1 − λ) × resultado esperado + λ × pior 10%.
    λ = 0 privilegia o retorno médio; λ = 1 privilegia o pior caso.
    Se houver limite de crédito, alternativas com custeio acima dele ficam inviáveis (por último)."""
    linhas = []
    for c in CULTURAS:
        if zarc is not None and c.split()[0] not in zarc:
            continue  # fora do zoneamento de risco (ZARC) para o município
        for nivel, (ym, cm) in MANEJO.items():
            r, rec = simular(c, nivel, ctx, area, atraso, n=n, com_receita=True)
            linhas.append(dict(
                Cultura=c, Manejo=nivel,
                Produtividade=ctx[c]["y"] * ym * (1 - min(0.9, CULTURAS[c]["perda_sem"] * atraso)) * (1 - ctx[c]["p_adv"][min(atraso, 8)] * np.mean(CULTURAS[c]["perda"])),
                Receita=rec.mean(),
                Esperado=r.mean(),
                Pior10=r[r <= np.percentile(r, 10)].mean(),
                ProbPrejuizo=(r < 0).mean(),
                Investimento=CULTURAS[c]["coe"] * cm * area * ctx[c].get("fator_custo", 1.0) + (IRRIG_FIXO * area if ctx[c].get("irrigado") else 0),
                PrecoMinimo=custo_ha(c, nivel, area, ctx[c].get("irrigado", False), ctx[c].get("fator_custo", 1.0)) / (ctx[c]["y"] * ym),
            ))
    colunas = ["Cultura", "Manejo", "Produtividade", "Receita", "Esperado", "Pior10", "ProbPrejuizo", "Investimento",
               "PrecoMinimo", "Score", "Fronteira", "Viavel"]
    if not linhas:  # nenhuma cultura tem zoneamento para o município
        return pd.DataFrame(columns=colunas)
    df = pd.DataFrame(linhas)
    df["Score"] = (1 - lam) * df.Esperado + lam * df.Pior10
    # eficiente = nenhuma outra alternativa tem retorno e pior caso iguais ou melhores
    df["Fronteira"] = [not ((df.Esperado >= e) & (df.Pior10 >= p)
                            & ((df.Esperado > e) | (df.Pior10 > p))).any()
                       for e, p in zip(df.Esperado, df.Pior10)]
    df["Viavel"] = True if credito_max is None else df.Investimento <= credito_max
    return df.sort_values(["Viavel", "Score"], ascending=[False, False], ignore_index=True)


def cenarios(ctx, area, atraso=0, zarc=None, n=10_000):
    """Resultado esperado (R$ na área) de cada alternativa em cada cenário de choque."""
    alts = [(c, m) for c in CULTURAS for m in MANEJO if zarc is None or c.split()[0] in zarc]
    return pd.DataFrame({
        nome: {f"{c} · {m}": simular(c, m, ctx, area, atraso, cen, n).mean() for c, m in alts}
        for nome, cen in CENARIOS.items()
    })


# ----------------------------- dados -----------------------------

def _csv(pasta, nome, **kw):
    caminho = os.path.join(pasta, nome)
    return pd.read_csv(caminho, **kw) if os.path.exists(caminho) else None


def municipios(uf):
    """Municípios da UF como {nome: código IBGE} (API de Localidades do IBGE)."""
    import requests
    url = f"https://servicodados.ibge.gov.br/api/v1/localidades/estados/{uf}/municipios"
    return {m["nome"]: str(m["id"]) for m in requests.get(url, timeout=20).json()}


def chuva_diaria(lat, lon, ini=2001, fim=2024):
    """Precipitação diária (mm) da NASA POWER para um ponto."""
    import requests
    url = ("https://power.larc.nasa.gov/api/temporal/daily/point?parameters=PRECTOTCORR"
           f"&community=AG&latitude={lat}&longitude={lon}&start={ini}0101&end={fim}1231&format=JSON")
    dados = requests.get(url, timeout=60).json()["properties"]["parameter"]["PRECTOTCORR"]
    s = pd.Series(dados, dtype=float)
    s.index = pd.to_datetime(s.index, format="%Y%m%d")
    return s.where(s >= 0).sort_index()  # -999 (falha) vira NaN


def produtividade_pam(codigo, c, anos=5):
    """Produtividade média (sc/ha) dos últimos anos, da PAM/IBGE (tabela 1712, via SIDRA)."""
    import requests
    url = (f"https://apisidra.ibge.gov.br/values/t/1712/n6/{codigo}"
           f"/v/214,216/p/last%20{anos}/c81/{CULTURAS[c]['sidra']}")
    prod = area = 0.0
    for linha in requests.get(url, timeout=30).json()[1:]:  # [0] é o cabeçalho
        txt = " ".join(str(v) for k, v in linha.items() if k[0] == "D" and k[-1] == "N").lower()
        if c.split()[0].lower() not in txt or linha["V"] in ("-", "...", "..", "X"):
            continue  # confere o nome do produto: código errado cai no fallback
        if "quantidade" in txt:
            prod += float(linha["V"])
        elif "colhida" in txt:
            area += float(linha["V"])
    if area == 0:
        raise ValueError("sem dados PAM para este código")
    return prod * 1000 / area / 60  # t/ha → kg/ha → sacas de 60 kg/ha


def montar_contexto(codigo=None, lat=None, lon=None, usar_api=True, pasta="dados", previsoes=None,
                    irrigado=False, epocas=None, solo="latossolo"):
    """Junta as fontes disponíveis e completa com premissas.
    Retorna (ctx, zarc, fontes): ctx por cultura, zarc={cultura: risco%} ou None."""
    fontes, chuva, pam_ok = [], None, []
    if usar_api and lat is not None:
        try:
            chuva = chuva_diaria(lat, lon)
            fontes.append("clima: NASA POWER 2001–2024")
        except Exception:
            fontes.append("clima: NASA POWER indisponível")
    if chuva is None:
        arq = _csv(pasta, "chuva.csv", parse_dates=["data"])
        if arq is not None:
            chuva = arq.set_index("data")["precipitacao_mm"].sort_index()
            fontes.append("clima: arquivo local")
    precos = _csv(pasta, "precos_conab.csv", parse_dates=["data"])
    futuros = _csv(pasta, "mercado_futuro.csv")
    sazonal = _csv(pasta, "previsao_sazonal.csv")
    usados = set()
    fac = SOLO.get(solo, SOLO["latossolo"])
    zarc_df = _csv(pasta, "zarc.csv", dtype={"codigo_ibge": str})
    zarc = None
    if zarc_df is not None and codigo:
        zarc = dict(zarc_df[zarc_df.codigo_ibge == codigo][["cultura", "risco_pct"]].values) or None
        fontes.append("zoneamento: ZARC" if zarc else "zoneamento: ZARC sem este município (sem restrição)")
    if precos is not None:
        fontes.append("preços: Conab (arquivo)")

    ctx = {}
    for c, k in CULTURAS.items():
        base = c.split()[0]
        y, preco, sigma = k["prod"], k["preco"], k["sigma"]
        tend_ok = False
        uf_cod = (codigo or "")[:2]
        if uf_cod in PROD_UF and c in PROD_UF[uf_cod]:
            y = PROD_UF[uf_cod][c]  # média estadual (Conab), sc/ha
            pam_ok.append(c)
        if precos is not None:
            s = precos[precos["produto"].str.startswith(base)].set_index("data")["preco"].sort_index()
            s = s[s.index >= s.index.max() - pd.DateOffset(years=5)]
            if len(s) > 12:
                preco, sigma = s.median(), float(np.clip(np.log(s).std(), .05, .6))
            if (previsoes or {}).get("tendencia"):
                tend = previsao.preco_tendencia(s, previsoes.get("ano", 2027))
                if tend:
                    preco, sigma = tend
                    tend_ok = True
                    usados.add("tendência de preço (Conab)")
        g = (previsoes or {}).get("crescimento") or 0
        if (previsoes or {}).get("tendencia") and not tend_ok and g:
            preco = previsao.preco_manual(preco, g)
            usados.add("crescimento digitado do preço")
        if (previsoes or {}).get("futuro"):
            do_arquivo = previsao.preco_futuro(futuros, base, previsoes.get("ano", 2027)) if futuros is not None else None
            f = do_arquivo or {"Soja": previsoes.get("fut_soja"), "Milho": previsoes.get("fut_milho")}.get(base)
            if f:
                preco = f
                usados.add("mercado futuro")
        risco = (zarc or {}).get(base)
        p_base = risco / 100 if risco is not None else P_ADV
        fator = previsao.fator_sazonal(sazonal, (previsoes or {}).get("prob_abaixo")) if (previsoes or {}).get("sazonal") else 1.0
        if fator != 1.0:
            usados.add("chuva sazonal (CPTEC)")
        f_tot = fator * (IRRIG_FATOR if irrigado else 1.0) * fac["seca"]
        p_adv = {}
        for w in range(9):  # chance de ano adverso para plantio com 0 a 8 semanas de atraso
            p = prob_adversidade(chuva, c, w, (epocas or {}).get(c)) if chuva is not None else None
            base_p = p_base if p is None else p
            p_adv[w] = base_p if f_tot == 1.0 else float(np.clip(base_p * f_tot, .02, .9))
        extra = 0.0  # semanas a mais em relação à época ideal
        if (epocas or {}).get(c):
            mes_e, dia_e = epocas[c]
            mes_i, dia_i = k["ideal"]
            extra = max(0.0, ((mes_e - mes_i) % 12) * 30.44 / 7 + (dia_e - dia_i) / 7)
        f_epoca = 1 - min(0.9, k["perda_sem"] * extra)
        ctx[c] = dict(y=y * (IRRIG_PROD if irrigado else 1.0) * f_epoca * fac["prod"], preco=preco, sigma=sigma,
                      p_adv=p_adv, irrigado=irrigado, fator_custo=fac["custo"])

    if irrigado:
        fontes.append(f"irrigação: +{(IRRIG_PROD - 1) * 100:.0f}% produtividade, chance de seca x{IRRIG_FATOR}, +R$ {IRRIG_FIXO}/ha (premissas P)")
    if usados:
        fontes.append("previsões: " + ", ".join(sorted(usados)))
    if chuva is None:
        fontes.append("clima: premissa (sem coordenadas ou dados)")
    if pam_ok:
        fontes.append("produtividade: Conab, média estadual")
    fontes.append("demais dados: premissas (P)")
    return ctx, zarc, fontes
