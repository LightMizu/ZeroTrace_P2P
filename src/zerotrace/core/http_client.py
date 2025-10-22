#!/usr/bin/env python3
"""HTTP Client Utilities with I2P Proxy Support for ZeroTrace"""

import httpx
from typing import Optional
from urllib.parse import urlparse


class ZeroTraceHTTPClient:
    """HTTP client factory that automatically routes I2P destinations through proxy."""
    
    # I2P HTTP proxy settings (default i2pd configuration)
    I2P_PROXY_HOST = "127.0.0.1"
    I2P_PROXY_PORT = 4444
    
    @classmethod
    def _is_localhost(cls, url: str) -> bool:
        """Check if URL is localhost/127.0.0.1.
        
        Args:
            url: URL to check
            
        Returns:
            True if localhost, False otherwise
        """
        try:
            parsed = urlparse(url)
            host = parsed.hostname or parsed.netloc
            
            # Check if host is localhost or 127.0.0.1
            localhost_variants = ['localhost', '127.0.0.1', '::1', '0.0.0.0']
            return host.lower() in localhost_variants if host else False
        except Exception:
            return False
    
    @classmethod
    def _is_i2p_destination(cls, url: str) -> bool:
        """Check if URL is an I2P destination (.b32.i2p or .i2p).
        
        Args:
            url: URL to check
            
        Returns:
            True if I2P destination, False otherwise
        """
        try:
            parsed = urlparse(url)
            host = parsed.hostname or parsed.netloc
            
            if host:
                # Check for .i2p or .b32.i2p domains
                return host.lower().endswith('.i2p')
            return False
        except Exception:
            return False
    
    @classmethod
    def _should_use_proxy(cls, url: str) -> bool:
        """Determine if URL should use I2P proxy.
        
        Args:
            url: URL to check
            
        Returns:
            True if should use proxy, False for direct connection
        """
        # Don't use proxy for localhost
        if cls._is_localhost(url):
            return False
        
        # Use proxy for I2P destinations
        if cls._is_i2p_destination(url):
            return True
        
        # For other URLs, don't use proxy by default
        # (could be extended to use proxy for all non-localhost)
        return False
    
    @classmethod
    def create_client(cls, base_url: Optional[str] = None, 
                     timeout: float = 10.0,
                     force_proxy: bool = False,
                     force_direct: bool = False) -> httpx.AsyncClient:
        """Create an async HTTP client with automatic I2P proxy routing.
        
        Args:
            base_url: Optional base URL for the client
            timeout: Request timeout in seconds
            force_proxy: Force use of I2P proxy regardless of URL
            force_direct: Force direct connection (no proxy)
            
        Returns:
            Configured httpx.AsyncClient instance
        """
        # Determine if we need proxy
        use_proxy = False
        
        if force_direct:
            use_proxy = False
        elif force_proxy:
            use_proxy = True
        elif base_url:
            use_proxy = cls._should_use_proxy(base_url)
        
        # Configure client
        client_kwargs = {
            'timeout': timeout,
            'follow_redirects': True
        }
        
        if base_url:
            client_kwargs['base_url'] = base_url
        
        if use_proxy:
            # Configure I2P HTTP proxy
            # In httpx 0.28+, use 'proxy' parameter (singular)
            proxy_url = f"http://{cls.I2P_PROXY_HOST}:{cls.I2P_PROXY_PORT}"
            client_kwargs['proxy'] = proxy_url
        
        return httpx.AsyncClient(**client_kwargs)
    
    @classmethod
    def create_sync_client(cls, base_url: Optional[str] = None,
                          timeout: float = 10.0,
                          force_proxy: bool = False,
                          force_direct: bool = False) -> httpx.Client:
        """Create a synchronous HTTP client with automatic I2P proxy routing.
        
        Args:
            base_url: Optional base URL for the client
            timeout: Request timeout in seconds
            force_proxy: Force use of I2P proxy regardless of URL
            force_direct: Force direct connection (no proxy)
            
        Returns:
            Configured httpx.Client instance
        """
        # Determine if we need proxy
        use_proxy = False
        
        if force_direct:
            use_proxy = False
        elif force_proxy:
            use_proxy = True
        elif base_url:
            use_proxy = cls._should_use_proxy(base_url)
        
        # Configure client
        client_kwargs = {
            'timeout': timeout,
            'follow_redirects': True
        }
        
        if base_url:
            client_kwargs['base_url'] = base_url
        
        if use_proxy:
            # Configure I2P HTTP proxy
            # In httpx 0.28+, use 'proxy' parameter (singular)
            proxy_url = f"http://{cls.I2P_PROXY_HOST}:{cls.I2P_PROXY_PORT}"
            client_kwargs['proxy'] = proxy_url
        
        return httpx.Client(**client_kwargs)
    
    @classmethod
    async def get(cls, url: str, **kwargs) -> httpx.Response:
        """Convenience method for GET requests with auto-proxy.
        
        Args:
            url: URL to request
            **kwargs: Additional arguments for httpx
            
        Returns:
            httpx.Response object
        """
        async with cls.create_client() as client:
            # Determine proxy based on URL
            if cls._should_use_proxy(url):
                proxy_url = f"http://{cls.I2P_PROXY_HOST}:{cls.I2P_PROXY_PORT}"
                # Create new client with proxy for this request
                async with httpx.AsyncClient(proxy=proxy_url, **kwargs) as proxy_client:
                    return await proxy_client.get(url, **kwargs)
            return await client.get(url, **kwargs)
    
    @classmethod
    async def post(cls, url: str, **kwargs) -> httpx.Response:
        """Convenience method for POST requests with auto-proxy.
        
        Args:
            url: URL to request
            **kwargs: Additional arguments for httpx
            
        Returns:
            httpx.Response object
        """
        async with cls.create_client() as client:
            # Determine proxy based on URL
            if cls._should_use_proxy(url):
                proxy_url = f"http://{cls.I2P_PROXY_HOST}:{cls.I2P_PROXY_PORT}"
                # Create new client with proxy for this request
                async with httpx.AsyncClient(proxy=proxy_url, **kwargs) as proxy_client:
                    return await proxy_client.post(url, **kwargs)
            return await client.post(url, **kwargs)


# Convenience functions for backward compatibility
def create_http_client(base_url: Optional[str] = None, **kwargs) -> httpx.AsyncClient:
    """Create HTTP client with automatic I2P proxy routing.
    
    This is a convenience wrapper around ZeroTraceHTTPClient.create_client().
    """
    return ZeroTraceHTTPClient.create_client(base_url=base_url, **kwargs)


def should_use_i2p_proxy(url: str) -> bool:
    """Check if a URL should use I2P proxy.
    
    Returns True for I2P destinations, False for localhost.
    """
    return ZeroTraceHTTPClient._should_use_proxy(url)
