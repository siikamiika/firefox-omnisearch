#!/usr/bin/env python3

import os
import glob
import json
from http.server import BaseHTTPRequestHandler, HTTPServer
from socketserver import ThreadingMixIn
from urllib.parse import urlencode, urlparse, parse_qs
import requests

USER_AGENT_STRING = 'Mozilla/5.0 (X11; Linux x86_64; rv:57.0) Gecko/20100101 Firefox/57.0'

class SearchEngine(object):

    def __init__(self, keyword, definition):
        self.keyword = keyword
        self.definition = definition
        self._parse_definition()

    def _parse_definition(self):
        definition = json.loads(self.definition)

        self.search_url = definition['search']['url']
        self.search_params = definition['search']['params']

        self.suggestions_url = definition['suggestions']['url']
        self.suggestions_params = definition['suggestions']['params']
        if definition['suggestions']['parser']:
            self.suggestions_parser = self._load_suggestions_parser()
        else:
            self.suggestions_parser = lambda s, p: self._default_suggestions_parser(s, p)

    def _load_suggestions_parser(self):
        raise NotImplementedError('Parsing suggestions is not implemented.')

    def _default_suggestions_parser(self, suggestions, prepend_keyword):
        if prepend_keyword:
            suggestions = json.loads(suggestions, encoding='utf-8')
            suggestions[0] = '{} {}'.format(self.keyword, suggestions[0])
            suggestions[1] = ['{} {}'.format(self.keyword, s) for s in suggestions[1]]
            return json.dumps(suggestions, ensure_ascii=False).encode('utf-8')
        else:
            return suggestions

    def get_suggestions(self, query, prepend_keyword=True):
        params = dict(self.suggestions_params)
        for key in params:
            params[key] = params[key].format(query=query)

        url = '{}?{}'.format(self.suggestions_url, urlencode(params))
        response = requests.get(url, headers={'User-Agent': USER_AGENT_STRING})

        return self.suggestions_parser(response.content, prepend_keyword)

    def get_search_url(self, query):
        params = dict(self.search_params)
        for key in params:
            params[key] = params[key].format(query=query)

        return '{}?{}'.format(self.search_url, urlencode(params))


class SearchEngineRouter(object):

    def __init__(self, search_engine_directory):
        self.search_engine_directory = search_engine_directory
        self.search_engines = {}
        self.default_search_engine = None
        self._load_search_engines()

    def _load_search_engines(self):
        pattern = os.path.join(self.search_engine_directory, '*.json')
        for filename in glob.glob(pattern):
            keyword = os.path.basename(filename)[:-5]

            if keyword[-8:] == '.default':
                keyword = keyword[:-8]
                self.default_search_engine = keyword
            elif not self.default_search_engine:
                self.default_search_engine = keyword

            with open(filename) as f:
                self.search_engines[keyword] = SearchEngine(keyword, f.read())

    def get_suggestions(self, query):
        arguments = query.split(' ')

        if len(arguments) < 2:
            return self.search_engines[self.default_search_engine].get_suggestions(query, prepend_keyword=False)
        else:
            if arguments[0] not in self.search_engines:
                return self.search_engines[self.default_search_engine].get_suggestions(query, prepend_keyword=False)
            else:
                return self.search_engines[arguments[0]].get_suggestions(' '.join(arguments[1:]))

    def get_search_url(self, query):
        arguments = query.split(' ')

        if len(arguments) < 2:
            return self.search_engines[self.default_search_engine].get_search_url(query)
        else:
            if arguments[0] not in self.search_engines:
                return self.search_engines[self.default_search_engine].get_search_url(query)
            else:
                return self.search_engines[arguments[0]].get_search_url(' '.join(arguments[1:]))


class FirefoxSearchServer(ThreadingMixIn, HTTPServer):

    def set_router(self, router):
        self.router = router

class FirefoxSearchRequestHandler(BaseHTTPRequestHandler):

    protocol_version = 'HTTP/1.1'

    def log_message(self, fmt, *args):
        pass

    def redirect(self, location):
        self.send_response(302)
        self.send_header('Location', location)
        self.send_header('Content-Length', 0)
        self.end_headers()

    def respond_ok(self, data=b'', content_type='text/html; charset=utf-8', age=0):
        self.send_response(200)
        self.send_header('Cache-Control', 'public, max-age={}'.format(age))
        self.send_header('Content-Type', content_type)
        self.send_header('Content-Length', len(data))
        self.end_headers()
        self.wfile.write(data)

    def respond_notfound(self, data='404'.encode()):
        self.send_response(404)
        self.send_header('Content-Type', 'text/plain')
        self.send_header('Content-Length', len(data))
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self):
        url = urlparse(self.path)
        query = parse_qs(url.query)

        self._handle_request(url, query)

    def do_POST(self):
        url = urlparse(self.path)
        content_length = int(self.headers.get('Content-Length') or 0)
        self.post_data = self.rfile.read(content_length)
        query = parse_qs(self.post_data.decode('utf-8'))

        self._handle_request(url, query)

    def _handle_request(self, url, query):
        if url.path == '/search':
            search_url = self.server.router.get_search_url(query['q'][0])
            self.redirect(search_url)
        elif url.path == '/suggestions':
            suggestions = self.server.router.get_suggestions(query['q'][0])
            self.respond_ok(data=suggestions, content_type='application/json; charset=utf-8')
        else:
            self.respond_notfound()


def main():
    server = FirefoxSearchServer(('127.0.0.1', 9881), FirefoxSearchRequestHandler)
    server.set_router(SearchEngineRouter('engines'))
    server.serve_forever()

if __name__ == '__main__':
    main()
