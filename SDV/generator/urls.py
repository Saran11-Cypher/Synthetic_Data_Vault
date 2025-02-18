from django.urls import path
from django.contrib.auth.views import LogoutView
from . import views
from .views import  home,user_login, generate_metadata, upload_file, logout_view, custom_logout
app_name = 'generator' 
urlpatterns = [
    path('', home, name='home'),
    path('login/', user_login, name='login'),
    path('generate-metadata/', generate_metadata, name='generate_metadata'),
    path('upload/', upload_file, name='upload_file'),
    path('logout/', logout_view, name='logout'),
    path('logout/', LogoutView.as_view(next_page='login'), name='logout'),
    path('logout/', custom_logout, name='logout'),
    
    path('forgot-password/', views.forgot_password, name='forgot_password'),
    path('verify-otp/', views.verify_otp, name='verify_otp'),
    path('password-reset/', views.password_reset, name='password_reset'),
    path('register/', views.register, name='register'),
    path('manage-users/', views.manage_users, name='manage_users'),
]