"""
工具结果摘要器
用于将大型工具输出压缩为关键信息，节省token
"""
import json
from pathlib import Path
from typing import Dict, Any, List
from loguru import logger


def _make_json_serializable(obj: Any) -> Any:
    """确保对象可JSON序列化"""
    # 处理 numpy 类型
    try:
        import numpy as np
        if isinstance(obj, (np.integer, np.floating)):
            return obj.item()
        elif isinstance(obj, np.ndarray):
            return obj.tolist()
    except (ImportError, AttributeError):
        pass
    
    if isinstance(obj, dict):
        return {str(k) if not isinstance(k, (str, int, float, bool)) else k: _make_json_serializable(v) 
                for k, v in obj.items()}
    elif isinstance(obj, (list, tuple)):
        return [_make_json_serializable(item) for item in obj]
    elif isinstance(obj, (str, int, float, bool, type(None))):
        return obj
    elif isinstance(obj, Path):
        return str(obj)
    elif hasattr(obj, '__dict__'):
        # 对于对象，尝试转换为字典
        try:
            return _make_json_serializable(obj.__dict__)
        except:
            return str(obj)
    elif hasattr(obj, 'item'):
        # numpy scalar
        try:
            return obj.item()
        except:
            return float(obj) if isinstance(obj, (int, float)) else str(obj)
    else:
        # 对于其他类型，尝试转换为字符串
        try:
            # 先尝试直接序列化
            json.dumps(obj)
            return obj
        except (TypeError, ValueError):
            # 如果失败，转换为字符串
            try:
                return str(obj)
            except:
                return repr(obj)


def summarize_slither_result(data: Dict[str, Any], max_items: int = 20) -> Dict[str, Any]:
    """摘要Slither扫描结果"""
    if not isinstance(data, dict):
        return {"summary": "无法解析Slither结果", "raw_length": len(str(data))}
    
    summary = {
        "detectors": [],
        "total_issues": 0,
        "by_severity": {"High": 0, "Medium": 0, "Low": 0, "Informational": 0}
    }
    
    # 提取检测器结果
    detectors = data.get("detectors", [])
    for det in detectors[:max_items]:
        check = det.get("check", "")
        impact = det.get("impact", "")
        confidence = det.get("confidence", "")
        elements = det.get("elements", [])
        
        # 提取关键信息
        locations = []
        for elem in elements[:3]:  # 只取前3个位置
            if isinstance(elem, dict):
                loc = elem.get("source_mapping", {})
                if loc:
                    locations.append({
                        "file": loc.get("filename_absolute", "").split("/")[-1],
                        "line": loc.get("lines", [None])[0]
                    })
        
        summary["detectors"].append({
            "check": check,
            "impact": impact,
            "confidence": confidence,
            "locations": locations
        })
        
        # 统计严重程度
        if impact in summary["by_severity"]:
            summary["by_severity"][impact] += 1
        summary["total_issues"] += 1
    
    if len(detectors) > max_items:
        summary["truncated"] = True
        summary["total_detectors"] = len(detectors)
    
    return summary


def summarize_mythril_result(data: Dict[str, Any]) -> Dict[str, Any]:
    """摘要Mythril扫描结果"""
    if not isinstance(data, dict):
        return {"summary": "无法解析Mythril结果", "raw_length": len(str(data))}
    
    issues = data.get("issues", [])
    summary = {
        "total_issues": len(issues),
        "issues": []
    }
    
    for issue in issues[:10]:  # 只取前10个问题
        summary["issues"].append({
            "title": issue.get("title", ""),
            "severity": issue.get("severity", ""),
            "description": issue.get("description", "")[:200],  # 截断描述
            "address": issue.get("address"),
            "swc_id": issue.get("swc-id")
        })
    
    if len(issues) > 10:
        summary["truncated"] = True
    
    return summary


def summarize_forge_result(data: Dict[str, Any]) -> Dict[str, Any]:
    """摘要Forge编译结果"""
    if not isinstance(data, dict):
        return {"summary": "无法解析Forge结果", "raw_length": len(str(data))}
    
    contracts = data.get("contracts", {})
    summary = {
        "compiled_contracts": len(contracts),
        "contracts": []
    }
    
    for name, contract_data in list(contracts.items())[:10]:
        summary["contracts"].append({
            "name": name,
            "has_abi": bool(contract_data.get("abi")),
            "has_bytecode": bool(contract_data.get("bytecode")),
            "compiler": contract_data.get("compiler", {}).get("version", "unknown")
        })
    
    return summary


def summarize_chain_state_result(data: Dict[str, Any]) -> Dict[str, Any]:
    """摘要链状态查询结果"""
    # 链状态结果通常已经很小，直接返回
    return data


def summarize_rag_result(data: Dict[str, Any]) -> Dict[str, Any]:
    """摘要RAG检索结果"""
    if not isinstance(data, dict):
        return data
    
    items = data.get("items", [])
    summary = {
        "total_items": len(items),
        "summary": data.get("summary", ""),
        "items": []
    }
    
    for item in items[:5]:  # 只取前5个结果
        content = item.get("content", "")
        summary["items"].append({
            "content": content[:300] + "..." if len(content) > 300 else content,  # 截断内容
            "score": item.get("score", 0),
            "meta": item.get("meta", {})
        })
    
    return summary


def summarize_read_file_result(data: Dict[str, Any]) -> Dict[str, Any]:
    """摘要文件读取结果"""
    if not isinstance(data, dict):
        return data
    
    file_info = data.get("file_info", {})
    content = data.get("content", "")
    
    # 如果内容太长，只保留前1000字符和文件信息
    if len(content) > 2000:
        summary = {
            "file_info": file_info,
            "content_preview": content[:1000] + "...",
            "content_length": len(content),
            "truncated": True
        }
    else:
        summary = {
            "file_info": file_info,
            "content": content,
            "truncated": False
        }
    
    return summary


# 工具结果摘要器映射
TOOL_SUMMARIZERS = {
    "slither": summarize_slither_result,
    "mythril": summarize_mythril_result,
    "forge": summarize_forge_result,
    "chain_state": summarize_chain_state_result,
    "rag_search": summarize_rag_result,
    "read_file": summarize_read_file_result,
}


def summarize_tool_result(tool_name: str, result: Dict[str, Any], max_length: int = 2000) -> Dict[str, Any]:
    """
    摘要工具结果
    
    Args:
        tool_name: 工具名称
        result: 工具原始结果
        max_length: 最大字符长度（超过则摘要）
    
    Returns:
        摘要后的结果
    """
    if not isinstance(result, dict) or not result.get("ok", False):
        return result
    
    # 确保结果可序列化，然后检查结果大小
    try:
        serializable_result = _make_json_serializable(result)
        result_str = json.dumps(serializable_result, ensure_ascii=False)
    except Exception as e:
        logger.warning(f"序列化结果失败 {tool_name}: {e}，跳过摘要")
        return result
    
    if len(result_str) <= max_length:
        return serializable_result
    
    # 根据工具类型选择摘要器
    tool_type = tool_name.split("_")[0]  # 提取工具类型前缀
    summarizer = TOOL_SUMMARIZERS.get(tool_type)
    
    if summarizer:
        try:
            data = serializable_result.get("data", {})
            summarized_data = summarizer(data)
            
            return {
                "tool": serializable_result.get("tool"),
                "ok": serializable_result.get("ok"),
                "data": summarized_data,
                "summarized": True,
                "original_size": len(result_str)
            }
        except Exception as e:
            logger.warning(f"摘要工具结果失败 {tool_name}: {e}")
            # 失败时返回截断的原始结果
            return {
                "tool": serializable_result.get("tool"),
                "ok": serializable_result.get("ok"),
                "data": {"raw": result_str[:max_length] + "...", "truncated": True}
            }
    
    # 没有对应的摘要器，直接截断
    return {
        "tool": serializable_result.get("tool"),
        "ok": serializable_result.get("ok"),
        "data": {"raw": result_str[:max_length] + "...", "truncated": True}
    }

