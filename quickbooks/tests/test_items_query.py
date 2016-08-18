import datetime
import os
import unittest

from freezegun import freeze_time

from config import QB_LOOKUP, celery_app
from ..qbcom import QuickBooks
from ..qbxml_serializers import parse_response
from ..qbxml_request_formatter import ItemQueryRequest
from . import get_elements, get_values_by_tag


TEST_DATA_DIR = os.path.join(os.path.dirname(__file__), 'qbxml_files')


class TestItemRequests(unittest.TestCase):
    def setUp(self):
        self.initial_item_request = os.path.join(
            TEST_DATA_DIR, 'initial_item_query.xml'
        )
        self.item_query_with_start_date = os.path.join(
            TEST_DATA_DIR, 'item_query_with_start_date.xml'
        )
        self.item_query_no_start_date = os.path.join(
            TEST_DATA_DIR, 'item_query_nostart.xml'
        )
        self.item_query_listids = os.path.join(
            TEST_DATA_DIR, 'item_query_with_list_ids.xml'
        )
        self.item_query_fullnames = os.path.join(
            TEST_DATA_DIR, 'item_query_with_fullnames.xml'
        )
        self.item_query_response = os.path.join(
            TEST_DATA_DIR, 'item_query_response.xml'
        )
        self.qb_com = QuickBooks(**QB_LOOKUP)

    @freeze_time("2016-10-13")
    def test_retrieving_items(self):
        # test initial request
        lookup = {
            'initial': True,
        }
        request_object = ItemQueryRequest(**lookup)
        test_request = self.qb_com.format_request(
            request_object.request_type,
            request_dictionary=request_object.request_dictionary,
        )
        with open(self.initial_item_request) as fin:
            expected_formatted_request = fin.read()
        self.assertEquals(test_request, expected_formatted_request)

        # test request with start date
        lookup = {
            'days': 20,
        }
        request_object = ItemQueryRequest(**lookup)
        test_request = self.qb_com.format_request(
            request_object.request_type,
            request_dictionary=request_object.request_dictionary,
        )
        with open(self.item_query_with_start_date) as fin:
            expected_formatted_request = fin.read()
        self.assertEquals(test_request, expected_formatted_request)

        # test request with no start date and not initial
        lookup = dict()
        request_object = ItemQueryRequest(**lookup)
        test_request = self.qb_com.format_request(
            request_object.request_type,
            request_dictionary=request_object.request_dictionary,
        )
        with open(self.item_query_no_start_date) as fin:
            expected_formatted_request = fin.read()
        self.assertEquals(test_request, expected_formatted_request)

    def test_listid_lookup(self):
        list_ids = [
            '8000380C-1459355152',
            '80002EDE-1426787483',
            '8000389D-1461788397',
            '8000332D-1441744420',
            '80002DC8-1426540969',
            '80002B70-1426111477',
            '80002813-1408669510',
            '8000380D-1459355181',
            '8000389C-1461776908',
            '8000389A-1461704236',
            '80003950-1467305266',
            '800038C2-1462902149',
            '8000380E-1459355198',
            '80003664-1446072946',
            '80003908-1464811534',
        ]
        lookup = {
            'list_ids': list_ids,
        }
        request_object = ItemQueryRequest(**lookup)
        test_request = self.qb_com.format_request(
            request_object.request_type,
            request_dictionary=request_object.request_dictionary,
        )
        with open(self.item_query_listids) as fin:
            expected_formatted_request = fin.read()

        # order of the list values isn't maintained but doesn't need to be
        # order of the qbxml elements does matter though
        self.assertEquals(
            get_elements(test_request),
            get_elements(expected_formatted_request)
        )
        # ensuring we have all list ids in the request
        self.assertEquals(
            get_values_by_tag(test_request, 'ListID'),
            get_values_by_tag(expected_formatted_request, 'ListID')
        )

    def test_fullname_lookup(self):
        full_names = [
            '25-105370',
            '11028',
            '70-106075',
            '11964',
            '11134',
            '10641',
            '564 (Old)',
            'MPVR30645',
            '12582',
            'S-14998',
            '12748',
            '20-300765',
            'MPVR38609',
            '12120',
            '560',
        ]
        lookup = {
            'full_names': full_names,
        }
        request_object = ItemQueryRequest(**lookup)
        test_request = self.qb_com.format_request(
            request_object.request_type,
            request_dictionary=request_object.request_dictionary,
        )
        with open(self.item_query_fullnames) as fin:
            expected_formatted_request = fin.read()

        # order of the list values isn't maintained but doesn't need to be
        # order of the qbxml elements does matter though
        self.assertEquals(
            get_elements(test_request),
            get_elements(expected_formatted_request)
        )
        # ensuring we have all list ids in the request
        self.assertEquals(
            get_values_by_tag(test_request, 'FullName'),
            get_values_by_tag(expected_formatted_request, 'FullName')
        )

    def test_parsing_item_query_response(self):
        # test initial request
        lookup = {
            'days': 20,
        }
        request_object = ItemQueryRequest(**lookup)
        with open(self.item_query_response) as fin:
            quickbooks_response = fin.read()

        parsed_response = parse_response(
            request_object.request_type, quickbooks_response
        )

        # test that item specific logic obtains items, groups and assemblies
        response_elements = list(
            request_object.get_response_elements(parsed_response)
        )
        self.assertEquals(len(response_elements), 421)

        # ensure the proper numbers for each category
        categories = [
            u'ItemInventoryAssemblyRet', u'ItemInventoryRet', u'ItemNonInventoryRet'
        ]
        # should be 81 assemblies
        self.assertEquals(
            sum((
                1 for i in response_elements if i['category'] == categories[0]
            )), 81
        )
        # should be 338 inventory
        self.assertEquals(
            sum((
                1 for i in response_elements if i['category'] == categories[1]
            )), 338
        )
        # should be 2 non inventory
        self.assertEquals(
            sum((
                1 for i in response_elements if i['category'] == categories[2]
            )), 2
        )


