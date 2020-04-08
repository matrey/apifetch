import binascii

from requests.models import Response

from .exceptions import InvalidResponse


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
