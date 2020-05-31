import logging
import pendulum
import dateparser
from dateutil import parser as dateutil_parser
from helper import default_tz, markup_dusi_request, speller

log = logging.getLogger(__name__)


class MatchMoreThenOne(Exception):
    pass


def get_datetime_by_dateutil(text):
    try:
        return dateutil_parser.parse(text)
    except Exception:
        return False


def get_datetime_by_pendulum(text, tz=default_tz):
    log.debug(f"{get_datetime_by_pendulum.__name__}: {locals()}")
    try:
        return pendulum.parse(text, tz=tz, strict=False)
    except Exception:
        log.debug("failed match")
        return False


def convert_to_pendulum(datetime):
    log.debug(f"{convert_to_pendulum.__name__}: {locals()}")
    try:
        return pendulum.instance(datetime, tz=default_tz)
    except Exception:
        log.debug("failed match")
        return False


async def parse_by_markup_dusi(text):
    log.debug(f"{parse_by_markup_dusi.__name__}: {locals()}")
    parsed_text = None
    try:
        objects = await markup_dusi_request(text)

        year = month = day = hour = minute = second = None
        dtf = {
            "year": year,
            "month": month,
            "day": day,
            "hour": hour,
            "minute": minute,
            "second": second,
        }
        for token in objects["tokens"]:
            if token["type"] == "Time":
                dtf["hour"], dtf["minute"], dtf["second"] = token["formatted"].split(
                    ":"
                )
            if token["type"] == "Date":
                dtf["day"], dtf["month"], dtf["year"] = token["formatted"].split(".")
            if token["type"] == "Text":
                parsed_text = token["value"]

        if bool([v for v in dtf.values() if v is not None]):
            # TODO: сделать на 10 утра, если нет точного времение
            now = pendulum.now()
            for k in dtf.keys():
                if dtf[k] is None:
                    dtf[k] = getattr(now, k)

            dtf = {k: int(v) for k, v in dtf.items()}
            dt = pendulum.datetime(**dtf, tz=default_tz)
            # TODO: поправить переход через полночь
            return dt, parsed_text
        return False, parsed_text
    except Exception:
        return False, parsed_text


def parse_by_tokens(tokens, min=5):
    log.debug(f"{parse_by_tokens.__name__}: {locals()}")
    dts = []
    dts = [
        convert_to_pendulum(dateparser.parse(t, languages=["ru"]))
        for t in tokens
        if len(t) >= min
    ]
    dts = [i for i in dts if i and i > pendulum.now()]

    if not dts:
        dts = [get_datetime_by_pendulum(t) for t in tokens if len(t) >= min]
        dts = [i for i in dts if i and i > pendulum.now()]

    if len(dts) == 1:
        return dts[0]
    elif len(dts) > 1:
        raise MatchMoreThenOne
    else:
        return False


async def parse(text):
    log.debug(f"{parse.__name__}: {locals()}")
    # парсим через внешнюю api с исправлением опечаток через yandex
    dt, parsed_text = await parse_by_markup_dusi(speller(text))
    if dt:
        return dt, parsed_text

    dt = get_datetime_by_pendulum(text)
    if dt:
        return dt, None

    try:
        dt = convert_to_pendulum(dateparser.parse(text, languages=["ru"]))
        if dt:
            return dt, None
    except Exception:
        pass

    tokens = text.split(" ")
    token_pairs = [f"{tokens[i - 1]} {tokens[i]}" for i in range(1, len(tokens))]
    token_pairs_through_one = [
        f"{tokens[i - 1]} {tokens[i + 1]}" for i in range(1, len(tokens) - 1)
    ]
    if len(tokens) >= 2:
        try:
            dt = parse_by_tokens(token_pairs)
            if dt:
                return dt, None
        except MatchMoreThenOne:
            log.warning("MatchMoreThenOne")
            pass

        token_pairs = [f"{tokens[i-1]} {tokens[i]}" for i in range(1, len(tokens))]
        try:
            dt = parse_by_tokens(tokens)
            if dt:
                return dt, None
        except MatchMoreThenOne:
            log.warning("MatchMoreThenOne")
            pass

        token_pairs_through_one = [
            f"{tokens[i-1]} {tokens[i+1]}" for i in range(1, len(tokens) - 1)
        ]
        try:
            dt = parse_by_tokens(token_pairs_through_one)
            if dt:
                return dt, None
        except MatchMoreThenOne:
            log.warning("MatchMoreThenOne")
            pass

    return False, None
