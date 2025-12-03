class CookieToHeaderJWTMiddleware:
    """Middleware that moves the `access_token` cookie into the
    `Authorization` header as `Bearer <token>` when the header is not
    already present.

    This allows Django/DRF authentication backends that expect an
    Authorization header (like Simple JWT's `JWTAuthentication`) to
    authenticate requests where the frontend stores tokens in
    HttpOnly cookies.
    """
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # If the request already has an Authorization header, prefer it.
        if 'HTTP_AUTHORIZATION' not in request.META:
            token = request.COOKIES.get('access_token')
            if token:
                request.META['HTTP_AUTHORIZATION'] = f'Bearer {token}'
        return self.get_response(request)
