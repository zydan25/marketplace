module.exports = {
  apps: [
    {
      name: "shabik-django",
      script: "/home/root/projects/shabik/backend/.venv/bin/gunicorn",
      args: "config.wsgi:application --bind 127.0.0.1:5015 --workers 3 --timeout 120",
      cwd: "/home/root/projects/shabik/backend",
      interpreter: "none",
      env: {
        // PM2 will also load .env.production if dotenv is used, but we pass it explicitly
        DJANGO_DEBUG: "0",
        PYTHONUNBUFFERED: "1"
      }
    }
  ]
};
