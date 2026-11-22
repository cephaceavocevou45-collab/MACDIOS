"""Helpers du stockage distant des sauvegardes chiffrées."""

from django.conf import settings


def client_s3():
    """Construit le client avec les identifiants fournis par boto3 dans l'environnement."""
    import boto3

    options = {
        "region_name": settings.AWS_REGION or None,
        "endpoint_url": settings.AWS_ENDPOINT_URL or None,
    }
    if settings.AWS_ACCESS_KEY_ID and settings.AWS_SECRET_ACCESS_KEY:
        options["aws_access_key_id"] = settings.AWS_ACCESS_KEY_ID
        options["aws_secret_access_key"] = settings.AWS_SECRET_ACCESS_KEY
    return boto3.client("s3", **options)


def cle_objet_s3(nom):
    prefixe = settings.BACKUP_S3_PREFIX
    return f"{prefixe}/{nom}" if prefixe else nom
