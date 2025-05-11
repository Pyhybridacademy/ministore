from .models import StoreSettings

def store_settings(request):
    settings = StoreSettings.objects.first()
    return {'store_settings': settings}