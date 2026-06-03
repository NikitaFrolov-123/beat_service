from datetime import datetime, timedelta, time
from functools import wraps

from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Q, Count, Avg, Case, When, IntegerField
from django.http import HttpResponseForbidden
from django.shortcuts import render, get_object_or_404, redirect
from django.utils import timezone
from django.views.decorators.http import require_http_methods
from django.db.models import Sum
from django.contrib.auth.decorators import login_required
from django.http import HttpResponseForbidden, JsonResponse

from .forms import ReviewForm
from .models import (
    Role, User, ServiceCategory, Service, Appointment, Payment,
    AppointmentService, Review, Notification, SiteSettings
)

WORK_START = 9
WORK_END = 20
SLOT_STEP = 15


def master_required(view_func):
    @wraps(view_func)
    def _wrapped(request, *args, **kwargs):
        user_id = request.session.get('user_id')
        user_role = request.session.get('user_role')

        if not user_id:
            messages.error(request, 'Нужно войти в аккаунт')
            return redirect('accounts:login')

        if user_role != 'master':
            return HttpResponseForbidden('Доступ только для мастера')

        return view_func(request, *args, **kwargs)
    return _wrapped


def admin_required(view_func):
    @wraps(view_func)
    def _wrapped(request, *args, **kwargs):
        user_id = request.session.get('user_id')
        user_role = request.session.get('user_role')

        if not user_id:
            messages.error(request, 'Нужно войти в аккаунт')
            return redirect('accounts:login')

        if user_role != 'admin':
            return HttpResponseForbidden('Доступ только для администратора')

        return view_func(request, *args, **kwargs)
    return _wrapped


def index(request):
    stats = {
        'total_users': User.objects.count(),
        'total_appointments': Appointment.objects.count(),
        'today_appointments': Appointment.objects.filter(
            start_datetime__date=datetime.now().date()
        ).count(),
    }

    recent = Appointment.objects.select_related('client', 'master').order_by('-created_at')[:5]
    services = Service.objects.select_related('category').prefetch_related('masters').filter(is_active=True)[:6]
    masters = User.objects.filter(role__name='master').annotate(
        avg_rating=Avg('master_reviews__rating', filter=Q(master_reviews__status='approved')),
        reviews_count=Count('master_reviews', filter=Q(master_reviews__status='approved'), distinct=True)
    )[:6]

    salon_reviews = Review.objects.select_related('client').filter(
        review_type=Review.REVIEW_TYPE_SALON,
        status=Review.STATUS_APPROVED
    ).order_by('-created_at')[:6]

    return render(request, 'index.html', {
        'stats': stats,
        'recent': recent,
        'services': services,
        'masters': masters,
        'salon_reviews': salon_reviews,
    })


@admin_required
def users_list(request):
    query = request.GET.get('q', '')
    users = User.objects.select_related('role').filter(
        Q(email__icontains=query) | Q(full_name__icontains=query)
    ).order_by('-created_at')

    paginator = Paginator(users, 20)
    page = request.GET.get('page')

    return render(request, 'users/list.html', {
        'users': paginator.get_page(page),
        'query': query,
    })


@admin_required
@require_http_methods(["GET", "POST"])
def user_create(request):
    if request.method == 'POST':
        try:
            user = User.objects.create(
                email=request.POST['email'],
                phone=request.POST['phone'],
                full_name=request.POST['full_name'],
                password_hash=request.POST['password_hash'],
                role_id=request.POST['role']
            )
            messages.success(request, f'Пользователь {user.full_name} создан')
            return redirect('beauty_salon:users_list')
        except Exception as e:
            messages.error(request, str(e))

    roles = Role.objects.all()
    return render(request, 'users/create.html', {'roles': roles})


@admin_required
@require_http_methods(["GET", "POST"])
def user_update(request, user_id):
    user = get_object_or_404(User, id=user_id)

    if request.method == 'POST':
        try:
            user.email = request.POST['email']
            user.phone = request.POST['phone']
            user.full_name = request.POST['full_name']
            user.password_hash = request.POST['password_hash']
            user.role_id = request.POST['role']
            user.save()
            messages.success(request, 'Пользователь обновлён')
            return redirect('beauty_salon:users_list')
        except Exception as e:
            messages.error(request, str(e))

    roles = Role.objects.all()
    return render(request, 'users/update.html', {'user': user, 'roles': roles})


@admin_required
def user_delete(request, user_id):
    user = get_object_or_404(User, id=user_id)
    if request.method == 'POST':
        try:
            user.delete()
            messages.success(request, 'Пользователь удалён')
        except Exception as e:
            messages.error(request, str(e))
        return redirect('beauty_salon:users_list')
    return render(request, 'users/delete.html', {'user': user})


@admin_required
def admin_panel(request):
    return render(request, 'admin/panel.html')


@admin_required
def reports_view(request):
    now = timezone.localtime(timezone.now())
    today = now.date()

    start_of_day = timezone.make_aware(datetime.combine(today, time.min))
    end_of_day = start_of_day + timedelta(days=1)

    start_of_month = timezone.make_aware(datetime.combine(today.replace(day=1), time.min))
    if today.month == 12:
        next_month_date = today.replace(year=today.year + 1, month=1, day=1)
    else:
        next_month_date = today.replace(month=today.month + 1, day=1)
    end_of_month = timezone.make_aware(datetime.combine(next_month_date, time.min))

    today_appointments = Appointment.objects.filter(
        start_datetime__gte=start_of_day,
        start_datetime__lt=end_of_day
    ).count()

    month_appointments = Appointment.objects.filter(
        start_datetime__gte=start_of_month,
        start_datetime__lt=end_of_month
    ).count()

    today_appointments_completed = Appointment.objects.filter(
        status='completed',
        start_datetime__gte=start_of_day,
        start_datetime__lt=end_of_day
    ).prefetch_related('services')

    month_appointments_completed = Appointment.objects.filter(
        status='completed',
        start_datetime__gte=start_of_month,
        start_datetime__lt=end_of_month
    ).prefetch_related('services')

    today_revenue = sum(
        service.price
        for appointment in today_appointments_completed
        for service in appointment.services.all()
    )

    month_revenue = sum(
        service.price
        for appointment in month_appointments_completed
        for service in appointment.services.all()
    )

    return render(request, 'admin/reports.html', {
        'title': 'Отчёты',
        'today_appointments': today_appointments,
        'month_appointments': month_appointments,
        'today_revenue': today_revenue,
        'month_revenue': month_revenue,
    })


def services_list(request):
    categories = ServiceCategory.objects.all().order_by('name')
    category_id = request.GET.get('category')

    services = Service.objects.select_related('category').prefetch_related('masters').all()
    current_category = None

    if category_id:
        current_category = get_object_or_404(ServiceCategory, id=category_id)
        services = services.filter(category=current_category)

    return render(request, 'services/list.html', {
        'services': services,
        'categories': categories,
        'current_category': current_category,
    })


def service_detail(request, service_id):
    service = get_object_or_404(
        Service.objects.select_related('category').prefetch_related('masters'),
        id=service_id
    )
    masters = service.masters.all()

    return render(request, 'services/detail.html', {
        'service': service,
        'masters': masters,
    })


@admin_required
@require_http_methods(["GET", "POST"])
def service_create(request):
    if request.method == 'POST':
        try:
            service = Service.objects.create(
                name=request.POST['name'],
                category_id=request.POST['category'],
                duration_minutes=int(request.POST['duration']),
                price=request.POST['price'],
                description=request.POST.get('description', ''),
                is_active=request.POST.get('is_active') == 'on'
            )
            masters_ids = request.POST.getlist('masters')
            if masters_ids:
                service.masters.set(masters_ids)
            messages.success(request, 'Услуга создана')
            return redirect('beauty_salon:services_list')
        except Exception as e:
            messages.error(request, str(e))

    categories = ServiceCategory.objects.all().order_by('name')
    masters = User.objects.filter(role__name='master').order_by('full_name')
    return render(request, 'services/create.html', {
        'categories': categories,
        'masters': masters,
    })


@admin_required
@require_http_methods(["GET", "POST"])
def service_update(request, service_id):
    service = get_object_or_404(Service, id=service_id)

    if request.method == 'POST':
        try:
            service.name = request.POST['name']
            service.category_id = request.POST['category']
            service.duration_minutes = int(request.POST['duration'])
            service.price = request.POST['price']
            service.description = request.POST.get('description', '')
            service.is_active = request.POST.get('is_active') == 'on'
            service.save()
            masters_ids = request.POST.getlist('masters')
            service.masters.set(masters_ids)
            messages.success(request, 'Услуга обновлена')
            return redirect('beauty_salon:services_list')
        except Exception as e:
            messages.error(request, str(e))

    categories = ServiceCategory.objects.all().order_by('name')
    masters = User.objects.filter(role__name='master').order_by('full_name')
    selected_masters = service.masters.values_list('id', flat=True)
    return render(request, 'services/update.html', {
        'service': service,
        'categories': categories,
        'masters': masters,
        'selected_masters': selected_masters,
    })


@admin_required
def service_delete(request, service_id):
    service = get_object_or_404(Service, id=service_id)
    if request.method == 'POST':
        service.delete()
        messages.success(request, 'Услуга удалена')
        return redirect('beauty_salon:services_list')
    return render(request, 'services/delete.html', {'service': service})


@admin_required
def appointments_list(request):
    status = request.GET.get('status')
    date_from = request.GET.get('date_from')
    masters = User.objects.filter(role__name='master').order_by('full_name')

    qs = Appointment.objects.select_related('client', 'master').prefetch_related('services').order_by('-start_datetime')

    if status:
        qs = qs.filter(status=status)
    if date_from:
        qs = qs.filter(start_datetime__date__gte=date_from)

    grouped = {}
    for appointment in qs:
        d = appointment.start_datetime.date()
        grouped.setdefault(d, []).append(appointment)

    grouped_appointments = [
        {'date': date, 'appointments': appointments}
        for date, appointments in sorted(grouped.items(), reverse=True)
    ]

    return render(request, 'appointments/list.html', {
        'grouped_appointments': grouped_appointments,
        'masters': masters,
        'status_filter': status,
        'date_from': date_from,
    })


def get_free_slots(master, service_duration, selected_date):
    day_start = timezone.make_aware(datetime.combine(selected_date, time(hour=WORK_START, minute=0)))
    day_end = timezone.make_aware(datetime.combine(selected_date, time(hour=WORK_END, minute=0)))

    appointments = Appointment.objects.filter(
        master=master,
        start_datetime__date=selected_date
    ).order_by('start_datetime')

    slots = []
    current = day_start
    duration_delta = timedelta(minutes=service_duration)

    while current + duration_delta <= day_end:
        slot_end = current + duration_delta

        conflict = appointments.filter(
            start_datetime__lt=slot_end,
            end_datetime__gt=current
        ).exists()

        if not conflict:
            slots.append(current.strftime('%H:%M'))

        current += timedelta(minutes=SLOT_STEP)

    return slots


@require_http_methods(["GET"])
def my_appointments_view(request):
    user_id = request.session.get('user_id')
    if not user_id:
        messages.error(request, 'Нужно войти в аккаунт')
        return redirect('accounts:login')

    client = get_object_or_404(User, pk=user_id)

    appointments = (
        Appointment.objects
        .filter(client=client)
        .select_related('client', 'master')
        .prefetch_related('services', 'reviews')
        .order_by('-start_datetime')
    )

    now = timezone.now()
    for appointment in appointments:
        appointment.can_cancel = appointment.status != 'completed' and appointment.start_datetime > now
        appointment.has_review = appointment.reviews.filter(review_type='master').exists()

    return render(request, 'beauty_salon/my_appointments.html', {
        'appointments': appointments,
    })


@require_http_methods(["GET", "POST"])
def appointment_create(request):
    if request.session.get('user_role') == 'master':
        messages.error(request, 'Мастерам нельзя создавать записи')
        return redirect('beauty_salon:index')

    user_id = request.session.get('user_id')
    if not user_id:
        messages.error(request, 'Нужно войти в аккаунт')
        return redirect('accounts:login')

    client = get_object_or_404(User, pk=user_id)

    selected_service = request.GET.get('service')
    selected_master = request.GET.get('master')
    selected_date = request.GET.get('date')

    masters_qs = User.objects.filter(role__name='master').order_by('full_name')
    services_qs = Service.objects.filter(is_active=True).order_by('name')

    if request.GET.get('json_slots'):
        try:
            service_id = request.GET.get('service')
            master_id = request.GET.get('master')
            date_str = request.GET.get('date')

            if not all([service_id, master_id, date_str]):
                return JsonResponse({'slots': []})

            service = get_object_or_404(Service, id=service_id, is_active=True)
            master = get_object_or_404(User, id=master_id, role__name='master')
            parsed_date = datetime.strptime(date_str, '%Y-%m-%d').date()
            slots = get_free_slots(master, service.duration_minutes, parsed_date)
            return JsonResponse({'slots': slots})
        except Exception:
            return JsonResponse({'slots': []})

    if request.method == 'POST':
        try:
            service_id = request.POST.get('service_id')
            master_id = request.POST.get('master_id')
            selected_date = request.POST.get('date')
            selected_time = request.POST.get('slot_time')
            notes = request.POST.get('notes', '')

            if not all([service_id, master_id, selected_date, selected_time]):
                messages.error(request, 'Заполните все поля и выберите свободное время')
                return redirect('beauty_salon:appointment_create')

            service = get_object_or_404(Service, id=service_id, is_active=True)
            master = get_object_or_404(User, id=master_id, role__name='master')

            if not service.masters.filter(id=master.id).exists():
                messages.error(request, 'Этот мастер не оказывает выбранную услугу')
                return redirect('beauty_salon:appointment_create')

            parsed_date = datetime.strptime(selected_date, '%Y-%m-%d').date()
            parsed_time = datetime.strptime(selected_time, '%H:%M').time()

            start_dt = timezone.make_aware(datetime.combine(parsed_date, parsed_time))
            end_dt = start_dt + timedelta(minutes=service.duration_minutes)

            work_start_dt = timezone.make_aware(datetime.combine(parsed_date, time(hour=WORK_START, minute=0)))
            work_end_dt = timezone.make_aware(datetime.combine(parsed_date, time(hour=WORK_END, minute=0)))

            if start_dt < work_start_dt or end_dt > work_end_dt:
                messages.error(request, 'Время вне рабочего графика')
                return redirect('beauty_salon:appointment_create')

            conflict = Appointment.objects.filter(
                master=master,
                start_datetime__lt=end_dt,
                end_datetime__gt=start_dt
            ).exists()

            if conflict:
                messages.error(request, 'Это время уже занято')
                return redirect('beauty_salon:appointment_create')

            appointment = Appointment.objects.create(
                client=client,
                master=master,
                start_datetime=start_dt,
                end_datetime=end_dt,
                status='new',
                notes=notes
            )

            AppointmentService.objects.create(
                appointment=appointment,
                service=service
            )

            appointment_date = parsed_date.strftime('%d.%m.%Y')

            Notification.objects.create(
                recipient=client,
                text=f'Вы записаны на {service.name} к мастеру {master.full_name} на {appointment_date} в {selected_time}.'
            )

            Notification.objects.create(
                recipient=master,
                text=f'Новая запись: {client.full_name}, услуга {service.name}, {appointment_date} в {selected_time}.'
            )

            messages.success(request, f'Запись #{appointment.appointment_id} создана')
            return redirect('beauty_salon:my_appointments')

        except ValueError:
            messages.error(request, 'Неверный формат даты или времени')
        except Exception as e:
            messages.error(request, f'Ошибка: {e}')

    return render(request, 'appointments/create.html', {
        'masters': masters_qs,
        'services': services_qs,
        'selected_service': selected_service,
        'selected_master': selected_master,
        'selected_date': selected_date,
    })


@require_http_methods(["GET", "POST"])
def appointment_update(request, pk):
    appointment = get_object_or_404(Appointment, pk=pk)

    if request.method == 'POST':
        try:
            appointment.notes = request.POST.get('notes', '')
            appointment.save()
            messages.success(request, 'Запись обновлена')
            return redirect('beauty_salon:appointments_list')
        except Exception as e:
            messages.error(request, str(e))

    return render(request, 'appointments/update.html', {
        'appointment': appointment,
    })


@require_http_methods(["POST"])
def appointment_cancel(request, pk):
    user_id = request.session.get('user_id')
    if not user_id:
        messages.error(request, 'Нужно войти в аккаунт')
        return redirect('accounts:login')

    client = get_object_or_404(User, pk=user_id)
    appointment = get_object_or_404(Appointment, pk=pk, client=client)

    if appointment.start_datetime <= timezone.now():
        messages.error(request, 'Нельзя отменить прошедшую запись')
        return redirect('beauty_salon:my_appointments')

    if appointment.status == 'completed':
        messages.info(request, 'Запись уже отменена')
        return redirect('beauty_salon:my_appointments')

    appointment.status = 'cancelled'
    appointment.save()
    messages.success(request, 'Запись отменена')
    return redirect('beauty_salon:my_appointments')


@require_http_methods(["POST"])
def appointment_delete(request, pk):
    user_id = request.session.get('user_id')
    if not user_id:
        messages.error(request, 'Нужно войти в аккаунт')
        return redirect('accounts:login')

    client = get_object_or_404(User, pk=user_id)
    appointment = get_object_or_404(Appointment, pk=pk, client=client)

    if appointment.start_datetime <= timezone.now():
        messages.error(request, 'Нельзя удалить прошедшую запись')
        return redirect('beauty_salon:my_appointments')

    appointment.delete()
    messages.success(request, 'Запись удалена')
    return redirect('beauty_salon:my_appointments')


def masters_list(request):
    masters = User.objects.filter(
        role__name='master'
    ).annotate(
        appointments_count=Count('master_appointments', distinct=True),
        avg_rating=Avg('master_reviews__rating', filter=Q(master_reviews__status='approved')),
        reviews_count=Count('master_reviews', filter=Q(master_reviews__status='approved'), distinct=True)
    ).prefetch_related('services').order_by('full_name')

    return render(request, 'masters/list.html', {'masters': masters})


def master_detail(request, user_id):
    master = get_object_or_404(
        User.objects.prefetch_related('services').annotate(
            avg_rating=Avg('master_reviews__rating', filter=Q(master_reviews__status='approved')),
            reviews_count=Count('master_reviews', filter=Q(master_reviews__status='approved'), distinct=True)
        ),
        id=user_id,
        role__name='master'
    )
    services = master.services.filter(is_active=True).select_related('category')
    reviews = Review.objects.select_related('client', 'appointment').filter(
        master=master,
        status='approved'
    ).order_by('-created_at')

    return render(request, 'masters/detail.html', {
        'master': master,
        'services': services,
        'reviews': reviews,
    })


@require_http_methods(["GET"])
def notifications_list(request):
    user_id = request.session.get('user_id')
    if not user_id:
        messages.error(request, 'Нужно войти в аккаунт')
        return redirect('accounts:login')

    notifications = Notification.objects.filter(recipient_id=user_id).order_by('-created_at')
    Notification.objects.filter(recipient_id=user_id, is_read=False).update(is_read=True)

    return render(request, 'notifications/list.html', {
        'notifications': notifications
    })


@master_required
def master_schedule(request):
    master = get_object_or_404(User, pk=request.session.get('user_id'), role__name='master')

    appointments = (
        Appointment.objects
        .filter(master=master, start_datetime__date__gte=timezone.localdate())
        .select_related('client', 'master')
        .prefetch_related('services')
        .annotate(
            status_order=Case(
                When(status='new', then=0),
                When(status='completed', then=1),
                When(status='cancelled', then=2),
                default=3,
                output_field=IntegerField(),
            )
        )
        .order_by('status_order', '-start_datetime')
    )

    return render(request, 'masters/schedule.html', {
        'appointments': appointments,
        'master': master,
    })


@master_required
@require_http_methods(["POST"])
def appointment_complete(request, pk):
    master = get_object_or_404(User, pk=request.session.get('user_id'), role__name='master')
    appointment = get_object_or_404(Appointment, pk=pk, master=master)

    if appointment.status == 'completed':
        messages.error(request, 'Нельзя завершить отменённую запись')
        return redirect('beauty_salon:master_schedule')

    if appointment.start_datetime > timezone.now():
        messages.error(request, 'Эту запись пока нельзя отметить как выполненной')
        return redirect('beauty_salon:master_schedule')

    appointment.status = 'completed'
    appointment.notes = request.POST.get('notes', appointment.notes or '')
    appointment.save()

    Notification.objects.create(
        recipient=appointment.client,
        text=f'Ваша услуга {appointment.start_datetime:%d.%m.%Y %H:%M} завершена. Оставьте отзыв о мастере.',
        url=f'/appointments/{appointment.appointment_id}/review/'
    )

    messages.success(request, 'Услуга отмечена как выполненная')
    return redirect('beauty_salon:master_schedule')


@master_required
@require_http_methods(["POST"])
def appointment_cancel_by_master(request, pk):
    master = get_object_or_404(User, pk=request.session.get('user_id'), role__name='master')
    appointment = get_object_or_404(Appointment, pk=pk, master=master)

    if appointment.status == 'completed':
        messages.info(request, 'Запись уже отменена')
        return redirect('beauty_salon:master_schedule')

    reason = request.POST.get('reason', '').strip()

    appointment.status = 'cancelled'
    if reason:
        appointment.notes = (appointment.notes or '') + f'\\n[Отмена мастером] {reason}'
    appointment.save()

    Notification.objects.create(
        recipient=appointment.client,
        text=f'Ваша запись на {appointment.start_datetime:%d.%m.%Y %H:%M} отменена мастером. Причина: {reason or "не указана"}.'
    )

    messages.success(request, 'Запись отменена')
    return redirect('beauty_salon:master_schedule')


@master_required
def appointment_receipt(request, pk):
    master = get_object_or_404(User, pk=request.session.get('user_id'), role__name='master')
    appointment = get_object_or_404(
        Appointment.objects.select_related('client', 'master').prefetch_related('services'),
        pk=pk,
        master=master,
        status='completed'
    )

    total_price = sum(service.price for service in appointment.services.all())

    return render(request, 'masters/receipt.html', {
        'appointment': appointment,
        'total_price': total_price,
    })


@require_http_methods(["GET", "POST"])
def review_create(request, appointment_id):
    user_id = request.session.get('user_id')
    if not user_id:
        messages.error(request, 'Нужно войти в аккаунт')
        return redirect('accounts:login')

    client = get_object_or_404(User, pk=user_id)
    appointment = get_object_or_404(
        Appointment.objects.select_related('client', 'master').prefetch_related('services'),
        pk=appointment_id,
        client=client,
        status='completed'
    )

    if Review.objects.filter(appointment=appointment).exists():
        messages.info(request, 'Отзыв по этой записи уже оставлен')
        return redirect('beauty_salon:my_appointments')

    if request.method == 'POST':
        form = ReviewForm(request.POST)
        if form.is_valid():
            review = form.save(commit=False)
            review.client = client
            review.master = appointment.master
            review.appointment = appointment
            review.review_type = Review.REVIEW_TYPE_MASTER
            review.status = Review.STATUS_PENDING
            review.save()

            Notification.objects.create(
                recipient=appointment.master,
                text=f'Клиент {client.full_name} оставил отзыв на проверку.'
            )

            messages.success(request, 'Отзыв отправлен на модерацию')
            return redirect('beauty_salon:my_appointments')
    else:
        form = ReviewForm()

    return render(request, 'reviews/create.html', {
        'form': form,
        'appointment': appointment,
    })


@require_http_methods(["GET", "POST"])
def review_create_salon(request):
    user_id = request.session.get('user_id')
    if not user_id:
        messages.error(request, 'Нужно войти в аккаунт')
        return redirect('accounts:login')

    client = get_object_or_404(User, pk=user_id)

    if request.method == 'POST':
        form = ReviewForm(request.POST)
        if form.is_valid():
            review = form.save(commit=False)
            review.client = client
            review.review_type = Review.REVIEW_TYPE_SALON
            review.status = Review.STATUS_PENDING
            review.save()

            messages.success(request, 'Отзыв о салоне отправлен на модерацию')
            return redirect('beauty_salon:index')
    else:
        form = ReviewForm()

    return render(request, 'reviews/create.html', {
        'form': form,
        'review_type': Review.REVIEW_TYPE_SALON,
    })


@admin_required
def clients_list(request):
    query = request.GET.get('q', '')

    clients = User.objects.select_related('role').prefetch_related(
        'client_appointments__services'
    ).filter(
        role__name='client'
    )

    if query:
        clients = clients.filter(
            Q(email__icontains=query) |
            Q(full_name__icontains=query) |
            Q(phone__icontains=query)
        )

    clients = clients.order_by('-created_at')

    paginator = Paginator(clients, 20)
    page = request.GET.get('page')

    return render(request, 'clients/list.html', {
        'clients': paginator.get_page(page),
        'query': query,
    })


@admin_required
def client_detail(request, user_id):
    client = get_object_or_404(
        User.objects.select_related('role').prefetch_related(
            'client_appointments__services',
            'reviews_written'
        ),
        id=user_id,
        role__name='client'
    )

    appointments = client.client_appointments.select_related('master').order_by('-start_datetime')

    return render(request, 'clients/detail.html', {
        'client': client,
        'appointments': appointments,
    })


@admin_required
@require_http_methods(["GET", "POST"])
def appointment_create_by_admin(request):
    if request.method == 'POST':
        try:
            service_id = request.POST.get('service_id')
            master_id = request.POST.get('master_id')
            client_phone = request.POST.get('client_phone')
            client_name = request.POST.get('client_name')
            selected_date = request.POST.get('date')
            selected_time = request.POST.get('slot_time')
            notes = request.POST.get('notes', '')

            if not all([service_id, master_id, client_phone, client_name, selected_date, selected_time]):
                messages.error(request, 'Заполните все поля')
                return redirect(request.path)

            client, created = User.objects.get_or_create(
                phone=client_phone,
                defaults={
                    'email': f'{client_phone}@client.local',
                    'full_name': client_name,
                    'role_id': Role.objects.get(name='client').id
                }
            )

            if created:
                messages.info(request, f'Клиент {client_name} создан')

            service = get_object_or_404(Service, id=service_id, is_active=True)
            master = get_object_or_404(User, id=master_id, role__name='master')

            if not service.masters.filter(id=master.id).exists():
                messages.error(request, 'Этот мастер не оказывает выбранную услугу')
                return redirect(request.path)

            parsed_date = datetime.strptime(selected_date, '%Y-%m-%d').date()
            parsed_time = datetime.strptime(selected_time, '%H:%M').time()

            start_dt = timezone.make_aware(datetime.combine(parsed_date, parsed_time))
            end_dt = start_dt + timedelta(minutes=service.duration_minutes)

            conflict = Appointment.objects.filter(
                master=master,
                start_datetime__lt=end_dt,
                end_datetime__gt=start_dt
            ).exists()

            if conflict:
                messages.error(request, 'Это время уже занято')
                return redirect(request.path)

            appointment = Appointment.objects.create(
                client=client,
                master=master,
                start_datetime=start_dt,
                end_datetime=end_dt,
                status='new',
                notes=notes
            )

            AppointmentService.objects.create(
                appointment=appointment,
                service=service
            )

            appointment_date = parsed_date.strftime('%d.%m.%Y')

            Notification.objects.create(
                recipient=client,
                text=f'Вы записаны на {service.name} к мастеру {master.full_name} на {appointment_date} в {selected_time}.'
            )

            Notification.objects.create(
                recipient=master,
                text=f'Новая запись: {client.full_name}, услуга {service.name}, {appointment_date} в {selected_time}.'
            )

            messages.success(request, f'Запись #{appointment.appointment_id} создана')
            return redirect('beauty_salon:appointments_list')

        except Exception as e:
            messages.error(request, f'Ошибка: {e}')

    selected_service_id = request.GET.get('service')
    selected_master_id = request.GET.get('master')
    selected_date = request.GET.get('date')

    all_masters = User.objects.filter(role__name='master').order_by('full_name')
    all_services = Service.objects.filter(is_active=True).order_by('name')

    if selected_master_id:
        all_services = Service.objects.filter(masters__id=selected_master_id, is_active=True).order_by('name')

    if selected_service_id:
        all_masters = User.objects.filter(role__name='master', services__id=selected_service_id).order_by('full_name').distinct()

    if request.GET.get('json_slots'):
        try:
            if not all([selected_service_id, selected_master_id, selected_date]):
                return JsonResponse({'slots': []})

            service = get_object_or_404(Service, id=selected_service_id, is_active=True)
            master = get_object_or_404(User, id=selected_master_id, role__name='master')
            parsed_date = datetime.strptime(selected_date, '%Y-%m-%d').date()
            slots = get_free_slots(master, service.duration_minutes, parsed_date)
            return JsonResponse({'slots': slots})
        except Exception:
            return JsonResponse({'slots': []})

    return render(request, 'appointments/create_by_admin.html', {
        'all_masters': all_masters,
        'all_services': all_services,
        'selected_service_id': selected_service_id,
        'selected_master_id': selected_master_id,
    })


@admin_required
def get_filters_json(request):
    service_id = request.GET.get('service')
    master_id = request.GET.get('master')

    if service_id:
        masters = User.objects.filter(role__name='master', services__id=service_id).distinct()
        master_ids = list(masters.values_list('id', flat=True))
        return JsonResponse({'master_ids': master_ids})

    if master_id:
        services = Service.objects.filter(masters__id=master_id, is_active=True)
        service_ids = list(services.values_list('id', flat=True))
        return JsonResponse({'service_ids': service_ids})

    return JsonResponse({'master_ids': [], 'service_ids': []})


@admin_required
@require_http_methods(["GET", "POST"])
def admin_settings(request):
    settings_obj, created = SiteSettings.objects.get_or_create(pk=1)

    if request.method == 'POST':
        try:
            settings_obj.salon_name = request.POST.get('salon_name', 'Beauty Salon')
            settings_obj.phone = request.POST.get('phone', '')
            settings_obj.email = request.POST.get('email', '')
            settings_obj.work_start = int(request.POST.get('work_start', 9))
            settings_obj.work_end = int(request.POST.get('work_end', 20))
            settings_obj.save()

            messages.success(request, 'Настройки сохранены')
            return redirect('beauty_salon:admin_settings')
        except Exception as e:
            messages.error(request, f'Ошибка при сохранении: {e}')

    total_users = User.objects.count()
    total_appointments = Appointment.objects.count()
    total_services = Service.objects.count()
    total_masters = User.objects.filter(role__name='master').count()

    return render(request, 'admin/settings.html', {
        'title': 'Настройки',
        'settings_obj': settings_obj,
        'total_users': total_users,
        'total_appointments': total_appointments,
        'total_services': total_services,
        'total_masters': total_masters,
    })