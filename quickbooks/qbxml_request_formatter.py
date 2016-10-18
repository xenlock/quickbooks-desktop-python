# coding=utf-8
from __future__ import unicode_literals

from collections import OrderedDict
import datetime

from constants import DISTRIBUTOR_ACCOUNTS, QUICKBOOKS_PURCHASE_ORDER_CLASSES

from . import pluralize


class QuickBooksQueryRequest(object):
    """
    Base class for formatting qbxml query requests and returning response instances

    Example usage:

        from tasks import  QB_LOOKUP, celery_app
        from quickbooks import QuickBooks

        qb = QuickBooks(**QB_LOOKUP)
        qb.begin_session()

        request_object = PurchaseOrderQueryRequest(**kwargs)
        response = qb.call(
            request_object.request_type,
            request_dictionary=request_object.request_dictionary,
        )
        purchase_order_elements = request_object.get_response_elements(response)
    """
    def __init__(self, request_type, response_type, response_element_label=None, *args, **kwargs):
        self.request_type = request_type
        self.response_type = response_type
        self.response_element_label = response_element_label
        self.initial = kwargs.get('initial', False)
        self.days = kwargs.get('days')
        self.start_date = kwargs.get('start_date')
        self.end_date = kwargs.get('end_date')

        # ACCOUNT FILTER
        # should be a list whether one or many but only names or ids.  Never both! 
        # refer to quickbooks sdk documentation
        self.account_names = kwargs.get('account_names', list())
        self.account_list_ids = kwargs.get('account_list_ids', list())

        self.include_line_items = kwargs.get('include_line_items', True)
        # these should be a list whether one of many
        self.ref_numbers = kwargs.get('ref_numbers')
        # these should be a list whether one of many
        self.txn_ids = kwargs.get('txn_ids')
        self.full_names = kwargs.get('full_names')
        self.list_ids = kwargs.get('list_ids')
        self.request_dictionary = list()
        self._build_request()

    def _build_request(self):
        """
        Building the request body. Override this if necessary for building various requests
        """
        if self.txn_ids:
            self.txn_id_filter()
        elif self.ref_numbers:
            self.ref_number_filter()
        elif self.list_ids:
            self.list_id_filter()
        elif self.full_names:
            self.full_name_filter()
        else:
            self.modified_date_range_filter()
            self.account_filter()

        self.include_line_items_filter()

    def txn_id_filter(self):
        """
        pass in a list of txn_ids whether looking up one or many
        """
        if self.txn_ids:
            self.request_dictionary.append(('TxnID', self.txn_ids))

    def ref_number_filter(self):
        """
        pass in a list of ref_numbers whether looking up one or many
        """
        if self.ref_numbers:
            self.request_dictionary.append(('RefNumber', self.ref_numbers))

    def list_id_filter(self):
        """
        pass in a list of list_ids whether looking up one or many
        """
        if self.list_ids:
            self.request_dictionary.append(('ListID', self.list_ids))

    def full_name_filter(self):
        """
        pass in a list of full names whether looking up one or many
        """
        if self.full_names:
            self.request_dictionary.append(('FullName', self.full_names))

    def _get_dates(self):
        """
        get appropriate start and end dates depending on whether inital, days or start_date 
        or end_date parameters are used
        """
        if not self.initial:
            # if start date and days are not passed we return date range for past 30 days
            if not self.start_date and not self.days:
                self.days = 30
            # get start date if days is used instead of start_date
            if self.days and not self.start_date:
                self.start_date = datetime.date.today() - datetime.timedelta(days=self.days)

            date_range = [('FromModifiedDate', str(self.start_date))]
            if self.end_date:
                date_range.append(('ToModifiedDate', str(self.end_date)))
            return date_range

    def modified_date_range_filter(self):
        """return tuple for ModifiedDateRangeFilter to be used in building qbxml request args"""
        date_range = self._get_dates()
        if date_range:
            self.request_dictionary.append(('ModifiedDateRangeFilter', OrderedDict(date_range)))

    def account_filter(self):
        values = None
        # list IDs are always preferred if available so check these first
        if self.account_list_ids:
            values = {'ListID': self.account_list_ids}
        elif self.account_names:
            values = {'FullName': self.account_names}
        if values:
            self.request_dictionary.append(('AccountFilter', values))
                
    def include_line_items_filter(self):
        if self.include_line_items:
            self.request_dictionary.append(('IncludeLineItems', '1'))

    def get_response_elements(self, response):
        """
        Removes unnecessary nested from quickbooks response.  Ensure _call method is called first
        """
        response_elements = response.get(self.response_type, dict()).get(self.response_element_label, dict())
        for element in pluralize(response_elements):
            yield element


class CheckQueryRequest(QuickBooksQueryRequest):
    processing_task = 'quickbooks.tasks.process_check'

    def __init__(self, **kwargs):
        kwargs['account_names'] = DISTRIBUTOR_ACCOUNTS
        super(CheckQueryRequest, self).__init__('CheckQueryRq', 'CheckQueryRs', 'CheckRet', **kwargs)


class ItemQueryRequest(QuickBooksQueryRequest):
    processing_task = 'quickbooks.tasks.process_item'

    def __init__(self, **kwargs):
        kwargs['include_line_items'] = False
        super(ItemQueryRequest, self).__init__('ItemQueryRq', 'ItemQueryRs', **kwargs)

    def modified_date_range_filter(self):
        """return tuple for ModifiedDateRangeFilter to be used in building qbxml request args"""
        date_range = self._get_dates()
        if date_range:
            self.request_dictionary += date_range

    def get_response_elements(self, response):
        """
        adding some item specific logic
        """
        # remove unnecessary nesting
        items = response.get(self.response_type)
        keys = [key for key in items.keys() if 'Item' in key]
        for category in keys:
            entry = items[category]
            for item in pluralize(entry):
                item['category'] = category
                yield item

class PurchaseOrderQueryRequest(QuickBooksQueryRequest):
    processing_task = 'quickbooks.tasks.process_purchase_order'

    def __init__(self, **kwargs):
        super(PurchaseOrderQueryRequest, self).__init__(
            'PurchaseOrderQueryRq', 
            'PurchaseOrderQueryRs',
            'PurchaseOrderRet',
             **kwargs
        )

    def get_response_elements(self, response):
        """
        adding some purchase order specific logic
        """
        purchase_orders = super(PurchaseOrderQueryRequest, self).get_response_elements(response)

        verified_pos = list()
        for purchase_order in purchase_orders:
            # only include relevant quickbooks classes
            if purchase_order.get('ClassRef', dict()).get('FullName') in QUICKBOOKS_PURCHASE_ORDER_CLASSES:
                # keep purchase order line items consistent 
                po_lines = list()
                po_lines += pluralize(purchase_order.get('PurchaseOrderLineRet', list()))

                po_line_groups = purchase_order.get('PurchaseOrderLineGroupRet', dict())
                if not isinstance(po_line_groups, list):
                    po_line_groups = [po_line_groups]
                for group in po_line_groups: 
                    po_lines += pluralize(group.get('PurchaseOrderLineRet', list()))

            if po_lines:
                purchase_order['po_lines'] = po_lines
                verified_pos.append(purchase_order)
        return verified_pos

