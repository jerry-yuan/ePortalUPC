import urllib.request


class HTTPRedirectHandler(urllib.request.HTTPRedirectHandler):
    def http_error_302(self, req, fp, code, msg, headers):
        pass

    http_error_301 = http_error_303 = http_error_307 = http_error_302