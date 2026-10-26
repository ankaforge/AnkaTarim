from django import forms
from django.contrib.auth.models import User
from django.utils import timezone
from django.utils.text import slugify

from core.models import Company

from .models import Package, Subscription


TURKISH_ASCII = str.maketrans('çğıöşüÇĞİÖŞÜ', 'cgiosuCGIOSU')


class SubscriptionAdminForm(forms.ModelForm):
    class Meta:
        model = Subscription
        fields = '__all__'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['ends_on'].required = False
        self.fields['ends_on'].help_text = 'Boş bırakılırsa paket süresine göre hesaplanır.'

    def clean(self):
        cleaned_data = super().clean()
        package = cleaned_data.get('package')
        starts_on = cleaned_data.get('starts_on')
        if package and starts_on and not cleaned_data.get('ends_on'):
            cleaned_data['ends_on'] = package.period_end(starts_on)
        return cleaned_data


class CompanySetupForm(forms.Form):
    name = forms.CharField(label='Şirket adı', max_length=160)
    slug = forms.SlugField(label='Kısa ad (slug)', max_length=180, required=False, help_text='Boş bırakılırsa şirket adından üretilir.')
    contact_name = forms.CharField(label='Yetkili kişi', max_length=120, required=False)
    phone = forms.CharField(label='Telefon', max_length=20, required=False)
    email = forms.EmailField(label='E-posta', required=False)
    tax_number = forms.CharField(label='Vergi / TC no', max_length=20, required=False)
    tax_office = forms.CharField(label='Vergi dairesi', max_length=80, required=False)
    address = forms.CharField(label='Adres', max_length=255, required=False)

    package = forms.ModelChoiceField(
        label='Paket',
        queryset=Package.objects.filter(is_active=True),
        help_text='Demo seçilirse ücret 0 ve ödeme durumu "Ücretsiz / deneme" olarak kaydedilir.',
    )
    starts_on = forms.DateField(label='Başlangıç tarihi', initial=timezone.localdate, widget=forms.DateInput(attrs={'type': 'date'}))
    price = forms.DecimalField(label='Ücret (TL)', max_digits=12, decimal_places=2, required=False, help_text='Boş bırakılırsa paketin liste fiyatı yazılır.')
    payment_status = forms.ChoiceField(label='Ödeme durumu', choices=Subscription.PAYMENT_STATUS_CHOICES, initial=Subscription.PAYMENT_PAID)

    admin_username = forms.CharField(label='Genel admin kullanıcı adı', max_length=150)
    admin_first_name = forms.CharField(label='Ad', max_length=150, required=False)
    admin_last_name = forms.CharField(label='Soyad', max_length=150, required=False)
    admin_email = forms.EmailField(label='Genel admin e-posta', required=False)

    def clean_slug(self):
        slug = self.cleaned_data.get('slug') or slugify(self.cleaned_data.get('name', '').translate(TURKISH_ASCII))
        if not slug:
            raise forms.ValidationError('Şirket adından kısa ad üretilemedi, lütfen elle girin.')
        if Company.objects.filter(slug=slug).exists():
            raise forms.ValidationError('Bu kısa ad başka bir şirkette kullanılıyor.')
        return slug

    def clean_admin_username(self):
        username = self.cleaned_data['admin_username'].strip()
        if User.objects.filter(username__iexact=username).exists():
            raise forms.ValidationError('Bu kullanıcı adı zaten kullanılıyor.')
        return username

    def clean(self):
        cleaned_data = super().clean()
        package = cleaned_data.get('package')
        if package and package.code == Package.DEMO_CODE:
            cleaned_data['price'] = 0
            cleaned_data['payment_status'] = Subscription.PAYMENT_WAIVED
        return cleaned_data

    def company_data(self):
        data = self.cleaned_data
        return {
            field: data[field]
            for field in ('name', 'slug', 'contact_name', 'phone', 'email', 'tax_number', 'tax_office', 'address')
        }

    def admin_data(self):
        data = self.cleaned_data
        return {
            'username': data['admin_username'],
            'first_name': data['admin_first_name'],
            'last_name': data['admin_last_name'],
            'email': data['admin_email'] or data['email'],
        }


class RenewForm(forms.Form):
    payment_status = forms.ChoiceField(label='Ödeme durumu', choices=Subscription.PAYMENT_STATUS_CHOICES, initial=Subscription.PAYMENT_PAID)
    payment_method = forms.ChoiceField(label='Ödeme yöntemi', choices=[('', '---')] + Subscription.PAYMENT_METHOD_CHOICES, required=False)
    payment_reference = forms.CharField(label='Dekont / fatura no', max_length=120, required=False)
    price = forms.DecimalField(label='Ücret (TL)', max_digits=12, decimal_places=2, required=False, help_text='Boş bırakılırsa paketin liste fiyatı yazılır.')
