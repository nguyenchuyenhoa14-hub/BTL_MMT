#
# Copyright (C) 2026 pdnguyen of HCMC University of Technology VNU-HCM.
# All rights reserved.
# This file is part of the CO3093/CO3094 course.
#
# AsynApRous release
#
# The authors hereby grant to Licensee personal permission to use
# and modify the Licensed Source Code for the sole purpose of studying
# while attending the course
#

"""
daemon.response
~~~~~~~~~~~~~~~~~

This module provides a :class: `Response <Response>` object to manage and persist
response settings (cookies, auth, proxies), and to construct HTTP responses
based on incoming requests.

The current version supports MIME type detection, content loading and header formatting
"""
import datetime
import os
import json
import mimetypes
from .dictionary import CaseInsensitiveDict

BASE_DIR = ""

class Response():
    """The :class:`Response <Response>` object, which contains a
    server's response to an HTTP request.

    Instances are generated from a :class:`Request <Request>` object, and
    should not be instantiated manually; doing so may produce undesirable
    effects.

    :class:`Response <Response>` object encapsulates headers, content,
    status code, cookies, and metadata related to the request-response cycle.
    It is used to construct and serve HTTP responses in a custom web server.

    :attrs status_code (int): HTTP status code (e.g., 200, 404).
    :attrs headers (dict): dictionary of response headers.
    :attrs url (str): url of the response.
    :attrs encoding (str): encoding used for decoding response content.
    :attrs history (list): list of previous Response objects (for redirects).
    :attrs reason (str): textual reason for the status code (e.g., "OK", "Not Found").
    :attrs cookies (CaseInsensitiveDict): response cookies.
    :attrs elapsed (datetime.timedelta): time taken to complete the request.
    :attrs request (PreparedRequest): the original request object.

    Usage::

      >>> import Response
      >>> resp = Response()
      >>> resp.build_response(req)
      >>> resp
      <Response>
    """

    __attrs__ = [
        "_content",
        "_header",
        "status_code",
        "method",
        "headers",
        "url",
        "history",
        "encoding",
        "reason",
        "cookies",
        "elapsed",
        "request",
        "body",
        "reason",
    ]


    def __init__(self, request=None):
        """
        Initializes a new :class:`Response <Response>` object.

        : params request : The originating request object.
        """

        self._content = b""
        self._content_consumed = False
        self._next = None
        self._header = b""

        #: Integer Code of responded HTTP Status, e.g. 404 or 200.
        self.status_code = 200

        #: Case-insensitive Dictionary of Response Headers.
        #: For example, ``headers['content-type']`` will return the
        #: value of a ``'Content-Type'`` response header.
        self.headers = {}

        #: URL location of Response.
        self.url = None

        #: Encoding to decode with when accessing response text.
        self.encoding = None

        #: A list of :class:`Response <Response>` objects from
        #: the history of the Request.
        self.history = []

        #: Textual reason of responded HTTP Status, e.g. "Not Found" or "OK".
        self.reason = "OK"

        #: A of Cookies the response headers.
        self.cookies = CaseInsensitiveDict()

        #: The amount of time elapsed between sending the request
        self.elapsed = datetime.timedelta(0)

        #: The :class:`PreparedRequest <PreparedRequest>` object to which this
        #: is a response.
        self.request = None

        #: Extra Set-Cookie headers to include
        self.set_cookies = {}


    def get_mime_type(self, path):
        """
        Determines the MIME type of a file based on its path.

        "params path (str): Path to the file.

        :rtype str: MIME type string (e.g., 'text/html', 'image/png').
        """

        try:
            mime_type, _ = mimetypes.guess_type(path)
        except Exception:
            return 'application/octet-stream'
        return mime_type or 'application/octet-stream'


    def prepare_content_type(self, mime_type='text/html'):
        """
        Prepares the Content-Type header and determines the base directory
        for serving the file based on its MIME type.

        :params mime_type (str): MIME type of the requested resource.

        :rtype str: Base directory path for locating the resource.

        :raises ValueError: If the MIME type is unsupported.
        """

        base_dir = ""

        # Validate header attr existence
        if not hasattr(self, "headers") or self.headers is None:
            self.headers = {}

        # Processing mime_type based on main_type and sub_type
        main_type, sub_type = mime_type.split('/', 1)
        print("[Response] Processing main_type={} sub_type={}".format(main_type,sub_type))
        if main_type == 'text':
            self.headers['Content-Type']='text/{}'.format(sub_type)
            if sub_type == 'plain' or sub_type == 'css':
                base_dir = BASE_DIR+"static/"
            elif sub_type == 'html':
                base_dir = BASE_DIR+"www/"
            else:
                base_dir = BASE_DIR+"static/"
        elif main_type == 'image':
            base_dir = BASE_DIR+"static/"
            self.headers['Content-Type']='image/{}'.format(sub_type)
        elif main_type == 'application':
            if sub_type == 'javascript':
                base_dir = BASE_DIR+"static/"
            else:
                base_dir = BASE_DIR+"apps/"
            self.headers['Content-Type']='application/{}'.format(sub_type)
        elif main_type == 'video':
            base_dir = BASE_DIR+"static/"
            self.headers['Content-Type']='video/{}'.format(sub_type)
        elif main_type == 'audio':
            base_dir = BASE_DIR+"static/"
            self.headers['Content-Type']='audio/{}'.format(sub_type)
        else:
            base_dir = BASE_DIR+"static/"
            self.headers['Content-Type'] = mime_type

        return base_dir


    def build_content(self, path, base_dir):
        """
        Loads the objects file from storage space.

        :params path (str): relative path to the file.
        :params base_dir (str): base directory where the file is located.

        :rtype tuple: (int, bytes) representing content length and content data.
        """

        filepath = os.path.join(base_dir, path.lstrip('/'))

        print("[Response] Serving the object at location {}".format(filepath))
        try:
            with open(filepath, "rb") as f:
               content = f.read()
        except FileNotFoundError:
            print("[Response] File not found: {}".format(filepath))
            return -1, b""
        except Exception as e:
            print("[Response] build_content exception: {}".format(e))
            return -1, b""
        return len(content), content


    def build_response_header(self, request, content_length=0):
        """
        Constructs the HTTP response headers based on the class:`Request <Request>
        and internal attributes.

        :params request (class:`Request <Request>`): incoming request object.
        :params content_length (int): Length of the response body.

        :rtypes bytes: encoded HTTP response header.
        """
        # Status line
        status_line = "HTTP/1.1 {} {}".format(self.status_code, self.reason)

        # Build header lines
        header_lines = [status_line]

        # Content-Type
        content_type = self.headers.get('Content-Type', 'text/html')
        header_lines.append("Content-Type: {}".format(content_type))

        # Content-Length
        header_lines.append("Content-Length: {}".format(content_length))

        # Date
        header_lines.append("Date: {}".format(
            datetime.datetime.utcnow().strftime("%a, %d %b %Y %H:%M:%S GMT")
        ))

        # Cache-Control
        header_lines.append("Cache-Control: no-cache")

        # Connection
        header_lines.append("Connection: close")

        # Server
        header_lines.append("Server: AsynapRous/1.0")

        # Set-Cookie headers
        for cookie_name, cookie_value in self.set_cookies.items():
            header_lines.append("Set-Cookie: {}={}; Path=/; HttpOnly".format(
                cookie_name, cookie_value
            ))

        # WWW-Authenticate header (for 401 responses)
        if self.status_code == 401:
            header_lines.append('WWW-Authenticate: Basic realm="AsynapRous Server"')

        # Additional custom headers
        for key, value in self.headers.items():
            if key not in ('Content-Type', 'Content-Length'):
                header_lines.append("{}: {}".format(key, value))

        # Join with CRLF and add blank line to separate from body
        fmt_header = "\r\n".join(header_lines) + "\r\n\r\n"

        return fmt_header.encode('utf-8')


    def build_notfound(self):
        """
        Constructs a standard 404 Not Found HTTP response.

        :rtype bytes: Encoded 404 response.
        """

        body = "404 Not Found"
        return (
                "HTTP/1.1 404 Not Found\r\n"
                "Accept-Ranges: bytes\r\n"
                "Content-Type: text/html\r\n"
                "Content-Length: {}\r\n"
                "Cache-Control: max-age=86000\r\n"
                "Connection: close\r\n"
                "\r\n"
                "{}".format(len(body), body)
            ).encode('utf-8')


    def build_unauthorized(self):
        """
        Constructs a 401 Unauthorized HTTP response.

        :rtype bytes: Encoded 401 response.
        """
        body = "401 Unauthorized - Please provide valid credentials"
        return (
                "HTTP/1.1 401 Unauthorized\r\n"
                "Content-Type: text/html\r\n"
                "Content-Length: {}\r\n"
                'WWW-Authenticate: Basic realm="AsynapRous Server"\r\n'
                "Connection: close\r\n"
                "\r\n"
                "{}".format(len(body), body)
            ).encode('utf-8')


    def build_json_response_bytes(self, data, status_code=200, reason="OK",
                                  cookies=None):
        """
        Builds a complete HTTP response with JSON body.

        :params data: dict or bytes to send as JSON body.
        :params status_code (int): HTTP status code.
        :params reason (str): HTTP reason phrase.
        :params cookies (dict): Optional cookies to set.

        :rtype bytes: Complete HTTP response.
        """
        if isinstance(data, dict):
            body = json.dumps(data).encode('utf-8')
        elif isinstance(data, str):
            body = data.encode('utf-8')
        elif isinstance(data, bytes):
            body = data
        else:
            body = str(data).encode('utf-8')

        # Build header
        header_lines = [
            "HTTP/1.1 {} {}".format(status_code, reason),
            "Content-Type: application/json",
            "Content-Length: {}".format(len(body)),
            "Date: {}".format(
                datetime.datetime.utcnow().strftime("%a, %d %b %Y %H:%M:%S GMT")
            ),
            "Connection: close",
            "Server: AsynapRous/1.0",
        ]

        # Add Set-Cookie headers
        if cookies:
            for name, value in cookies.items():
                header_lines.append(
                    "Set-Cookie: {}={}; Path=/; HttpOnly".format(name, value)
                )

        header = "\r\n".join(header_lines) + "\r\n\r\n"
        return header.encode('utf-8') + body


    def build_response(self, request, envelop_content=None):
        """
        Builds a full HTTP response including headers and content based on the request.

        :params request (class:`Request <Request>`): incoming request object.
        :params envelop_content: Optional pre-built content.

        :rtype bytes: complete HTTP response using prepared headers and content.
        """
        print("[Response] Start build response with req {}".format(request))

        path = request.path

        if path is None:
            return self.build_notfound()

        mime_type = self.get_mime_type(path)
        print("[Response] {} path {} mime_type {}".format(request.method, request.path, mime_type))

        base_dir = ""

        # If HTML, parse and serve embedded objects
        if path.endswith('.html') or mime_type == 'text/html':
            base_dir = self.prepare_content_type(mime_type='text/html')
        elif mime_type == 'text/css':
            base_dir = self.prepare_content_type(mime_type='text/css')
        elif mime_type == 'text/javascript' or mime_type == 'application/javascript':
            base_dir = self.prepare_content_type(mime_type='application/javascript')
        elif mime_type.startswith('image/'):
            base_dir = self.prepare_content_type(mime_type=mime_type)
        elif mime_type == 'application/json' or mime_type == 'application/octet-stream':
            base_dir = self.prepare_content_type(mime_type='application/json')
            if envelop_content:
                # Use provided content (e.g., from hook handler)
                self._content = envelop_content if isinstance(envelop_content, bytes) else envelop_content.encode('utf-8')
                self._header = self.build_response_header(request, len(self._content))
                return self._header + self._content
        else:
            # Try to serve as generic file
            base_dir = self.prepare_content_type(mime_type=mime_type)

        # Load content from file
        content_length, content = self.build_content(path, base_dir)

        if content_length == -1:
            return self.build_notfound()

        self._content = content
        self.status_code = 200
        self.reason = "OK"
        self._header = self.build_response_header(request, content_length)

        return self._header + self._content
