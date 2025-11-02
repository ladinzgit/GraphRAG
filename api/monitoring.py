"""
성능 모니터링 및 로깅 유틸리티
"""
import time
import logging
from functools import wraps
from typing import Callable
from pythonjsonlogger import jsonlogger

# JSON 로거 설정
def setup_logger(name: str = "graphrag") -> logging.Logger:
    """구조화된 JSON 로거 설정"""
    logger = logging.getLogger(name)
    logger.setLevel(logging.INFO)
    
    # 핸들러가 없는 경우에만 추가
    if not logger.handlers:
        handler = logging.StreamHandler()
        formatter = jsonlogger.JsonFormatter(
            '%(asctime)s %(name)s %(levelname)s %(message)s'
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)
    
    return logger

logger = setup_logger()

def time_it(func: Callable) -> Callable:
    """함수 실행 시간 측정 데코레이터"""
    @wraps(func)
    async def async_wrapper(*args, **kwargs):
        start = time.time()
        try:
            result = await func(*args, **kwargs)
            elapsed = time.time() - start
            logger.info(
                "Function executed",
                extra={
                    "function": func.__name__,
                    "elapsed_ms": round(elapsed * 1000, 2),
                    "status": "success"
                }
            )
            return result
        except Exception as e:
            elapsed = time.time() - start
            logger.error(
                "Function failed",
                extra={
                    "function": func.__name__,
                    "elapsed_ms": round(elapsed * 1000, 2),
                    "status": "error",
                    "error": str(e)
                }
            )
            raise
    
    @wraps(func)
    def sync_wrapper(*args, **kwargs):
        start = time.time()
        try:
            result = func(*args, **kwargs)
            elapsed = time.time() - start
            logger.info(
                "Function executed",
                extra={
                    "function": func.__name__,
                    "elapsed_ms": round(elapsed * 1000, 2),
                    "status": "success"
                }
            )
            return result
        except Exception as e:
            elapsed = time.time() - start
            logger.error(
                "Function failed",
                extra={
                    "function": func.__name__,
                    "elapsed_ms": round(elapsed * 1000, 2),
                    "status": "error",
                    "error": str(e)
                }
            )
            raise
    
    # async 함수인지 확인
    if hasattr(func, '__code__') and func.__code__.co_flags & 0x100:
        return async_wrapper
    return sync_wrapper

class PerformanceTracker:
    """API 호출 성능 추적"""
    def __init__(self):
        self.metrics = {
            "search_times": [],
            "llm_times": [],
            "total_requests": 0,
            "cache_hits": 0,
            "cache_misses": 0
        }
    
    def record_search_time(self, elapsed: float):
        """검색 시간 기록"""
        self.metrics["search_times"].append(elapsed)
        if len(self.metrics["search_times"]) > 100:
            self.metrics["search_times"].pop(0)
    
    def record_llm_time(self, elapsed: float):
        """LLM 응답 시간 기록"""
        self.metrics["llm_times"].append(elapsed)
        if len(self.metrics["llm_times"]) > 100:
            self.metrics["llm_times"].pop(0)
    
    def record_request(self):
        """요청 카운트"""
        self.metrics["total_requests"] += 1
    
    def record_cache_hit(self):
        """캐시 히트"""
        self.metrics["cache_hits"] += 1
    
    def record_cache_miss(self):
        """캐시 미스"""
        self.metrics["cache_misses"] += 1
    
    def get_stats(self) -> dict:
        """통계 조회"""
        search_times = self.metrics["search_times"]
        llm_times = self.metrics["llm_times"]
        
        return {
            "total_requests": self.metrics["total_requests"],
            "cache_hit_rate": (
                self.metrics["cache_hits"] / 
                (self.metrics["cache_hits"] + self.metrics["cache_misses"])
                if (self.metrics["cache_hits"] + self.metrics["cache_misses"]) > 0
                else 0
            ),
            "avg_search_time_ms": (
                sum(search_times) / len(search_times) * 1000
                if search_times else 0
            ),
            "avg_llm_time_ms": (
                sum(llm_times) / len(llm_times) * 1000
                if llm_times else 0
            ),
            "p95_search_time_ms": (
                sorted(search_times)[int(len(search_times) * 0.95)] * 1000
                if len(search_times) > 20 else 0
            ),
            "p95_llm_time_ms": (
                sorted(llm_times)[int(len(llm_times) * 0.95)] * 1000
                if len(llm_times) > 20 else 0
            )
        }

# 글로벌 성능 트래커
perf_tracker = PerformanceTracker()
