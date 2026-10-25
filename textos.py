"""Textos da interface (português, chinês e russo) e formatação de números e dinheiro."""
import re

IDX = {"pt": 0, "zh": 1, "ru": 2}
SEP = {"pt": (".", ","), "zh": (",", "."), "ru": ("\u00a0", ",")}

T = {
    "titulo": ("Qual cultivo e manejo rendem mais com segurança?", "哪种作物和管理方式在安全前提下收益最高？",
               "Какая культура и агротехника дают больше при меньшем риске?"),
    "sec_regiao": ("1. Região", "1. 地区", "1. Регион"),
    "estado": ("Estado", "州", "Штат"),
    "municipio": ("Município", "市/县", "Муниципалитет"),
    "lat": ("Latitude (0 = não informada)", "纬度（0 = 未填写）", "Широта (0 = не указана)"),
    "lon": ("Longitude (0 = não informada)", "经度（0 = 未填写）", "Долгота (0 = не указана)"),
    "sem_coord": ("Sem coordenadas: o clima local não será consultado. Digite latitude e longitude para usar a NASA POWER.",
                  "没有坐标：不会查询当地气候。输入纬度和经度即可使用 NASA POWER。",
                  "Нет координат: местный климат не будет запрошен. Введите широту и долготу, чтобы использовать NASA POWER."),
    "sec_prop": ("2. Propriedade", "2. 农场", "2. Хозяйство"),
    "area": ("Tamanho da área (ha)", "面积（公顷）", "Площадь (га)"),
    "atraso": ("Atraso no plantio (semanas)", "播种延迟（周）", "Задержка посева (недели)"),
    "credito": ("Crédito máximo para custeio (R$; 0 = sem limite)", "生产信贷上限（R$；0 = 不限）",
                "Лимит кредита на custeio (R$; 0 = без лимита)"),
    "irrig": ("A área tem irrigação?", "该地块有灌溉吗？", "На участке есть орошение?"),
    "sim": ("Sim", "是", "Да"),
    "nao": ("Não", "否", "Нет"),
    "solo": ("Tipo de solo", "土壤类型", "Тип почвы"),
    "solo_help": ("Muda produtividade, custo de correção e risco de seca. Valores (P) são premissas.",
                  "影响产量、土壤改良成本和干旱风险。（P）为假设值。",
                  "Меняет урожайность, затраты на корректировку и риск засухи. Значения (P) — предположения."),
    "sec_risco": ("3. Seu perfil de risco", "3. 风险偏好", "3. Ваш профиль риска"),
    "lam": ("Proteção contra o pior cenário", "最差情景保护", "Защита от худшего сценария"),
    "lam_help": ("0 = maximizar o resultado médio. 1 = priorizar o pior 10% dos anos.",
                 "0 = 最大化平均结果；1 = 优先考虑最差的 10% 年份。",
                 "0 = максимум среднего результата. 1 = приоритет худшим 10% лет."),
    "api": ("Usar dados reais (IBGE e NASA POWER)", "使用真实数据（IBGE 和 NASA POWER）",
            "Использовать реальные данные (IBGE и NASA POWER)"),
    "sec_epoca": ("Época de plantio", "播种时期", "Время посева"),
    "padrao": ("Padrão", "默认", "По умолчанию"),
    "sec_prev": ("4. Previsões (opcional)", "4. 预测（可选）", "4. Прогнозы (необязательно)"),
    "prev_tend": ("Preço pela tendência", "按趋势预测价格", "Цена по тренду"),
    "prev_var": ("Variação do preço até a colheita de 2027 (%)", "2027 年收获前的价格变化（%）",
                 "Изменение цены до урожая 2027 г. (%)"),
    "prev_fut": ("Preço do mercado futuro (B3)", "期货价格（B3）", "Цена фьючерсов (B3)"),
    "fut_soja": ("Soja: cotação futura (R$/saca; 0 = não informar)", "大豆期货价（R$/袋；0 = 不填）",
                 "Соя: цена фьючерса (R$/мешок; 0 = не указывать)"),
    "fut_milho": ("Milho: cotação futura (R$/saca; 0 = não informar)", "玉米期货价（R$/袋；0 = 不填）",
                  "Кукуруза: цена фьючерса (R$/мешок; 0 = не указывать)"),
    "prev_saz": ("Chuva da safra (CPTEC)", "收获季降雨（CPTEC）", "Осадки в сезоне (CPTEC)"),
    "prob_abaixo": ("Chance de chuva abaixo do normal (%; 0 = não informar)", "降雨低于正常的概率（%；0 = 不填）",
                    "Вероятность осадков ниже нормы (%; 0 = не указывать)"),
    "arq_ok": ("arquivo encontrado na pasta dados", "已在 dados 文件夹中找到文件", "файл найден в папке dados"),
    "arq_falta": ("sem arquivo: use o campo acima", "没有文件：请使用上面的栏目", "нет файла: используйте поле выше"),
    "safra": ("Safra de referência: colheita de 2027 (ano que vem).", "参考季：2027 年收获（明年）。",
              "Сезон: урожай 2027 г. (в следующем году)."),
    "cap": ("{nome} ({uf}) · {area} ha · solo: {solo} · atraso de {atraso} sem. · fontes: {fontes}",
            "{nome}（{uf}）· {area} 公顷 · 土壤：{solo} · 延迟 {atraso} 周 · 来源：{fontes}",
            "{nome} ({uf}) · {area} га · почва: {solo} · задержка {atraso} нед. · источники: {fontes}"),
    "err_zarc": ("Nenhuma cultura tem zoneamento ZARC para este município no arquivo zarc.csv.",
                 "zarc.csv 中该市没有任何作物的 ZARC 区划数据。",
                 "В файле zarc.csv для этого муниципалитета нет зонирования ZARC ни для одной культуры."),
    "err_credito": ("Nenhuma alternativa cabe no crédito informado. Reduza a área ou aumente o crédito.",
                    "没有任何方案符合所填信贷额度。请减少面积或增加信贷。",
                    "Ни одна альтернатива не укладывается в указанный кредит. Уменьшите площадь или увеличьте кредит."),
    "reco": ("Recomendação: {cultura}, {manejo}.", "推荐：{cultura}，{manejo}。", "Рекомендация: {cultura}, {manejo}."),
    "reco_det": ("Lucro médio esperado de {esp} na área, com {prob} de chance de prejuízo. No pior 10% dos anos, o lucro fica em {pior}.",
                 "该面积的预期平均利润为 {esp}，亏损概率 {prob}。在最差的 10% 年份，利润为 {pior}。",
                 "Средняя ожидаемая прибыль на площади: {esp}, вероятность убытка {prob}. В худших 10% лет прибыль составит {pior}."),
    "sub_tab": ("Alternativas, da melhor para a pior", "方案（从最好到最差）", "Варианты: от лучшего к худшему"),
    "col_cult": ("Cultura", "作物", "Культура"),
    "col_manejo": ("Manejo", "管理方式", "Агротехника"),
    "col_cabe": ("Cabe no crédito", "符合信贷", "Укладывается в кредит"),
    "col_prod": ("Produtividade (sc/ha)", "产量（袋/公顷）", "Урожайность (мешки/га)"),
    "col_esp": ("Lucro médio esperado", "预期平均利润", "Средняя ожидаемая прибыль"),
    "col_pior": ("Pior 10% dos anos", "最差 10% 年份", "Худшие 10% лет"),
    "col_prej": ("Chance de prejuízo", "亏损概率", "Вероятность убытка"),
    "col_custeio": ("Custeio (R$)", "生产成本（R$）", "Затраты custeio (R$)"),
    "col_precomin": ("Preço mínimo (R$/sc)", "最低价格（R$/袋）", "Минимальная цена (R$/мешок)"),
    "col_efic": ("Eficiente", "有效", "Эффективно"),
    "sub_ret": ("Retorno × risco", "收益 × 风险", "Доходность × риск"),
    "cap_ret": ("Pontos cheios são eficientes: nenhuma outra alternativa tem retorno e pior caso iguais ou melhores.",
                "实心点为有效方案：没有其他方案的收益和最差情况都不低于它。",
                "Заполненные точки эффективны: ни одна другая альтернатива не имеет равного или лучшего дохода и худшего случая."),
    "ax_x": ("Pior 10% dos anos (R$)", "最差 10% 年份（R$）", "Худшие 10% лет (R$)"),
    "ax_y": ("Lucro médio esperado (R$)", "预期平均利润（R$）", "Средняя ожидаемая прибыль (R$)"),
    "sub_cen": ("Cenários de choque (lucro médio esperado, R$ na área)", "冲击情景（该面积的预期平均利润，R$）",
                "Сценарии шока (средняя ожидаемая прибыль, R$ на площади)"),
    "cap_cen": ("Como cada alternativa reage a queda de preço, seca, atraso no plantio e combinações.",
                "各方案如何应对价格下跌、干旱、播种延迟及其组合。",
                "Как каждая альтернатива реагирует на падение цены, засуху, задержку посева и их сочетания."),
    "sub_melhor": ("Melhor alternativa em cada cenário", "各情景下的最佳方案", "Лучшая альтернатива в каждом сценарии"),
    "col_cenario": ("Cenário", "情景", "Сценарий"),
    "col_melhor": ("Melhor alternativa", "最佳方案", "Лучшая альтернатива"),
    "segura": ("Alternativa mais segura (maior resultado no pior cenário): {alt}, com {valor} no pior caso.",
               "最安全的方案（最差情景下结果最高）：{alt}，最差情况下为 {valor}。",
               "Самая надёжная альтернатива (лучший результат в худшем сценарии): {alt}, при {valor} в худшем случае."),
    "expander": ("Como a decisão é calculada", "决策如何计算", "Как вычисляется решение"),
    "expl": ("- **Lucro médio** = produtividade × preço − custo variável − juros − custo fixo rateado pela área, média dos 10 mil anos simulados.\n"
             "- **Score** = (1 − λ) × lucro médio + λ × pior 10%. Com λ = 0 vence o retorno médio; com λ = 1, vence o pior caso.\n"
             "- **Área:** o custo fixo por hectare cai com o tamanho (economia de escala), e o custeio cresce junto. Com crédito limitado, áreas maiores tiram alternativas da lista.\n"
             "- **Premissas (P):** valores de referência, estimativas a confirmar. Fontes e limitações estão no site do projeto.",
             "- **平均利润** = 产量 × 价格 − 可变成本 − 利息 − 按面积分摊的固定成本，取 1 万年模拟的平均值。\n"
             "- **得分** = (1 − λ) × 平均利润 + λ × 最差 10%。λ = 0 时看平均收益；λ = 1 时看最差情况。\n"
             "- **面积：**每公顷固定成本随规模下降（规模经济），生产成本同步上升。信贷有限时，大面积会减少可选方案。\n"
             "- **假设（P）：**参考值，属于待确认的估计。来源和局限见项目网站。",
             "- **Средняя прибыль** = урожайность × цена − переменные затраты − проценты − постоянные затраты, распределённые по площади; среднее по 10 тысячам смоделированных лет.\n"
             "- **Балл** = (1 − λ) × средняя прибыль + λ × худшие 10%. При λ = 0 важен средний доход; при λ = 1 — худший случай.\n"
             "- **Площадь:** постоянные затраты на гектар снижаются с размером (эффект масштаба), а затраты custeio растут. При ограниченном кредите большие площади исключают альтернативы.\n"
             "- **Предположения (P):** справочные значения, требующие подтверждения. Источники и ограничения — на сайте проекта."),
    "segura_neg": ("Menor prejuízo no pior cenário: {alt}, com {valor} no pior caso.",
                   "最差情景下亏损最小的方案：{alt}，最差情况下为 {valor}。",
                   "Наименьший убыток в худшем сценарии: {alt}, при {valor} в худшем случае."),
}

CULT = {
    "Soja": ("Soja", "大豆", "Соя"),
    "Milho verão": ("Milho verão", "夏季玉米", "Кукуруза (лето)"),
    "Milho safrinha": ("Milho safrinha", "二季玉米（safrinha）", "Кукуруза safrinha"),
    "Sorgo": ("Sorgo", "高粱", "Сорго"),
    "Feijão": ("Feijão", "菜豆（feijão）", "Фасоль"),
}
MAN = {
    "Baixo insumo": ("Baixo insumo", "低投入", "Низкие затраты"),
    "Médio insumo": ("Médio insumo", "中等投入", "Средние затраты"),
    "Alto insumo": ("Alto insumo", "高投入", "Высокие затраты"),
}
CEN = {
    "Base": ("Base", "基准", "Базовый"),
    "Preço −20%": ("Preço −20%", "价格 −20%", "Цена −20%"),
    "Seca (produção −30%)": ("Seca (produção −30%)", "干旱（产量 −30%）", "Засуха (урожай −30%)"),
    "Atraso de 3 semanas": ("Atraso de 3 semanas", "延迟 3 周", "Задержка на 3 недели"),
    "Combinado": ("Combinado", "组合", "Комбинированный"),
}
MES = {
    10: ("Outubro", "十月", "Октябрь"), 11: ("Novembro", "十一月", "Ноябрь"), 12: ("Dezembro", "十二月", "Декабрь"),
    1: ("Janeiro", "一月", "Январь"), 2: ("Fevereiro", "二月", "Февраль"), 3: ("Março", "三月", "Март"),
}
SOLO = {
    "latossolo": ("Latossolo (profundo, bem drenado)", "Latossolo（深厚，排水良好）", "Латосолы (глубокие, хорошо дренированные)"),
    "argissolo": ("Argissolo (mais argiloso)", "Argissolo（粘土含量较高）", "Аргисолы (более глинистые)"),
    "neossolo": ("Neossolo Quartzarênico (arenoso)", "Neossolo Quartzarênico（沙质）", "Неосолы кварцевые (песчаные)"),
}
PREV = {
    "tendência de preço (Conab)": ("按趋势的价格（Conab）", "цена по тренду (Conab)"),
    "crescimento digitado do preço": ("输入的价格增长", "введённый рост цены"),
    "mercado futuro": ("期货市场", "фьючерсы"),
    "chuva sazonal (CPTEC)": ("季节性降雨（CPTEC）", "сезонные осадки (CPTEC)"),
}
FIXAS = {
    "clima: NASA POWER 2001–2024": ("气候：NASA POWER 2001–2024", "климат: NASA POWER 2001–2024"),
    "clima: NASA POWER indisponível": ("气候：NASA POWER 不可用", "климат: NASA POWER недоступен"),
    "clima: arquivo local": ("气候：本地文件", "климат: локальный файл"),
    "produtividade: Conab, média estadual": ("产量：Conab，州平均", "урожайность: Conab, средняя по штату"),
    "zoneamento: ZARC": ("区划：ZARC", "зонирование: ZARC"),
    "zoneamento: ZARC sem este município (sem restrição)": ("区划：该市无 ZARC 数据（无限制）",
                                                         "зонирование: нет ZARC для этого муниципалитета (без ограничений)"),
    "preços: Conab (arquivo)": ("价格：Conab（文件）", "цены: Conab (файл)"),
    "clima: premissa (sem coordenadas ou dados)": ("气候：假设（无坐标或数据）", "климат: предположение (нет координат или данных)"),
    "demais dados: premissas (P)": ("其他数据：假设（P）", "остальные данные: предположения (P)"),
}


def t(lang, chave, **kw):
    s = T[chave][IDX[lang]]
    return s.format(**kw) if kw else s


def nome(tabela, lang, chave):
    return tabela.get(chave, (str(chave),) * 3)[IDX[lang]]


def traduz_alt(s, lang):
    c, m = s.split(" · ", 1)
    return f"{nome(CULT, lang, c)} · {nome(MAN, lang, m)}"


def fmt(v, lang, casas=2, sim=None):
    mil, dec = SEP[lang]
    s = f"{v:,.{casas}f}".replace(",", "\0").replace(".", dec).replace("\0", mil)
    if not sim:
        return s
    # em russo o símbolo vem depois do número: 184 948 207,50 ₽
    return f"{s} {sim}" if lang == "ru" else f"{sim} {s}"


def dinheiro(v_brl, lang, taxa=1.0, sim="R$"):
    return fmt(v_brl * taxa, lang, 2, sim)


def traduz_fonte(s, lang, taxa=1.0, sim="R$"):
    """Traduz uma linha da lista de fontes. Valores em reais viram a moeda escolhida."""
    m = re.match(r"irrigação: \+(\d+)% produtividade, chance de seca x([\d.]+), \+R\$ (\d+)/ha", s)
    if m:
        a, b, c = m.groups()
        custo = fmt(float(c) * taxa, lang, 0, sim)
        if lang == "pt":
            return f"irrigação: +{a}% produtividade, chance de seca x{b}, +{custo}/ha (premissas P)"
        if lang == "zh":
            return f"灌溉：产量 +{a}%，干旱概率 ×{b}，+{custo}/公顷"
        return f"орошение: урожайность +{a}%, вероятность засухи ×{b}, +{custo}/га"
    if lang == "pt":
        return s
    k = 0 if lang == "zh" else 1
    if s in FIXAS:
        return FIXAS[s][k]
    m = re.match(r"produtividade: IBGE PAM \((\d+) culturas\)", s)
    if m:
        n = m.group(1)
        return f"产量：IBGE PAM（{n} 种作物）" if k == 0 else f"урожайность: IBGE PAM ({n} культур)"
    if s.startswith("previsões: "):
        itens = [PREV[x][k] if x in PREV else x for x in s[len("previsões: "):].split(", ")]
        return ("预测：" if k == 0 else "прогнозы: ") + ", ".join(itens)
    return s

MOEDA = {
    "brl": {"simbolo": "R$", "nome": ("Real (R$)", "雷亚尔 (R$)", "Реал (R$)"), "cotacao": 1.0},
    "rub": {"simbolo": "₽", "nome": ("Rublo (₽)", "卢布 (₽)", "Рубль (₽)"), "cotacao": 15.0},
    "cny": {"simbolo": "CN¥", "nome": ("Yuan (CN¥)", "人民币 (CN¥)", "Юань (CN¥)"), "cotacao": 1.33},
}
