import json
import logging
import secrets
from datetime import timedelta

from django.conf import settings
from django.contrib.auth import authenticate, get_user_model, logout, update_session_auth_hash
from django.contrib.auth import login as auth_login
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.core.mail import send_mail
from django.http import JsonResponse
from django.utils import timezone
from django.utils.crypto import constant_time_compare, salted_hmac
from django.views.decorators.csrf import ensure_csrf_cookie
from django.views.decorators.http import require_GET, require_POST

from .models import PasswordResetOTP, LoginOTP

User = get_user_model()
logger = logging.getLogger(__name__)

CODE_TTL = timedelta(minutes=10)
RESEND_COOLDOWN = 30  # seconds between code requests (matches the frontend countdown)
MAX_ATTEMPTS = 5
REMEMBER_ME_SECONDS = 60 * 60 * 24 * 30  # 30 days
PENDING_KEY = "pending_2fa_user_id"
PENDING_REMEMBER_KEY = "pending_2fa_remember"
PENDING_BACKEND_KEY = "pending_2fa_backend"

def _mask_email(email: str) -> str:
    name, _, domain = email.partition("@")
    return f"{name[:2]}{'*' * max(len(name) - 2, 1)}@{domain}"

def _clear_pending(request):
    request.session.pop(PENDING_KEY, None)
    request.session.pop(PENDING_REMEMBER_KEY, None)
    request.session.pop(PENDING_BACKEND_KEY, None)

def _issue_login_otp(user, enforce_cooldown=True):
    """Creates and emails a code. Returns None on success, or a JsonResponse error."""
    if enforce_cooldown:
        existing = LoginOTP.objects.filter(user=user).first()
        if existing:
            elapsed = (timezone.now() - existing.created_at).total_seconds()
            if elapsed < RESEND_COOLDOWN:
                wait = int(RESEND_COOLDOWN - elapsed) + 1
                return _detail(f"Please wait {wait} seconds before requesting a new code.", 429)

    code = f"{secrets.randbelow(10**6):06d}"
    now = timezone.now()
    LoginOTP.objects.update_or_create(
        user=user,
        defaults={"otp_hash": _hash(code), "attempts": 0,
                  "created_at": now, "expires_at": now + CODE_TTL},
    )
    try:
        send_mail(
            subject="Your Ashirwad Industries login code",
            message=(f"Hello {user.firstname or user.get_username()},\n\n"
                     f"Your login verification code is {code}.\n"
                     f"It expires in 10 minutes.\n\n"
                     f"If you didn't try to sign in, please change your password."),
            from_email=getattr(settings, "DEFAULT_FROM_EMAIL", None),
            recipient_list=[user.email],
        )
    except OSError:
        LoginOTP.objects.filter(user=user).delete()
        return _detail("We couldn't send the email right now. Please try again in a moment.", 502)
    return None
# ---------- helpers ----------
def _body(request):
    try:
        data = json.loads(request.body or b"{}")
        return data if isinstance(data, dict) else {}
    except json.JSONDecodeError:
        return {}

def _s(data, key):
    return str(data.get(key) or "").strip()

def _hash(value: str) -> str:
    return salted_hmac("login_auth.reset", value).hexdigest()

def _errors(errors: dict, status=400):
    return JsonResponse({k: [v] for k, v in errors.items()}, status=status)

def _detail(message: str, status=400):
    return JsonResponse({"detail": message}, status=status)

def _find_user_by_email(email: str):
    return User.objects.filter(email__iexact=email, is_active=True).first()


# ---------- endpoints ----------
@require_GET
@ensure_csrf_cookie
def csrf(request):
    """The frontend calls this once so Django sets the csrftoken cookie."""
    return JsonResponse({"ok": True})


@require_POST
def login(request):
    d = _body(request)
    identifier, password = _s(d, "identifier"), d.get("password") or ""
    if not identifier or not password:
        return _detail("Enter your email / user ID and password.")

    user_obj = (User.objects.filter(username__iexact=identifier).first()
                or User.objects.filter(email__iexact=identifier).first())
    user = authenticate(request, username=user_obj.get_username(), password=password) if user_obj else None
    if user is None:
        return _detail("Invalid credentials.", 401)

    # Password is correct, but do NOT log in yet. Send the code first.
    error = _issue_login_otp(user, enforce_cooldown=False)
    if error:
        return error

    request.session[PENDING_KEY] = user.pk
    request.session[PENDING_REMEMBER_KEY] = bool(d.get("remember_me"))
    request.session[PENDING_BACKEND_KEY] = user.backend   # set by authenticate()
    request.session.set_expiry(CODE_TTL)   # pending state dies with the code

    return JsonResponse({
        "detail": "Verification code sent to your email.",
        "otp_required": True,
        "email": _mask_email(user.email),
    })

@require_POST
def forgot_password(request):
    """Also used by the "Resend code" button on the Verify Code page."""
    email = _s(_body(request), "email").lower()
    if not email:
        return _errors({"email": "Email is required."})
 
    user = _find_user_by_email(email)
    if not user:
        return _errors({"email": "No account found with this email."}, status=404)
 
    # Server-side cooldown so the code can't be spammed (matches the 30 s timer on the page)
    existing = PasswordResetOTP.objects.filter(user=user).first()
    if existing:
        elapsed = (timezone.now() - existing.created_at).total_seconds()
        if elapsed < RESEND_COOLDOWN:
            wait = int(RESEND_COOLDOWN - elapsed) + 1
            return _detail(f"Please wait {wait} seconds before requesting a new code.", 429)
 
    code = f"{secrets.randbelow(10**6):06d}"
    PasswordResetOTP.objects.update_or_create(
        user=user,
        defaults={"otp_hash": _hash(code), "reset_token_hash": "", "attempts": 0,
                  "created_at": timezone.now(), "expires_at": timezone.now() + CODE_TTL},
    )
    try:
        send_mail(
            subject="Your Ashirwad Industries verification code",
            message=(f"Hello {user.firstname or user.get_username()},\n\n"
                     f"Your verification code is {code}.\n"
                     f"It expires in 10 minutes.\n\n"
                     f"If you didn't request this, you can ignore this email."),
            from_email=getattr(settings, "DEFAULT_FROM_EMAIL", None),
            recipient_list=[user.email],
        )
    except OSError:  # SMTP / network problems
        PasswordResetOTP.objects.filter(user=user).delete()  # so the user can retry immediately
        return _detail("We couldn't send the email right now. Please try again in a moment.", 502)
 
    return JsonResponse({"detail": "A verification code has been sent to your email."})
 
 
@require_POST
def verify_otp(request):
    d = _body(request)
    email, code = _s(d, "email").lower(), _s(d, "code")
 
    user = _find_user_by_email(email)
    rc = PasswordResetOTP.objects.filter(user=user).first() if user else None
 
    if not rc or not rc.otp_hash:
        return _errors({"code": "No active code. Please request a new one."})
    if rc.expires_at < timezone.now():
        return _errors({"code": "This code has expired. Please request a new one."})
    if rc.attempts >= MAX_ATTEMPTS:
        return _errors({"code": "Too many wrong attempts. Please request a new code."})
 
    if not constant_time_compare(rc.otp_hash, _hash(code)):
        rc.attempts += 1
        rc.save(update_fields=["attempts"])
        left = MAX_ATTEMPTS - rc.attempts
        return _errors({"code": f"Incorrect code. {left} attempt(s) left."})
 
    token = secrets.token_urlsafe(32)
    rc.reset_token_hash = _hash(token)
    rc.otp_hash = ""          # code can't be reused
    rc.expires_at = timezone.now() + CODE_TTL
    rc.save(update_fields=["reset_token_hash", "otp_hash", "expires_at"])
    return JsonResponse({"reset_token": token})
 
 
@require_POST
def set_new_password(request):
    d = _body(request)
    email, token, new_password = _s(d, "email").lower(), _s(d, "reset_token"), d.get("new_password") or ""
 
    user = _find_user_by_email(email)
    rc = PasswordResetOTP.objects.filter(user=user).first() if user else None
    if (not rc or not rc.reset_token_hash or rc.expires_at < timezone.now()
            or not constant_time_compare(rc.reset_token_hash, _hash(token))):
        return _detail("Your reset session has expired. Please start again.")
 
    try:
        validate_password(new_password, user=user)
    except ValidationError as e:
        return _errors({"new_password": " ".join(e.messages)})
 
    user.set_password(new_password)
    user.save(update_fields=["password"])
    rc.delete()
    return JsonResponse({"detail": "Password updated."})
 
 
@require_GET
def me(request):
    if not request.user.is_authenticated:
        return JsonResponse(
            {"authenticated": False},
            status=401
        )

    user = request.user

    return JsonResponse({
        "authenticated": True,
        "id": user.id,
        "username": user.username,
        "firstname": user.firstname,
        "lastname": user.lastname,
        "email": user.email,
        "mobile_no": user.mobile_no,
        "role": user.role,
        "date_joined":user.date_joined,
        "is_superuser": user.is_superuser,
        "last_login" : user.login_time,
    })

@require_POST
def change_password(request):
    if not request.user.is_authenticated:
        return _detail("Authentication required.", 401)

    d = _body(request)
    current = d.get("current_password") or ""
    new_password = d.get("new_password") or ""
    confirm = d.get("confirm_password") or ""

    if not request.user.check_password(current):
        return _errors({"current_password": "Current password is incorrect."})
    if new_password != confirm:
        return _errors({"confirm_password": "Passwords do not match."})
    if new_password == current:
        return _errors({"new_password": "New password must be different from the current one."})

    try:
        validate_password(new_password, user=request.user)
    except ValidationError as e:
        return _errors({"new_password": " ".join(e.messages)})

    request.user.set_password(new_password)
    request.user.save(update_fields=["password"])
    update_session_auth_hash(request, request.user)   # keeps the user logged in
    return JsonResponse({"detail": "Password updated."})

@require_POST
def verify_login_otp(request):
    user_id = request.session.get(PENDING_KEY)
    user = User.objects.filter(pk=user_id, is_active=True).first() if user_id else None
    if not user:
        _clear_pending(request)
        return _detail("Your login session has expired. Please sign in again.", 401)

    code = _s(_body(request), "code")
    rc = LoginOTP.objects.filter(user=user).first()

    if not rc or not rc.otp_hash:
        _clear_pending(request)
        return _detail("No active code. Please sign in again.", 401)
    if rc.expires_at < timezone.now():
        return _errors({"code": "This code has expired. Please request a new one."})
    if rc.attempts >= MAX_ATTEMPTS:
        rc.delete()
        _clear_pending(request)
        return _detail("Too many wrong attempts. Please sign in again.", 401)

    if not constant_time_compare(rc.otp_hash, _hash(code)):
        rc.attempts += 1
        rc.save(update_fields=["attempts"])
        left = MAX_ATTEMPTS - rc.attempts
        return _errors({"code": f"Incorrect code. {left} attempt(s) left."})

        # Success: finish the login
    remember = request.session.get(PENDING_REMEMBER_KEY, False)
    backend = request.session.get(PENDING_BACKEND_KEY)
    _clear_pending(request)
    rc.delete()

    auth_login(request, user, backend=backend)
    request.session.set_expiry(REMEMBER_ME_SECONDS if remember else 0)
    return JsonResponse({"detail": "Logged in.", "username": user.get_username()})

@require_POST
def resend_login_otp(request):
    user_id = request.session.get(PENDING_KEY)
    user = User.objects.filter(pk=user_id, is_active=True).first() if user_id else None
    if not user:
        _clear_pending(request)
        return _detail("Your login session has expired. Please sign in again.", 401)

    error = _issue_login_otp(user, enforce_cooldown=True)
    if error:
        return error
    request.session.set_expiry(CODE_TTL)
    return JsonResponse({"detail": "A new verification code has been sent."})

@require_POST
def logout_view(request):
    logout(request)
    return JsonResponse({"detail": "Logged out."})