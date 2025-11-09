"""
重试机制工具
支持指数退避和错误分类
"""
import time
from typing import Callable, TypeVar, Optional, List
from functools import wraps
from loguru import logger

from config import get_config

T = TypeVar('T')


class RetryableError(Exception):
    """可重试的错误"""
    pass


class NonRetryableError(Exception):
    """不可重试的错误（如参数错误）"""
    pass


def retry_with_backoff(
    max_retries: Optional[int] = None,
    backoff_factor: Optional[float] = None,
    retryable_exceptions: Optional[List[type]] = None
):
    """
    重试装饰器（指数退避）
    
    Args:
        max_retries: 最大重试次数
        backoff_factor: 退避系数
        retryable_exceptions: 可重试的异常类型列表
    """
    config = get_config()
    max_retries = max_retries or config.max_retries
    backoff_factor = backoff_factor or config.retry_backoff
    retryable_exceptions = retryable_exceptions or [Exception]
    
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @wraps(func)
        def wrapper(*args, **kwargs) -> T:
            last_exception = None
            
            for attempt in range(max_retries + 1):
                try:
                    return func(*args, **kwargs)
                except NonRetryableError as e:
                    # 不可重试的错误，直接抛出
                    try:
                        error_msg = str(e)[:200] if len(str(e)) > 200 else str(e)
                        logger.error(f"不可重试的错误: {error_msg}")
                    except:
                        logger.error("不可重试的错误: 无法提取错误信息")
                    raise
                except tuple(retryable_exceptions) as e:
                    last_exception = e
                    if attempt < max_retries:
                        wait_time = backoff_factor ** attempt
                        try:
                            error_msg = str(e)[:200] if len(str(e)) > 200 else str(e)
                            logger.warning(
                                f"工具调用失败 (尝试 {attempt + 1}/{max_retries + 1}): {error_msg}，"
                                f"{wait_time:.2f}秒后重试"
                            )
                        except:
                            logger.warning(f"工具调用失败 (尝试 {attempt + 1}/{max_retries + 1})，{wait_time:.2f}秒后重试")
                        time.sleep(wait_time)
                    else:
                        try:
                            error_msg = str(e)[:200] if len(str(e)) > 200 else str(e)
                            logger.error(f"工具调用失败，已达最大重试次数: {error_msg}")
                        except:
                            logger.error("工具调用失败，已达最大重试次数")
                except Exception as e:
                    # 其他异常，根据类型决定是否重试
                    if any(isinstance(e, exc_type) for exc_type in retryable_exceptions):
                        last_exception = e
                        if attempt < max_retries:
                            wait_time = backoff_factor ** attempt
                            try:
                                error_msg = str(e)[:200] if len(str(e)) > 200 else str(e)
                                logger.warning(
                                    f"工具调用失败 (尝试 {attempt + 1}/{max_retries + 1}): {error_msg}，"
                                    f"{wait_time:.2f}秒后重试"
                                )
                            except:
                                logger.warning(f"工具调用失败 (尝试 {attempt + 1}/{max_retries + 1})，{wait_time:.2f}秒后重试")
                            time.sleep(wait_time)
                        else:
                            try:
                                error_msg = str(e)[:200] if len(str(e)) > 200 else str(e)
                                logger.error(f"工具调用失败，已达最大重试次数: {error_msg}")
                            except:
                                logger.error("工具调用失败，已达最大重试次数")
                    else:
                        # 不可重试的异常
                        raise
            
            # 所有重试都失败了
            if last_exception:
                raise last_exception
            raise RuntimeError("重试失败，未知错误")
        
        return wrapper
    return decorator

