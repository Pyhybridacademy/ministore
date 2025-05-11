from django.shortcuts import render, redirect, get_object_or_404
from django.core.paginator import Paginator
from django.http import JsonResponse
from django.contrib.auth.decorators import user_passes_test
from django.core.mail import send_mail
from django.conf import settings
from django.views.decorators.http import require_POST
from django.db.models import Count, Sum
import uuid
import json
from datetime import datetime, timedelta
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from .models import Product, PaymentDetail, Order, StoreSettings, Wishlist

def home(request):
    featured_products = Product.objects.filter(featured=True).order_by('-created_at')
    products = Product.objects.all().order_by('-created_at')
    paginator = Paginator(products, 12)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    payment_details = PaymentDetail.objects.first()
    
    # Ensure session key exists for wishlist
    if not request.session.session_key:
        request.session.create()
    
    return render(request, 'store/home.html', {
        'featured_products': featured_products,
        'page_obj': page_obj,
        'payment_details': payment_details,
    })

@require_POST
def submit_order(request):
    if request.method == 'POST' and request.FILES.get('receipt'):
        try:
            order_id = str(uuid.uuid4())[:8].upper()
            items = request.POST.get('items')
            total = request.POST.get('total')
            receipt = request.FILES['receipt']
            
            order = Order.objects.create(
                order_id=order_id,
                items=items,
                total=total,
                receipt=receipt
            )
            
            # Send email notification to admin
            store_settings = StoreSettings.objects.first()
            if store_settings:
                items_json = json.loads(items)
                items_text = "\n".join([f"- {item['name']} x{item['quantity']} (${float(item['price']) * int(item['quantity'])})" for item in items_json])
                
                email_subject = f"New Order: {order_id}"
                email_message = f"""
                A new order has been placed!
                
                Order ID: {order_id}
                Total: ${total}
                
                Items:
                {items_text}
                
                Please check the admin panel for more details.
                """
                
                send_mail(
                    email_subject,
                    email_message,
                    settings.DEFAULT_FROM_EMAIL,
                    [store_settings.email],
                    fail_silently=True,
                )
            
            return JsonResponse({
                'status': 'success',
                'order_id': order_id
            })
        except Exception as e:
            return JsonResponse({
                'status': 'error',
                'message': str(e)
            }, status=400)
    return JsonResponse({'status': 'error', 'message': 'Invalid request'}, status=400)

# Wishlist views
def wishlist(request):
    if not request.session.session_key:
        request.session.create()
    
    session_key = request.session.session_key
    wishlist_items = Wishlist.objects.filter(session_key=session_key).select_related('product')
    payment_details = PaymentDetail.objects.first()
    
    return render(request, 'store/wishlist.html', {
        'wishlist_items': wishlist_items,
        'payment_details': payment_details,
    })

@require_POST
def add_to_wishlist(request, product_id):
    if not request.session.session_key:
        request.session.create()
    
    session_key = request.session.session_key
    product = get_object_or_404(Product, id=product_id)
    
    # Check if already in wishlist
    wishlist_item, created = Wishlist.objects.get_or_create(
        session_key=session_key,
        product=product
    )
    
    if created:
        return JsonResponse({'status': 'success', 'message': 'Added to wishlist'})
    else:
        return JsonResponse({'status': 'info', 'message': 'Already in wishlist'})

@require_POST
def remove_from_wishlist(request, wishlist_id):
    wishlist_item = get_object_or_404(Wishlist, id=wishlist_id, session_key=request.session.session_key)
    wishlist_item.delete()
    return JsonResponse({'status': 'success'})

def is_admin(user):
    return user.is_staff

@login_required
@user_passes_test(is_admin)
def admin_dashboard(request):
    # Get statistics
    total_products = Product.objects.count()
    total_orders = Order.objects.count()
    recent_orders = Order.objects.order_by('-created_at')[:5]
    
    # Get sales data for the last 7 days
    today = datetime.now().date()
    last_week = today - timedelta(days=7)
    
    daily_orders = Order.objects.filter(
        created_at__date__gte=last_week
    ).extra(
        select={'day': "DATE(created_at)"}
    ).values('day').annotate(
        count=Count('id'),
        total_sales=Sum('total')
    ).order_by('day')
    
    # Format for chart
    days = [(today - timedelta(days=i)).strftime('%a') for i in range(7, 0, -1)]
    order_counts = [0] * 7
    sales_data = [0] * 7
    
    for entry in daily_orders:
        day_str = entry['day']
        try:
            day = datetime.strptime(day_str, '%Y-%m-%d').date()
        except ValueError:
            # Handle the case where the date format is unexpected
            print(f"Unexpected date format: {day_str}")
            continue  # Skip this entry or handle it differently

        day_index = 6 - (today - day).days
        if 0 <= day_index < 7:
            order_counts[day_index] = entry['count']
            sales_data[day_index] = float(entry['total_sales'])
    
    return render(request, 'store/admin/dashboard.html', {
        'total_products': total_products,
        'total_orders': total_orders,
        'recent_orders': recent_orders,
        'days': json.dumps(days),
        'order_counts': json.dumps(order_counts),
        'sales_data': json.dumps(sales_data),
    })
    
@user_passes_test(is_admin)
def admin_products(request):
    products = Product.objects.all().order_by('-created_at')
    return render(request, 'store/admin/products.html', {
        'products': products,
    })

@user_passes_test(is_admin)
def admin_product_edit(request, product_id=None):
    if product_id:
        product = get_object_or_404(Product, id=product_id)
        title = "Edit Product"
    else:
        product = None
        title = "Add New Product"
    
    if request.method == 'POST':
        name = request.POST.get('name')
        price = request.POST.get('price')
        description = request.POST.get('description')
        featured = request.POST.get('featured') == 'on'
        
        if product:
            product.name = name
            product.price = price
            product.description = description
            product.featured = featured
            
            if request.FILES.get('image'):
                product.image = request.FILES['image']
            
            product.save()
        else:
            if request.FILES.get('image'):
                product = Product.objects.create(
                    name=name,
                    price=price,
                    description=description,
                    featured=featured,
                    image=request.FILES['image']
                )
            else:
                return render(request, 'store/admin/product_edit.html', {
                    'product': None,
                    'title': title,
                    'error': 'Image is required'
                })
        
        return redirect('admin_products')
    
    return render(request, 'store/admin/product_edit.html', {
        'product': product,
        'title': title,
    })

@user_passes_test(is_admin)
def admin_product_delete(request, product_id):
    product = get_object_or_404(Product, id=product_id)
    
    if request.method == 'POST':
        product.delete()
        return redirect('admin_products')
    
    return render(request, 'store/admin/product_delete.html', {
        'product': product,
    })

@user_passes_test(is_admin)
def admin_orders(request):
    orders = Order.objects.all().order_by('-created_at')
    return render(request, 'store/admin/orders.html', {
        'orders': orders,
    })

@user_passes_test(is_admin)
def admin_order_detail(request, order_id):
    order = get_object_or_404(Order, order_id=order_id)
    items = json.loads(order.items)
    
    if request.method == 'POST':
        status = request.POST.get('status')
        order.status = status
        order.save()
        return redirect('admin_order_detail', order_id=order_id)
    
    return render(request, 'store/admin/order_detail.html', {
        'order': order,
        'items': items,
    })

@user_passes_test(is_admin)
def admin_settings(request):
    settings = StoreSettings.objects.first()
    
    if request.method == 'POST':
        settings.store_name = request.POST.get('store_name')
        settings.email = request.POST.get('email')
        settings.address = request.POST.get('address')
        settings.phone = request.POST.get('phone')
        settings.whatsapp = request.POST.get('whatsapp')
        settings.instagram = request.POST.get('instagram')
        settings.facebook = request.POST.get('facebook')
        settings.twitter = request.POST.get('twitter')
        
        if request.FILES.get('logo'):
            settings.logo = request.FILES['logo']
        
        settings.save()
        return redirect('admin_settings')
    
    return render(request, 'store/admin/settings.html', {
        'settings': settings,
    })

@user_passes_test(is_admin)
def admin_payment_details(request):
    payment_details = PaymentDetail.objects.first()
    
    if request.method == 'POST':
        payment_details.bank_name = request.POST.get('bank_name')
        payment_details.account_name = request.POST.get('account_name')
        payment_details.account_number = request.POST.get('account_number')
        payment_details.save()
        return redirect('admin_payment_details')
    
    return render(request, 'store/admin/payment_details.html', {
        'payment_details': payment_details,
    })




# Add these views to your views.py file

def admin_login(request):
    if request.user.is_authenticated and request.user.is_staff:
        return redirect('admin_dashboard')
    
    error = None
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        user = authenticate(request, username=username, password=password)
        
        if user is not None and user.is_staff:
            login(request, user)
            return redirect('admin_dashboard')
        else:
            error = "Invalid username or password, or you don't have admin privileges."
    
    return render(request, 'store/admin/login.html', {'error': error})

@login_required
def admin_logout(request):
    logout(request)
    return redirect('home')