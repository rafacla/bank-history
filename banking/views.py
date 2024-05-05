import calendar

from datetime import date, datetime

from django.db import transaction
from bootstrap_modal_forms.generic import (BSModalCreateView,
                                           BSModalDeleteView, BSModalFormView,
                                           BSModalReadView, BSModalUpdateView)
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import PermissionDenied
from django.db import models
from django.forms import formset_factory
from django.shortcuts import redirect, render
from django.urls import reverse_lazy
from django.views import View
from django.views.generic import TemplateView
from django.views.generic.detail import DetailView
from django.views.generic.edit import (CreateView, DeleteView, FormView,
                                       UpdateView)
from django.views.generic.list import ListView

from banking import forms, models as bankingModels

from .forms import (AccountForm, CategoryForm, FileConfirmImport, FileImportForm,
                    InlineFormSetHelper, ModalDeleteForm, RuleRunForm,
                    TransactionCategorizeForm, TransactionForm,
                    TransactionInternalTransferForm)
from .models import Account, Category, Rule, Transaction
from .utils import strToDate_anyformat, lastDayOfMonth

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
        return qs.filter(user=self.request.user).order_by("type", "name")

    def get_context_data(self, **kwargs):
        data = super().get_context_data(**kwargs)

        accounts = Account.objects.filter(user=self.request.user)
        data["total_balance"] = 0
        data["accounts_balances"] = {}
        data["accounts_types"] = Account.ACCOUNT_TYPES

        for account in accounts:
            data["total_balance"] += account.getBalance()
            if account.type in data["accounts_balances"]:
                data["accounts_balances"][account.type] += account.getBalance()
            else:
                data["accounts_balances"][account.type] = account.getBalance()
            
        return data


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
            self.initial["id"] = None
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
        not_classified = self.request.GET.get("not_classified", None)
        not_concilied = self.request.GET.get("not_concilied", None)
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
            account = Account.objects.filter(id = account_id).first()
        else: 
            account = None
        if from_date:
            qs = qs.filter(date__gte=from_date)
        if until_date:
            qs = qs.filter(date__lte=until_date)
        if transaction_description:
            qs = qs.filter(description__icontains=transaction_description)
        if not_classified == '1':
            qs = qs.filter(category=None).filter(is_transfer=False)
        if not_concilied == '1':
            qs = qs.filter(concilied=False)
        
        if account and account.type == "creditCard" and not_classified != '1':
            statement_date = strToDate_anyformat(self.request.GET.get("statement_date", None))
            if (statement_date) == None:
                statement_date = date.today()
            statement_date = statement_date.replace(day=1)
            
            qs = qs.filter(models.Q(competency_date=None, date__lte=lastDayOfMonth(statement_date), date__gte=statement_date.replace(day=1)) | models.Q(competency_date__lte=lastDayOfMonth(statement_date), competency_date__gte=statement_date.replace(day=1)))
            
        qs = (
            qs.filter(merged_to=None, account__user=self.request.user)
            .annotate(
                balance=models.Window(
                    models.Sum("value"), order_by=models.F("date").asc()
                ),
            )
            .order_by("-date")
        )
        return qs

    def get_context_data(self, **kwargs):
        data = super().get_context_data(**kwargs)

        account_id = self.request.GET.get("account_id", None)
        account_name = self.request.GET.get("account_name", None)
        not_classified = self.request.GET.get("not_classified", 0)

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
        statement_date = strToDate_anyformat(self.request.GET.get("statement_date", None))
        if (statement_date) == None:
            statement_date = date.today()
        statement_date = statement_date.replace(day=1)

        user = self.request.user
        qs = self.object_list.aggregate(
            first_date=models.Min("date"), last_date=models.Max("date")
        )
        data["first_date"] = qs["first_date"]
        data["last_date"] = qs["last_date"]
        data["statement_date"] = statement_date
        data["not_classified"] = not_classified

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


        #if this is a CC Statement, we need to provide a few informations for the layout:
        if "account" in data and data["account"].type == "creditCard":
            data["months"] = Transaction.getMonthsWTransactions(account=data["account"])
            transactionsQueryBase = Transaction.objects.filter(account = data["account"])
            data["ccCurrentDebits"] = transactionsQueryBase.filter(value__lt=0).filter(models.Q(competency_date=None, date__lte=lastDayOfMonth(statement_date), date__gte=statement_date.replace(day=1)) | models.Q(competency_date__lte=lastDayOfMonth(statement_date), competency_date__gte=statement_date.replace(day=1))).aggregate(balance=models.Sum("value"))["balance"]
            data["ccCurrentPayments"] = transactionsQueryBase.filter(value__gt=0).filter(models.Q(competency_date=None, date__lte=lastDayOfMonth(statement_date), date__gte=statement_date.replace(day=1)) | models.Q(competency_date__lte=lastDayOfMonth(statement_date), competency_date__gte=statement_date.replace(day=1))).aggregate(balance=models.Sum("value"))["balance"]
            data["ccBalanceLastMonth"] = transactionsQueryBase.filter(models.Q(competency_date=None, date__lt=statement_date.replace(day=1)) | models.Q(competency_date__lt=statement_date.replace(day=1))).aggregate(balance=models.Sum("value"))["balance"]
            data["ccCurrentDebits"] = data["ccCurrentDebits"]*(-1) if data["ccCurrentDebits"] else 0
            data["ccCurrentPayments"] = data["ccCurrentPayments"]*(1) if data["ccCurrentPayments"] else 0
            data["ccBalanceLastMonth"] = data["ccBalanceLastMonth"] if data["ccBalanceLastMonth"] else 0
            data["ccDebits"] = data["ccCurrentDebits"] - data["ccBalanceLastMonth"]
            data["ccPaymentRatio"] = abs(round((100*(data["ccCurrentPayments"] if data["ccCurrentPayments"] else 0)/(data["ccDebits"])) if data["ccDebits"] else 100,2))
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

    def get_success_url(self):
        return (
            reverse_lazy("banking:transaction_list")
            + "?"
            + self.request.GET.urlencode(safe='&').replace('&amp%3B','&')
        )

    def form_valid(self, form):
        match form.cleaned_data["type"]:
            case "D":
                form.instance.value = (-1)*abs(form.cleaned_data["value"])
                form.instance.is_transfer = False
            case "C":
                form.instance.value = abs(form.cleaned_data["value"])
                form.instance.is_transfer = False
            case "IT":
                form.instance.value = abs(form.cleaned_data["value"])
                form.instance.is_transfer = True
                form.instance.category = None
            case "OT":
                form.instance.value = (-1)*abs(form.cleaned_data["value"])
                form.instance.is_transfer = True
                form.instance.category = None
        return super(TransactionCreateView, self).form_valid(form)


class TransactionUpdateView(TransactionBaseView, BSModalUpdateView):
    """View to update a Transaction"""

    form_class = TransactionForm
    success_message = "Success!"

    def get_success_url(self):
        return (
            reverse_lazy("banking:transaction_list")
            + "?"
            + self.request.GET.urlencode(safe='&').replace('&amp%3B','&')
        )

    def get_queryset(self):
        qs = super().get_queryset()
        return qs.filter(
            pk=self.request.resolver_match.kwargs["pk"], account__user=self.request.user
        )
    
    def get_form_kwargs(self):
        form_kwargs = super(TransactionUpdateView, self).get_form_kwargs()
        return form_kwargs

    def form_valid(self, form):
        match form.cleaned_data["type"]:
            case "D":
                form.instance.value = (-1)*abs(form.cleaned_data["value"])
                form.instance.is_transfer = False
            case "C":
                form.instance.value = abs(form.cleaned_data["value"])
                form.instance.is_transfer = False
            case "IT":
                form.instance.value = abs(form.cleaned_data["value"])
                form.instance.is_transfer = True
                form.instance.category = None
            case "OT":
                form.instance.value = (-1)*abs(form.cleaned_data["value"])
                form.instance.is_transfer = True
                form.instance.category = None
        return super(TransactionUpdateView, self).form_valid(form)

    def get_initial(self):
        initial_values = super().get_initial()
        transaction = self.object
        if transaction.is_transfer:
            if transaction.value < 0:
                initial_values["type"] = "OT"
                initial_values["value"] = abs(transaction.value)
            else:
                initial_values["type"] = "IT"
        else:
            if transaction.value < 0:
                initial_values["type"] = "D"
                initial_values["value"] = abs(transaction.value)
            else:
                initial_values["type"] = "C"
        return initial_values


class TransactionDeleteView(BSModalFormView):
    form_class = ModalDeleteForm
    template_name = "banking/modal_confirm_delete.html"

    def get_success_url(self):
        return (
            reverse_lazy("banking:transaction_list")
            + "?"
            + self.request.GET.urlencode(safe='&').replace('&amp%3B','&')
        )

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
        query = self.request.resolver_match.kwargs["ids"].split(",")
        qs = Transaction.objects.filter(id__in=query, account__user=self.request.user)
        if qs.count() != len(query):
            raise PermissionDenied()
        form_kwargs["ids"] = [
            (transaction_id, transaction_id) for transaction_id in query
        ]
        form_kwargs["initial_ids"] = query
        return form_kwargs


class TransactionInternalTransferView(BSModalFormView):
    form_class = TransactionInternalTransferForm
    template_name = "banking/transaction_confirm_internal_transfer.html"

    def get_success_url(self):
        return (
            reverse_lazy("banking:transaction_list")
            + "?"
            + self.request.GET.urlencode(safe='&').replace('&amp%3B','&')
        )

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


class TransactionMergeView(BSModalFormView):
    form_class = TransactionInternalTransferForm
    template_name = "banking/transaction_confirm_merge.html"

    def get_success_url(self):
        return (
            reverse_lazy("banking:transaction_list")
            + "?"
            + self.request.GET.urlencode(safe='&').replace('&amp%3B','&')
        )

    def form_valid(self, form):

        Transaction.objects.filter(id__in=form.cleaned_data["id"]).exclude(id=min(form.cleaned_data["id"])).update(
            merged_to=min(form.cleaned_data["id"])
        )
        return super(TransactionMergeView, self).form_valid(form)

    def get_form_kwargs(self):
        form_kwargs = super(TransactionMergeView, self).get_form_kwargs()
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

    def get_success_url(self):
        return (
            reverse_lazy("banking:transaction_list")
            + "?"
            + self.request.GET.urlencode(safe='&').replace('&amp%3B','&')
        )

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


def import_file(request):
    if request.user.is_authenticated == False:
        return redirect("banking:home")
    
    TransactionFormSet = formset_factory(FileConfirmImport, extra=0)
    formset = TransactionFormSet()
    helper = InlineFormSetHelper()
    if request.method == "POST":
        fileImportForm = FileImportForm(request.POST, request.FILES)
        formset = TransactionFormSet(request.POST)

        # Before we validating our forms, we need to reinitiate all ChoiceFields choices, otherwite validation is going to fail...
        # fileImportForm account field:
        fileImportForm.fields["import_account"].queryset = Account.objects.filter(
            user=request.user
        )
        # formset account and category fields:
        for form in formset.forms:
            form.fields[
                "category"
            ].choices = Category.getUserGroupedAndSortedCategories(request.user)
            form.fields["account"].queryset = Account.objects.filter(user=request.user)
        if formset.is_valid():
            importedListIds = []
            for form in formset:
                form_data = form.cleaned_data
                if form_data and form_data["decision"] == "import":
                    importedListIds.append(Transaction.objects.create(
                        value=form_data["value"],
                        account=form_data["account"],
                        category=Category.objects.filter(
                            id=form_data["category"], user=request.user
                        ).first()
                        if form_data["category"].isnumeric()
                        else None,
                        is_transfer=form_data["is_transfer"],
                        concilied=form_data["concilied"],
                        date=form_data["date"],
                        competency_date=form_data["competency_date"],
                        description=form_data["description"],
                        merged_to=None,
                    ).id)
            for rule in Rule.objects.filter(user=request.user,runs_on_imported_transactions=True):
                rule.applyRule(transactionsIds=importedListIds)
            return redirect(reverse_lazy("banking:transaction_list")
            + "?"
            + request.GET.urlencode(safe='&').replace('&amp%3B','&'))
        elif "formset-submit" in request.POST:
            return render(
                request,
                "banking/transaction_import_form.html",
                {"formset": formset, "helper": helper},
            )
        elif fileImportForm.is_valid():
            listOfTransactions = fileImportForm.cleaned_data["listOfTransactions"]
            TransactionFormSet = formset_factory(FileConfirmImport, extra=0)

            formset = TransactionFormSet(initial=listOfTransactions, form_kwargs={'user': request.user})

            return render(
                request,
                "banking/transaction_import_form.html",
                {"formset": formset, "helper": helper},
            )
        else:
            return render(
                request,
                "banking/transaction_import_form.html",
                {"form": fileImportForm},
            )
    else:
        fileImportForm = FileImportForm()
        fileImportForm.fields["import_account"].queryset = Account.objects.filter(
            user=request.user
        )

    return render(request, "banking/transaction_import_form.html", {"form": fileImportForm})


class DashboardView(LoginRequiredMixin, TemplateView):
    template_name = "banking/dashboard.html"

    def get(self, request, *args, **kwargs):
        data = dict()
        data["filtered_month"] = self.request.GET.get(
            "month", date.today().strftime("%Y-%m")
        )

        date_from = datetime.strptime(data["filtered_month"] + "-01", "%Y-%m-%d").date()
        date_to = datetime.strptime(
            data["filtered_month"]
            + "-"
            + str(calendar.monthrange(date_from.year, date_from.month)[1]),
            "%Y-%m-%d",
        ).date()

        userTransactions = Transaction.objects.filter(
            account__user=self.request.user, is_transfer=False
        ).filter(
            (models.Q(competency_date__isnull=True)
            & models.Q(date__lte=date_to)
            & models.Q(date__gte=date_from))
            | (models.Q(competency_date__isnull=False)
            & models.Q(competency_date__lte=date_to)
            & models.Q(competency_date__gte=date_from))
        )
        userCreditTransactions = userTransactions.filter(value__gt=0)
        userDebitTransactions = userTransactions.filter(value__lt=0)

        data["sumOfCreditTransactions"] = (
            userCreditTransactions.aggregate(incurred=models.Sum("value"))["incurred"]
            or 0
        )
        data["sumOfDebitTransactions"] = (
            userDebitTransactions.aggregate(incurred=-models.Sum("value"))["incurred"]
            or 0
        )
        data["topTenCreditCategories"] = (
            userCreditTransactions.filter(category__isnull=False)
            .values("category__name")
            .annotate(
                incurred=models.Sum("value"),
                ratio=100 * models.Sum("value") / data["sumOfCreditTransactions"],
            )
            .order_by("-incurred")
        )[:10]
        data["topTenDebitCategories"] = (
            userDebitTransactions.filter(category__isnull=False)
            .values("category__name")
            .annotate(
                incurred=-models.Sum("value"),
                ratio=-100 * models.Sum("value") / data["sumOfDebitTransactions"],
            )
            .order_by("-incurred")
        )[:10]
        data["sumOfNotClassifiedCreditTransactions"] = (
            userCreditTransactions.filter(category__isnull=True).aggregate(
                incurred=models.Sum("value")
            )["incurred"]
            or 0
        )
        data["sumOfNotClassifiedDebitTransactions"] = (
            userDebitTransactions.filter(category__isnull=True).aggregate(
                incurred=models.Sum("value")
            )["incurred"]
            or 0
        ) * (-1)
        data["ratioOfNotClassifiedCreditTransactions"] = (
            100
            * data["sumOfNotClassifiedCreditTransactions"]
            / data["sumOfCreditTransactions"]
            if data["sumOfCreditTransactions"]
            else 0
        )
        data["ratioOfNotClassifiedDebitTransactions"] = (
            100
            * data["sumOfNotClassifiedDebitTransactions"]
            / data["sumOfDebitTransactions"]
            if data["sumOfDebitTransactions"]
            else 0
        )
        return render(
            request,
            self.template_name,
            data,
        )


class RuleBaseView(LoginRequiredMixin, View):
    model = Rule
    success_url = reverse_lazy("banking:rule_list")


class RuleListView(RuleBaseView, ListView):
    def get_queryset(self):
        qs = super().get_queryset()
        return qs.filter(user=self.request.user).order_by("sorting")
            
        return data


class RuleRunView(BSModalFormView):
    form_class = RuleRunForm
    template_name = "banking/rule_run.html"

    def get_success_url(self):
        return (
            reverse_lazy("banking:rule_list")
        )

    def form_valid(self, form):
        # Run the Rules here:
        if form.cleaned_data["id"][0] == 'all':
            rules = Rule.objects.filter(user=self.request.user)
        else:
            rules = Rule.objects.filter(id__in=form.cleaned_data["id"], user=self.request.user)
        for rule in rules:
            rule.applyRule()
        return super(RuleRunView, self).form_valid(form)

    def get_form_kwargs(self):
        form_kwargs = super(RuleRunView, self).get_form_kwargs()
        query = self.request.resolver_match.kwargs["ids"].split(",")

        if query[0] == "all":
            qs = Rule.objects.filter(user=self.request.user)
        else:
            qs = Rule.objects.filter(id__in=query, user=self.request.user)
            if qs.count() != len(query):
                raise PermissionDenied()
        form_kwargs["ids"] = [
            (id, id) for id in query
        ]
        form_kwargs["initial_ids"] = query
        return form_kwargs


class RuleTestView(BSModalFormView):
    form_class = RuleRunForm
    template_name = "banking/rule_test.html"

    def get_success_url(self):
        return (
            reverse_lazy("banking:rule_list")
        )

    def get_context_data(self, **kwargs):
        context = super(RuleTestView, self).get_context_data(**kwargs)
        query = self.request.resolver_match.kwargs["ids"].split(",")
        rules = Rule.objects.filter(user=self.request.user, id__in=query)
        transactions_ids = []
        for rule in rules:
            transactions_ids.extend(rule.getApplicableTransactions().values_list('id', flat=True))
        
        transactions = Transaction.objects.filter(id__in=transactions_ids)

        context['transactions'] = transactions[:20]
        return context

    def form_valid(self, form):
        # Run the Rules here:
        if form.cleaned_data["id"][0] == 'all':
            rules = Rule.objects.filter(user=self.request.user)
        else:
            rules = Rule.objects.filter(id__in=form.cleaned_data["id"], user=self.request.user)
        for rule in rules:
            rule.applyRule()
        return super(RuleTestView, self).form_valid(form)

    def get_form_kwargs(self):
        form_kwargs = super(RuleTestView, self).get_form_kwargs()
        query = self.request.resolver_match.kwargs["ids"].split(",")

        if query[0] == "all":
            qs = Rule.objects.filter(user=self.request.user)
        else:
            qs = Rule.objects.filter(id__in=query, user=self.request.user)
            if qs.count() != len(query):
                raise PermissionDenied()
        form_kwargs["ids"] = [
            (id, id) for id in query
        ]
        form_kwargs["initial_ids"] = query
        return form_kwargs


class RuleDeleteView(BSModalFormView):
    form_class = ModalDeleteForm
    template_name = "banking/modal_confirm_delete.html"
    success_url = reverse_lazy("banking:rule_list")

    def get_success_url(self):
        return (
            reverse_lazy("banking:rule_list")
        )

    def form_valid(self, form):   
        qs = Rule.objects.filter(id__in=form.cleaned_data["id"], user=self.request.user)
        if qs.count() != len(form.cleaned_data["id"]):
            redirect("banking:rule_list") 
        else:
            Rule.objects.filter(id__in=form.cleaned_data["id"]).delete()
        return super(RuleDeleteView, self).form_valid(form)

    def get_queryset(self):
        qs = super().get_queryset()
        return qs.filter(
            pk=self.request.resolver_match.kwargs["pk"], user=self.request.user
        )

    def get_form_kwargs(self):
        form_kwargs = super(RuleDeleteView, self).get_form_kwargs()
        query = self.request.resolver_match.kwargs["ids"].split(",")
        form_kwargs["ids"] = [
            (id, id) for id in query
        ]
        form_kwargs["initial_ids"] = query
        return form_kwargs


class RuleCreateView(RuleBaseView, BSModalCreateView):
    """View to create a new account"""
    extra_context = {"title": "Create Rule"}
    form_class = forms.RuleForm
    success_message = "Success!"
    template_name = "banking/modal_form.html"
    helper = InlineFormSetHelper()

    def form_valid(self, form):
        context = self.get_context_data()
        inline_formset = context['inline_formset']
        with transaction.atomic():
            user = self.request.user
            form.instance.user = user
            form.instance.created_when = datetime.now()
            form.instance.modified_when = datetime.now()
            self.object = form.save()
            if inline_formset.is_valid():
                inline_formset.instance = self.object
                inline_formset.save()
        return super(RuleCreateView, self).form_valid(form)

    def get_context_data(self, **kwargs):
        context = super(RuleCreateView, self).get_context_data(**kwargs)
        context['helper'] = self.helper
        context['inline_formset'] = forms.RulesItemsFormsetCreate(self.request.POST or None, instance=self.object, form_kwargs={"user": self.request.user, "request": self.request})
        return context


class RuleUpdateView(RuleBaseView, BSModalUpdateView):
    """View to update a account"""
    extra_context = {"title": "Modify Rule"}
    form_class = forms.RuleForm
    success_message = "Success!"
    template_name = "banking/modal_form.html"
    helper = InlineFormSetHelper()

    def get_queryset(self):
        qs = super().get_queryset()
        return qs.filter(
            pk=self.request.resolver_match.kwargs["pk"], user=self.request.user
        )

    def form_valid(self, form):
        context = self.get_context_data()
        inline_formset = context['inline_formset']
        with transaction.atomic():
            form.instance.modified_when = datetime.now()
            self.object = form.save()
            if inline_formset.is_valid():
                inline_formset.instance = self.object
                inline_formset.save()
        
        return super(RuleUpdateView, self).form_valid(form)

    def get_context_data(self, **kwargs):
        context = super(RuleUpdateView, self).get_context_data(**kwargs)
        context['helper'] = self.helper
        context['inline_formset'] = forms.RulesItemsFormsetUpdate(self.request.POST or None, instance=self.object, form_kwargs={"user": self.request.user, "request":self.request})
        return context
        