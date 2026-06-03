from django import forms
from django.contrib.auth.models import User
from .models import Profile

class UserRegistrationForm(forms.ModelForm):
    password = forms.CharField()
    password2 = forms.CharField()
    
    class Meta:
        model = User
        fields = ['username', 'first_name', 'email']
        
    # срабатывает при вызове is_valid()
    def clean_password2(self):
        cd = self.cleaned_data
        if cd['password'] != cd['password2']:
            raise forms.ValidationError('Passwords don\'t match.')
        return cd['password2']
    
    def clean_email(self):
        data = self.cleaned_data['email']
        if User.objects.filter(email=data).exists():
            raise forms.ValidationError('Email already in use.')
        return data


class UserEditForm(forms.ModelForm):
    
    class Meta: 
        model = User 
        fields = ['first_name', 'last_name', 'email']
    
    def clean_email(self):
        data = self.cleaned_data['email']
        qs = User.objects.exclude(id=self.instance.id)\
                                .filter(email=data)
        if qs.exists():
            raise forms.ValidationError(' Email already in use.')
        return data      


class ProfileEditForm(forms.ModelForm):
    class Meta:
        model = Profile
        fields = ['age', 'weight', 'height', 'gender', 'avatar']
        # labels 
        labels = {
            'age': 'Возраст',
            'weight': 'Вес (кг)',
            'height': 'Рост (см)',
            'gender': 'Пол',
            'avatar': 'Фото профиля',
        }
        #  валидаторы (min_value, max_value и т.д.)
        widgets = {
            'age': forms.NumberInput(attrs={'min': 10, 'max': 100}),
            'weight': forms.NumberInput(attrs={'min': 30, 'max': 300, 'step': 0.1}),
            'height': forms.NumberInput(attrs={'min': 100, 'max': 250}),
        }



