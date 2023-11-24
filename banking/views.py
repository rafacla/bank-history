from django.contrib.auth.mixins import LoginRequiredMixin
from django.urls import reverse_lazy
from django.views import View
from django.views.generic.detail import DetailView
from django.views.generic.edit import CreateView, DeleteView, UpdateView
from django.views.generic.list import ListView


from .models import Account


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
    fields = ["name", "type", "closing_day", "due_day", "bank", "currency"]  # don't include 'user' here
    
    def form_valid(self, form):
        user = self.request.user
        form.instance.user = user
        return super(AccountCreateView, self).form_valid(form)


class AccountUpdateView(AccountBaseView, UpdateView):
    """View to update a account"""
    extra_context = {"title": "Update Account"}
    fields = ["name", "type", "closing_day", "due_day", "bank", "currency"]  # don't include 'user' here

class AccountDeleteView(AccountBaseView, DeleteView):
    """View to delete a account"""
