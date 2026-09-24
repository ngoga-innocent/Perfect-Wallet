
from django.contrib import admin
from django.urls import include, path
from authentication.views import home
urlpatterns = [
    path('', home, name='home'),
    path('admin/', admin.site.urls),
    path('api/auth/', include('authentication.urls')),
    path('api/accounts/', include('Accounts.urls')),
    path('api/transactions/', include('transactions.urls')),
    path('api/loans/', include('loans.urls')),
    path('api/financial-reminders/', include('reminders.urls')),
    path('api/dashboard/', include('dashboard.urls')),
]
