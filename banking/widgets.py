from django import forms


class CategorySelect(forms.Select):
    def create_option(
        self, name, value, label, selected, index, subindex=None, attrs=None
    ):
        option = super().create_option(
            name, value, label, selected, index, subindex, attrs
        )
        if value:
            option["attrs"]["class"] = "ps-" + str(int(label["level"])*2)
            option["label"] = label["name"]
        return option
