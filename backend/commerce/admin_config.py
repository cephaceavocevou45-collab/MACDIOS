"""Configure Django Admin avec son contrôle d'accès super-admin dédié."""

from django.contrib.admin.apps import AdminConfig


class AdministrationConfig(AdminConfig):
    default_site = "commerce.admin_site.SiteSuperAdmin"
