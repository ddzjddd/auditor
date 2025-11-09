"""
工具结果缓存系统
支持内存缓存和磁盘缓存，基于参数hash
"""
import hashlib
import json
import time
import os
from pathlib import Path
from typing import Any, Optional, Dict
from functools import wraps
import orjson
from loguru import logger

from config import get_config


def _make_json_serializable(obj: Any) -> Any:
    """确保对象可JSON序列化"""
    if isinstance(obj, dict):
        return {k: _make_json_serializable(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [_make_json_serializable(item) for item in obj]
    elif isinstance(obj, (str, int, float, bool, type(None))):
        return obj
    elif hasattr(obj, '__dict__'):
        # 对于对象，尝试转换为字典
        try:
            return _make_json_serializable(obj.__dict__)
        except:
            return str(obj)
    else:
        # 对于其他类型，尝试转换为字符串
        try:
            json.dumps(obj)
            return obj
        except (TypeError, ValueError):
            return str(obj)


class ToolCache:
    """工具结果缓存"""
    
    def __init__(self, cache_dir: str = ".cache", ttl: int = 3600):
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.ttl = ttl
        self.memory_cache: Dict[str, tuple[Any, float]] = {}
    
    def _make_key(self, tool_name: str, args: dict) -> str:
        """生成缓存键"""
        # 清理不可序列化的参数
        from utils.summarizer import _make_json_serializable
        try:
            clean_args = _make_json_serializable(args)
        except Exception:
            # 如果清理失败，尝试手动过滤
            clean_args = {}
            for k, v in args.items():
                try:
                    # 测试是否可序列化
                    orjson.dumps({k: v})
                    clean_args[k] = v
                except (TypeError, ValueError):
                    # 跳过不可序列化的值
                    logger.warning(f"跳过不可序列化的参数: {k}")
                    continue
        
        # 使用工具名和参数的hash作为key
        key_data = {"tool": tool_name, "args": clean_args}
        try:
            key_str = orjson.dumps(key_data, option=orjson.OPT_SORT_KEYS).decode()
        except (TypeError, ValueError) as e:
            # 如果仍然失败，使用字符串表示
            logger.warning(f"序列化缓存键失败: {e}，使用字符串表示")
            key_str = f"{tool_name}:{str(clean_args)}"
        return hashlib.sha256(key_str.encode()).hexdigest()
    
    def _get_cache_path(self, key: str) -> Path:
        """获取缓存文件路径"""
        return self.cache_dir / f"{key}.json"
    
    def get(self, tool_name: str, args: dict) -> Optional[Any]:
        """获取缓存结果"""
        key = self._make_key(tool_name, args)
        
        # 先检查内存缓存
        if key in self.memory_cache:
            result, timestamp = self.memory_cache[key]
            if time.time() - timestamp < self.ttl:
                logger.debug(f"缓存命中（内存）: {tool_name}")
                return result
            else:
                del self.memory_cache[key]
        
        # 检查磁盘缓存
        cache_path = self._get_cache_path(key)
        if cache_path.exists():
            try:
                with open(cache_path, 'rb') as f:
                    data = orjson.loads(f.read())
                    timestamp = data.get('timestamp', 0)
                    if time.time() - timestamp < self.ttl:
                        result = data.get('result')
                        # 更新内存缓存
                        self.memory_cache[key] = (result, timestamp)
                        logger.debug(f"缓存命中（磁盘）: {tool_name}")
                        return result
                    else:
                        # 过期，删除
                        cache_path.unlink()
            except Exception as e:
                logger.warning(f"读取缓存失败: {e}")
        
        return None
    
    def set(self, tool_name: str, args: dict, result: Any):
        """设置缓存"""
        key = self._make_key(tool_name, args)
        timestamp = time.time()
        
        # 确保结果可序列化
        try:
            serializable_result = _make_json_serializable(result)
        except Exception as e:
            logger.warning(f"清理缓存结果失败: {e}，跳过缓存")
            return
        
        # 更新内存缓存
        self.memory_cache[key] = (serializable_result, timestamp)
        
        # 更新磁盘缓存
        cache_path = self._get_cache_path(key)
        try:
            cache_data = {
                "tool": tool_name,
                "timestamp": timestamp,
                "result": serializable_result
            }
            with open(cache_path, 'wb') as f:
                f.write(orjson.dumps(cache_data))
        except Exception as e:
            logger.warning(f"写入缓存失败: {e}")
    
    def clear(self, tool_name: Optional[str] = None):
        """清除缓存"""
        if tool_name:
            # 清除特定工具的缓存
            keys_to_remove = [k for k in self.memory_cache.keys()]
            for key in keys_to_remove:
                cache_path = self._get_cache_path(key)
                if cache_path.exists():
                    cache_path.unlink()
            self.memory_cache.clear()
        else:
            # 清除所有缓存
            for cache_file in self.cache_dir.glob("*.json"):
                cache_file.unlink()
            self.memory_cache.clear()
        logger.info(f"缓存已清除: {tool_name or '全部'}")


# 全局缓存实例
_cache: Optional[ToolCache] = None


def get_cache() -> Optional[ToolCache]:
    """获取缓存实例"""
    global _cache
    config = get_config()
    if config.enable_cache and _cache is None:
        _cache = ToolCache(cache_dir=config.cache_dir, ttl=config.cache_ttl)
    return _cache if config.enable_cache else None


def cached_tool(tool_name: str):
    """工具缓存装饰器"""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            cache = get_cache()
            if cache is None:
                return func(*args, **kwargs)
            
            # 构建参数字典
            tool_args = kwargs.copy()
            if args:
                # 如果有位置参数，需要根据函数签名映射
                import inspect
                sig = inspect.signature(func)
                param_names = list(sig.parameters.keys())
                
                # 跳过 self 参数（如果是实例方法）
                start_idx = 0
                if param_names and param_names[0] == 'self':
                    start_idx = 1
                
                for i, arg in enumerate(args[start_idx:], start=start_idx):
                    if i < len(param_names):
                        param_name = param_names[i]
                        # 跳过 self 参数
                        if param_name == 'self':
                            continue
                        tool_args[param_name] = arg
            
            # 清理不可序列化的参数（双重保险）
            from utils.summarizer import _make_json_serializable
            try:
                tool_args = _make_json_serializable(tool_args)
            except Exception as e:
                logger.warning(f"清理工具参数失败 {tool_name}: {e}，使用原始参数")
            
            # 检查缓存
            try:
                cached_result = cache.get(tool_name, tool_args)
                if cached_result is not None:
                    return cached_result
            except Exception as e:
                logger.warning(f"获取缓存失败 {tool_name}: {e}，继续执行")
            
            # 执行工具
            result = func(*args, **kwargs)
            
            # 缓存结果（只缓存成功的）
            if isinstance(result, dict) and result.get("ok", False):
                try:
                    # 在缓存前确保结果可序列化
                    cache.set(tool_name, tool_args, result)
                except Exception as e:
                    logger.warning(f"缓存工具结果失败 {tool_name}: {e}，继续执行")
            
            return result
        return wrapper
    return decorator

