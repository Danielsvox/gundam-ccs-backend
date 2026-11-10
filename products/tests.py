from decimal import Decimal

from django.db import connection
from django.test import TestCase
from django.test.utils import CaptureQueriesContext
from django.urls import reverse
from rest_framework.test import APIClient

from .models import Category, Product, ProductImage


def make_product(category, name, price, **kwargs):
    defaults = dict(description=f'{name} description', grade='HG', scale='1/144',
                    manufacturer='Bandai', in_stock=True, stock_quantity=5)
    defaults.update(kwargs)
    return Product.objects.create(name=name, price=Decimal(price), category=category, **defaults)


class CatalogApiTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.uc = Category.objects.create(name='Universal Century')
        cls.seed = Category.objects.create(name='Cosmic Era')
        cls.rx = make_product(cls.uc, 'RX-78-2 Gundam', '30.00', grade='MG', scale='1/100', sku='T-1')
        cls.zaku = make_product(cls.uc, 'Zaku II', '25.00', sku='T-2')
        # On sale: customer pays 10.00 even though list price is 40.00
        cls.strike = make_product(cls.seed, 'Strike Gundam', '40.00', sale_price=Decimal('10.00'),
                                  grade='RG', sku='T-3')
        # in_stock flag is True but quantity is 0 (the model default for new products)
        cls.ghost = make_product(cls.seed, 'Ghost Kit', '20.00', stock_quantity=0, sku='T-4')
        cls.hidden = make_product(cls.seed, 'Inactive Kit', '5.00', is_active=False, sku='T-5')
        cls.client_api = APIClient()

    def get(self, params=None):
        return self.client.get(reverse('products:product_list'), params or {})

    def names(self, response):
        return [p['name'] for p in response.json()['results']]

    def test_inactive_products_are_not_listed(self):
        self.assertNotIn('Inactive Kit', self.names(self.get()))

    def test_page_size_is_honoured_and_bounded(self):
        r = self.get({'page_size': 2}).json()
        self.assertEqual(len(r['results']), 2)
        self.assertEqual(r['count'], 4)
        r = self.get({'page_size': 5000}).json()
        self.assertEqual(len(r['results']), 4)

    def test_scale_and_grade_filters_combine(self):
        self.assertEqual(self.names(self.get({'scale': '1/100'})), ['RX-78-2 Gundam'])
        self.assertEqual(self.names(self.get({'scale': '1/144', 'grade': 'RG'})), ['Strike Gundam'])
        self.assertEqual(self.names(self.get({'scale': '1/100', 'grade': 'RG'})), [])

    def test_category_slug_filter(self):
        self.assertCountEqual(self.names(self.get({'category_slug': 'cosmic-era'})),
                              ['Strike Gundam', 'Ghost Kit'])

    def test_price_filter_uses_the_price_the_customer_pays(self):
        # Strike's list price is 40 but it sells for 10.
        self.assertEqual(self.names(self.get({'max_price': '15'})), ['Strike Gundam'])
        self.assertNotIn('Strike Gundam', self.names(self.get({'min_price': '20'})))

    def test_invalid_price_is_a_400_not_a_500(self):
        for bad in ('abc', '-3', 'NaN'):
            self.assertEqual(self.get({'min_price': bad}).status_code, 400, bad)
            self.assertEqual(self.get({'max_price': bad}).status_code, 400, bad)

    def test_ordering_by_effective_price(self):
        asc = self.names(self.get({'ordering': 'effective_price'}))
        self.assertEqual(asc, ['Strike Gundam', 'Ghost Kit', 'Zaku II', 'RX-78-2 Gundam'])
        desc = self.names(self.get({'ordering': '-effective_price'}))
        self.assertEqual(desc[0], 'RX-78-2 Gundam')

    def test_available_requires_flag_and_quantity(self):
        self.assertNotIn('Ghost Kit', self.names(self.get({'available': 'true'})))
        self.assertIn('Ghost Kit', self.names(self.get({'in_stock': 'true'})))  # legacy flag unchanged

    def test_on_sale_filter(self):
        self.assertEqual(self.names(self.get({'on_sale': 'true'})), ['Strike Gundam'])

    def test_search_covers_manufacturer_and_scale(self):
        self.assertEqual(self.names(self.get({'search': '1/100'})), ['RX-78-2 Gundam'])

    def test_list_query_count_does_not_grow_with_products(self):
        for p in Product.objects.all():
            ProductImage.objects.create(product=p, image='products/x.jpg', is_primary=True)
        with CaptureQueriesContext(connection) as small:
            self.get({'page_size': 60})
        for i in range(10):
            p = make_product(self.uc if i % 2 else self.seed, f'Extra {i}', '12.00', sku=f'E-{i}')
            ProductImage.objects.create(product=p, image='products/y.jpg', is_primary=True)
        with CaptureQueriesContext(connection) as large:
            response = self.get({'page_size': 60})
        self.assertEqual(response.json()['count'], 14)
        # same categories -> same number of queries, regardless of how many products
        self.assertEqual(len(small), len(large))

    def test_primary_image_present_in_list(self):
        ProductImage.objects.create(product=self.zaku, image='products/z.jpg', is_primary=True)
        row = next(p for p in self.get().json()['results'] if p['name'] == 'Zaku II')
        self.assertIn('products/z.jpg', row['primary_image']['image'])

    def test_literal_routes_are_not_swallowed_by_the_slug_route(self):
        for name in ('product_search', 'featured_products', 'new_arrivals', 'on_sale_products', 'product_facets'):
            response = self.client.get(reverse(f'products:{name}'))
            self.assertEqual(response.status_code, 200, name)

    def test_search_endpoint_filters(self):
        r = self.client.get(reverse('products:product_search'), {'q': 'zaku'}).json()
        self.assertEqual([p['name'] for p in r['results']], ['Zaku II'])

    def test_facets(self):
        data = self.client.get(reverse('products:product_facets')).json()
        self.assertEqual({g['value']: g['count'] for g in data['grades']}, {'HG': 2, 'MG': 1, 'RG': 1})
        self.assertEqual({s['value']: s['count'] for s in data['scales']}, {'1/144': 3, '1/100': 1})
        self.assertEqual(data['manufacturers'], [{'value': 'Bandai', 'count': 4}])
        self.assertEqual({c['slug']: c['count'] for c in data['categories']},
                         {'universal-century': 2, 'cosmic-era': 2})
        self.assertEqual(data['price_range'], {'min': '10.00', 'max': '30.00'})

    def test_detail_by_slug_still_works(self):
        r = self.client.get(reverse('products:product_detail', kwargs={'slug': self.zaku.slug}))
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.json()['name'], 'Zaku II')
