-- Курируемый банк технических вопросов (Веха 1), status='approved'.
-- Контент — стандартные, общепринятые концепции IB/финансов (не рыночные данные).

INSERT INTO questions (topic_id, type, difficulty, body, options_json, correct_key, correct_answer, tolerance_pct, explanation, source, status) VALUES (
    1, 'open', 2, 'Перечисли основные шаги построения DCF-модели (кратко, по порядку).',
    NULL, NULL, NULL, NULL,
    'Прогноз выручки и статей P&L -> расчёт unlevered FCF (EBIT*(1-t) + D&A - CapEx - изменение NWC) -> выбор ставки дисконтирования (WACC) -> дисконтирование прогнозных FCF -> расчёт terminal value (Gordon Growth или Exit Multiple) -> дисконтирование TV -> сумма = Enterprise Value -> минус чистый долг и неконтролирующие доли, плюс доли в ассоциированных компаниях -> Equity Value -> делим на число акций.', 'seed_v1', 'approved'
);

INSERT INTO questions (topic_id, type, difficulty, body, options_json, correct_key, correct_answer, tolerance_pct, explanation, source, status) VALUES (
    1, 'open', 2, 'В чём разница между FCFF (unlevered FCF) и FCFE (levered FCF)?',
    NULL, NULL, NULL, NULL,
    'FCFF - денежный поток, доступный всем поставщикам капитала (держателям долга и акций), не учитывает процентные платежи. FCFE - поток, доступный только акционерам, после обслуживания долга (за вычетом процентов и чистого погашения долга, плюс нетто новых заимствований). FCFF дисконтируется по WACC и даёт EV, FCFE дисконтируется по cost of equity и даёт Equity Value напрямую.', 'seed_v1', 'approved'
);

INSERT INTO questions (topic_id, type, difficulty, body, options_json, correct_key, correct_answer, tolerance_pct, explanation, source, status) VALUES (
    1, 'mcq', 2, 'Какая формула корректно считает Unlevered Free Cash Flow (FCFF)?',
    '[{"key": "A", "text": "EBIT×(1−t) + D&A − CapEx − ΔNWC"}, {"key": "B", "text": "Net Income + D&A − CapEx"}, {"key": "C", "text": "EBITDA − Interest − Taxes"}, {"key": "D", "text": "Net Income − CapEx + ΔNWC"}]', 'A', NULL, NULL,
    'FCFF строится от EBIT, не от Net Income, чтобы исключить влияние структуры финансирования (проценты не вычитаются).', 'seed_v1', 'approved'
);

INSERT INTO questions (topic_id, type, difficulty, body, options_json, correct_key, correct_answer, tolerance_pct, explanation, source, status) VALUES (
    1, 'open', 3, 'Почему для дисконтирования FCFF используется WACC, а не стоимость собственного капитала (cost of equity)?',
    NULL, NULL, NULL, NULL,
    'FCFF - поток, принадлежащий всем инвесторам (и держателям долга, и акционерам), поэтому его нужно дисконтировать по средневзвешенной стоимости капитала обоих источников - WACC. Использование только cost of equity занизило бы ставку дисконтирования и завысило бы стоимость, так как не учитывало бы стоимость долгового финансирования.', 'seed_v1', 'approved'
);

INSERT INTO questions (topic_id, type, difficulty, body, options_json, correct_key, correct_answer, tolerance_pct, explanation, source, status) VALUES (
    1, 'open', 3, 'Как рассчитывается terminal value методом Gordon Growth и какие у него ограничения?',
    NULL, NULL, NULL, NULL,
    'TV = FCF(n+1) / (WACC − g), где FCF(n+1) - FCF первого года после прогнозного периода, g - долгосрочный темп роста. Ограничение: результат крайне чувствителен к разнице (WACC − g); g не должен превышать долгосрочный темп роста экономики, а при g, близком к WACC, оценка становится нестабильной.', 'seed_v1', 'approved'
);

INSERT INTO questions (topic_id, type, difficulty, body, options_json, correct_key, correct_answer, tolerance_pct, explanation, source, status) VALUES (
    1, 'open', 2, 'Чем terminal value через Exit Multiple отличается от Gordon Growth?',
    NULL, NULL, NULL, NULL,
    'Exit Multiple берёт мультипликатор (например EV/EBITDA) сопоставимых компаний и применяет его к прогнозному показателю последнего года прогноза, получая TV напрямую из рыночных данных, а не из формулы роста. Это делает TV менее чувствительным к предположению о g, но переносит в модель текущую рыночную оценку компаний-аналогов.', 'seed_v1', 'approved'
);

INSERT INTO questions (topic_id, type, difficulty, body, options_json, correct_key, correct_answer, tolerance_pct, explanation, source, status) VALUES (
    1, 'numeric', 2, 'FCF в последнем прогнозном году составляет $80m, долгосрочный темп роста g=2%, WACC=10%. Посчитай terminal value (в млн $) по формуле Gordon Growth.',
    NULL, NULL, '1020', 1,
    'TV = FCF×(1+g) / (WACC − g) = 80×1.02 / (0.10 − 0.02) = 81.6 / 0.08 = 1020 млн $.', 'seed_v1', 'approved'
);

INSERT INTO questions (topic_id, type, difficulty, body, options_json, correct_key, correct_answer, tolerance_pct, explanation, source, status) VALUES (
    1, 'open', 3, 'Почему при переходе от Enterprise Value к Equity Value нужно вычесть именно чистый долг, а не общий долг?',
    NULL, NULL, NULL, NULL,
    'Enterprise Value отражает стоимость операционного бизнеса независимо от структуры финансирования и денежных остатков. Cash - неоперационный актив, который «гасит» часть долговой нагрузки, поэтому вычитается net debt = total debt − cash & equivalents, а не gross debt, чтобы корректно получить стоимость, принадлежащую акционерам.', 'seed_v1', 'approved'
);

INSERT INTO questions (topic_id, type, difficulty, body, options_json, correct_key, correct_answer, tolerance_pct, explanation, source, status) VALUES (
    2, 'open', 1, 'В чём базовое отличие EV/EBITDA от P/E как мультипликатора?',
    NULL, NULL, NULL, NULL,
    'EV/EBITDA - мультипликатор enterprise-value: делит стоимость всей компании (долг+equity−cash) на показатель до вычета процентов, налогов и D&A, поэтому не зависит от структуры капитала. P/E - equity-мультипликатор (цена акции / EPS), чувствителен к долговой нагрузке (через проценты) и хуже подходит для сравнения компаний с разной структурой капитала.', 'seed_v1', 'approved'
);

INSERT INTO questions (topic_id, type, difficulty, body, options_json, correct_key, correct_answer, tolerance_pct, explanation, source, status) VALUES (
    2, 'open', 2, 'Почему нельзя делить EV на Net Income (а не на EBITDA/EBIT)?',
    NULL, NULL, NULL, NULL,
    'EV - числитель, отражающий стоимость и держателей долга, и акционеров (до процентов). Net Income - прибыль уже после процентов и налогов, то есть показатель, принадлежащий только акционерам. Смешивание «числителя для всех инвесторов» со «знаменателем только для акционеров» даёт математически несопоставимый мультипликатор.', 'seed_v1', 'approved'
);

INSERT INTO questions (topic_id, type, difficulty, body, options_json, correct_key, correct_answer, tolerance_pct, explanation, source, status) VALUES (
    2, 'mcq', 2, 'Какая пара числитель/знаменатель мультипликаторов методологически корректна?',
    '[{"key": "A", "text": "EV / Net Income"}, {"key": "B", "text": "Equity Value / EBITDA"}, {"key": "C", "text": "EV / EBITDA"}, {"key": "D", "text": "EV / EPS"}]', 'C', NULL, NULL,
    'И EV, и EBITDA - показатели «до платежей поставщикам капитала», это единственная методологически согласованная пара из перечисленных.', 'seed_v1', 'approved'
);

INSERT INTO questions (topic_id, type, difficulty, body, options_json, correct_key, correct_answer, tolerance_pct, explanation, source, status) VALUES (
    2, 'open', 2, 'Что показывает мультипликатор P/B (Price/Book) и для каких секторов он особенно применим?',
    NULL, NULL, NULL, NULL,
    'P/B сравнивает рыночную капитализацию с балансовой стоимостью собственного капитала. Особенно полезен для секторов, где балансовая стоимость активов близка к их реальной ценности - банки и финансовые компании (активы - в основном регулярно переоцениваемые финансовые инструменты), страховые и REIT.', 'seed_v1', 'approved'
);

INSERT INTO questions (topic_id, type, difficulty, body, options_json, correct_key, correct_answer, tolerance_pct, explanation, source, status) VALUES (
    2, 'open', 3, 'Почему быстрорастущие убыточные компании часто оценивают через EV/Revenue, а не EV/EBITDA?',
    NULL, NULL, NULL, NULL,
    'Если EBITDA отрицательна или близка к нулю, мультипликатор EV/EBITDA становится неинформативным или даёт бессмысленный результат. Выручка обычно положительна даже у убыточных быстрорастущих компаний, поэтому EV/Revenue остаётся применимым, хотя и менее точным, так как не учитывает разницу в марже.', 'seed_v1', 'approved'
);

INSERT INTO questions (topic_id, type, difficulty, body, options_json, correct_key, correct_answer, tolerance_pct, explanation, source, status) VALUES (
    2, 'numeric', 2, 'У компании EV = $1200m, LTM EBITDA = $150m. Посчитай EV/EBITDA.',
    NULL, NULL, '8', 1,
    'EV/EBITDA = 1200 / 150 = 8x.', 'seed_v1', 'approved'
);

INSERT INTO questions (topic_id, type, difficulty, body, options_json, correct_key, correct_answer, tolerance_pct, explanation, source, status) VALUES (
    2, 'open', 2, 'Что такое comps (comparable companies analysis) и какие есть подводные камни при выборе аналогов?',
    NULL, NULL, NULL, NULL,
    'Comps - метод оценки через мультипликаторы публичных компаний-аналогов (или прецедентных сделок). Подводные камни: различия в размере, темпах роста, марже, географии, стадии цикла, учётной политике; малая выборка аналогов; рыночные мультипликаторы отражают текущий сентимент рынка, а не «справедливую» стоимость.', 'seed_v1', 'approved'
);

INSERT INTO questions (topic_id, type, difficulty, body, options_json, correct_key, correct_answer, tolerance_pct, explanation, source, status) VALUES (
    2, 'open', 3, 'Почему при сравнении компаний из разных стран мультипликаторы EV/EBITDA нужно интерпретировать с осторожностью?',
    NULL, NULL, NULL, NULL,
    'Различия в налоговых режимах, учётных стандартах (например трактовка операционной аренды по IFRS 16 vs старым стандартам), уровне листинговых рисков, стоимости капитала и макроэкономических условиях (страновая премия за риск) могут делать номинально похожие мультипликаторы несопоставимыми по существу.', 'seed_v1', 'approved'
);

INSERT INTO questions (topic_id, type, difficulty, body, options_json, correct_key, correct_answer, tolerance_pct, explanation, source, status) VALUES (
    3, 'open', 2, 'Назови три классических источника доходности (return drivers) в LBO.',
    NULL, NULL, NULL, NULL,
    '(1) Delevering / debt paydown - погашение долга за счёт денежного потока компании увеличивает долю equity в итоговой стоимости; (2) EBITDA growth - рост операционного показателя за период владения; (3) Multiple expansion (или contraction) - изменение мультипликатора продажи на выходе относительно мультипликатора входа.', 'seed_v1', 'approved'
);

INSERT INTO questions (topic_id, type, difficulty, body, options_json, correct_key, correct_answer, tolerance_pct, explanation, source, status) VALUES (
    3, 'open', 2, 'Почему в LBO-сделках предпочитают компании со стабильным и предсказуемым денежным потоком?',
    NULL, NULL, NULL, NULL,
    'Высокая долговая нагрузка требует регулярного обслуживания (проценты + погашение основного долга). Стабильный, предсказуемый FCF снижает риск нарушения ковенант и дефолта, позволяя обслуживать долг даже в сложные периоды - поэтому LBO-фонды избегают циклических/капиталоёмких бизнесов с волатильным CF без веской причины.', 'seed_v1', 'approved'
);

INSERT INTO questions (topic_id, type, difficulty, body, options_json, correct_key, correct_answer, tolerance_pct, explanation, source, status) VALUES (
    3, 'open', 3, 'Как рост доли долга в структуре финансирования (leverage) влияет на IRR инвестора при прочих равных, и почему у этого есть предел?',
    NULL, NULL, NULL, NULL,
    'При прочих равных больший leverage повышает IRR на equity, потому что тот же прирост EBITDA и мультипликатор на выходе распределяются на меньшую сумму вложенного equity (financial leverage effect). Предел - рост стоимости долга и риска дефолта: чем выше leverage, тем выше процентная ставка и жёстче ковенанты, а в стрессовом сценарии компания может не справиться с обслуживанием долга, что обнулит equity.', 'seed_v1', 'approved'
);

INSERT INTO questions (topic_id, type, difficulty, body, options_json, correct_key, correct_answer, tolerance_pct, explanation, source, status) VALUES (
    3, 'mcq', 2, 'Что из перечисленного НЕ является типичным источником финансирования LBO?',
    '[{"key": "A", "text": "Term Loan"}, {"key": "B", "text": "High Yield Bonds"}, {"key": "C", "text": "Sponsor equity"}, {"key": "D", "text": "Государственная субсидия"}]', 'D', NULL, NULL,
    'Term Loan, High Yield Bonds и sponsor equity - стандартные источники финансирования LBO. Государственные субсидии не являются типичным источником финансирования подобных сделок.', 'seed_v1', 'approved'
);

INSERT INTO questions (topic_id, type, difficulty, body, options_json, correct_key, correct_answer, tolerance_pct, explanation, source, status) VALUES (
    3, 'open', 2, 'Что такое covenants в контексте LBO-долга и зачем они нужны кредиторам?',
    NULL, NULL, NULL, NULL,
    'Covenants - договорные условия долгового соглашения, ограничивающие поведение заёмщика (например максимальный leverage ratio, минимальный interest coverage ratio, ограничения на доп. заимствования или дивиденды). Они защищают кредиторов правом потребовать досрочного погашения или пересмотра условий, если финансовое состояние компании ухудшается сверх установленных порогов.', 'seed_v1', 'approved'
);

INSERT INTO questions (topic_id, type, difficulty, body, options_json, correct_key, correct_answer, tolerance_pct, explanation, source, status) VALUES (
    3, 'numeric', 3, 'Sponsor вложил $100m equity, купил компанию с Entry EV/EBITDA=8x при EBITDA=$50m (Entry EV=$400m, Debt=$300m). Через 5 лет EBITDA выросла до $70m, долг погашен до $150m, Exit EV/EBITDA тот же 8x. Посчитай Exit Equity Value (в млн $).',
    NULL, NULL, '410', 2,
    'Exit EV = 70 × 8 = 560 млн $. Exit Equity Value = Exit EV − Debt = 560 − 150 = 410 млн $.', 'seed_v1', 'approved'
);

INSERT INTO questions (topic_id, type, difficulty, body, options_json, correct_key, correct_answer, tolerance_pct, explanation, source, status) VALUES (
    3, 'open', 3, 'Почему PE-фонды часто проводят add-on acquisitions (bolt-on) после первичной LBO-покупки?',
    NULL, NULL, NULL, NULL,
    'Add-on приобретения меньших компаний в ту же платформу позволяют реализовать синергии и рост выручки/EBITDA быстрее органического роста, а также часто покупаются по более низкому мультипликатору, чем у платформы (multiple arbitrage) - после консолидации объединённая EBITDA может быть переоценена по более высокому «платформенному» мультипликатору на выходе.', 'seed_v1', 'approved'
);

INSERT INTO questions (topic_id, type, difficulty, body, options_json, correct_key, correct_answer, tolerance_pct, explanation, source, status) VALUES (
    3, 'open', 2, 'Чем LBO-модель принципиально отличается от DCF-модели по цели построения?',
    NULL, NULL, NULL, NULL,
    'DCF оценивает справедливую (intrinsic) стоимость бизнеса на основе прогнозируемых денежных потоков. LBO-модель отвечает на вопрос «какую максимальную цену может заплатить финансовый покупатель, чтобы получить требуемую доходность (IRR/MOIC) при заданной структуре финансирования и горизонте выхода» - то есть это модель доходности инвестора, а не оценки бизнеса.', 'seed_v1', 'approved'
);

INSERT INTO questions (topic_id, type, difficulty, body, options_json, correct_key, correct_answer, tolerance_pct, explanation, source, status) VALUES (
    4, 'open', 2, 'Как увеличение амортизации (D&A) на $10 влияет на три финансовых отчёта (при ставке налога t)?',
    NULL, NULL, NULL, NULL,
    'P&L: операционная прибыль (EBIT) снижается на $10, чистая прибыль - на $10×(1−t). Cash Flow Statement: чистая прибыль корректируется обратно добавлением D&A (+$10, non-cash статья), итоговое изменение денежного потока = +$10×t (экономия на налогах). Balance Sheet: накопленная амортизация растёт на $10 (PP&E net снижается), денежные средства растут на $10×t, retained earnings снижается на величину чистой прибыли.', 'seed_v1', 'approved'
);

INSERT INTO questions (topic_id, type, difficulty, body, options_json, correct_key, correct_answer, tolerance_pct, explanation, source, status) VALUES (
    4, 'open', 2, 'Почему рост Accounts Receivable снижает операционный денежный поток, хотя выручка та же?',
    NULL, NULL, NULL, NULL,
    'Рост AR означает, что компания признала выручку (по методу начисления), но ещё не получила деньги от клиентов - часть выручки «заморожена» в дебиторской задолженности. В Cash Flow Statement это отражается как отрицательная корректировка, поскольку реального денежного притока по этой сумме ещё не было.', 'seed_v1', 'approved'
);

INSERT INTO questions (topic_id, type, difficulty, body, options_json, correct_key, correct_answer, tolerance_pct, explanation, source, status) VALUES (
    4, 'mcq', 2, 'Какая статья НЕ входит в расчёт Net Working Capital в классическом определении для DCF/LBO моделей?',
    '[{"key": "A", "text": "Accounts Receivable"}, {"key": "B", "text": "Inventory"}, {"key": "C", "text": "Cash & Cash Equivalents"}, {"key": "D", "text": "Accounts Payable"}]', 'C', NULL, NULL,
    'Cash обычно исключают из операционного NWC, так как это финансовый, а не операционный актив (управляется отдельно как часть капитальной структуры).', 'seed_v1', 'approved'
);

INSERT INTO questions (topic_id, type, difficulty, body, options_json, correct_key, correct_answer, tolerance_pct, explanation, source, status) VALUES (
    4, 'open', 3, 'Как связаны между собой три финансовых отчёта (P&L, Balance Sheet, Cash Flow Statement)?',
    NULL, NULL, NULL, NULL,
    'P&L формирует Net Income, который является отправной точкой Cash Flow Statement (операционный раздел) и одновременно пополняет Retained Earnings в Balance Sheet. Cash Flow Statement объясняет изменение денежных средств на балансе между двумя периодами (операционная + инвестиционная + финансовая деятельность). Balance Sheet на конец периода должен соблюдать Assets = Liabilities + Equity.', 'seed_v1', 'approved'
);

INSERT INTO questions (topic_id, type, difficulty, body, options_json, correct_key, correct_answer, tolerance_pct, explanation, source, status) VALUES (
    4, 'open', 2, 'В чём разница между операционным (operating) и финансовым (finance/capital) лизингом с точки зрения влияния на баланс до перехода на IFRS 16 / ASC 842?',
    NULL, NULL, NULL, NULL,
    'До новых стандартов operating lease не отражался на балансе (off-balance-sheet financing) - платежи шли как операционные расходы в P&L. Finance/capital lease признавался на балансе как актив (право пользования) и обязательство, с амортизацией актива и процентными расходами по обязательству. После IFRS 16/ASC 842 (2019) большинство операционных лизингов тоже выводятся на баланс.', 'seed_v1', 'approved'
);

INSERT INTO questions (topic_id, type, difficulty, body, options_json, correct_key, correct_answer, tolerance_pct, explanation, source, status) VALUES (
    4, 'numeric', 1, 'Выручка компании $200m, себестоимость (COGS) $120m. Посчитай Gross Margin в процентах.',
    NULL, NULL, '40', 0.5,
    'Gross Margin = (200 − 120) / 200 = 0.40 = 40%.', 'seed_v1', 'approved'
);

INSERT INTO questions (topic_id, type, difficulty, body, options_json, correct_key, correct_answer, tolerance_pct, explanation, source, status) VALUES (
    4, 'open', 3, 'Почему увеличение Deferred Tax Liability добавляется обратно в Cash Flow Statement?',
    NULL, NULL, NULL, NULL,
    'DTL возникает, когда налог, начисленный по бухгалтерским правилам (book tax expense в P&L), больше налога, реально уплаченного по налоговым правилам (например, из-за ускоренной налоговой амортизации). Разница - non-cash расход, уменьшивший Net Income, но не являющийся реальным оттоком денег в этом периоде, поэтому её прибавляют обратно при переходе от Net Income к операционному денежному потоку.', 'seed_v1', 'approved'
);

INSERT INTO questions (topic_id, type, difficulty, body, options_json, correct_key, correct_answer, tolerance_pct, explanation, source, status) VALUES (
    4, 'open', 2, 'Чем EBIT отличается от EBITDA и когда предпочтительнее использовать каждый из них?',
    NULL, NULL, NULL, NULL,
    'EBIT = Net Income + Interest + Taxes (прибыль до процентов и налогов, но после D&A). EBITDA = EBIT + D&A. EBITDA часто используют как прокси операционного денежного потока и для сравнения капиталоёмких компаний с разной учётной политикой амортизации. EBIT предпочтительнее, когда важно учесть реальные капитальные затраты бизнеса, для которого D&A отражает реальный износ активов, требующих регулярной замены.', 'seed_v1', 'approved'
);

INSERT INTO questions (topic_id, type, difficulty, body, options_json, correct_key, correct_answer, tolerance_pct, explanation, source, status) VALUES (
    5, 'open', 2, 'Что такое accretion/dilution анализ и что он показывает?',
    NULL, NULL, NULL, NULL,
    'Accretion/dilution анализ сравнивает pro forma EPS объединённой компании после сделки со standalone EPS покупателя до сделки. Если pro forma EPS выше - сделка accretive (прирастающая), если ниже - dilutive (размывающая). Это один из ключевых индикаторов, которым отчитывается покупатель перед своими акционерами при анонсе сделки.', 'seed_v1', 'approved'
);

INSERT INTO questions (topic_id, type, difficulty, body, options_json, correct_key, correct_answer, tolerance_pct, explanation, source, status) VALUES (
    5, 'open', 3, 'От чего в первую очередь зависит, будет ли сделка accretive или dilutive при финансировании акциями (stock deal)?',
    NULL, NULL, NULL, NULL,
    'В первую очередь - от соотношения P/E покупателя и P/E цели (плюс синергии). Если покупатель платит P/E ниже своего собственного P/E, сделка обычно accretive; если платит P/E выше своего - обычно dilutive при прочих равных, потому что новые акции, выпущенные для оплаты сделки, размывают базу EPS сильнее, чем добавленная прибыль цели.', 'seed_v1', 'approved'
);

INSERT INTO questions (topic_id, type, difficulty, body, options_json, correct_key, correct_answer, tolerance_pct, explanation, source, status) VALUES (
    5, 'mcq', 2, 'Что из перечисленного увеличивает вероятность того, что сделка окажется accretive при кэш-финансировании (all-cash deal)?',
    '[{"key": "A", "text": "Высокая стоимость заёмного финансирования сделки"}, {"key": "B", "text": "Низкая cost of debt относительно earnings yield цели (E/P)"}, {"key": "C", "text": "Высокая цена премии к цели"}, {"key": "D", "text": "Отсутствие синергий"}]', 'B', NULL, NULL,
    'При cash deal EPS-эффект зависит от сравнения стоимости долга, привлечённого для покупки, с доходностью (earnings yield = E/P) приобретаемой компании - если earnings yield цели выше стоимости долга, сделка обычно accretive.', 'seed_v1', 'approved'
);

INSERT INTO questions (topic_id, type, difficulty, body, options_json, correct_key, correct_answer, tolerance_pct, explanation, source, status) VALUES (
    5, 'open', 2, 'В чём разница между stock deal и cash deal с точки зрения риска для акционеров покупателя?',
    NULL, NULL, NULL, NULL,
    'В cash deal акционеры покупателя платят фиксированную сумму и полностью сохраняют экономику будущего апсайда/риска объединённой компании, но покупатель принимает на себя риск финансирования (обычно через долг). В stock deal акционеры цели получают акции покупателя и разделяют будущий риск и апсайд сделки вместе с существующими акционерами покупателя, а акционеры покупателя размываются в доле компании.', 'seed_v1', 'approved'
);

INSERT INTO questions (topic_id, type, difficulty, body, options_json, correct_key, correct_answer, tolerance_pct, explanation, source, status) VALUES (
    5, 'open', 2, 'Что такое synergies в M&A и на какие два типа их обычно делят?',
    NULL, NULL, NULL, NULL,
    'Synergies - дополнительная стоимость, возникающая от объединения двух компаний сверх суммы их standalone стоимостей. Делят на: (1) revenue synergies - рост совместных продаж, обычно более неопределённые и медленно реализуемые; (2) cost synergies - снижение издержек (устранение дублирующих функций, экономия на масштабе), обычно более предсказуемые и быстрее реализуемые, поэтому именно на них чаще фокусируются при обосновании цены сделки.', 'seed_v1', 'approved'
);

INSERT INTO questions (topic_id, type, difficulty, body, options_json, correct_key, correct_answer, tolerance_pct, explanation, source, status) VALUES (
    5, 'open', 3, 'Почему покупатель в сделке M&A обычно платит премию к текущей рыночной цене акций цели?',
    NULL, NULL, NULL, NULL,
    'Премия компенсирует существующим акционерам цели отказ от будущего самостоятельного апсайда и убеждает совет директоров/акционеров одобрить сделку (control premium). Она также отражает ожидаемые синергии, которыми покупатель готов частично поделиться, чтобы сделка состоялась, а не досталась конкурирующему покупателю на аукционе.', 'seed_v1', 'approved'
);

INSERT INTO questions (topic_id, type, difficulty, body, options_json, correct_key, correct_answer, tolerance_pct, explanation, source, status) VALUES (
    5, 'open', 3, 'Чем asset deal отличается от stock deal (share deal) с точки зрения покупателя, и как это связано с обязательствами компании?',
    NULL, NULL, NULL, NULL,
    'В asset deal покупатель приобретает выбранные активы (и, опционально, отдельные обязательства) напрямую, оставляя юридическое лицо продавцу - это позволяет избежать принятия на себя неизвестных/непрофильных обязательств и часто даёт налоговые преимущества (step-up базы активов для будущей амортизации). В stock deal покупатель приобретает акции юрлица целиком, автоматически принимая на себя все его активы и обязательства, включая непредвиденные (contingent liabilities), что требует более тщательного due diligence.', 'seed_v1', 'approved'
);

INSERT INTO questions (topic_id, type, difficulty, body, options_json, correct_key, correct_answer, tolerance_pct, explanation, source, status) VALUES (
    5, 'numeric', 3, 'Компания-покупатель имеет 100m акций и Net Income $200m (EPS=$2). Она покупает компанию-цель за $500m исключительно акциями по своей текущей цене $40/акцию (выпускает 12.5m новых акций). Net Income цели - $30m, синергий нет. Посчитай pro forma EPS объединённой компании (в $, округли до сотых).',
    NULL, NULL, '2.04', 1,
    'Pro forma Net Income = 200 + 30 = 230 млн $. Pro forma число акций = 100 + 12.5 = 112.5m. Pro forma EPS = 230 / 112.5 = 2.04 $. Сделка accretive (2.04 > 2.00), что согласуется с тем, что покупатель платит за цель P/E = 500/30 ≈ 16.7x - ниже своего собственного P/E = 4000/200 = 20x.', 'seed_v1', 'approved'
);
