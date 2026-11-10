"""Stock + role helpers shared by the inventory API, checkout and order cancellation."""
from django.db import transaction

from .models import Product, StockMovement

OWNER_GROUP = 'owner'
INVENTORY_GROUP = 'inventory'


class InsufficientStock(Exception):
    def __init__(self, product, available):
        self.product = product
        self.available = available
        super().__init__(f"Only {available} left of {product.name}")


def inventory_role(user):
    """'owner' (sees cost/investor), 'inventory' (stock/price/photos) or None."""
    if not user or not user.is_authenticated or not user.is_active:
        return None
    if user.is_superuser or user.groups.filter(name=OWNER_GROUP).exists():
        return 'owner'
    if user.groups.filter(name=INVENTORY_GROUP).exists():
        return 'inventory'
    return None


@transaction.atomic
def change_stock(product_id, delta, reason, user=None, note='', order_number=''):
    """Apply a stock delta under a row lock and log it. Raises InsufficientStock."""
    product = Product.objects.select_for_update().get(pk=product_id)
    new_qty = product.stock_quantity + delta
    if new_qty < 0:
        raise InsufficientStock(product, product.stock_quantity)
    product.stock_quantity = new_qty
    product.in_stock = new_qty > 0
    product.save(update_fields=['stock_quantity', 'in_stock', 'updated_at'])
    StockMovement.objects.create(
        product=product, delta=delta, quantity_after=new_qty, reason=reason,
        note=note[:255], order_number=order_number, user=user)
    return product


def reserve_for_order(order, items, user=None):
    """Take stock for [(product, quantity)] atomically with the caller's transaction."""
    for product, quantity in items:
        if not product.is_active:
            raise InsufficientStock(product, 0)
        change_stock(product.pk, -quantity, 'order', user=user,
                     order_number=order.order_number)


def restore_for_order(order, user=None):
    for item in order.items.select_related('product'):
        if item.product_id:
            change_stock(item.product_id, item.quantity, 'order_cancelled',
                         user=user, order_number=order.order_number)