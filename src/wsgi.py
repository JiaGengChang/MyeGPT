import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from main import app  # FastAPI app

from fastapi.middleware.wsgi import WSGIMiddleware

def application(environ, start_response):
    wsgi_app = WSGIMiddleware(app)
    return wsgi_app(environ, start_response)