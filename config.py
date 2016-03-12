from __future__ import absolute_import

import json


with open("settings.json") as fin:
    SETTINGS = json.loads(fin.read())


QB_LOOKUP = {
    'application_name': SETTINGS.get(u'qb_application_name'),
    'company_file_name': SETTINGS.get(u'qb_file_location')
}


# Celery
CELERY_ACCEPT_CONTENT = ['pickle', 'json']
BROKER_URL = SETTINGS.get('broker')
CELERY_RESULT_BACKEND = SETTINGS.get('backend')
CELERY_ENABLE_UTC = True
CELERY_DEFAULT_QUEUE = 'quickbooks'
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


