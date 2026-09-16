"""WSGI config for manufacturing system."""
import os
from django.core.wsgi import get_wsgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
application = get_wsgi_application()
app = application

# Ensure database tables and demo seed data exist
try:
    from django.db import connection
    from django.core.management import call_command
    
    tables = connection.introspection.table_names()
    if 'django_session' not in tables or 'accounts_user' not in tables:
        print("[WSGI] Running automatic database migrations...")
        call_command('migrate', interactive=False)
        print("[WSGI] Migrations complete.")
        
        from apps.accounts.models import User
        if not User.objects.filter(email='superadmin@example.com').exists():
            print("[WSGI] Seeding demo accounts and master data...")
            call_command('seed_demo_data')
            print("[WSGI] Demo data seeded successfully.")
except Exception as e:
    import sys
    print(f"[WSGI] Database auto-setup note: {e}", file=sys.stderr)

