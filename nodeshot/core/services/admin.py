from django.contrib import admin
from django.conf import settings
from nodeshot.core.base.admin import BaseAdmin, BaseStackedInline#, BaseTabularInline
from models import Category, Service, Login, Port
from nodeshot.core.network.models import Ip

class CategoryAdmin(BaseAdmin):
    list_display  = ('name', 'description', 'added', 'updated')
    ordering = ('name',)
    search_fields = ('name', 'description')

class PortInline(BaseStackedInline):
    model = Port

class LoginInline(BaseStackedInline):
    model = Login

class ServiceAdmin(BaseAdmin):
    list_display  = ('name', 'device', 'category', 'access_level', 'status', 'is_published', 'added', 'updated')
    list_filter   = ('category', 'status', 'is_published')
    filter_horizontal = ['ips']
    search_fields = ('name', 'description', 'uri', 'documentation_url')
    inlines = (PortInline, LoginInline,)
    
    def get_object(self, request, object_id):
        """
        Hook obj for use in formfield_for_manytomany
        """
        self.obj = super(ServiceAdmin, self).get_object(request, object_id)
        return self.obj
    
    def formfield_for_manytomany(self, db_field, request, **kwargs):
        if db_field.name == "ips" and getattr(self, 'obj', None):
            kwargs["queryset"] = Ip.objects.select_related().filter(interface__device=self.obj.device)
        return super(ServiceAdmin, self).formfield_for_manytomany(db_field, request, **kwargs)

admin.site.register(Category, CategoryAdmin)
admin.site.register(Service, ServiceAdmin)