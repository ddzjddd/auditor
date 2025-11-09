# src/rag/retriever.py
import os
import json
import sys
from pathlib import Path
from typing import Optional
import faiss
import numpy as np
import pickle
from rank_bm25 import BM25Okapi
from openai import OpenAI

# 添加父目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from config import get_config
from tools.schemas import RAGSearchArgs
from utils.cache import cached_tool
from utils.retry import retry_with_backoff, RetryableError, NonRetryableError
from utils.logger import get_logger

logger = get_logger()


class RAGRetriever:
    """RAG检索器（延迟加载）"""
    
    def __init__(self):
        self.config = get_config()
        self._faiss_index: Optional[faiss.Index] = None
        self._texts: Optional[list] = None
        self._metas: Optional[list] = None
        self._bm25: Optional[BM25Okapi] = None
        self._embedding_client: Optional[OpenAI] = None
        self._embedding_model: Optional[str] = None
        self._last_query: Optional[str] = None
        self._initialized = False
    
    def _ensure_initialized(self):
        """确保索引已加载（延迟加载）"""
        if self._initialized:
            return
        
        index_dir = Path(self.config.index_dir)
        faiss_path = index_dir / "faiss.index"
        meta_path = index_dir / "meta.json"
        bm25_path = index_dir / "bm25.pkl"
        
        # 检查索引文件是否存在
        if not faiss_path.exists():
            raise FileNotFoundError(
                f"FAISS索引文件不存在: {faiss_path}\n"
                f"请先运行: python src/rag/build_index.py"
            )
        if not meta_path.exists():
            raise FileNotFoundError(
                f"元数据文件不存在: {meta_path}\n"
                f"请先运行: python src/rag/build_index.py"
            )
        if not bm25_path.exists():
            raise FileNotFoundError(
                f"BM25索引文件不存在: {bm25_path}\n"
                f"请先运行: python src/rag/build_index.py"
            )
        
        try:
            # 加载索引
            logger.info("加载RAG索引...")
            self._faiss_index = faiss.read_index(str(faiss_path))
            
            with open(meta_path, 'r', encoding='utf-8') as f:
                meta = json.load(f)
            self._texts = meta.get("texts", [])
            self._metas = meta.get("metas", [])
            
            with open(bm25_path, 'rb') as f:
                self._bm25 = pickle.load(f)
            
            # 初始化embedding客户端
            self._setup_embedding_client()
            
            self._initialized = True
            logger.info(f"RAG索引加载完成: {len(self._texts)} 个文档")
            
        except Exception as e:
            raise RuntimeError(f"加载RAG索引失败: {e}")
    
    def _setup_embedding_client(self):
        """设置embedding客户端"""
        # 优先顺序: Qwen → OpenAI → DeepSeek
        dashscope_key = self.config.dashscope_api_key
        openai_key = self.config.openai_api_key
        deepseek_key = self.config.deepseek_api_key
        
        self._embedding_model = self.config.embedding_model
        
        if dashscope_key:
            # 使用Qwen (DashScope)
            if not self._embedding_model:
                self._embedding_model = "text-embedding-v2"
            logger.info(f"使用Qwen Embedding: {self._embedding_model}")
            # Qwen需要特殊处理，这里先标记
            self._use_qwen = True
            try:
                from dashscope import TextEmbedding
                self._qwen_client = TextEmbedding
                self._qwen_api_key = dashscope_key
            except ImportError:
                raise ImportError("请安装 dashscope: pip install dashscope")
        elif openai_key:
            # 使用OpenAI
            if not self._embedding_model:
                self._embedding_model = "text-embedding-3-large"
            logger.info(f"使用OpenAI Embedding: {self._embedding_model}")
            self._embedding_client = OpenAI(api_key=openai_key)
            self._use_qwen = False
        elif deepseek_key:
            # 使用DeepSeek (可能不支持)
            if not self._embedding_model:
                self._embedding_model = "text-embedding-3-large"
            logger.warning(f"使用DeepSeek Embedding (可能不支持): {self._embedding_model}")
            base_url = self.config.deepseek_base_url
            self._embedding_client = OpenAI(api_key=deepseek_key, base_url=base_url)
            self._use_qwen = False
        else:
            raise ValueError("未设置任何embedding API密钥")
    
    def _embed(self, text: str) -> np.ndarray:
        """生成文本embedding"""
        self._ensure_initialized()
        
        if self._use_qwen:
            # 使用Qwen
            try:
                resp = self._qwen_client.call(
                    model=self._embedding_model,
                    input=text,
                    api_key=self._qwen_api_key
                )
                if resp.status_code == 200:
                    vec = resp["output"]["embeddings"][0]["embedding"]
                    return np.array([vec], dtype="float32")
                else:
                    raise RetryableError(f"Qwen embedding失败: {resp.message}")
            except Exception as e:
                raise RetryableError(f"Qwen embedding失败: {e}")
        else:
            # 使用OpenAI/DeepSeek
            try:
                resp = self._embedding_client.embeddings.create(
                    model=self._embedding_model,
                    input=text
                )
                return np.array([resp.data[0].embedding], dtype="float32")
            except Exception as e:
                if "404" in str(e) or "Not Found" in str(e):
                    raise NonRetryableError(
                        f"Embeddings endpoint不可用。请设置OPENAI_API_KEY或DASHSCOPE_API_KEY。"
                        f"原始错误: {e}"
                    )
                raise RetryableError(f"Embedding失败: {e}")
    
    @cached_tool("rag_search")
    @retry_with_backoff(retryable_exceptions=[ConnectionError, TimeoutError])
    def rag_search(self, query: str, k: int = 5) -> dict:
        """
        RAG检索
        
        Args:
            query: 检索查询
            k: 返回结果数量
        
        Returns:
            dict: {"tool": "rag_search", "ok": bool, "data": dict}
        """
        # 参数验证
        try:
            args = RAGSearchArgs(query=query, k=k)
            query = args.query
            k = int(args.k)  # 确保 k 是整数
            if k <= 0:
                k = 5  # 默认值
            if k > 20:
                k = 20  # 限制最大值
        except Exception as e:
            raise NonRetryableError(f"参数验证失败: {e}")
        
        # 重复查询检查
        if query == self._last_query:
            return {"tool": "rag_search", "ok": True, "summary": "重复查询已忽略。"}
        self._last_query = query
        
        logger.info(f"RAG检索: {query[:50]}...", tool_name="rag_search", tool_args={"query": query, "k": k})
        
        try:
            self._ensure_initialized()
            
            # 生成embedding
            emb = self._embed(query)
            # 确保 emb 是 2D 数组
            if emb.ndim == 1:
                emb = emb.reshape(1, -1)
            faiss.normalize_L2(emb)
            
            # 确保 k 是整数
            search_k = int(k * 3)
            if search_k <= 0:
                search_k = 15  # 默认值
            
            # 向量检索
            D, I = self._faiss_index.search(emb, search_k)
            vec_results = []
            for j, i in enumerate(I[0]):
                # 确保所有值都是可序列化的基本类型
                text = str(self._texts[i]) if self._texts[i] else ""
                meta = self._metas[i] if i < len(self._metas) else {}
                # 确保距离值是 Python float，不是 numpy float
                score_val = D[0][j]
                if hasattr(score_val, 'item'):  # numpy scalar
                    score_val = score_val.item()
                score_val = float(score_val)
                vec_results.append((text, meta, score_val))
            
            # 关键词检索
            kw_results = self._bm25.get_top_n(query.split(), self._texts, n=k)
            merged = vec_results[:k] + [(str(t) if t else "", {}, 0.5) for t in kw_results]
            
            # 去重并确保可序列化
            unique, seen = [], set()
            for t, m, s in merged:
                # 使用内容的前100个字符作为去重键，避免内存问题
                content_key = t[:100] if t else ""
                if content_key not in seen:
                    seen.add(content_key)
                    # 确保meta是可序列化的字典，清理所有不可序列化的值
                    if isinstance(m, dict):
                        meta_dict = {}
                        for meta_key, meta_value in m.items():
                            # 确保键是字符串
                            key_str = str(meta_key) if not isinstance(meta_key, (str, int, float, bool)) else str(meta_key)
                            # 确保值是基本类型
                            if isinstance(meta_value, (str, int, float, bool, type(None))):
                                meta_dict[key_str] = meta_value
                            elif isinstance(meta_value, (list, tuple)):
                                # 列表/元组：递归清理
                                try:
                                    meta_dict[key_str] = [_make_json_serializable(item) for item in meta_value]
                                except:
                                    meta_dict[key_str] = str(meta_value)
                            elif hasattr(meta_value, '__str__'):
                                try:
                                    # 尝试转换为字符串
                                    meta_dict[key_str] = str(meta_value)
                                except:
                                    meta_dict[key_str] = repr(meta_value)
                            else:
                                meta_dict[key_str] = repr(meta_value)
                    else:
                        meta_dict = {}
                    
                    # 确保score是Python float
                    score_float = float(s) if s else 0.0
                    if hasattr(score_float, 'item'):  # numpy scalar
                        score_float = score_float.item()
                    
                    unique.append({
                        "content": str(t) if t else "",
                        "meta": meta_dict,
                        "score": float(score_float)
                    })
            
            # 限制结果数量（确保 k 是整数）
            k_int = int(k) if isinstance(k, (int, float, str)) else 5
            if k_int <= 0:
                k_int = 5
            if k_int > len(unique):
                k_int = len(unique)
            final_items = unique[:k_int]
            context = "\n\n".join([f"[文档{i}] {u['content']}" for i, u in enumerate(final_items)])
            summary = f"检索到 {len(final_items)} 条知识片段。"
            
            # 构建结果前先清理
            from utils.summarizer import _make_json_serializable
            
            result = {
                "tool": "rag_search",
                "ok": True,
                "summary": summary,
                "items": _make_json_serializable(final_items),
                "context": str(context)
            }
            
            # 确保结果完全可序列化（双重保险）
            try:
                import json
                json.dumps(result, ensure_ascii=False)  # 测试序列化
                logger.debug("RAG结果序列化测试通过")
            except (TypeError, ValueError) as e:
                logger.warning(f"⚠️ RAG结果包含不可序列化对象: {type(e).__name__}: {e}")
                logger.warning(f"序列化错误详情 - 错误类型: {type(e)}, 错误消息: {str(e)}")
                
                # 尝试找出具体是哪个字段导致的问题
                try:
                    logger.warning("🔍 开始检查各个字段的序列化状态...")
                    for key, value in result.items():
                        try:
                            json.dumps({key: value}, ensure_ascii=False)
                            logger.debug(f"字段 '{key}' 序列化正常")
                        except Exception as field_error:
                            logger.warning(f"❌ 字段 '{key}' 序列化失败: {type(field_error).__name__}: {field_error}")
                            logger.warning(f"   字段类型: {type(value).__name__}, 值预览: {repr(value)[:200]}")
                            
                            # 如果是 items 字段，进一步检查每个 item
                            if key == "items" and isinstance(value, list):
                                logger.warning(f"📋 检查 items 列表，共 {len(value)} 项")
                                for idx, item in enumerate(value):
                                    try:
                                        json.dumps(item, ensure_ascii=False)
                                    except Exception as item_error:
                                        logger.warning(f"  ❌ items[{idx}] 序列化失败: {type(item_error).__name__}: {item_error}")
                                        logger.warning(f"     item类型: {type(item).__name__}, 内容预览: {repr(item)[:300]}")
                                        # 检查 item 的每个字段
                                        if isinstance(item, dict):
                                            for item_key, item_value in item.items():
                                                try:
                                                    json.dumps({item_key: item_value}, ensure_ascii=False)
                                                except Exception as item_field_error:
                                                    logger.warning(f"    ❌ items[{idx}]['{item_key}'] 序列化失败: {type(item_field_error).__name__}: {item_field_error}")
                                                    logger.warning(f"       类型: {type(item_value).__name__}, 值: {repr(item_value)[:200]}")
                except Exception as debug_error:
                    logger.error(f"调试序列化问题时出错: {debug_error}")
                
                # 如果失败，进行深度清理
                logger.warning("🧹 开始深度清理结果...")
                result = _make_json_serializable(result)
                # 再次测试
                try:
                    json.dumps(result, ensure_ascii=False)
                    logger.warning("✅ 深度清理后序列化测试通过")
                except Exception as e2:
                    logger.error(f"❌ 深度清理后仍无法序列化: {type(e2).__name__}: {e2}")
                    logger.warning(f"清理后的结果类型: {type(result).__name__}, keys: {list(result.keys()) if isinstance(result, dict) else 'N/A'}")
                    # 返回最小化的可序列化结果
                    logger.warning("⚠️ 返回最小化结果以避免序列化错误")
                    result = {
                        "tool": "rag_search",
                        "ok": True,
                        "summary": summary,
                        "items": [{"content": str(item.get("content", ""))[:500], "score": float(item.get("score", 0.0))} for item in final_items],
                        "context": str(context)[:2000]
                    }
            
            logger.debug(f"RAG检索完成，返回 {len(result.get('items', []))} 个结果")
            return result
            
        except NonRetryableError as e:
            # 确保异常消息可序列化
            error_msg = str(e)[:500] if len(str(e)) > 500 else str(e)
            raise NonRetryableError(error_msg)
        except Exception as e:
            # 记录详细的错误信息用于调试
            error_type = type(e).__name__
            error_msg = str(e)
            logger.error(f"❌ RAG检索异常: {error_type}: {error_msg}")
            logger.warning(f"异常详细信息 - 类型: {error_type}, 消息: {error_msg}, 异常对象: {repr(e)[:500]}")
            
            # 如果是序列化相关错误，记录更多信息
            if "not JSON serializable" in error_msg or "序列化" in error_msg:
                logger.warning("🔍 检测到序列化相关错误，记录调用栈")
                import traceback
                logger.warning(f"调用栈:\n{traceback.format_exc()}")
            
            # 确保异常消息可序列化，避免包含对象引用
            if len(error_msg) > 500:
                error_msg = error_msg[:500] + "..."
            # 如果错误消息可能包含不可序列化对象，进一步清理
            if "RAGRetriever" in error_msg or "not JSON serializable" in error_msg:
                error_msg = f"{error_type}: 序列化错误"
            raise RetryableError(f"RAG检索失败: {error_msg}")


# 全局检索器实例（单例）
_retriever: Optional[RAGRetriever] = None


def get_retriever() -> RAGRetriever:
    """获取RAG检索器实例（单例）"""
    global _retriever
    if _retriever is None:
        _retriever = RAGRetriever()
    return _retriever


def rag_search(query: str, k: int = 5) -> dict:
    """RAG检索函数（兼容旧接口）"""
    # 确保 k 是整数
    try:
        k = int(k) if k is not None else 5
    except (ValueError, TypeError):
        k = 5
    return get_retriever().rag_search(query, k)


if __name__ == "__main__":
    print(rag_search("ERC20 reentrancy approve misuse")["summary"])
