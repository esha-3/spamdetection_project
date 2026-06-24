from django.urls import path
from . import views

urlpatterns = [
    path('api/check/', views.check_spam_api, name='check_spam_api'),
    path('api/history/', views.get_history_api, name='get_history_api'),
    path('api/history/<int:pk>/', views.delete_history_item_api, name='delete_history_item_api'),
    path('api/stats/', views.get_stats_api, name='get_stats_api'),
]
