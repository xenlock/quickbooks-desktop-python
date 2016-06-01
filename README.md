# quickbooks-desktop-python
forking the following project https://github.com/invisibleroads/inteum-quickbooks-sync

It appears to be abandoned for good reason.  I think most of the planet has moved from Quickbooks desktop except me unforunately.  
Looking to utilize the qbcom and qbxml modules.

Implementing using celery worker running on a windows machine using activestate active python installation listed below for com module.
Most of the logic will be performed by outside project running on well behaved operating systems.  Inspired by the following article:

http://www.imankulov.name/posts/celery-for-internal-api.html

running as a service:
```
    python service.py --startup=auto install
    python service.py start

```
And to remove:

```
    python service.py stop
    python service.py remove

```
ensure settings.json is setup correctly and that the logon is a not Local System account.
This will throw an error when attempting to open the quickbooks file on a machine where somebody is logged into quickbooks.
This is a known issue:

http://support.flexquarters.com/esupport/index.php?/Knowledgebase/Article/View/2529/45/qb-begin-session-failed-error--80040408-could-not-start-quickbooks


## Requirements
- QuickBooks desktop application
- QuickBooks SDK
- win32com http://www.activestate.com/activepython/downloads


## Tasks

### qb_requests:

We always send a list of requests so we aren't opening and closing file more than necessary
ex: 
```
qb_requests.delay([
        (item_key, model_name, ('ItemReceiptAddRq', receipt_instance.quickbooks_request_tuple)),
        (item_key, model_name, ('ItemReceiptAddRq', receipt_instance.quickbooks_request_tuple))
        ])
```

By default we are also grabbing and returning list of all open purchase orders in the process and likely performing some more tasks going forward.  This way we get the latest list of purchase orders each time we post item receipts.  This is optional if we are making a lot of requests that don't need to be concerned with purchase orders for every request.

```
qb_requests.delay([
        (item_key, model_name, ('ItemReceiptAddRq', receipt_instance.quickbooks_request_tuple)),
        (item_key, model_name, ('ItemReceiptAddRq', receipt_instance.quickbooks_request_tuple))
        ], with_sides=False)

```

We can also send nothing if we just want to update purchase orders

```
qb_requests.delay()

```

### get_items:
this task takes no arguments and just grabs every item in Quickbooks and sends a task to process the response for each item.  I will likely be adding argument for item type in the future.

### pretty_print:
send the same list of requests as you would to qb_request without the key or model name.  The requests will be formatted to qbxml and saved to files in the worker directory where they can be tested using the qbxml validator from intuit

```
pretty_print.delay([
        ('ItemReceiptAddRq', receipt_instance.quickbooks_request_tuple),
        ('ItemReceiptAddRq', receipt_instance.quickbooks_request_tuple)
        ])
```


