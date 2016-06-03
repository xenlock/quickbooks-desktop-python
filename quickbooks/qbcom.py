# coding=utf-8
from __future__ import unicode_literals

from collections import OrderedDict
import csv
import ctypes
import datetime
import os
import uuid

from pythoncom import CoInitialize
from pywintypes import com_error
import win32api
from win32com.client import Dispatch, constants
from win32com.client.makepy import GenerateFromTypeLibSpec

from .exceptions import QuickBooksError
from .qbxml import format_request, parse_response


# After running the following command, you can check the generated type library
# for a list of dispatchable classes and their associated methods.
# The generated type library should be in site-packages/win32com/gen_py/
# e.g. /Python27/Lib/site-packages/win32com/gen_py/
GenerateFromTypeLibSpec('QBXMLRP2 1.0 Type Library')

# Quickbook's classes are like categories for transactions
QUICKBOOKS_CLASSES = ["Gifting"]


class QuickBooks(object):
    'Wrapper for the QuickBooks RequestProcessor COM interface'

    def __init__(self, application_id='', application_name='Example', company_file_name='', connection_type=constants.localQBD):
        'Connect'
        self.application_id = application_id
        self.application_name = application_name
        self.company_file_name = company_file_name
        self.connection_type = connection_type

    def begin_session(self):
        CoInitialize()
        try:
            self.request_processor = Dispatch('QBXMLRP2.RequestProcessor')
        except com_error, error:
            raise QuickBooksError('Could not access QuickBooks COM interface: %s' % error)

        try:
            self.request_processor.OpenConnection2(
                self.application_id, self.application_name, self.connection_type
            )
            self.session = self.request_processor.BeginSession(
                self.company_file_name, constants.qbFileOpenDoNotCare
            )
        except com_error, error:
            raise QuickBooksError('Could not start QuickBooks COM interface: %s' % error)

    def __del__(self):
        'Disconnect'
        self.request_processor.EndSession(self.session)
        self.request_processor.CloseConnection()
        self.close_by_force()

    def close_by_force(self):
        rows = os.popen('tasklist /FO CSV').readlines()
        pids = [i for i in csv.DictReader(rows)]

        for i in pids:
            if i['Session Name'] == 'Services' and i['Image Name'] in ['qbupdate.exe', 'QBW32.EXE']:
                # Kill the process using pywin32
                PROCESS_TERMINATE = 1
                handle = ctypes.windll.kernel32.OpenProcess(PROCESS_TERMINATE, False, int(i['PID']))
                ctypes.windll.kernel32.TerminateProcess(handle, -1)
                ctypes.windll.kernel32.CloseHandle(handle)

    def format_request(self, request_type, request_dictionary=None, qbxml_version='13.0', onError='stopOnError', saveXML=False):
        def save_timestamp(name, content):
            now = datetime.datetime.now()
            open(now.strftime('%Y%m%d-%H%M%S') + '-{}{}'.format(uuid.uuid4(), name), 'wt').write(content)
        request = format_request(request_type, request_dictionary, qbxml_version, onError)
        if saveXML:
            save_timestamp('request.xml', request)
        return request

    def call(self, request_type, request_dictionary=None, qbxml_version='13.0', onError='stopOnError', saveXML=False):
        'Send request and parse response'
        request = self.format_request(request_type, request_dictionary, qbxml_version, onError)
        response = self.request_processor.ProcessRequest(self.session, request)
        return parse_response(request_type, response)

    def get_purchase_orders(self, initial=False, days=None):
        request_args = [('IncludeLineItems', '1')]
        if days and not initial:
            start_date = datetime.date.today() - datetime.timedelta(days=days)
            request_args = [
                ('ModifiedDateRangeFilter', {'FromModifiedDate': str(start_date)})
            ] + request_args

        response = self.call('PurchaseOrderQueryRq', request_dictionary=OrderedDict(request_args))
        # remove unnecessary nesting
        purchase_orders = response.get('PurchaseOrderQueryRs', {}).get('PurchaseOrderRet', {})
        if not isinstance(purchase_orders, list):
            purchase_orders = [purchase_orders]

        verified_pos = []
        for purchase_order in purchase_orders:
            def get_lines(po_line_ret):
                if not isinstance(po_line_ret, list):
                    po_line_ret = [po_line_ret]
                for line in po_line_ret:
                    purchase_order['po_lines'].append(line)
                           
            # only include relevant quickbooks classes
            if purchase_order.get('ClassRef', {}).get('FullName') in QUICKBOOKS_CLASSES:
                # keep purchase order line items consistent 
                purchase_order['po_lines'] = []
                get_lines(purchase_order.get('PurchaseOrderLineRet', []))

                po_line_groups = purchase_order.get('PurchaseOrderLineGroupRet', {})
                if not isinstance(po_line_groups, list):
                    po_line_groups = [po_line_groups]
                for group in po_line_groups: 
                    get_lines(group.get('PurchaseOrderLineRet', []))

                # don't grab closed purchase orders if no start date
                if not days:
                    if purchase_order.get('IsManuallyClosed') == 'true' or purchase_order.get('IsFullyReceived') == 'true':
                        purchase_order['po_lines'] = []
		    
            if purchase_order.get('po_lines'):
                verified_pos.append(purchase_order)
        return verified_pos

    def get_items(self, request_args=None, initial=False, days=None):
        if not initial and not request_args:
            td = days if days else 30
            start_date = datetime.date.today() - datetime.timedelta(days=td)
            request_args = OrderedDict([('FromModifiedDate', str(start_date)),])
        response = self.call('ItemQueryRq', request_dictionary=request_args)
        # remove unnecessary nesting
        items = response['ItemQueryRs']
        keys = [key for key in items.keys() if 'Item' in key]

        for category in keys:
            entry = items[category]
            if not isinstance(entry, list):
                entry = [entry]
            for item in entry:
                item['category'] = category
                yield item

    def get_checks(self, request_args=None, initial=False, days=None, account='uncleared'):
        accounts = {
            'uncleared': 'SOC Distributor Bonus Account:SOC Bonus Uncleared',
            'cleared': 'SOC Distributor Bonus Account:SOC Bonus Cleared',
        }
        account = accounts.get(account)
        if not request_args:
            td = days if days else 30
            start_date = datetime.date.today() - datetime.timedelta(days=td)
            request_args = [
                ('AccountFilter', {'FullName': account}),
                ('IncludeLineItems', '1'),
            ]
            if days and not initial:
                request_args = [
                    ('ModifiedDateRangeFilter', {'FromModifiedDate': str(start_date)})
                ] + request_args
        request_args = OrderedDict(request_args)

        # retrieve uncleared checks
        response = self.call('CheckQueryRq', request_dictionary=request_args)
        uncleared_checks = response['CheckQueryRs'].get('CheckRet', [])
        if not isinstance(uncleared_checks, list):
            uncleared_checks = [uncleared_checks]

        # return all checks
        return uncleared_checks

    def get_preferences(self):
        response = self.call('PreferencesQueryRq')
        preferences = response.get('PreferencesQueryRs', {}).get('PreferencesRet', {})
        return [(i, dict(preferences[i])) for i in preferences]

