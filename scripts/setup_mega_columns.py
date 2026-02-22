"""
setup_mega_columns.py

Creates 17 flat Shopify menus (one per mega-menu column group) and
prints the JSON blocks to add to sections/header-group.json.

Run: python scripts/setup_mega_columns.py
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

# ── Column definitions ──────────────────────────────────────────────────────────
# Each entry: (nav_item_title, column_title, handle_suffix, [(link_title, url), ...])

COLUMNS = [
    # Лечение и здраве
    ('Лечение и здраве', 'Имунна система', 'lechenie-1', [
        ('Грип и настинка',                   '/collections/grip-i-nastinka'),
        ('Имунна система',                     '/collections/imunna-sistema'),
        ('Имуностимуланти за възрастни',       '/collections/imunostimulanti-za-vazrastni'),
        ('Алергии',                            '/collections/alergii'),
        ('Хомеопатия',                         '/collections/homeopatiya'),
        ('Висока температура',                 '/collections/visoka-temperatura'),
    ]),
    ('Лечение и здраве', 'Витамини и добавки', 'lechenie-2', [
        ('Витамини и минерали',    '/collections/vitamini-i-minerali'),
        ('Витамини',               '/collections/vitamini'),
        ('Мултивитамини',          '/collections/multivitamini'),
        ('Монопрепарати',          '/collections/monopreparati'),
        ('Антиоксиданти',          '/collections/antioksidanti'),
        ('Пробиотици',             '/collections/probiotitsi'),
    ]),
    ('Лечение и здраве', 'Болки и системи', 'lechenie-3', [
        ('Болкоуспокояващи',              '/collections/bolkouspokoyavashti'),
        ('Болки в гърлото',               '/collections/bolki-v-garloto'),
        ('Кашлица',                       '/collections/kashlitsa'),
        ('Мускулни и ставни болки',       '/collections/muskulni-i-stavni-bolki'),
        ('Опорно-двигателна система',     '/collections/oporno-dvigatelna-sistema'),
        ('Сърдечно-съдова система',       '/collections/sardechno-sadova-sistema'),
    ]),
    ('Лечение и здраве', 'Специализирани', 'lechenie-4', [
        ('Храносмилателна система', '/collections/hranosmilatelna-sistema'),
        ('Кожни болести',           '/collections/kozhni-bolesti'),
        ('Очи',                     '/collections/ochi'),
        ('Уши',                     '/collections/ushi'),
        ('Нос и уста',              '/collections/nos-i-usta'),
        ('Депресия',               '/collections/depresiya'),
    ]),

    # Козметика
    ('Козметика', 'Грижа за лице', 'kozmetika-1', [
        ('Грижа за лице',                    '/collections/grizha-za-litse'),
        ('Кремове за лице',                  '/collections/kremove-za-litse'),
        ('Кремове и флуиди',                 '/collections/kremove-i-fluidi-za-litse'),
        ('Серуми',                           '/collections/serumi'),
        ('Маски за лице',                    '/collections/maski-za-litse'),
        ('Почистване и премахване на грим',  '/collections/pochistvane-na-kozhata-i-premahvane-na-grim'),
    ]),
    ('Козметика', 'Грижа за тяло', 'kozmetika-2', [
        ('Грижа за тяло',     '/collections/grizha-za-tyalo'),
        ('Душ гелове',         '/collections/dush-gelove'),
        ('Сапуни и баня',      '/collections/sapuni-i-produkti-za-banya'),
        ('Дезодоранти',        '/collections/dezodoranti-i-antiperspiranti'),
    ]),
    ('Козметика', 'Грижа за коса', 'kozmetika-3', [
        ('Грижа за коса',   '/collections/grizha-za-kosa'),
        ('Шампоани',         '/collections/shampoani-za-kosa'),
        ('Балсами',          '/collections/balsami-za-kosa'),
    ]),
    ('Козметика', 'Специализирана грижа', 'kozmetika-4', [
        ('Слънцезащита',      '/collections/slantsezashtita'),
        ('Орална хигиена',    '/collections/oralna-higiena'),
        ('Кремове',           '/collections/kremove'),
    ]),

    # Майка и дете
    ('Майка и дете', 'Здраве на децата', 'mayka-1', [
        ('Детско здраве',               '/collections/detsko-zdrave'),
        ('Имуностимуланти за деца',     '/collections/imunostimulanti-za-detsa'),
        ('Мултивитамини за деца',       '/collections/multivitamini-za-detsa'),
    ]),
    ('Майка и дете', 'Хранене и грижа', 'mayka-2', [
        ('Бебешко и детско хранене',    '/collections/bebeshko-i-detsko-hranene'),
        ('Адаптирани млека',            '/collections/adaptirani-mleka'),
        ('Детска козметика',            '/collections/detska-kozmetika-i-oralna-higiena'),
        ('Козметика за бебета',         '/collections/kozmetika-za-bebeta-i-detsa'),
    ]),
    ('Майка и дете', 'Бременност', 'mayka-3', [
        ('Бременност и кърмене',        '/collections/bremennost-i-karmene'),
        ('Витамини за бременни',        '/collections/vitamini-i-dobavki-za-bremenni'),
    ]),
    ('Майка и дете', 'Аксесоари', 'mayka-4', [
        ('Аксесоари за бебето',  '/collections/aksesoari-za-bebeto-i-deteto'),
        ('Шишета',               '/collections/shisheta'),
        ('Биберони',             '/collections/biberoni'),
        ('Чаши и биберони',      '/collections/chashi-i-biberoni'),
    ]),

    # Медицински изделия
    ('Медицински изделия', 'Диагностика', 'med-1', [
        ('Диагностични тестове',                      '/collections/diagnostichni-testove'),
        ('Апарати за кръвно налягане',                '/collections/aparati-za-izmervane-na-kravno-nalyagane'),
        ('Термометри',                                 '/collections/termometri'),
        ('Глюкомери',                                  '/collections/glyukomeri'),
        ('Апарати и уреди',                           '/collections/aparati-i-uredi'),
        ('Инхалатори',                                 '/collections/inhalatori'),
    ]),
    ('Медицински изделия', 'Превръзки и дезинфекция', 'med-2', [
        ('Превързочни материали и ЛПС', '/collections/prevarzochni-materiali-i-lichni-predpazni-sredstva'),
        ('Лепенки и ленти',             '/collections/lepenki-i-adhezivni-lenti'),
        ('Компреси и марли',             '/collections/kompresi-i-marli'),
        ('Медицински превръзки',         '/collections/meditsinski-prevrazki'),
        ('Дезинфектанти',                '/collections/dezinfektanti'),
        ('Дезинфекция на рани',          '/collections/dezinfektsiya-na-rani'),
    ]),
    ('Медицински изделия', 'Специализирани', 'med-3', [
        ('Ортопедични помощни средства',    '/collections/ortopedichni-pomoshtni-sredstva'),
        ('Медицински консумативи',          '/collections/meditsinski-instrumenti-i-konsumativi'),
        ('Помощни средства при инконт.',    '/collections/pomoshtni-sredstva-pri-inkontinentsiya'),
        ('Пелени за възрастни',             '/collections/peleni-za-vazrastni'),
    ]),

    # Спорт
    ('Спорт', 'Спортно хранене', 'sport-1', [
        ('Протеини',                     '/collections/proteini'),
        ('Аминокиселини',                '/collections/aminokiselini'),
        ('Мастни киселини',              '/collections/mastni-kiselini'),
        ('Фитнес и протеинови храни',    '/collections/fitnes-i-proteinovi-hrani'),
        ('Суперхрани',                   '/collections/superhrani'),
        ('Контрол на теглото',           '/collections/kontrol-na-tegloto'),
    ]),

    # Здравословно хранене
    ('Здравословно хранене', 'Продукти', 'zdrave-hran-1', [
        ('Чайове и билки',                              '/collections/chayove-i-bilki'),
        ('Храни за специални медицински цели',          '/collections/hrani-za-spetsialni-meditsinski-tseli'),
    ]),
]

# ── GraphQL mutations ───────────────────────────────────────────────────────────

CREATE_MUTATION = """
mutation menuCreate($title: String!, $handle: String!, $items: [MenuItemCreateInput!]!) {
  menuCreate(title: $title, handle: $handle, items: $items) {
    menu {
      id
      handle
    }
    userErrors {
      field
      message
    }
  }
}
"""


def gql(query, variables):
    resp = requests.post(
        API_URL,
        headers=HEADERS,
        json={'query': query, 'variables': variables},
        timeout=30,
    )
    resp.raise_for_status()
    return resp.json()


def create_menu(title, handle, items):
    """Create a flat menu and return its handle."""
    menu_items = [{'title': t, 'type': 'HTTP', 'url': u} for t, u in items]
    data = gql(CREATE_MUTATION, {
        'title': title,
        'handle': handle,
        'items': menu_items,
    })
    errors = data.get('data', {}).get('menuCreate', {}).get('userErrors', [])
    if errors:
        print(f'  ⚠ Errors for {handle}: {errors}')
        return None
    menu = data.get('data', {}).get('menuCreate', {}).get('menu', {})
    print(f'  ✅ Created: {menu.get("handle")} (id: {menu.get("id")})')
    return menu.get('handle')


def run():
    created_blocks = []
    print(f'Creating {len(COLUMNS)} flat column menus...\n')

    for nav_item, col_title, handle_suffix, links in COLUMNS:
        handle = f'mega-col-{handle_suffix}'
        menu_title = f'Mega: {col_title}'
        print(f'Creating {handle} ({len(links)} links)...')
        actual_handle = create_menu(menu_title, handle, links)
        if actual_handle:
            created_blocks.append({
                'nav_item': nav_item,
                'column_title': col_title,
                'column_menu_handle': actual_handle,
            })

    print(f'\n\n{"="*60}')
    print('BLOCKS JSON for sections/header-group.json:')
    print('Add these into the "blocks" object and "block_order" array')
    print('="*60}\n')

    blocks_dict = {}
    block_order = []
    for i, b in enumerate(created_blocks):
        block_id = f'mega_col_{i+1:02d}'
        blocks_dict[block_id] = {
            'type': 'mega_column',
            'settings': {
                'nav_item': b['nav_item'],
                'column_title': b['column_title'],
                'column_menu': b['column_menu_handle'],
            }
        }
        block_order.append(block_id)

    print(json.dumps({'blocks': blocks_dict, 'block_order': block_order}, indent=2, ensure_ascii=False))


if __name__ == '__main__':
    run()
