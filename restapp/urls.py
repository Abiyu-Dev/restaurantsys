#restapp/urls.py

from django.urls import path
from . import views
from .views import *


from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('', views.home, name='home'),
    path('menu/', views.menu_list, name='menu'),
    path('tables/', views.table_list, name='tables'),
    path('orders/create/', views.create_order, name='create_order'),
    path('server/orders/', views.server_orders, name='server_orders'),
    path('orders/', views.order_list, name='orders'),
    path('order/create/', views.order_create, name='order_create'),
    path('order/<int:pk>/', views.order_detail, name='order_detail'),
    path('order/<int:pk>/update/', views.order_update, name='order_update'),
    path('order/<int:pk>/delete/', views.order_delete, name='order_delete'),

    path('cart/', views.cart_view, name='cart'),
    path('cart/add/<int:item_id>/', views.add_to_cart, name='add_to_cart'),
    path('cart/count/', views.cart_count, name='cart_count'),
    path('cart/remove/<int:item_id>/', views.remove_from_cart, name='remove_from_cart'),
    path('cart/update/<int:item_id>/', views.update_cart, name='update_cart'),

    path('checkout/', views.checkout_view, name='checkout'),
    path('checkout/success/<int:order_id>/', views.checkout_success, name='checkout_success'),
    # Menu Item URLs
    path('menu/item/add/', views.MenuItemCreateView.as_view(), name='menu_item_add'),
    path('menu/item/<int:pk>/edit/', views.MenuItemUpdateView.as_view(), name='menu_item_edit'),
    path('menu/item/<int:pk>/delete/', views.MenuItemDeleteView.as_view(), name='menu_item_delete'),

    # Category URLs
    path('menu/category/add/', views.CategoryCreateView.as_view(), name='category_add'),
    path('menu/category/<int:pk>/edit/', views.CategoryUpdateView.as_view(), name='category_edit'),
    path('menu/category/<int:pk>/delete/', views.CategoryDeleteView.as_view(), name='category_delete'),

    # Table URLs
    path('tables/add/', views.TableCreateView.as_view(), name='table_add'),
    path('tables/<int:pk>/edit/', views.TableUpdateView.as_view(), name='table_edit'),
    path('tables/<int:pk>/delete/', views.TableDeleteView.as_view(), name='table_delete'),

    # Order Item URLs
    path('order/<int:order_id>/add-item/', views.order_item_add, name='order_item_add'),
    path('order/item/<int:item_id>/remove/', views.order_item_remove, name='order_item_remove'),
    path('dashboard/', views.dashboard, name='dashboard'),
    
    path('menu/search/', views.menu_search, name='menu_search'),
    path('order/<int:pk>/rate/', views.order_rate, name='order_rate'),
    path('customer/orders/', CustomerOrderListView.as_view(), name='customer_orders'),
    path('customer/orders/<int:pk>/', CustomerOrderDetailView.as_view(), name='customer_order_detail'),
    path('customer/dashboard/', CustomerDashboardView.as_view(), name='customer_dashboard'),

    path('order/', CustomerOrderCreateView.as_view(), name='customer_order'),
    path('orders/', CustomerOrderListView.as_view(), name='customer_orders'),
    path('orders/<int:pk>/', CustomerOrderDetailView.as_view(), name='customer_order_detail'),

    path('manager/dashboard/', ManagerDashboardView.as_view(), name='manager_dashboard'),
    path('manager/activity-log/', ActivityLogView.as_view(), name='activity_log'),
    path('manager/sales-report/', sales_report, name='sales_report'),
    # Menu Item URLs
    path('manager/menu-items/', MenuItemListView.as_view(), name='menu_item_list'),
    path('manager/menu-items/create/', MenuItemCreateView.as_view(), name='menu_item_create'),
    path('manager/menu-items/<int:pk>/update/', MenuItemUpdateView.as_view(), name='menu_item_update'),
    
    path('manager/staff/create/', StaffCreateView.as_view(), name='staff_create'),
    # Table URLs
    path('manager/tables/', TableListView.as_view(), name='table_list'),
    path('manager/tables/create/', TableCreateView.as_view(), name='table_create'),
    path('manager/tables/<int:pk>/update/', TableUpdateView.as_view(), name='table_update'),

    path('ingredients/', ingredient_list, name='ingredient_list'),
    path('ingredients/create/', ingredient_create, name='ingredient_create'),
    path('ingredients/<int:pk>/update/', ingredient_update, name='ingredient_update'),
    path('ingredients/<int:pk>/stock/', stock_update, name='stock_update'),
    path('ingredients/<int:pk>/transaction/', stock_transaction_create, name='stock_transaction_create'),
    path('transactions/', stock_transaction_list, name='stock_transaction_list'),

    path('chef/orders/', ChefOrderListView.as_view(), name='chef_orders'),
    path('chef/orders/<int:pk>/update/', ChefOrderUpdateView.as_view(), name='chef_update_order'),

    path('reservations/', views.reservation_list, name='reservations'),
    path('reservation/create/', views.reservation_create, name='reservation_create'),
    path('reservation/<int:pk>/', views.reservation_detail, name='reservation_detail'),
    path('reservation/<int:pk>/update/', ReservationUpdateView.as_view(), name='reservation_update'),
    path('reservation/<int:pk>/delete/', ReservationDeleteView.as_view(), name='reservation_delete'),

    path('staff/', views.StaffListView.as_view(), name='staff_list'),
    path('staff/<int:pk>/edit/', views.StaffUpdateView.as_view(), name='staff_edit'),
    path('signup/', SignUpView.as_view(), name='signup'),

    path('delivery/orders/', views.delivery_orders, name='delivery_orders'),
    path('delivery/orders/<int:order_id>/accept/', views.accept_order, name='accept_order'),
    path('delivery/orders/<int:order_id>/complete/', views.complete_order, name='complete_order'),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)