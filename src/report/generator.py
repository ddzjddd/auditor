"""
自动化报告生成器
从审计会话生成结构化报告
"""
import json
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any, Optional
from loguru import logger

from config import get_config


class ReportGenerator:
    """报告生成器"""
    
    def __init__(self):
        self.config = get_config()
        self.template_path = Path(self.config.report_template)
        self.output_dir = Path(self.config.report_output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        if not self.template_path.exists():
            logger.warning(f"报告模板不存在: {self.template_path}，使用默认模板")
            self.template = self._get_default_template()
        else:
            self.template = self.template_path.read_text(encoding="utf-8")
    
    def _get_default_template(self) -> str:
        """默认报告模板"""
        return """# 审计报告
- 目标：{target}
- 日期：{date}
- 工具：{tools_used}

## 摘要
{summary}

## 发现列表
{findings}

## 部署与治理
{governance}

## 覆盖与限制
{coverage}
"""
    
    def _extract_findings(self, session_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """从会话数据中提取漏洞发现"""
        findings = []
        
        # 从工具调用结果中提取
        tool_calls = session_data.get("tool_calls", [])
        for tool_call in tool_calls:
            result = tool_call.get("result", {})
            if not result.get("ok"):
                continue
            
            tool_name = tool_call.get("name", "")
            data = result.get("data", {})
            
            if tool_name == "slither_scan":
                # 提取Slither检测结果
                detectors = data.get("detectors", [])
                if isinstance(detectors, list):
                    for det in detectors:
                        findings.append({
                            "severity": det.get("impact", "Unknown"),
                            "title": det.get("check", "Unknown"),
                            "description": det.get("description", ""),
                            "locations": det.get("elements", []),
                            "source": "Slither"
                        })
            
            elif tool_name == "mythril_scan":
                # 提取Mythril检测结果
                issues = data.get("issues", [])
                if isinstance(issues, list):
                    for issue in issues:
                        findings.append({
                            "severity": issue.get("severity", "Unknown"),
                            "title": issue.get("title", "Unknown"),
                            "description": issue.get("description", ""),
                            "swc_id": issue.get("swc-id"),
                            "source": "Mythril"
                        })
        
        return findings
    
    def _categorize_findings(self, findings: List[Dict[str, Any]]) -> Dict[str, List[Dict[str, Any]]]:
        """按严重程度分类漏洞"""
        categorized = {
            "Critical": [],
            "High": [],
            "Medium": [],
            "Low": [],
            "Informational": [],
            "Unknown": []
        }
        
        for finding in findings:
            severity = finding.get("severity", "Unknown")
            # 标准化严重程度
            severity_map = {
                "Critical": ["Critical", "critical"],
                "High": ["High", "high"],
                "Medium": ["Medium", "medium"],
                "Low": ["Low", "low"],
                "Informational": ["Informational", "informational", "Info", "info"]
            }
            
            found = False
            for cat, keywords in severity_map.items():
                if severity in keywords:
                    categorized[cat].append(finding)
                    found = True
                    break
            
            if not found:
                categorized["Unknown"].append(finding)
        
        return categorized
    
    def _format_finding(self, finding: Dict[str, Any], index: int, severity_prefix: str) -> str:
        """格式化单个漏洞发现"""
        title = finding.get("title", "Unknown")
        description = finding.get("description", "")
        locations = finding.get("locations", [])
        source = finding.get("source", "")
        
        lines = [f"### [{severity_prefix}-{index:02d}] {title}"]
        lines.append(f"- **来源**: {source}")
        lines.append(f"- **描述**: {description}")
        
        if locations:
            lines.append("- **位置**:")
            for loc in locations[:3]:  # 只显示前3个位置
                if isinstance(loc, dict):
                    file = loc.get("source_mapping", {}).get("filename_absolute", "")
                    line = loc.get("source_mapping", {}).get("lines", [None])[0]
                    if file:
                        file = Path(file).name
                        lines.append(f"  - {file}:{line}" if line else f"  - {file}")
        
        swc_id = finding.get("swc_id")
        if swc_id:
            lines.append(f"- **SWC-ID**: {swc_id}")
        
        return "\n".join(lines)
    
    def generate(self, session_data: Dict[str, Any], target: str = "Unknown") -> str:
        """
        生成报告
        
        Args:
            session_data: 审计会话数据
            target: 审计目标
        
        Returns:
            报告内容
        """
        # 提取发现
        findings = self._extract_findings(session_data)
        categorized = self._categorize_findings(findings)
        
        # 生成摘要
        summary_lines = []
        for severity in ["Critical", "High", "Medium", "Low", "Informational"]:
            count = len(categorized[severity])
            if count > 0:
                summary_lines.append(f"{severity}: {count}")
        
        summary = ", ".join(summary_lines) if summary_lines else "未发现漏洞"
        
        # 生成发现列表
        findings_text = []
        index = 1
        for severity in ["Critical", "High", "Medium", "Low", "Informational"]:
            if categorized[severity]:
                findings_text.append(f"## {severity} 级别")
                for finding in categorized[severity]:
                    findings_text.append(self._format_finding(finding, index, severity[0]))
                    index += 1
        
        findings_text = "\n\n".join(findings_text) if findings_text else "未发现漏洞"
        
        # 提取使用的工具
        tool_calls = session_data.get("tool_calls", [])
        tools_used = list(set([tc.get("name", "") for tc in tool_calls]))
        tools_used_str = ", ".join(tools_used) if tools_used else "无"
        
        # 填充模板
        report = self.template.format(
            target=target,
            date=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            tools_used=tools_used_str,
            summary=summary,
            findings=findings_text,
            governance="待补充",
            coverage="待补充"
        )
        
        return report
    
    def save(self, report: str, filename: Optional[str] = None) -> Path:
        """
        保存报告到文件
        
        Args:
            report: 报告内容
            filename: 文件名（可选）
        
        Returns:
            保存的文件路径
        """
        if filename is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"audit_report_{timestamp}.md"
        
        filepath = self.output_dir / filename
        filepath.write_text(report, encoding="utf-8")
        logger.info(f"报告已保存: {filepath}")
        
        return filepath


def generate_report_from_session(session_data: Dict[str, Any], target: str = "Unknown") -> str:
    """从会话数据生成报告的便捷函数"""
    generator = ReportGenerator()
    return generator.generate(session_data, target)

