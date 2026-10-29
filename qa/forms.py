from django import forms
from django.contrib.auth.forms import UserCreationForm
from pathlib import PurePosixPath
from .models import Collection, Document


MAX_DOCUMENT_SIZE = 25 * 1024 * 1024


class DocumentUploadForm(forms.Form):
    document = forms.FileField()
    collection = forms.ModelChoiceField(
        queryset=Collection.objects.none(),
        required=False,
        empty_label="No collection",
    )

    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        if user is not None:
            self.fields["collection"].queryset = Collection.objects.filter(owner=user)

    def clean_document(self):
        uploaded_file = self.cleaned_data["document"]
        extension = PurePosixPath(uploaded_file.name).suffix.lower()
        if extension not in {".pdf", ".txt"}:
            raise forms.ValidationError("Upload a PDF or TXT file.")
        if uploaded_file.size > MAX_DOCUMENT_SIZE:
            raise forms.ValidationError("Files must be 25 MB or smaller.")
        return uploaded_file


class QuestionForm(forms.Form):
    question = forms.CharField(
        max_length=2000,
        widget=forms.Textarea(attrs={"rows": 3, "placeholder": "Ask a question about your documents…"}),
    )


class CollectionForm(forms.ModelForm):
    class Meta:
        model = Collection
        fields = ["name"]
        widgets = {"name": forms.TextInput(attrs={"placeholder": "e.g. Research papers"})}

    def __init__(self, *args, user=None, **kwargs):
        self.user = user
        super().__init__(*args, **kwargs)

    def clean_name(self):
        name = self.cleaned_data["name"].strip()
        if self.user:
            existing = Collection.objects.filter(owner=self.user, name__iexact=name)
            if self.instance.pk:
                existing = existing.exclude(pk=self.instance.pk)
            if existing.exists():
                raise forms.ValidationError("You already have a collection with this name.")
        return name


class DocumentManageForm(forms.ModelForm):
    class Meta:
        model = Document
        fields = ["display_name", "collection"]
        widgets = {"display_name": forms.TextInput(attrs={"placeholder": "Use the original file name"})}

    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["display_name"].required = False
        self.fields["collection"].required = False
        self.fields["collection"].empty_label = "No collection"
        self.fields["collection"].queryset = Collection.objects.filter(owner=user)


from django.contrib.auth.models import User

class SignUpForm(UserCreationForm):
    email = forms.EmailField(required=True)

    class Meta(UserCreationForm.Meta):
        model = User
        fields = UserCreationForm.Meta.fields + ("email",)
