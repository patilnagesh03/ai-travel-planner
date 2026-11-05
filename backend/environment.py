"""Small, pure helpers for reading configuration from the environment.

They live outside ``settings.py`` so the "must not start in production"
rules can be unit tested without reloading Django's settings module, and so
that ``settings.py`` stays a readable list of configuration rather than a
pile of inline validation.
"""

from django.core.exceptions import ImproperlyConfigured


# Used only when DEBUG is on and the developer has not provided a key. It is
# deliberately obvious, and it is rejected whenever DEBUG is off.
DEVELOPMENT_SECRET_KEY = (
    "django-insecure-development-only-do-not-use-in-production"
)

# Django's own generator prefixes keys with this, so its presence is a
# reliable sign that a key was never meant for production.
INSECURE_SECRET_KEY_PREFIX = "django-insecure-"

# Values people leave behind in a template. None of them is a secret.
PLACEHOLDER_SECRET_KEYS = frozenset(
    {
        "your-secret-key-here",
        "your_secret_key_here",
        "changeme",
        "change-me",
        "changethis",
        "change-this",
        "secret",
        "django-secret-key",
    }
)

_SECRET_KEY_HELP = (
    "Set SECRET_KEY in the environment (or in backend/.env). Generate one "
    "with:\n"
    "    python -c \"from django.core.management.utils import "
    "get_random_secret_key; print(get_random_secret_key())\""
)


def split_csv(raw):
    """Split a comma-separated value into stripped, non-empty items."""

    if raw is None:
        return []

    return [item.strip() for item in str(raw).split(",") if item.strip()]


def resolve_secret_key(raw, debug):
    """Return a usable SECRET_KEY or explain why the project cannot start.

    In development a missing key falls back to a known development key, so
    somebody cloning the repository is never blocked by configuration. In
    production a missing, placeholder or ``django-insecure-`` key is a hard
    error: running with a known key would let anyone forge the signed values
    Django relies on (sessions, password-reset tokens, and so on).
    """

    key = (raw or "").strip()

    if not key:
        if debug:
            return DEVELOPMENT_SECRET_KEY

        raise ImproperlyConfigured(
            "SECRET_KEY is not set and DEBUG is False, so the project "
            "refuses to start. " + _SECRET_KEY_HELP
        )

    if not debug:
        if key.startswith(INSECURE_SECRET_KEY_PREFIX):
            raise ImproperlyConfigured(
                "SECRET_KEY is a development key (it starts with "
                "'django-insecure-'), which must not be used in production. "
                + _SECRET_KEY_HELP
            )

        if key.lower() in PLACEHOLDER_SECRET_KEYS:
            raise ImproperlyConfigured(
                "SECRET_KEY is still a placeholder value and must not be "
                "used in production. " + _SECRET_KEY_HELP
            )

    return key


def resolve_allowed_hosts(raw, debug):
    """Return ALLOWED_HOSTS, defaulting sensibly for local development."""

    hosts = split_csv(raw)

    if hosts:
        return hosts

    if debug:
        return ["127.0.0.1", "localhost", "[::1]"]

    raise ImproperlyConfigured(
        "ALLOWED_HOSTS is empty and DEBUG is False. Set it to the "
        "comma-separated hostnames this site is served from, for example "
        "ALLOWED_HOSTS=example.com,www.example.com"
    )


def resolve_cors_origins(raw, debug):
    """Return the explicit list of browser origins allowed to call the API.

    The frontend is a separate origin, so it has to be named. There is no
    "allow everything" switch here on purpose: a wildcard would let any
    website call the API with a visitor's credentials.
    """

    origins = split_csv(raw)

    if origins:
        return origins

    if debug:
        # Vite's defaults, so a local frontend works without extra setup.
        return [
            "http://localhost:5173",
            "http://127.0.0.1:5173",
        ]

    return []


def resolve_csrf_trusted_origins(raw, cors_origins):
    """Return the origins trusted for unsafe cross-site requests.

    The API itself is token based, but Django's admin and session flows use
    CSRF tokens. Trusting the frontend origins by default means a deployment
    that already configured CORS does not silently break those flows. An
    explicit list, when supplied, always wins.
    """

    origins = split_csv(raw)

    if origins:
        return origins

    return list(cors_origins)


def resolve_security_settings(debug):
    """Return the HTTPS and cookie defaults for the current environment.

    Production (``DEBUG`` off) opts into the safe behaviour: redirect to
    HTTPS, mark cookies ``Secure`` and send HSTS. Development turns all of
    it off so the local HTTP frontend and admin keep working. Every value
    can still be overridden from the environment, which matters when TLS is
    terminated by a reverse proxy or during a staged rollout.
    """

    production = not debug

    return {
        "SECURE_SSL_REDIRECT": production,
        "SESSION_COOKIE_SECURE": production,
        "CSRF_COOKIE_SECURE": production,
        "SECURE_HSTS_SECONDS": 31536000 if production else 0,
        "SECURE_HSTS_INCLUDE_SUBDOMAINS": production,
        "SECURE_HSTS_PRELOAD": production,
    }
