import csv

from bootstrap_modal_forms.generic import (
    BSModalCreateView,
    BSModalDeleteView,
    BSModalFormView,
    BSModalReadView,
    BSModalUpdateView,
)
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import PermissionDenied
from django.db import models
from django.forms import formset_factory
from django.shortcuts import render
from django.urls import reverse_lazy
from django.views import View
from django.views.generic.detail import DetailView
from django.views.generic.edit import CreateView, DeleteView, FormView, UpdateView
from django.views.generic.list import ListView

from .forms import (
    AccountForm,
    CategoryForm,
    CSVImportForm,
    CSVConfirmImport,
    TransactionCategorizeForm,
    TransactionDeleteForm,
    TransactionForm,
    TransactionInternalTransferForm,
    CSVConfirmImportFormSetHelper,
)
from .models import Account, Category, Transaction
from django.shortcuts import redirect


class AccountBaseView(LoginRequiredMixin, View):
    model = Account
    success_url = reverse_lazy("banking:account_list")


class AccountListView(AccountBaseView, ListView):
    extra_context = {"title": "Accounts"}

    """View to list all accounts.
    Use the 'account_list' variable in the template
    to access all Account objects"""

    def get_queryset(self):
        qs = super().get_queryset()
        return qs.filter(user=self.request.user)


class AccountDetailView(AccountBaseView, DetailView):
    """View to list the details from one account.
    Use the 'account' variable in the template to access
    the specific account here and in the Views below"""

    def get_queryset(self):
        qs = super().get_queryset()
        return qs.filter(
            pk=self.request.resolver_match.kwargs["pk"], user=self.request.user
        )


class AccountCreateView(AccountBaseView, BSModalCreateView):
    """View to create a new account"""

    form_class = AccountForm
    success_message = "Success!"

    def form_valid(self, form):
        user = self.request.user
        form.instance.user = user
        return super(AccountCreateView, self).form_valid(form)


class AccountUpdateView(AccountBaseView, BSModalUpdateView):
    """View to update a account"""

    form_class = AccountForm
    success_message = "Success!"

    def get_queryset(self):
        qs = super().get_queryset()
        return qs.filter(
            pk=self.request.resolver_match.kwargs["pk"], user=self.request.user
        )


class AccountDeleteView(AccountBaseView, DeleteView):
    """View to delete a account"""

    def get_queryset(self):
        qs = super().get_queryset()
        return qs.filter(
            pk=self.request.resolver_match.kwargs["pk"], user=self.request.user
        )


class CategoryBaseView(LoginRequiredMixin, View):
    model = Category
    success_url = reverse_lazy("banking:category_list")


class CategoryListView(CategoryBaseView, ListView):
    extra_context = {"title": "Categories"}

    """View to list all categories.
    Use the 'category_list' variable in the template
    to access all Category objects"""

    def get_queryset(self):
        qs = super().get_queryset()
        return qs.filter(user=self.request.user)


class CategoryDetailView(CategoryBaseView, DetailView):
    """View to list the details from one category.
    Use the 'category' variable in the template to access
    the specific category here and in the Views below"""

    def get_queryset(self):
        qs = super().get_queryset()
        return qs.filter(
            pk=self.request.resolver_match.kwargs["pk"], user=self.request.user
        )


class CategoryCreateView(CategoryBaseView, BSModalCreateView):
    """View to create a new category"""

    form_class = CategoryForm
    success_message = "Success!"

    def get_initial(self):
        super().get_initial()
        if "type" in self.request.resolver_match.kwargs:
            self.initial["type"] = self.request.resolver_match.kwargs["type"]
        return self.initial

    def form_valid(self, form):
        user = self.request.user
        form.instance.user = user
        form.instance.sorting = Category.getLastSort(form.instance.nested_to, user)
        if "type" in self.request.resolver_match.kwargs:
            form.instance.type = self.request.resolver_match.kwargs["type"]
        if "nested_to_id" in self.request.resolver_match.kwargs:
            form.instance.nested_to = Category.objects.filter(
                user=user, id=self.request.resolver_match.kwargs["nested_to_id"]
            ).first()
        return super(CategoryCreateView, self).form_valid(form)


class CategoryUpdateView(CategoryBaseView, BSModalUpdateView):
    """View to update a category"""

    form_class = CategoryForm
    success_message = "Success!"

    def get_initial(self):
        super().get_initial()
        self.initial["type"] = self.object.type
        self.initial["id"] = self.object.id
        return self.initial

    def get_queryset(self):
        qs = super().get_queryset()
        return qs.filter(
            pk=self.request.resolver_match.kwargs["pk"], user=self.request.user
        )


class CategoryDeleteView(CategoryBaseView, DeleteView):
    """View to delete a category"""

    def get_queryset(self):
        qs = super().get_queryset()
        return qs.filter(
            pk=self.request.resolver_match.kwargs["pk"], user=self.request.user
        )


class TransactionBaseView(LoginRequiredMixin, View):
    model = Transaction
    success_url = reverse_lazy("banking:transaction_list")


class TransactionListView(TransactionBaseView, ListView):
    """View to list all transactions of given user.
    Use the 'transaction_list' variable in the template
    to access all Transaction objects"""

    def get_queryset(self, *args, **kwargs):
        qs = super(TransactionListView, self).get_queryset(*args, **kwargs)

        account_id = self.request.GET.get("account_id", None)
        account_name = self.request.GET.get("account_name", None)
        if account_name:
            account_id = (
                Account.objects.filter(
                    user=self.request.user, name__icontains=account_name
                )
                .first()
                .id
                if Account.objects.filter(
                    user=self.request.user, name__icontains=account_name
                ).first()
                else -1
            )
        transaction_description = self.request.GET.get("transaction_description", None)
        from_date = self.request.GET.get("from_date", None)
        until_date = self.request.GET.get("from_date", None)

        if account_id:
            qs = qs.filter(account__id=account_id)
        if from_date:
            qs = qs.filter(date__gte=from_date)
        if until_date:
            qs = qs.filter(date__lte=until_date)
        if transaction_description:
            qs = qs.filter(description__icontains=transaction_description)

        qs = (
            qs.filter(merged_to=None, account__user=self.request.user)
            .annotate(
                balance=models.Window(
                    models.Sum("value"), order_by=models.F("date").asc()
                ),
            )
            .order_by("date")
        )
        return qs

    def get_context_data(self, **kwargs):
        data = super().get_context_data(**kwargs)

        account_id = self.request.GET.get("account_id", None)
        account_name = self.request.GET.get("account_name", None)
        if account_name:
            account_id = (
                Account.objects.filter(
                    user=self.request.user, name__icontains=account_name
                )
                .first()
                .id
                if Account.objects.filter(
                    user=self.request.user, name__icontains=account_name
                ).first()
                else -1
            )
        transaction_description = self.request.GET.get("transaction_description", None)
        from_date = self.request.GET.get("from_date", None)
        until_date = self.request.GET.get("from_date", None)

        user = self.request.user
        qs = self.object_list.aggregate(
            first_date=models.Min("date"), last_date=models.Max("date")
        )
        data["first_date"] = qs["first_date"]
        data["last_date"] = qs["last_date"]

        if data["first_date"] and data["last_date"]:
            data["balance_first_date"] = (
                Transaction.objects.filter(
                    account__user=user, date__lt=data["first_date"], merged_to=None
                ).aggregate(balance=models.Sum("value"))["balance"]
                or 0
            )
            data["balance_last_date"] = (
                Transaction.objects.filter(
                    account__user=user, date__lte=data["last_date"], merged_to=None
                ).aggregate(balance=models.Sum("value"))["balance"]
                or 0
            )

        if account_id:
            data["account_id"] = account_id
            data["account"] = Account.objects.filter(id=data["account_id"]).first()
        if from_date:
            data["from_date"] = from_date
        if until_date:
            data["until_date"] = until_date
        if transaction_description:
            data["transaction_description"] = transaction_description

        return data


class TransactionDetailView(TransactionBaseView, DetailView):
    """View to list the details from one Transaction.
    Use the 'transaction' variable in the template to access
    the specific transaction here and in the Views below"""

    def get_queryset(self):
        qs = super().get_queryset()
        return qs.filter(
            pk=self.request.resolver_match.kwargs["pk"], account__user=self.request.user
        )


class TransactionCreateView(TransactionBaseView, BSModalCreateView):
    """View to create a new Transaction"""

    form_class = TransactionForm
    success_message = "Success!"


class TransactionUpdateView(TransactionBaseView, BSModalUpdateView):
    """View to update a Transaction"""

    form_class = TransactionForm
    success_message = "Success!"

    def get_queryset(self):
        qs = super().get_queryset()
        return qs.filter(
            pk=self.request.resolver_match.kwargs["pk"], account__user=self.request.user
        )


class TransactionDeleteView(BSModalFormView):
    form_class = TransactionDeleteForm
    template_name = "banking/transaction_confirm_delete.html"
    success_url = reverse_lazy("banking:transaction_list")

    def form_valid(self, form):
        Transaction.objects.filter(id__in=form.cleaned_data["id"]).delete()
        return super(TransactionDeleteView, self).form_valid(form)

    def get_queryset(self):
        qs = super().get_queryset()
        return qs.filter(
            pk=self.request.resolver_match.kwargs["pk"], user=self.request.user
        )

    def get_form_kwargs(self):
        form_kwargs = super(TransactionDeleteView, self).get_form_kwargs()
        query = self.request.resolver_match.kwargs["transaction_ids"].split(",")
        qs = Transaction.objects.filter(id__in=query, account__user=self.request.user)
        if qs.count() != len(query):
            raise PermissionDenied()
        form_kwargs["transaction_ids"] = [
            (transaction_id, transaction_id) for transaction_id in query
        ]
        form_kwargs["initial_transaction_ids"] = query
        return form_kwargs


class TransactionInternalTransferView(BSModalFormView):
    form_class = TransactionInternalTransferForm
    template_name = "banking/transaction_confirm_internal_transfer.html"
    success_url = reverse_lazy("banking:transaction_list")

    def form_valid(self, form):
        Transaction.objects.filter(id__in=form.cleaned_data["id"]).update(
            is_transfer=True, category=None
        )
        return super(TransactionInternalTransferView, self).form_valid(form)

    def get_form_kwargs(self):
        form_kwargs = super(TransactionInternalTransferView, self).get_form_kwargs()
        query = self.request.resolver_match.kwargs["transaction_ids"].split(",")
        qs = Transaction.objects.filter(id__in=query, account__user=self.request.user)
        if qs.count() != len(query):
            raise PermissionDenied()
        form_kwargs["transaction_ids"] = [
            (transaction_id, transaction_id) for transaction_id in query
        ]
        form_kwargs["initial_transaction_ids"] = query
        return form_kwargs


class TransactionCategorizeView(BSModalFormView):
    form_class = TransactionCategorizeForm
    template_name = "banking/transaction_categorize.html"
    success_url = reverse_lazy("banking:transaction_list")

    def form_valid(self, form):
        Transaction.objects.filter(id__in=form.cleaned_data["id"]).update(
            is_transfer=False, category=form.cleaned_data["category"]
        )
        return super(TransactionCategorizeView, self).form_valid(form)

    def get_form_kwargs(self):
        form_kwargs = super(TransactionCategorizeView, self).get_form_kwargs()
        query = self.request.resolver_match.kwargs["transaction_ids"].split(",")
        qs = Transaction.objects.filter(id__in=query, account__user=self.request.user)
        if qs.count() != len(query):
            raise PermissionDenied()
        form_kwargs["transaction_ids"] = [
            (transaction_id, transaction_id) for transaction_id in query
        ]
        form_kwargs["initial_transaction_ids"] = query
        return form_kwargs


def import_csv(request):
    TransactionFormSet = formset_factory(CSVConfirmImport, extra=0)
    formset = TransactionFormSet()
    helper = CSVConfirmImportFormSetHelper()
    if request.method == "POST":
        form_csv = CSVImportForm(request.POST, request.FILES)
        formset = TransactionFormSet(request.POST)

        # Before we validating our forms, we need to reinitiate all ChoiceFields choices, otherwite validation is going to fail...
        # form_csv account field:
        form_csv.fields["csv_account"].queryset = Account.objects.filter(user=request.user)
        # formset account and category fields:
        for form in formset.forms:
            form.fields[
                "category"
            ].choices = Category.getUserGroupedAndSortedCategories(request.user)
            form.fields["account"].queryset = Account.objects.filter(user=request.user)
        if formset.is_valid():
            for form in formset:
                form_data = form.cleaned_data
                if form_data and form_data["decision"] == "import":
                    Transaction.objects.create(
                        value=form_data["value"],
                        account=form_data["account"],
                        category=Category.objects.filter(
                            id=form_data["category"], user=request.user
                        ).first() if form_data["category"].isnumeric() else None,
                        is_transfer=form_data["is_transfer"],
                        concilied=form_data["concilied"],
                        date=form_data["date"],
                        competency_date=form_data["competency_date"],
                        description=form_data["description"],
                        merged_to=None,
                    )
            return redirect("banking:transaction_list")
        elif form_csv.is_valid():
            csv_file = request.FILES["csv_file"].read().decode("utf-8-sig").splitlines()
            csv_reader = csv.DictReader(csv_file)

            listOfTransactions = []
            for row in csv_reader:
                listOfTransactions.append(
                    {
                        "select_row": False,
                        "value": row["value"] if "value" in row else None,
                        "date": row["date"] if "date" in row else None,
                        "competency_date": row["competency_date"]
                        if "competency_date" in row
                        else None,
                        "description": row["description"]
                        if "description" in row
                        else None,
                        "account": Account.objects.filter(user=request.user, id=row["account_id"]).first()
                        if "account_id" in row
                        else form_csv.cleaned_data["csv_account"],
                        "category": Category.objects.filter(id=row["category_id"])
                        if "category_id" in row
                        else None,
                        "is_transfer": row["is_transfer"]
                        if "transfer" in row
                        else None,
                        "concilied": row["concilied"] if "concilied" in row else None,
                        "user": request.user,
                    }
                )
            TransactionFormSet = formset_factory(CSVConfirmImport, extra=0)

            formset = TransactionFormSet(initial=listOfTransactions)

            return render(
                request,
                "banking/transaction_import_form.html",
                {"formset": formset, "helper": helper},
            )
        else:
            return render(
                request,
                "banking/transaction_import_form.html",
                {"formset": formset, "helper": helper},
            )
    else:
        form_csv = CSVImportForm()
        form_csv.fields["csv_account"].queryset = Account.objects.filter(user=request.user)

    return render(request, "banking/transaction_import_form.html", {"form": form_csv})
