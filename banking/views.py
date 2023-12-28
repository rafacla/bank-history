from django.contrib.auth.mixins import LoginRequiredMixin
from django.urls import reverse_lazy
from django.views import View
from django.views.generic.detail import DetailView
from django.views.generic.edit import CreateView, DeleteView, UpdateView
from django.views.generic.list import ListView
from django.db import models

from bootstrap_modal_forms.generic import (
  BSModalCreateView,
  BSModalUpdateView,
  BSModalReadView,
  BSModalDeleteView
)

from .models import Account, Category, Transaction
from .forms import CategoryForm


class AccountBaseView(LoginRequiredMixin, View):
    model = Account
    fields = "__all__"
    success_url = reverse_lazy("banking:account_list")


class AccountListView(AccountBaseView, ListView):
    extra_context = {"title": "Accounts"}

    """View to list all accounts.
    Use the 'account_list' variable in the template
    to access all Account objects"""


class AccountDetailView(AccountBaseView, DetailView):
    """View to list the details from one account.
    Use the 'account' variable in the template to access
    the specific account here and in the Views below"""


class AccountCreateView(AccountBaseView, CreateView):
    """View to create a new account"""

    extra_context = {"title": "Create Account"}
    fields = [
        "name",
        "type",
        "closing_day",
        "due_day",
        "bank",
        "currency",
    ]  # don't include 'user' here

    def form_valid(self, form):
        user = self.request.user
        form.instance.user = user
        return super(AccountCreateView, self).form_valid(form)


class AccountUpdateView(AccountBaseView, UpdateView):
    """View to update a account"""

    extra_context = {"title": "Update Account"}
    fields = [
        "name",
        "type",
        "closing_day",
        "due_day",
        "bank",
        "currency",
    ]  # don't include 'user' here


class AccountDeleteView(AccountBaseView, DeleteView):
    """View to delete a account"""


class CategoryBaseView(LoginRequiredMixin, View):
    model = Category
    success_url = reverse_lazy("banking:category_list")


class CategoryListView(CategoryBaseView, ListView):
    extra_context = {"title": "Categories"}

    """View to list all categories.
    Use the 'category_list' variable in the template
    to access all Category objects"""


class CategoryDetailView(CategoryBaseView, DetailView):
    """View to list the details from one category.
    Use the 'category' variable in the template to access
    the specific category here and in the Views below"""


class CategoryCreateView(CategoryBaseView, BSModalCreateView):
    """View to create a new category"""    
    form_class = CategoryForm
    success_message = "Success!"

    def get_initial(self):
        super().get_initial()
        if ("type" in self.request.resolver_match.kwargs):
            self.initial['type'] = self.request.resolver_match.kwargs['type']
        return self.initial

    def form_valid(self, form):
        user = self.request.user
        form.instance.user = user
        form.instance.sorting = Category.getLastSort(form.instance.nested_to, user)
        if ("type" in self.request.resolver_match.kwargs):
            form.instance.type = self.request.resolver_match.kwargs['type']
        if ("nested_to_id" in self.request.resolver_match.kwargs):
            form.instance.nested_to = Category.objects.filter(user=user, id=self.request.resolver_match.kwargs['nested_to_id']).first()
        return super(CategoryCreateView, self).form_valid(form)


class CategoryUpdateView(CategoryBaseView, BSModalUpdateView):
    """View to update a category"""

    form_class = CategoryForm
    success_message = "Success!"

    def get_initial(self):
        super().get_initial()
        self.initial['type'] = self.object.type
        self.initial['id'] = self.object.id
        return self.initial


class CategoryDeleteView(CategoryBaseView, DeleteView):
    """View to delete a category"""


class TransactionBaseView(LoginRequiredMixin, View):
    model = Transaction
    success_url = reverse_lazy("banking:transaction_list")


class TransactionListView(TransactionBaseView, ListView):
    extra_context = {"title": "Transactions", "add_button_title": "Add Transaction"}

    """View to list all transactions of given user.
    Use the 'transaction_list' variable in the template
    to access all Transaction objects"""
    def get_queryset(self, *args, **kwargs): 
        qs = super(TransactionListView, self).get_queryset(*args, **kwargs) 
        qs = qs.filter(merged_to=None).annotate(
            balance=models.Window(models.Sum('value'), order_by=models.F('date').asc())
        ).order_by("date")
        return qs

    def get_context_data(self, **kwargs):
        data = super().get_context_data(**kwargs)
        user = self.request.user
        qs = self.object_list.aggregate(first_date=models.Min("date"), last_date=models.Max("date"))
        data["first_date"] = qs["first_date"]
        data["last_date"] = qs["last_date"]
        data["balance_first_date"] = Transaction.objects.filter(account__user = user, date__lt=data["first_date"], merged_to=None).aggregate(balance=models.Sum("value"))["balance"] or 0
        data["balance_last_date"] = Transaction.objects.filter(account__user = user, date__lte=data["last_date"], merged_to=None).aggregate(balance=models.Sum("value"))["balance"] or 0
        return data