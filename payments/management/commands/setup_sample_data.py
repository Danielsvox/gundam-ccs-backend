from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from products.models import Category, Product
from orders.models import TaxRate
from decimal import Decimal
import uuid

User = get_user_model()


class Command(BaseCommand):
    help = 'Set up sample data for testing (categories, products, tax rates)'

    def handle(self, *args, **options):
        self.stdout.write("Setting up sample data...")
        self.stdout.write("=" * 50)

        # Create sample categories
        self.create_categories()
        
        # Create sample products
        self.create_products()
        
        # Create sample tax rates
        self.create_tax_rates()

        self.stdout.write(self.style.SUCCESS("Sample data created successfully!"))

    def create_categories(self):
        """Create sample Gundam categories."""
        self.stdout.write("Creating categories...")
        
        categories_data = [
            {
                'name': 'Master Grade (MG)',
                'slug': 'master-grade',
                'description': 'High-quality 1/100 scale model kits with excellent detail and articulation.'
            },
            {
                'name': 'High Grade (HG)',
                'slug': 'high-grade',
                'description': '1/144 scale model kits perfect for beginners and collectors.'
            },
            {
                'name': 'Perfect Grade (PG)',
                'slug': 'perfect-grade',
                'description': 'Premium 1/60 scale model kits with the highest level of detail.'
            },
            {
                'name': 'Real Grade (RG)',
                'slug': 'real-grade',
                'description': '1/144 scale model kits with Master Grade level detail.'
            },
            {
                'name': 'Super Deformed (SD)',
                'slug': 'super-deformed',
                'description': 'Chibi-style model kits with cute proportions.'
            }
        ]

        for cat_data in categories_data:
            category, created = Category.objects.get_or_create(
                name=cat_data['name'],
                defaults={
                    'slug': cat_data['slug'],
                    'description': cat_data['description'],
                    'is_active': True
                }
            )
            if created:
                self.stdout.write(f"  ✓ Created category: {category.name}")
            else:
                self.stdout.write(f"  - Category already exists: {category.name}")

    def create_products(self):
        """Create sample Gundam products."""
        self.stdout.write("Creating products...")
        
        # Get categories
        mg_category = Category.objects.filter(name__icontains='Master Grade').first()
        hg_category = Category.objects.filter(name__icontains='High Grade').first()
        pg_category = Category.objects.filter(name__icontains='Perfect Grade').first()
        
        products_data = [
            {
                'name': 'RX-78-2 Gundam Master Grade',
                'slug': 'rx-78-2-gundam-mg',
                'description': 'The iconic RX-78-2 Gundam in Master Grade form. Features excellent articulation and detailed inner frame.',
                'short_description': 'Classic Gundam in MG form',
                'price': Decimal('45.99'),
                'grade': 'MG',
                'scale': '1/100',
                'manufacturer': 'Bandai',
                'stock_quantity': 15,
                'sku': 'MG-RX78-001',
                'category': mg_category
            },
            {
                'name': 'MS-06S Zaku II Char\'s Custom',
                'slug': 'ms-06s-zaku-ii-chars-custom',
                'description': 'Char Aznable\'s custom red Zaku II. Features detailed armor and weapons.',
                'short_description': 'Char\'s red Zaku II',
                'price': Decimal('32.99'),
                'grade': 'HG',
                'scale': '1/144',
                'manufacturer': 'Bandai',
                'stock_quantity': 25,
                'sku': 'HG-ZAKU-002',
                'category': hg_category
            },
            {
                'name': 'RX-0 Unicorn Gundam Perfect Grade',
                'slug': 'rx-0-unicorn-gundam-pg',
                'description': 'The Unicorn Gundam in Perfect Grade form. Features LED lighting and transformation.',
                'short_description': 'PG Unicorn with LED',
                'price': Decimal('299.99'),
                'grade': 'PG',
                'scale': '1/60',
                'manufacturer': 'Bandai',
                'stock_quantity': 5,
                'sku': 'PG-UNICORN-003',
                'category': pg_category
            },
            {
                'name': 'RX-178 Gundam Mk-II Real Grade',
                'slug': 'rx-178-gundam-mk-ii-rg',
                'description': 'The Gundam Mk-II in Real Grade form. Features advanced articulation and detail.',
                'short_description': 'RG Gundam Mk-II',
                'price': Decimal('28.99'),
                'grade': 'RG',
                'scale': '1/144',
                'manufacturer': 'Bandai',
                'stock_quantity': 20,
                'sku': 'RG-MKII-004',
                'category': hg_category
            },
            {
                'name': 'SD Gundam RX-78-2',
                'slug': 'sd-gundam-rx-78-2',
                'description': 'Super Deformed version of the classic RX-78-2 Gundam. Perfect for beginners.',
                'short_description': 'SD Gundam for beginners',
                'price': Decimal('12.99'),
                'grade': 'SD',
                'scale': '1/144',
                'manufacturer': 'Bandai',
                'stock_quantity': 30,
                'sku': 'SD-RX78-005',
                'category': Category.objects.filter(name__icontains='Super Deformed').first()
            }
        ]

        for prod_data in products_data:
            product, created = Product.objects.get_or_create(
                name=prod_data['name'],
                defaults={
                    'slug': prod_data['slug'],
                    'description': prod_data['description'],
                    'short_description': prod_data['short_description'],
                    'price': prod_data['price'],
                    'grade': prod_data['grade'],
                    'scale': prod_data['scale'],
                    'manufacturer': prod_data['manufacturer'],
                    'stock_quantity': prod_data['stock_quantity'],
                    'sku': prod_data['sku'],
                    'category': prod_data['category'],
                    'is_active': True,
                    'in_stock': True
                }
            )
            if created:
                self.stdout.write(f"  ✓ Created product: {product.name}")
            else:
                self.stdout.write(f"  - Product already exists: {product.name}")

    def create_tax_rates(self):
        """Create sample tax rates."""
        self.stdout.write("Creating tax rates...")
        
        tax_rates_data = [
            {
                'country': 'United States',
                'state': 'California',
                'rate': Decimal('0.085'),  # 8.5%
                'is_active': True
            },
            {
                'country': 'United States',
                'state': 'New York',
                'rate': Decimal('0.0875'),  # 8.75%
                'is_active': True
            },
            {
                'country': 'United States',
                'state': 'Texas',
                'rate': Decimal('0.0625'),  # 6.25%
                'is_active': True
            },
            {
                'country': 'Canada',
                'state': 'Ontario',
                'rate': Decimal('0.13'),  # 13% HST
                'is_active': True
            }
        ]

        for tax_data in tax_rates_data:
            tax_rate, created = TaxRate.objects.get_or_create(
                country=tax_data['country'],
                state=tax_data['state'],
                defaults={
                    'rate': tax_data['rate'],
                    'is_active': tax_data['is_active']
                }
            )
            if created:
                self.stdout.write(f"  ✓ Created tax rate: {tax_rate}")
            else:
                self.stdout.write(f"  - Tax rate already exists: {tax_rate}") 