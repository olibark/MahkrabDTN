from wsgiref.simple_server import WSGIServer
from socketserver import ThreadingMixIn


class ThreadedWSGIServer(ThreadingMixIn, WSGIServer): daemon_threads = True