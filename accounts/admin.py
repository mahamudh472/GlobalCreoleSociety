from django.contrib import admin
from .models import User, Education, Location, Work, Friendship, SiteSetting


class EducationInline(admin.StackedInline):
    model = Education
    extra = 0
class LocationInline(admin.StackedInline):
    model = Location
    extra = 0
class WorkInline(admin.StackedInline):
    model = Work
    extra = 0

class UserAdmin(admin.ModelAdmin):
    list_display = ('email', 'profile_name', 'is_staff', 'is_active')
    search_fields = ('email', 'profile_name')
    readonly_fields = ('date_joined', 'last_login')
    inlines = [LocationInline, WorkInline, EducationInline]

admin.site.register(User, UserAdmin)
class FriendshipAdmin(admin.ModelAdmin):
    list_display = ('id', 'requester', 'receiver', 'created_at')
    search_fields = ('requester__email', 'receiver__email')
    readonly_fields = ('created_at',)
admin.site.register(Friendship, FriendshipAdmin)

class SiteSettingAdmin(admin.ModelAdmin):
    list_display = ('product_tax', 'shipping_cost')
    search_fields = ('product_tax', 'shipping_cost')

admin.site.register(SiteSetting, SiteSettingAdmin)