import xml.etree.ElementTree as ET


def get_elements(xml_docstring):
    tree = ET.fromstring(xml_docstring)
    return [i.tag for i in tree.iter()]

def get_values_by_tag(xml_docstring, tag):
    tree = ET.fromstring(xml_docstring)
    return {i.text for i in tree.iter(tag)}


