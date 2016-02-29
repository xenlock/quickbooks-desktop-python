from __future__ import absolute_import

from collections import OrderedDict
import datetime
import json

from celery_app import celery_app, SETTINGS
from celery.utils.log import get_task_logger

from quickbooks import QuickBooks


logger = get_task_logger(__name__)


QB_LOOKUP = {
    'application_name': SETTINGS.get(u'qb_application_name'),
    'company_file_name': SETTINGS.get(u'qb_file_location')
}


@celery_app.task(name='qb_desktop.tasks.qb_requests', track_started=True, max_retries=5)
def qb_requests(request_list=None, initial=False, with_sides=True):
    """
    Always send a list of requests so we aren't opening and closing file more than necessary
    ex: 
    qb_requests.delay([
            (item_key, model_name, ('ItemReceiptAddRq', receipt_instance.quickbooks_request_tuple)),
            (item_key, model_name, ('ItemReceiptAddRq', receipt_instance.quickbooks_request_tuple))
            ])

    By default we are also grabbing and returning list of all open purchase orders in the process and likely performing some more tasks going forward.  This way we get the latest list of purchase orders each time we post item receipts.  This is optional if we are making a lot of requests that don't need to be concerned with purchase orders for every request.

    qb_requests.delay([
            (item_key, model_name, ('ItemReceiptAddRq', receipt_instance.quickbooks_request_tuple)),
            (item_key, model_name, ('ItemReceiptAddRq', receipt_instance.quickbooks_request_tuple))
            ]), with_sides=False)

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
    """
    this task takes no arguments and just grabs every item in Quickbooks and sends a task to process the response for each item.  I will likely be adding argument for item type in the future.
    """
    qb = QuickBooks(**QB_LOOKUP)
    qb.begin_session()
    for item in qb.get_items():
        celery_app.send_task('quickbooks.tasks.process_item', [item], queue='soc_accounting')
    del(qb)


@celery_app.task(name='qb_desktop.tasks.pretty_print', track_started=True, max_retries=5)
def pretty_print(request_list):
    """
    send the same list of requests as you would to qb_request without the key or model name.  The requests will be formatted to qbxml and saved to files in the worker directory where they can be tested using the qbxml validator from intuit
    ex: 
    pretty_print.delay([
            ('ItemReceiptAddRq', receipt_instance.quickbooks_request_tuple),
            ('ItemReceiptAddRq', receipt_instance.quickbooks_request_tuple)
            ])

    """
    qb = QuickBooks(**QB_LOOKUP)

    for entry in request_list:
        request_type, request_dict = entry
        qb.format_request(request_type, request_dictionary=request_dict, saveXML=True)

