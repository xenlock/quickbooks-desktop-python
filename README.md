quickbooks-desktop-python
======================
forking the following project https://github.com/invisibleroads/inteum-quickbooks-sync

It appears to be abandoned for good reason.  I think most of the planet has moved from Quickbooks desktop except me unforunately.  
Looking to utilize the qbcom and qbxml modules.

Implementing using celery worker running on a windows machine using activestate active python installation listed below for com module.
Most of the logic will be performed by outside project running on well behaved operating systems.  Inspired by the following article:

http://www.imankulov.name/posts/celery-for-internal-api.html

Set variables in settings.json in project and run task using as windows service using the following commands:

```
    python service.py --startup=auto install
    python service.py start

```
And to remove:

```
    python service.py stop
    python service.py remove

```
Be sure to set --pool=solo when running working on windows. Seems to be an issue:
http://stackoverflow.com/questions/25495613/celery-getting-started-not-able-to-retrieve-results-always-pending

Requirements
------------
- QuickBooks desktop application
- QuickBooks SDK
- `win32com <http://www.activestate.com/activepython/downloads>`_

