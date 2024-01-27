import csv

from bootstrap_modal_forms.forms import BSModalForm, BSModalModelForm
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Submit
from django import forms
from django.core.exceptions import ValidationError
from django.forms.models import inlineformset_factory

from banking import models
from banking.models import Account, Category, Transaction
from banking.widgets import CategorySelect
from banking.utils import strToDate_anyformat


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
        ]
        widgets = {
            "category": CategorySelect,
            "date": forms.NumberInput(attrs={"type": "date"}),
            "competency_date": forms.NumberInput(attrs={"type": "date"}),
            "notes": forms.Textarea(attrs={"rows": 3}),
        }

    def __init__(self, *args, **kwargs):
        super(TransactionForm, self).__init__(*args, **kwargs)
        self.fields["account"].queryset = Account.objects.filter(user=self.request.user)
        self.fields["category"].choices = Category.getUserGroupedAndSortedCategories(
            self.request.user
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

        # Check file format, for now we consider only CSV:
        if ("import_file" in cd):
            import_file = cd["import_file"].read().decode("utf-8-sig").splitlines()
            csv_reader = csv.DictReader(import_file)

            listOfTransactions = []
            for row in csv_reader:
                if not "value" in row or not "date" in row or not "description" in row:
                    raise ValidationError(
                        "CSV file doesn't have all the columns needed: date, description and value"
                    )
                    break
                # we try to convert the dates:
                row["value"] = row["value"].replace(" ","")
                row["date"] = strToDate_anyformat(row["date"])
                # here we work in a filter to detect possible duplicated transactions:
                duplicated_transaction = Transaction.objects.filter(account__id=row["account_id"] if "account_id" in row
                        else cd["import_account"].id,value=row["value"], date=row["date"]).first()
                
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
                        "account": cd["import_account"],
                        "category": Category.objects.filter(id=row["category_id"])
                        if "category_id" in row
                        else None,
                        "is_transfer": row["is_transfer"]
                        if "transfer" in row
                        else None,
                        "concilied": row["concilied"] if "concilied" in row else None,
                        "decision": "do_not_import" if duplicated_transaction != None else "import",
                        "duplicated_transaction": duplicated_transaction,
                    }
                )
            
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
            self.fields[
                "category"
            ].choices = Category.getUserGroupedAndSortedCategories(user)
            self.fields["account"].queryset = Account.objects.filter(
                user=user
            )


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
            "set_as_transfer"
        ]

class RulesItemForm(BSModalModelForm):
    class Meta:
        fields=("boolean_type","account","value_type","value","description_type","description","date_type","date","competency_date_type","competency_date",)

    def __init__(self, *args, user, **kwargs):
        super(RulesItemForm, self).__init__(*args, **kwargs)
        self.fields["account"].queryset = Account.objects.filter(user = user)



RulesItemsFormsetCreate = inlineformset_factory(
    models.Rule, models.RulesItem, RulesItemForm, extra=1
)
RulesItemsFormsetUpdate = inlineformset_factory(
    models.Rule, models.RulesItem, RulesItemForm, extra=0
)
