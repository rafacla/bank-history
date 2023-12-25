from django import forms
from banking.models import Category
from bootstrap_modal_forms.forms import BSModalModelForm


class CategoryForm(BSModalModelForm):

    class Meta:
        model = Category
        fields = ["name", "nested_to"]

    def __init__(self, *args, **kwargs):
        super(CategoryForm, self).__init__(*args, **kwargs)
        if 'type' in kwargs["initial"]:
             self.fields['nested_to'].queryset = Category.objects.filter(type=kwargs["initial"]["type"], nested_to=None)