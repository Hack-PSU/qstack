"""
Gunicorn configuration for Cloud Run.

Cloud Run gives the container one request-serving process, injects the port to
listen on, and terminates TLS in front. Everything here follows from that plus
the size of the shared Cloud SQL instance.
"""

import os

# Cloud Run injects PORT and routes to it. The previous image hardcoded 3001,
# so it would never have received traffic.
bind = "0.0.0.0:%s" % os.environ.get("PORT", "8080")

# Threads, not more processes: each worker keeps its own SQLAlchemy pool, and
# the Cloud SQL instance is shared with apiv3 and gavel. Two threaded workers
# give the same concurrency on one vCPU while bounding this service at
# workers x (pool_size + max_overflow) = 14 connections per instance.
workers = int(os.environ.get("WEB_CONCURRENCY", "2"))
threads = int(os.environ.get("WEB_THREADS", "8"))
worker_class = "gthread"

# QStack's work is database round trips, not CPU, so threads block on I/O and
# release the GIL.

# Under Cloud Run's own 300s request timeout, so gunicorn is the one to give up,
# with a log line, rather than the platform.
timeout = int(os.environ.get("WEB_TIMEOUT", "120"))
graceful_timeout = 30
keepalive = 65

# Import once before forking rather than per worker: shortens cold starts, and
# means create_all races between workers happen less often.
preload_app = True

accesslog = "-"
errorlog = "-"
loglevel = os.environ.get("LOG_LEVEL", "info")
# Cloud Run's load balancer is the immediate peer, so log the forwarded client.
#
# Method and path only, never %(r)s: that logs the full request line including
# the query string, and the auth server completes login on non-hackpsu.org
# origins by putting a session token in the URL. With %(r)s those tokens land
# in Cloud Run's logs in full, usable for the five days they stay valid.
access_log_format = '%({x-forwarded-for}i)s "%(m)s %(U)s" %(s)s %(b)s %(D)sus'
