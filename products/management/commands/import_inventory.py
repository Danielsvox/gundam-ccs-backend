"""Import the store's purchase sheet (CSV) into the catalog.

Dry-run by default: prints exactly what would be created/changed. Use --apply to write.

Sheet columns used: MODELO, PRECIO + ENVIO (unit cost), Valor bruto, Precio 30% UP (sale price).
When "Precio 30% UP" is empty the price is CALCULATED as round(Valor bruto x 1.69)
(= (cost + ads) x 1.3 x 1.3, the sheet's own rule) and flagged so a human reviews it.
Rows with the same model are merged: stock = number of rows, investor = "Carlos x2, Miguel".
Products that are not in the sheet are archived (is_active=False), never deleted.
"""
import csv
import re
from collections import OrderedDict
from decimal import ROUND_HALF_UP, Decimal

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils.text import slugify

from products.inventory_service import change_stock
from products.models import Category, Product

INVESTORS = ('CARLOS', 'MIGUEL', 'FRAN', 'ALE')
KEEP_UPPER = {'HG', 'RG', 'MG', 'PG', 'SD', 'AT', 'AEUG'}
MULTIPLIER = Decimal('1.69')

# Owner-approved corrections to the sheet's spelling (matched on the lower-cased cleaned name).
RENAMES = {
    'hg zagann': 'HG Zagan',
    'xenosentinel rojo': 'Xentinel Rojo',
    'sheik zikron': 'Sheik Zi-Kron',
}

# Brand/scale verified against manufacturer or retailer pages (see docs/photo-candidates.md in the
# frontend repo). Order matters: first match wins. Only facts a source confirmed are listed.
BRAND_RULES = [
    (r'^(fenrir|xenostrike|xenodash)\b', 'Sheik Mainland', '1/18'),   # 3MIN Project, 1/18
    (r'^xentinel\b', 'Sheik Mainland', ''),                       # scale not confirmed
    (r'^sheik (zarov|zi-kron)\b', 'Sheik Mainland', '1/144'),          # Ultra Action Trooper, 1/144
    (r'^blokees\b', 'Blokees', ''),                                   # Star Wars Champion Class
    (r'^hg\b', 'Bandai', '1/144'),                                    # HG line is 1/144
]


def money(text):
    text = (text or '').replace('$', '').replace(',', '').strip()
    return Decimal(text) if re.fullmatch(r'\d+(\.\d+)?', text) else None


def split_investor(raw):
    m = re.match(r'^(%s)(?=\s|BLOKEES)\s*(.*)$' % '|'.join(INVESTORS), raw.strip(), re.I)
    if not m:
        raise ValueError(f'No investor prefix in "{raw}"')
    return m.group(1).capitalize(), m.group(2).strip()


def pretty(model):
    out = []
    for tok in model.split():
        if tok.upper() in KEEP_UPPER or any(ch.isdigit() for ch in tok):
            out.append(tok.upper())
        else:
            out.append(tok.capitalize())
    return ' '.join(out)


def parse_sheet(path):
    with open(path, newline='', encoding='utf-8-sig') as fh:
        rows = list(csv.reader(fh))[1:]
    merged, skipped = OrderedDict(), []
    for r in rows:
        r += [''] * (12 - len(r))
        raw = r[0].strip()
        if not raw or raw.upper() == 'TOTAL':
            continue
        cost, bruto, listed = money(r[1]), money(r[4]), money(r[9])
        try:
            investor, model = split_investor(raw)
        except ValueError:
            skipped.append((raw, 'not an investor/model row'))
            continue
        if cost is None or bruto is None:
            skipped.append((raw, 'no cost/price in sheet (nothing to publish)'))
            continue
        name = pretty(model)
        name = RENAMES.get(name.lower(), name)
        key = re.sub(r'\s+', ' ', name).lower()
        item = merged.setdefault(key, dict(name=name, investors=OrderedDict(), costs=set(),
                                           listed=set(), brutos=set(), rows=0))
        item['rows'] += 1
        item['investors'][investor] = item['investors'].get(investor, 0) + 1
        item['costs'].add(cost)
        item['brutos'].add(bruto)
        if listed is not None:
            item['listed'].add(listed)
    products = []
    for item in merged.values():
        notes = []
        if item['listed']:
            price, source = max(item['listed']), 'sheet'
            if len(item['listed']) > 1:
                notes.append(f"prices differ in sheet {sorted(item['listed'])}, used highest")
        else:
            bruto = max(item['brutos'])
            price = (bruto * MULTIPLIER).quantize(Decimal('1'), rounding=ROUND_HALF_UP)
            source = 'CALCULATED'
        if len(item['costs']) > 1:
            notes.append(f"costs differ {sorted(item['costs'])}, used average")
        cost = (sum(item['costs']) / len(item['costs'])).quantize(Decimal('0.01'))
        investor = ', '.join(f'{n} x{c}' if c > 1 else n for n, c in item['investors'].items())
        if item['rows'] > 1 and any(c > 1 for c in item['investors'].values()):
            notes.append('same investor repeated: confirm it is not a duplicate entry')
        is_hg = item['name'].upper().startswith('HG ')
        brand, scale = ('Otro', '')
        for pattern, b, s in BRAND_RULES:
            if re.match(pattern, item['name'], re.I):
                brand, scale = b, s
                break
        products.append(dict(
            name=item['name'], price=price, price_source=source, cost=cost, investor=investor,
            qty=item['rows'], grade='HG' if is_hg else 'NG',
            manufacturer=brand, scale=scale,
            category='High Grade (HG)' if is_hg else 'Otros kits', notes='; '.join(notes)))
    return products, skipped


class Command(BaseCommand):
    help = __doc__

    def add_arguments(self, parser):
        parser.add_argument('csv_path')
        parser.add_argument('--apply', action='store_true', help='Write changes (default is a dry-run).')

    def handle(self, csv_path, apply=False, **opts):
        try:
            products, skipped = parse_sheet(csv_path)
        except OSError as exc:
            raise CommandError(str(exc))

        self.stdout.write(f"{'APPLY' if apply else 'DRY-RUN'}: {len(products)} products from sheet\n")
        w = self.stdout.write
        w(f"{'Name':34} {'Grade':5} {'Qty':>3} {'Cost':>6} {'Price':>6}  {'Source':10} Investor / notes")
        for p in products:
            extra = p['investor'] + (f"  !! {p['notes']}" if p['notes'] else '')
            w(f"{p['name']:34} {p['grade']:5} {p['qty']:>3} {p['cost']:>6} {p['price']:>6}  {p['price_source']:10} {extra}")
        for raw, why in skipped:
            w(f'NOT IMPORTED: {raw} ({why})')

        slugs = {slugify(p['name']) for p in products}
        stale = Product.objects.filter(is_active=True).exclude(slug__in=slugs)
        w(f"\nWould archive (hide, not delete) {stale.count()} existing products: "
          + ', '.join(stale.values_list('name', flat=True)))
        if not apply:
            w('\nNothing written. Re-run with --apply after reviewing the prices above.')
            return

        with transaction.atomic():
            for p in products:
                category, _ = Category.objects.get_or_create(name=p['category'])
                product, created = Product.objects.get_or_create(
                    slug=slugify(p['name']),
                    defaults=dict(name=p['name'], description='', price=p['price'], category=category,
                                  grade=p['grade'], manufacturer=p['manufacturer'], scale=p['scale'], stock_quantity=0,
                                  in_stock=False))
                product.price, product.cost_usd, product.investor = p['price'], p['cost'], p['investor']
                product.manufacturer, product.scale = p['manufacturer'], p['scale']
                product.is_active = True
                product.sale_price = None
                product.save()
                delta = p['qty'] - product.stock_quantity
                if delta:
                    change_stock(product.pk, delta, 'initial' if created else 'adjustment',
                                 note='Import from purchase sheet')
            archived = stale.update(is_active=False)
        w(self.style.SUCCESS(f'Done. Imported/updated {len(products)}, archived {archived}.'))