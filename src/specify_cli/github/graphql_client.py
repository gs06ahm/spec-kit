"""GraphQL client for GitHub Projects API."""

import time
import json
from typing import Optional, Any, Dict
from datetime import datetime

try:
    import httpx
except ImportError:
    raise ImportError("httpx is required for GitHub API client. Install with: pip install httpx")


class GitHubGraphQLError(Exception):
    """Exception raised for GitHub GraphQL API errors."""
    pass


class RateLimitError(GitHubGraphQLError):
    """Exception raised when rate limit is exceeded."""
    pass


class GraphQLClient:
    """
    GitHub GraphQL API client with rate limiting and retry logic.
    """
    
    GITHUB_GRAPHQL_URL = "https://api.github.com/graphql"
    MIN_REMAINING_BEFORE_DELAY = 500  # Start adding delays when remaining < 500
    CRITICAL_REMAINING = 100  # Critical threshold
    
    def __init__(self, token: str, timeout: int = 30):
        """
        Initialize GraphQL client.
        
        Args:
            token: GitHub personal access token
            timeout: Request timeout in seconds
        """
        self.token = token
        self.timeout = timeout
        self._client = httpx.Client(timeout=timeout)
        self._rate_limit_remaining = 5000
        self._rate_limit_reset_at: Optional[datetime] = None
        
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
    
    def close(self):
        """Close the HTTP client."""
        self._client.close()
    
    def _get_headers(self) -> Dict[str, str]:
        """Get request headers with authorization."""
        return {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json",
            "Accept": "application/vnd.github.v4+json",
        }
    
    def _update_rate_limit(self, headers: httpx.Headers) -> None:
        """Update rate limit information from response headers."""
        if "X-RateLimit-Remaining" in headers:
            self._rate_limit_remaining = int(headers["X-RateLimit-Remaining"])
        
        if "X-RateLimit-Reset" in headers:
            reset_timestamp = int(headers["X-RateLimit-Reset"])
            self._rate_limit_reset_at = datetime.fromtimestamp(reset_timestamp)
    
    def _check_rate_limit(self) -> None:
        """Check rate limit and add delays if needed."""
        if self._rate_limit_remaining < self.CRITICAL_REMAINING:
            # Critical threshold - wait 5 seconds
            time.sleep(5)
        elif self._rate_limit_remaining < self.MIN_REMAINING_BEFORE_DELAY:
            # Low threshold - wait 1 second
            time.sleep(1)
    
    def execute(
        self,
        query: str,
        variables: Optional[Dict[str, Any]] = None,
        retry_count: int = 3,
    ) -> Dict[str, Any]:
        """
        Execute a GraphQL query or mutation.
        
        Args:
            query: GraphQL query or mutation string
            variables: Query variables
            retry_count: Number of retries on failure
            
        Returns:
            Response data dictionary
            
        Raises:
            GitHubGraphQLError: On API errors
            RateLimitError: On rate limit exceeded
        """
        self._check_rate_limit()
        
        payload = {"query": query}
        if variables:
            payload["variables"] = variables
        
        last_error = None
        
        for attempt in range(retry_count):
            try:
                response = self._client.post(
                    self.GITHUB_GRAPHQL_URL,
                    json=payload,
                    headers=self._get_headers(),
                )
                
                self._update_rate_limit(response.headers)
                
                # Handle HTTP errors
                if response.status_code == 401:
                    raise GitHubGraphQLError("Unauthorized: Invalid or expired token")
                elif response.status_code == 403:
                    raise RateLimitError("Rate limit exceeded")
                elif response.status_code >= 500:
                    # Server error - retry with exponential backoff
                    if attempt < retry_count - 1:
                        wait_time = 2 ** attempt
                        time.sleep(wait_time)
                        continue
                    raise GitHubGraphQLError(f"Server error: {response.status_code}")
                
                response.raise_for_status()
                
                data = response.json()
                
                # Check for GraphQL errors
                if "errors" in data:
                    error_messages = [e.get("message", str(e)) for e in data["errors"]]
                    error_str = "; ".join(error_messages)
                    
                    # Check if it's a rate limit error
                    if any("rate limit" in msg.lower() for msg in error_messages):
                        raise RateLimitError(error_str)
                    
                    raise GitHubGraphQLError(f"GraphQL errors: {error_str}")
                
                return data.get("data", {})
                
            except httpx.TimeoutException as e:
                last_error = e
                if attempt < retry_count - 1:
                    time.sleep(2 ** attempt)
                    continue
                raise GitHubGraphQLError(f"Request timeout: {e}")
            
            except httpx.HTTPError as e:
                last_error = e
                if attempt < retry_count - 1:
                    time.sleep(2 ** attempt)
                    continue
                raise GitHubGraphQLError(f"HTTP error: {e}")
        
        # If we get here, all retries failed
        raise GitHubGraphQLError(f"Failed after {retry_count} retries: {last_error}")
    
    def get_rate_limit_info(self) -> Dict[str, Any]:
        """
        Get current rate limit information.
        
        Returns:
            Dictionary with remaining, reset_at, and other rate limit info
        """
        return {
            "remaining": self._rate_limit_remaining,
            "reset_at": self._rate_limit_reset_at.isoformat() if self._rate_limit_reset_at else None,
        }
