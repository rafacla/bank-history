from django.contrib import admin
from .models import Bank, Currency, Account, Category, Transaction

admin.site.register(Bank)
admin.site.register(Currency)
admin.site.register(Account)
admin.site.register(Category)
admin.site.register(Transaction)