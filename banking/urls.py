from django.urls import path, register_converter
from . import views
from banking.converters import DateConverter


app_name = 'banking'
register_converter(DateConverter, 'date')

urlpatterns = [
    path('', views.DashboardView.as_view(), name='home'),
    path('dashboard/', views.DashboardView.as_view(), name='dashboard'),
    path('accounts/', views.AccountListView.as_view(), name='account_list'),
    path('accounts/<int:pk>/detail', views.AccountDetailView.as_view(), name='account_detail'),
    path('accounts/create/', views.AccountCreateView.as_view(), name='account_create'),
    path('accounts/<int:pk>/update/', views.AccountUpdateView.as_view(), name='account_update'),
    path('accounts/<int:pk>/delete/', views.AccountDeleteView.as_view(), name='account_delete'),
    path('categories/', views.CategoryListView.as_view(), name='category_list'),
    path('categories/<int:pk>/detail', views.CategoryDetailView.as_view(), name='category_detail'),
    path('categories/create/<str:type>/', views.CategoryCreateView.as_view(), name='category_create'),
    path('categories/create/<str:type>/<int:nested_to_id>/', views.CategoryCreateView.as_view(), name='category_create'),
    path('categories/<int:pk>/update/', views.CategoryUpdateView.as_view(), name='category_update'),
    path('categories/<int:pk>/delete/', views.CategoryDeleteView.as_view(), name='category_delete'),
    path('transactions/', views.TransactionListView.as_view(), name='transaction_list'),
    path('transactions/<int:pk>/detail', views.TransactionDetailView.as_view(), name='transaction_detail'),
    path('transactions/create/', views.TransactionCreateView.as_view(), name='transaction_create'),
    path('transactions/<int:pk>/update/', views.TransactionUpdateView.as_view(), name='transaction_update'),
    path('transactions/delete/<str:transaction_ids>/', views.TransactionDeleteView.as_view(), name='transaction_delete'),
    path('transactions/internal_transfer/<str:transaction_ids>/', views.TransactionInternalTransferView.as_view(), name='transaction_internal_transfer'),
    path('transactions/categorize/<str:transaction_ids>/', views.TransactionCategorizeView.as_view(), name='transaction_categorize'),
    path('transactions/merge/<str:transaction_ids>/', views.TransactionMergeView.as_view(), name='transaction_merge'),
    path('transactions/import/', views.import_csv, name='import_csv'),
    path('rules/', views.RuleListView.as_view(), name='rule_list'),
    path('rules/create/', views.RuleListView.as_view(), name='rule_create'),
    path('rules/<int:pk>/update/', views.CategoryUpdateView.as_view(), name='rule_update'),
    path('rules/<int:pk>/delete/', views.CategoryDeleteView.as_view(), name='rule_delete'),
    path('rules/<int:pk>/run/', views.CategoryDeleteView.as_view(), name='rule_run'),
]