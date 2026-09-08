module.exports = {
  apps: [
    {
      name: "shabik-django",
      script: "/home/root/projects/shabik/backend/.venv/bin/gunicorn",
      args: "config.wsgi:application --bind 127.0.0.1:5015 --workers 3 --timeout 120",
      cwd: "/home/root/projects/shabik/backend",
      interpreter: "none",
      env: {
        // The service queue worker now runs inside Django; the process lock
        // guarantees only one Gunicorn worker executes queued tasks.
        DJANGO_DEBUG: "0",
        PYTHONUNBUFFERED: "1",
        SERVICES_EMBEDDED_WORKER: "1",
        SERVICES_WORKER_LOCK_PATH: "/tmp/shabik-services-worker.lock"
      }
    }
  ]
};
