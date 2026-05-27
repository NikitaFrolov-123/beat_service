from django.db import models
from django.contrib.auth.hashers import make_password, check_password


class Role(models.Model):
    name = models.CharField(max_length=100, unique=True)

    class Meta:
        db_table = 'role'
        verbose_name = 'Роль'
        verbose_name_plural = 'Роли'

    def __str__(self):
        return self.name


class User(models.Model):
    email = models.EmailField(unique=True)
    phone = models.CharField(max_length=20, unique=True)
    full_name = models.CharField(max_length=200)
    password_hash = models.CharField(max_length=255)
    role = models.ForeignKey(Role, on_delete=models.PROTECT, related_name='users')
    created_at = models.DateTimeField(auto_now_add=True)
    photo = models.ImageField(upload_to='masters/', blank=True, null=True, verbose_name='Фото мастера')

    class Meta:
        db_table = 'users'
        verbose_name = 'Пользователь'
        verbose_name_plural = 'Пользователи'

    def __str__(self):
        return self.email

    def set_password(self, raw_password):
        self.password_hash = make_password(raw_password)

    def check_password(self, raw_password):
        return check_password(raw_password, self.password_hash)


class RoleUser(models.Model):
    role = models.ForeignKey(Role, on_delete=models.CASCADE, db_column='Roleid')
    user = models.ForeignKey(User, on_delete=models.CASCADE, db_column='Usersuser_id')

    class Meta:
        db_table = 'role_users'
        unique_together = ('role', 'user')
        verbose_name = 'Роль пользователя'
        verbose_name_plural = 'Роли пользователей'

    def __str__(self):
        return f'{self.user} - {self.role}'


class ServiceCategory(models.Model):
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True, null=True)

    class Meta:
        db_table = 'service_categories'
        verbose_name = 'Категория услуги'
        verbose_name_plural = 'Категории услуг'

    def __str__(self):
        return self.name


class Service(models.Model):
    name = models.CharField(max_length=200)
    category = models.ForeignKey(
        ServiceCategory,
        on_delete=models.PROTECT,
        related_name='services',
        db_column='category_id'
    )
    duration_minutes = models.PositiveIntegerField()
    price = models.DecimalField(max_digits=10, decimal_places=2)
    description = models.TextField(blank=True, null=True)
    is_active = models.BooleanField(default=True)
    image = models.ImageField(
        upload_to='services/',
        blank=True,
        null=True,
        verbose_name='Фото услуги'
    )
    masters = models.ManyToManyField(
        User,
        related_name='services',
        blank=True,
        limit_choices_to={'role__name': 'master'}
    )

    class Meta:
        db_table = 'services'
        verbose_name = 'Услуга'
        verbose_name_plural = 'Услуги'

    def __str__(self):
        return self.name


class Appointment(models.Model):
    appointment_id = models.AutoField(primary_key=True)
    client = models.ForeignKey(User, on_delete=models.PROTECT, related_name='client_appointments', db_column='client_id')
    master = models.ForeignKey(User, on_delete=models.PROTECT, related_name='master_appointments', db_column='master_id')
    start_datetime = models.DateTimeField()
    end_datetime = models.DateTimeField()
    status = models.CharField(max_length=20)
    notes = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    services = models.ManyToManyField(Service, through='AppointmentService', related_name='appointments')

    class Meta:
        db_table = 'appointments'
        verbose_name = 'Запись'
        verbose_name_plural = 'Записи'

    def __str__(self):
        return f'{self.client} - {self.start_datetime}'


class AppointmentService(models.Model):
    appointment = models.ForeignKey(Appointment, on_delete=models.CASCADE, db_column='Appointments_appointment_id')
    service = models.ForeignKey(Service, on_delete=models.CASCADE, db_column='Services_id')

    class Meta:
        db_table = 'appointments_services'
        unique_together = ('appointment', 'service')
        verbose_name = 'Услуга в записи'
        verbose_name_plural = 'Услуги в записях'

    def __str__(self):
        return f'{self.appointment} - {self.service}'


class Payment(models.Model):
    payment_id = models.AutoField(primary_key=True)
    appointment = models.ForeignKey(Appointment, on_delete=models.CASCADE, related_name='payments', db_column='appointment_id')
    payment_method = models.CharField(max_length=20)
    payment_date = models.DateTimeField()
    is_paid = models.BooleanField(default=False)
    amount = models.DecimalField(max_digits=10, decimal_places=2)

    class Meta:
        db_table = 'payments'
        verbose_name = 'Платёж'
        verbose_name_plural = 'Платежи'

    def __str__(self):
        return f'{self.payment_id} - {self.amount}'


class Review(models.Model):
    review_id = models.AutoField(primary_key=True)
    rating = models.PositiveSmallIntegerField()
    comment = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    appointment = models.ForeignKey(Appointment, on_delete=models.CASCADE, related_name='reviews', db_column='appointment_id')
    client = models.ForeignKey(User, on_delete=models.CASCADE, related_name='reviews', db_column='client_id')

    class Meta:
        db_table = 'reviews'
        verbose_name = 'Отзыв'
        verbose_name_plural = 'Отзывы'

    def __str__(self):
        return f'{self.review_id} - {self.rating}'


class Product(models.Model):
    product_id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=200)
    category = models.CharField(max_length=100)
    purchase_price = models.DecimalField(max_digits=10, decimal_places=2)
    retail_price = models.DecimalField(max_digits=10, decimal_places=2)
    quantity = models.PositiveIntegerField()
    min_quantity = models.PositiveIntegerField()
    unit = models.CharField(max_length=20)

    class Meta:
        db_table = 'products'
        verbose_name = 'Товар'
        verbose_name_plural = 'Товары'

    def __str__(self):
        return self.name


class ProductUsage(models.Model):
    usage_id = models.AutoField(primary_key=True)
    appointment = models.ForeignKey(Appointment, on_delete=models.CASCADE, related_name='product_usages', db_column='appointment_id')
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='usages', db_column='product_id')
    quantity_used = models.DecimalField(max_digits=10, decimal_places=3)
    usage_date = models.DateField()

    class Meta:
        db_table = 'product_usage'
        verbose_name = 'Использование товара'
        verbose_name_plural = 'Использование товаров'

    def __str__(self):
        return f'{self.product} - {self.quantity_used}'


class Notification(models.Model):
    recipient = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='notifications'
    )
    text = models.CharField(max_length=255)
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'notifications'
        verbose_name = 'Уведомление'
        verbose_name_plural = 'Уведомления'

    def __str__(self):
        return self.text