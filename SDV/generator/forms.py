from django import forms

class MetadataForm(forms.Form):
    table_name = forms.CharField(label='Table Name', max_length=100)
    data_limit = forms.IntegerField(label='Data Limit', initial=10)
    metadata_choice = forms.ChoiceField(
        choices=[('generate', 'Generate from scratch'), ('use_existing', 'Use Existing')],
        label='Metadata Option'
    )

class UserLoginForm(forms.Form):
    username = forms.CharField(max_length=150)
    password = forms.CharField(widget=forms.PasswordInput)

class UploadFileForm(forms.Form):
    file = forms.FileField(label='Select an Excel file')