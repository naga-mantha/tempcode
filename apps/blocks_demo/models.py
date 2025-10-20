"""Models for the blocks_demo app mirroring the classic Northwind schema."""

from django.db import models


class Category(models.Model):
    """Product category information."""

    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    picture = models.BinaryField(blank=True, null=True)

    class Meta:
        verbose_name_plural = "categories"

    def __str__(self) -> str:
        return self.name


class Supplier(models.Model):
    """Supplier details."""

    company_name = models.CharField(max_length=100)
    contact_name = models.CharField(max_length=100, blank=True)
    contact_title = models.CharField(max_length=100, blank=True)
    address = models.CharField(max_length=200, blank=True)
    city = models.CharField(max_length=100, blank=True)
    region = models.CharField(max_length=100, blank=True)
    postal_code = models.CharField(max_length=20, blank=True)
    country = models.CharField(max_length=100, blank=True)
    phone = models.CharField(max_length=30, blank=True)
    fax = models.CharField(max_length=30, blank=True)
    homepage = models.URLField(blank=True)

    def __str__(self) -> str:
        return self.company_name


class Product(models.Model):
    """Product catalog information."""

    name = models.CharField(max_length=100)
    supplier = models.ForeignKey(
        Supplier, on_delete=models.PROTECT, related_name="products"
    )
    category = models.ForeignKey(
        Category, on_delete=models.PROTECT, related_name="products"
    )
    quantity_per_unit = models.CharField(max_length=50, blank=True)
    unit_price = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    units_in_stock = models.PositiveSmallIntegerField(default=0)
    units_on_order = models.PositiveSmallIntegerField(default=0)
    reorder_level = models.PositiveSmallIntegerField(default=0)
    discontinued = models.BooleanField(default=False)

    def __str__(self) -> str:
        return self.name


class Customer(models.Model):
    """Customer contact and address details."""

    company_name = models.CharField(max_length=100)
    contact_name = models.CharField(max_length=100, blank=True)
    contact_title = models.CharField(max_length=100, blank=True)
    address = models.CharField(max_length=200, blank=True)
    city = models.CharField(max_length=100, blank=True)
    region = models.CharField(max_length=100, blank=True)
    postal_code = models.CharField(max_length=20, blank=True)
    country = models.CharField(max_length=100, blank=True)
    phone = models.CharField(max_length=30, blank=True)
    fax = models.CharField(max_length=30, blank=True)

    def __str__(self) -> str:
        return self.company_name


class Order(models.Model):
    """Order header information."""

    customer = models.ForeignKey(
        Customer, on_delete=models.PROTECT, related_name="orders"
    )
    order_date = models.DateField(blank=True, null=True)
    required_date = models.DateField(blank=True, null=True)
    shipped_date = models.DateField(blank=True, null=True)
    ship_via = models.CharField(max_length=50, blank=True)
    freight = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    ship_name = models.CharField(max_length=100, blank=True)
    ship_address = models.CharField(max_length=200, blank=True)
    ship_city = models.CharField(max_length=100, blank=True)
    ship_region = models.CharField(max_length=100, blank=True)
    ship_postal_code = models.CharField(max_length=20, blank=True)
    ship_country = models.CharField(max_length=100, blank=True)

    def __str__(self) -> str:
        return f"Order {self.pk}"


class OrderDetail(models.Model):
    """Line items associated with an order."""

    order = models.ForeignKey(
        Order, on_delete=models.CASCADE, related_name="details"
    )
    product = models.ForeignKey(
        Product, on_delete=models.PROTECT, related_name="order_details"
    )
    unit_price = models.DecimalField(max_digits=10, decimal_places=2)
    quantity = models.PositiveSmallIntegerField()
    discount = models.DecimalField(max_digits=4, decimal_places=2, default=0)

    class Meta:
        unique_together = ("order", "product")

    def __str__(self) -> str:
        return f"{self.product} ({self.quantity})"
