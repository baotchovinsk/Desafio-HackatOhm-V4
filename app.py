"""Interface do motor de decisão: três idiomas, três moedas e recursos de acessibilidade.

Rodar:  pip install streamlit pandas numpy requests altair
        streamlit run app.py

Arquivos: app.py, motor.py, textos.py e previsao.py. Dados opcionais na pasta ./dados.
"""
import json
import os

import altair as alt
import pandas as pd
import streamlit as st
import streamlit.components.v1 as components

import motor
import textos as tx

st.set_page_config(page_title="Qual cultivo rende mais com segurança?", layout="wide")
# Impede a tradução automática do Chrome, que quebra a página (erro removeChild) e troca palavras
components.html("""<script>
try{const d=window.parent.document;d.documentElement.lang="pt-BR";d.documentElement.setAttribute("translate","no");
if(!d.querySelector("meta[name=google]")){const m=d.createElement("meta");m.name="google";m.content="notranslate";d.head.appendChild(m);}}catch(e){}
</script>""", height=0)

# Centro aproximado de municípios do Cerrado (a grade da NASA POWER é de ~50 km, então basta)
COORD = {
    "Patos de Minas": (-18.58, -46.52),
    "Uberlândia": (-18.92, -48.28),
    "Uberaba": (-19.75, -47.93),
    "Unaí": (-16.36, -46.91),
    "Paracatu": (-17.22, -46.87),
    "Rio Verde": (-17.80, -50.93),
    "Sorriso": (-12.55, -55.72),
    "Luís Eduardo Magalhães": (-12.10, -45.80),
}
IDIOMAS = {"Português": "pt", "中文": "zh", "Русский": "ru"}
TTS = {"pt": "pt-BR", "zh": "zh-CN", "ru": "ru-RU"}
SOLOS = ["latossolo", "argissolo", "neossolo"]
ESCOLHAS_EPOCA = {
    "Soja": ["padrao", "10", "11", "12"],
    "Milho verão": ["padrao", "10", "11", "12"],
    "Milho safrinha": ["padrao", "1", "2", "3"],
    "Sorgo": ["padrao", "11", "12", "1"],
    "Feijão": ["padrao", "10", "11"],
}
LANG = "pt"
moeda = "brl"
sim, taxa = "R$", 1.0  # símbolo e cotação (unidades da moeda por 1 R$), definidos na barra lateral


def T(chave, **kw):
    return tx.t(LANG, chave, **kw)


def Tm(chave):
    """Texto com o símbolo da moeda escolhida no lugar de R$."""
    return T(chave).replace("R$", sim)


def dinh(v):
    """Valor em reais convertido para a moeda escolhida, com o formato do idioma."""
    return tx.dinheiro(v, LANG, taxa, sim)


@st.cache_data(ttl=86_400, show_spinner=False)
def municipios(uf):
    try:
        return motor.municipios(uf)
    except Exception:
        return {nome: None for nome in COORD}  # sem internet: lista mínima


@st.cache_data(ttl=86_400, show_spinner=False)
def contexto(codigo, lat, lon, usar_api, prev, irrig, epo, solo):
    return motor.montar_contexto(codigo, lat, lon, usar_api, previsoes=dict(prev), irrigado=irrig,
                                 epocas=dict(epo), solo=solo)


def arquivo(nome_arq):
    return T("arq_ok") if os.path.exists(os.path.join("dados", nome_arq)) else T("arq_falta")


with st.sidebar:
    st.caption("Versão 4: produtividade estadual (Conab), juros de 12,5%, idiomas, moedas e acessibilidade")
    LANG = IDIOMAS[st.selectbox("Idioma / 语言 / Язык", list(IDIOMAS))]

    with st.expander(T("sec_acess")):
        tam = st.radio(T("acess_tam"), ["normal", "grande", "muito"], horizontal=True,
                       format_func=lambda k: T({"normal": "tam_normal", "grande": "tam_grande",
                                                "muito": "tam_muito"}[k]))
        contraste = st.checkbox(T("acess_contraste"), value=False)

    moeda = st.selectbox(T("moeda"), list(tx.MOEDA), format_func=lambda k: tx.MOEDA[k]["nome"][tx.IDX[LANG]])
    sim = tx.MOEDA[moeda]["simbolo"]
    taxa = 1.0
    if moeda != "brl":
        taxa = st.number_input(T("cotacao", sim=sim), min_value=0.01,
                               value=float(tx.MOEDA[moeda]["cotacao"]), format="%.4f")
        st.caption(T("cot_nota"))

    st.header(T("sec_regiao"))
    uf = st.selectbox(T("estado"), ["MG", "GO", "MT", "MS", "BA", "MA", "TO", "PI"])
    lista = municipios(uf)
    nomes = list(lista)
    padrao = nomes.index("Patos de Minas") if "Patos de Minas" in nomes else 0
    nome = st.selectbox(T("municipio"), nomes, index=padrao)
    lat0, lon0 = COORD.get(nome, (0.0, 0.0))
    lat = st.number_input(T("lat"), value=float(lat0), format="%.4f")
    lon = st.number_input(T("lon"), value=float(lon0), format="%.4f")
    if not (lat and lon):
        st.info(T("sem_coord"))

    st.header(T("sec_prop"))
    area = st.number_input(T("area"), min_value=1, max_value=10_000_000, value=100)
    atraso = st.slider(T("atraso"), 0, 6, 0)
    credito = st.number_input(Tm("credito"), min_value=0.0, value=0.0, step=10_000.0)
    irrig = st.radio(T("irrig"), [False, True], horizontal=True,
                     format_func=lambda v: T("sim") if v else T("nao"))
    solo = st.selectbox(T("solo"), SOLOS, format_func=lambda s: tx.nome(tx.SOLO, LANG, s),
                        help=T("solo_help"))

    st.header(T("sec_risco"))
    lam = st.slider(T("lam"), 0.0, 1.0, 0.5, help=T("lam_help"))
    usar_api = st.toggle(T("api"), value=True)

    st.header(T("sec_epoca"))
    escolhas = {}
    for c, opcoes in ESCOLHAS_EPOCA.items():
        escolhas[c] = st.selectbox(
            tx.nome(tx.CULT, LANG, c), opcoes, key="ep_" + c,
            format_func=lambda m: T("padrao") if m == "padrao" else tx.nome(tx.MES, LANG, int(m)))
    epo = tuple(sorted((c, (int(m), 15)) for c, m in escolhas.items() if m != "padrao"))

    st.header(T("sec_prev"))
    g, f_soja, f_milho, pr = 0.0, 0.0, 0.0, 0.0
    p_tend = st.checkbox(T("prev_tend"), value=False)
    if p_tend:
        g = st.number_input(T("prev_var"), min_value=-50.0, max_value=100.0, value=0.0, step=1.0)
        st.caption(arquivo("precos_conab.csv"))
    p_fut = st.checkbox(T("prev_fut"), value=False)
    if p_fut:
        f_soja = st.number_input(Tm("fut_soja"), min_value=0.0, value=0.0, step=1.0)
        f_milho = st.number_input(Tm("fut_milho"), min_value=0.0, value=0.0, step=1.0)
        st.caption(arquivo("mercado_futuro.csv"))
    p_saz = st.checkbox(T("prev_saz"), value=False)
    if p_saz:
        pr = st.number_input(T("prob_abaixo"), min_value=0.0, max_value=100.0, value=0.0, step=1.0)
        st.caption(arquivo("previsao_sazonal.csv"))
    ano = 2027
    st.caption(T("safra"))

# Acessibilidade: tamanho do texto e alto contraste
css = ""
if tam != "normal":
    css += "html{font-size:%d%% !important}" % (120 if tam == "grande" else 140)
if contraste:
    css += ("[data-testid='stAppViewContainer'],[data-testid='stSidebar'],[data-testid='stHeader']{background:#000 !important}"
            "body,p,span,label,li,h1,h2,h3,h4,div{color:#fff !important}"
            "input,[data-baseweb='select'] > div{background:#111 !important;color:#fff !important;border-color:#fff !important}"
            "a{color:#ffe600 !important}")
if css:
    st.markdown(f"<style>{css}</style>", unsafe_allow_html=True)

# Valores digitados em moeda escolhida voltam para reais, que é a moeda do modelo
coord = (lat, lon) if (lat and lon) else (None, None)
f_soja_brl = f_soja / taxa if f_soja else None
f_milho_brl = f_milho / taxa if f_milho else None
credito_brl = credito / taxa if credito else None
ctx, zarc, fontes = contexto(lista.get(nome), coord[0], coord[1], usar_api,
                             (("tendencia", p_tend), ("futuro", p_fut), ("sazonal", p_saz), ("ano", ano),
                              ("crescimento", g / 100), ("fut_soja", f_soja_brl), ("fut_milho", f_milho_brl),
                              ("prob_abaixo", pr / 100 if pr else None)), irrig, epo, solo)
tab = motor.avaliar(ctx, area, atraso, lam, zarc, credito_max=credito_brl)

st.title(T("titulo"))
if tab.empty:
    st.error(T("err_zarc"))
    st.stop()
st.caption(T("cap", nome=nome, uf=uf, area=tx.fmt(area, LANG, 0), solo=tx.nome(tx.SOLO, LANG, solo),
             atraso=atraso, fontes="; ".join(tx.traduz_fonte(f, LANG, taxa, sim) for f in fontes)))
viaveis = tab[tab.Viavel]
if viaveis.empty:
    st.error(T("err_credito"))
    st.stop()
melhor = viaveis.iloc[0]
texto_voz = (T("reco", cultura=tx.nome(tx.CULT, LANG, melhor.Cultura), manejo=tx.nome(tx.MAN, LANG, melhor.Manejo))
             + " " + T("reco_det", esp=dinh(melhor.Esperado), prob=f"{melhor.ProbPrejuizo:.0%}",
                       pior=dinh(melhor.Pior10)))
st.success(texto_voz)
components.html(
    f"""<button id="ouvir" style="font-size:1rem;padding:.4rem .9rem;cursor:pointer">{T('ouvir')}</button>
<script>
document.getElementById("ouvir").onclick = function () {{
  speechSynthesis.cancel();
  var u = new SpeechSynthesisUtterance({json.dumps(texto_voz)});
  u.lang = "{TTS[LANG]}";
  speechSynthesis.speak(u);
}};
</script>""",
    height=60,
)

st.subheader(T("sec_resumo"))
m1, m2, m3 = st.columns(3)
m1.metric(T("arrecadacao"), dinh(melhor.Receita))
m2.metric(T("custeio"), dinh(melhor.Investimento))
m3.metric(T("lucro_medio"), dinh(melhor.Esperado))

st.subheader(T("sub_tab"))
exib = tab.assign(
    Cultura=tab.Cultura.map(lambda c: tx.nome(tx.CULT, LANG, c)),
    Manejo=tab.Manejo.map(lambda m: tx.nome(tx.MAN, LANG, m)),
    ProbPrejuizo=tab.ProbPrejuizo * 100,
    Produtividade=tab.Produtividade.map(lambda v: tx.fmt(v, LANG, 1)),
    Receita=tab.Receita.map(dinh),
    Esperado=tab.Esperado.map(dinh),
    Pior10=tab.Pior10.map(dinh),
    Investimento=tab.Investimento.map(dinh),
    PrecoMinimo=tab.PrecoMinimo.map(dinh),
)
st.dataframe(
    exib[["Cultura", "Manejo", "Viavel", "Produtividade", "Receita", "Esperado", "Pior10", "ProbPrejuizo",
          "Investimento", "PrecoMinimo", "Fronteira"]],
    hide_index=True,
    column_config={
        "Cultura": st.column_config.TextColumn(T("col_cult")),
        "Manejo": st.column_config.TextColumn(T("col_manejo")),
        "Viavel": st.column_config.CheckboxColumn(T("col_cabe")),
        "Produtividade": st.column_config.TextColumn(T("col_prod")),
        "Receita": st.column_config.TextColumn(T("col_receita")),
        "Esperado": st.column_config.TextColumn(T("col_esp")),
        "Pior10": st.column_config.TextColumn(T("col_pior")),
        "ProbPrejuizo": st.column_config.NumberColumn(T("col_prej"), format="%.0f%%"),
        "Investimento": st.column_config.TextColumn(Tm("col_custeio")),
        "PrecoMinimo": st.column_config.TextColumn(Tm("col_precomin")),
        "Fronteira": st.column_config.CheckboxColumn(T("col_efic")),
    },
)

st.subheader(T("sub_ret"))
st.caption(T("cap_ret"))
tab_g = tab.assign(Cultura=exib.Cultura, Manejo=exib.Manejo, Esperado=tab.Esperado * taxa, Pior10=tab.Pior10 * taxa)
grafico = alt.Chart(tab_g).mark_circle(size=180).encode(
    x=alt.X("Pior10:Q", title=Tm("ax_x")),
    y=alt.Y("Esperado:Q", title=Tm("ax_y")),
    color=alt.Color("Cultura:N", title=T("col_cult")),
    shape=alt.Shape("Manejo:N", title=T("col_manejo")),
    opacity=alt.condition("datum.Fronteira", alt.value(1.0), alt.value(0.25)),
    tooltip=["Cultura", "Manejo", alt.Tooltip("Esperado:Q", format=",.0f"),
             alt.Tooltip("Pior10:Q", format=",.0f"), alt.Tooltip("ProbPrejuizo:Q", format=".0%")],
).properties(height=360)
st.altair_chart(grafico, use_container_width=True)

st.subheader(Tm("sub_cen"))
st.caption(T("cap_cen"))
cen = motor.cenarios(ctx, area, atraso, zarc)
cen.index = [tx.traduz_alt(s, LANG) for s in cen.index]
cen.columns = [tx.nome(tx.CEN, LANG, c) for c in cen.columns]
st.dataframe(cen.map(dinh))

st.subheader(T("sub_melhor"))
melhores = pd.DataFrame([{T("col_cenario"): col, T("col_melhor"): cen[col].idxmax(),
                          T("col_esp"): dinh(cen[col].max())} for col in cen.columns])
st.dataframe(melhores, hide_index=True)
pior = cen.min(axis=1)
chave_seg = "segura" if pior.max() >= 0 else "segura_neg"
st.info(T(chave_seg, alt=pior.idxmax(), valor=dinh(pior.max())))

with st.expander(T("expander")):
    st.markdown(T("expl"))
