import unicodedata

from .jsonc import JSONEncoder


def as_canonical_json_string(d: dict) -> str:
    return JSONEncoder(sort_keys=True).encode(d)


def remove_control_characters_tabs_breaks(s):
    # Thanks to https://stackoverflow.com/a/19016117/8046487
    # Note that \n, \r and \t are considered as control chars (Cc) and will get trimmed
    # Good riddance for \r, and we pre-process \n and \t to convert them to spaces instead
    s_notab = s.replace("\t", " ").replace("\n", " ")
    return "".join(ch for ch in s_notab if unicodedata.category(ch)[0] != "C")


def fix_latin_mojibake(s):
    # List from http://www.i18nqa.com/debug/utf8-debug.html
    moji = [
        "\xC2\xA0",  # 'NO-BREAK SPACE' (U+00A0)
        "\xC2\xA1",  # "¡"
        "\xC2\xA2",  # "¢"
        "\xC2\xA3",  # "£"
        "\xC2\xA4",  # "¤"
        "\xC2\xA5",  # "¥"
        "\xC2\xA6",  # "¦"
        "\xC2\xA7",  # "§"
        "\xC2\xA8",  # "¨"
        "\xC2\xA9",  # "©"
        "\xC2\xAA",  # "ª"
        "\xC2\xAB",  # "«"
        "\xC2\xAC",  # "¬"
        "\xC2\xAD",  # 'SOFT HYPHEN' (U+00AD)
        "\xC2\xAE",  # "®"
        "\xC2\xAF",  # "¯"
        "\xC2\xB0",  # "°"
        "\xC2\xB1",  # "±"
        "\xC2\xB2",  # "²"
        "\xC2\xB3",  # "³"
        "\xC2\xB4",  # "´"
        "\xC2\xB5",  # "µ"
        "\xC2\xB6",  # "¶"
        "\xC2\xB7",  # "·"
        "\xC2\xB8",  # "¸"
        "\xC2\xB9",  # "¹"
        "\xC2\xBA",  # "º"
        "\xC2\xBB",  # "»"
        "\xC2\xBC",  # "¼"
        "\xC2\xBD",  # "½"
        "\xC2\xBE",  # "¾"
        "\xC2\xBF",  # "¿"
        "\xC3\x80",  # "À"
        "\xC3\x81",  # "Á"
        "\xC3\x82",  # "Â"
        "\xC3\x83",  # "Ã"
        "\xC3\x84",  # "Ä"
        "\xC3\x85",  # "Å"
        "\xC3\x86",  # "Æ"
        "\xC3\x87",  # "Ç"
        "\xC3\x88",  # "È"
        "\xC3\x89",  # "É"
        "\xC3\x8A",  # "Ê"
        "\xC3\x8B",  # "Ë"
        "\xC3\x8C",  # "Ì"
        "\xC3\x8D",  # "Í"
        "\xC3\x8E",  # "Î"
        "\xC3\x8F",  # "Ï"
        "\xC3\x90",  # "Ð"
        "\xC3\x91",  # "Ñ"
        "\xC3\x92",  # "Ò"
        "\xC3\x93",  # "Ó"
        "\xC3\x94",  # "Ô"
        "\xC3\x95",  # "Õ"
        "\xC3\x96",  # "Ö"
        "\xC3\x97",  # "×"
        "\xC3\x98",  # "Ø"
        "\xC3\x99",  # "Ù"
        "\xC3\x9A",  # "Ú"
        "\xC3\x9B",  # "Û"
        "\xC3\x9C",  # "Ü"
        "\xC3\x9D",  # "Ý"
        "\xC3\x9E",  # "Þ"
        "\xC3\x9F",  # "ß"
        "\xC3\xA0",  # "à"
        "\xC3\xA1",  # "á"
        "\xC3\xA2",  # "â"
        "\xC3\xA3",  # "ã"
        "\xC3\xA4",  # "ä"
        "\xC3\xA5",  # "å"
        "\xC3\xA6",  # "æ"
        "\xC3\xA7",  # "ç"
        "\xC3\xA8",  # "è"
        "\xC3\xA9",  # "é"
        "\xC3\xAA",  # "ê"
        "\xC3\xAB",  # "ë"
        "\xC3\xAC",  # "ì"
        "\xC3\xAD",  # "í"
        "\xC3\xAE",  # "î"
        "\xC3\xAF",  # "ï"
        "\xC3\xB0",  # "ð"
        "\xC3\xB1",  # "ñ"
        "\xC3\xB2",  # "ò"
        "\xC3\xB3",  # "ó"
        "\xC3\xB4",  # "ô"
        "\xC3\xB5",  # "õ"
        "\xC3\xB6",  # "ö"
        "\xC3\xB7",  # "÷"
        "\xC3\xB8",  # "ø"
        "\xC3\xB9",  # "ù"
        "\xC3\xBA",  # "ú"
        "\xC3\xBB",  # "û"
        "\xC3\xBC",  # "ü"
        "\xC3\xBD",  # "ý"
        "\xC3\xBE",  # "þ"
        "\xC3\xBF",  # "ÿ"
        "\xC5\x92",  # "Œ"
        "\xC5\x93",  # "œ"
        "\xC5\xA0",  # "Š"
        "\xC5\xA1",  # "š"
        "\xC5\xB8",  # "Ÿ"
        "\xC5\xBD",  # "Ž"
        "\xC5\xBE",  # "ž"
        "\xC6\x92",  # "ƒ"
        "\xCB\x86",  # "ˆ"
        "\xCB\x9C",  # "˜"
        "\xE2\x80\x93",  # "–"
        "\xE2\x80\x94",  # "—"
        "\xE2\x80\x98",  # "‘"
        "\xE2\x80\x99",  # "’"
        "\xE2\x80\x9A",  # "‚"
        "\xE2\x80\x9C",  # "“"
        "\xE2\x80\x9D",  # "”"
        "\xE2\x80\x9E",  # "„"
        "\xE2\x80\xA0",  # "†"
        "\xE2\x80\xA1",  # "‡"
        "\xE2\x80\xA2",  # "•"
        "\xE2\x80\xA6",  # "…"
        "\xE2\x80\xB0",  # "‰"
        "\xE2\x80\xB9",  # "‹"
        "\xE2\x80\xBA",  # "›"
        "\xE2\x82\xAC",  # "€"
        "\xE2\x84\xA2",  # "™"
    ]
    is_moji = False
    for pattern in moji:
        if pattern in s:
            is_moji = True
            break

    if is_moji:
        print(
            "Detected likely ISO-8859-xx / latin1 / win-1252 mojibake: {}".format(s)
        )  # TODO: use logging
        try:
            return s.encode("windows-1252").decode()
        except Exception as e:
            # Can fail (e.g. mojibake mixed with UTF-8 content, like "Móc cùi đề DÃ©railleur")
            # UnicodeEncodeError: 'charmap' codec can't encode characters in position 8-9: character maps to <undefined>
            print(
                'Failed to fix suspected mojibake "{}", error returned: {}'.format(
                    s, str(e)
                )
            )  # TODO: use logging, with warning level (not normal)
            pass

    return s
