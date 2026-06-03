from django.urls import path
from . import views

app_name = 'beauty_salon'

urlpatterns = [
    path('', views.index, name='index'),

    path('users/', views.users_list, name='users_list'),
    path('users/create/', views.user_create, name='user_create'),
    path('users/<int:user_id>/update/', views.user_update, name='user_update'),
    path('users/<int:user_id>/delete/', views.user_delete, name='users_list'),

    path('services/', views.services_list, name='services_list'),
    path('services/category/<int:category_id>/', views.services_list, name='services_by_category'),
    path('services/<int:service_id>/', views.service_detail, name='service_detail'),
    path('services/create/', views.service_create, name='service_create'),
    path('services/<int:service_id>/update/', views.service_update, name='service_update'),
    path('services/<int:service_id>/delete/', views.service_delete, name='service_delete'),

    path('appointments/', views.appointments_list, name='appointments_list'),
    path('appointments/my/', views.my_appointments_view, name='my_appointments'),
    path('appointments/create/', views.appointment_create, name='appointment_create'),
    path('appointments/create-by-admin/', views.appointment_create_by_admin, name='appointment_create_by_admin'),
    path('appointments/<int:pk>/update/', views.appointment_update, name='appointment_update'),
    path('appointments/<int:pk>/cancel/', views.appointment_cancel, name='appointment_cancel'),
    path('appointments/<int:pk>/delete/', views.appointment_delete, name='appointment_delete'),

    path('masters/', views.masters_list, name='masters_list'),
    path('masters/<int:user_id>/', views.master_detail, name='master_detail'),

    path('notifications/', views.notifications_list, name='notifications_list'),

    path('master/schedule/', views.master_schedule, name='master_schedule'),
    path('master/appointment/<int:pk>/complete/', views.appointment_complete, name='appointment_complete'),
    path('master/appointment/<int:pk>/cancel/', views.appointment_cancel_by_master, name='appointment_cancel_by_master'),
    path('master/appointments/<int:pk>/receipt/', views.appointment_receipt, name='appointment_receipt'),

    path('appointments/<int:appointment_id>/review/', views.review_create, name='review_create'),
    path('reviews/salon/create/', views.review_create_salon, name='review_create_salon'),

    path('admin-panel/', views.admin_panel, name='admin_panel'),
    path('beauty_salon/admin/reports/', views.reports_view, name='reports'),

    path('clients/', views.clients_list, name='clients_list'),
    path('clients/<int:user_id>/', views.client_detail, name='client_detail'),

    path('admin/settings/', views.admin_settings, name='admin_settings'),
]