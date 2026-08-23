"""
Gunicorn configuration for Render Web Service deployment (Phase DEPLOY-1).
==========================================================================
Location: foundation/gunicorn.conf.py
"""
import os

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
