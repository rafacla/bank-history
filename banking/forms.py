import csv
import datetime

from bootstrap_modal_forms.forms import BSModalForm, BSModalModelForm
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, Fieldset, Div, Submit, Field
from crispy_forms.bootstrap import InlineRadios
from django import forms
from django.core.exceptions import ValidationError
from django.forms.models import inlineformset_factory

from banking import models
from banking.models import Account, Category, Transaction
from banking.widgets import CategorySelect
from banking.utils import parseCSV, parseXLSX, strToDate_anyformat
from banking.pdfparser.pdfparser import PDFParser

class AccountForm(BSModalModelForm):
    class Meta:
        model = Account
        fields = [
            "name",
            "type",
            "closing_day",
            "due_day",
            "bank",
            "currency",
            "incur_on_competency"
        ]

    def __init__(self, *args, **kwargs):
        super(AccountForm, self).__init__(*args, **kwargs)


class CategoryForm(BSModalModelForm):
    class Meta:
        model = Category
        fields = ["name", "nested_to"]

    def __init__(self, *args, **kwargs):
        super(CategoryForm, self).__init__(*args, **kwargs)
        if "type" in kwargs["initial"]:
            self.fields["nested_to"].queryset = Category.objects.filter(
                type=kwargs["initial"]["type"], nested_to=None
            )
            if "id" in kwargs["initial"]:
                self.fields["nested_to"].queryset = self.fields[
                    "nested_to"
                ].queryset.exclude(id=kwargs["initial"]["id"])
        self.fields["nested_to"].queryset = self.fields["nested_to"].queryset.filter(
            user=self.request.user
        )


class TransactionForm(BSModalModelForm):
    class Meta:
        model = Transaction
        fields = [
            "account",
            "date",
            "competency_date",
            "description",
            "is_transfer",
            "category",
            "concilied",
            "value",
            "notes",
            "budget_incur_type"
        ]
        widgets = {
            "category": CategorySelect,
            "date": forms.NumberInput(attrs={"type": "date"}),
            "competency_date": forms.NumberInput(attrs={"type": "date"}),
            "notes": forms.Textarea(attrs={"rows": 3}),
        }

    type = forms.ChoiceField(
        choices=[
            ("D", "Debit"),
            ("C", "Credit"),
            ("IT", "Inbound Transfer"),
            ("OT", "Outbound Transfer"),
        ],
        widget=forms.RadioSelect,
        required=True
    )

    def __init__(self, *args, **kwargs):
        super(TransactionForm, self).__init__(*args, **kwargs)
        # Here we pull the user accounts to fill the select box with options
        self.fields["account"].queryset = Account.objects.filter(user=self.request.user)
        # If user has already filtered an account and is creating a transaction, odds are that user wants to add a transaction in this account
        # So we take it from URL:
        account = Account.objects.filter(
            user=self.request.user, pk=self.request.GET.get("account_id")
        ).first()
        # Here we want to start the new transaction form with statement due date if user is creating transaction from statement view
        # So we check if the account filtered is a credit card
        if account:
            self.fields["account"].initial = account
            if account.type == 'creditCard':
                diaVencimento = account.due_day if account.due_day else 1
                # For the current month, URL won't have a query parameter named statement_date, so we need to figure it out
                if self.request.GET.get("statement_date"):
                    self.fields["competency_date"].initial = datetime.date(strToDate_anyformat(self.request.GET.get("statement_date")).year, strToDate_anyformat(self.request.GET.get("statement_date")).month, diaVencimento)
                else:
                    self.fields["competency_date"].initial = datetime.date(datetime.date.today().year, datetime.date.today().month, diaVencimento)

        # Fill the select box of categories:
        self.fields["category"].choices = Category.getUserGroupedAndSortedCategories(
            self.request.user
        )

        # Here we design the form layout using crispy forms:
        self.helper = FormHelper()
        self.helper.form_tag = False
        self.helper.layout = Layout(
            Fieldset(
                "",
                "account",
                Div(
                    Field("date", wrapper_class="col-md-6"),
                    Field("competency_date", wrapper_class="col-md-6"),
                    css_class="row",
                ),
                "description",
                Field("type", template="tabler_crispy/selectbox.html"),
                "category",
                "concilied",
                "value",
                "notes",
                "budget_incur_type",
            ),
        )


class ModalDeleteForm(BSModalForm):
    id = forms.MultipleChoiceField()

    class Meta:
        fields = ["id"]

    def __init__(self, ids, initial_ids, *args, **kwargs):
        super(ModalDeleteForm, self).__init__(*args, **kwargs)
        self.fields["id"].choices = ids
        self.initial["id"] = list(initial_ids)
        self.fields["id"].widget = forms.MultipleHiddenInput()


class TransactionInternalTransferForm(BSModalForm):
    id = forms.MultipleChoiceField()

    class Meta:
        fields = ["id"]

    def __init__(self, transaction_ids, initial_transaction_ids, *args, **kwargs):
        super(TransactionInternalTransferForm, self).__init__(*args, **kwargs)
        self.fields["id"].choices = transaction_ids
        self.initial["id"] = list(initial_transaction_ids)
        self.fields["id"].widget = forms.MultipleHiddenInput()


class TransactionCategorizeForm(BSModalForm):
    id = forms.MultipleChoiceField()
    category = forms.ChoiceField(choices=[], required=False, widget=CategorySelect)

    class Meta:
        fields = ["id", "category"]
        widgets = {"category": CategorySelect}

    def __init__(self, transaction_ids, initial_transaction_ids, *args, **kwargs):
        super(TransactionCategorizeForm, self).__init__(*args, **kwargs)
        self.fields["id"].choices = transaction_ids
        self.initial["id"] = list(initial_transaction_ids)
        self.fields["id"].widget = forms.MultipleHiddenInput()
        self.fields["category"].choices = Category.getUserGroupedAndSortedCategories(
            self.request.user
        )


class FileImportForm(forms.Form):
    import_account = forms.ModelChoiceField(
        queryset=Account.objects.none(), label="Select account to import to:"
    )
    import_file = forms.FileField(label="File to Import:")

    def clean(self):
        cd = self.cleaned_data

        # Check file format, and call the correct parser:
        if "import_file" in cd:
            listOfTransactions = []
            if cd["import_file"].name.endswith(".csv"):
                listOfTransactions = parseCSV(cd["import_file"])
            elif cd["import_file"].name.endswith(".pdf"):
                pdfFile = PDFParser(cd["import_file"].read())
                listOfTransactions = pdfFile.parse()
                #listOfTransactions = parsePDF(cd["import_file"])
            elif cd["import_file"].name.endswith(".xlsx") or cd[
                "import_file"
            ].name.endswith(".xls"):
                listOfTransactions = parseXLSX(cd["import_file"])
            else:
                raise ValidationError("File format not supported")

            # With list of transactions parsed from file, we procceed to find the account and check if duplicated:
            for transaction in listOfTransactions:
                # let's try to parse account from imported file, if not we use the import account:
                if transaction["account_id"]:
                    account = (
                        Account.objects.filter(user=user)
                        .filter(id=tansaction["account_id"])
                        .first()
                    )
                elif transaction["account_name"]:
                    account = (
                        Account.objects.filter(user=user)
                        .filter(name__icontains=tansaction["account_name"])
                        .first()
                    )
                else:
                    account = None
                if account:
                    transaction["account"] = account
                else:
                    transaction["account"] = cd["import_account"]

                # here we work in a filter to detect possible duplicated transactions:
                duplicated_transaction = Transaction.objects.filter(
                    account=transaction["account"],
                    value=transaction["value"],
                    date=transaction["date"],
                ).first()

                # now we are going to do a basic check, if the description is the same, we can be sure that this is probably a duplicated transaction
                # users can make a purchase of same value twice (or more) in the same store and same day? they can, but this is not the case in 99% of times
                # we also remove spaces to compare because sometimes the file can have trailing spaces between words that can vary (I'm talking about you Santander Brasil)
                if duplicated_transaction:
                    if (
                        duplicated_transaction.description.replace(" ", "").upper()
                        != transaction["description"].replace(" ", "").upper()
                    ):
                        duplicated_transaction = None

                transaction["decision"] = (
                    "do_not_import" if duplicated_transaction != None else "import"
                )
                transaction["duplicated_transaction"] = duplicated_transaction

            cd["listOfTransactions"] = listOfTransactions
        return cd


class FileConfirmImport(forms.Form):
    select_row = forms.CheckboxInput()
    account = forms.ModelChoiceField(queryset=Account.objects.none())
    date = forms.DateField()
    competency_date = forms.DateField(required=False)
    description = forms.CharField()
    is_transfer = forms.BooleanField(required=False)
    category = forms.ChoiceField(required=False, widget=CategorySelect)
    concilied = forms.BooleanField(required=False)
    value = forms.DecimalField(decimal_places=2)
    decision = forms.ChoiceField(
        choices=[("import", "Import"), ("do_not_import", "Do not Import")]
    )

    def __init__(self, *args, user=None, **kwargs):
        super(FileConfirmImport, self).__init__(*args, **kwargs)

        if user:
            self.fields["category"].choices = (
                Category.getUserGroupedAndSortedCategories(user)
            )
            self.fields["account"].queryset = Account.objects.filter(user=user)


class InlineFormSetHelper(FormHelper):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.form_method = "post"
        self.form_tag = False
        self.render_required_fields = (True,)
        self.template = "form_helpers/table_inline_formset.html"


class RuleRunForm(BSModalForm):
    id = forms.MultipleChoiceField()

    class Meta:
        fields = ["id"]

    def __init__(self, ids, initial_ids, *args, **kwargs):
        super(RuleRunForm, self).__init__(*args, **kwargs)
        self.fields["id"].choices = ids
        self.initial["id"] = list(initial_ids)
        self.fields["id"].widget = forms.MultipleHiddenInput()


class RuleForm(BSModalModelForm):
    class Meta:
        model = models.Rule
        fields = [
            "active",
            "description",
            "sorting",
            "runs_on_already_classified_transactions",
            "runs_on_imported_transactions",
            "apply_category",
            "set_as_transfer",
        ]


class RulesItemForm(BSModalModelForm):
    class Meta:
        fields = (
            "boolean_type",
            "account",
            "value_type",
            "value",
            "description_type",
            "description",
            "date_type",
            "date",
            "competency_date_type",
            "competency_date",
        )

    def __init__(self, *args, user, **kwargs):
        super(RulesItemForm, self).__init__(*args, **kwargs)
        self.fields["account"].queryset = Account.objects.filter(user=user)


RulesItemsFormsetCreate = inlineformset_factory(
    models.Rule, models.RulesItem, RulesItemForm, extra=1
)
RulesItemsFormsetUpdate = inlineformset_factory(
    models.Rule, models.RulesItem, RulesItemForm, extra=0
)
