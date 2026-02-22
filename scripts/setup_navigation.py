"""
setup_navigation.py
Rebuilds the Shopify main-menu into a 3-level Apple-style mega menu.

Level 1 → top nav bar item  (6 categories)
Level 2 → column label      (section header inside dropdown, links to #)
Level 3 → clickable link    (actual subcollection)

Run: python scripts/setup_navigation.py
"""

import json
import os
import sys
import requests

# ── Credentials ────────────────────────────────────────────────────────────────
TOKEN_FILE = os.path.join(os.path.dirname(__file__), '..', '.shopify_token.json')
with open(TOKEN_FILE) as f:
    _creds = json.load(f)

SHOP    = _creds['shop'] + '.myshopify.com'
TOKEN   = _creds['access_token']
API_URL = f'https://{SHOP}/admin/api/2025-01/graphql.json'
HEADERS = {'X-Shopify-Access-Token': TOKEN, 'Content-Type': 'application/json'}

MAIN_MENU_ID = 'gid://shopify/Menu/251398586705'

# ── 3-level menu definition ─────────────────────────────────────────────────────
# Each top-level item has columns; each column has links.
# Column URL '#' makes it a non-clickable section label (styled by CSS).

MENU = [
    {
        'title': 'Лечение и здраве',
        'url': '/collections/lechenie-i-zdrave',
        'columns': [
            {
                'title': 'Имунна система',
                'items': [
                    ('Грип и настинка',                   '/collections/grip-i-nastinka'),
                    ('Имунна система',                     '/collections/imunna-sistema'),
                    ('Имуностимуланти за възрастни',       '/collections/imunostimulanti-za-vazrastni'),
                    ('Алергии',                            '/collections/alergii'),
                    ('Хомеопатия',                         '/collections/homeopatiya'),
                    ('Висока температура',                 '/collections/visoka-temperatura'),
                ],
            },
            {
                'title': 'Витамини и добавки',
                'items': [
                    ('Витамини и минерали',    '/collections/vitamini-i-minerali'),
                    ('Витамини',               '/collections/vitamini'),
                    ('Мултивитамини',          '/collections/multivitamini'),
                    ('Монопрепарати',          '/collections/monopreparati'),
                    ('Антиоксиданти',          '/collections/antioksidanti'),
                    ('Пробиотици',             '/collections/probiotitsi'),
                ],
            },
            {
                'title': 'Болки и системи',
                'items': [
                    ('Болкоуспокояващи',              '/collections/bolkouspokoyavashti'),
                    ('Болки в гърлото',               '/collections/bolki-v-garloto'),
                    ('Кашлица',                       '/collections/kashlitsa'),
                    ('Мускулни и ставни болки',       '/collections/muskulni-i-stavni-bolki'),
                    ('Опорно-двигателна система',     '/collections/oporno-dvigatelna-sistema'),
                    ('Сърдечно-съдова система',       '/collections/sardechno-sadova-sistema'),
                ],
            },
            {
                'title': 'Специализирани',
                'items': [
                    ('Храносмилателна система', '/collections/hranosmilatelna-sistema'),
                    ('Кожни болести',           '/collections/kozhni-bolesti'),
                    ('Очи',                     '/collections/ochi'),
                    ('Уши',                     '/collections/ushi'),
                    ('Нос и уста',              '/collections/nos-i-usta'),
                    ('Депресия',               '/collections/depresiya'),
                ],
            },
        ],
    },
    {
        'title': 'Козметика',
        'url': '/collections/kozmetika',
        'columns': [
            {
                'title': 'Грижа за лице',
                'items': [
                    ('Грижа за лице',                    '/collections/grizha-za-litse'),
                    ('Кремове за лице',                  '/collections/kremove-za-litse'),
                    ('Кремове и флуиди',                 '/collections/kremove-i-fluidi-za-litse'),
                    ('Серуми',                           '/collections/serumi'),
                    ('Маски за лице',                    '/collections/maski-za-litse'),
                    ('Почистване и премахване на грим',  '/collections/pochistvane-na-kozhata-i-premahvane-na-grim'),
                ],
            },
            {
                'title': 'Грижа за тяло',
                'items': [
                    ('Грижа за тяло',     '/collections/grizha-za-tyalo'),
                    ('Душ гелове',         '/collections/dush-gelove'),
                    ('Сапуни и баня',      '/collections/sapuni-i-produkti-za-banya'),
                    ('Дезодоранти',        '/collections/dezodoranti-i-antiperspiranti'),
                ],
            },
            {
                'title': 'Грижа за коса',
                'items': [
                    ('Грижа за коса',   '/collections/grizha-za-kosa'),
                    ('Шампоани',         '/collections/shampoani-za-kosa'),
                    ('Балсами',          '/collections/balsami-za-kosa'),
                ],
            },
            {
                'title': 'Специализирана грижа',
                'items': [
                    ('Слънцезащита',      '/collections/slantsezashtita'),
                    ('Орална хигиена',    '/collections/oralna-higiena'),
                    ('Кремове',           '/collections/kremove'),
                ],
            },
        ],
    },
    {
        'title': 'Майка и дете',
        'url': '/collections/mayka-i-dete',
        'columns': [
            {
                'title': 'Здраве на децата',
                'items': [
                    ('Детско здраве',               '/collections/detsko-zdrave'),
                    ('Имуностимуланти за деца',     '/collections/imunostimulanti-za-detsa'),
                    ('Мултивитамини за деца',       '/collections/multivitamini-za-detsa'),
                ],
            },
            {
                'title': 'Хранене и грижа',
                'items': [
                    ('Бебешко и детско хранене',    '/collections/bebeshko-i-detsko-hranene'),
                    ('Адаптирани млека',            '/collections/adaptirani-mleka'),
                    ('Детска козметика',            '/collections/detska-kozmetika-i-oralna-higiena'),
                    ('Козметика за бебета',         '/collections/kozmetika-za-bebeta-i-detsa'),
                ],
            },
            {
                'title': 'Бременност',
                'items': [
                    ('Бременност и кърмене',        '/collections/bremennost-i-karmene'),
                    ('Витамини за бременни',        '/collections/vitamini-i-dobavki-za-bremenni'),
                ],
            },
            {
                'title': 'Аксесоари',
                'items': [
                    ('Аксесоари за бебето',  '/collections/aksesoari-za-bebeto-i-deteto'),
                    ('Шишета',               '/collections/shisheta'),
                    ('Биберони',             '/collections/biberoni'),
                    ('Чаши и биберони',      '/collections/chashi-i-biberoni'),
                ],
            },
        ],
    },
    {
        'title': 'Медицински изделия',
        'url': '/collections/meditsinski-izdeliya-i-konsumativi',
        'columns': [
            {
                'title': 'Диагностика',
                'items': [
                    ('Диагностични тестове',                      '/collections/diagnostichni-testove'),
                    ('Апарати за кръвно налягане',                '/collections/aparati-za-izmervane-na-kravno-nalyagane'),
                    ('Термометри',                                 '/collections/termometri'),
                    ('Глюкомери',                                  '/collections/glyukomeri'),
                    ('Апарати и уреди',                           '/collections/aparati-i-uredi'),
                    ('Инхалатори',                                 '/collections/inhalatori'),
                ],
            },
            {
                'title': 'Превръзки и дезинфекция',
                'items': [
                    ('Превързочни материали и ЛПС', '/collections/prevarzochni-materiali-i-lichni-predpazni-sredstva'),
                    ('Лепенки и ленти',             '/collections/lepenki-i-adhezivni-lenti'),
                    ('Компреси и марли',             '/collections/kompresi-i-marli'),
                    ('Медицински превръзки',         '/collections/meditsinski-prevrazki'),
                    ('Дезинфектанти',                '/collections/dezinfektanti'),
                    ('Дезинфекция на рани',          '/collections/dezinfektsiya-na-rani'),
                ],
            },
            {
                'title': 'Специализирани',
                'items': [
                    ('Ортопедични помощни средства',    '/collections/ortopedichni-pomoshtni-sredstva'),
                    ('Медицински консумативи',          '/collections/meditsinski-instrumenti-i-konsumativi'),
                    ('Помощни средства при инконт.',    '/collections/pomoshtni-sredstva-pri-inkontinentsiya'),
                    ('Пелени за възрастни',             '/collections/peleni-za-vazrastni'),
                ],
            },
        ],
    },
    {
        'title': 'Спорт',
        'url': '/collections/sport',
        'columns': [
            {
                'title': 'Спортно хранене',
                'items': [
                    ('Протеини',                     '/collections/proteini'),
                    ('Аминокиселини',                '/collections/aminokiselini'),
                    ('Мастни киселини',              '/collections/mastni-kiselini'),
                    ('Фитнес и протеинови храни',    '/collections/fitnes-i-proteinovi-hrani'),
                    ('Суперхрани',                   '/collections/superhrani'),
                    ('Контрол на теглото',           '/collections/kontrol-na-tegloto'),
                ],
            },
        ],
    },
    {
        'title': 'Здравословно хранене',
        'url': '/collections/zdravoslovno-hranene-chayove-i-bilki',
        'columns': [
            {
                'title': 'Продукти',
                'items': [
                    ('Чайове и билки',                              '/collections/chayove-i-bilki'),
                    ('Храни за специални медицински цели',          '/collections/hrani-za-spetsialni-meditsinski-tseli'),
                ],
            },
        ],
    },
]


def build_items(menu_def):
    """Convert the MENU definition into Shopify MenuItemInput list."""
    items = []
    for cat in menu_def:
        col_items = []
        for col in cat['columns']:
            link_items = [
                {'title': t, 'type': 'HTTP', 'url': u}
                for t, u in col['items']
            ]
            col_items.append({
                'title': col['title'],
                'type': 'HTTP',
                'url': '#',
                'items': link_items,
            })
        items.append({
            'title': cat['title'],
            'type': 'HTTP',
            'url': cat['url'],
            'items': col_items,
        })
    return items


MUTATION = """
mutation menuUpdate($id: ID!, $title: String!, $handle: String!, $items: [MenuItemUpdateInput!]!) {
  menuUpdate(id: $id, title: $title, handle: $handle, items: $items) {
    menu {
      id
      handle
      title
      items {
        title
        url
        items {
          title
          url
          items {
            title
            url
          }
        }
      }
    }
    userErrors {
      field
      message
    }
  }
}
"""


def run():
    items = build_items(MENU)
    variables = {
        'id':     MAIN_MENU_ID,
        'title':  'Main menu',
        'handle': 'main-menu',
        'items':  items,
    }

    print(f'Updating main-menu with {len(items)} top-level items...')
    for item in items:
        print(f'  {item["title"]} → {len(item["items"])} columns')

    resp = requests.post(
        API_URL,
        headers=HEADERS,
        json={'query': MUTATION, 'variables': variables},
        timeout=30,
    )
    resp.raise_for_status()
    data = resp.json()

    errors = data.get('data', {}).get('menuUpdate', {}).get('userErrors', [])
    if errors:
        print('\n❌ API errors:')
        for e in errors:
            print(f'  {e["field"]}: {e["message"]}')
        sys.exit(1)

    result_menu = data.get('data', {}).get('menuUpdate', {}).get('menu', {})
    if not result_menu:
        print('\n❌ Unexpected response:')
        print(json.dumps(data, indent=2, ensure_ascii=False))
        sys.exit(1)

    print(f'\n✅ Menu updated: {result_menu["handle"]} (id: {result_menu["id"]})')
    for item in result_menu.get('items', []):
        print(f'\n  📂 {item["title"]}')
        for col in item.get('items', []):
            print(f'     └─ {col["title"]} ({len(col.get("items", []))} links)')


if __name__ == '__main__':
    run()
