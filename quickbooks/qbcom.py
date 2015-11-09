'Convenience classes for interacting with QuickBooks via win32com'
from collections import OrderedDict
import datetime
from win32com.client import Dispatch, constants
from win32com.client.makepy import GenerateFromTypeLibSpec
from pythoncom import CoInitialize
from pywintypes import com_error
import uuid

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
        CoInitialize() # Needed in case we are running in a separate thread
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
        try:
            self.request_processor.EndSession(self.session)
            self.request_processor.CloseConnection()
        except:
            pass

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
        return parse_response(response)



    def get_open_purchase_orders(self, start_date=None):
        request_args = [('IncludeLineItems', '1')]
        if start_date:
            request_args = [('ModifiedDateRangeFilter', {'FromModifiedDate': str(start_date)})] + request_args

        response = self.call('PurchaseOrderQueryRq', request_dictionary=OrderedDict(request_args))
        # remove unnecessary nesting
        purchase_orders = response['PurchaseOrderQueryRs']['PurchaseOrderRet']

	verified_pos = []
        for purchase_order in purchase_orders:
            def get_lines(po_line_ret):
                if not isinstance(po_line_ret, list):
                    po_line_ret = [po_line_ret]
                for line in po_line_ret:
                    purchase_order['po_lines'].append(line)
                           
            # don't grab closed purchase orders
            if purchase_order.get('IsManuallyClosed') != 'true' and purchase_order.get('IsFullyReceived') != 'true':
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
		    
		    if purchase_order['po_lines']:
                        verified_pos.append(purchase_order)
	return verified_pos

    def get_items(self):
        response = self.call('ItemQueryRq')
        # remove unnecessary nesting
        items = response['ItemQueryRs']
        keys = [key for key in items.keys() if 'Item' in key]

        for category in keys:
            for item in items[category]:
                item['category'] = category
                yield item


class QuickBooksError(Exception):
    pass

