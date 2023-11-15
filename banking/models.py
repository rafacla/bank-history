import uuid

from django.contrib.auth.models import User
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models


class Bank(models.Model):
    name = models.CharField(max_length=100)
    logo = models.ImageField(upload_to="db-images/bank-logos/")
    country = models.CharField(max_length=100)

    def save(self, *args):
        if self.logo:
            self.logo.name = str(uuid.uuid4())
        super(Bank, self).save(*args)

    def __str__(self):
        return self.name


class Currency(models.Model):
    name = models.CharField(max_length=100)
    symbol = models.CharField(max_length=3)
    code = models.CharField(max_length=3)

    def __str__(self):
        return self.name

    class Meta:
        verbose_name_plural = "currencies"


class Account(models.Model):
    ACCOUNT_TYPES = (
        ("checkingAccount", "Checking Account"),
        ("savingAccount", "Saving Account"),
        ("creditCard", "Credit Card"),
        ("investmentAccount", "Investment Account"),
        ("liabilityAccount", "Liability Account"),
    )

    name = models.CharField(max_length=100)
    type = models.CharField(max_length=20, choices=ACCOUNT_TYPES)
    closing_day = models.IntegerField(blank=True, null=True)
    due_day = models.IntegerField(blank=True, null=True)
    bank = models.ForeignKey(Bank, on_delete=models.RESTRICT)
    currency = models.ForeignKey(Currency, on_delete=models.RESTRICT)
    user = models.ForeignKey(User, on_delete=models.CASCADE)

    class Meta:
        unique_together = ('user', 'name')

    def __str__(self):
        return f"{self.name} ({self.type} - {self.currency.name})"


class Category(models.Model):
    CATEGORY_TYPE = (
        ("D", "Debit"),
        ("C", "Credit"),
    )

    name = models.CharField(max_length=100)
    type = models.CharField(max_length=1, choices=CATEGORY_TYPE)
    ordering = models.IntegerField()
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    nested_to = models.ForeignKey(
        "self", on_delete=models.CASCADE, blank=True, null=True
    )

    def __str__(self):
        return f"{self.name} ({self.type})"

    class Meta:
        verbose_name_plural = "categories"


class Transaction(models.Model):
    date = models.DateField()
    competency_date = models.DateField(blank=True, null=True)
    description = models.CharField(max_length=200)
    merged_to = models.ForeignKey(
        "self", on_delete=models.CASCADE, blank=True, null=True
    )
    is_transfer = models.BooleanField(default=False)
    category = models.ForeignKey(
        Category, on_delete=models.SET_NULL, blank=True, null=True
    )
    concilied = models.BooleanField(default=False)
