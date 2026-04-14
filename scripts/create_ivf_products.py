#!/usr/bin/env python3
"""Create IVF products on Shopify.

These are prescription-only products available in physical pharmacies only.
Products are created with inventory=0 and deny overselling, so the storefront
shows them as informational pages (no Add to Cart). Assign the "ivf" product
template in Shopify Admin after creation.

Usage:
    python scripts/create_ivf_products.py --dry-run
    python scripts/create_ivf_products.py
    python scripts/create_ivf_products.py --collection-only
"""
from __future__ import annotations

import sys
import time
from pathlib import Path

# Project root on sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.common.cli import base_parser, init_logging, shopify_client_from_env

# ---------------------------------------------------------------------------
# Product data — add new products here
# ---------------------------------------------------------------------------

IVF_PRODUCTS: list[dict] = [
    {
        "title": "ГОНАЛ-F ПЕН 900 IU инжекционен разтвор в предварително напълнена писалка",
        "vendor": "Merck Serono",
        "product_type": "Лекарства",
        "tags": ["ivf", "само-в-аптека", "рецептурно", "Безплодие", "Гинекология"],
        "body_html": """
<div class="ivf-product-info">
  <p><strong>GONAL-f 900 IU/1,44 ml</strong> — инжекционен разтвор в предварително напълнена писалка, съдържащ <strong>фолитропин алфа</strong> (рекомбинантен фоликулостимулиращ хормон, FSH).</p>

  <h3>За какво се използва</h3>
  <ul>
    <li>Стимулиране на овулация при жени, които не овулират и не са се повлияли от кломифен цитрат</li>
    <li>Заедно с лутропин алфа (LH) — при жени с много ниски нива на FSH и LH</li>
    <li>Развитие на множество фоликули при асистирани репродуктивни технологии (IVF, GIFT, ZIFT)</li>
    <li>При мъже — заедно с hCG за стимулиране на сперматогенезата</li>
  </ul>

  <h3>Активно вещество</h3>
  <p>Фолитропин алфа (follitropin alfa) — 900 IU (66 микрограма) в 1,44 ml разтвор.</p>

  <h3>Начин на приложение</h3>
  <p>Подкожна инжекция. Предварително напълнената писалка позволява многократни инжекции с дозиране на стъпки от 12,5 IU. Максимална единична доза: 450 IU.</p>

  <h3>Съхранение</h3>
  <p>В хладилник (2°C–8°C). След отваряне — до 28 дни при температура 2°C–25°C.</p>

  <h3>Производител</h3>
  <p>Merck Serono S.p.A., Италия. Притежател на разрешението: Merck Europe B.V., Нидерландия.</p>

  <p><em>Това е лекарствен продукт с рецепта. Използвайте само по лекарско предписание.</em></p>
</div>
""",
        "images": [
            {"src": "https://static.framar.bg/product/fr-gonal-f-inzhektsionen-raztvor-v-predvaritelno-napalnena-pisalka-png.jpg"}
        ],
        # Price placeholder — user will set their own
        "variants": [
            {
                "price": "0.00",
                "sku": "GONAL-F-900",
                "inventory_management": "shopify",
                "inventory_policy": "deny",
                "inventory_quantity": 0,
                "requires_shipping": False,
            }
        ],
    },
    {
        "title": "ПРОЛУТЕКС 25 мг инжекционен разтвор — 7 предварително напълнени спринцовки",
        "vendor": "IBSA Farmaceutici",
        "product_type": "Лекарства",
        "tags": ["ivf", "само-в-аптека", "рецептурно", "Безплодие", "Гинекология"],
        "body_html": """
<div class="ivf-product-info">
  <p><strong>Пролутекс 25 mg</strong> — инжекционен разтвор в предварително напълнена спринцовка, съдържащ <strong>прогестерон</strong> — естествен женски полов хормон.</p>

  <h3>За какво се използва</h3>
  <ul>
    <li>Лутеална поддръжка при програми за асистирана репродукция (IVF/АРТ)</li>
    <li>Действа върху лигавицата на матката — помага за забременяване и поддържане на бременност в ранните етапи</li>
    <li>Предназначен за жени, които не могат да използват или не понасят вагинални прогестеронови препарати</li>
  </ul>

  <h3>Активно вещество</h3>
  <p>Прогестерон (progesterone) — 25 mg във всеки флакон (1,112 ml разтвор; концентрация 22,48 mg/ml).</p>
  <p>Други съставки: хидроксипропилбетадекс, динатриев фосфат, натриев дихидроген фосфат дихидрат, вода за инжекции.</p>

  <h3>Дозировка и начин на приложение</h3>
  <p>По 25 mg веднъж дневно, обикновено до 12-та седмица на потвърдена бременност (около 10-седмично лечение). Прилага се:</p>
  <ul>
    <li><strong>Подкожно</strong> (в областта на корема или предната част на бедрото)</li>
    <li><strong>Мускулно</strong> — само от лекар или медицински специалист</li>
  </ul>
  <p>Всеки флакон е само за еднократна употреба. Използва се само под наблюдението на лекар с опит в лечението на проблеми с фертилитета.</p>

  <h3>Съхранение</h3>
  <ul>
    <li>Да се съхранява под 25°C</li>
    <li>Да <strong>не</strong> се съхранява в хладилник или замразява</li>
    <li>В оригиналната опаковка, защитена от светлина</li>
    <li>Да се използва веднага след първото отваряне</li>
  </ul>

  <h3>Опаковка</h3>
  <p>Бистър безцветен разтвор във флакон от безцветно стъкло. Опаковки от 1, 7 или 14 флакона.</p>

  <h3>Производител</h3>
  <p>IBSA Farmaceutici Italia S.r.l., Via Martiri di Cefalonia 2, 26900 Lodi, Италия.</p>

  <p><em>Това е лекарствен продукт с рецепта. Използвайте само по лекарско предписание. Информацията е съгласно одобрената от ИАЛ кратка характеристика на продукта.</em></p>
</div>
""",
        "images": [
            {"src": "https://static.framar.bg/product/prolutex-solution.jpg"}
        ],
        "variants": [
            {
                "price": "0.00",
                "sku": "PROLUTEX-25-7",
                "inventory_management": "shopify",
                "inventory_policy": "deny",
                "inventory_quantity": 0,
                "requires_shipping": False,
            }
        ],
    },
    # ------------------------------------------------------------------
    # Pergoveris 900 IU / 450 IU (top revenue IVF product)
    # Source: EMA EPAR product information (Bulgarian)
    # ------------------------------------------------------------------
    {
        "title": "ПЕРГОВЕРИС 900 IU/450 IU инжекционен разтвор в предварително напълнена писалка",
        "vendor": "Merck Serono",
        "product_type": "Лекарства",
        "tags": ["ivf", "само-в-аптека", "рецептурно", "Безплодие", "Гинекология"],
        "body_html": """
<div class="ivf-product-info">
  <p><strong>Перговерис (900 IU + 450 IU)/1,44 ml</strong> — инжекционен разтвор в предварително напълнена писалка, съдържащ две активни вещества: <strong>фолитропин алфа</strong> (рекомбинантен FSH) и <strong>лутропин алфа</strong> (рекомбинантен LH).</p>

  <h3>За какво се използва</h3>
  <ul>
    <li>Стимулиране на развитието на фоликулите при жени с тежък дефицит на FSH и LH</li>
    <li>Прилага се при жени, при които лечението само с FSH не е дало достатъчен резултат</li>
    <li>Използва се в програми за асистирана репродукция (IVF/АРТ)</li>
  </ul>

  <h3>Активни вещества</h3>
  <p>Фолитропин алфа — 900 IU (66 µg) + лутропин алфа — 450 IU (18 µg) в 1,44 ml разтвор.</p>

  <h3>Начин на приложение</h3>
  <p>Подкожна инжекция. Писалката позволява многократни инжекции с прецизно дозиране. Лечението се провежда под наблюдението на лекар с опит в лечението на безплодие.</p>

  <h3>Съхранение</h3>
  <p>В хладилник (2°C–8°C). Да не се замразява. След първо отваряне — до 28 дни при температура не по-висока от 25°C.</p>

  <h3>Производител</h3>
  <p>Merck Serono S.p.A., Италия. Притежател на разрешението: Merck Europe B.V., Нидерландия.</p>

  <p><em>Това е лекарствен продукт с рецепта. Използвайте само по лекарско предписание. Информацията е съгласно одобрената от EMA кратка характеристика на продукта.</em></p>
</div>
""",
        "images": [],
        "variants": [
            {
                "price": "0.00",
                "sku": "PERGOVERIS-900-450",
                "inventory_management": "shopify",
                "inventory_policy": "deny",
                "inventory_quantity": 0,
                "requires_shipping": False,
            }
        ],
    },
    # ------------------------------------------------------------------
    # Pergoveris 300 IU / 150 IU
    # ------------------------------------------------------------------
    {
        "title": "ПЕРГОВЕРИС 300 IU/150 IU инжекционен разтвор в предварително напълнена писалка",
        "vendor": "Merck Serono",
        "product_type": "Лекарства",
        "tags": ["ivf", "само-в-аптека", "рецептурно", "Безплодие", "Гинекология"],
        "body_html": """
<div class="ivf-product-info">
  <p><strong>Перговерис (300 IU + 150 IU)/0,48 ml</strong> — инжекционен разтвор в предварително напълнена писалка, съдържащ <strong>фолитропин алфа</strong> (рекомбинантен FSH) и <strong>лутропин алфа</strong> (рекомбинантен LH).</p>

  <h3>За какво се използва</h3>
  <ul>
    <li>Стимулиране на развитието на фоликулите при жени с тежък дефицит на FSH и LH</li>
    <li>Прилага се при жени, при които лечението само с FSH не е дало достатъчен резултат</li>
    <li>Използва се в програми за асистирана репродукция (IVF/АРТ)</li>
  </ul>

  <h3>Активни вещества</h3>
  <p>Фолитропин алфа — 300 IU (22 µg) + лутропин алфа — 150 IU (6 µg) в 0,48 ml разтвор.</p>

  <h3>Начин на приложение</h3>
  <p>Подкожна инжекция. Писалката е предназначена за еднократна употреба. Лечението се провежда под наблюдението на лекар с опит в лечението на безплодие.</p>

  <h3>Съхранение</h3>
  <p>В хладилник (2°C–8°C). Да не се замразява. След първо отваряне — да се използва веднага.</p>

  <h3>Производител</h3>
  <p>Merck Serono S.p.A., Италия. Притежател на разрешението: Merck Europe B.V., Нидерландия.</p>

  <p><em>Това е лекарствен продукт с рецепта. Използвайте само по лекарско предписание. Информацията е съгласно одобрената от EMA кратка характеристика на продукта.</em></p>
</div>
""",
        "images": [],
        "variants": [
            {
                "price": "0.00",
                "sku": "PERGOVERIS-300-150",
                "inventory_management": "shopify",
                "inventory_policy": "deny",
                "inventory_quantity": 0,
                "requires_shipping": False,
            }
        ],
    },
    # ------------------------------------------------------------------
    # Мериоферт 150 IU
    # Source: IBSA product info, BDA
    # ------------------------------------------------------------------
    {
        "title": "МЕРИОФЕРТ 150 IU прах и разтворител за инжекционен разтвор",
        "vendor": "IBSA Farmaceutici",
        "product_type": "Лекарства",
        "tags": ["ivf", "само-в-аптека", "рецептурно", "Безплодие", "Гинекология"],
        "body_html": """
<div class="ivf-product-info">
  <p><strong>Мериоферт 150 IU</strong> — прах и разтворител за инжекционен разтвор, съдържащ <strong>менотропин</strong> (високопречистен човешки менопаузален гонадотропин, HMG) с FSH и LH активност.</p>

  <h3>За какво се използва</h3>
  <ul>
    <li>Стимулиране на овулация при жени с ановулация (включително синдром на поликистозните яйчници)</li>
    <li>Контролирана овариална хиперстимулация при програми за асистирана репродукция (IVF/ICSI)</li>
    <li>Стимулиране на сперматогенезата при мъже с хипогонадотропен хипогонадизъм (заедно с hCG)</li>
  </ul>

  <h3>Активно вещество</h3>
  <p>Менотропин (menotrophin) — 150 IU FSH активност и 150 IU LH активност на флакон.</p>

  <h3>Начин на приложение</h3>
  <p>Подкожна или мускулна инжекция. Прахът се разтваря в приложения разтворител непосредствено преди инжектиране.</p>

  <h3>Съхранение</h3>
  <p>Под 25°C. Да не се замразява. В оригиналната опаковка, защитена от светлина.</p>

  <h3>Производител</h3>
  <p>IBSA Farmaceutici Italia S.r.l., Lodi, Италия. IBSA Institut Biochimique SA, Лугано, Швейцария.</p>

  <p><em>Това е лекарствен продукт с рецепта. Използвайте само по лекарско предписание.</em></p>
</div>
""",
        "images": [],
        "variants": [
            {
                "price": "0.00",
                "sku": "MERIOFERT-150",
                "inventory_management": "shopify",
                "inventory_policy": "deny",
                "inventory_quantity": 0,
                "requires_shipping": False,
            }
        ],
    },
    # ------------------------------------------------------------------
    # Цетротид 0.25 mg
    # Source: EMA EPAR (Cetrotide), centralized authorization
    # ------------------------------------------------------------------
    {
        "title": "ЦЕТРОТИД 0,25 мг прах и разтворител за инжекционен разтвор",
        "vendor": "Merck Serono",
        "product_type": "Лекарства",
        "tags": ["ivf", "само-в-аптека", "рецептурно", "Безплодие", "Гинекология"],
        "body_html": """
<div class="ivf-product-info">
  <p><strong>Цетротид 0,25 mg</strong> — прах и разтворител за инжекционен разтвор, съдържащ <strong>цетрореликс</strong> — антагонист на гонадотропин-освобождаващия хормон (GnRH).</p>

  <h3>За какво се използва</h3>
  <ul>
    <li>Предотвратяване на преждевременна овулация при контролирана овариална стимулация</li>
    <li>Прилага се в програми за асистирана репродукция (IVF/ICSI)</li>
    <li>Блокира действието на естествения GnRH, което предотвратява преждевременното освобождаване на яйцеклетките</li>
  </ul>

  <h3>Активно вещество</h3>
  <p>Цетрореликс (cetrorelix) — 0,25 mg на флакон (като цетрореликс ацетат).</p>

  <h3>Начин на приложение</h3>
  <p>Подкожна инжекция в долната коремна стена. Прилага се веднъж дневно на всеки 24 часа, сутрин или вечер.</p>

  <h3>Съхранение</h3>
  <p>Под 25°C. В оригиналната опаковка, защитена от светлина. Неразтвореният прах може да се съхранява при стайна температура (до 30°C) за период до 3 месеца.</p>

  <h3>Производител</h3>
  <p>Merck Healthcare KGaA, Дармщат, Германия. Притежател на разрешението: Merck Europe B.V., Нидерландия.</p>

  <p><em>Това е лекарствен продукт с рецепта. Използвайте само по лекарско предписание. Информацията е съгласно одобрената от EMA кратка характеристика на продукта.</em></p>
</div>
""",
        "images": [],
        "variants": [
            {
                "price": "0.00",
                "sku": "CETROTIDE-025",
                "inventory_management": "shopify",
                "inventory_policy": "deny",
                "inventory_quantity": 0,
                "requires_shipping": False,
            }
        ],
    },
    # ------------------------------------------------------------------
    # Гонал-F ПЕН 300 IU
    # Source: EMA EPAR (Gonal-f)
    # ------------------------------------------------------------------
    {
        "title": "ГОНАЛ-F ПЕН 300 IU инжекционен разтвор в предварително напълнена писалка",
        "vendor": "Merck Serono",
        "product_type": "Лекарства",
        "tags": ["ivf", "само-в-аптека", "рецептурно", "Безплодие", "Гинекология"],
        "body_html": """
<div class="ivf-product-info">
  <p><strong>GONAL-f 300 IU/0,5 ml</strong> — инжекционен разтвор в предварително напълнена писалка, съдържащ <strong>фолитропин алфа</strong> (рекомбинантен фоликулостимулиращ хормон, FSH).</p>

  <h3>За какво се използва</h3>
  <ul>
    <li>Стимулиране на овулация при жени, които не овулират и не са се повлияли от кломифен цитрат</li>
    <li>Заедно с лутропин алфа (LH) — при жени с много ниски нива на FSH и LH</li>
    <li>Развитие на множество фоликули при асистирани репродуктивни технологии (IVF, GIFT, ZIFT)</li>
    <li>При мъже — заедно с hCG за стимулиране на сперматогенезата</li>
  </ul>

  <h3>Активно вещество</h3>
  <p>Фолитропин алфа (follitropin alfa) — 300 IU (22 микрограма) в 0,5 ml разтвор.</p>

  <h3>Начин на приложение</h3>
  <p>Подкожна инжекция. Писалката позволява многократни инжекции с дозиране на стъпки от 12,5 IU.</p>

  <h3>Съхранение</h3>
  <p>В хладилник (2°C–8°C). След отваряне — до 28 дни при температура 2°C–25°C.</p>

  <h3>Производител</h3>
  <p>Merck Serono S.p.A., Италия. Притежател на разрешението: Merck Europe B.V., Нидерландия.</p>

  <p><em>Това е лекарствен продукт с рецепта. Използвайте само по лекарско предписание. Информацията е съгласно одобрената от EMA кратка характеристика на продукта.</em></p>
</div>
""",
        "images": [],
        "variants": [
            {
                "price": "0.00",
                "sku": "GONAL-F-300",
                "inventory_management": "shopify",
                "inventory_policy": "deny",
                "inventory_quantity": 0,
                "requires_shipping": False,
            }
        ],
    },
    # ------------------------------------------------------------------
    # Гонал-F ПЕН 450 IU
    # ------------------------------------------------------------------
    {
        "title": "ГОНАЛ-F ПЕН 450 IU инжекционен разтвор в предварително напълнена писалка",
        "vendor": "Merck Serono",
        "product_type": "Лекарства",
        "tags": ["ivf", "само-в-аптека", "рецептурно", "Безплодие", "Гинекология"],
        "body_html": """
<div class="ivf-product-info">
  <p><strong>GONAL-f 450 IU/0,75 ml</strong> — инжекционен разтвор в предварително напълнена писалка, съдържащ <strong>фолитропин алфа</strong> (рекомбинантен фоликулостимулиращ хормон, FSH).</p>

  <h3>За какво се използва</h3>
  <ul>
    <li>Стимулиране на овулация при жени, които не овулират и не са се повлияли от кломифен цитрат</li>
    <li>Заедно с лутропин алфа (LH) — при жени с много ниски нива на FSH и LH</li>
    <li>Развитие на множество фоликули при асистирани репродуктивни технологии (IVF, GIFT, ZIFT)</li>
    <li>При мъже — заедно с hCG за стимулиране на сперматогенезата</li>
  </ul>

  <h3>Активно вещество</h3>
  <p>Фолитропин алфа (follitropin alfa) — 450 IU (33 микрограма) в 0,75 ml разтвор.</p>

  <h3>Начин на приложение</h3>
  <p>Подкожна инжекция. Писалката позволява многократни инжекции с дозиране на стъпки от 12,5 IU. Максимална единична доза: 450 IU.</p>

  <h3>Съхранение</h3>
  <p>В хладилник (2°C–8°C). След отваряне — до 28 дни при температура 2°C–25°C.</p>

  <h3>Производител</h3>
  <p>Merck Serono S.p.A., Италия. Притежател на разрешението: Merck Europe B.V., Нидерландия.</p>

  <p><em>Това е лекарствен продукт с рецепта. Използвайте само по лекарско предписание. Информацията е съгласно одобрената от EMA кратка характеристика на продукта.</em></p>
</div>
""",
        "images": [],
        "variants": [
            {
                "price": "0.00",
                "sku": "GONAL-F-450",
                "inventory_management": "shopify",
                "inventory_policy": "deny",
                "inventory_quantity": 0,
                "requires_shipping": False,
            }
        ],
    },
    # ------------------------------------------------------------------
    # Овитрел 250 mcg
    # Source: EMA EPAR (Ovitrelle)
    # ------------------------------------------------------------------
    {
        "title": "ОВИТРЕЛ 250 микрограма инжекционен разтвор в предварително напълнена спринцовка",
        "vendor": "Merck Serono",
        "product_type": "Лекарства",
        "tags": ["ivf", "само-в-аптека", "рецептурно", "Безплодие", "Гинекология"],
        "body_html": """
<div class="ivf-product-info">
  <p><strong>Овитрел 250 µg/0,5 ml</strong> — инжекционен разтвор в предварително напълнена спринцовка, съдържащ <strong>хориогонадотропин алфа</strong> (рекомбинантен човешки хорионгонадотропин, r-hCG).</p>

  <h3>За какво се използва</h3>
  <ul>
    <li>Предизвикване на финалното узряване на фоликулите и овулация след стимулация с гонадотропини (FSH, HMG)</li>
    <li>Тригер за овулация при асистирана репродукция (IVF/ICSI) — прилага се 24–48 часа преди пункция на яйцеклетките</li>
    <li>Предизвикване на овулация и лутеинизация при ановулаторни или олиговулаторни жени след стимулация на растежа на фоликулите</li>
  </ul>

  <h3>Активно вещество</h3>
  <p>Хориогонадотропин алфа (choriogonadotropin alfa) — 250 микрограма (приблизително 6 500 IU) в 0,5 ml разтвор.</p>

  <h3>Начин на приложение</h3>
  <p>Подкожна инжекция. Прилага се еднократно.</p>

  <h3>Съхранение</h3>
  <p>В хладилник (2°C–8°C). Да не се замразява. В оригиналната опаковка, защитена от светлина.</p>

  <h3>Производител</h3>
  <p>Merck Serono S.p.A., Италия. Притежател на разрешението: Merck Europe B.V., Нидерландия.</p>

  <p><em>Това е лекарствен продукт с рецепта. Използвайте само по лекарско предписание. Информацията е съгласно одобрената от EMA кратка характеристика на продукта.</em></p>
</div>
""",
        "images": [],
        "variants": [
            {
                "price": "0.00",
                "sku": "OVITRELLE-250",
                "inventory_management": "shopify",
                "inventory_policy": "deny",
                "inventory_quantity": 0,
                "requires_shipping": False,
            }
        ],
    },
    # ------------------------------------------------------------------
    # Кринон 8% вагинален гел
    # Source: SmPC (medicines.org.uk / EMA)
    # ------------------------------------------------------------------
    {
        "title": "КРИНОН 8% вагинален гел — 15 апликатора",
        "vendor": "Merck Serono",
        "product_type": "Лекарства",
        "tags": ["ivf", "само-в-аптека", "рецептурно", "Безплодие", "Гинекология"],
        "body_html": """
<div class="ivf-product-info">
  <p><strong>Кринон 8%</strong> — вагинален гел, съдържащ <strong>прогестерон</strong> (90 mg на апликатор) в система за контролирано освобождаване.</p>

  <h3>За какво се използва</h3>
  <ul>
    <li>Лутеална поддръжка при програми за асистирана репродукция (IVF/АРТ)</li>
    <li>Допълване на прогестерон при жени с недостатъчност на жълтото тяло</li>
    <li>Поддържане на ранна бременност след ембриотрансфер</li>
  </ul>

  <h3>Активно вещество</h3>
  <p>Прогестерон (progesterone) — 90 mg на апликатор (8% гел, 1,125 g). Системата Polycarbophil осигурява контролирано освобождаване на прогестерона.</p>

  <h3>Начин на приложение</h3>
  <p>Вагинално. По 1 апликатор (90 mg) веднъж дневно, обикновено от деня на ембриотрансфер. Всеки апликатор е за еднократна употреба.</p>

  <h3>Съхранение</h3>
  <p>Под 25°C. Да не се замразява.</p>

  <h3>Производител</h3>
  <p>Fleet Laboratories Ltd., Великобритания (за Merck Serono).</p>

  <p><em>Това е лекарствен продукт с рецепта. Използвайте само по лекарско предписание.</em></p>
</div>
""",
        "images": [],
        "variants": [
            {
                "price": "0.00",
                "sku": "CRINONE-8-15",
                "inventory_management": "shopify",
                "inventory_policy": "deny",
                "inventory_quantity": 0,
                "requires_shipping": False,
            }
        ],
    },
    # ------------------------------------------------------------------
    # Утрогестан 200 mg (sold as "300mg" = 3x200mg/day regimen)
    # Source: SmPC (medicines.org.uk), Besins Healthcare
    # ------------------------------------------------------------------
    {
        "title": "УТРОГЕСТАН 200 мг меки вагинални капсули",
        "vendor": "Besins Healthcare",
        "product_type": "Лекарства",
        "tags": ["ivf", "само-в-аптека", "рецептурно", "Безплодие", "Гинекология"],
        "body_html": """
<div class="ivf-product-info">
  <p><strong>Утрогестан 200 mg</strong> — меки капсули за вагинално приложение, съдържащи <strong>микронизиран прогестерон</strong> — естествен женски полов хормон.</p>

  <h3>За какво се използва</h3>
  <ul>
    <li>Лутеална поддръжка при програми за асистирана репродукция (IVF/АРТ) — обичайна доза 600 mg дневно (3 × 200 mg)</li>
    <li>Превенция на преждевременно раждане при жени с къса шийка на матката</li>
    <li>Допълване на прогестерон при лутеална недостатъчност</li>
  </ul>

  <h3>Активно вещество</h3>
  <p>Микронизиран прогестерон (progesterone) — 200 mg на капсула.</p>
  <p>Други съставки: слънчогледово масло, соев лецитин. Обвивка: желатин, глицерол, титанов диоксид (E171).</p>

  <h3>Начин на приложение</h3>
  <p>Вагинално. При IVF: по 200 mg три пъти дневно (сутрин, обяд и вечер), от деня на ембриотрансфер.</p>

  <h3>Съхранение</h3>
  <p>Не изисква специални условия на съхранение.</p>

  <h3>Производител</h3>
  <p>Besins Healthcare SA, Брюксел, Белгия.</p>

  <p><em>Това е лекарствен продукт с рецепта. Използвайте само по лекарско предписание.</em></p>
</div>
""",
        "images": [],
        "variants": [
            {
                "price": "0.00",
                "sku": "UTROGESTAN-200",
                "inventory_management": "shopify",
                "inventory_policy": "deny",
                "inventory_quantity": 0,
                "requires_shipping": False,
            }
        ],
    },
    # ------------------------------------------------------------------
    # Бемфола 150 IU (biosimilar on Gonal-F)
    # Source: EMA EPAR (Bemfola)
    # ------------------------------------------------------------------
    {
        "title": "БЕМФОЛА 150 IU/0,25 ml инжекционен разтвор в предварително напълнена писалка",
        "vendor": "Gedeon Richter",
        "product_type": "Лекарства",
        "tags": ["ivf", "само-в-аптека", "рецептурно", "Безплодие", "Гинекология"],
        "body_html": """
<div class="ivf-product-info">
  <p><strong>Бемфола 150 IU/0,25 ml</strong> — инжекционен разтвор в предварително напълнена писалка, съдържащ <strong>фолитропин алфа</strong> (рекомбинантен фоликулостимулиращ хормон, FSH). Биоподобен лекарствен продукт.</p>

  <h3>За какво се използва</h3>
  <ul>
    <li>Стимулиране на овулация при жени с ановулация, които не са се повлияли от кломифен цитрат</li>
    <li>Развитие на множество фоликули при асистирани репродуктивни технологии (IVF)</li>
    <li>Заедно с лутропин — при жени с тежък дефицит на FSH и LH</li>
    <li>При мъже — заедно с hCG за стимулиране на сперматогенезата</li>
  </ul>

  <h3>Активно вещество</h3>
  <p>Фолитропин алфа (follitropin alfa) — 150 IU (11 микрограма) в 0,25 ml разтвор.</p>

  <h3>Начин на приложение</h3>
  <p>Подкожна инжекция. Предварително напълнена писалка за еднократна употреба.</p>

  <h3>Съхранение</h3>
  <p>В хладилник (2°C–8°C). Да не се замразява. Може да се съхранява при температура до 25°C за период до 3 месеца (без да се връща обратно в хладилник).</p>

  <h3>Производител</h3>
  <p>Gedeon Richter Plc., Будапеща, Унгария.</p>

  <p><em>Това е лекарствен продукт с рецепта. Използвайте само по лекарско предписание. Информацията е съгласно одобрената от EMA кратка характеристика на продукта.</em></p>
</div>
""",
        "images": [],
        "variants": [
            {
                "price": "0.00",
                "sku": "BEMFOLA-150",
                "inventory_management": "shopify",
                "inventory_policy": "deny",
                "inventory_quantity": 0,
                "requires_shipping": False,
            }
        ],
    },
    # ------------------------------------------------------------------
    # Хориомон 5000 IU
    # Source: IBSA product info
    # ------------------------------------------------------------------
    {
        "title": "ХОРИОМОН 5000 IU прах и разтворител за инжекционен разтвор",
        "vendor": "IBSA Farmaceutici",
        "product_type": "Лекарства",
        "tags": ["ivf", "само-в-аптека", "рецептурно", "Безплодие", "Гинекология"],
        "body_html": """
<div class="ivf-product-info">
  <p><strong>Хориомон 5000 IU</strong> — прах и разтворител за инжекционен разтвор, съдържащ <strong>човешки хорионгонадотропин</strong> (hCG), извлечен от урината на бременни жени и високо пречистен.</p>

  <h3>За какво се използва</h3>
  <ul>
    <li>Предизвикване на финално узряване на фоликулите и овулация след стимулация с FSH/HMG</li>
    <li>Тригер за овулация при асистирана репродукция (IVF) — прилага се 24–48 часа преди пункция</li>
    <li>Лутеална поддръжка след ембриотрансфер</li>
    <li>При мъже — стимулиране на производството на тестостерон и сперматогенеза</li>
  </ul>

  <h3>Активно вещество</h3>
  <p>Човешки хорионгонадотропин (human chorionic gonadotropin, hCG) — 5000 IU на флакон.</p>

  <h3>Начин на приложение</h3>
  <p>Мускулна или подкожна инжекция. Прахът се разтваря в приложения разтворител непосредствено преди инжектиране. Обикновено еднократна доза.</p>

  <h3>Съхранение</h3>
  <p>В хладилник (2°C–8°C). Неразтвореният прах може да се съхранява и при стайна температура (под 25°C). След разтваряне — да се използва веднага.</p>

  <h3>Производител</h3>
  <p>IBSA Institut Biochimique SA, Лугано, Швейцария.</p>

  <p><em>Това е лекарствен продукт с рецепта. Използвайте само по лекарско предписание.</em></p>
</div>
""",
        "images": [],
        "variants": [
            {
                "price": "0.00",
                "sku": "CHORIOMON-5000",
                "inventory_management": "shopify",
                "inventory_policy": "deny",
                "inventory_quantity": 0,
                "requires_shipping": False,
            }
        ],
    },
]

COLLECTION_TITLE = "Ин витро препарати"
COLLECTION_HANDLE = "in-vitro"

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def create_product(client, product_data: dict, *, dry_run: bool = False) -> dict | None:
    """Create a single product via REST API. Returns the created product or None."""
    payload = {
        "product": {
            "title": product_data["title"],
            "vendor": product_data["vendor"],
            "product_type": product_data["product_type"],
            "tags": ", ".join(product_data["tags"]),
            "body_html": product_data["body_html"].strip(),
            "status": "active",
            "published": True,
            "variants": product_data["variants"],
            "images": product_data.get("images", []),
        }
    }

    if dry_run:
        print(f"  [DRY RUN] Would create: {product_data['title']}")
        print(f"            Vendor: {product_data['vendor']}")
        print(f"            Tags: {', '.join(product_data['tags'])}")
        print(f"            SKU: {product_data['variants'][0]['sku']}")
        return None

    result = client.rest_request("POST", "products.json", data=payload)
    if result and "product" in result:
        product = result["product"]
        print(f"  Created: {product['title']} (ID: {product['id']})")
        return product
    else:
        print(f"  FAILED: {product_data['title']}")
        return None


def create_collection(client, *, dry_run: bool = False) -> dict | None:
    """Create the IVF smart collection. Returns the collection or None."""
    payload = {
        "smart_collection": {
            "title": COLLECTION_TITLE,
            "handle": COLLECTION_HANDLE,
            "rules": [
                {
                    "column": "tag",
                    "relation": "equals",
                    "condition": "ivf",
                }
            ],
            "sort_order": "best-selling",
            "published": True,
            "body_html": (
                "<p>Специализирани препарати за ин витро оплождане (IVF) и асистирана "
                "репродукция. Всички продукти са налични в нашите аптеки.</p>"
            ),
        }
    }

    if dry_run:
        print(f"  [DRY RUN] Would create collection: {COLLECTION_TITLE}")
        print(f"            Handle: {COLLECTION_HANDLE}")
        print("            Rule: tag = ivf")
        return None

    # Check if collection already exists
    existing = client.rest_request("GET", f"smart_collections.json?handle={COLLECTION_HANDLE}")
    if existing:
        collections = existing.get("smart_collections", [])
        if collections:
            print(f"  Collection already exists: {collections[0]['title']} (ID: {collections[0]['id']})")
            return collections[0]

    result = client.rest_request("POST", "smart_collections.json", data=payload)
    if result and "smart_collection" in result:
        coll = result["smart_collection"]
        print(f"  Created collection: {coll['title']} (ID: {coll['id']})")
        return coll
    else:
        print("  FAILED to create collection")
        return None


def set_inventory_to_zero(client, product: dict) -> None:
    """Ensure all variants have inventory_quantity=0 at the default location."""
    # Get the shop's locations
    locations = client.rest_request("GET", "locations.json")
    if not locations or not locations.get("locations"):
        print("    Warning: Could not fetch locations to set inventory")
        return

    location_id = locations["locations"][0]["id"]

    for variant in product.get("variants", []):
        inventory_item_id = variant.get("inventory_item_id")
        if not inventory_item_id:
            continue

        client.rest_request(
            "POST",
            "inventory_levels/set.json",
            data={
                "location_id": location_id,
                "inventory_item_id": inventory_item_id,
                "available": 0,
            },
        )
    print(f"    Inventory set to 0 for {product['title'][:50]}...")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main() -> None:
    parser = base_parser("Create IVF products on Shopify")
    parser.add_argument(
        "--collection-only",
        action="store_true",
        help="Only create the collection, skip products",
    )
    parser.add_argument(
        "--products-only",
        action="store_true",
        help="Only create products, skip collection",
    )
    parser.add_argument(
        "--skip-existing",
        action="store_true",
        help="Skip products whose SKU already exists on Shopify",
    )
    args = parser.parse_args()
    init_logging(args)

    client, shop, _token = shopify_client_from_env()

    if not client.test_connection():
        print("Error: Could not connect to Shopify")
        sys.exit(1)

    # Create collection
    if not args.products_only:
        print("\n--- IVF Smart Collection ---")
        collection = create_collection(client, dry_run=args.dry_run)
    else:
        collection = None

    if args.collection_only:
        print("\nDone (collection only).")
        return

    # Fetch existing SKUs to avoid duplicates
    existing_skus: set[str] = set()
    if args.skip_existing and not args.dry_run:
        print("\nChecking existing products...")
        page = client.rest_request("GET", "products.json?limit=250&fields=id,variants")
        while page and "products" in page:
            for p in page["products"]:
                for v in p.get("variants", []):
                    if v.get("sku"):
                        existing_skus.add(v["sku"])
            # Simple pagination — if we got 250, there might be more
            if len(page["products"]) == 250:
                last_id = page["products"][-1]["id"]
                page = client.rest_request("GET", f"products.json?limit=250&since_id={last_id}&fields=id,variants")
            else:
                break
        print(f"  Found {len(existing_skus)} existing SKUs")

    # Create products
    print(f"\n--- IVF Products ({len(IVF_PRODUCTS)} total) ---")
    created = []
    skipped = 0
    for i, product_data in enumerate(IVF_PRODUCTS, 1):
        sku = product_data["variants"][0]["sku"]
        if args.skip_existing and sku in existing_skus:
            print(f"\n[{i}/{len(IVF_PRODUCTS)}] SKIP (exists): {product_data['title'][:60]}...")
            skipped += 1
            continue
        print(f"\n[{i}/{len(IVF_PRODUCTS)}]")
        product = create_product(client, product_data, dry_run=args.dry_run)
        if product:
            created.append(product)
            set_inventory_to_zero(client, product)
            time.sleep(0.5)  # Rate limiting courtesy

    # Summary
    print("\n--- Summary ---")
    print(f"Products created: {len(created)}/{len(IVF_PRODUCTS)}"
          f" (skipped {skipped} existing)" if skipped else
          f"Products created: {len(created)}/{len(IVF_PRODUCTS)}")
    if collection:
        print(f"Collection: https://viapharma.us/collections/{COLLECTION_HANDLE}")
    for p in created:
        handle = p.get("handle", "unknown")
        print(f"  Product: https://viapharma.us/products/{handle}")

    if created:
        print(
            "\nNext steps:"
            "\n  1. Set prices for each product in Shopify Admin"
            "\n  2. Assign the 'ivf' product template to each product"
            "\n     (Admin → Products → [product] → Theme template → ivf)"
        )


if __name__ == "__main__":
    main()
