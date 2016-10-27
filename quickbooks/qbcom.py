# coding=utf-8
from __future__ import unicode_literals

from collections import OrderedDict
import csv
import ctypes
import datetime
from itertools import chain
import os
import uuid

from pythoncom import CoInitialize
from pywintypes import com_error
import win32api
from win32com.client import Dispatch, constants
from win32com.client.makepy import GenerateFromTypeLibSpec

from .exceptions import AdapterNotFound, QuickBooksError
from .qbxml_serializers import format_request, parse_response
from .qbxml_request_formatter import (
    CheckQueryRequest,
    ItemQueryRequest,
    PurchaseOrderQueryRequest
)


# After running the following command, you can check the generated type library
# for a list of dispatchable classes and their associated methods.
# The generated type library should be in site-packages/win32com/gen_py/
# e.g. /Python27/Lib/site-packages/win32com/gen_py/
GenerateFromTypeLibSpec('QBXMLRP2 1.0 Type Library')


def save_request_xml(request_type, request):
    now = datetime.datetime.now().strftime('%Y%m%d-%H%M%S')
    file_name = '{}-{}{}.xml'.format(now, uuid.uuid4(), request_type)
    with open(file_name, 'wt') as fout:
        fout.write(request)


def get_request_formatter(request_type, query_params):
    adapters = {
        'check': CheckQueryRequest,
        'item': ItemQueryRequest,
        'purchase_order': PurchaseOrderQueryRequest,
    }
    try:
        return adapters[request_type](**query_params)
    except KeyError:
        raise AdapterNotFound(
            "Adapter for {0} not found.".format(request_type)
        )


class QuickBooks(object):
    'Wrapper for the QuickBooks RequestProcessor COM interface'

    def __init__(self, application_id='', application_name='Example', company_file_name='', service_user=None, connection_type=constants.localQBD):
        'Connect'
        self.application_id = application_id
        self.application_name = application_name
        self.company_file_name = company_file_name
        self.service_user = service_user
        self.connection_type = connection_type

    def begin_session(self):
        try:
            CoInitialize()
            self.request_processor = Dispatch('QBXMLRP2.RequestProcessor')
            self.request_processor.OpenConnection2(
                self.application_id, self.application_name, self.connection_type
            )
            self.session = self.request_processor.BeginSession(
                self.company_file_name, constants.qbFileOpenDoNotCare
            )
        except com_error, error:
            self.close_by_force()
            raise QuickBooksError('Could not start QuickBooks COM interface: %s' % error)

    def __del__(self):
        'Disconnect'
        self.end_session()

    def end_session(self):
        'Disconnect'
        try:
            # attempt to do this correctly although it doesn't
            self.request_processor.EndSession(self.session)
            self.request_processor.CloseConnection()
        finally:
            # either way, close by force when you are finished
            self.close_by_force()

    def close_by_force(self):
        rows = os.popen('tasklist /V /FO CSV').readlines()
        pids = [i for i in csv.DictReader(rows)]

        for i in pids:
            user_name = i['User Name'] if i['User Name'] else ''
            if user_name.endswith(self.service_user) and i['Image Name'] in ['qbupdate.exe', 'QBW32.EXE']:
                # Kill the process using pywin32
                PROCESS_TERMINATE = 1
                handle = ctypes.windll.kernel32.OpenProcess(PROCESS_TERMINATE, False, int(i['PID']))
                ctypes.windll.kernel32.TerminateProcess(handle, -1)
                ctypes.windll.kernel32.CloseHandle(handle)

    def format_request(self, request_type, request_dictionary=None, save_xml=False):
        request = format_request(request_type, request_dictionary)
        if save_xml:
            save_request_xml(request_type, request)
        return request

    def call(self, request_type, request_dictionary=None, save_xml=False):
        'Send request and parse response'
        request = self.format_request(request_type, request_dictionary, save_xml=save_xml)
        response = self.request_processor.ProcessRequest(self.session, request)
        if save_xml:
            save_request_xml(request_type, response)
        return parse_response(request_type, response)

    def quickbooks_query(self, query_type, request_args=dict()):
        request_object = get_request_formatter(query_type, request_args)
        response = self.call(
            request_object.request_type,
            request_dictionary=request_object.request_dictionary,
        )
        return request_object.get_response_elements(response)

    def get_preferences(self):
        response = self.call('PreferencesQueryRq')
        preferences = response.get('PreferencesQueryRs', {}).get('PreferencesRet', {})
        return [(i, dict(preferences[i])) for i in preferences]

