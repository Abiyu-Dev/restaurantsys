#restapp/views.py

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from .models import *
from .forms import *
from django.http import Http404, HttpResponseForbidden
from django.views.generic import CreateView, UpdateView, DeleteView, ListView, DetailView, TemplateView
from django.urls import reverse_lazy
from .decorators import *
from .mixins import *
from django.utils import timezone
from django.db.models import Count, Sum, F, DecimalField, Q
from django.db.models.functions import Coalesce
from django.db import models
from .utils import *
from decimal import Decimal

from django.http import JsonResponse

import json
from django.views.decorators.http import require_POST
from datetime import timedelta
from django.utils import timezone

from django.db.models.functions import TruncDate
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.contrib.auth import logout
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.forms import inlineformset_factory
from .utils import log_activity


from django.db.models import Sum

@login_required
@role_required('manager')
def sales_report(request):
    # Default date range (last 30 days)
    end_date = timezone.now()
    start_date = end_date - timedelta(days=30)

    # Get filters from request
    date_range = request.GET.get('range', '30days')
    if date_range == '7days':
        start_date = end_date - timedelta(days=7)
    elif date_range == 'today':
        start_date = end_date.replace(hour=0, minute=0, second=0)

    # Get completed orders
    completed_orders = Order.objects.filter(
        status='paid'
    ).prefetch_related('orderitem_set__menu_item')

    # Calculate total sales
    total_sales = sum(
        sum(item.quantity * item.menu_item.price for item in order.orderitem_set.all())
        for order in completed_orders
    )

    # Total orders count
    total_orders = completed_orders.count()

    # Average order value
    avg_order_value = total_sales / total_orders if total_orders else 0

    # Daily sales breakdown
    daily_sales = []
    current_date = start_date.date()
    while current_date <= end_date.date():
        daily_orders = completed_orders.filter(
            created_at__date=current_date
        )
        daily_total = sum(
            sum(item.quantity * item.menu_item.price for item in order.orderitem_set.all())
            for order in daily_orders
        )
        daily_sales.append({
            'date': current_date,
            'daily_total': daily_total,
            'order_count': daily_orders.count()
        })
        current_date += timedelta(days=1)

    # Stock information
    stock_info = Ingredient.objects.annotate(
        total_quantity=Sum('transactions__quantity')
    ).values('name', 'total_quantity')

    # Add total for each order
    orders_with_totals = []
    for order in completed_orders:
        order_total = sum(item.quantity * item.menu_item.price for item in order.orderitem_set.all())
        orders_with_totals.append({
            'id': order.id,
            'customer': order.customer,
            'total': order_total,
            'created_at': order.created_at,
        })

    context = {
        'total_sales': total_sales,
        'total_orders': total_orders,
        'avg_order_value': avg_order_value,
        'daily_sales': daily_sales,
        'completed_orders': orders_with_totals,
        'stock_info': stock_info,
    }
    return render(request, 'manager/sales_report.html', context)

def cart_view(request):
    cart = request.session.get('cart', {})
    cart_items = []
    total = 0
    
    for item_id, quantity in cart.items():
        item = get_object_or_404(MenuItem, id=item_id)
        subtotal = item.price * quantity
        cart_items.append({
            'item': item,
            'quantity': quantity,
            'subtotal': subtotal
        })
        total += subtotal
    
    return render(request, 'cart/cart.html', {
        'cart_items': cart_items,
        'total': total
    })

@require_POST
def add_to_cart(request, item_id):
    try:
        data = json.loads(request.body)
        quantity = int(data.get('quantity', 1))
        
        item = get_object_or_404(MenuItem, id=item_id)
        cart = request.session.get('cart', {})
        
        current_quantity = cart.get(str(item_id), 0)
        cart[str(item_id)] = current_quantity + quantity
        request.session['cart'] = cart
        request.session.modified = True
        
        return JsonResponse({
            'success': True,
            'cart_count': sum(cart.values()),
            'item_name': item.name,
            'message': f"{item.name} added to cart"
        })
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=400)

def cart_count(request):
    cart = request.session.get('cart', {})
    return JsonResponse({
        'count': sum(cart.values())
    })

def remove_from_cart(request, item_id):
    cart = request.session.get('cart', {})
    
    if str(item_id) in cart:
        del cart[str(item_id)]
        request.session['cart'] = cart
        messages.success(request, "Item removed from your cart")
    
    return redirect('cart')

def update_cart(request, item_id):
    quantity = request.POST.get('quantity', 1)
    try:
        quantity = int(quantity)
        if quantity > 0:
            cart = request.session.get('cart', {})
            cart[str(item_id)] = quantity
            request.session['cart'] = cart
            messages.success(request, "Cart updated")
    except ValueError:
        messages.error(request, "Invalid quantity")
    
    return redirect('cart')

def checkout_view(request):
    cart = request.session.get('cart', {})
    
    if not cart:
        messages.warning(request, "Your cart is empty")
        return redirect('cart')

    if request.method == 'POST':
        form = CheckoutForm(request.POST)
        if form.is_valid():
            # Create order without total first
            order = Order.objects.create(
                customer=request.user,
                order_type=form.cleaned_data['order_type'],
                notes=form.cleaned_data['notes'],
                status='pending'
            )
            
            # If it's a delivery order, save the delivery address
            if form.cleaned_data['order_type'] == 'delivery':
                DeliveryAddress.objects.create(
                    order=order,
                    address=request.POST.get('address'),
                    phone=request.POST.get('phone')
                )
            
            # Create order items which will calculate the total
            for item_id, quantity in cart.items():
                try:
                    menu_item = MenuItem.objects.get(id=item_id)
                    OrderItem.objects.create(
                        order=order,
                        menu_item=menu_item,
                        quantity=quantity
                    )
                except MenuItem.DoesNotExist:
                    continue
            
            # Clear cart
            request.session['cart'] = {}
            request.session.modified = True
            
            messages.success(request, "Order placed successfully!")
            return redirect('checkout_success', order_id=order.id)
        else:
            messages.error(request, "Please correct the errors below.")
    else:
        form = CheckoutForm()
    
    # Calculate total for display only
    total = 0
    cart_items = []
    for item_id, quantity in cart.items():
        try:
            item = MenuItem.objects.get(id=item_id)
            subtotal = item.price * quantity
            total += subtotal
            cart_items.append({
                'item': item,
                'quantity': quantity,
                'subtotal': subtotal
            })
        except MenuItem.DoesNotExist:
            continue
    
    return render(request, 'checkout/checkout.html', {
        'form': form,
        'cart_items': cart_items,
        'total': total
    })
    
def checkout_success(request, order_id):
    order = get_object_or_404(Order, id=order_id)
    return render(request, 'checkout/success.html', {'order': order})

class ManagerDashboardView(UserPassesTestMixin, TemplateView):
    template_name = 'manager/dashboard.html'
    
    def test_func(self):
        return self.request.user.role == 'manager'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        today = timezone.now().date()
        
        # Get today's orders
        orders_today = Order.objects.filter(created_at__date=today)
        total_orders = orders_today.count()
        
        # Calculate revenue from OrderItems
        revenue_aggregate = OrderItem.objects.filter(
            order__created_at__date=today
        ).aggregate(
            total_revenue=Sum(F('quantity') * F('menu_item__price'), 
                           output_field=DecimalField())
        )
        
        # Get popular items
        popular_items = OrderItem.objects.filter(
            order__created_at__date=today
        ).values(
            'menu_item__name'
        ).annotate(
            total_ordered=Sum('quantity')
        ).order_by('-total_ordered')[:5]
        
        # Get table status
        tables = Table.objects.annotate(
            active_orders=Count('order',
                filter=models.Q(order__status__in=['pending', 'preparing'])
        ))
        
        # Get active staff
        active_staff = User.objects.filter(
            role__in=['server', 'chef'],
            is_active=True
        )

        orders = Order.objects.all().order_by('-created_at')

        pickup_orders = orders_today.filter(order_type='pickup').count()
        delivery_orders = orders_today.filter(order_type='delivery').count()
        reservations_today = Reservation.objects.filter(reservation_time__date=today).count()

        # Get recent activities
        recent_activities = ActivityLog.objects.all().order_by('-created_at')[:10]
        
        context.update({
            'pickup_orders': pickup_orders,
            'delivery_orders': delivery_orders,
            'reservations_today': reservations_today,
            'total_orders': total_orders,
            'revenue_today': revenue_aggregate['total_revenue'] or Decimal('0.00'),
            'pending_orders': orders_today.filter(status='pending').count(),
            'popular_items': popular_items,
            'tables': tables,
            'active_staff': active_staff,
            'orders': orders,
            'recent_orders': orders_today,
            'recent_activities': recent_activities,
        })
        return context


class CustomerDashboardView(LoginRequiredMixin, UserPassesTestMixin, TemplateView):
    template_name = 'customer/dashboard.html'
    
    def test_func(self):
        return self.request.user.role == 'customer'
    
    def handle_no_permission(self):
        if self.request.user.is_authenticated:
            messages.error(self.request, "You don't have customer access")
            return redirect('home')
        return super().handle_no_permission()
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user
        context['active_orders'] = Order.objects.filter(
            customer=user
        ).exclude(status='completed').order_by('-created_at')[:3]
        context['past_orders'] = Order.objects.filter(
            customer=user,
            status='completed'
        ).order_by('-created_at')[:5]
        return context

class CustomerOrderCreateView(LoginRequiredMixin, CreateView):
    model = Order
    form_class = CustomerOrderForm
    template_name = 'orders/customer_create.html'
    success_url = reverse_lazy('customer_orders')

    def form_valid(self, form):
        form.instance.customer = self.request.user
        return super().form_valid(form)

class CustomerOrderListView(LoginRequiredMixin, ListView):
    model = Order
    template_name = 'orders/customer_list.html'
    context_object_name = 'orders'

    def get_queryset(self):
        # Only show orders belonging to the current customer
        return Order.objects.filter(customer=self.request.user).order_by('-created_at')

class CustomerOrderDetailView(LoginRequiredMixin, DetailView):
    model = Order
    template_name = 'orders/customer_detail.html'
    context_object_name = 'order'

    def get_object(self, queryset=None):
        # Ensure customer can only access their own orders
        order = get_object_or_404(Order, pk=self.kwargs['pk'])
        if order.customer != self.request.user:
            raise Http404("Order not found")
        return order

class ChefOrderListView(LoginRequiredMixin, UserPassesTestMixin, ListView):
    model = Order
    template_name = 'orders/chef_list.html'
    context_object_name = 'orders'
    
    def test_func(self):
        return self.request.user.role == 'chef'
    
    def get_queryset(self):
        return Order.objects.exclude(status='delivered').order_by('status', 'created_at')

class ChefOrderUpdateView(LoginRequiredMixin, UserPassesTestMixin, UpdateView):
    model = Order
    fields = ['status']
    template_name = 'orders/chef_update.html'
    success_url = reverse_lazy('chef_orders')
    
    def test_func(self):
        return self.request.user.role == 'chef'
    
    def form_valid(self, form):
        response = super().form_valid(form)
        
        # Log the action
        log_activity(
            user=self.request.user,
            action_type="UPDATE",
            description=f"Updated Order #{self.object.id} status to {self.object.status}",
            related_model="Order",
            related_id=self.object.id,
            ip_address=get_client_ip(self.request)
        )
        
        messages.success(self.request, f"Order #{self.object.id} updated successfully!")
        return response


def custom_logout(request):
    logout(request)
    # Add any additional logic here (e.g., logging)
    return redirect('home')  # Redirect to home page

@login_required
def create_order(request):
    OrderItemFormSet = inlineformset_factory(Order, OrderItem, fields=('menu_item', 'quantity'), extra=1, can_delete=True)

    if request.method == 'POST':
        form = OrderForm(request.POST)
        formset = OrderItemFormSet(request.POST)

        if form.is_valid() and formset.is_valid():
            order = form.save(commit=False)
            order.server = request.user
            order.save()

            formset.instance = order
            formset.save()

            # Log the action
            log_activity(
                user=request.user,
                action_type="CREATE",
                description=f"Created Order #{order.id}",
                related_model="Order",
                related_id=order.id,
                ip_address=get_client_ip(request)
            )

            messages.success(request, "Order created successfully!")
            return redirect('server_orders')
    else:
        form = OrderForm()
        formset = OrderItemFormSet()

    return render(request, 'orders/create.html', {
        'form': form,
        'formset': formset
    })

@login_required
def server_orders(request):
    orders = Order.objects.filter(server=request.user).order_by('-created_at')
    return render(request, 'orders/server_list.html', {'orders': orders})


@login_required
def order_rate(request, pk):
    order = get_object_or_404(Order, pk=pk)
    
    # Check if the user is the customer who placed the order
    if request.user != order.table.customer:
        messages.error(request, "You can only rate orders you've placed")
        return redirect('order_detail', pk=order.pk)
    
    # Check if rating already exists
    existing_rating = Rating.objects.filter(order=order, customer=request.user).first()
    
    if request.method == 'POST':
        form = RatingForm(request.POST, instance=existing_rating)
        if form.is_valid():
            rating = form.save(commit=False)
            rating.order = order
            rating.customer = request.user
            rating.save()
            messages.success(request, "Thank you for your rating!")
            return redirect('order_detail', pk=order.pk)
    else:
        form = RatingForm(instance=existing_rating)
    
    return render(request, 'orders/rate.html', {
        'order': order,
        'form': form,
        'existing_rating': existing_rating
    })

@login_required
def reservation_detail(request, pk):
    reservation = get_object_or_404(Reservation, pk=pk)
    
    # Check if user has permission to view this reservation
    if not (request.user == reservation.customer or 
            request.user.role in ['manager', 'server']):
        return HttpResponseForbidden("You don't have permission to view this reservation")
    
    return render(request, 'reservations/detail.html', {
        'reservation': reservation,
        'can_edit': request.user == reservation.customer or request.user.role == 'manager'
    })  

def reservation_create(request):
    if request.method == 'POST':
        form = ReservationForm(request.POST)
        if form.is_valid():
            reservation = form.save(commit=False)
            reservation.customer = request.user
            reservation.save()
            
            # Mark table as occupied (optional)
            reservation.table.is_occupied = True
            reservation.table.save()
            
            return redirect('reservations')  # Redirect to reservations list
    else:
        form = ReservationForm()
    
    return render(request, 'reservations/create.html', {
        'form': form,
        'available_tables': Table.objects.filter(is_occupied=False).count()
    })

class ReservationUpdateView(UpdateView):
    model = Reservation
    form_class = ReservationForm
    template_name = 'reservations/form.html'
    success_url = reverse_lazy('reservations')

class ReservationDeleteView(DeleteView):
    model = Reservation
    template_name = 'reservations/delete.html'
    success_url = reverse_lazy('reservations')
    
    def delete(self, request, *args, **kwargs):
        reservation = self.get_object()
        # Mark table as available before deletion
        reservation.table.is_occupied = False
        reservation.table.save()
        messages.success(request, "Reservation deleted successfully")
        return super().delete(request, *args, **kwargs)

def reservation_list(request):
    if request.user.role == 'customer':
        reservations = Reservation.objects.filter(customer=request.user).order_by('reservation_time')
        
    else:
        reservations = Reservation.objects.all().order_by('reservation_time')
    
    # Date filtering
    if 'date' in request.GET:
        date = request.GET['date']
        reservations = reservations.filter(reservation_time__date=date)
    
    # Pagination
    paginator = Paginator(reservations, 10)  # Show 10 reservations per page
    page_number = request.GET.get('page')
    
    try:
        page_obj = paginator.page(page_number)
    except PageNotAnInteger:
        # If page is not an integer, deliver first page
        page_obj = paginator.page(1)
    except EmptyPage:
        # If page is out of range, deliver last page of results
        page_obj = paginator.page(paginator.num_pages)
    
    return render(request, 'reservations/list.html', {
        'page_obj': page_obj,
        'reservations': page_obj.object_list,
    })


class StaffCreateView(UserPassesTestMixin, CreateView):
    model = User
    form_class = StaffCreationForm
    template_name = 'manager/staff_form.html'
    success_url = reverse_lazy('staff_list')

    def test_func(self):
        return self.request.user.role == 'manager'

    def form_valid(self, form):
        user = form.save(commit=False)
        user.set_password(form.cleaned_data['password1'])
        user.save()
        log_activity(
            user=self.request.user,
            action_type="CREATE",
            description=f"Created Staff #{self.object.id} - {user.username}",
            related_model="User",
            related_id=self.object.id,
            ip_address=get_client_ip(self.request)
        )
        messages.success(self.request, f"Staff member {user.username} created successfully!")
        return redirect(self.success_url)


class SignUpView(CreateView):
    form_class = CustomUserCreationForm
    success_url = reverse_lazy('login')
    template_name = 'registration/signup.html'

class StaffListView(ManagerRequiredMixin, ListView):
    model = User
    template_name = 'manager/staff_list.html'
    context_object_name = 'staff_members'
    
    def get_queryset(self):
        return User.objects.exclude(role='customer')

class StaffUpdateView(ManagerRequiredMixin, UpdateView):
    model = User
    fields = ['username', 'email', 'role', 'is_active']
    template_name = 'manager/staff_form.html'
    success_url = reverse_lazy('staff_list')
    
    def get_queryset(self):
        return User.objects.exclude(role='customer')

@login_required
@role_required('manager', 'server', 'chef', 'cashier', 'deliveryboy')
def dashboard(request):
    today = timezone.now().date()
    context = {
        'current_date': today,
        'user_role': request.user.role
    }

    if request.user.role == 'manager':
        # Manager-specific data
        orders_today = Order.objects.filter(created_at__date=today)
        context.update({
            'total_tables': Table.objects.count(),
            'occupied_tables': Table.objects.filter(is_occupied=True).count(),
            'total_orders': orders_today.count(),
            
            'popular_items': OrderItem.objects.filter(
                order__created_at__date=today
            ).values(
                'menu_item__name'
            ).annotate(
                total_ordered=Sum('quantity')
            ).order_by('-total_ordered')[:5]
        })

    elif request.user.role == 'chef':
        # Chef-specific data
        context['pending_orders'] = Order.objects.filter(
            status__in=['pending', 'preparing']
        ).order_by('created_at')

    elif request.user.role == 'server':
        # Server-specific data
        context['my_tables'] = Table.objects.filter(
            order__server=request.user,
            order__status__in=['pending', 'preparing']
        ).distinct()
        context['my_orders'] = Order.objects.filter(
            server=request.user,
            created_at__date=today
        ).order_by('-created_at')[:5]

    elif request.user.role == 'cashier':
        # Cashier-specific data
        context['unpaid_orders'] = Order.objects.filter(
            status='ready'
        ).order_by('created_at')

    elif request.user.role == 'deliveryboy':
        # Delivery Boy-specific data
        available_orders = Order.objects.filter(
            order_type='delivery',
            status='ready'
        ).order_by('-created_at')

        assigned_orders = Order.objects.filter(
            delivery_boy=request.user,
            status__in=['out_for_delivery']
        ).order_by('-created_at')

        context.update({
            'available_orders': available_orders,
            'assigned_orders': assigned_orders,
        })


    return render(request, 'dashboard.html', context)

def menu_search(request):
    query = request.GET.get('q', '')
    category_id = request.GET.get('category', None)
    
    menu_items = MenuItem.objects.filter(available=True)
    
    if query:
        menu_items = menu_items.filter(
            Q(name__icontains=query) | 
            Q(description__icontains=query)
        )
    
    if category_id and category_id != 'all':
        menu_items = menu_items.filter(category_id=category_id)
    
    categories = Category.objects.all()
    
    return render(request, 'menu/search_results.html', {
        'menu_items': menu_items,
        'categories': categories,
        'query': query,
        'selected_category': category_id
    })




# Menu Item Views
class MenuItemListView(UserPassesTestMixin, ListView):
    model = MenuItem
    template_name = 'manager/menu_item_list.html'
    
    def test_func(self):
        return self.request.user.role == 'manager'

class MenuItemCreateView(UserPassesTestMixin, CreateView):
    model = MenuItem
    fields = ['name', 'description', 'price', 'category', 'available', 'image']
    template_name = 'manager/menu_item_form.html'
    success_url = reverse_lazy('menu_item_list')
    
    def test_func(self):
        return self.request.user.role == 'manager'
    
    def form_valid(self, form):
        messages.success(self.request, "Menu item created successfully!")
        return super().form_valid(form)

class MenuItemUpdateView(UserPassesTestMixin, UpdateView):
    model = MenuItem
    fields = ['name', 'description', 'price', 'category', 'available', 'image']
    template_name = 'manager/menu_item_form.html'
    success_url = reverse_lazy('menu_item_list')
    
    def test_func(self):
        return self.request.user.role == 'manager'
    
    def form_valid(self, form):
        log_activity(
            user=self.request.user,
            action_type="UPDATE",
            description=f"Updated Menu #{self.object.id}",
            related_model="MenuItem",
            related_id=self.object.id,
            ip_address=get_client_ip(self.request)
        )
        messages.success(self.request, "Menu item updated successfully!")
        return super().form_valid(form)


class MenuItemDeleteView(LoginRequiredMixin, UserPassesTestMixin, DeleteView):
    model = MenuItem
    template_name = 'menu/item_confirm_delete.html'
    success_url = reverse_lazy('menu')

    def test_func(self):
        return self.request.user.role == 'manager'

    def delete(self, request, *args, **kwargs):
        menu_item = self.get_object()

        # Log the action
        log_activity(
            user=request.user,
            action_type="DELETE",
            description=f"Deleted Menu Item #{menu_item.id} - {menu_item.name}",
            related_model="MenuItem",
            related_id=menu_item.id,
            ip_address=get_client_ip(request)
        )

        messages.success(request, f"Menu item {menu_item.name} deleted successfully!")
        return super().delete(request, *args, **kwargs)


class TableListView(UserPassesTestMixin, ListView):
    model = Table
    template_name = 'manager/table_list.html'
    
    def test_func(self):
        return self.request.user.role == 'manager'

class TableCreateView(UserPassesTestMixin, CreateView):
    model = Table
    fields = ['number', 'capacity']
    template_name = 'manager/table_form.html'
    success_url = reverse_lazy('table_list')
    
    def test_func(self):
        return self.request.user.role == 'manager'

    def form_valid(self, form):
        response = super().form_valid(form)
        
        # Log the action
        log_activity(
            user=self.request.user,
            action_type="CREATE",
            description=f"Created Table #{self.object.id} - Number: {self.object.number}, Capacity: {self.object.capacity}",
            related_model="Table",
            related_id=self.object.id,
            ip_address=get_client_ip(self.request)
        )
        
        messages.success(self.request, f"Table {self.object.number} created successfully!")
        return response

class TableUpdateView(UserPassesTestMixin, UpdateView):
    model = Table
    fields = ['number', 'capacity', 'is_available']
    template_name = 'manager/table_form.html'
    success_url = reverse_lazy('table_list')
    
    def test_func(self):
        return self.request.user.role == 'manager'

    def form_valid(self, form):
        response = super().form_valid(form)
        
        # Log the action
        log_activity(
            user=self.request.user,
            action_type="UPDATE",
            description=f"Updated Table #{self.object.id} - Number: {self.object.number}, Capacity: {self.object.capacity}, Available: {self.object.is_available}",
            related_model="Table",
            related_id=self.object.id,
            ip_address=get_client_ip(self.request)
        )
        
        messages.success(self.request, f"Table {self.object.number} updated successfully!")
        return response

class TableDeleteView(LoginRequiredMixin, UserPassesTestMixin, DeleteView):
    model = Table
    template_name = 'manager/table_confirm_delete.html'
    success_url = reverse_lazy('table_list')

    def test_func(self):
        return self.request.user.role == 'manager'

    def delete(self, request, *args, **kwargs):
        table = self.get_object()

        # Log the action
        log_activity(
            user=request.user,
            action_type="DELETE",
            description=f"Deleted Table #{table.id} - Number: {table.number}, Capacity: {table.capacity}",
            related_model="Table",
            related_id=table.id,
            ip_address=get_client_ip(request)
        )

        messages.success(request, f"Table {table.number} deleted successfully!")
        return super().delete(request, *args, **kwargs)


# Category Views
class CategoryCreateView(LoginRequiredMixin, CreateView):
    model = Category
    fields = ['name']
    template_name = 'menu/category_form.html'
    success_url = reverse_lazy('menu')

class CategoryUpdateView(LoginRequiredMixin, UpdateView):
    model = Category
    fields = ['name']
    template_name = 'menu/category_form.html'
    success_url = reverse_lazy('menu')

class CategoryDeleteView(LoginRequiredMixin, DeleteView):
    model = Category
    template_name = 'menu/category_confirm_delete.html'
    success_url = reverse_lazy('menu')

# Table Views
class TableCreateView(LoginRequiredMixin, CreateView):
    model = Table
    fields = ['number', 'capacity']
    template_name = 'tables/table_form.html'
    success_url = reverse_lazy('tables')





def home(request):
    return render(request, 'home.html')

'''
# views.py
@login_required
@role_required(['manager'])
def sales_report(request):
    today = timezone.now().date()
    orders = Order.objects.filter(
        created_at__date=today,
        status='paid'
    )
    total_sales = sum(order.total() for order in orders)
    
    context = {
        'orders': orders,
        'total_sales': total_sales,
        'date': today
    }
    return render(request, 'reports/sales.html', context)

'''
# Order Item Views
@login_required
def order_item_add(request, order_id):
    order = get_object_or_404(Order, pk=order_id)
    if request.method == 'POST':
        form = OrderItemForm(request.POST)
        if form.is_valid():
            order_item = form.save(commit=False)
            order_item.order = order
            order_item.save()

            # Log the action
            log_activity(
                user=request.user,
                action_type="CREATE",
                description=f"Added item {order_item.menu_item.name} to Order #{order.id}",
                related_model="OrderItem",
                related_id=order_item.id,
                ip_address=get_client_ip(request)
            )

            messages.success(request, 'Item added to order!')
            return redirect('order_detail', pk=order_id)
    else:
        form = OrderItemForm()
    return render(request, 'orders/add_item.html', {'form': form, 'order': order})

@login_required
def order_item_remove(request, item_id):
    order_item = get_object_or_404(OrderItem, pk=item_id)
    order_id = order_item.order.id

    # Log the action
    log_activity(
        user=request.user,
        action_type="DELETE",
        description=f"Removed item {order_item.menu_item.name} from Order #{order_id}",
        related_model="OrderItem",
        related_id=order_item.id,
        ip_address=get_client_ip(request)
    )

    order_item.delete()
    messages.success(request, 'Item removed from order!')
    return redirect('order_detail', pk=order_id)

@login_required
def menu_list(request):
    menu_items = MenuItem.objects.filter(available=True)
    categories = Category.objects.all()
    return render(request, 'menu/list.html', {
        'menu_items': menu_items,
        'categories': categories,
    })

@login_required
def table_list(request):
    tables = Table.objects.all()
    return render(request, 'tables/list.html', {'tables': tables})

@login_required
def order_list(request):
    if request.user.role == 'customer':
        orders = Order.objects.filter(customer=request.user).order_by('-created_at')
    else:
        orders = Order.objects.all().order_by('-created_at')
    return render(request, 'orders/list.html', {'orders': orders})

@login_required
def order_create(request):
    if request.method == 'POST':
        form = OrderForm(request.POST)
        if form.is_valid():
            order = form.save(commit=False)
            order.server = request.user
            order.save()

            # Log the action
            log_activity(
                user=request.user,
                action_type="CREATE",
                description=f"Created Order #{order.id}",
                related_model="Order",
                related_id=order.id,
                ip_address=get_client_ip(request)
            )

            messages.success(request, 'Order created successfully!')
            return redirect('order_detail', pk=order.pk)
    else:
        form = OrderForm()
    return render(request, 'orders/create.html', {'form': form})

@login_required
def order_detail(request, pk):
    order = get_object_or_404(Order, pk=pk)
    context = {
        'order': order,
        'subtotal': order.subtotal(),
        'tax': order.tax(),
        'total': order.total(),
    }
    return render(request, 'orders/detail.html', context)

@login_required
def order_update(request, pk):
    order = get_object_or_404(Order, pk=pk)
    if request.method == 'POST':
        form = OrderForm(request.POST, instance=order)
        if form.is_valid():
            form.save()

            # Log the action
            log_activity(
                user=request.user,
                action_type="UPDATE",
                description=f"Updated Order #{order.id}",
                related_model="Order",
                related_id=order.id,
                ip_address=get_client_ip(request)
            )

            messages.success(request, 'Order updated successfully!')
            return redirect('order_detail', pk=order.pk)
    else:
        form = OrderForm(instance=order)
    return render(request, 'orders/update.html', {'form': form, 'order': order})

@login_required
def order_delete(request, pk):
    order = get_object_or_404(Order, pk=pk)
    if request.method == 'POST':

        # Log the action
        log_activity(
            user=request.user,
            action_type="DELETE",
            description=f"Deleted Order #{order.id}",
            related_model="Order",
            related_id=order.id,
            ip_address=get_client_ip(request)
        )

        order.delete()
        messages.success(request, 'Order deleted successfully!')
        return redirect('orders')
    return render(request, 'orders/delete.html', {'order': order})

# Stock Management Views
@login_required
@role_required('manager')
def ingredient_list(request):
    ingredients = Ingredient.objects.all()
    return render(request, 'stock/ingredient_list.html', {'ingredients': ingredients})

@login_required
@role_required('manager')
def ingredient_create(request):
    if request.method == 'POST':
        form = IngredientForm(request.POST)
        if form.is_valid():
            ingredient = form.save()
            # Create initial stock record
            Stock.objects.create(
                ingredient=ingredient,
                current_quantity=0,
                alert_threshold=ingredient.minimum_quantity
            )

            # Log the action
            log_activity(
                user=request.user,
                action_type="CREATE",
                description=f"Created Ingredient {ingredient.name}",
                related_model="Ingredient",
                related_id=ingredient.id,
                ip_address=get_client_ip(request)
            )
            messages.success(request, 'Ingredient created successfully.')
            return redirect('ingredient_list')
    else:
        form = IngredientForm()
    return render(request, 'stock/ingredient_form.html', {'form': form, 'title': 'Create Ingredient'})

@login_required
@role_required('manager')
def ingredient_update(request, pk):
    ingredient = get_object_or_404(Ingredient, pk=pk)
    if request.method == 'POST':
        form = IngredientForm(request.POST, instance=ingredient)
        if form.is_valid():
            form.save()

            # Log the action
            log_activity(
                user=request.user,
                action_type="UPDATE",
                description=f"Updated Ingredient #{ingredient.id} - {ingredient.name}",
                related_model="Ingredient",
                related_id=ingredient.id,
                ip_address=get_client_ip(request)
            )

            messages.success(request, 'Ingredient updated successfully.')
            return redirect('ingredient_list')
    else:
        form = IngredientForm(instance=ingredient)
    return render(request, 'stock/ingredient_form.html', {'form': form, 'title': 'Update Ingredient'})

@login_required
@role_required('manager')
def stock_update(request, pk):
    ingredient = get_object_or_404(Ingredient, pk=pk)
    stock, created = Stock.objects.get_or_create(ingredient=ingredient)
    
    if request.method == 'POST':
        form = StockUpdateForm(request.POST, instance=stock)
        if form.is_valid():
            form.save()

            # Log the action
            log_activity(
                user=request.user,
                action_type="UPDATE",
                description=f"Updated Stock for Ingredient #{ingredient.id} - {ingredient.name}",
                related_model="Stock",
                related_id=stock.id,
                ip_address=get_client_ip(request)
            )

            messages.success(request, 'Stock level updated successfully.')
            return redirect('ingredient_list')
    else:
        form = StockUpdateForm(instance=stock)
    return render(request, 'stock/stock_update.html', {'form': form, 'ingredient': ingredient})

@login_required
@role_required('manager')
def stock_transaction_create(request, pk):
    ingredient = get_object_or_404(Ingredient, pk=pk)
    if request.method == 'POST':
        form = StockTransactionForm(request.POST)
        if form.is_valid():
            transaction = form.save(commit=False)
            transaction.ingredient = ingredient
            transaction.created_by = request.user
            transaction.save()

            # Log the action
            log_activity(
                user=request.user,
                action_type="CREATE",
                description=f"Created Stock Transaction #{transaction.id} for Ingredient #{ingredient.id} - {ingredient.name}",
                related_model="StockTransaction",
                related_id=transaction.id,
                ip_address=get_client_ip(request)
            )

            messages.success(request, 'Stock transaction recorded successfully.')
            return redirect('ingredient_list')
    else:
        form = StockTransactionForm()
    return render(request, 'stock/transaction_form.html', {
        'form': form,
        'ingredient': ingredient,
        'title': 'Create Stock Transaction'
    })

@login_required
@role_required('manager')
def stock_transaction_list(request):
    transactions = StockTransaction.objects.all().order_by('-created_at')
    return render(request, 'stock/transaction_list.html', {'transactions': transactions})

class ActivityLogView(LoginRequiredMixin, UserPassesTestMixin, ListView):
    model = ActivityLog
    template_name = 'manager/activity_log.html'
    context_object_name = 'activities'
    paginate_by = 20
    
    def test_func(self):
        return self.request.user.role == 'manager'
    
    def get_queryset(self):
        return ActivityLog.objects.all().order_by('-created_at')

@login_required
def delivery_orders(request):
    if request.user.role != 'deliveryboy':
        return HttpResponseForbidden("You don't have permission to access this page.")

    # Get orders assigned to the delivery boy or unassigned orders
    orders = Order.objects.filter(
        Q(delivery_boy=request.user) | Q(status='ready')
    ).order_by('-created_at')

    return render(request, 'delivery/orders.html', {'orders': orders})


@login_required
def accept_order(request, order_id):
    if request.user.role != 'deliveryboy':
        return HttpResponseForbidden("You don't have permission to access this page.")

    order = get_object_or_404(Order, id=order_id, status='ready')
    order.delivery_boy = request.user
    order.status = 'out_for_delivery'
    order.save()

    # Log the action
    log_activity(
        user=request.user,
        action_type="UPDATE",
        description=f"Accepted Order #{order.id}",
        related_model="Order",
        related_id=order.id,
        ip_address=get_client_ip(request)
    )

    messages.success(request, f"Order #{order.id} accepted successfully!")
    return redirect('delivery_orders')


@login_required
def complete_order(request, order_id):
    if request.user.role != 'deliveryboy':
        return HttpResponseForbidden("You don't have permission to access this page.")

    order = get_object_or_404(Order, id=order_id, delivery_boy=request.user, status='out_for_delivery')
    order.status = 'paid'
    order.save()

    # Log the action
    log_activity(
        user=request.user,
        action_type="UPDATE",
        description=f"Completed Order #{order.id}",
        related_model="Order",
        related_id=order.id,
        ip_address=get_client_ip(request)
    )

    messages.success(request, f"Order #{order.id} marked as completed and paid!")
    return redirect('dashboard')