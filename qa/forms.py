from django import forms
from django.contrib.auth.forms import UserCreationForm



class DocumentUploadForm(forms.Form):
    document = forms.FileField()


class QuestionForm(forms.Form):
    question = forms.CharField(widget=forms.Textarea)


from django.contrib.auth.models import User

class SignUpForm(UserCreationForm):
    email = forms.EmailField(required=True)

    class Meta(UserCreationForm.Meta):
        model = User
        fields = UserCreationForm.Meta.fields + ("email",)
