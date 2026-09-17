"""Create the fixed Render bootstrap admin when the SQLite DB has no admin."""
import os
import sys

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import django

django.setup()

from marketplace.models import User

USERNAME = "renderadmin"
PASSWORD = "renderadmin12345"

admins = User.objects.filter(role="admin").exists() or User.objects.filter(is_superuser=True).exists()
if admins:
    print("Render bootstrap admin: existing admin found; no changes made.")
    raise SystemExit(0)

user = User.objects.filter(username=USERNAME).first()
if user is None:
    user = User(username=USERNAME)

user.set_password(PASSWORD)
user.role = "admin"
user.is_staff = True
user.is_superuser = True
user.is_active = True
user.save()

print("Render bootstrap admin ready.")
print(f"username: {USERNAME}")
print(f"password: {PASSWORD}")
print("Change this password after the first successful login.")
