import uuid

from django.contrib.auth.models import User
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from emoji import EMOJI_DATA 


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
    closing_day = models.PositiveIntegerField(
        blank=True, null=True, validators=[MinValueValidator(1), MaxValueValidator(28)]
    )
    due_day = models.PositiveIntegerField(
        blank=True, null=True, validators=[MinValueValidator(1), MaxValueValidator(28)]
    )
    bank = models.ForeignKey(Bank, on_delete=models.RESTRICT)
    currency = models.ForeignKey(Currency, on_delete=models.RESTRICT)
    user = models.ForeignKey(User, on_delete=models.CASCADE)

    class Meta:
        unique_together = ("user", "name")

    def __str__(self):
        return f"{self.name} ({dict(self.ACCOUNT_TYPES)[self.type]})"

    def getBalance(self):
        return sum([item.value for item in Transaction.objects.filter(account=self)])

    def getNotClassifiedTransactions(self):
        return Transaction.objects.filter(
            account=self, category=None, is_transfer=False
        )

    def getNotConciliedTransactions(self):
        return Transaction.objects.filter(account=self, concilied=False)


class Category(models.Model):
    CATEGORY_TYPE = (
        ("D", "Debit"),
        ("C", "Credit"),
    )

    name = models.CharField(max_length=100)
    type = models.CharField(max_length=1, choices=CATEGORY_TYPE)
    sorting = models.IntegerField()
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    nested_to = models.ForeignKey(
        "self", on_delete=models.CASCADE, blank=True, null=True
    )

    def __str__(self):
        return f"{self.name} ({self.type})"

    class Meta:
        verbose_name_plural = "categories"

    def beginsWithEmoji(self):
        return self.name[:1] in EMOJI_DATA

    def getLastSort(nested_to, user):
        last_sort = Category.objects.filter(nested_to=nested_to, user=user).aggregate(
            last_sort=models.Max("sorting", output_field=models.IntegerField())
        )["last_sort"]
        if last_sort == None:
            last_sort = 0
        else:
            last_sort = last_sort + 1
        return last_sort

    def getNumberOfTransactions(self):
        transactions = Transaction.objects.filter(category=self).count()
        return transactions

    def getSubcategories(self):
        categories = Category.objects.filter(nested_to=self).order_by("type","sorting")
        return categories

    def getUserGroupedAndSortedCategories(user: User):
        listOfUserCreditCategories = list()
        listOfUserDebitCategories = list()
        qs = Category.objects.filter(user=user, nested_to=None).order_by(
            "type", "sorting"
        )
        for item in qs.iterator():
            if item.type == "C":
                listOfUserCreditCategories.append(
                    (
                        item.id,
                        {
                            "id": item.id,
                            "name": item.name,
                            "type": item.type,
                            "sorting": item.sorting,
                            "nested_to_id": item.nested_to.id
                            if item.nested_to != None
                            else None,
                            "level": "1",
                        },
                    )
                )
                for item2 in item.getSubcategories():
                    listOfUserCreditCategories.append(
                        (
                            item2.id,
                            {
                                "id": item2.id,
                                "name": item2.name,
                                "type": item2.type,
                                "sorting": item2.sorting,
                                "nested_to_id": item2.nested_to.id
                                if item2.nested_to != None
                                else None,
                                "level": "2",
                            },
                        )
                    )
                    for item3 in item2.getSubcategories():
                        listOfUserCreditCategories.append(
                            (
                                item3.id,
                                {
                                    "id": item3.id,
                                    "name": item3.name,
                                    "type": item3.type,
                                    "sorting": item3.sorting,
                                    "nested_to_id": item3.nested_to.id
                                    if item3.nested_to != None
                                    else None,
                                    "level": "3",
                                },
                            )
                        )
            else:
                listOfUserDebitCategories.append(
                    (
                        item.id,
                        {
                            "id": item.id,
                            "name": item.name,
                            "type": item.type,
                            "sorting": item.sorting,
                            "nested_to_id": item.nested_to.id
                            if item.nested_to != None
                            else None,
                            "level": "1",
                        },
                    )
                )
                for item2 in item.getSubcategories():
                    listOfUserDebitCategories.append(
                        (
                            item2.id,
                            {
                                "id": item2.id,
                                "name": item2.name,
                                "type": item2.type,
                                "sorting": item2.sorting,
                                "nested_to_id": item2.nested_to.id
                                if item2.nested_to != None
                                else None,
                                "level": "2",
                            },
                        )
                    )
                    for item3 in item2.getSubcategories():
                        listOfUserDebitCategories.append(
                            (
                                item3.id,
                                {
                                    "id": item3.id,
                                    "name": item3.name,
                                    "type": item3.type,
                                    "sorting": item3.sorting,
                                    "nested_to_id": item3.nested_to.id
                                    if item3.nested_to != None
                                    else None,
                                    "level": "3",
                                },
                            )
                        )
        listOfUserCategories = (
            ("","No category"),
            ("Credit Categories",
            listOfUserCreditCategories),
            ("Debit Categories",
            listOfUserDebitCategories)
        )
        return listOfUserCategories


class Transaction(models.Model):
    account = models.ForeignKey(Account, on_delete=models.CASCADE)
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
    value = models.DecimalField(max_digits=10, decimal_places=2)
    notes = models.TextField(blank=True, null=True)

    def getMergedTransactions(self):
        mergedTransactions = Transaction.objects.filter(merged_to=self)
        return mergedTransactions
