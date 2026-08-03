"""Cliente HTTP compartilhado com transporte injetável."""

from asus_theye.net.http import HttpError, HttpResponse, Transport, UrllibTransport, get_bytes

__all__ = ["HttpError", "HttpResponse", "Transport", "UrllibTransport", "get_bytes"]
