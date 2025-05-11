from django.urls import path
from . import views

urlpatterns = [
    # Store front-end
    path('', views.home, name='home'),
    path('submit-order/', views.submit_order, name='submit_order'),
    path('wishlist/', views.wishlist, name='wishlist'),
    path('add-to-wishlist/<int:product_id>/', views.add_to_wishlist, name='add_to_wishlist'),
    path('remove-from-wishlist/<int:wishlist_id>/', views.remove_from_wishlist, name='remove_from_wishlist'),
    
    # Admin panel
    # Add these URL patterns to your urlpatterns list
    path('admin-panel/login/', views.admin_login, name='admin_login'),
    path('admin-panel/logout/', views.admin_logout, name='admin_logout'),
    path('admin-panel/', views.admin_dashboard, name='admin_dashboard'),
    path('admin-panel/products/', views.admin_products, name='admin_products'),
    path('admin-panel/products/add/', views.admin_product_edit, name='admin_product_add'),
    path('admin-panel/products/edit/<int:product_id>/', views.admin_product_edit, name='admin_product_edit'),
    path('admin-panel/products/delete/<int:product_id>/', views.admin_product_delete, name='admin_product_delete'),
    path('admin-panel/orders/', views.admin_orders, name='admin_orders'),
    path('admin-panel/orders/<str:order_id>/', views.admin_order_detail, name='admin_order_detail'),
    path('admin-panel/settings/', views.admin_settings, name='admin_settings'),
    path('admin-panel/payment-details/', views.admin_payment_details, name='admin_payment_details'),
]