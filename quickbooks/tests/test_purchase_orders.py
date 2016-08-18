import datetime
import os
import unittest

from config import QB_LOOKUP, celery_app
from ..qbcom import QuickBooks
from ..qbxml_serializers import parse_response
from ..qbxml_request_formatter import PurchaseOrderQueryRequest
from . import get_elements, get_values_by_tag


TEST_DATA_DIR = os.path.join(os.path.dirname(__file__), 'qbxml_files')


class TestPurchaseOrderRequests(unittest.TestCase):
    def setUp(self):
        self.initial_purchase_order_request = os.path.join(
            TEST_DATA_DIR, 'initial_purchase_order_query.xml'
        )
        self.purchase_order_request = os.path.join(
            TEST_DATA_DIR, 'purchase_order_query_with_startdate.xml'
        )
        self.purchase_order_txnids = os.path.join(
            TEST_DATA_DIR, 'purchase_order_query_with_txnids.xml'
        )
        self.purchase_order_refnumbers = os.path.join(
            TEST_DATA_DIR, 'purchase_order_query_with_refnumbers.xml'
        )
        self.purchase_order_response = os.path.join(
            TEST_DATA_DIR, 'purchase_order_query_response.xml'
        )
        self.qb_com = QuickBooks(**QB_LOOKUP)

    def test_retrieving_purchase_orders(self):
        # test initial request
        lookup = {
            'initial': True,
        }
        request_object = PurchaseOrderQueryRequest(**lookup)
        test_request = self.qb_com.format_request(
            request_object.request_type,
            request_dictionary=request_object.request_dictionary,
        )
        with open(self.initial_purchase_order_request) as fin:
            expected_formatted_request = fin.read()
        self.assertEquals(test_request, expected_formatted_request)

        # test request with start date
        lookup = {
            'start_date': datetime.date(2016, 8, 27)
        }
        request_object = PurchaseOrderQueryRequest(**lookup)
        test_request = self.qb_com.format_request(
            request_object.request_type,
            request_dictionary=request_object.request_dictionary,
        )
        with open(self.purchase_order_request) as fin:
            expected_formatted_request = fin.read()
        self.assertEquals(test_request, expected_formatted_request)

    def test_txnid_lookup(self):
        txn_ids = [
            '466E04-1470691662',
            '46DE05-1473362163',
            '471219-1474393071',
            '46526B-1469811956',
            '46D39D-1472843278',
            '471A38-1474580814',
            '466522-1470326943',
            '45A24B-1467222708',
            '46D2DC-1472835223',
            '46E6C9-1473706489',
            '44B53A-1464296822',
            '47069F-1474045450',
            '46D622-1473171639',
        ]
        lookup = {
            'txn_ids': txn_ids,
        }
        request_object = PurchaseOrderQueryRequest(**lookup)
        test_request = self.qb_com.format_request(
            request_object.request_type,
            request_dictionary=request_object.request_dictionary,
        )
        with open(self.purchase_order_txnids) as fin:
            expected_formatted_request = fin.read()

        # order of the list values isn't maintained but doesn't need to be
        # order of the qbxml elements does matter though
        self.assertEquals(
            get_elements(test_request),
            get_elements(expected_formatted_request)
        )
        # ensuring we have all txn_ids in the request
        self.assertEquals(
            get_values_by_tag(test_request, 'TxnID'),
            get_values_by_tag(expected_formatted_request, 'TxnID')
        )

    def test_refnumber_lookup(self):
        ref_numbers = [
            'SOC19062',
            'SOC19242',
            'SOC19313',
            'SOC18998',
            'SOC19204',
            'SOC19329',
            'SOC19039',
            'SOC18853',
            'SOC19200',
            'SOC19265',
            'SOC18651',
            'SOC19294',
            'SOC19230',
        ]
        lookup = {
            'ref_numbers': ref_numbers,
        }
        request_object = PurchaseOrderQueryRequest(**lookup)
        test_request = self.qb_com.format_request(
            request_object.request_type,
            request_dictionary=request_object.request_dictionary,
        )
        with open(self.purchase_order_refnumbers) as fin:
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

    def test_parsing_purchase_order_query_response(self):
        # test initial request
        lookup = {
            'start_date': datetime.date(2016, 8, 27)
        }
        request_object = PurchaseOrderQueryRequest(**lookup)
        with open(self.purchase_order_response) as fin:
            quickbooks_response = fin.read()

        parsed_response = parse_response(
            request_object.request_type, quickbooks_response
        )
        # test that purchase order specific logic filters out unnecessary 
        response_elements = request_object.get_response_elements(parsed_response)
        self.assertEquals(len(list(response_elements)), 56)

