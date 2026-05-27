from django.urls import path
from . import views

app_name = 'beauty_salon'

urlpatterns = [
    path('', views.index, name='index'),

    path('users/', views.users_list, name='users_list'),
    path('users/create/', views.user_create, name='user_create'),
    path('users/<int:user_id>/update/', views.user_update, name='user_update'),
    path('users/<int:user_id>/delete/', views.user_delete, name='user_delete'),

    path('services/', views.services_list, name='services_list'),
    path('services/category/<int:category_id>/', views.services_list, name='services_by_category'),
    path('services/<int:service_id>/', views.service_detail, name='service_detail'),
    path('services/create/', views.service_create, name='service_create'),
    path('services/<int:service_id>/update/', views.service_update, name='service_update'),
    path('services/<int:service_id>/delete/', views.service_delete, name='service_delete'),

    path('appointments/', views.appointments_list, name='appointments_list'),
    path('appointments/my/', views.my_appointments_view, name='my_appointments'),
    path('appointments/create/', views.appointment_create, name='appointment_create'),
    path('appointments/<int:pk>/update/', views.appointment_update, name='appointment_update'),
    path('appointments/<int:pk>/cancel/', views.appointment_cancel, name='appointment_cancel'),
    path('appointments/<int:pk>/delete/', views.appointment_delete, name='appointment_delete'),

    path('masters/', views.masters_list, name='masters_list'),
    path('masters/<int:user_id>/', views.master_detail, name='master_detail'),

    path('notifications/', views.notifications_list, name='notifications_list'),
]