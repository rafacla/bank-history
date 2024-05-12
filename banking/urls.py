from django.urls import path, register_converter
from . import views as bankingViews
from banking.converters import DateConverter


app_name = 'banking'
register_converter(DateConverter, 'date')

urlpatterns = [
    path('', bankingViews.DashboardView.as_view(), name='home'),
    path('dashboard/', bankingViews.DashboardView.as_view(), name='dashboard'),
    path('dashboard/transactions/<int:pk>/<str:month>/', bankingViews.DashboardTransactionsFilter.as_view(), name='dashboard_transactions'),
    path('accounts/', bankingViews.AccountListView.as_view(), name='account_list'),
    path('accounts/<int:pk>/detail', bankingViews.AccountDetailView.as_view(), name='account_detail'),
    path('accounts/create/', bankingViews.AccountCreateView.as_view(), name='account_create'),
    path('accounts/<int:pk>/update/', bankingViews.AccountUpdateView.as_view(), name='account_update'),
    path('accounts/<int:pk>/delete/', bankingViews.AccountDeleteView.as_view(), name='account_delete'),
    path('categories/', bankingViews.CategoryListView.as_view(), name='category_list'),
    path('categories/<int:pk>/detail', bankingViews.CategoryDetailView.as_view(), name='category_detail'),
    path('categories/create/<str:type>/', bankingViews.CategoryCreateView.as_view(), name='category_create'),
    path('categories/create/<str:type>/<int:nested_to_id>/', bankingViews.CategoryCreateView.as_view(), name='category_create'),
    path('categories/<int:pk>/update/', bankingViews.CategoryUpdateView.as_view(), name='category_update'),
    path('categories/<int:pk>/delete/', bankingViews.CategoryDeleteView.as_view(), name='category_delete'),
    path('transactions/', bankingViews.TransactionListView.as_view(), name='transaction_list'),
    path('transactions/<int:pk>/detail', bankingViews.TransactionDetailView.as_view(), name='transaction_detail'),
    path('transactions/create/', bankingViews.TransactionCreateView.as_view(), name='transaction_create'),
    path('transactions/<int:pk>/update/', bankingViews.TransactionUpdateView.as_view(), name='transaction_update'),
    path('transactions/delete/<str:ids>/', bankingViews.TransactionDeleteView.as_view(), name='transaction_delete'),
    path('transactions/internal_transfer/<str:transaction_ids>/', bankingViews.TransactionInternalTransferView.as_view(), name='transaction_internal_transfer'),
    path('transactions/categorize/<str:transaction_ids>/', bankingViews.TransactionCategorizeView.as_view(), name='transaction_categorize'),
    path('transactions/merge/<str:transaction_ids>/', bankingViews.TransactionMergeView.as_view(), name='transaction_merge'),
    path('transactions/import/', bankingViews.import_file, name='import_csv'),
    path('rules/', bankingViews.RuleListView.as_view(), name='rule_list'),
    path('rules/create/', bankingViews.RuleCreateView.as_view(), name='rule_create'),
    path('rules/<int:pk>/update/', bankingViews.RuleUpdateView.as_view(), name='rule_update'),
    path('rules/delete/<str:ids>/', bankingViews.RuleDeleteView.as_view(), name='rule_delete'),
    path('rules/<str:ids>/run/', bankingViews.RuleRunView.as_view(), name='rule_run'),
    path('rules/<str:ids>/test/', bankingViews.RuleTestView.as_view(), name='rule_test'),
]