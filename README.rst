quickbooks-desktop-python
======================
forking the following project https://github.com/invisibleroads/inteum-quickbooks-sync

It appears to be abandoned for good reason.  I think most of the planet has moved from Quickbooks desktop except me unforunately.  
Looking to utilize the qbcom and qbxml modules and make this pip installable in case somebody else in the planet needs to do something similar.

Implementing using celery worker running on a windows machine using activestate active python installation listed below for com module.
Most of the logic will be performed by outside project running on well behaved operating systems.  Inspired by the following article:

http://www.imankulov.name/posts/celery-for-internal-api.html

Set variables in settings.json in project and run task using windows task scheduler

https://www.calazan.com/windows-tip-run-applications-in-the-background-using-task-scheduler/


Requirements
------------
- QuickBooks desktop application
- QuickBooks SDK
- `win32com <http://www.activestate.com/activepython/downloads>`_

