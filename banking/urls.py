from django.urls import path
from . import views

app_name = 'banking'

urlpatterns = [
    path('accounts/', views.AccountListView.as_view(), name='account_list'),
    path('accounts/<int:pk>/detail', views.AccountDetailView.as_view(), name='account_detail'),
    path('accounts/create/', views.AccountCreateView.as_view(), name='account_create'),
    path('accounts/<int:pk>/update/', views.AccountUpdateView.as_view(), name='account_update'),
    path('accounts/<int:pk>/delete/', views.AccountDeleteView.as_view(), name='account_delete'),
]