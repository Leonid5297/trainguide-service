from django import forms


class SearchForm(forms.Form):
    query = forms.CharField(
        label='',
        required=False,
        widget=forms.TextInput(attrs={
            'placeholder': 'Поиск статей...',
            'class': (
                'w-full pl-12 pr-4 py-4 bg-white border border-slate-100 '
                'rounded-2xl text-sm font-medium outline-none shadow-sm '
                'focus:border-[#0088CC] transition-all'
            ),
            'autocomplete': 'off',
        }),
    )
