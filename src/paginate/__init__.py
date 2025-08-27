"""
Modified by sky-cake for use in Ayase Quart with the following modifications:

- ported to quart
- removed current_app config extract
- bs4 styles only
- utf-8 only

flask_paginate
~~~~~~~~~~~~~~~~~~
Copyright (c) 2012 by Lix Xu.

Some rights reserved.

Redistribution and use in source and binary forms, with or without
modification, are permitted provided that the following conditions are
met:

* Redistributions of source code must retain the above copyright
  notice, this list of conditions and the following disclaimer.

* Redistributions in binary form must reproduce the above
  copyright notice, this list of conditions and the following
  disclaimer in the documentation and/or other materials provided
  with the distribution.

* The names of the contributors may not be used to endorse or
  promote products derived from this software without specific
  prior written permission.

THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
"AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR
A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT
OWNER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL,
SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT
LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE,
DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY
THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
(INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
"""

from markupsafe import Markup
from quart import request, url_for

PREV_PAGES = """<li class="page-item">
<a class="page-link" href="{0}" aria-label="Previous"{2}>
<span aria-hidden="true">{1}</span>
<span class="sr-only">Previous</span></a></li>"""

NEXT_PAGES = '''<li class="page-item">
<a class="page-link" href="{0}" aria-label="Next"{2}>
<span aria-hidden="true">{1}</span>
<span class="sr-only">Next</span></a></li>'''

CURRENT_PAGES = '''<li class="page-item active"><a class="page-link">{0}
<span class="sr-only">(current)</span></a></li>'''

LINK = '<li class="page-item"><a class="page-link" href="{0}">{1}</a></li>'

GAP_MARKERS = '<li class="page-item disabled"><span class="page-link">...</span></li>'

PREV_DISABLED_PAGES = '''<li class="page-item disabled"><span class="page-link"> {0}
</span></li>'''

NEXT_DISABLED_PAGES = '''<li class="page-item disabled"><span class="page-link"> {0}
</span></li>'''

PREV_LABEL = "&laquo;"
NEXT_LABEL = "&raquo;"
RECORD_NAME = "records"

DISPLAY_MSG = "displaying <b>{start} - {end}</b> {record_name} in \
total <b>{total}</b>"

SEARCH_MSG = "found <b>{found}</b> {record_name}, \
displaying <b>{start} - {end}</b>"

CSS_LINKS = '<nav aria-label="..."><ul class="pagination {0} {1}">'

CSS_LINKS_END = "</ul></nav>"


def get_parameter(param=None, args=None, default="page"):
    if not args:
        args = request.args.copy()
        args.update(request.view_args.copy())

    if not param:
        pk = "page_parameter" if default == "page" else "per_page_parameter"
        param = args.get(pk)

    return param or default


def get_page_parameter(param=None, args=None):
    return get_parameter(param, args, "page")


def get_per_page_parameter(param=None, args=None):
    return get_parameter(param, args, "per_page")


def get_page_args(
    page_parameter=None, per_page_parameter=None, for_test=False, **kwargs
):
    """param order: 1. passed parameter 2. request.args 3: config value
    for_test will return page_parameter and per_page_parameter"""
    args = request.args.copy()
    args.update(request.view_args.copy())

    page_name = get_page_parameter(page_parameter, args)
    per_page_name = get_per_page_parameter(per_page_parameter, args)
    for name in (page_name, per_page_name):
        if name in kwargs:
            args.setdefault(name, kwargs[name])

    if for_test:
        return page_name, per_page_name

    page = int(args.get(page_name, 1, type=int))
    per_page = args.get(per_page_name, type=int)
    if not per_page:
        per_page = 10
    else:
        per_page = int(per_page)

    offset = (page - 1) * per_page
    return page, per_page, offset


def get_param_value(name, kwargs={}, default=None, cfg_name="", prefix="pagination"):
    """Get parameter value from kwargs or config"""
    config_name = cfg_name or name
    if prefix:
        config_name = "{}_{}".format(prefix, config_name)

    return kwargs.get(name, default)


class Pagination(object):
    """A simple pagination extension for flask."""

    def __init__(self, found=0, **kwargs):
        """Detail parameters.

            **found**: used when searching

            **page**: current page

            **per_page**: how many records displayed on one page

            **page_parameter**: a name(string) of a GET parameter that holds \
            a page index, Use it if you want to iterate over multiple \
            Pagination objects simultaneously.
            default is 'page'.

            **per_page_parameter**: a name for per_page likes page_parameter.
            default is 'per_page'.

            **inner_window**: how many links around current page

            **outer_window**: how many links near first/last link

            **prev_label**: text for previous page, default is **&laquo;**

            **next_label**: text for next page, default is **&raquo;**

            **search**: search or not?

            **total**: total records for pagination

            **display_msg**: text for pagination information

            **search_msg**: text for search information

            **record_name**: record name showed in pagination information

            **link_size**: font size of page links

            **alignment**: the alignment of pagination links

            **href**: Add custom href for links - this supports forms \
            with post method. It MUST contain {0} to format page number

            **show_single_page**: decide whether or not a single page \
            returns pagination

            **anchor**: anchor parameter, appends to page href

            **format_total**: number format total, like **1,234**, \
            default is False

            **format_number**: number format start and end, like **1,234**, \
            default is False

            **prev_rel**: rel of previous page

            **next_rel**: rel of next page

            **include_first_page_number**: include 1 for first page or not

        """
        self.found = found
        page_parameter = kwargs.get("page_parameter")
        if not page_parameter:
            page_parameter = get_page_parameter()

        self.page_parameter = page_parameter
        self.page = int(kwargs.get(self.page_parameter, 1))

        if self.page < 1:
            self.page = 1

        per_page_param = kwargs.get("per_page_parameter")
        if not per_page_param:
            per_page_param = get_per_page_parameter()

        self.per_page_parameter = per_page_param
        self.per_page = int(
            get_param_value(per_page_param, kwargs, 10, cfg_name="per_page", prefix="")
        )
        self.is_disabled = self.per_page < 1
        self.skip = (self.page - 1) * self.per_page
        self.inner_window = int(get_param_value("inner_window", kwargs, 2))
        self.outer_window = int(get_param_value("outer_window", kwargs, 1))
        self.prev_label = get_param_value("prev_label", kwargs, PREV_LABEL)
        self.next_label = get_param_value("next_label", kwargs, NEXT_LABEL)
        self.search = kwargs.get("search", False)
        self.total = kwargs.get("total", 0)
        self.format_total = get_param_value("format_total", kwargs, False)
        self.format_number = get_param_value("format_number", kwargs, False)
        self.display_msg = get_param_value("display_msg", kwargs, DISPLAY_MSG)
        self.search_msg = get_param_value("search_msg", kwargs, SEARCH_MSG)
        self.record_name = get_param_value("record_name", kwargs, RECORD_NAME)

        self.link_size = get_param_value("link_size", kwargs, "")
        if self.link_size:
            self.link_size = " pagination-{0}".format(self.link_size)

        self.prev_rel = get_param_value("prev_rel", kwargs, "")
        if self.prev_rel:
            self.prev_rel = ' rel="{}"'.format(self.prev_rel)

        self.next_rel = get_param_value("next_rel", kwargs, "")
        if self.next_rel:
            self.next_rel = ' rel="{}"'.format(self.next_rel)

        self.alignment = get_param_value("alignment", kwargs, "")
        if self.alignment:
            if self.alignment == "center":
                self.alignment = " justify-content-center"
            elif self.alignment in ("right", "end"):
                self.alignment = " justify-content-end"

        self.href = kwargs.get("href")
        self.anchor = kwargs.get("anchor")
        self.show_single_page = get_param_value("show_single_page", kwargs, False)

        self.link = LINK
        self.current_page_fmt = CURRENT_PAGES
        self.link_css_fmt = CSS_LINKS
        self.gap_marker_fmt = GAP_MARKERS
        self.prev_disabled_page_fmt = PREV_DISABLED_PAGES
        self.next_disabled_page_fmt = NEXT_DISABLED_PAGES
        self.prev_page_fmt = PREV_PAGES
        self.next_page_fmt = NEXT_PAGES
        self.css_end_fmt = CSS_LINKS_END
        self.include_first_page_number = get_param_value(
            "include_first_page_number", kwargs, False
        )
        self.init_values()

    def page_href(self, page):
        if self.href:
            url = self.href.format(page or 1)
        else:
            self.args[self.page_parameter] = page
            if self.anchor:
                url = url_for(self.endpoint, _anchor=self.anchor, **self.args)
            else:
                url = url_for(self.endpoint, **self.args)

        return url

    def init_values(self):
        current_total = self.found if self.search else self.total
        if self.is_disabled:
            self.total_pages = 1
            self.has_prev = self.has_next = False
        else:
            pages = divmod(current_total, self.per_page)
            self.total_pages = pages[0] + 1 if pages[1] else pages[0]
            self.has_prev = self.page > 1
            self.has_next = self.page < self.total_pages

        args = request.args.copy()
        args.update(request.view_args.copy())
        self.args = {}
        for k, v in args.lists():
            if len(v) == 1:
                self.args[k] = v[0]
            else:
                self.args[k] = v

        self.endpoint = request.endpoint

    @property
    def prev_page(self):
        if self.has_prev:
            page = self.page - 1
            if self.page <= 2 and not self.include_first_page_number:
                page = None

            url = self.page_href(page)
            args = (url, self.prev_label, self.prev_rel)

            return self.prev_page_fmt.format(*args)

        return self.prev_disabled_page_fmt.format(self.prev_label)

    @property
    def next_page(self):
        if self.has_next:
            url = self.page_href(self.page + 1)
            args = (url, self.next_label, self.next_rel)

            return self.next_page_fmt.format(*args)

        return self.next_disabled_page_fmt.format(self.next_label)

    @property
    def first_page(self):
        # current page is first page
        if self.has_prev:
            if self.include_first_page_number:
                return self.link.format(self.page_href(1), 1)

            return self.link.format(self.page_href(None), 1)

        return self.current_page_fmt.format(1)

    @property
    def last_page(self):
        if self.has_next:
            url = self.page_href(self.total_pages)
            return self.link.format(url, self.total_pages)

        return self.current_page_fmt.format(self.page)

    @property
    def pages(self):
        if self.total_pages < self.inner_window * 2 - 1:
            return range(1, self.total_pages + 1)

        pages = []
        win_from = self.page - self.inner_window
        win_to = self.page + self.inner_window
        if win_to > self.total_pages:
            win_from -= win_to - self.total_pages
            win_to = self.total_pages

        if win_from < 1:
            win_to = win_to + 1 - win_from
            win_from = 1
            if win_to > self.total_pages:
                win_to = self.total_pages

        if win_from > self.inner_window:
            pages.extend(range(1, self.outer_window + 1 + 1))
            pages.append(None)
        else:
            pages.extend(range(1, win_to + 1))

        if win_to < self.total_pages - self.inner_window + 1:
            if win_from > self.inner_window:
                pages.extend(range(win_from, win_to + 1))

            pages.append(None)
            if self.outer_window == 0:
                pages.extend(range(self.total_pages, self.total_pages + 1))
            else:
                pages.extend(range(self.total_pages - 1, self.total_pages + 1))

        elif win_from > self.inner_window:
            pages.extend(range(win_from, self.total_pages + 1))
        else:
            pages.extend(range(win_to + 1, self.total_pages + 1))

        return pages

    def single_page(self, page):
        if page == self.page:
            return self.current_page_fmt.format(page)

        if page == 1:
            return self.first_page

        if page == self.total_pages:
            return self.last_page

        return self.link.format(self.page_href(page), page)

    def _get_single_page_link(self):
        s = [self.link_css_fmt.format(self.link_size, self.alignment)]
        s.append(self.prev_page)
        s.append(self.single_page(1))
        s.append(self.next_page)
        s.append(self.css_end_fmt)

        return Markup("".join(s))

    @property
    def links(self):
        """Get all the pagination links."""
        if self.total_pages <= 1:
            if self.show_single_page:
                return self._get_single_page_link()

            return ""

        s = [self.link_css_fmt.format(self.link_size, self.alignment)]
        s.append(self.prev_page)
        for page in self.pages:
            s.append(self.single_page(page) if page else self.gap_marker_fmt)

        s.append(self.next_page)
        s.append(self.css_end_fmt)

        return Markup("".join(s))

    @property
    def info(self):
        """Get the pagination information."""
        s = ['<div class="pagination-page-info">']
        page_msg = self.search_msg if self.search else self.display_msg
        if self.format_total:
            total_text = "{0:,}".format(self.total)
        else:
            total_text = "{0}".format(self.total)

        if self.is_disabled:
            start = 1
            end = self.found if self.search else self.total
        else:
            start = 1 + (self.page - 1) * self.per_page
            end = start + self.per_page - 1
            if end > self.total:
                end = self.found if self.search else self.total

            if start > self.total:
                start = self.found if self.search else self.total

        if self.format_number:
            start_text = "{0:,}".format(start)
            end_text = "{0:,}".format(end)
        else:
            start_text = start
            end_text = end

        s.append(
            page_msg.format(
                found=self.found,
                total=total_text,
                start=start_text,
                end=end_text,
                record_name=self.record_name,
            )
        )
        s.append("</div>")
        return Markup("".join(s))
