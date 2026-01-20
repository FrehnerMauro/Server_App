"""
Gunicorn configuration for production deployment.
"""
import multiprocessing
import os

# Server Socket
bind = f"{os.getenv('HOST', '0.0.0.0')}:{os.getenv('PORT', '8000')}"
backlog = 2048

# Worker Processes
workers = int(os.getenv('WORKERS', multiprocessing.cpu_count() * 2 + 1))
worker_class = 'sync'
worker_connections = 1000
max_requests = 1000
max_requests_jitter = 50
timeout = 30
keepalive = 2

# Process Naming
proc_name = 'socialhabit_api'

# Logging
accesslog = '-'  # STDOUT
errorlog = '-'   # STDERR
loglevel = os.getenv('LOG_LEVEL', 'info').lower()
access_log_format = '%(h)s %(l)s %(u)s %(t)s "%(r)s" %(s)s %(b)s "%(f)s" "%(a)s" %(D)s'

# Server Mechanics
daemon = False
pidfile = None
umask = 0
user = None
group = None
tmp_upload_dir = None

# SSL (Optional)
# keyfile = '/path/to/keyfile'
# certfile = '/path/to/certfile'

# Server Hooks
def on_starting(server):
    """Hook beim Server-Start."""
    print("=" * 60)
    print("🚀 SocialHabit API starting...")
    print(f"Workers: {workers}")
    print(f"Bind: {bind}")
    print("=" * 60)


def worker_int(worker):
    """Hook wenn Worker unterbrochen wird."""
    worker.log.info("Worker received INT or QUIT signal")


def worker_abort(worker):
    """Hook wenn Worker abgebrochen wird."""
    worker.log.warning("Worker received SIGABRT signal")
