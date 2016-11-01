from __future__ import absolute_import

from collections import OrderedDict
import datetime
import json

from config import celery_app, QB_LOOKUP
import constants
from celery.utils.log import get_task_logger

from quickbooks.exceptions import QuickBooksError
from quickbooks.qbxml_request_formatter import CheckQueryRequest
from quickbooks.qbcom import QuickBooks


logger = get_task_logger(__name__)


# doesn't seem to respect the CELERYD_TASK_SOFT_TIME_LIMIT setting
SOFT_TIME_LIMIT = 3600


@celery_app.task(name='qb_desktop.tasks.qb_requests', track_started=True, max_retries=5, soft_time_limit=SOFT_TIME_LIMIT)
def qb_requests(request_list=None, app='quickbooks'):
    """
    Always send a list of requests so we aren't opening and closing file more than necessary
    ex: 
    qb_requests.delay([
        (item_key, model_name, ('ItemReceiptAddRq', receipt_instance.quickbooks_request_tuple)),
        (item_key, model_name, ('ItemReceiptAddRq', receipt_instance.quickbooks_request_tuple))
    ])
    """
    try:
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
                        celery_app.send_task(
                            'quickbooks.tasks.process_response',
                            queue='quickbooks',
                            args=[surrogate_key, model_name, response, app], expires=1800
                        )
                except Exception as e:
                    logger.error(e)

        celery_app.send_task(
            'quickbooks.tasks.process_preferences',
            queue='quickbooks',
            args=[qb.get_preferences()], expires=1800
        )
    finally:
        # making sure to end session and close file
        del(qb)


@celery_app.task(name='qb_desktop.tasks.quickbooks_query', track_started=True, max_retries=5, soft_time_limit=SOFT_TIME_LIMIT)
def quickbooks_query(query_type, query_params):
    """
    args are query type string and any query_params which should be a dict
    query types include 
    purchase_order, item, check
    """
    try:
        qb = QuickBooks(**QB_LOOKUP)
        qb.begin_session()
        results = qb.quickbooks_query(query_type, query_params)
        celery_app.send_task(
            'quickbooks.tasks.process_quickbooks_entities',
            queue='quickbooks', args=[query_type, list(results)], expires=1800
        )
    finally:
        del(qb)


@celery_app.task(name='qb_desktop.tasks.pretty_print', track_started=True, max_retries=5)
def pretty_print(request_list):
    """
    send the same list of requests as you would to qb_request without the key or model name.  The requests will be formatted to qbxml and saved to files in the worker directory where they can be tested using the qbxml validator from intuit
    ex: 
    pretty_print.delay([
        (item_key, model_name, ('ItemReceiptAddRq', receipt_instance.quickbooks_request_tuple)),
        (item_key, model_name, ('ItemReceiptAddRq', receipt_instance.quickbooks_request_tuple))
    ])

    """
    qb = QuickBooks(**QB_LOOKUP)

    for entry in request_list:
        surrogate_key, model_name, request_body = entry
        request_type, request_dict = request_body
        qb.format_request(request_type, request_dictionary=request_dict, save_xml=True)

