from django import forms
from django.contrib.auth.models import User
from django.contrib.auth.forms import UserCreationForm

from .models import UserProfile


class SignUpForm(UserCreationForm):
    avatar = forms.ImageField(required=False)

    class Meta:
        model = User
        fields = ('username', 'email', 'password1', 'password2', 'avatar',)

    def clean_email(self):
        email = self.cleaned_data.get('email')
        try:
            User.objects.get(email__iexact=email)
        except User.DoesNotExist:
            return email
        raise forms.ValidationError("This email address is already in use.")


class UserProfileForm(forms.ModelForm):
    username = forms.CharField(required=False, disabled=True)
    email = forms.EmailField()

    def clean_username(self):
        if self.instance:
            return self.instance.user.username
        else:
            return self.fields['username']

    def clean_email(self):
        username = self.cleaned_data.get('username')
        email = self.cleaned_data.get('email')
        users = User.objects.filter(email=email).exclude(username__iexact=username)
        if users:
            raise forms.ValidationError("This email address is already in use.")
        return email

    class Meta:
        model = UserProfile
        fields = ('username', 'email', 'avatar',)

