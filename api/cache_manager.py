"""
Redis 기반 캐싱 시스템
반복적인 검색 및 LLM 호출 결과를 캐싱하여 응답 속도 향상
"""
import json
import hashlib
from typing import Optional, Any
from datetime import timedelta

try:
    import redis.asyncio as redis
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False
    print("⚠️ Redis not available. Caching disabled.")

class CacheManager:
    def __init__(self, redis_url: str = "redis://localhost:6379/0"):
        self.redis_url = redis_url
        self.client = None
        self.enabled = REDIS_AVAILABLE
    
    async def connect(self):
        """Redis 연결"""
        if not self.enabled:
            return
        
        try:
            self.client = await redis.from_url(self.redis_url, encoding="utf-8", decode_responses=True)
            await self.client.ping()
            print("✅ Redis cache connected")
        except Exception as e:
            print(f"⚠️ Redis connection failed: {e}. Caching disabled.")
            self.enabled = False
    
    async def disconnect(self):
        """Redis 연결 종료"""
        if self.client:
            await self.client.close()
    
    def _make_key(self, prefix: str, data: str) -> str:
        """캐시 키 생성"""
        hash_val = hashlib.md5(data.encode()).hexdigest()
        return f"{prefix}:{hash_val}"
    
    async def get(self, prefix: str, key_data: str) -> Optional[Any]:
        """캐시 조회"""
        if not self.enabled or not self.client:
            return None
        
        try:
            cache_key = self._make_key(prefix, key_data)
            value = await self.client.get(cache_key)
            
            if value:
                return json.loads(value)
            return None
        except Exception as e:
            print(f"Cache get error: {e}")
            return None
    
    async def set(
        self, 
        prefix: str, 
        key_data: str, 
        value: Any, 
        ttl: int = 3600
    ):
        """캐시 저장"""
        if not self.enabled or not self.client:
            return
        
        try:
            cache_key = self._make_key(prefix, key_data)
            value_json = json.dumps(value, ensure_ascii=False)
            await self.client.setex(cache_key, ttl, value_json)
        except Exception as e:
            print(f"Cache set error: {e}")
    
    async def delete(self, prefix: str, key_data: str):
        """캐시 삭제"""
        if not self.enabled or not self.client:
            return
        
        try:
            cache_key = self._make_key(prefix, key_data)
            await self.client.delete(cache_key)
        except Exception as e:
            print(f"Cache delete error: {e}")
    
    async def clear_prefix(self, prefix: str):
        """특정 prefix의 모든 캐시 삭제"""
        if not self.enabled or not self.client:
            return
        
        try:
            pattern = f"{prefix}:*"
            async for key in self.client.scan_iter(match=pattern):
                await self.client.delete(key)
        except Exception as e:
            print(f"Cache clear error: {e}")

# 글로벌 캐시 매니저 인스턴스
cache = CacheManager()

# 캐시 TTL 설정
CACHE_TTL = {
    "search": 3600,      # 검색 결과: 1시간
    "llm_response": 7200,  # LLM 응답: 2시간
    "embedding": 86400,   # 임베딩: 24시간
    "stats": 300          # 통계: 5분
}
