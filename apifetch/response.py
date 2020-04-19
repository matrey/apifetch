import abc
import binascii
from typing import List

from requests.models import Response
from requests.utils import parse_header_links

from .exceptions import InvalidResponse


class AbstractProcessor(metaclass=abc.ABCMeta):
    @abc.abstractmethod
    def process_one_response(self, res: Response) -> None:
        pass

    @abc.abstractmethod
    def return_all_data(self):
        pass


class JsonListProcessor(AbstractProcessor):

    data: List

    def __init__(self):
        self.data = []

    def process_one_response(self, res: Response) -> None:
        # Validate the payload is proper JSON (or raise an InvalidResponse)
        j = get_json(res)

        # Give an opportunity to mangle the whole payload, to expose a list
        payload = self.mangle_payload(j)

        for entry in payload:
            # Extract what we are interested in
            unit = self.process_item(entry)

            if unit is not None:
                # allows killing bad entries
                self.data.append(unit)

    def return_all_data(self):
        return self.data

    @staticmethod
    def process_item(entry):
        return entry

    @staticmethod
    def mangle_payload(payload):
        return payload


def get_header_links(r: Response, rel=None):  # for REST API pagination
    try:
        rels = parse_header_links(r.headers.get("link"))
        if rel is None:
            return rels
        for d in rels:
            currel = d.get("rel", None)
            if currel == rel:
                return d.get("url", None)
        return None
    except Exception:
        if rel is None:
            return []
        else:
            return None


def get_jpeg(r: Response):
    # Last 2 bytes must be ffd9
    # https://en.wikipedia.org/wiki/JPEG#Syntax_and_structure
    lastbytes = binascii.b2a_hex(r.content[-2:])
    if lastbytes != b"ffd9":
        raise InvalidResponse(
            "Payload is not a valid JPEG! Last 2 bytes were: " + str(lastbytes)
        )
    return r.content


def get_png(r: Response):
    # First 8 bytes must be 89 50 4e 47 0d 0a 1a 0a
    # http://www.libpng.org/pub/png/spec/1.2/PNG-Rationale.html#R.PNG-file-signature
    firstbytes = binascii.b2a_hex(r.content[:8])
    if firstbytes != b"89504e470d0a1a0a":
        raise InvalidResponse(
            "Payload is not a valid PNG! First 8 bytes were: " + str(firstbytes)
        )
    return r.content


def get_json(r: Response):
    # This will raise a ValueError exception if not valid JSON
    try:
        return r.json()
    except Exception as e:
        raise InvalidResponse("Payload is not valid JSON! " + str(e))


def get_xml(r: Response):
    # This will raise a ParseError exception if not valid XML
    from xml.etree import ElementTree

    try:
        return ElementTree.fromstring(r.text)
    except Exception as e:
        raise InvalidResponse("Payload is not valid XML! " + str(e))
