from decimal import Decimal

from django.contrib.auth.models import Group
from django.test import TestCase
from rest_framework.test import APIClient

from accounts.models import User
from cart.models import Cart, CartItem
from orders.models import Order, ShippingMethod
from .models import Category, Product, StockMovement

API = '/api/v1/inventory/'


def user(name, groups=(), **kw):
    u = User.objects.create_user(username=name, email=f'{name}@example.com', password='pw12345678', **kw)
    for g in groups:
        u.groups.add(Group.objects.get_or_create(name=g)[0])
    return u


def client_for(u):
    c = APIClient()
    if u:
        c.force_authenticate(u)
    return c


class InventoryApiTests(TestCase):
    def setUp(self):
        self.cat = Category.objects.create(name='HG')
        self.owner = user('owner', ['owner'])
        self.staff = user('staff', ['inventory'])
        self.customer = user('cust')
        self.p = Product.objects.create(
            name='HG Aerial', price=Decimal('39'), category=self.cat, description='',
            stock_quantity=2, in_stock=True, cost_usd=Decimal('18'), investor='Carlos')

    def test_requires_staff_role(self):
        self.assertEqual(client_for(None).get(API + 'products/').status_code, 401)
        self.assertEqual(client_for(self.customer).get(API + 'products/').status_code, 403)
        self.assertEqual(client_for(self.staff).get(API + 'products/').status_code, 200)
        self.assertEqual(client_for(self.customer).get(API + 'me/').json(), {'role': None})
        self.assertEqual(client_for(self.owner).get(API + 'me/').json(), {'role': 'owner'})

    def test_cost_and_investor_only_for_owner(self):
        staff_row = client_for(self.staff).get(API + 'products/').json()[0]
        owner_row = client_for(self.owner).get(API + 'products/').json()[0]
        self.assertNotIn('cost_usd', staff_row)
        self.assertNotIn('investor', staff_row)
        self.assertEqual((owner_row['cost_usd'], owner_row['investor']), ('18.00', 'Carlos'))

    def test_staff_cannot_write_private_fields(self):
        r = client_for(self.staff).patch(f'{API}products/{self.p.pk}/', {'cost_usd': '1', 'investor': 'x'}, format='json')
        self.assertEqual(r.status_code, 200)
        self.p.refresh_from_db()
        self.assertEqual((self.p.cost_usd, self.p.investor), (Decimal('18.00'), 'Carlos'))

    def test_public_api_never_leaks_private_fields(self):
        data = APIClient().get(f'/api/v1/products/products/{self.p.slug}/').json()
        self.assertNotIn('cost_usd', data)
        self.assertNotIn('investor', data)
        listing = APIClient().get('/api/v1/products/products/').json()['results'][0]
        self.assertNotIn('cost_usd', listing)
        self.assertNotIn('investor', listing)

    def test_create_with_initial_stock_logs_and_unique_slug_sku(self):
        c = client_for(self.owner)
        a = c.post(API + 'products/', {'name': 'Nuevo Kit', 'price': '10', 'stock_quantity': 3, 'grade': 'HG'}, format='json')
        b = c.post(API + 'products/', {'name': 'Nuevo Kit', 'price': '11', 'grade': 'NG'}, format='json')
        self.assertEqual((a.status_code, b.status_code), (201, 201), (a.content, b.content))
        self.assertNotEqual(a.json()['slug'], b.json()['slug'])
        self.assertNotEqual(a.json()['sku'], b.json()['sku'])
        self.assertEqual((a.json()['stock_quantity'], a.json()['in_stock']), (3, True))
        self.assertEqual((b.json()['stock_quantity'], b.json()['in_stock']), (0, False))
        mv = StockMovement.objects.get(product_id=a.json()['id'])
        self.assertEqual((mv.delta, mv.reason, mv.quantity_after), (3, 'initial', 3))

    def test_multipart_create_is_visible_by_default(self):
        r = client_for(self.staff).post(API + 'products/', {'name': 'Form Kit', 'price': '9.5'}, format='multipart')
        self.assertEqual(r.status_code, 201, r.content)
        self.assertTrue(r.json()['is_active'])
        self.assertEqual(APIClient().get('/api/v1/products/products/form-kit/').status_code, 200)

    def test_validation(self):
        c = client_for(self.staff)
        self.assertEqual(c.post(API + 'products/', {'name': 'X', 'price': '0'}, format='json').status_code, 400)
        r = c.patch(f'{API}products/{self.p.pk}/', {'sale_price': '50'}, format='json')
        self.assertEqual(r.status_code, 400)

    def test_stock_adjust_set_and_never_negative(self):
        c = client_for(self.staff)
        url = f'{API}products/{self.p.pk}/stock/'
        self.assertEqual(c.post(url, {'delta': 3, 'note': 'llegaron'}, format='json').json()['stock_quantity'], 5)
        self.assertEqual(c.post(url, {'set_to': 1}, format='json').json()['stock_quantity'], 1)
        self.assertEqual(c.post(url, {'delta': -5}, format='json').status_code, 400)
        self.assertEqual(c.post(url, {'set_to': 0}, format='json').json()['in_stock'], False)
        self.assertEqual(c.post(url, {'delta': 'abc'}, format='json').status_code, 400)
        history = c.get(f'{API}products/{self.p.pk}/movements/').json()
        self.assertEqual([m['quantity_after'] for m in history], [0, 1, 5])

    def test_archive_not_delete(self):
        c = client_for(self.staff)
        self.assertEqual(c.delete(f'{API}products/{self.p.pk}/').status_code, 405)
        c.patch(f'{API}products/{self.p.pk}/', {'is_active': False}, format='json')
        self.assertEqual(APIClient().get('/api/v1/products/products/').json()['count'], 0)


class CheckoutStockTests(TestCase):
    def setUp(self):
        self.cat = Category.objects.create(name='HG')
        self.u = user('buyer')
        self.ship = ShippingMethod.objects.create(name='Pickup', price=Decimal('0'), estimated_days='1')
        self.p = Product.objects.create(name='HG Zagann', price=Decimal('40'), category=self.cat,
                                        description='', stock_quantity=2, in_stock=True)
        self.cart = Cart.objects.create(user=self.u)
        self.item = CartItem.objects.create(cart=self.cart, product=self.p, quantity=2)
        self.c = client_for(self.u)
        self.body = {'shipping_address': {'name': 'A', 'line1': 'x'}, 'shipping_method_id': self.ship.id}

    def test_checkout_reserves_stock_and_cancel_restores(self):
        r = self.c.post('/api/v1/payments/checkout/', self.body, format='json')
        self.assertEqual(r.status_code, 200, r.content)
        self.p.refresh_from_db()
        self.assertEqual((self.p.stock_quantity, self.p.in_stock), (0, False))
        order = Order.objects.get()
        self.assertEqual(StockMovement.objects.filter(reason='order', order_number=order.order_number).count(), 1)
        cancel = self.c.post(f'/api/v1/orders/orders/{order.id}/cancel/')
        self.assertEqual(cancel.status_code, 200, cancel.content)
        self.p.refresh_from_db()
        self.assertEqual((self.p.stock_quantity, self.p.in_stock), (2, True))

    def test_not_enough_stock_blocks_order_and_changes_nothing(self):
        Product.objects.filter(pk=self.p.pk).update(stock_quantity=1)
        r = self.c.post('/api/v1/payments/checkout/', self.body, format='json')
        self.assertEqual(r.status_code, 409)
        self.assertEqual(r.json()['code'], 'insufficient_stock')
        self.assertFalse(Order.objects.exists())
        self.assertEqual(Cart.objects.get(user=self.u).items.count(), 1)  # cart untouched
        self.p.refresh_from_db()
        self.assertEqual(self.p.stock_quantity, 1)
