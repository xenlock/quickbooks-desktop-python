from __future__ import absolute_import

import celery
from celery import signals
from celery_api import CeleryApi

from raven import Client as RavenClient
from raven.contrib.celery import register_signal, register_logger_signal

from .config import SETTINGS


class Celery(celery.Celery):
    def on_configure(self):
        client = RavenClient(SETTINGS.get('sentry_dsn'))

        # register a custom filter to filter out duplicate logs
        register_logger_signal(client)

        # hook into the Celery error handler
        register_signal(client)


celery_app = Celery(SETTINGS.get('app_name'))
celery_app.config_from_object('config:config')

api = CeleryApi(celery_app)

