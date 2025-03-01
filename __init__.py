# -*- coding: utf-8 ts=4 sw=4 sts=4 et -*-
from __future__ import (absolute_import, print_function, unicode_literals)

from calibre import browser
from calibre.gui2 import open_url
from calibre.gui2.store.search_result import SearchResult
from calibre.gui2.store.web_store_dialog import WebStoreDialog

from six.moves import urllib

from contextlib import closing
from lxml import html
from PyQt5.Qt import QUrl
from urllib.parse import urljoin

class GenericStore():
    external_only      = False
    url                = None
    search_url         = None
    words_drm_locked   = ['drm']
    words_drm_unlocked = []

    def search(self, query, max_results, timeout):
        url = self.search_url.format(self.url, self.quote(query), max_results)
        br = browser()
        with closing(br.open(url, timeout=timeout)) as f:
            doc = html.fromstring(f.read())
            
            # if there's a perfect hit, some stores redirect to the result
            if url != f.geturl():
                r = SearchResult()
                r.detail_item = f.geturl()
                r.title       = '...'
                return [ r ]

            results = []
            for r in self.find_search_results(doc):
                result = self.parse_search_result(r)
                result = self.normalize(result)
                results.append(result)
            return results

    def get_details(self, result, timeout):
        if not self.needs_details(result):
            return False

        url = self.item_to_url(result.detail_item)
        br = browser()
        with closing(br.open(url, timeout=timeout)) as f:
            doc = html.fromstring(f.read())

            details = self.find_book_details(doc)
            r = self.parse_book_details(details)
            if not r:
                return False
            else:
                r = self.normalize(r)
            
            result.title     = r.title if r.title else result.title
            result.author    = r.author if r.author else result.author
            result.price     = r.price if r.price else result.price
            result.cover_url = r.cover_url if r.cover_url else result.cover_url
            result.formats   = r.formats if r.formats else result.formats
            result.drm       = r.drm if r.drm else result.drm
            return True

    def open(self, name, gui, parent, item, external):
        url = self.item_to_url(item)
        if external or self.external_only:
            open_url(QUrl(url))
        else:
            d = WebStoreDialog(gui, self.url, parent, url)
            d.setWindowTitle(name)
            d.exec_()

    def quote(self, query):
        return urllib.parse.quote_plus(query)

    def find_search_results(self, doc):
        return self.find_book_details(doc)
    
    def parse_search_result(self, node):
        raise NotImplementedError()
    
    def find_book_details(self, doc):
        node = xpath(doc, '//*[@itemtype="http://schema.org/Book"]')
        if len(node) > 0:
            return node[0]
        raise NotImplementedError()
    
    def parse_book_details(self, node):
        raise NotImplementedError()

    def create_browser(self):
        br = browser()
        br.addheaders[('Referer', self.url)]
        return browser

    def needs_details(self, result):
        return not result \
               or not result.title or result.title == '...' \
               or not result.author \
               or not result.price \
               or not result.cover_url \
               or not result.formats \
               or not result.drm

    def item_to_url(self, item):
        if not item:
            return None
        return urljoin(self.url, item)

    def normalize(self, result):
        if not result:
            return None
        if result.cover_url:
            result.cover_url = self.item_to_url(result.cover_url)
        if result.author:
            result.author = self.normalize_author(result.author)
        if result.formats:
            result.formats = self.normalize_formats(result.formats)
        if result.drm and not isinstance(result.drm, int):
            result.drm = self.normalize_drm(result.drm)
        return result

    def normalize_author(self, text):
        return text

    def normalize_formats(self, text):
        return text.strip().upper()

    def normalize_drm(self, text):
        words = text.strip().lower().split()
        for word in self.words_drm_locked:
            if word in words:
                return SearchResult.DRM_LOCKED
        for word in self.words_drm_unlocked:
            if word in words:
                return SearchResult.DRM_UNLOCKED
        return SearchResult.DRM_UNKNOWN

def xpath(node, elem, cls='', suffix=''):
    if cls:
        xpath = '{0}[contains(@class, "{1}")]{2}'.format(elem, cls, suffix)
    else:
        xpath = '{0}{1}'.format(elem, suffix)
    return node.xpath(xpath)

def text(node, elem, cls='', suffix='//text()'):
    value = xpath(node, elem, cls, suffix)
    value = ''.join(value).replace('\r\n', ' ').strip()
    return value


