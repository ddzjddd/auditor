# src/rag/build_index.py
import os, json, faiss, numpy as np, pickle
from tqdm import tqdm
from rank_bm25 import BM25Okapi
from dotenv import load_dotenv

load_dotenv()

# 优先顺序: Qwen → OpenAI → DeepSeek
use_qwen = bool(os.getenv("DASHSCOPE_API_KEY"))
use_openai = bool(os.getenv("OPENAI_API_KEY"))
use_deepseek = bool(os.getenv("DEEPSEEK_API_KEY"))

if not (use_qwen or use_openai or use_deepseek):
    raise ValueError("请在 .env 中设置 DASHSCOPE_API_KEY 或 OPENAI_API_KEY 或 DEEPSEEK_API_KEY")

embedding_model = (
    os.getenv("EMBEDDING_MODEL")
    or ("text-embedding-v2" if use_qwen else "text-embedding-3-large")
)

if use_qwen:
    print(f"🚀 使用 Qwen 模型生成 Embedding: {embedding_model}")
    from dashscope import TextEmbedding

    def embed_batch(texts):
        vecs = []
        for t in tqdm(texts, desc="Embedding with Qwen"):
            try:
                resp = TextEmbedding.call(
                    model=embedding_model,
                    input=t,
                    api_key=os.getenv("DASHSCOPE_API_KEY"),
                )
                vec = resp["output"]["embeddings"][0]["embedding"]
                vecs.append(vec)
            except Exception as e:
                print(f"⚠️ Qwen embedding 失败: {e}")
                vecs.append([0.0] * 1536)
        return np.array(vecs, dtype="float32")

elif use_openai:
    print(f"🚀 使用 OpenAI 模型生成 Embedding: {embedding_model}")
    from openai import OpenAI
    client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

    def embed_batch(texts):
        resp = client.embeddings.create(model=embedding_model, input=texts)
        return np.array([d.embedding for d in resp.data], dtype="float32")

else:
    print(f"🚀 使用 DeepSeek 模型生成 Embedding: {embedding_model}")
    from openai import OpenAI
    base_url = os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com/v1")
    client = OpenAI(api_key=os.getenv("DEEPSEEK_API_KEY"), base_url=base_url)

    def embed_batch(texts):
        try:
            resp = client.embeddings.create(model=embedding_model, input=texts)
            return np.array([d.embedding for d in resp.data], dtype="float32")
        except Exception as e:
            raise ValueError(
                f"⚠️ DeepSeek embedding 不可用。建议改用 Qwen 或 OpenAI。\n错误信息: {e}"
            )


# ---------------- Corpus ----------------
corpus_dir = "src/rag/corpus"
index_dir = "src/rag/index"
os.makedirs(index_dir, exist_ok=True)

def chunk_text(text, max_tokens=600):
    paras = text.split("\n\n")
    out, buf = [], ""
    for p in paras:
        if len(buf) + len(p) > max_tokens:
            out.append(buf.strip())
            buf = ""
        buf += p + "\n\n"
    if buf.strip():
        out.append(buf.strip())
    return out

texts, metas = [], []
for root, _, files in os.walk(corpus_dir):
    for f in files:
        if not f.endswith((".md", ".txt", ".json")):
            continue
        path = os.path.join(root, f)
        content = open(path, encoding="utf-8").read()
        chunks = chunk_text(content)
        for i, ch in enumerate(chunks):
            texts.append(ch)
            metas.append({"source": path, "chunk_id": i})

print(f"📚 共 {len(texts)} 个文本块。开始生成 Embedding…")

# ---------------- Embedding ----------------
vecs = embed_batch(texts)

# 向量标准化 + 写入 Faiss
faiss.normalize_L2(vecs)
index = faiss.IndexFlatIP(vecs.shape[1])
index.add(vecs)
faiss.write_index(index, os.path.join(index_dir, "faiss.index"))

# 存 metadata
with open(os.path.join(index_dir, "meta.json"), "w", encoding="utf-8") as f:
    json.dump({"metas": metas, "texts": texts}, f, ensure_ascii=False, indent=2)

# 构建 BM25
bm25 = BM25Okapi([t.split() for t in texts])
with open(os.path.join(index_dir, "bm25.pkl"), "wb") as f:
    pickle.dump(bm25, f)

print("✅ 向量索引与BM25构建完成。")
