import abc
from urllib.parse import parse_qs, urlparse

from requests.models import Response

from .response import get_header_links


class PaginatorInterface(metaclass=abc.ABCMeta):
    @abc.abstractmethod
    def reset(self):
        pass

    @abc.abstractmethod
    def alter_request_params(self, reqp: dict) -> None:
        # reqp should be mutated directly
        pass

    @abc.abstractmethod
    def inspect_response(self, res: Response) -> None:
        pass

    @abc.abstractmethod
    def has_more(self) -> bool:
        pass


class LinkPaginator(PaginatorInterface):
    # Assumptions:
    # * page is passed as a query string argument
    # * next page is extracted from the Link (rel=next) header

    # If page size is configurable
    define_page_size: bool = False
    page_size_attr: str
    page_size: int

    page_num_start: int
    page_num_attr: str
    page_num: int

    # TODO: sanity check / limit of calls for pagination
    nb_dl: int

    keep_going: bool

    def __init__(
        self,
        page_num_attr: str,
        page_num_start: int = 0,
        page_size: int = None,
        page_size_attr: str = None,
    ):
        if (page_size is not None and page_size_attr is None) or (
            page_size is None and page_size_attr is not None
        ):
            raise Exception(
                "page_size_attr and page_size need to be both defined or both None"
            )
        if page_size is not None and page_size_attr is not None:
            self.define_page_size = True
            self.page_size = page_size
            self.page_size_attr = page_size_attr
        self.page_num_attr = page_num_attr
        self.page_num_start = page_num_start
        self.reset()

    def reset(self):
        self.page_num = self.page_num_start
        self.keep_going = True
        self.nb_dl = 0

    def alter_request_params(self, reqp: dict) -> None:
        # We add query string arguments (requests' "params")
        # Note that we mutate reqp directly
        p = {self.page_num_attr: self.page_num}
        if self.define_page_size:
            p.update({self.page_size_attr: self.page_size})

        if "params" in reqp:
            reqp["params"].update(p)
        else:
            reqp["params"] = p

    def inspect_response(self, res: Response) -> None:
        self.nb_dl += 1

        # See if there is another page to fetch
        next_link = get_header_links(res, rel="next")
        has_more = False
        if next_link:
            u = urlparse(next_link)
            # "query" will be an empty string if no query string args
            q = parse_qs(u.query)
            # note that values are always returned as lists, e.g. {'page': ['1'], 'size': ['50']}

            if self.page_num_attr in q and len(q[self.page_num_attr]) == 1:
                if int(q[self.page_num_attr][0]) <= self.page_num:
                    raise Exception(
                        'Found a link for next page={} (extracted from "{}"), but it is less or equal to the current page={}'.format(
                            q[self.page_num_attr][0],
                            res.headers.get("link"),
                            self.page_num,
                        )
                    )
                self.page_num = int(q[self.page_num_attr][0])
                has_more = True
        self.keep_going = has_more

    def has_more(self) -> bool:
        return self.keep_going
