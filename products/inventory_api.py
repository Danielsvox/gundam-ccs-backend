"""Staff-only inventory API (simple CRUD + stock log) used by the /inventario page."""
from decimal import Decimal

from django.db import transaction
from django.utils.text import slugify
from rest_framework import generics, permissions, serializers, status
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.response import Response
from rest_framework.views import APIView

from .inventory_service import InsufficientStock, change_stock, inventory_role
from .models import Category, Product, ProductImage, StockMovement

OWNER_ONLY_FIELDS = ('cost_usd', 'investor')


class IsInventoryStaff(permissions.BasePermission):
    def has_permission(self, request, view):
        return inventory_role(request.user) is not None


def _unique_slug(name, exclude_pk=None):
    base = slugify(name) or 'producto'
    slug, n = base, 2
    qs = Product.objects.all()
    if exclude_pk:
        qs = qs.exclude(pk=exclude_pk)
    while qs.filter(slug=slug).exists():
        slug = f'{base}-{n}'
        n += 1
    return slug


def _default_category():
    cat, _ = Category.objects.get_or_create(name='Otros kits')
    return cat


class InventoryProductSerializer(serializers.ModelSerializer):
    image = serializers.SerializerMethodField()
    new_image = serializers.ImageField(write_only=True, required=False)
    category_name = serializers.CharField(source='category.name', read_only=True)
    stock_quantity = serializers.IntegerField(min_value=0, required=False)

    class Meta:
        model = Product
        fields = ('id', 'slug', 'sku', 'name', 'description', 'short_description', 'grade',
                  'scale', 'manufacturer', 'category', 'category_name', 'price', 'sale_price',
                  'stock_quantity', 'in_stock', 'is_active', 'image', 'new_image',
                  'cost_usd', 'investor', 'updated_at')
        read_only_fields = ('id', 'slug', 'sku', 'in_stock', 'updated_at')
        extra_kwargs = {
            'category': {'required': False},
            'description': {'required': False, 'allow_blank': True},
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        request = self.context.get('request')
        if inventory_role(getattr(request, 'user', None)) != 'owner':
            for field in OWNER_ONLY_FIELDS:
                self.fields.pop(field, None)

    def get_image(self, obj):
        images = list(obj.images.all())
        if not images:
            return None
        primary = next((i for i in images if i.is_primary), images[0])
        request = self.context.get('request')
        url = primary.image.url
        return request.build_absolute_uri(url) if request else url

    def validate(self, attrs):
        # DRF treats a missing checkbox in multipart/form data as False; new products default to visible.
        if self.instance is None and 'is_active' not in self.initial_data:
            attrs['is_active'] = True
        price = attrs.get('price', getattr(self.instance, 'price', None))
        sale = attrs.get('sale_price', getattr(self.instance, 'sale_price', None))
        if price is not None and price <= 0:
            raise serializers.ValidationError({'price': 'Price must be greater than 0.'})
        if sale is not None and price is not None and sale >= price:
            raise serializers.ValidationError({'sale_price': 'Sale price must be lower than the price.'})
        return attrs

    def _save_image(self, product, image):
        if image:
            ProductImage.objects.create(
                product=product, image=image, alt_text=product.name, is_primary=True)

    @transaction.atomic
    def create(self, validated_data):
        image = validated_data.pop('new_image', None)
        initial = validated_data.pop('stock_quantity', 0)
        validated_data.setdefault('category', _default_category())
        validated_data['slug'] = _unique_slug(validated_data['name'])
        validated_data['stock_quantity'] = 0
        validated_data['in_stock'] = False
        validated_data['created_by'] = self.context['request'].user
        validated_data['updated_by'] = self.context['request'].user
        product = Product.objects.create(**validated_data)
        if initial:
            change_stock(product.pk, initial, 'initial', user=self.context['request'].user)
            product.refresh_from_db()
        self._save_image(product, image)
        return product

    @transaction.atomic
    def update(self, instance, validated_data):
        image = validated_data.pop('new_image', None)
        new_qty = validated_data.pop('stock_quantity', None)
        user = self.context['request'].user
        validated_data['updated_by'] = user
        instance = super().update(instance, validated_data)
        # Stock changes always go through the log so the history stays complete.
        if new_qty is not None and new_qty != instance.stock_quantity:
            change_stock(instance.pk, new_qty - instance.stock_quantity, 'adjustment',
                         user=user, note='Edited in inventory')
            instance.refresh_from_db()
        self._save_image(instance, image)
        return instance


class StockMovementSerializer(serializers.ModelSerializer):
    user = serializers.SerializerMethodField()

    class Meta:
        model = StockMovement
        fields = ('id', 'delta', 'quantity_after', 'reason', 'note', 'order_number', 'user', 'created_at')

    def get_user(self, obj):
        return (obj.user.first_name or obj.user.email) if obj.user else ''


def _queryset():
    return Product.objects.select_related('category').prefetch_related('images').order_by('name')


class InventoryMeView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        return Response({'role': inventory_role(request.user)})


class InventoryProductListCreateView(generics.ListCreateAPIView):
    permission_classes = [IsInventoryStaff]
    serializer_class = InventoryProductSerializer
    parser_classes = [MultiPartParser, FormParser, JSONParser]
    pagination_class = None

    def get_queryset(self):
        qs = _queryset()
        params = self.request.query_params
        search = params.get('search', '').strip()
        if search:
            qs = qs.filter(name__icontains=search) | qs.filter(sku__icontains=search)
        if params.get('active') in ('0', '1'):
            qs = qs.filter(is_active=params['active'] == '1')
        return qs


class InventoryProductDetailView(generics.RetrieveUpdateAPIView):
    """No DELETE on purpose: staff archive products (is_active=false) so order history stays intact."""
    permission_classes = [IsInventoryStaff]
    serializer_class = InventoryProductSerializer
    parser_classes = [MultiPartParser, FormParser, JSONParser]
    queryset = _queryset()


class StockAdjustView(APIView):
    """POST {delta, reason?, note?} or {set_to, note?}."""
    permission_classes = [IsInventoryStaff]

    def post(self, request, pk):
        try:
            product = Product.objects.get(pk=pk)
        except Product.DoesNotExist:
            return Response({'error': 'Not found.'}, status=status.HTTP_404_NOT_FOUND)
        data = request.data
        try:
            if data.get('set_to') not in (None, ''):
                delta = int(data['set_to']) - product.stock_quantity
            else:
                delta = int(data.get('delta'))
        except (TypeError, ValueError):
            return Response({'error': 'delta or set_to must be an integer.'}, status=status.HTTP_400_BAD_REQUEST)
        if delta == 0:
            return Response(InventoryProductSerializer(product, context={'request': request}).data)
        reason = data.get('reason') if data.get('reason') in ('purchase', 'adjustment') else (
            'purchase' if delta > 0 else 'adjustment')
        try:
            product = change_stock(product.pk, delta, reason, user=request.user,
                                   note=str(data.get('note', '')))
        except InsufficientStock as exc:
            return Response({'error': f'Stock cannot go below 0 (now {exc.available}).'},
                            status=status.HTTP_400_BAD_REQUEST)
        product = _queryset().get(pk=product.pk)
        return Response(InventoryProductSerializer(product, context={'request': request}).data)


class StockMovementListView(generics.ListAPIView):
    permission_classes = [IsInventoryStaff]
    serializer_class = StockMovementSerializer
    pagination_class = None

    def get_queryset(self):
        return StockMovement.objects.filter(product_id=self.kwargs['pk']).select_related('user')[:50]