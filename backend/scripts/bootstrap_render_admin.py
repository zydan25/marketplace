"""Create a one-time Render bootstrap admin when the SQLite DB has no admin."""
import hashlib
import os
import sys

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import django

django.setup()

from django.conf import settings
from marketplace.models import User

USERNAME = os.getenv("RENDER_BOOTSTRAP_ADMIN_USERNAME", "renderadmin")

admins = User.objects.filter(role="admin").exists() | User.objects.filter(is_superuser=True).exists()
if admins:
    print("Render bootstrap admin: existing admin found; no changes made.")
    raise SystemExit(0)

password = "R-" + hashlib.sha256(settings.SECRET_KEY.encode("utf-8")).hexdigest()[:24] + "-A9!"
user = User.objects.filter(username=USERNAME).first()
if user is None:
    user = User(username=USERNAME)

user.set_password(password)
user.role = "admin"
user.is_staff = True
user.is_superuser = True
user.is_active = True
user.save()

print("Render bootstrap admin created.")
print(f"username: {USERNAME}")
print(f"password: {password}")
print("Change this password after the first successful login.")
