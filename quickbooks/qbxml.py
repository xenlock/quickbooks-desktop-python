'Functions for formatting and parsing QBXML'
from __future__ import unicode_literals

from collections import OrderedDict
import json
import logging
import xml.etree.ElementTree as ET
import xmltodict

from .exceptions import QuickBooksError


logger = logging.getLogger(__name__)


def format_request(request_type, request_dictionary=None, qbxmlVersion='13.0', onError='stopOnError'):
    'Format request as QBXML'
    if not request_dictionary:
        request_dictionary = dict()
    section = ET.Element(request_type)
    for key, value in request_dictionary.iteritems():
        section.extend(format_request_part(key, value))
    body = ET.Element('QBXMLMsgsRq', onError=onError)
    body.append(section)
    document = ET.Element('QBXML')
    document.append(body)
    elements = [
        ET.ProcessingInstruction('xml', 'version="1.0"'),
        ET.ProcessingInstruction('qbxml', 'version="%s"' % qbxmlVersion),
        document,
    ]
    return ''.join(ET.tostring(x) for x in elements)


def format_request_part(key, value):
    'Format request part recursively'
    # If value is a dictionary,
    if isinstance(value, tuple):
        value = OrderedDict(value)
    if hasattr(value, 'iteritems'):
        part = ET.Element(key)
        for x, y in value.iteritems():
            part.extend(format_request_part(x, y))
        return [part]
    # If value is a list of dictionaries,
    elif isinstance(value, list):
        parts = []
        for valueByKey in value:
            if isinstance(valueByKey, tuple):
                valueByKey = OrderedDict(valueByKey)
            part = ET.Element(key)
            for x, y in valueByKey.iteritems():
                part.extend(format_request_part(x, y))
            parts.append(part)
        return parts
    # If value is neither a dictionary nor a list,
    else:
        part = ET.Element(key)
        part.text = unicode(value)
        return [part]


def parse_response(request_type, response):
    'Parse QBXML response into a list of dictionaries'
    response_dict = xmltodict.parse(response)
    response_body = response_dict['QBXML']['QBXMLMsgsRs']
    contents = response_body.get(list(response_body.keys())[0], {})
    qb_error = contents.get('@statusSeverity')
    if qb_error == 'Error':
        logger.error('Request Type: {} Error Message: {}'.format(request_type, contents.get('@statusMessage')))
    return response_body

