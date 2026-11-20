
import json
import logging
import re
import secrets
from datetime import timedelta

from django.conf import settings

from django.contrib.auth import authenticate, get_user_model, logout
from django.contrib.auth import login as auth_login 
from django.contrib.auth.password_validation import validate_password
from django.contrib.auth.hashers import make_password, check_password

from django.core.exceptions import ValidationError
from django.core.mail import send_mail

from django.db import IntegrityError, transaction

from django.http import JsonResponse

from django.utils import timezone
from django.utils.crypto import constant_time_compare, salted_hmac

from django.views.decorators.csrf import ensure_csrf_cookie
from django.views.decorators.http import require_GET, require_POST

from .models import PasswordResetOTP, CustomUser

User = get_user_model()
logger = logging.getLogger(__name__)

CODE_TTL = timedelta(minutes=10)
RESEND_COOLDOWN = 30  # seconds before another code can be requested
RESEND_COOLDOWN = 30  # seconds between code requests (the frontend shows the same 30s countdown)
MAX_ATTEMPTS = 5
REMEMBER_ME_SECONDS = 60 * 60 * 24 * 30  # 30 days
MOBILE_RE = re.compile(r"^\+?\d{7,15}$")

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
    """Field errors in DRF style: {"field": ["message"]} — the frontend shows them under the field."""
    return JsonResponse({k: [v] for k, v in errors.items()}, status=status)

def _detail(message: str, status=400):
    return JsonResponse({"detail": message}, status=status)

def _generate_username(first: str, last: str) -> str:
    """First name + first letter of last name, e.g. Manish Suryavanshi -> ManishS.
    If taken, add a number: ManishS1, ManishS2, ..."""
    first_word = (first.split() or [""])[0]
    last_word = (last.split() or [""])[0]
    base = (re.sub(r"[^\w]", "", first_word).capitalize()
            + re.sub(r"[^\w]", "", last_word)[:1].upper()) or "User"
    base = base[:140]

    taken = {
        u.lower() for u in User.objects.filter(username__istartswith=base).values_list("username", flat=True)
    }
    if base.lower() not in taken:
        return base
    n = 1
    while f"{base}{n}".lower() in taken:
        n += 1
    return f"{base}{n}"

def _find_user_by_email(email: str):
    return User.objects.filter(email__iexact=email, is_active=True).first()

# ---------- endpoints ----------
@require_GET
@ensure_csrf_cookie
def csrf(request):
    """The frontend calls this once so Django sets the csrftoken cookie."""
    return JsonResponse({"ok": True})

@require_POST
def register(request):
    d = _body(request)
    first, last = _s(d, "firstname"), _s(d, "lastname")
    email, mobile_no = _s(d, "email").lower(), _s(d, "mobile_no")
    password, confirm = d.get("password") or "", d.get("confirm_password") or ""

    errs = {}
    if not first:
        errs["firstname"] = "First name is required."
    if not last:
        errs["lastname"] = "Last name is required."
    if not re.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", email):
        errs["email"] = "Enter a valid email address."
    elif User.objects.filter(email__iexact=email).exists():
        errs["email"] = "An account with this email already exists."
    if not mobile_no:
        return JsonResponse(
            {"error": "Mobile number is required"},
            status=400
        )
    if not MOBILE_RE.match(mobile_no.replace(" ", "").replace("-", "")):
        errs["mobile_no"] = "Enter a valid mobile number."
    if password != confirm:
        errs["confirm_password"] = "Passwords do not match."
    if "password" not in errs and password:
        try:
            validate_password(password, user=User(username=first + last[:1], email=email, firstname=first, lastname=last))
        except ValidationError as e:
            errs["password"] = " ".join(e.messages)
    elif not password:
        errs["password"] = "Password is required."
    if errs:
        return _errors(errs)

    # Retry in the rare case two people register the same name at the same moment
    for _ in range(5):
        username = _generate_username(first, last)
        try:
            with transaction.atomic():
                user = User.objects.create_user(firstname=first, lastname=last, email=email,mobile_no=mobile_no,  password=password)
            break
        except IntegrityError:
            continue
    else:
        return _detail("Could not create the account. Please try again.", 500)
    return JsonResponse({"detail": "Account created.", "username": user.get_username()}, status=201)

@require_POST
def login(request):
    d = _body(request)
    identifier, password = _s(d, "identifier"), d.get("password") or ""
    if not identifier or not password:
        return _detail("Enter your email / user ID and password.")

    # Accept either username or email
    user_obj = (User.objects.filter(username__iexact=identifier).first()
                or User.objects.filter(email__iexact=identifier).first())
    user = authenticate(request, username=user_obj.get_username(), password=password) if user_obj else None
    if user is None:
        return _detail("Invalid credentials.", 401)

    auth_login(request, user)
    # "Remember me" → persistent 30-day session; otherwise ends when the browser closes
    request.session.set_expiry(REMEMBER_ME_SECONDS if d.get("remember_me") else 0)
    return JsonResponse({"detail": "Logged in.", "username": user.get_username()})

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
def logout_view(request):
    logout(request)
    return JsonResponse({"detail": "Logged out."})