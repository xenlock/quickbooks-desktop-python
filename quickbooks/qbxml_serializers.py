# coding=utf-8
from __future__ import unicode_literals

from collections import OrderedDict
import json
import logging
from xml.dom import minidom
import xml.etree.ElementTree as ET

import xmltodict

from constants import STOP_ON_ERROR
from .exceptions import QuickBooksError


logger = logging.getLogger(__name__)


def format_request(request_type, request_items=None, qbxml_version='13.0', on_error=STOP_ON_ERROR):
    'Format request as QBXML'
    if not request_items:
        request_items = dict()
    section = ET.Element(request_type)
    if hasattr(request_items, 'items'):
        request_items = request_items.items()
    for key, value in request_items:
        section.extend(format_request_part(key, value))
    body = ET.Element('QBXMLMsgsRq', onError=on_error)
    body.append(section)
    document = ET.Element('QBXML')
    document.append(body)
    elements = [
        ET.ProcessingInstruction('xml', 'version="1.0"'),
        ET.ProcessingInstruction('qbxml', 'version="{}"'.format(qbxml_version)),
        document,
    ]
    request = ''.join(ET.tostring(x) for x in elements)
    return minidom.parseString(request).toprettyxml(indent="  ")


def format_request_part(key, value):
    'Format request part recursively'
    # If value is a dictionary or tuple
    if isinstance(value, tuple):
        value = OrderedDict(value)
    if hasattr(value, 'iteritems'):
        part = ET.Element(key)
        for k, v in value.iteritems():
            part.extend(format_request_part(k, v))
        return [part]
    # If value is a list
    elif isinstance(value, list):
        parts = list()
        for entry in value:
            # List of tuples is actually preferred to maintain order of elements
            # also seems to be an issue passing OrderedDict on queue last I checked
            if isinstance(entry, tuple):
                entry = OrderedDict(entry)
            # If value is a list of dictionaries,
            if hasattr(entry, 'iteritems'):
                part = ET.Element(key)
                for k, v in entry.iteritems():
                    part.extend(format_request_part(k, v))
                parts.append(part)
            # If value is a list of repeating elements
            else:
                parts += format_request_part(key, entry)
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

