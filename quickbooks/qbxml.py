'Functions for formatting and parsing QBXML'
from __future__ import unicode_literals
from collections import OrderedDict
from celery.utils.log import get_task_logger

import json
from lxml import etree as xml
import xmltodict


logger = get_task_logger(__name__)


def format_request(request_type, request_dictionary=None, qbxmlVersion='13.0', onError='stopOnError'):
    'Format request as QBXML'
    if not request_dictionary:
        request_dictionary = dict()
    section = xml.Element(request_type)
    for key, value in request_dictionary.iteritems():
        section.extend(format_request_part(key, value))
    body = xml.Element('QBXMLMsgsRq', onError=onError)
    body.append(section)
    document = xml.Element('QBXML')
    document.append(body)
    elements = [
        xml.ProcessingInstruction('xml', 'version="1.0"'),
        xml.ProcessingInstruction('qbxml', 'version="%s"' % qbxmlVersion),
        document,
    ]
    return ''.join(xml.tostring(x, pretty_print=True) for x in elements)


def format_request_part(key, value):
    'Format request part recursively'
    # If value is a dictionary,
    if isinstance(value, tuple):
        value = OrderedDict(value)
    if hasattr(value, 'iteritems'):
        part = xml.Element(key)
        for x, y in value.iteritems():
            part.extend(format_request_part(x, y))
        return [part]
    # If value is a list of dictionaries,
    elif isinstance(value, list):
        parts = []
        for valueByKey in value:
            if isinstance(valueByKey, tuple):
                valueByKey = OrderedDict(valueByKey)
            part = xml.Element(key)
            for x, y in valueByKey.iteritems():
                part.extend(format_request_part(x, y))
            parts.append(part)
        return parts
    # If value is neither a dictionary nor a list,
    else:
        part = xml.Element(key)
        part.text = unicode(value)
        return [part]


def parse_response(response):
    'Parse QBXML response into a list of dictionaries'
    response_dict = xmltodict.parse(response)
    response_body = response_dict['QBXML']['QBXMLMsgsRs']
    qb_error = response_body.get(list(response_body.keys())[0], {}).get(
        '@statusSeverity'
    )
    if qb_error:
        logger.error(response_body)
    return response_body

