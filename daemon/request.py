#
# Copyright (C) 2026 pdnguyen of HCMC University of Technology VNU-HCM.
# All rights reserved.
# This file is part of the CO3093/CO3094 course.
#
# AsynapRous release
#
# The authors hereby grant to Licensee personal permission to use
# and modify the Licensed Source Code for the sole purpose of studying
# while attending the course
#

"""
daemon.request
~~~~~~~~~~~~~~~~~

This module provides a Request object to manage and persist
request settings (cookies, auth, proxies).
"""
from .dictionary import CaseInsensitiveDict
import base64

class Request():
    """The fully mutable "class" `Request <Request>` object,
    containing the exact bytes that will be sent to the server.

    Instances are generated from a "class" `Request <Request>` object, and
    should not be instantiated manually; doing so may produce undesirable
    effects.

    Usage::

      >>> import deamon.request
      >>> req = request.Request()
      ## Incoming message obtain aka. incoming_msg
      >>> r = req.prepare(incoming_msg)
      >>> r
      <Request>
    """
    __attrs__ = [
        "method",
        "url",
        "headers",
        "body",
        "_raw_headers",
        "_raw_body",
        "reason",
        "cookies",
        "body",
        "routes",
        "hook",
    ]

    def __init__(self):
        #: HTTP verb to send to the server.
        self.method = None
        #: HTTP URL to send the request to.
        self.url = None
        #: dictionary of HTTP headers.
        self.headers = {}
        #: HTTP path
        self.path = None
        #: HTTP version
        self.version = None
        # The cookies set used to create Cookie header
        self.cookies = {}
        #: request body to send to the server.
        self.body = None
        # The raw header
        self._raw_headers = None
        #: The raw body
        self._raw_body = None
        #: Routes
        self.routes = {}
        #: Hook point for routed mapped-path
        self.hook = None
        #: Authentication info
        self.auth = None

    def extract_request_line(self, request):
        """Extract HTTP method, path, and version from the request line.

        :param request (str): Raw HTTP request string.
        :rtype: tuple (method, path, version) or (None, None, None).
        """
        try:
            lines = request.splitlines()
            first_line = lines[0]
            method, path, version = first_line.split()

            if path == '/':
                path = '/index.html'
        except Exception:
            return None, None, None

        return method, path, version

    def prepare_headers(self, request):
        """Prepares the given HTTP headers.

        :param request (str): Raw HTTP request string.
        :rtype: dict of header key-value pairs.
        """
        lines = request.split('\r\n')
        headers = {}
        for line in lines[1:]:
            if ': ' in line:
                key, val = line.split(': ', 1)
                headers[key.lower()] = val
        return headers

    def fetch_headers_body(self, request):
        """Splits raw HTTP request into header and body sections.

        :param request (str): Raw HTTP request string.
        :rtype: tuple (_headers, _body) strings.
        """
        # Split request into header section and body section
        parts = request.split("\r\n\r\n", 1)  # split once at blank line

        _headers = parts[0]
        _body = parts[1] if len(parts) > 1 else ""
        return _headers, _body

    def prepare(self, request, routes=None):
        """Prepares the entire request with the given parameters.

        :param request (str): Raw HTTP request string.
        :param routes (dict): Route mapping for webapp hooks.
        """
        if not request or not request.strip():
            self.method = None
            self.path = None
            self.version = None
            return

        # Prepare the request line from the request header
        print("[Request] prepare request msg {}".format(request[:200]))
        self.method, self.path, self.version = self.extract_request_line(request)
        print("[Request] {} path {} version {}".format(self.method, self.path, self.version))

        if self.method is None:
            return

        # Parse headers and body
        self._raw_headers, self._raw_body = self.fetch_headers_body(request)
        self.headers = self.prepare_headers(request)
        self.body = self._raw_body

        # Parse cookies from header
        cookie_str = self.headers.get('cookie', '')
        if cookie_str:
            self.cookies = self.parse_cookies(cookie_str)
        else:
            self.cookies = {}

        # Parse authentication from header
        auth_header = self.headers.get('authorization', '')
        if auth_header:
            self.auth = self.parse_auth(auth_header)

        #
        # @bksysnet Preparing the webapp hook with AsynapRous instance
        # The default behaviour with HTTP server is empty routed
        #
        if routes and routes != {}:
            self.routes = routes
            print("[Request] Routing METHOD {} path {}".format(self.method, self.path))
            self.hook = routes.get((self.method, self.path))
            print("[Request] Hook found: {}".format(self.hook))

        return

    def parse_cookies(self, cookie_str):
        """Parse cookies from Cookie header string.

        :param cookie_str (str): Cookie header value.
        :rtype: dict of cookie key-value pairs.
        """
        cookies = {}
        try:
            for pair in cookie_str.split(';'):
                pair = pair.strip()
                if '=' in pair:
                    key, value = pair.split('=', 1)
                    cookies[key.strip()] = value.strip()
        except Exception:
            pass
        return cookies

    def parse_auth(self, auth_header):
        """Parse Authorization header.

        Supports Basic authentication scheme (RFC 2617).

        :param auth_header (str): Authorization header value.
        :rtype: tuple (username, password) or None.
        """
        try:
            if auth_header.lower().startswith('basic '):
                encoded = auth_header.split(' ', 1)[1]
                decoded = base64.b64decode(encoded).decode('utf-8')
                username, password = decoded.split(':', 1)
                return (username, password)
        except Exception:
            pass
        return None

    def prepare_body(self, data, files=None, json=None):
        """Prepare request body content.

        :param data: Body data.
        :param files: File attachments (optional).
        :param json: JSON data (optional).
        """
        self.body = data
        if self.body:
            self.prepare_content_length(self.body)
        return

    def prepare_content_length(self, body):
        """Set Content-Length header based on body size.

        :param body: Body content.
        """
        if body:
            self.headers["Content-Length"] = str(len(body))
        else:
            self.headers["Content-Length"] = "0"
        return

    def prepare_auth(self, auth, url=""):
        """Prepare request authentication.

        :param auth (tuple): (username, password) tuple.
        :param url (str): Target URL.
        """
        if auth and len(auth) == 2:
            username, password = auth
            credentials = base64.b64encode(
                "{}:{}".format(username, password).encode('utf-8')
            ).decode('utf-8')
            self.headers["Authorization"] = "Basic {}".format(credentials)
            self.auth = auth
        return

    def prepare_cookies(self, cookies):
        """Set Cookie header from cookies dict.

        :param cookies (dict or str): Cookie data.
        """
        if isinstance(cookies, dict):
            cookie_str = '; '.join(
                '{}={}'.format(k, v) for k, v in cookies.items()
            )
            self.headers["Cookie"] = cookie_str
        elif isinstance(cookies, str):
            self.headers["Cookie"] = cookies
