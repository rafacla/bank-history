from django.contrib.auth.mixins import LoginRequiredMixin
from django.urls import reverse_lazy
from django.views import View
from django.views.generic.detail import DetailView
from django.views.generic.edit import CreateView, DeleteView, UpdateView
from django.views.generic.list import ListView


from .models import Account, Category


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
    fields = "__all__"
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


class CategoryCreateView(CategoryBaseView, CreateView):
    """View to create a new category"""

    extra_context = {"title": "Create Category"}
    fields = [
        "name",
        "type",
        "nested_to"
    ]  # don't include 'user' here

    def form_valid(self, form):
        user = self.request.user
        form.instance.user = user
        sort = Category
        return super(CategoryCreateView, self).form_valid(form)


class CategoryUpdateView(CategoryBaseView, UpdateView):
    """View to update a category"""

    extra_context = {"title": "Update Category"}
    fields = [
        "name",
        "nested_to"
    ]  # don't include 'user' here


class CategoryDeleteView(CategoryBaseView, DeleteView):
    """View to delete a category"""
