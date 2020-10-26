# quickbooks-desktop-python
forking the following project https://github.com/DanHanson82/quickbooks-desktop-python

Implementing using celery worker running on a windows machine using activestate active python installation listed below for com module.
Most of the logic will be performed by outside project running on well behaved operating systems.  

running as a service:
```
    python service.py --startup=auto install

```
Edit the service Log On properties in the windows services manager.
ensure settings.json is setup correctly and that the logon is a not Local System account.
Also, when running on Windows 7, 8 or Vista, ensure that UAC is turned on.  For whatever reason there will be issues if it isn't

 And to remove:
 
 ```
     python service.py remove
 
 ```

https://community.intuit.com/articles/1019738-turn-user-account-control-uac-on-and-off-in-windows-8-7-or-vista

## Requirements
- QuickBooks desktop application
- QuickBooks SDK
- win32com http://www.activestate.com/activepython/downloads


## Tasks

### clearing the queue
celery -A tasks amqp queue.purge qb_desktop

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


