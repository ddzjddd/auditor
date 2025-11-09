# src/tools/read_file.py
import os
import sys
from pathlib import Path

# 添加父目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from tools.schemas import ReadFileArgs
from utils.cache import cached_tool
from utils.retry import retry_with_backoff, RetryableError, NonRetryableError
from utils.logger import get_logger

logger = get_logger()


@retry_with_backoff(retryable_exceptions=[IOError, OSError])
def _read_file_impl(file_path: str, max_lines: int = 1000, encoding: str = "utf-8") -> dict:
    """
    读取文件内容（内部实现，不包含缓存）
    
    Args:
        file_path: 文件路径（相对或绝对路径）
        max_lines: 最大读取行数（防止文件过大，默认1000行）
        encoding: 文件编码（默认utf-8）
    
    Returns:
        dict: {"tool": "read_file", "ok": bool, "data": dict}
    """
    # 参数验证
    try:
        args = ReadFileArgs(file_path=file_path, max_lines=max_lines, encoding=encoding)
        file_path = args.file_path
        max_lines = args.max_lines
        encoding = args.encoding
    except Exception as e:
        raise NonRetryableError(f"参数验证失败: {e}")
    
    logger.info(f"读取文件: {file_path}", tool_name="read_file", tool_args={"file_path": file_path, "max_lines": max_lines})
    
    try:
        # 解析路径并规范化（用于缓存键）
        path = Path(file_path)
        if not path.is_absolute():
            # 相对路径，从项目根目录开始
            project_root = Path(__file__).parent.parent.parent
            path = project_root / path
        
        # 规范化路径（解析符号链接，统一格式）
        try:
            path = path.resolve()
        except Exception:
            pass  # 如果resolve失败，使用原路径
        
        if not path.exists():
            raise NonRetryableError(f"文件不存在: {file_path} (解析后路径: {path})")
        
        if not path.is_file():
            raise NonRetryableError(f"路径不是文件: {file_path}")
        
        # 检查文件大小（防止读取过大文件）
        file_size = path.stat().st_size
        max_size = 10 * 1024 * 1024  # 10MB
        if file_size > max_size:
            raise NonRetryableError(f"文件过大 ({file_size / 1024 / 1024:.2f}MB)，超过限制 ({max_size / 1024 / 1024}MB)")
        
        # 读取文件
        try:
            with open(path, 'r', encoding=encoding) as f:
                lines = f.readlines()
        except UnicodeDecodeError:
            # 如果UTF-8失败，尝试其他编码
            try:
                with open(path, 'r', encoding='latin-1') as f:
                    lines = f.readlines()
                encoding = 'latin-1'
            except Exception as e:
                raise RetryableError(f"无法读取文件（编码问题）: {e}")
        
        total_lines = len(lines)
        
        # 如果文件超过最大行数，只返回前N行和最后几行
        if total_lines > max_lines:
            truncated = True
            content_lines = lines[:max_lines] + [f"\n... (省略 {total_lines - max_lines} 行) ...\n"] + lines[-10:]
            content = "".join(content_lines)
        else:
            truncated = False
            content = "".join(lines)
        
        # 获取文件信息
        file_info = {
            "path": str(path),
            "size": file_size,
            "total_lines": total_lines,
            "encoding": encoding,
            "truncated": truncated,
            "lines_shown": max_lines if not truncated else max_lines + 10
        }
        
        return {
            "tool": "read_file",
            "ok": True,
            "data": {
                "file_info": file_info,
                "content": content
            }
        }
        
    except NonRetryableError:
        raise
    except FileNotFoundError:
        raise NonRetryableError(f"文件不存在: {file_path}")
    except PermissionError:
        raise NonRetryableError(f"无权限读取文件: {file_path}")
    except Exception as e:
        raise RetryableError(f"读取文件失败: {e}")


@cached_tool("read_file")
def read_file(file_path: str, max_lines: int = 1000, encoding: str = "utf-8") -> dict:
    """
    读取文件内容（带缓存）
    
    Args:
        file_path: 文件路径（相对或绝对路径）
        max_lines: 最大读取行数（防止文件过大，默认1000行）
        encoding: 文件编码（默认utf-8）
    
    Returns:
        dict: {"tool": "read_file", "ok": bool, "data": dict}
    """
    # 规范化路径用于缓存键（在调用前就规范化，确保缓存键一致）
    path = Path(file_path)
    if not path.is_absolute():
        project_root = Path(__file__).parent.parent.parent
        path = project_root / path
    try:
        path = path.resolve()
    except Exception:
        pass
    
    # 使用规范化后的路径作为参数（确保缓存键一致）
    normalized_path = str(path)
    
    return _read_file_impl(normalized_path, max_lines, encoding)

