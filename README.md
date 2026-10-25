# Qual cultivo e manejo rendem mais com segurança

Simulador de decisão para escolher cultivo e manejo de grãos no Cerrado (soja, milho, sorgo e feijão).
Usa clima da NASA POWER, zoneamento de risco do ZARC, preços do Cepea e produtividade estadual da Conab.

## Arquivos

- `app.py`: a interface (Streamlit).
- `motor.py`: os cálculos e as premissas.
- `textos.py`: textos em português, chinês e russo, e formatação de dinheiro.
- `previsao.py`: previsões opcionais (tendência de preço, mercado futuro e chance de seca).
- `requirements.txt`: bibliotecas necessárias.
- `dados/` (opcional): `precos_conab.csv`, `zarc.csv`, `chuva.csv`, `mercado_futuro.csv`, `previsao_sazonal.csv`.

## Rodar no computador

```
python -m pip install -r requirements.txt
python -m streamlit run app.py
```

O navegador abre em `http://localhost:8501`.

## Publicar no Streamlit Community Cloud

1. Envie estes arquivos para um repositório no GitHub.
2. Em share.streamlit.io, escolha o repositório, o branch principal e `app.py` como arquivo principal.

## Premissas

Os valores marcados com (P) são estimativas. Eles estão listados na seção de fontes do site.
