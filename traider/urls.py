from django.contrib import admin
from django.contrib.auth.views import LoginView, LogoutView
from django.urls import include, path

from . import views

urlpatterns = [
    path("admin/", admin.site.urls),
    path("login/", LoginView.as_view(template_name="index.html"), name="login"),
    path("logout/", LogoutView.as_view(next_page="index"), name="logout"),
    path("", views.index, name="index"),
    path("", include("app.urls"), name="app"),
    path("dash/", include("django_plotly_dash.urls")),
]
