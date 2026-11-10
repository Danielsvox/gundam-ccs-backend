from decimal import Decimal
from unittest import mock

from django.test import SimpleTestCase, TestCase
from rest_framework.test import APIClient

from accounts.models import User
from orders.models import Order
from payments.models import PagoMovilBankCode, PagoMovilRecipient, PagoMovilVerificationRequest
from payments.services.exchange_rate_service import ExchangeRateService

PAGE = """<html><script>AF_initDataCallback({key: 'ds:2', hash: '1', data:[[[["/g/11g2tsrffq",null,"USD / VES",3,null,[897.1802,0.86,0.096,4,4,3],null,896.3164,null,null,null,[1794274800],null,0,"/g/11g2tsrffq",["USD","VES"],null]]]], sideChannel: {}});</script></html>"""


BCV_PAGE = '''<div id="dolar" class="x"><div><strong class="strong-tb">899,27050000</strong></div></div><div id="euro"><strong>1.050,5</strong></div><div>Fecha Valor: <span content="2026-11-10T00:00:00-04:00">Martes</span></div>'''


class BcvRateTests(SimpleTestCase):
    def test_parses_usd_rate_and_date(self):
        rate, date = ExchangeRateService._parse_bcv_rate(BCV_PAGE)
        self.assertEqual(rate, Decimal('899.27050000'))
        self.assertEqual(date, '2026-11-10T00:00:00-04:00')

    def test_rejects_missing_or_invalid(self):
        for html in ('', '<div id="dolar"></div>', '<div id="dolar"><strong>0,00</strong></div>'):
            with self.assertRaises(ValueError):
                ExchangeRateService._parse_bcv_rate(html)

    def test_bcv_is_first_source(self):
        self.assertEqual(ExchangeRateService().sources[0].__name__, '_fetch_from_bcv')

    def test_session_trusts_bundled_intermediate(self):
        ExchangeRateService._bcv_session()  # loads certifi + bundled cert without error


class GoogleFinanceRateTests(SimpleTestCase):
    def test_parses_quote_from_embedded_data(self):
        self.assertEqual(ExchangeRateService._parse_google_finance_rate(PAGE), Decimal('897.1802'))

    def test_raises_when_quote_missing(self):
        for html in ('', '<html></html>', PAGE.replace('USD / VES', 'EUR / VES')):
            with self.assertRaises(ValueError):
                ExchangeRateService._parse_google_finance_rate(html)

    def test_fetch_returns_google_finance_source_without_markup(self):
        resp = mock.Mock(text=PAGE)
        resp.raise_for_status = mock.Mock()
        with mock.patch('payments.services.exchange_rate_service.requests.get', return_value=resp):
            result = ExchangeRateService()._fetch_from_google_finance()
        self.assertEqual(result, {'rate': Decimal('897.1802'), 'source': 'google_finance'})

    def test_google_is_second_source(self):
        self.assertEqual(ExchangeRateService().sources[1].__name__, '_fetch_from_google_finance')


class PagoMovilOrderLinkTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='a', email='a@example.com', password='pw12345678')
        self.other = User.objects.create_user(username='b', email='b@example.com', password='pw12345678')
        bank = PagoMovilBankCode.objects.create(bank_code='0102', bank_name='Bank')
        self.recipient = PagoMovilRecipient.objects.create(
            recipient_name='Store', recipient_id='J-12345678-0',
            recipient_phone='04121234567', bank_code=bank)
        self.bank = bank
        self.client = APIClient()
        self.client.force_authenticate(self.user)

    def _order(self, user, **kw):
        return Order.objects.create(
            user=user, subtotal=Decimal('10'), tax_amount=Decimal('0.85'),
            shipping_amount=Decimal('0'), discount_amount=Decimal('0'),
            total_amount=Decimal('10.85'), shipping_address={'name': 'x'},
            billing_address={'name': 'x'}, status='pending', payment_status='pending', **kw)

    def _payload(self, order):
        return {
            'order': order.id, 'sender_id': 'V-12345678', 'sender_phone': '04121234567',
            'bank_code': self.bank.id, 'recipient': self.recipient.id, 'amount_ves': '400.00',
        }

    def test_verification_links_to_own_order_and_approval_pays_it(self):
        order = self._order(self.user)
        resp = self.client.post('/api/v1/payments/pagomovil/verify/', self._payload(order), format='json')
        self.assertEqual(resp.status_code, 201, resp.content)
        verification = PagoMovilVerificationRequest.objects.get()
        self.assertEqual(verification.order_id, order.id)
        verification.approve(self.user)
        order.refresh_from_db()
        self.assertEqual((order.payment_status, order.status), ('paid', 'confirmed'))

    def test_cannot_link_someone_elses_order(self):
        order = self._order(self.other)
        resp = self.client.post('/api/v1/payments/pagomovil/verify/', self._payload(order), format='json')
        self.assertEqual(resp.status_code, 400)
        self.assertFalse(PagoMovilVerificationRequest.objects.exists())

    def test_cannot_link_paid_order(self):
        order = self._order(self.user)
        order.payment_status = 'paid'
        order.save()
        resp = self.client.post('/api/v1/payments/pagomovil/verify/', self._payload(order), format='json')
        self.assertEqual(resp.status_code, 400)
