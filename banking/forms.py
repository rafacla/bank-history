from django import forms
from banking.models import Account, Category, Transaction
from banking.widgets import CategorySelect
from bootstrap_modal_forms.forms import BSModalModelForm, BSModalForm


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
                self.fields["nested_to"].queryset = self.fields["nested_to"].queryset.exclude(id=kwargs["initial"]["id"])
        self.fields["nested_to"].queryset = self.fields["nested_to"].queryset.filter(user=self.request.user)


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
        ]
        widgets = {"category": CategorySelect}

    def __init__(self, *args, **kwargs):
        super(TransactionForm, self).__init__(*args, **kwargs)
        self.fields["account"].queryset = Account.objects.filter(user=self.request.user)
        self.fields["category"].choices = Category.getUserGroupedAndSortedCategories(self.request.user)
        

class TransactionDeleteForm(BSModalForm):
    id = forms.MultipleChoiceField()

    class Meta:
        fields = ['id']

    def __init__(self, transaction_ids, initial_transaction_ids, *args, **kwargs):
        super(TransactionDeleteForm, self).__init__(*args, **kwargs)
        self.fields['id'].choices = transaction_ids
        self.initial['id'] = list(initial_transaction_ids)
        self.fields['id'].widget = forms.MultipleHiddenInput()


class TransactionInternalTransferForm(BSModalForm):
    id = forms.MultipleChoiceField()

    class Meta:
        fields = ['id']

    def __init__(self, transaction_ids, initial_transaction_ids, *args, **kwargs):
        super(TransactionInternalTransferForm, self).__init__(*args, **kwargs)
        self.fields['id'].choices = transaction_ids
        self.initial['id'] = list(initial_transaction_ids)
        self.fields['id'].widget = forms.MultipleHiddenInput()


class TransactionCategorizeForm(BSModalForm):
    id = forms.MultipleChoiceField()
    category = forms.ChoiceField(choices=[], required=False, widget=CategorySelect)

    class Meta:
        fields = ['id', 'category']
        widgets = {"category": CategorySelect}

    def __init__(self, transaction_ids, initial_transaction_ids, *args, **kwargs):
        super(TransactionCategorizeForm, self).__init__(*args, **kwargs)
        self.fields['id'].choices = transaction_ids
        self.initial['id'] = list(initial_transaction_ids)
        self.fields['id'].widget = forms.MultipleHiddenInput()
        self.fields['category'].choices = Category.getUserGroupedAndSortedCategories(self.request.user)