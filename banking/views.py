from django.urls import reverse_lazy
from django.views import View
from django.views.generic.detail import DetailView
from django.views.generic.edit import CreateView, DeleteView, UpdateView
from django.views.generic.list import ListView

from .models import Account


class AccountBaseView(View):
    model = Account
    fields = "__all__"
    success_url = reverse_lazy("banking:account_list")


class AccountListView(AccountBaseView, ListView):
    """View to list all accounts.
    Use the 'account_list' variable in the template
    to access all Account objects"""


class AccountDetailView(AccountBaseView, DetailView):
    """View to list the details from one account.
    Use the 'account' variable in the template to access
    the specific account here and in the Views below"""


class AccountCreateView(AccountBaseView, CreateView):
    """View to create a new account"""


class AccountUpdateView(AccountBaseView, UpdateView):
    """View to update a account"""


class AccountDeleteView(AccountBaseView, DeleteView):
    """View to delete a account"""
