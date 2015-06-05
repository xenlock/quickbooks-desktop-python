import json

from celery import Celery

from quickbooks import QuickBooks


with open("settings.json") as fin:
    settings = json.loads(fin.read())

app = Celery(settings.get(u'app_name'), broker=settings.get(u'broker'), backend=settings.get(u'backend'))
app.conf.update(
    CELERY_ACCEPT_CONTENT=['pickle'],
    CELERY_ENABLE_UTC=True,
    CELERY_ROUTES={
        'qb_desktop.tasks.qb_request': {'queue': 'qb_request'},
        'qb_desktop.tasks.pretty_print': {'queue': 'pretty_print'}
        }
    )


QB_LOOKUP = {
    'application_name': settings.get(u'qb_application_name'),
    'company_file_name': settings.get(u'qb_file_location')
}

@app.task(name='qb_desktop.tasks.qb_request', track_started=True, max_retries=5)
def qb_request(request_type, request_dictionary=None):
    qb = QuickBooks(**QB_LOOKUP)
    response = qb.call(request_type, request_dictionary=request_dictionary)

    # making sure to end session and close file
    del(qb)
    return response


@app.task(name='qb_desktop.tasks.pretty_print', track_started=True, max_retries=5)
def pretty_print(request_type, request_dictionary=None):
    qb = QuickBooks(**QB_LOOKUP)
    qb.format_request(request_type, request_dictionary=request_dictionary, saveXML=True)

