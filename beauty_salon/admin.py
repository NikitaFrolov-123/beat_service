from django.contrib import admin
from django import forms
from django.utils.html import format_html

from .models import (
    Role, User, RoleUser, ServiceCategory, Service, Appointment,
    AppointmentService, Payment, Review, Product, ProductUsage
)


@admin.register(Role)
class RoleAdmin(admin.ModelAdmin):
    list_display = ('id', 'name')
    search_fields = ('name',)
    ordering = ('name',)


class UserAdminForm(forms.ModelForm):
    password = forms.CharField(
        label='Пароль',
        widget=forms.PasswordInput,
        required=False
    )

    class Meta:
        model = User
        fields = ('email', 'phone', 'full_name', 'password', 'role', 'photo')


@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    form = UserAdminForm
    list_display = ('id', 'email', 'full_name', 'phone', 'role', 'photo_preview', 'created_at')
    search_fields = ('email', 'full_name', 'phone')
    list_filter = ('role', 'created_at')
    ordering = ('-created_at',)
    readonly_fields = ('photo_preview',)

    fieldsets = (
        (None, {
            'fields': ('email', 'phone', 'full_name', 'password', 'role', 'photo', 'photo_preview')
        }),
    )

    def photo_preview(self, obj):
        if obj and obj.photo:
            return format_html(
                '<img src="{}" style="width: 140px; height: 140px; object-fit: cover; border-radius: 8px; border: 1px solid #ddd;" />',
                obj.photo.url
            )
        return "Фото не загружено"

    photo_preview.short_description = "Фото"

    def save_model(self, request, obj, form, change):
        password = form.cleaned_data.get('password')
        if password:
            obj.set_password(password)
        super().save_model(request, obj, form, change)


@admin.register(RoleUser)
class RoleUserAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'role')
    search_fields = ('user__email', 'user__full_name', 'role__name')
    list_filter = ('role',)
    ordering = ('user',)


@admin.register(ServiceCategory)
class ServiceCategoryAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'description')
    search_fields = ('name', 'description')
    list_filter = ('name',)
    ordering = ('name',)


@admin.register(Service)
class ServiceAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'category', 'duration_minutes', 'price', 'is_active', 'image_preview')
    search_fields = ('name', 'description', 'category__name')
    list_filter = ('category', 'is_active', 'duration_minutes')
    ordering = ('category', 'name')
    filter_horizontal = ('masters',)
    readonly_fields = ('image_preview',)

    fieldsets = (
        (None, {
            'fields': (
                'name',
                'category',
                'duration_minutes',
                'price',
                'description',
                'is_active',
                'image',
                'masters',
                'image_preview',
            )
        }),
    )

    def image_preview(self, obj):
        if obj and obj.image:
            return format_html(
                '<img src="{}" style="width: 160px; height: 160px; object-fit: cover; border-radius: 8px; border: 1px solid #ddd;" />',
                obj.image.url
            )
        return "Фото не загружено"

    image_preview.short_description = "Фото"


@admin.register(Appointment)
class AppointmentAdmin(admin.ModelAdmin):
    list_display = ('appointment_id', 'client', 'master', 'start_datetime', 'end_datetime', 'status', 'created_at')
    search_fields = ('client__email', 'client__full_name', 'master__email', 'master__full_name', 'status', 'notes')
    list_filter = ('status', 'start_datetime', 'master')
    ordering = ('-start_datetime',)


@admin.register(AppointmentService)
class AppointmentServiceAdmin(admin.ModelAdmin):
    list_display = ('id', 'appointment', 'service')
    search_fields = ('appointment__client__full_name', 'service__name')
    list_filter = ('service',)
    ordering = ('appointment',)


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ('payment_id', 'appointment', 'payment_method', 'payment_date', 'is_paid', 'amount')
    search_fields = ('appointment__client__full_name', 'payment_method')
    list_filter = ('payment_method', 'is_paid', 'payment_date')
    ordering = ('-payment_date',)


@admin.register(Review)
class ReviewAdmin(admin.ModelAdmin):
    list_display = ('review_id', 'appointment', 'client', 'rating', 'created_at')
    search_fields = ('comment', 'client__full_name', 'appointment__client__full_name')
    list_filter = ('rating', 'created_at')
    ordering = ('-created_at',)


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ('product_id', 'name', 'category', 'quantity', 'min_quantity', 'purchase_price', 'retail_price', 'unit')
    search_fields = ('name', 'category', 'unit')
    list_filter = ('category', 'unit')
    ordering = ('name',)


@admin.register(ProductUsage)
class ProductUsageAdmin(admin.ModelAdmin):
    list_display = ('usage_id', 'appointment', 'product', 'quantity_used', 'usage_date')
    search_fields = ('product__name', 'appointment__client__full_name')
    list_filter = ('usage_date', 'product')
    ordering = ('-usage_date',)