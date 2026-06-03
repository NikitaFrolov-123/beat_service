from .models import SiteSettings

def site_settings(request):
    settings_obj = SiteSettings.objects.first()
    if not settings_obj:
        settings_obj = SiteSettings.objects.create()
    return {'site_settings': settings_obj}