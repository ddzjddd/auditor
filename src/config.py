"""
统一配置管理系统
使用 Pydantic Settings 进行配置验证和管理
"""
try:
    from pydantic_settings import BaseSettings
except ImportError:
    # 兼容旧版本
    from pydantic import BaseSettings

from pydantic import Field
from typing import Optional
from pathlib import Path


class AuditConfig(BaseSettings):
    """审计Agent配置"""
    
    # LLM配置
    deepseek_api_key: Optional[str] = Field(None, description="DeepSeek API密钥")
    deepseek_base_url: str = Field("https://api.deepseek.com/v1", description="DeepSeek API地址")
    openai_api_key: Optional[str] = Field(None, description="OpenAI API密钥")
    dashscope_api_key: Optional[str] = Field(None, description="阿里云DashScope API密钥")
    model_name: str = Field("deepseek-reasoner", description="思考模式")
    
    # Hardhat Network配置
    hardhat_rpc_url: str = Field("http://localhost:8545", description="Hardhat Network RPC URL")
    hardhat_fork_url: Optional[str] = Field(None, description="默认Fork网络RPC URL（可选）")
    
    # Embedding配置
    embedding_model: Optional[str] = Field(None, description="Embedding模型名称")
    
    # Agent配置
    max_tool_iterations: int = Field(15, description="最大工具调用轮次")
    tool_timeout: int = Field(120, description="工具执行超时时间（秒）")
    temperature: float = Field(0.1, description="LLM温度参数")
    max_tokens: int = Field(2048, description="LLM最大输出token数")
    
    # RAG配置
    rag_top_k: int = Field(5, description="RAG检索返回top-k结果")
    corpus_dir: str = Field("src/rag/corpus", description="知识库目录")
    index_dir: str = Field("src/rag/index", description="索引目录")
    
    # 缓存配置
    enable_cache: bool = Field(True, description="是否启用工具结果缓存")
    cache_dir: str = Field(".cache", description="缓存目录")
    cache_ttl: int = Field(3600, description="缓存TTL（秒）")
    
    # 日志配置
    log_level: str = Field("INFO", description="日志级别")
    log_file: Optional[str] = Field(None, description="日志文件路径")
    enable_json_log: bool = Field(False, description="是否使用JSON格式日志")
    
    # 报告配置
    report_output_dir: str = Field("reports", description="报告输出目录")
    report_template: str = Field("src/report/template.md", description="报告模板路径")
    
    # 审计目标配置
    default_contract_dir: str = Field("contracts", description="默认合约目录")
    default_target: Optional[str] = Field(None, description="默认审计目标（文件或目录路径）")
    
    # 重试配置
    max_retries: int = Field(3, description="最大重试次数")
    retry_backoff: float = Field(1.5, description="重试退避系数")
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False


# 全局配置实例
_config: Optional[AuditConfig] = None


def get_config() -> AuditConfig:
    """获取配置实例（单例模式）"""
    global _config
    if _config is None:
        _config = AuditConfig()
    return _config


def reload_config() -> AuditConfig:
    """重新加载配置"""
    global _config
    _config = AuditConfig()
    return _config

