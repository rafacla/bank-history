import calendar
import csv
import re
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

from .forms import (AccountForm, CategoryForm, CSVConfirmImport, CSVImportForm,
                    InlineFormSetHelper, ModalDeleteForm, RuleRunForm,
                    TransactionCategorizeForm, TransactionForm,
                    TransactionInternalTransferForm)
from .models import Account, Category, Rule, Transaction


def strToDate_anyformat(format_date, expected_format = ""):
        numbers = ''.join(re.findall(r'\d+', format_date))
        if ("/" in format_date or expected_format.upper() == "%D/%M/%Y" or expected_format.upper() == "%M/%D/%Y"):
            #in this case, we consider the date as short_date, defaulting to %d/%m/%Y
            if (expected_format == "" or expected_format.upper() == "%D/%M/%Y"):
                if len(numbers) == 8 and int(numbers[2:4]) <= 12:
                    d = datetime(int(numbers[4:8]), int(numbers[2:4]), int(numbers[:2]))
                elif len(numbers) == 6:
                    d = datetime(int(numbers[4:6])+2000, int(numbers[2:4]), int(numbers[:2]))
                else:
                    raise AssertionError(f'length not match:{format_date} or doesn\'t fit the expected format: '+expected_format)
            else:
                #it's in american standard:
                if len(numbers) == 8 and int(numbers[:2]) <= 12:
                    d = datetime(int(numbers[4:8]), int(numbers[:2]), int(numbers[2:4]))
                elif len(numbers) == 6:
                    d = datetime(int(numbers[4:6])+2000, int(numbers[:2]), int(numbers[2:4]))
                else:
                    raise AssertionError(f'length not match:{format_date} or doesn\'t fit the expected format: '+expected_format)
        else:
            #else, it's a full date:
            if len(numbers) == 8:
                d = datetime(int(numbers[:4]), int(numbers[4:6]), int(numbers[6:8]))
            elif len(numbers) == 14:
                d = datetime(int(numbers[:4]), int(numbers[4:6]), int(numbers[6:8]), int(numbers[8:10]), int(numbers[10:12]), int(numbers[12:14]))
            elif len(numbers) > 14:
                d = datetime(int(numbers[:4]), int(numbers[4:6]), int(numbers[6:8]), int(numbers[8:10]), int(numbers[10:12]), int(numbers[12:14]), microsecond=1000*int(numbers[14:]))
            else:
                raise AssertionError(f'length not match:{format_date}')
        return d


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
    form_class = ModalDeleteForm
    template_name = "banking/modal_confirm_delete.html"

    def get_success_url(self):
        return (
            reverse_lazy("banking:transaction_list")
            + "?"
            + self.request.GET.urlencode()
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
            + self.request.GET.urlencode()
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
            + self.request.GET.urlencode()
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
            + self.request.GET.urlencode()
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


def import_csv(request):
    if request.user.is_authenticated == False:
        return redirect("banking:home")
    
    TransactionFormSet = formset_factory(CSVConfirmImport, extra=0)
    formset = TransactionFormSet()
    helper = InlineFormSetHelper()
    if request.method == "POST":
        form_csv = CSVImportForm(request.POST, request.FILES)
        formset = TransactionFormSet(request.POST)

        # Before we validating our forms, we need to reinitiate all ChoiceFields choices, otherwite validation is going to fail...
        # form_csv account field:
        form_csv.fields["csv_account"].queryset = Account.objects.filter(
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
            return redirect("banking:transaction_list")
        elif form_csv.is_valid():
            csv_file = form_csv.cleaned_data["csv_file"]
            csv_reader = csv.DictReader(csv_file)

            listOfTransactions = []
            for row in csv_reader:
                # we try to convert the dates:
                row["value"] = row["value"].replace(" ","")
                row["date"] = strToDate_anyformat(row["date"])
                # here we work in a filter to detect possible duplicated transactions:
                duplicated_transaction = Transaction.objects.filter(account__id=row["account_id"] if "account_id" in row
                        else form_csv.cleaned_data["csv_account"].id,value=row["value"], date=row["date"]).first()
                
                #now we are going to do a basic check, if the description is the same, we can be sure that this is probably a duplicated transaction
                #users can make a purchase of same value twice (or more) in the same store and same day? they can, but this is not the case in 99% of times
                #we also remove spaces to compare because sometimes the file can have trailing spaces between words that can vary (I'm talking about you Santander Brasil)
                if duplicated_transaction:
                    if duplicated_transaction.description.replace(" ","").upper() != row["description"].replace(" ","").upper():
                        duplicated_transaction = None
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
                        "account": Account.objects.filter(
                            user=request.user, id=row["account_id"]
                        ).first()
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
                        "decision": "do_not_import" if duplicated_transaction != None else "import",
                        "duplicated_transaction": duplicated_transaction,
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
                {"form": form_csv},
            )
    else:
        form_csv = CSVImportForm()
        form_csv.fields["csv_account"].queryset = Account.objects.filter(
            user=request.user
        )

    return render(request, "banking/transaction_import_form.html", {"form": form_csv})


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

        data["filteredRule"] = Rule.objects.filter(user=self.request.user).first().getApplicableTransactions()
        Rule.objects.filter(user=self.request.user).first().applyRule()
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
        