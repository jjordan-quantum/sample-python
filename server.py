import os
import http.server
import socketserver

from http import HTTPStatus

from src import liquidity_example

class Handler(http.server.SimpleHTTPRequestHandler):
    def do_GET(self):
        self.send_response(HTTPStatus.OK)
        self.end_headers()
        msg = 'Welcome to yieldfarmer001! You requested the following route %s' % (self.path)
        if self.path == '/new':
            msg = 'This is a new path: %s ... runing run_test function' % (self.path)
            liquidity_example.run_test()
        self.wfile.write(msg.encode())


port = int(os.getenv('PORT', 80))
print('Listening on port %s' % (port))
httpd = socketserver.TCPServer(('', port), Handler)
httpd.serve_forever()
