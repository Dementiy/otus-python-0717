from django import forms

from .models import Question, Answer


class TagWidget(forms.TextInput):
    def render(self, name, value, attrs=None):
        if value is not None and not isinstance(value, str):
            value = ','.join([tag.name for tag in value])
        return super(TagWidget, self).render(name, value, attrs)


class QuestionForm(forms.ModelForm):
    tags = forms.CharField(required=False, widget=TagWidget)

    def clean_tags(self):
        tags = self.cleaned_data.get('tags')
        return [] if not tags else tags.split(',')

    class Meta:
        model = Question
        fields = ("title", "text", "tags",)


class AnswerForm(forms.ModelForm):
    text = forms.CharField(label='', widget=forms.Textarea, required=True)

    class Meta:
        model = Answer
        fields = ("text",)

