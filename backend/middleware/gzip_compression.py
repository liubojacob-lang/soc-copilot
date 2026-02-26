"""
Gzip Compression Middleware for FastAPI
Compresses responses larger than 1KB to reduce bandwidth usage.
"""

import gzip
from io import BytesIO
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response
from starlette.types import ASGIApp, Message, Receive, Scope, Send


class GzipCompressionMiddleware(BaseHTTPMiddleware):
    """
    Middleware to compress HTTP responses using Gzip.
    
    Compresses responses when:
    - Response size &gt; 1KB
    - Client accepts gzip encoding
    - Response is not already compressed
    """
    
    def __init__(
        self,
        app: ASGIApp,
        minimum_size: int = 1024,
        compresslevel: int = 6,
    ):
        super().__init__(app)
        self.minimum_size = minimum_size
        self.compresslevel = compresslevel
    
    async def dispatch(self, request, call_next):
        accept_encoding = request.headers.get("accept-encoding", "")
        
        if "gzip" not in accept_encoding.lower():
            return await call_next(request)
        
        response = await call_next(request)
        
        if response.status_code &lt; 200 or response.status_code &gt;= 300:
            return response
        
        content_encoding = response.headers.get("content-encoding", "")
        if "gzip" in content_encoding.lower():
            return response
        
        content_length = response.headers.get("content-length")
        if content_length and int(content_length) &lt; self.minimum_size:
            return response
        
        body = b""
        async for chunk in response.body_iterator:
            body += chunk
        
        if len(body) &lt; self.minimum_size:
            return Response(
                content=body,
                status_code=response.status_code,
                headers=dict(response.headers),
                media_type=response.media_type,
            )
        
        compressed_body = self._gzip_compress(body)
        
        headers = dict(response.headers)
        headers["Content-Encoding"] = "gzip"
        headers["Content-Length"] = str(len(compressed_body))
        headers["Vary"] = "Accept-Encoding"
        
        if "Transfer-Encoding" in headers:
            del headers["Transfer-Encoding"]
        
        return Response(
            content=compressed_body,
            status_code=response.status_code,
            headers=headers,
            media_type=response.media_type,
        )
    
    def _gzip_compress(self, data: bytes) -&gt; bytes:
        """Compress data using Gzip."""
        buffer = BytesIO()
        with gzip.GzipFile(fileobj=buffer, mode="wb", compresslevel=self.compresslevel) as f:
            f.write(data)
        return buffer.getvalue()
