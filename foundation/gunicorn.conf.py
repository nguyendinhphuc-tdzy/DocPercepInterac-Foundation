"""
Gunicorn configuration for Render Web Service deployment (Phase DEPLOY-1).
==========================================================================
Location: foundation/gunicorn.conf.py
"""
import os

# Anchor the app root to THIS file's directory (foundation/) so the service boots
# correctly no matter which working directory the platform launches gunicorn from.
# `pythonpath` is applied by gunicorn before the WSGI app is imported, so
# "api.app:create_app()" resolves even if CWD is the repo root.
chdir = os.path.dirname(os.path.abspath(__file__))
pythonpath = chdir

# Render dynamically injects the listening port via PORT environment variable
port = os.getenv("PORT", "5000")
bind = f"0.0.0.0:{port}"

# Concurrency settings
workers = int(os.getenv("WEB_CONCURRENCY", "2"))
threads = int(os.getenv("PYTHON_GET_THREADS", "4"))
worker_class = "gthread"

# Timeout: 120 seconds to allow perception of multi-page documents without false worker kills
timeout = 120
graceful_timeout = 30
keepalive = 5

# Logging to stdout/stderr for Render log stream aggregation
accesslog = "-"
errorlog = "-"
loglevel = os.getenv("LOG_LEVEL", "info")
