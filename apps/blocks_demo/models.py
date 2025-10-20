"""Models for the blocks_demo app mirroring the classic Northwind schema."""

from __future__ import annotations

from decimal import Decimal

from django.db import models


class Category(models.Model):
    """Product category information."""

    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    picture = models.BinaryField(blank=True, null=True)

    class Meta:
        ordering = ["name"]
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

    class Meta:
        ordering = ["company_name"]

    def __str__(self) -> str:
        return self.company_name


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

    class Meta:
        ordering = ["company_name"]

    def __str__(self) -> str:
        return self.company_name


class Shipper(models.Model):
    """Shipping companies used to fulfil orders."""

    company_name = models.CharField(max_length=100)
    phone = models.CharField(max_length=30, blank=True)

    class Meta:
        ordering = ["company_name"]

    def __str__(self) -> str:
        return self.company_name


class Employee(models.Model):
    """Sales representatives associated with an order."""

    last_name = models.CharField(max_length=50)
    first_name = models.CharField(max_length=50)
    title = models.CharField(max_length=100, blank=True)
    title_of_courtesy = models.CharField(max_length=50, blank=True)
    birth_date = models.DateField(blank=True, null=True)
    hire_date = models.DateField(blank=True, null=True)
    address = models.CharField(max_length=200, blank=True)
    city = models.CharField(max_length=100, blank=True)
    region = models.CharField(max_length=100, blank=True)
    postal_code = models.CharField(max_length=20, blank=True)
    country = models.CharField(max_length=100, blank=True)
    home_phone = models.CharField(max_length=30, blank=True)
    extension = models.CharField(max_length=10, blank=True)
    notes = models.TextField(blank=True)
    reports_to = models.ForeignKey(
        "self",
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name="direct_reports",
    )
    photo_path = models.CharField(max_length=255, blank=True)

    class Meta:
        ordering = ["last_name", "first_name"]

    def __str__(self) -> str:
        return f"{self.first_name} {self.last_name}".strip()


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
    unit_price = models.DecimalField(
        max_digits=10, decimal_places=2, default=Decimal("0.00")
    )
    units_in_stock = models.PositiveSmallIntegerField(default=0)
    units_on_order = models.PositiveSmallIntegerField(default=0)
    reorder_level = models.PositiveSmallIntegerField(default=0)
    discontinued = models.BooleanField(default=False)

    class Meta:
        ordering = ["name"]

    def __str__(self) -> str:
        return self.name


class Order(models.Model):
    """Order header information."""

    customer = models.ForeignKey(
        Customer, on_delete=models.PROTECT, related_name="orders"
    )
    employee = models.ForeignKey(
        Employee,
        on_delete=models.PROTECT,
        related_name="orders",
        blank=True,
        null=True,
    )
    shipper = models.ForeignKey(
        Shipper,
        on_delete=models.PROTECT,
        related_name="orders",
        blank=True,
        null=True,
    )
    order_date = models.DateField(blank=True, null=True)
    required_date = models.DateField(blank=True, null=True)
    shipped_date = models.DateField(blank=True, null=True)
    freight = models.DecimalField(
        max_digits=10, decimal_places=2, default=Decimal("0.00")
    )
    ship_name = models.CharField(max_length=100, blank=True)
    ship_address = models.CharField(max_length=200, blank=True)
    ship_city = models.CharField(max_length=100, blank=True)
    ship_region = models.CharField(max_length=100, blank=True)
    ship_postal_code = models.CharField(max_length=20, blank=True)
    ship_country = models.CharField(max_length=100, blank=True)

    class Meta:
        ordering = ["-order_date", "pk"]

    def __str__(self) -> str:
        return f"Order {self.pk}" if self.pk else "New Order"


class OrderDetail(models.Model):
    """Line items associated with an order."""

    order = models.ForeignKey(
        Order, on_delete=models.CASCADE, related_name="details"
    )
    product = models.ForeignKey(
        Product, on_delete=models.PROTECT, related_name="order_details"
    )
    unit_price = models.DecimalField(
        max_digits=10, decimal_places=2, default=Decimal("0.00")
    )
    quantity = models.PositiveSmallIntegerField()
    discount = models.DecimalField(
        max_digits=4, decimal_places=2, default=Decimal("0.00")
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["order", "product"], name="uniq_order_product"
            )
        ]

    def __str__(self) -> str:
        return f"{self.product} ({self.quantity})"
