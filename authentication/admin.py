from django.contrib import admin
from .models import User,AppVersion,UserSecurity
# Register your models here.
admin.site.register(User)
admin.site.register(AppVersion)
admin.site.register(UserSecurity)