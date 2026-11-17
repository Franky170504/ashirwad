# Ashirwad Industries – Auth pages (Next.js 14 + Tailwind)

## Run
```bash
npm install
cp .env.example .env.local
# put your logo at public/logo.png
npm run dev        # http://localhost:3000
```

## Routes
| Page | Route |
|---|---|
| Login | `/login` |
| New User | `/register` |
| Forgot Password | `/forgot-password` |
| Verify Code | `/verify-code` |
| Set Password | `/set-password` |

Password fields (`components/PasswordField.tsx`) have a show/hide eye toggle.

## Django endpoints expected (all `POST`, JSON)
| URL | Body | Success response |
|---|---|---|
| `/api/auth/register/` | first_name, last_name, email, mobile, password, confirm_password | 201 |
| `/api/auth/login/` | identifier, password, remember_me | 200 (sets session cookie) |
| `/api/auth/forgot-password/` | email | 200 (sends a code) |
| `/api/auth/verify-code/` | email, code | 200 `{ "reset_token": "..." }` |
| `/api/auth/set-password/` | email, reset_token, new_password | 200 |

Errors: DRF-style `{"detail": "..."}` or `{"field": ["msg"]}` are shown under the matching field.
Next.js proxies `/api/*` to `DJANGO_API_URL` (see `next.config.js`), so there's no CORS setup and Django's
session + CSRF cookies work. If you call Django directly instead, enable `django-cors-headers` with
`CORS_ALLOW_CREDENTIALS = True` and add the Next.js origin to `CSRF_TRUSTED_ORIGINS`.

Tip: in the forgot-password view, return 200 even if the email doesn't exist (avoids account enumeration).

## Theming
Colors: `tailwind.config.ts` (`brand.light`, `brand.dark`, `brand.button`). Fonts: `app/layout.tsx`.
