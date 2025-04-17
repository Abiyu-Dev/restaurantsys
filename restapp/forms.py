from django import forms
from .models import *
from django.contrib.auth.forms import UserCreationForm
from django.utils import timezone
from django.core.exceptions import ValidationError



class CheckoutForm(forms.Form):
    ORDER_TYPE_CHOICES = [
        ('delivery', 'Delivery'),
        ('pickup', 'Pickup'),
    ]
    
    order_type = forms.ChoiceField(
        choices=ORDER_TYPE_CHOICES,
        widget=forms.RadioSelect
    )
    notes = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={
            'rows': 3,
            'placeholder': 'Any special instructions?'
        })
    )
    
    # Add delivery address fields if needed
    # Add payment method fields if needed

class StaffCreationForm(UserCreationForm):
    class Meta(UserCreationForm.Meta):
        model = User
        fields = ['username', 'email', 'role', 'first_name', 'last_name', 'phone', 'profile_picture']
        widgets = {
            'profile_picture': forms.FileInput(attrs={'class': 'hidden', 'id': 'profile-picture-upload'}),
        }
        
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['role'].choices = [
            ('server', 'Server'),
            ('chef', 'Chef'),
            ('cashier', 'Cashier'),
            ('deliveryboy', 'Delivery Boy'),
            ('customer', 'Customer'),
            ('manager', 'Manager')  # Added manager role
        ]
        # Remove password help text
        self.fields['password1'].help_text = None
        self.fields['password2'].help_text = None
        
        # Add Tailwind classes to all fields
        for field in self.fields.values():
            field.widget.attrs.update({'class': 'w-full p-2 mb-3 border rounded-md'})

    def clean_phone(self):
        phone = self.cleaned_data.get('phone')
        if phone and not phone.isdigit():
            raise ValidationError("Phone number should contain only digits.")
        return phone


class CustomerOrderForm(forms.ModelForm):
    ORDER_TYPE_CHOICES = [
        ('pickup', 'Pickup'),
        ('delivery', 'Delivery'),
    ]
    
    order_type = forms.ChoiceField(
        choices=ORDER_TYPE_CHOICES,
        widget=forms.RadioSelect(attrs={
            'class': 'inline-flex space-x-4',
        })
    )
    
    class Meta:
        model = Order
        fields = ['order_type', 'notes']
        widgets = {
            'notes': forms.Textarea(attrs={
                'rows': 3,
                'class': 'w-full border rounded-md p-2 focus:ring-2 focus:ring-blue-500',
                'placeholder': 'Any special instructions?'
            }),
        }


class DeliveryAddressForm(forms.ModelForm):
    class Meta:
        model = DeliveryAddress
        fields = ['address', 'phone']
        widgets = {
            'address': forms.Textarea(attrs={
                'rows': 3,
                'class': 'w-full border rounded-md p-2 focus:ring-2 focus:ring-blue-500',
                'placeholder': 'Enter your full delivery address'
            }),
            'phone': forms.TextInput(attrs={
                'class': 'w-full border rounded-md p-2 focus:ring-2 focus:ring-blue-500',
                'placeholder': 'Phone number for delivery',
                'pattern': '[0-9]{10,15}',
                'title': 'Enter a valid phone number (10-15 digits)'
            }),
        }


class OrderItemForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['menu_item'].queryset = MenuItem.objects.filter(available=True)
        self.fields['menu_item'].widget.attrs.update({
            'class': 'w-full p-2 border rounded-md'
        })

    quantity = forms.IntegerField(
        min_value=1,
        max_value=20,
        initial=1,
        widget=forms.NumberInput(attrs={
            'class': 'w-16 text-center border rounded-md',
            'min': '1',
            'max': '20'
        })
    )

    special_requests = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'w-full border rounded-md p-2 text-sm',
            'placeholder': 'Special requests (allergies, modifications, etc.)'
        })
    )

    class Meta:
        model = OrderItem
        fields = ['menu_item', 'quantity', 'special_requests']


OrderItemFormSet = forms.inlineformset_factory(
    Order,
    OrderItem,
    form=OrderItemForm,
    extra=3,
    can_delete=True,
    min_num=1,
    validate_min=True
)


class CustomUserCreationForm(UserCreationForm):
    class Meta(UserCreationForm.Meta):
        model = User
        fields = ('username', 'email', 'phone', 'first_name', 'last_name')
        widgets = {
            'email': forms.EmailInput(attrs={'required': True}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Add Tailwind classes
        for field in self.fields.values():
            field.widget.attrs.update({'class': 'w-full p-2 mb-3 border rounded-md'})
        
        # Remove password help text
        self.fields['password1'].help_text = None
        self.fields['password2'].help_text = None

    def save(self, commit=True):
        user = super().save(commit=False)
        user.role = 'customer'  # Force customer role
        if commit:
            user.save()
        return user


class RatingForm(forms.ModelForm):
    RATING_CHOICES = [
        (1, '★'),
        (2, '★★'),
        (3, '★★★'),
        (4, '★★★★'),
        (5, '★★★★★'),
    ]
    
    rating = forms.ChoiceField(
        choices=RATING_CHOICES,
        widget=forms.RadioSelect(attrs={
            'class': 'flex space-x-2'
        })
    )

    class Meta:
        model = Rating
        fields = ['rating', 'comment']
        widgets = {
            'comment': forms.Textarea(attrs={
                'rows': 3,
                'class': 'w-full p-2 border rounded-md focus:ring-2 focus:ring-blue-500',
                'placeholder': 'Tell us about your experience...'
            }),
        }




class ReservationForm(forms.ModelForm):
    class Meta:
        model = Reservation
        fields = ['table', 'reservation_time', 'party_size', 'special_requests']
        widgets = {
            'reservation_time': forms.DateTimeInput(attrs={'type': 'datetime-local'}),
            'special_requests': forms.Textarea(attrs={'rows': 3}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Filter only available tables
        self.fields['table'].queryset = Table.objects.filter(is_occupied=False)
        
        # Set minimum datetime to current time
        self.fields['reservation_time'].widget.attrs['min'] = timezone.now().strftime('%Y-%m-%dT%H:%M')



def clean(self):
    cleaned_data = super().clean()
    table = cleaned_data.get('table')
    reservation_time = cleaned_data.get('reservation_time')
    
    if table and reservation_time:
        # Check if table is already booked for this time
        conflicting_reservations = Reservation.objects.filter(
            table=table,
            reservation_time__range=(
                reservation_time - timezone.timedelta(hours=2),
                reservation_time + timezone.timedelta(hours=2)
            )
        )
        
        if conflicting_reservations.exists():
            raise forms.ValidationError("This table is already booked for a nearby time slot.")
    
    return cleaned_data

    
class OrderForm(forms.ModelForm):
    class Meta:
        model = Order
        fields = ['table', 'notes']
        widgets = {
            'table': forms.Select(attrs={
                'class': 'w-full p-2 border rounded-md'
            }),
            'notes': forms.Textarea(attrs={
                'rows': 3,
                'class': 'w-full p-2 border rounded-md',
                'placeholder': 'Order notes...'
            }),
        }

class IngredientForm(forms.ModelForm):
    class Meta:
        model = Ingredient
        fields = ['name', 'description', 'unit', 'minimum_quantity', 'cost_per_unit', 'supplier']
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'w-full p-2 border-2 border-gray-300 rounded-md focus:border-blue-500 focus:ring-2 focus:ring-blue-200',
                'placeholder': 'Enter ingredient name'
            }),
            'description': forms.Textarea(attrs={
                'class': 'w-full p-2 border-2 border-gray-300 rounded-md focus:border-blue-500 focus:ring-2 focus:ring-blue-200',
                'rows': 3,
                'placeholder': 'Enter ingredient description'
            }),
            'unit': forms.TextInput(attrs={
                'class': 'w-full p-2 border-2 border-gray-300 rounded-md focus:border-blue-500 focus:ring-2 focus:ring-blue-200',
                'placeholder': 'e.g., kg, liters, pieces'
            }),
            'minimum_quantity': forms.NumberInput(attrs={
                'class': 'w-full p-2 border-2 border-gray-300 rounded-md focus:border-blue-500 focus:ring-2 focus:ring-blue-200',
                'step': '0.01'
            }),
            'cost_per_unit': forms.NumberInput(attrs={
                'class': 'w-full p-2 border-2 border-gray-300 rounded-md focus:border-blue-500 focus:ring-2 focus:ring-blue-200',
                'step': '0.01'
            }),
            'supplier': forms.TextInput(attrs={
                'class': 'w-full p-2 border-2 border-gray-300 rounded-md focus:border-blue-500 focus:ring-2 focus:ring-blue-200',
                'placeholder': 'Enter supplier name'
            })
        }

class StockTransactionForm(forms.ModelForm):
    class Meta:
        model = StockTransaction
        fields = ['transaction_type', 'quantity', 'unit_price', 'reference_number', 'notes']
        widgets = {
            'quantity': forms.NumberInput(attrs={'step': '0.01'}),
            'unit_price': forms.NumberInput(attrs={'step': '0.01'}),
            'notes': forms.Textarea(attrs={'rows': 3}),
        }

class StockUpdateForm(forms.ModelForm):
    class Meta:
        model = Stock
        fields = ['current_quantity', 'alert_threshold']
        widgets = {
            'current_quantity': forms.NumberInput(attrs={
                'class': 'w-full p-2 border-2 border-gray-300 rounded-md focus:border-blue-500 focus:ring-2 focus:ring-blue-200',
                'step': '0.01',
                'placeholder': 'Enter current quantity'
            }),
            'alert_threshold': forms.NumberInput(attrs={
                'class': 'w-full p-2 border-2 border-gray-300 rounded-md focus:border-blue-500 focus:ring-2 focus:ring-blue-200',
                'step': '0.01',
                'placeholder': 'Enter alert threshold'
            })
        }