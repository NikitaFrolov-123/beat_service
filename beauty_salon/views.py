from datetime import datetime, timedelta, time
from functools import wraps

from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Q, Count, Avg
from django.http import HttpResponseForbidden
from django.shortcuts import render, get_object_or_404, redirect
from django.utils import timezone
from django.views.decorators.http import require_http_methods

from .models import Notification
from .models import (
    Role, User, ServiceCategory, Service, Appointment, AppointmentService,
)

WORK_START = 9
WORK_END = 20
SLOT_STEP = 15


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
    masters = User.objects.filter(role__name='master')[:6]

    return render(request, 'index.html', {
        'stats': stats,
        'recent': recent,
        'services': services,
        'masters': masters,
    })


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


def services_list(request):
    categories = ServiceCategory.objects.all().order_by('name')
    category_id = request.GET.get('category')

    services = Service.objects.select_related('category').prefetch_related('masters').filter(is_active=True)
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
        id=service_id,
        is_active=True
    )
    masters = service.masters.all()

    return render(request, 'services/detail.html', {
        'service': service,
        'masters': masters,
    })


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


def service_delete(request, service_id):
    service = get_object_or_404(Service, id=service_id)
    if request.method == 'POST':
        service.delete()
        messages.success(request, 'Услуга удалена')
        return redirect('beauty_salon:services_list')
    return render(request, 'services/delete.html', {'service': service})


def appointments_list(request):
    status = request.GET.get('status')
    date_from = request.GET.get('date_from')
    masters = User.objects.filter(role__name='master').order_by('full_name')

    qs = Appointment.objects.select_related('client', 'master').prefetch_related('services').order_by('-start_datetime')

    if status:
        qs = qs.filter(status=status)
    if date_from:
        qs = qs.filter(start_datetime__date__gte=date_from)

    paginator = Paginator(qs, 25)
    page = request.GET.get('page')

    return render(request, 'appointments/list.html', {
        'appointments': paginator.get_page(page),
        'masters': masters,
        'status_filter': status,
        'date_from': date_from,
    })


def get_free_slots(master, service_duration, selected_date):
    day_start = datetime.combine(selected_date, time(hour=WORK_START, minute=0))
    day_end = datetime.combine(selected_date, time(hour=WORK_END, minute=0))

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
        .prefetch_related('services')
        .order_by('-start_datetime')
    )

    now = timezone.now()
    for appointment in appointments:
        appointment.can_cancel = appointment.status != 'cancelled' and appointment.start_datetime > now

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

    free_slots = []
    service_obj = None
    master_obj = None

    masters_qs = (
        User.objects.filter(role__name='master')
        .prefetch_related('services')
        .order_by('full_name')
    )
    services_qs = (
        Service.objects.select_related('category')
        .prefetch_related('masters')
        .filter(is_active=True)
        .order_by('name')
    )

    if selected_service:
        service_obj = get_object_or_404(Service, id=selected_service, is_active=True)
        masters_qs = masters_qs.filter(services__id=selected_service).distinct()

    if selected_master:
        master_obj = get_object_or_404(User, id=selected_master, role__name='master')
        services_qs = services_qs.filter(masters=master_obj)

    if selected_date and service_obj and master_obj:
        try:
            parsed_date = datetime.strptime(selected_date, '%Y-%m-%d').date()
            free_slots = get_free_slots(master_obj, service_obj.duration_minutes, parsed_date)
        except ValueError:
            free_slots = []

    if request.method == 'POST':
        try:
            service_id = request.POST.get('service_id')
            master_id = request.POST.get('master_id')
            selected_date = request.POST.get('date')
            selected_time = request.POST.get('slot_time')
            notes = request.POST.get('notes', '')

            if not all([service_id, master_id, selected_date, selected_time]):
                messages.error(request, 'Заполните все поля и выберите свободное время')
                return redirect(f"{request.path}?service={service_id or ''}&master={master_id or ''}&date={selected_date or ''}")

            service = get_object_or_404(Service, id=service_id, is_active=True)
            master = get_object_or_404(User, id=master_id, role__name='master')

            if not service.masters.filter(id=master.id).exists():
                messages.error(request, 'Этот мастер не оказывает выбранную услугу')
                return redirect(f"{request.path}?service={service_id}&master={master_id}&date={selected_date}")

            parsed_date = datetime.strptime(selected_date, '%Y-%m-%d').date()
            parsed_time = datetime.strptime(selected_time, '%H:%M').time()
            start_dt = datetime.combine(parsed_date, parsed_time)
            end_dt = start_dt + timedelta(minutes=service.duration_minutes)

            work_start_dt = datetime.combine(parsed_date, time(hour=WORK_START, minute=0))
            work_end_dt = datetime.combine(parsed_date, time(hour=WORK_END, minute=0))

            if start_dt < work_start_dt or end_dt > work_end_dt:
                messages.error(request, 'Время вне рабочего графика')
                return redirect(f"{request.path}?service={service_id}&master={master_id}&date={selected_date}")

            conflict = Appointment.objects.filter(
                master=master,
                start_datetime__lt=end_dt,
                end_datetime__gt=start_dt
            ).exists()

            if conflict:
                messages.error(request, 'Это время уже занято')
                return redirect(f"{request.path}?service={service_id}&master={master_id}&date={selected_date}")

            if selected_time not in get_free_slots(master, service.duration_minutes, parsed_date):
                messages.error(request, 'Выбранное время уже недоступно')
                return redirect(f"{request.path}?service={service_id}&master={master_id}&date={selected_date}")

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
        'free_slots': free_slots,
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

    if appointment.status == 'cancelled':
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
        appointments_count=Count('master_appointments'),
        avg_rating=Avg('master_appointments__reviews__rating')
    ).prefetch_related('services').order_by('full_name')

    return render(request, 'masters/list.html', {'masters': masters})


def master_detail(request, user_id):
    master = get_object_or_404(
        User.objects.prefetch_related('services'),
        id=user_id,
        role__name='master'
    )
    services = master.services.filter(is_active=True).select_related('category')

    return render(request, 'masters/detail.html', {
        'master': master,
        'services': services,
    })


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


@master_required
def master_schedule(request):
    master = get_object_or_404(User, pk=request.session.get('user_id'), role__name='master')

    appointments = (
        Appointment.objects
        .filter(master=master, start_datetime__date__gte=timezone.localdate())
        .select_related('client', 'master')
        .prefetch_related('services')
        .order_by('start_datetime')
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

    if appointment.status == 'cancelled':
        messages.error(request, 'Нельзя завершить отменённую запись')
        return redirect('beauty_salon:master_schedule')

    if appointment.status == 'completed':
        messages.info(request, 'Запись уже завершена')
        return redirect('beauty_salon:master_schedule')

    appointment.status = 'completed'
    appointment.notes = request.POST.get('notes', appointment.notes or '')
    appointment.save()

    messages.success(request, 'Услуга отмечена как выполненная')
    return redirect('beauty_salon:master_schedule')


@master_required
@require_http_methods(["POST"])
def appointment_cancel_by_master(request, pk):
    master = get_object_or_404(User, pk=request.session.get('user_id'), role__name='master')
    appointment = get_object_or_404(Appointment, pk=pk, master=master)

    if appointment.status == 'cancelled':
        messages.info(request, 'Запись уже отменена')
        return redirect('beauty_salon:master_schedule')

    reason = request.POST.get('reason', '').strip()

    appointment.status = 'cancelled'
    if reason:
        appointment.notes = (appointment.notes or '') + f'\n[Отмена мастером] {reason}'
    appointment.save()

    Notification.objects.create(
        recipient=appointment.client,
        text=f'Ваша запись на {appointment.start_datetime:%d.%m.%Y %H:%M} отменена мастером. Причина: {reason or "не указана"}.'
    )

    messages.success(request, 'Запись отменена')
    return redirect('beauty_salon:master_schedule')