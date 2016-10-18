import datetime
from decimal import Decimal
import os
import unittest

from freezegun import freeze_time

from config import QB_LOOKUP, celery_app
from ..qbcom import QuickBooks
from ..qbxml_serializers import parse_response
from ..qbxml_request_formatter import CheckQueryRequest
from . import get_elements, get_values_by_tag


TEST_DATA_DIR = os.path.join(os.path.dirname(__file__), 'qbxml_files')


class TestItemRequests(unittest.TestCase):
    def setUp(self):
        self.initial_check_request = os.path.join(
            TEST_DATA_DIR, 'initial_check_query.xml'
        )
        self.check_query_with_start_date = os.path.join(
            TEST_DATA_DIR, 'check_query_with_start_date.xml'
        )
        self.check_query_no_start_date = os.path.join(
            TEST_DATA_DIR, 'check_query_nostart.xml'
        )
        self.check_query_refnumbers = os.path.join(
            TEST_DATA_DIR, 'check_query_with_refnumbers.xml'
        )
        self.check_query_response = os.path.join(
            TEST_DATA_DIR, 'check_query_response.xml'
        )
        self.qb_com = QuickBooks(**QB_LOOKUP)

    @freeze_time("2016-10-17")
    def test_retrieving_items(self):
        # test initial request
        lookup = {
            'initial': True,
        }
        request_object = CheckQueryRequest(**lookup)
        test_request = self.qb_com.format_request(
            request_object.request_type,
            request_dictionary=request_object.request_dictionary,
        )
        with open(self.initial_check_request) as fin:
            expected_formatted_request = fin.read()
        self.assertEquals(test_request, expected_formatted_request)

        # test request with start date
        lookup = {
            'days': 20,
        }
        request_object = CheckQueryRequest(**lookup)
        test_request = self.qb_com.format_request(
            request_object.request_type,
            request_dictionary=request_object.request_dictionary,
        )
        with open(self.check_query_with_start_date) as fin:
            expected_formatted_request = fin.read()

        # order of the list values isn't maintained but doesn't need to be
        # order of the qbxml elements does matter though
        self.assertEquals(
            get_elements(test_request),
            get_elements(expected_formatted_request)
        )
        # ensuring we have all accounts in the request
        self.assertEquals(
            get_values_by_tag(test_request, 'FullName'),
            get_values_by_tag(expected_formatted_request, 'FullName')
        )
        # ensure date is the same
        self.assertEquals(
            get_values_by_tag(test_request, 'FromModifiedDate'),
            get_values_by_tag(expected_formatted_request, 'FromModifiedDate')
        )

        # test request with no start date and not initial
        lookup = dict()
        request_object = CheckQueryRequest(**lookup)
        test_request = self.qb_com.format_request(
            request_object.request_type,
            request_dictionary=request_object.request_dictionary,
        )
        with open(self.check_query_no_start_date) as fin:
            expected_formatted_request = fin.read()

        # order of the list values isn't maintained but doesn't need to be
        # order of the qbxml elements does matter though
        self.assertEquals(
            get_elements(test_request),
            get_elements(expected_formatted_request)
        )
        # ensuring we have all accounts in the request
        self.assertEquals(
            get_values_by_tag(test_request, 'FullName'),
            get_values_by_tag(expected_formatted_request, 'FullName')
        )
        # ensure date is the same
        self.assertEquals(
            get_values_by_tag(test_request, 'FromModifiedDate'),
            get_values_by_tag(expected_formatted_request, 'FromModifiedDate')
        )

    def test_refnumber_lookup(self):
        ref_numbers = [
            '384951',
            '136250',
            '509842',
            '385310',
            '450013',
            '384982',
            '433436',
            '450007',
            '468334',
            '494445',
            '385356',
            '433679',
            '450076',
            '468367',
            '509940'
        ]
        lookup = {
            'ref_numbers': ref_numbers,
        }
        request_object = CheckQueryRequest(**lookup)
        test_request = self.qb_com.format_request(
            request_object.request_type,
            request_dictionary=request_object.request_dictionary,
        )
        with open(self.check_query_refnumbers) as fin:
            expected_formatted_request = fin.read()

        # order of the list values isn't maintained but doesn't need to be
        # order of the qbxml elements does matter though
        self.assertEquals(
            get_elements(test_request),
            get_elements(expected_formatted_request)
        )
        # ensuring we have all refnumbers in the request
        self.assertEquals(
            get_values_by_tag(test_request, 'RefNumber'),
            get_values_by_tag(expected_formatted_request, 'RefNumber')
        )

    def test_parsing_item_query_response(self):
        lookup = dict()
        request_object = CheckQueryRequest(**lookup)
        with open(self.check_query_response) as fin:
            quickbooks_response = fin.read()

        parsed_response = parse_response(
            request_object.request_type, quickbooks_response
        )

        # test that response is parsed and checks retrieved
        response_elements = list(
            request_object.get_response_elements(parsed_response)
        )
        self.assertEquals(len(response_elements), 16)

        # test that amount is the same
        amounts = sum((Decimal(i['Amount']) for i in response_elements))
        self.assertEquals(amounts, Decimal('653.71'))
