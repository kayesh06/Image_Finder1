# bot/urls.py
from django.urls import path
from . import views

urlpatterns = [
    path('login/', views.google_login, name='google_login'),
    path('oauth2callback/', views.oauth2_callback, name='oauth2_callback'),
    path('match-image/', views.match_image, name='match_image'),
    path('auth-status/', views.auth_status, name='auth_status'),
]