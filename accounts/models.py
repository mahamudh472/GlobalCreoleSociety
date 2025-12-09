from django.db import models
from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin, BaseUserManager
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
import uuid

class UserManager(BaseUserManager):
    """
    Custom manager where email is the unique identifiers
    for authentication instead of usernames.
    """

    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError("The Email field must be set")
        email = self.normalize_email(email)
        extra_fields.setdefault("is_active", True)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password, **extra_fields):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        extra_fields.setdefault("is_active", True)

        if extra_fields.get("is_staff") is not True:
            raise ValueError("Superuser must have is_staff=True.")
        if extra_fields.get("is_superuser") is not True:
            raise ValueError("Superuser must have is_superuser=True.")

        return self.create_user(email, password, **extra_fields)


class User(AbstractBaseUser, PermissionsMixin):
    """
    Custom User model that uses email for authentication.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    email = models.EmailField(_("email address"), unique=True)
    profile_name = models.CharField(_("profile name"), max_length=150, unique=True)

    description = models.TextField(_("description"), blank=True)
    profile_image = models.ImageField(_("profile image"), upload_to="profile_images/", blank=True, null=True)
    cover_photo = models.ImageField(_("cover photo"), upload_to="cover_photos/", blank=True, null=True)
    website = models.TextField(_("website"), blank=True)
    phone_number = models.CharField(_("phone number"), max_length=20, blank=True)
    gender = models.CharField(_("gender"), max_length=20, blank=True)
    date_of_birth = models.DateField(_("date of birth"), blank=True, null=True)
    share_data = models.BooleanField(_("share data"), default=False)


    is_staff = models.BooleanField(
        _("staff status"),
        default=False,
        help_text=_("Designates whether the user can log into this admin site."),
    )
    is_active = models.BooleanField(
        _("active"),
        default=True,
        help_text=_("Designates whether this user should be treated as active."),
    )
    date_joined = models.DateTimeField(_("date joined"), default=timezone.now)

    profile_lock = models.BooleanField(_("profile lock"), default=False)

    objects = UserManager()

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["profile_name"]

    class Meta:
        verbose_name = _("user")
        verbose_name_plural = _("users")


    def __str__(self):
        return self.email
    
class Location(models.Model):
    name = models.CharField(max_length=255, blank=True, null=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='locations')

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name or "Unnamed Location"

class Work(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='works')
    company = models.CharField(max_length=255, blank=True, null=True)
    position = models.CharField(max_length=255, blank=True, null=True)
    description = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.title or "Untitled Work"

class Education(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='educations')
    collage = models.CharField(max_length=255, blank=True, null=True)
    subject = models.CharField(max_length=255, blank=True, null=True)
    description = models.TextField(blank=True, null=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.collage or "Unnamed Education"

class Friendship(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('accepted', 'Accepted'),
        ('blocked', 'Blocked'),
    ]

    requester = models.ForeignKey(
        User,
        related_name="friend_requests_sent",
        on_delete=models.CASCADE
    )
    receiver = models.ForeignKey(
        User,
        related_name="friend_requests_received",
        on_delete=models.CASCADE
    )
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='pending'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('requester', 'receiver')

    def __str__(self):
        return f"{self.requester} → {self.receiver} ({self.status})"

class OTP(models.Model):
    OTP_TYPES = [
        ('password_reset', 'Password Reset'),
        ('email_verification', 'Email Verification'),
        ('number_verification', 'Number Verification'),
    ]
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='otps')
    code = models.CharField(max_length=6)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()

    def is_expired(self):
        return timezone.now() > self.expires_at

    def __str__(self):
        return f"OTP for {self.user.email} - {self.code}"

    def create_otp(cls, user, code, validity_minutes=10):
        from django.utils import timezone
        expires_at = timezone.now() + timezone.timedelta(minutes=validity_minutes)
        otp_instance = cls.objects.create(user=user, code=code, expires_at=expires_at)
        return otp_instance

class ExtraEmail(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='extra_emails')
    email = models.EmailField(unique=True)
    is_verified = models.BooleanField(default=False)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.email

class ExtraPhoneNumber(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='extra_phone_numbers')
    phone_number = models.CharField(max_length=20, unique=True)
    is_verified = models.BooleanField(default=False)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.phone_number