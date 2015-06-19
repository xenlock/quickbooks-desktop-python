import json

from celery import Celery
from celery.utils.log import get_task_logger

from quickbooks import QuickBooks


logger = get_task_logger(__name__)

with open("settings.json") as fin:
    settings = json.loads(fin.read())

celery_app = Celery(settings.get('app_name'), broker=settings.get('broker'))
celery_app.conf.update(
    CELERY_ACCEPT_CONTENT=['pickle'],
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
def qb_requests(request_list):
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

    for request, request_dict in request_list:
        try:
            response = qb.call(request_type, request_dictionary=request_dict)
            celery_app.send_task('quickbooks.tasks.log_response', [response], queue='soc_accounting')
        except Exception as e:
            logger.error(e)

    purchase_orders = qb.get_open_purchase_orders()
    celery_app.send_task('quickbooks.tasks.process_purchase_orders', [purchase_orders], queue='soc_accounting')
    # making sure to end session and close file
    del(qb)


@celery_app.task(name='qb_desktop.tasks.pretty_print', track_started=True, max_retries=5)
def pretty_print(request_type, request_dictionary=None):
    qb = QuickBooks(**QB_LOOKUP)
    qb.format_request(request_type, request_dictionary=request_dictionary, saveXML=True)

