from backend.main import app
for route in app.routes:
    print(getattr(route, "methods", set()), getattr(route, "path", ""))
