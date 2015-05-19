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
        'lacky.tasks.qb_request': {
            'queue': 'qb_request',
            'routing_key': 'qb_request',
        }
    }
)


@app.task(name='lacky.tasks.qb_request', track_started=True, max_retries=5)
def qb_request(request_type, request_dictionary=None):
    qb = QuickBooks(
       application_name=settings.get(u'qb_application_name'),
       company_file_name=settings.get(u'qb_file_location')
       )
    response = qb.call(request_type, request_dictionary=request_dictionary)

    # making sure to end session and close file
    del(qb)
    return response

