"""Render entrypoint for OxyZen backend.

The application routes live in server.py. Keeping this module as a thin
entrypoint prevents a second AQI routing implementation from drifting away
from the main API.
"""
from server import app
