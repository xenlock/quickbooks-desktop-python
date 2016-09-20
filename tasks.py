from __future__ import absolute_import

from collections import OrderedDict
import datetime
import json

from config import celery_app, QB_LOOKUP
from celery.utils.log import get_task_logger

from quickbooks import QuickBooks, QuickBooksError


logger = get_task_logger(__name__)


@celery_app.task(name='qb_desktop.tasks.qb_requests', track_started=True, max_retries=5)
def qb_requests(request_list=None, initial=False, with_sides=True, app='quickbooks', days=3):
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
            ], with_sides=False)

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

        if with_sides:
            # process all appropriate purchase orders with soc_accounting and
            # post all unposted purchase orders to snapfulfil once these are finished processing
            for purchase_order in qb.get_purchase_orders(days=days):
                celery_app.send_task(
                    'quickbooks.tasks.process_purchase_order',
                    queue='quickbooks',
                    args=[purchase_order], expires=1800
                )
        celery_app.send_task(
            'quickbooks.tasks.post_purchase_orders_to_snapfulfil',
            queue='quickbooks',
            expires=1800
        )
        celery_app.send_task(
                'quickbooks.tasks.process_preferences',
                queue='quickbooks',
                args=[qb.get_preferences()], expires=1800
        )
        # making sure to end session and close file
    finally:
        del(qb)


@celery_app.task(name='qb_desktop.tasks.get_items', track_started=True, max_retries=5)
def get_items(initial=False, days=3):
    """
    this task takes no arguments and just grabs every item in Quickbooks and sends a task to process the response for each item.  I will likely be adding argument for item type in the future.
    """
    try:
        qb = QuickBooks(**QB_LOOKUP)
        qb.begin_session()
        for item in qb.get_items(initial=initial, days=days):
            celery_app.send_task(
                'quickbooks.tasks.process_item',
                queue='quickbooks',
                args=[item], expires=3600
            )
    finally:
        del(qb)


@celery_app.task(name='qb_desktop.tasks.get_checks', track_started=True, max_retries=5)
def get_checks(initial=False, days=5, accounts=['uncleared', 'cleared']):
    """
    grab all cleared and uncleared Distributor checks
    """
    try:
        qb = QuickBooks(**QB_LOOKUP)
        qb.begin_session()
        for check in qb.get_checks(initial=initial, days=days, accounts=accounts):
            celery_app.send_task(
                'quickbooks.tasks.process_check',
                queue='quickbooks',
                args=[check], expires=3600
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
        qb.format_request(request_type, request_dictionary=request_dict, saveXML=True)

