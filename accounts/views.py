from django.contrib import messages
from django.shortcuts import render, redirect, get_object_or_404

from beauty_salon.models import User, Role
from .forms import RegisterForm, LoginForm, ProfileForm


def register_view(request):
    if request.session.get('user_id'):
        return redirect('beauty_salon:index')

    if request.method == 'POST':
        form = RegisterForm(request.POST)
        if form.is_valid():
            full_name = form.cleaned_data['full_name']
            email = form.cleaned_data['email']
            phone = form.cleaned_data['phone']
            password = form.cleaned_data['password1']

            if User.objects.filter(email=email).exists():
                form.add_error('email', 'Пользователь с таким email уже существует')
            elif User.objects.filter(phone=phone).exists():
                form.add_error('phone', 'Пользователь с таким телефоном уже существует')
            else:
                client_role = get_object_or_404(Role, name='client')
                user = User(
                    full_name=full_name,
                    email=email,
                    phone=phone,
                    role=client_role,
                )
                user.set_password(password)
                user.save()

                request.session['user_id'] = user.id
                request.session['user_name'] = user.full_name
                request.session['user_role'] = user.role.name

                messages.success(request, 'Регистрация прошла успешно')
                return redirect('beauty_salon:index')
    else:
        form = RegisterForm()

    return render(request, 'accounts/register.html', {'form': form})


def login_view(request):
    if request.session.get('user_id'):
        return redirect('beauty_salon:index')

    if request.method == 'POST':
        form = LoginForm(request.POST)
        if form.is_valid():
            email = form.cleaned_data['email']
            password = form.cleaned_data['password']

            user = User.objects.filter(email=email).select_related('role').first()
            if user and user.check_password(password):
                request.session['user_id'] = user.id
                request.session['user_name'] = user.full_name
                request.session['user_role'] = user.role.name

                messages.success(request, 'Вы успешно вошли в аккаунт')
                return redirect('beauty_salon:index')

            messages.error(request, 'Неверный email или пароль')
    else:
        form = LoginForm()

    return render(request, 'accounts/login.html', {'form': form})


def logout_view(request):
    request.session.flush()
    messages.success(request, 'Вы вышли из аккаунта')
    return redirect('beauty_salon:index')


def profile_view(request):
    user_id = request.session.get('user_id')
    if not user_id:
        messages.error(request, 'Нужно войти в аккаунт')
        return redirect('accounts:login')

    user = get_object_or_404(User, pk=user_id)

    if request.method == 'POST':
        form = ProfileForm(request.POST)
        if form.is_valid():
            full_name = form.cleaned_data['full_name']
            email = form.cleaned_data['email']
            phone = form.cleaned_data['phone']

            email_exists = User.objects.exclude(pk=user.pk).filter(email=email).exists()
            phone_exists = User.objects.exclude(pk=user.pk).filter(phone=phone).exists()

            if email_exists:
                form.add_error('email', 'Этот email уже занят')
            elif phone_exists:
                form.add_error('phone', 'Этот телефон уже занят')
            else:
                user.full_name = full_name
                user.email = email
                user.phone = phone
                user.save()

                request.session['user_name'] = user.full_name

                messages.success(request, 'Профиль успешно обновлён')
                return redirect('accounts:profile')
    else:
        form = ProfileForm(initial={
            'full_name': user.full_name,
            'email': user.email,
            'phone': user.phone,
        })

    return render(request, 'accounts/profile.html', {
        'form': form,
        'user_obj': user,
    })