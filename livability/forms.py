from django import forms
from django.contrib.auth.forms import UserCreationForm
from livability.models import CityLivabilityScore
from .models import CategoryFuzzyComparison

class CustomUserCreationForm(UserCreationForm):
    city = forms.ChoiceField(label="Şehir", choices=[], required=True)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Benzersiz şehir isimlerini getir
        cities = CityLivabilityScore.objects.values_list('city_name', flat=True).distinct()
        self.fields['city'].choices = [(c, c) for c in sorted(cities)]

class CategoryFuzzyComparisonForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        categories = CityLivabilityScore.objects.values_list('category', flat=True).distinct()
        choices = [(cat, cat) for cat in categories]
        self.fields['category1'].choices = choices
        self.fields['category2'].choices = choices

    category1 = forms.ChoiceField(label="Kategori 1", choices=[])
    category2 = forms.ChoiceField(label="Kategori 2", choices=[])

    class Meta:
        model = CategoryFuzzyComparison
        fields = ['category1', 'category2', 'value_l', 'value_m', 'value_u']
        widgets = {
            'value_l': forms.NumberInput(attrs={'step': '0.01', 'class': 'form-control'}),
            'value_m': forms.NumberInput(attrs={'step': '0.01', 'class': 'form-control'}),
            'value_u': forms.NumberInput(attrs={'step': '0.01', 'class': 'form-control'}),
        }