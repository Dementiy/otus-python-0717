from django import forms

from .models import Question


class TagWidget(forms.TextInput):
    def render(self, name, value, attrs=None):
        if value is not None and not isinstance(value, str):
            value = ','.join([tag.name for tag in value])
        return super(TagWidget, self).render(name, value, attrs)


class QuestionForm(forms.ModelForm):
    tags = forms.CharField(required=False, widget=TagWidget)

    class Meta:
        model = Question
        fields = ("title", "text", "tags",)

