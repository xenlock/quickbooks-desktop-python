'Convenience classes for interacting with QuickBooks via win32com'
import datetime
from win32com.client import Dispatch, constants
from win32com.client.makepy import GenerateFromTypeLibSpec
from pythoncom import CoInitialize
from pywintypes import com_error

from .qbxml import format_request, parse_response


# After running the following command, you can check the generated type library
# for a list of dispatchable classes and their associated methods.
# The generated type library should be in site-packages/win32com/gen_py/
# e.g. /Python27/Lib/site-packages/win32com/gen_py/
GenerateFromTypeLibSpec('QBXMLRP2 1.0 Type Library')


class QuickBooks(object):
    'Wrapper for the QuickBooks RequestProcessor COM interface'

    def __init__(self, application_id='', application_name='Example', company_file_name='', connection_type=constants.localQBD):
        'Connect'
        CoInitialize() # Needed in case we are running in a separate thread
        try:
            self.request_processor = Dispatch('QBXMLRP2.RequestProcessor')
        except com_error, error:
            raise QuickBooksError('Could not access QuickBooks COM interface: %s' % error)
        try:
            self.request_processor.OpenConnection2(application_id, application_name, connection_type)
            self.session = self.request_processor.BeginSession(company_file_name, constants.qbFileOpenDoNotCare)
        except com_error, error:
            raise QuickBooksError('Could not start QuickBooks COM interface: %s' % error)

    def __del__(self):
        'Disconnect'
        try:
            self.request_processor.EndSession(self.session)
            self.request_processor.CloseConnection()
        except:
            pass

    def call(self, requestType, requestDictionary=None, qbxmlVersion='8.0', onError='stopOnError', saveXML=False):
        'Send request and parse response'
        def save_timestamp(name, content):
            now = datetime.datetime.now()
            open(now.strftime('%Y%m%d-%H%M%S') + '-%06i-%s' % (now.microsecond, name), 'wt').write(content)
        request = format_request(requestType, requestDictionary or {}, qbxmlVersion, onError)
        if saveXML:
            save_timestamp('request.xml', request)
        response = self.request_processor.ProcessRequest(self.session, request)
        if saveXML:
            save_timestamp('response.xml', response)
        return parse_response(response)


class QuickBooksError(Exception):
    pass

