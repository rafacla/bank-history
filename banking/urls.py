from django.urls import path
from . import views

app_name = 'banking'

urlpatterns = [
    path('', views.AccountListView.as_view(), name='home'),
    path('accounts/', views.AccountListView.as_view(), name='account_list'),
    path('accounts/<int:pk>/detail', views.AccountDetailView.as_view(), name='account_detail'),
    path('accounts/create/', views.AccountCreateView.as_view(), name='account_create'),
    path('accounts/<int:pk>/update/', views.AccountUpdateView.as_view(), name='account_update'),
    path('accounts/<int:pk>/delete/', views.AccountDeleteView.as_view(), name='account_delete'),
    path('categories/', views.CategoryListView.as_view(), name='category_list'),
    path('categories/<int:pk>/detail', views.CategoryDetailView.as_view(), name='category_detail'),
    path('categories/create/', views.CategoryCreateView.as_view(), name='category_create'),
    path('categories/<int:pk>/update/', views.CategoryUpdateView.as_view(), name='category_update'),
    path('categories/<int:pk>/delete/', views.CategoryDeleteView.as_view(), name='category_delete'),
    path('transactions/', views.CategoryListView.as_view(), name='transaction_list'),
    path('transactions/<int:pk>/statement', views.CategoryDetailView.as_view(), name='account_statement'),
]