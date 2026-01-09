import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings')
django.setup()

from django.contrib.auth.models import User

# Usuń istniejącego użytkownika jeśli istnieje
User.objects.filter(username='mati').delete()

# Stwórz nowego superusera
user = User.objects.create_superuser('mati', 'mati@gmail.com', 'test123')
print(f"✓ Użytkownik '{user.username}' stworzony")
print(f"  Email: {user.email}")
print(f"  Hasło: test123")
print("\nTeraz możesz się zalogować na http://localhost:8000/login/")
