"""
工具参数验证模型
使用 Pydantic 进行参数类型验证和文档生成
"""
from pydantic import BaseModel, Field, validator
from typing import Optional, List
from pathlib import Path


class SlitherScanArgs(BaseModel):
    """Slither扫描参数"""
    target: str = Field(..., description="文件路径或项目根目录")
    config: Optional[str] = Field(None, description="Slither配置文件路径")
    
    @validator('target')
    def validate_target(cls, v):
        if not Path(v).exists():
            raise ValueError(f"目标路径不存在: {v}")
        return str(Path(v).absolute())


class MythrilScanArgs(BaseModel):
    """Mythril扫描参数"""
    bytecode: str = Field(..., description="合约字节码（hex格式）")
    entry: Optional[str] = Field(None, description="入口函数名")
    timeout: int = Field(120, ge=10, le=600, description="执行超时时间（秒）")
    
    @validator('bytecode')
    def validate_bytecode(cls, v):
        v = v.strip()
        if not v.startswith('0x'):
            v = '0x' + v
        if len(v) < 4:
            raise ValueError("字节码长度不足")
        return v


class ForgeCompileArgs(BaseModel):
    """Forge编译参数"""
    root_dir: str = Field(..., description="项目根目录")
    evm_version: Optional[str] = Field(None, description="EVM版本")
    opt_runs: int = Field(200, ge=0, le=10000, description="优化器运行次数")
    timeout: int = Field(60, ge=10, le=300, description="编译超时时间（秒）")
    
    @validator('root_dir')
    def validate_root_dir(cls, v):
        if not Path(v).exists():
            raise ValueError(f"项目根目录不存在: {v}")
        return str(Path(v).absolute())


class ChainStateArgs(BaseModel):
    """链状态查询参数"""
    chain: str = Field(..., description="链名称（ethereum/arbitrum/bsc/polygon）")
    address: str = Field(..., description="合约地址")
    
    @validator('chain')
    def validate_chain(cls, v):
        allowed = ["ethereum", "arbitrum", "bsc", "polygon", "optimism", "base"]
        if v.lower() not in allowed:
            raise ValueError(f"不支持的链: {v}，支持的链: {allowed}")
        return v.lower()
    
    @validator('address')
    def validate_address(cls, v):
        if not v.startswith('0x') or len(v) != 42:
            raise ValueError(f"无效的地址格式: {v}")
        return v


class RAGSearchArgs(BaseModel):
    """RAG检索参数"""
    query: str = Field(..., min_length=1, max_length=500, description="检索查询")
    k: int = Field(5, ge=1, le=20, description="返回结果数量")


class ReadFileArgs(BaseModel):
    """读取文件参数"""
    file_path: str = Field(..., description="文件路径（相对或绝对路径）")
    max_lines: int = Field(1000, ge=1, le=10000, description="最大读取行数（防止文件过大）")
    encoding: str = Field("utf-8", description="文件编码")
    
    @validator('file_path')
    def validate_file_path(cls, v):
        if not v or not v.strip():
            raise ValueError("文件路径不能为空")
        return v.strip()


class EchidnaTestArgs(BaseModel):
    """Echidna模糊测试参数"""
    target: str = Field(..., description="测试文件路径或项目根目录")
    config: Optional[str] = Field(None, description="Echidna配置文件路径")
    test_mode: str = Field("property", description="测试模式 (property/assertion)")
    timeout: int = Field(300, ge=10, le=3600, description="执行超时时间（秒）")
    seq_len: int = Field(100, ge=1, le=1000, description="测试序列长度")
    
    @validator('target')
    def validate_target(cls, v):
        if not Path(v).exists():
            raise ValueError(f"目标路径不存在: {v}")
        return str(Path(v).absolute())
    
    @validator('test_mode')
    def validate_test_mode(cls, v):
        if v not in ["property", "assertion"]:
            raise ValueError("test_mode必须是'property'或'assertion'")
        return v


class SemgrepScanArgs(BaseModel):
    """Semgrep扫描参数"""
    target: str = Field(..., description="文件路径或项目根目录")
    config: Optional[str] = Field(None, description="Semgrep配置（规则集或配置文件，如'p/solidity'）")
    severity: Optional[str] = Field(None, description="过滤严重程度 (ERROR/WARNING/INFO)")
    output_format: str = Field("json", description="输出格式 (json/text)")
    
    @validator('target')
    def validate_target(cls, v):
        if not Path(v).exists():
            raise ValueError(f"目标路径不存在: {v}")
        return str(Path(v).absolute())
    
    @validator('severity')
    def validate_severity(cls, v):
        if v and v.upper() not in ["ERROR", "WARNING", "INFO"]:
            raise ValueError("severity必须是ERROR、WARNING或INFO")
        return v.upper() if v else None


class AnalyzerScanArgs(BaseModel):
    """4naly3er Gas分析参数"""
    target: str = Field(..., description="文件路径或项目根目录")
    report_format: str = Field("json", description="报告格式 (json/md/txt)")
    no_optimizations: bool = Field(False, description="是否禁用优化建议")
    
    @validator('target')
    def validate_target(cls, v):
        if not Path(v).exists():
            raise ValueError(f"目标路径不存在: {v}")
        return str(Path(v).absolute())
    
    @validator('report_format')
    def validate_report_format(cls, v):
        if v not in ["json", "md", "txt"]:
            raise ValueError("report_format必须是json、md或txt")
        return v


class HardhatNetworkArgs(BaseModel):
    """Hardhat Network 本地测试网络参数"""
    transaction: dict = Field(..., description="交易对象，包含from/to/input/value/gas等字段")
    fork_url: Optional[str] = Field(None, description="Fork的网络RPC URL（可选，用于fork主网状态）")
    fork_block: Optional[int] = Field(None, description="Fork的区块号（可选）")
    rpc_url: Optional[str] = Field(None, description="Hardhat节点RPC URL（可选，默认http://localhost:8545）")
    
    @validator('transaction')
    def validate_transaction(cls, v):
        if not isinstance(v, dict):
            raise ValueError("transaction必须是字典")
        required_fields = ["from", "to", "input"]
        for field in required_fields:
            if field not in v:
                raise ValueError(f"transaction缺少必需字段: {field}")
        return v
    
    @validator('fork_url')
    def validate_fork_url(cls, v):
        if v and not (v.startswith("http://") or v.startswith("https://")):
            raise ValueError("fork_url必须是有效的HTTP/HTTPS URL")
        return v


# 工具参数模型映射
TOOL_ARGS_MODELS = {
    "slither_scan": SlitherScanArgs,
    "mythril_scan": MythrilScanArgs,
    "forge_compile": ForgeCompileArgs,
    "read_chain_state": ChainStateArgs,
    "rag_search": RAGSearchArgs,
    "read_file": ReadFileArgs,
    "echidna_test": EchidnaTestArgs,
    "semgrep_scan": SemgrepScanArgs,
    "analyzer_scan": AnalyzerScanArgs,
    "hardhat_simulate": HardhatNetworkArgs,
}

