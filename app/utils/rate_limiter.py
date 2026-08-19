# app/utils/rate_limiter.py
import time
from collections import defaultdict
from typing import Dict, Tuple
from fastapi import HTTPException, status
from datetime import datetime

class RateLimiter:
    """Rate limiter untuk mencegah brute force attack"""
    
    def __init__(self):
        self._attempts: Dict[str, list] = defaultdict(list)
        self.window_seconds = 300  
        self.max_attempts = 5 
    
    def check(self, key: str) -> Tuple[bool, int]:
        """
        Cek apakah IP masih boleh mencoba login/register.
        
        Returns:
            (allowed, remaining_attempts)
        """
        now = time.time()
        
        self._attempts[key] = [
            t for t in self._attempts.get(key, [])
            if now - t < self.window_seconds
        ]
        
        
        used = len(self._attempts[key])
        remaining = self.max_attempts - used
        
        if remaining <= 0:
            
            oldest = min(self._attempts.get(key, []))
            wait_time = int(self.window_seconds - (now - oldest))
            return False, wait_time
        
        return True, remaining
    
    def record_attempt(self, key: str) -> None:
        """Catat percobaan login/register"""
        self._attempts[key].append(time.time())
    
    def reset(self, key: str) -> None:
        """Reset percobaan setelah login sukses"""
        if key in self._attempts:
            del self._attempts[key]


rate_limiter = RateLimiter()


def get_client_ip(request) -> str:
    """Dapatkan IP client dari request"""
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host