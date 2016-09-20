from __future__ import absolute_import

import json
import os

from kombu import Exchange, Queue


fn = os.path.join(os.path.dirname(__file__), 'settings.json')


with open(fn) as fin:
    SETTINGS = json.loads(fin.read())


QB_LOOKUP = {
    'application_name': SETTINGS.get(u'qb_application_name'),
    'company_file_name': SETTINGS.get(u'qb_file_location'),
    'service_user': SETTINGS.get(u'service_user'),
}



default_exchange = Exchange('qb_desktop', type='direct')
quickbooks_exchange = Exchange('quickbooks', type='direct')
CELERY_QUEUES = (
    Queue('qb_desktop', default_exchange, routing_key='qb_desktop'),
    Queue('quickbooks', quickbooks_exchange, routing_key='quickbooks'),
)
CELERY_DEFAULT_EXCHANGE = default_exchange
CELERYD_TASK_SOFT_TIME_LIMIT = 3600
CELERY_DEFAULT_EXCHANGE_TYPE = 'direct'
CELERY_DEFAULT_ROUTING_KEY = 'qb_desktop'
CELERY_DEFAULT_QUEUE = 'qb_desktop'
CELERY_CREATE_MISSING_QUEUES = False
CELERY_ACCEPT_CONTENT = ['pickle', 'json']
BROKER_URL = SETTINGS.get('broker')
CELERY_RESULT_BACKEND = SETTINGS.get('backend')
CELERY_ENABLE_UTC = True
CELERY_TASK_RESULT_EXPIRES = 7200
CELERY_TIMEZONE = 'America/Denver'
CELERY_DEFAULT_QUEUE = 'qb_desktop'
CELERYD_HIJACK_ROOT_LOGGER = False
IGNORE_RESULT = False
CELERY_ALWAYS_EAGER = False

LOGGING = {
    'version': 1,
    'disable_existing_loggers': True,
    'root': {
        'level': 'WARNING',
        'handlers': ['sentry'],
    },
    'formatters': {
        'verbose': {
            'format': '%(levelname)s %(asctime)s %(module)s %(process)d %(thread)d %(message)s'
        },
    },
    'handlers': {
        'console': {
            'level': 'DEBUG',
            'class': 'logging.StreamHandler',
        },
        'sentry': {
            'level': 'DEBUG',
            'class': 'raven.handlers.logging.SentryHandler',
            'dsn': SETTINGS.get('sentry_dsn'),
            },
    },
    'loggers': {
        'raven': {
            'level': 'DEBUG',
            'handlers': ['console', 'sentry'],
            'propagate': False,
        },
        'sentry.errors': {
            'level': 'DEBUG',
            'handlers': ['console', 'sentry'],
            'propagate': False,
        },
    },
}


