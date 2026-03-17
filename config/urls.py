from django.contrib import admin
from django.urls import include, path
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/auth/", include("accounts.urls")),
    path("api/workers/", include("workers.urls")),
    path("api/documents/", include("documents.urls")),
    path("api/applications/", include("applications.urls")),
    path("api/officer/", include("officer_portal.urls")),
    path("api/id-card/", include("id_cards.urls")),
    path("worker/", include("worker_portal.urls")),
    path("", include("worker_portal.urls")),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)