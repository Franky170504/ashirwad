import json
import re
import secrets
from datetime import timedelta

from django.conf import settings
from django.contrib.auth import authenticate, get_user_model, logout
from django.contrib.auth import login as auth_login  # alias: our view below is also called "login"
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.core.mail import send_mail
from django.db import IntegrityError, transaction
from django.http import JsonResponse
from django.utils import timezone
from django.utils.crypto import constant_time_compare, salted_hmac
from django.views.decorators.csrf import ensure_csrf_cookie
from django.views.decorators.http import require_GET, require_POST

from .models import PasswordResetCode, Profile

User = get_user_model()

CODE_TTL = timedelta(minutes=10)
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
    first, last = _s(d, "first_name"), _s(d, "last_name")
    email, mobile = _s(d, "email").lower(), _s(d, "mobile")
    password, confirm = d.get("password") or "", d.get("confirm_password") or ""

    errs = {}
    if not first:
        errs["first_name"] = "First name is required."
    if not last:
        errs["last_name"] = "Last name is required."
    if not re.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", email):
        errs["email"] = "Enter a valid email address."
    elif User.objects.filter(email__iexact=email).exists():
        errs["email"] = "An account with this email already exists."
    if not MOBILE_RE.match(mobile.replace(" ", "").replace("-", "")):
        errs["mobile"] = "Enter a valid mobile number."
    if password != confirm:
        errs["confirm_password"] = "Passwords do not match."
    if "password" not in errs and password:
        try:
            validate_password(password, user=User(username=first + last[:1], email=email, first_name=first, last_name=last))
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
                user = User.objects.create_user(username=username, email=email, password=password,
                                                first_name=first, last_name=last)
                Profile.objects.create(user=user, mobile=mobile)
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
    email = _s(_body(request), "email").lower()
    if not email:
        return _errors({"email": "Email is required."})

    user = _find_user_by_email(email)
    if user:
        code = f"{secrets.randbelow(10**6):06d}"
        PasswordResetCode.objects.update_or_create(
            user=user,
            defaults={"code_hash": _hash(code), "token_hash": "", "attempts": 0,
                      "created_at": timezone.now(), "expires_at": timezone.now() + CODE_TTL},
        )
        send_mail(
            subject="Your Ashirwad Industries verification code",
            message=f"Your verification code is {code}. It expires in 10 minutes.\n"
                    f"If you didn't request this, you can ignore this email.",
            from_email=getattr(settings, "DEFAULT_FROM_EMAIL", None),
            recipient_list=[user.email],
            fail_silently=False,
        )
    # Same response whether or not the account exists (prevents email enumeration)
    return JsonResponse({"detail": "If the email is registered, a code has been sent."})


@require_POST
def verify_code(request):
    d = _body(request)
    email, code = _s(d, "email").lower(), _s(d, "code")
    invalid = "Invalid or expired code."

    user = _find_user_by_email(email)
    rc = PasswordResetCode.objects.filter(user=user).first() if user else None
    if not rc or rc.expires_at < timezone.now() or rc.attempts >= MAX_ATTEMPTS:
        return _errors({"code": invalid})

    if not constant_time_compare(rc.code_hash, _hash(code)):
        rc.attempts += 1
        rc.save(update_fields=["attempts"])
        return _errors({"code": invalid})

    token = secrets.token_urlsafe(32)
    rc.token_hash = _hash(token)
    rc.code_hash = ""          # code can't be reused
    rc.expires_at = timezone.now() + CODE_TTL
    rc.save(update_fields=["token_hash", "code_hash", "expires_at"])
    return JsonResponse({"reset_token": token})


@require_POST
def set_password(request):
    d = _body(request)
    email, token, new_password = _s(d, "email").lower(), _s(d, "reset_token"), d.get("new_password") or ""

    user = _find_user_by_email(email)
    rc = PasswordResetCode.objects.filter(user=user).first() if user else None
    if (not rc or not rc.token_hash or rc.expires_at < timezone.now()
            or not constant_time_compare(rc.token_hash, _hash(token))):
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
        return _detail("Not authenticated.", 401)
    u = request.user
    profile = Profile.objects.filter(user=u).first()  # superusers may not have one
    return JsonResponse({
        "name": u.get_full_name() or u.get_username(),
        "username": u.get_username(),
        "email": u.email,
        "mobile": profile.mobile if profile else "",
        "date_joined": u.date_joined.isoformat(),
        "last_login": u.last_login.isoformat() if u.last_login else None,
        "role": "Administrator" if u.is_superuser else ("Staff" if u.is_staff else "User"),
    })


@require_POST
def logout_view(request):
    logout(request)
    return JsonResponse({"detail": "Logged out."})