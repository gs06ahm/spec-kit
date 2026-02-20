"""GitHub authentication utilities."""

import os
import subprocess
from typing import Optional


def resolve_github_token(explicit_token: Optional[str] = None) -> Optional[str]:
    """
    Resolve GitHub token from multiple sources in order of precedence:
    1. Explicit token argument
    2. GH_TOKEN environment variable
    3. GITHUB_TOKEN environment variable
    4. gh CLI auth token command
    
    Returns None if no token is found.
    """
    # Check explicit token
    if explicit_token:
        return explicit_token.strip()
    
    # Check environment variables
    if token := os.getenv("GH_TOKEN"):
        return token.strip()
    
    if token := os.getenv("GITHUB_TOKEN"):
        return token.strip()
    
    # Try gh CLI
    try:
        result = subprocess.run(
            ["gh", "auth", "token"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        if result.returncode == 0 and result.stdout.strip():
            return result.stdout.strip()
    except (subprocess.TimeoutExpired, FileNotFoundError):
        pass
    
    return None


def validate_token(token: str) -> bool:
    """
    Validate that a token is non-empty and looks like a GitHub token.
    Does not make API calls.
    """
    if not token or not isinstance(token, str):
        return False
    
    token = token.strip()
    
    # GitHub tokens are typically 40+ characters
    if len(token) < 20:
        return False
    
    # Check for common GitHub token prefixes
    valid_prefixes = ["ghp_", "gho_", "ghu_", "ghs_", "ghr_", "github_pat_"]
    
    # Classic tokens don't have prefixes, so also allow alphanumeric strings
    if any(token.startswith(prefix) for prefix in valid_prefixes):
        return True
    
    # Classic token: 40 hex characters
    if len(token) == 40 and all(c in "0123456789abcdef" for c in token):
        return True
    
    # For other formats, just check it's not empty and has reasonable length
    return len(token) >= 20
