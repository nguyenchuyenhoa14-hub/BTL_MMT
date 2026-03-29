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
daemon.httpadapter
~~~~~~~~~~~~~~~~~

This module provides a http adapter object to manage and persist
http settings (headers, bodies). The adapter supports both
raw URL paths and RESTful route definitions, and integrates with
Request and Response objects to handle client-server communication.
"""

from .request import Request
from .response import Response
from .dictionary import CaseInsensitiveDict

import asyncio
import inspect
import json

class HttpAdapter:
    """
    A mutable :class:`HTTP adapter <HTTP adapter>` for managing client connections
    and routing requests.

    The `HttpAdapter` class encapsulates the logic for receiving HTTP requests,
    dispatching them to appropriate route handlers, and constructing responses.
    It supports RESTful routing via hooks and integrates with :class:`Request <Request>`
    and :class:`Response <Response>` objects for full request lifecycle management.

    Attributes:
        ip (str): IP address of the client.
        port (int): Port number of the client.
        conn (socket): Active socket connection.
        connaddr (tuple): Address of the connected client.
        routes (dict): Mapping of route paths to handler functions.
        request (Request): Request object for parsing incoming data.
        response (Response): Response object for building and sending replies.
    """

    __attrs__ = [
        "ip",
        "port",
        "conn",
        "connaddr",
        "routes",
        "request",
        "response",
    ]

    def __init__(self, ip, port, conn, connaddr, routes):
        """
        Initialize a new HttpAdapter instance.

        :param ip (str): IP address of the client.
        :param port (int): Port number of the client.
        :param conn (socket): Active socket connection.
        :param connaddr (tuple): Address of the connected client.
        :param routes (dict): Mapping of route paths to handler functions.
        """

        #: IP address.
        self.ip = ip
        #: Port.
        self.port = port
        #: Connection
        self.conn = conn
        #: Connection address
        self.connaddr = connaddr
        #: Routes
        self.routes = routes if routes else {}
        #: Request
        self.request = Request()
        #: Response
        self.response = Response()

    def handle_client(self, conn, addr, routes):
        """
        Handle an incoming client connection.

        This method reads the request from the socket, prepares the request object,
        invokes the appropriate route handler if available, builds the response,
        and sends it back to the client.

        :param conn (socket): The client socket connection.
        :param addr (tuple): The client's address.
        :param routes (dict): The route mapping for dispatching requests.
        """

        # Connection handler.
        self.conn = conn
        # Connection address.
        self.connaddr = addr
        # Request handler
        req = self.request
        # Response handler
        resp = self.response

        try:
            # Handle the request
            msg_bytes = b""
            while b"\r\n\r\n" not in msg_bytes:
                chunk = conn.recv(4096)
                if not chunk:
                    break
                msg_bytes += chunk

            if not msg_bytes:
                conn.close()
                return

            headers_part = msg_bytes.split(b"\r\n\r\n")[0]
            body_part = msg_bytes[len(headers_part)+4:]

            content_length = 0
            for line in headers_part.split(b"\r\n"):
                if line.lower().startswith(b"content-length:"):
                    try:
                        content_length = int(line.split(b":")[1].strip())
                    except:
                        pass

            while len(body_part) < content_length:
                chunk = conn.recv(4096)
                if not chunk:
                    break
                body_part += chunk
                msg_bytes += chunk

            msg = msg_bytes.decode('utf-8', errors='replace')
            req.prepare(msg, routes)
            print("[HttpAdapter] Invoke handle_client connection {}".format(addr))

            if req.method is None:
                conn.sendall(resp.build_notfound())
                conn.close()
                return

            # Handle request hook (AsynapRous webapp route)
            if req.hook:
                print("[HttpAdapter] Dispatching to hook: {}".format(req.hook))
                try:
                    # Call the route handler with headers and body
                    if inspect.iscoroutinefunction(req.hook):
                        # Run async hook in event loop
                        loop = asyncio.new_event_loop()
                        result = loop.run_until_complete(
                            req.hook(headers=req._raw_headers, body=req.body)
                        )
                        loop.close()
                    else:
                        result = req.hook(headers=req._raw_headers, body=req.body)

                    # Build JSON response from hook result
                    if isinstance(result, bytes):
                        response = resp.build_json_response_bytes(
                            result.decode('utf-8') if result else '{}',
                            cookies=resp.set_cookies
                        )
                    elif isinstance(result, dict):
                        response = resp.build_json_response_bytes(
                            result,
                            cookies=resp.set_cookies
                        )
                    elif isinstance(result, str):
                        response = resp.build_json_response_bytes(
                            result,
                            cookies=resp.set_cookies
                        )
                    else:
                        response = resp.build_json_response_bytes(
                            {"message": "OK"},
                            cookies=resp.set_cookies
                        )
                except Exception as e:
                    print("[HttpAdapter] Hook error: {}".format(e))
                    import traceback
                    traceback.print_exc()
                    response = resp.build_json_response_bytes(
                        {"error": str(e)},
                        status_code=500,
                        reason="Internal Server Error"
                    )
            else:
                # No hook - serve static file
                response = resp.build_response(req)

            conn.sendall(response)
        except Exception as e:
            print("[HttpAdapter] Error handling client {}: {}".format(addr, e))
            import traceback
            traceback.print_exc()
            try:
                conn.sendall(resp.build_notfound())
            except Exception:
                pass
        finally:
            try:
                conn.close()
            except Exception:
                pass

    async def handle_client_coroutine(self, reader, writer):
        """
        Handle an incoming client connection using stream reader writer asynchronously.

        This method reads the request from the socket, prepares the request object,
        invokes the appropriate route handler if available, builds the response,
        and sends it back to the client.

        :param reader (StreamReader): Async stream reader.
        :param writer (StreamWriter): Async stream writer.
        """
        # Request handler
        req = self.request
        # Response handler
        resp = self.response

        addr = writer.get_extra_info("peername")
        print("[HttpAdapter] Invoke handle_client_coroutine connection {}".format(addr))

        try:
            # Handle the request asynchronously
            msg_bytes = b""
            while b"\r\n\r\n" not in msg_bytes:
                chunk = await reader.read(4096)
                if not chunk:
                    break
                msg_bytes += chunk

            if not msg_bytes:
                writer.close()
                await writer.wait_closed()
                return

            headers_part = msg_bytes.split(b"\r\n\r\n")[0]
            body_part = msg_bytes[len(headers_part)+4:]

            content_length = 0
            for line in headers_part.split(b"\r\n"):
                if line.lower().startswith(b"content-length:"):
                    try:
                        content_length = int(line.split(b":")[1].strip())
                    except:
                        pass

            while len(body_part) < content_length:
                chunk = await reader.read(4096)
                if not chunk:
                    break
                body_part += chunk
                msg_bytes += chunk

            req.prepare(msg_bytes.decode("utf-8", errors='replace'), routes=self.routes)
            if req.method is None:
                writer.write(resp.build_notfound())
                await writer.drain()
                writer.close()
                await writer.wait_closed()
                return

            # Handle request hook
            if req.hook:
                print("[HttpAdapter] Async dispatching to hook: {}".format(req.hook))
                try:
                    if inspect.iscoroutinefunction(req.hook):
                        result = await req.hook(headers=req._raw_headers, body=req.body)
                    else:
                        result = req.hook(headers=req._raw_headers, body=req.body)

                    if isinstance(result, bytes):
                        response = resp.build_json_response_bytes(
                            result.decode('utf-8') if result else '{}',
                            cookies=resp.set_cookies
                        )
                    elif isinstance(result, dict):
                        response = resp.build_json_response_bytes(
                            result, cookies=resp.set_cookies
                        )
                    elif isinstance(result, str):
                        response = resp.build_json_response_bytes(
                            result, cookies=resp.set_cookies
                        )
                    else:
                        response = resp.build_json_response_bytes(
                            {"message": "OK"}, cookies=resp.set_cookies
                        )
                except Exception as e:
                    print("[HttpAdapter] Async hook error: {}".format(e))
                    response = resp.build_json_response_bytes(
                        {"error": str(e)},
                        status_code=500,
                        reason="Internal Server Error"
                    )
            else:
                # Build response for static file
                response = resp.build_response(req)

            # Send the response asynchronously
            writer.write(response)
            await writer.drain()
        except Exception as e:
            print("[HttpAdapter] Coroutine error: {}".format(e))
            try:
                writer.write(resp.build_notfound())
                await writer.drain()
            except Exception:
                pass
        finally:
            try:
                writer.close()
                await writer.wait_closed()
            except Exception:
                pass

    def extract_cookies(self, req):
        """
        Build cookies from the :class:`Request <Request>` headers.

        :param req:(Request) The :class:`Request <Request>` object.
        :rtype: cookies - A dictionary of cookie key-value pairs.
        """
        return req.cookies if hasattr(req, 'cookies') else {}

    def build_response(self, req, resp):
        """Builds a :class:`Response <Response>` object

        :param req: The :class:`Request <Request>` used to generate the response.
        :param resp: The response object.
        :rtype: Response
        """
        response = Response()

        response.raw = resp
        response.reason = getattr(resp, 'reason', 'OK')

        if isinstance(req.url, bytes):
            response.url = req.url.decode("utf-8")
        else:
            response.url = req.url

        # Add new cookies from the server.
        response.cookies = self.extract_cookies(req)

        # Give the Response some context.
        response.request = req
        response.connection = self

        return response

    def build_json_response(self, req, resp):
        """Builds a :class:`Response <Response>` object from JSON data

        :param req: The :class:`Request <Request>` used to generate the response.
        :param resp: The response object.
        :rtype: Response
        """
        response = Response(req)

        response.raw = resp

        if isinstance(req.url, bytes):
            response.url = req.url.decode("utf-8")
        else:
            response.url = req.url

        # Give the Response some context.
        response.request = req
        response.connection = self

        return response

    def add_headers(self, request):
        """
        Add headers to the request.

        This method is intended to be overridden by subclasses to inject
        custom headers. It does nothing by default.

        :param request: :class:`Request <Request>` to add headers to.
        """
        pass

    def build_proxy_headers(self, proxy):
        """Returns a dictionary of the headers to add to any request sent
        through a proxy.

        :class:`HttpAdapter <HttpAdapter>`.

        :param proxy: The url of the proxy being used for this request.
        :rtype: dict
        """
        headers = {}
        username, password = ("user1", "password")

        if username:
            headers["Proxy-Authorization"] = (username, password)

        return headers