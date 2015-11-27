from __future__ import absolute_import

from collections import OrderedDict
import datetime
import json

import celery
from celery.utils.log import get_task_logger
from raven import Client as RavenClient
from raven.contrib.celery import register_signal, register_logger_signal

from quickbooks import QuickBooks


logger = get_task_logger(__name__)


with open("settings.json") as fin:
    settings = json.loads(fin.read())


class Celery(celery.Celery):
    def on_configure(self):
        client = RavenClient(settings.get('sentry_dsn'))

        # register a custom filter to filter out duplicate logs
        register_logger_signal(client)

        # hook into the Celery error handler
        register_signal(client)


celery_app = Celery(settings.get('app_name'), broker=settings.get('broker'))
celery_app.conf.update(
    CELERY_ACCEPT_CONTENT=['pickle', 'json'],
    CELERY_RESULT_BACKEND=settings.get('backend'),
    CELERY_ENABLE_UTC=True,
    CELERY_DEFAULT_QUEUE='quickbooks',
    IGNORE_RESULT=False
)


QB_LOOKUP = {
    'application_name': settings.get(u'qb_application_name'),
    'company_file_name': settings.get(u'qb_file_location')
}


@celery_app.task(name='qb_desktop.tasks.qb_requests', track_started=True, max_retries=5)
def qb_requests(request_list=None, initial=False, with_sides=True):
    """
    Always send a list of requests so we aren't opening and closing file more than necessary
    ex: 
    qb_requests.delay([
            ('ItemReceiptAddRq', receipt_instance.quickbooks_request_tuple),
            ('ItemReceiptAddRq', receipt_instance.quickbooks_request_tuple)
            ])

    Also will be grabbing and returning list of all open purchase orders in the process
    """
    qb = QuickBooks(**QB_LOOKUP)
    qb.begin_session()

    # process request list if it exists or just get open purchase orders
    if request_list:
        for entry in request_list:
            try:
                surrogate_key, model_name, request_body = entry
                request_type, request_dict = request_body
                response = qb.call(request_type, request_dictionary=request_dict)
                if surrogate_key and request_dict:
                    celery_app.send_task('quickbooks.tasks.process_response', [surrogate_key, model_name, response], queue='soc_accounting')
            except Exception as e:
                logger.error(e)

    if with_sides:
        if initial:
            start_date = None
        else:
            start_date = datetime.date.today() - datetime.timedelta(days=90)

        for purchase_order in qb.get_open_purchase_orders(start_date=start_date):
            celery_app.send_task('quickbooks.tasks.process_purchase_order', [purchase_order], queue='soc_accounting')

    # making sure to end session and close file
    del(qb)


@celery_app.task(name='qb_desktop.tasks.get_items', track_started=True, max_retries=5)
def get_items():
    qb = QuickBooks(**QB_LOOKUP)
    qb.begin_session()
    for item in qb.get_items():
        celery_app.send_task('quickbooks.tasks.process_item', [item], queue='soc_accounting')
    del(qb)


@celery_app.task(name='qb_desktop.tasks.pretty_print', track_started=True, max_retries=5)
def pretty_print(request_list):
    qb = QuickBooks(**QB_LOOKUP)

    for entry in request_list:
        request_type, request_dict = entry
        qb.format_request(request_type, request_dictionary=request_dict, saveXML=True)

