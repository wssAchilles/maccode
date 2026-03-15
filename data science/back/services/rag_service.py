"""
文档 RAG 问答服务 (Retrieval-Augmented Generation Service)
实现对项目文档的向量嵌入和语义检索

功能：
1. 文档加载与分块
2. 向量嵌入创建
3. 语义检索
4. 上下文增强回答
"""

import os
import re
import tempfile
from typing import Dict, List, Optional, Any, Union
from pathlib import Path
import warnings
import pandas as pd

# 延迟加载变量
_SENTENCE_TRANSFORMERS_AVAILABLE = None
_CHROMADB_AVAILABLE = None
_TFIDF_BACKEND_AVAILABLE = None
SentenceTransformer = None
chromadb = None
Settings = None

# NumPy 用于向量计算
import numpy as np

from services.storage_service import StorageService


class Document:
    """文档数据类"""
    def __init__(self, content: str, metadata: Optional[Dict] = None):
        self.content = content
        self.metadata = metadata or {}
    
    def __repr__(self):
        preview = self.content[:100] + "..." if len(self.content) > 100 else self.content
        return f"Document(content='{preview}', metadata={self.metadata})"


class RAGService:
    """
    RAG (Retrieval-Augmented Generation) 服务
    
    使用向量嵌入进行语义检索，增强问答能力
    """
    
    def __init__(
        self,
        model_name: str = 'paraphrase-multilingual-MiniLM-L12-v2',
        collection_name: str = 'project_docs'
    ):
        """
        初始化 RAG 服务
        
        Args:
            model_name: Sentence Transformer 模型名称
            collection_name: ChromaDB 集合名称
        """
        self.model_name = model_name
        self.collection_name = collection_name
        self.model = None
        self.chroma_client = None
        self.collection = None
        self.documents = []
        self._fallback_index = None
        self._storage = None
        
        # 不再在初始化时强制加载，改为按需加载或检查
        # self._initialize() 将在第一次使用功能时尝试运行
    
    @staticmethod
    def _ensure_dependencies():
        """延迟加载依赖"""
        global _SENTENCE_TRANSFORMERS_AVAILABLE, _CHROMADB_AVAILABLE
        global _TFIDF_BACKEND_AVAILABLE
        global SentenceTransformer, chromadb, Settings
        
        if _SENTENCE_TRANSFORMERS_AVAILABLE is None:
            try:
                from sentence_transformers import SentenceTransformer as _ST
                SentenceTransformer = _ST
                _SENTENCE_TRANSFORMERS_AVAILABLE = True
            except ImportError:
                _SENTENCE_TRANSFORMERS_AVAILABLE = False
                warnings.warn("sentence-transformers 未安装。安装命令: pip install sentence-transformers")

        if _CHROMADB_AVAILABLE is None:
            try:
                import chromadb as _chromadb
                from chromadb.config import Settings as _Settings
                chromadb = _chromadb
                Settings = _Settings
                _CHROMADB_AVAILABLE = True
            except ImportError:
                _CHROMADB_AVAILABLE = False
                warnings.warn("chromadb 未安装。安装命令: pip install chromadb")

        if _TFIDF_BACKEND_AVAILABLE is None:
            try:
                from sklearn.feature_extraction.text import TfidfVectorizer  # noqa: F401
                from sklearn.metrics.pairwise import cosine_similarity  # noqa: F401
                import joblib  # noqa: F401

                _TFIDF_BACKEND_AVAILABLE = True
            except ImportError:
                _TFIDF_BACKEND_AVAILABLE = False

        return {
            'sentence_transformers': _SENTENCE_TRANSFORMERS_AVAILABLE,
            'chromadb': _CHROMADB_AVAILABLE,
            'tfidf_backend': _TFIDF_BACKEND_AVAILABLE,
        }

    @staticmethod
    def _full_backend_available() -> bool:
        deps = RAGService._ensure_dependencies()
        return bool(deps['sentence_transformers'] and deps['chromadb'])

    def _storage_service(self) -> StorageService:
        if self._storage is None:
            self._storage = StorageService()
        return self._storage

    def _index_storage_path(self) -> str:
        safe_name = re.sub(r'[^a-zA-Z0-9_.-]+', '_', self.collection_name).strip('._') or 'default'
        return f'rag_indices/{safe_name}.joblib'

    def _ensure_fallback_index_loaded(self) -> Optional[Dict[str, Any]]:
        if self._fallback_index is not None:
            return self._fallback_index
        storage = self._storage_service()
        index_path = self._index_storage_path()
        if not storage.file_exists(index_path):
            return None
        raw_bytes = storage.download_file(index_path)
        with tempfile.NamedTemporaryFile(suffix='.joblib', delete=False) as temp_file:
            temp_file.write(raw_bytes)
            temp_path = temp_file.name
        try:
            import joblib

            self._fallback_index = joblib.load(temp_path)
        finally:
            try:
                os.remove(temp_path)
            except OSError:
                pass
        return self._fallback_index

    def _persist_fallback_index(self, index_payload: Dict[str, Any]) -> None:
        import joblib

        with tempfile.NamedTemporaryFile(suffix='.joblib', delete=False) as temp_file:
            temp_path = temp_file.name
        try:
            joblib.dump(index_payload, temp_path)
            with open(temp_path, 'rb') as handle:
                self._storage_service().upload_file(
                    handle,
                    self._index_storage_path(),
                    content_type='application/octet-stream',
                )
        finally:
            try:
                os.remove(temp_path)
            except OSError:
                pass

    def _document_key(self, doc: Document) -> str:
        metadata = doc.metadata or {}
        return '|'.join(
            [
                str(metadata.get('source', '')),
                str(metadata.get('filename', '')),
                str(metadata.get('chunk_index', '')),
                doc.content[:120],
            ]
        )

    def _build_fallback_index(self, documents: List[Document], *, reset: bool = False) -> Dict[str, Any]:
        from sklearn.feature_extraction.text import TfidfVectorizer

        merged_documents = list(documents)
        if not reset:
            existing = self._ensure_fallback_index_loaded()
            if existing:
                existing_docs = [
                    Document(
                        content=item.get('content', ''),
                        metadata=dict(item.get('metadata') or {}),
                    )
                    for item in existing.get('documents', [])
                    if isinstance(item, dict) and item.get('content')
                ]
                seen = {self._document_key(doc) for doc in existing_docs}
                for doc in documents:
                    if self._document_key(doc) not in seen:
                        existing_docs.append(doc)
                        seen.add(self._document_key(doc))
                merged_documents = existing_docs

        texts = [doc.content for doc in merged_documents if doc.content.strip()]
        if not texts:
            raise RuntimeError('没有可用于知识库构建的有效文档内容')

        vectorizer = TfidfVectorizer(
            max_features=8000,
            analyzer='char_wb',
            ngram_range=(2, 4),
            lowercase=False,
        )
        matrix = vectorizer.fit_transform(texts)
        payload = {
            'backend': 'tfidf_fallback',
            'collection_name': self.collection_name,
            'document_count': len(texts),
            'model_name': 'tfidf',
            'documents': [
                {'content': doc.content, 'metadata': dict(doc.metadata or {})}
                for doc in merged_documents
                if doc.content.strip()
            ],
            'vectorizer': vectorizer,
            'matrix': matrix,
        }
        self._fallback_index = payload
        self._persist_fallback_index(payload)
        return payload

    def reset_collection(self) -> None:
        if self._full_backend_available():
            self._initialize()
            if self.chroma_client is not None:
                try:
                    self.chroma_client.delete_collection(self.collection_name)
                except Exception:
                    pass
                self.collection = None
        else:
            storage = self._storage_service()
            index_path = self._index_storage_path()
            if storage.file_exists(index_path):
                try:
                    storage.delete_file(index_path)
                except Exception:
                    pass
            self._fallback_index = None

    def _initialize(self):
        """初始化模型和数据库 (如果尚未初始化)"""
        self._ensure_dependencies()
        if not self._full_backend_available():
            return
        
        if self.model is None and _SENTENCE_TRANSFORMERS_AVAILABLE:
            print(f"📦 加载嵌入模型: {self.model_name}")
            self.model = SentenceTransformer(self.model_name)
            print(f"   ✓ 模型加载完成")
        
        if self.collection is None and _CHROMADB_AVAILABLE:
            if self.chroma_client is None:
                # 使用内存数据库 (可改为持久化)
                self.chroma_client = chromadb.Client(Settings(anonymized_telemetry=False))
            
            self.collection = self.chroma_client.get_or_create_collection(
                name=self.collection_name,
                metadata={"hnsw:space": "cosine"}
            )
            print(f"   ✓ ChromaDB 集合就绪: {self.collection_name}")
    
    @staticmethod
    def is_available() -> Dict[str, bool]:
        """检查依赖可用性"""
        deps = RAGService._ensure_dependencies()
        full_backend = bool(deps['sentence_transformers'] and deps['chromadb'])
        fallback_backend = bool(deps['tfidf_backend'])
        return {
            'sentence_transformers': deps['sentence_transformers'],
            'chromadb': deps['chromadb'],
            'tfidf_backend': fallback_backend,
            'full_backend': full_backend,
            'available': full_backend or fallback_backend,
            'fully_available': full_backend,
        }
    
    def load_documents(
        self,
        doc_paths: Union[str, List[str]],
        chunk_size: int = 500,
        chunk_overlap: int = 50
    ) -> List[Document]:
        """
        加载文档并分块
        
        Args:
            doc_paths: 文档路径 (文件或目录)
            chunk_size: 每块最大字符数
            chunk_overlap: 块之间重叠字符数
            
        Returns:
            Document 列表
        """
        if isinstance(doc_paths, str):
            doc_paths = [doc_paths]
        
        all_docs = []
        
        for path in doc_paths:
            path = Path(path)
            
            if path.is_file():
                docs = self._load_single_file(path, chunk_size, chunk_overlap)
                all_docs.extend(docs)
            elif path.is_dir():
                # 递归加载目录
                for file_path in path.rglob('*'):
                    if file_path.is_file() and file_path.suffix.lower() in [
                        '.txt',
                        '.md',
                        '.py',
                        '.json',
                        '.csv',
                        '.xlsx',
                        '.xls',
                    ]:
                        docs = self._load_single_file(file_path, chunk_size, chunk_overlap)
                        all_docs.extend(docs)
        
        self.documents = all_docs
        print(f"📄 加载了 {len(all_docs)} 个文档块")
        return all_docs
    
    def _load_single_file(
        self,
        file_path: Path,
        chunk_size: int,
        chunk_overlap: int
    ) -> List[Document]:
        """加载单个文件并分块"""
        suffix = file_path.suffix.lower()
        if suffix in {'.csv', '.xlsx', '.xls'}:
            return self._load_tabular_file(file_path, chunk_size, chunk_overlap)

        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
        except Exception as e:
            print(f"   ⚠️ 无法读取 {file_path}: {e}")
            return []
        
        # 分块
        chunks = self._split_text(content, chunk_size, chunk_overlap)
        
        documents = []
        for i, chunk in enumerate(chunks):
            if chunk.strip():
                doc = Document(
                    content=chunk,
                    metadata={
                        'source': str(file_path),
                        'filename': file_path.name,
                        'chunk_index': i
                    }
                )
                documents.append(doc)
        
        return documents

    def _load_tabular_file(
        self,
        file_path: Path,
        chunk_size: int,
        chunk_overlap: int,
    ) -> List[Document]:
        """把结构化表格转成可检索的文档块。"""
        try:
            if file_path.suffix.lower() == '.csv':
                df = pd.read_csv(file_path, nrows=200)
            else:
                df = pd.read_excel(file_path, nrows=200)
        except Exception as e:
            print(f"   ⚠️ 无法解析表格 {file_path}: {e}")
            return []

        if df.empty:
            return []

        columns = [str(column) for column in df.columns]
        preview_columns = columns[: min(len(columns), 12)]
        lines = [
            f'文件名: {file_path.name}',
            f'数据列: {", ".join(preview_columns)}',
            f'样本行数: {len(df)}',
        ]

        for index, (_, row) in enumerate(df.head(80).iterrows(), start=1):
            fields = []
            for column in preview_columns:
                value = row.get(column)
                if pd.isna(value):
                    continue
                text = str(value).strip()
                if not text:
                    continue
                if len(text) > 80:
                    text = f'{text[:77]}...'
                fields.append(f'{column}={text}')
            if fields:
                lines.append(f'样本{index}: ' + ' | '.join(fields))

        content = '\n'.join(lines)
        chunks = self._split_text(content, chunk_size, chunk_overlap)
        return [
            Document(
                content=chunk,
                metadata={
                    'source': str(file_path),
                    'filename': file_path.name,
                    'file_type': 'tabular',
                    'chunk_index': index,
                },
            )
            for index, chunk in enumerate(chunks)
            if chunk.strip()
        ]
    
    def _split_text(self, text: str, chunk_size: int, overlap: int) -> List[str]:
        """简单文本分块"""
        if len(text) <= chunk_size:
            return [text]
        
        chunks = []
        start = 0
        
        while start < len(text):
            end = start + chunk_size
            
            # 尝试在句号或换行处断开
            if end < len(text):
                # 向前找断点
                for sep in ['\n\n', '\n', '。', '. ', '，', ', ']:
                    last_sep = text.rfind(sep, start, end)
                    if last_sep > start:
                        end = last_sep + len(sep)
                        break
            
            chunks.append(text[start:end])
            start = end - overlap
        
        return chunks
    
    def create_embeddings(self, documents: Optional[List[Document]] = None) -> int:
        """
        为文档创建向量嵌入并存入数据库
        
        Args:
            documents: 文档列表 (None 则使用已加载的文档)
            
        Returns:
            添加的文档数量
        """
        if documents is None:
            documents = self.documents
        
        if not documents:
            print("⚠️ 没有文档需要嵌入")
            return 0

        print(f"🔢 创建向量嵌入 ({len(documents)} 文档)...")
        if self._full_backend_available():
            self._initialize()

            texts = [doc.content for doc in documents]
            embeddings = self.model.encode(texts, show_progress_bar=True)
            ids = [f"doc_{i}" for i in range(len(documents))]
            metadatas = [doc.metadata for doc in documents]

            self.collection.add(
                ids=ids,
                embeddings=embeddings.tolist(),
                documents=texts,
                metadatas=metadatas,
            )
            print(f"   ✓ 已添加 {len(documents)} 个嵌入到向量数据库")
            return len(documents)

        if not self._ensure_dependencies().get('tfidf_backend'):
            raise RuntimeError('RAG 服务当前不可用 (缺少依赖)')

        payload = self._build_fallback_index(documents)
        print(f"   ✓ 已使用 TF-IDF fallback 构建 {payload['document_count']} 个文档片段")
        return int(payload['document_count'])
    
    def query(
        self,
        question: str,
        top_k: int = 3,
        include_metadata: bool = True
    ) -> List[Dict[str, Any]]:
        """
        语义检索相关文档
        
        Args:
            question: 查询问题
            top_k: 返回的最相关文档数量
            include_metadata: 是否包含元数据
            
        Returns:
            相关文档列表
        """
        if self._full_backend_available():
            self._initialize()

            question_embedding = self.model.encode([question])[0]
            results = self.collection.query(
                query_embeddings=[question_embedding.tolist()],
                n_results=top_k,
                include=['documents', 'metadatas', 'distances'],
            )

            formatted = []
            for i in range(len(results['ids'][0])):
                item = {
                    'id': results['ids'][0][i],
                    'content': results['documents'][0][i],
                    'distance': results['distances'][0][i],
                    'relevance_score': round(1 - results['distances'][0][i], 4),
                }
                if include_metadata and results['metadatas']:
                    item['metadata'] = results['metadatas'][0][i]
                formatted.append(item)

            return formatted

        fallback = self._ensure_fallback_index_loaded()
        if not fallback:
            return []

        from sklearn.metrics.pairwise import cosine_similarity

        vectorizer = fallback['vectorizer']
        matrix = fallback['matrix']
        documents = fallback.get('documents', [])
        query_vector = vectorizer.transform([question])
        similarities = cosine_similarity(query_vector, matrix).flatten()
        ranked_indices = np.argsort(similarities)[::-1][:top_k]

        formatted = []
        for index in ranked_indices:
            score = float(similarities[index])
            if score <= 0:
                continue
            item = documents[index]
            formatted.append(
                {
                    'id': f'doc_{index}',
                    'content': item.get('content', ''),
                    'distance': round(1 - score, 4),
                    'relevance_score': round(score, 4),
                    'metadata': dict(item.get('metadata') or {}) if include_metadata else None,
                }
            )
        return formatted
    
    def generate_context(self, question: str, top_k: int = 3) -> str:
        """
        生成问答上下文
        
        Args:
            question: 查询问题
            top_k: 使用的文档数量
            
        Returns:
            合并的上下文字符串
        """
        results = self.query(question, top_k)
        
        if not results:
            return ""
        
        context_parts = []
        for i, result in enumerate(results, 1):
            source = result.get('metadata', {}).get('filename', 'Unknown')
            context_parts.append(f"[来源 {i}: {source}]\n{result['content']}")
        
        return "\n\n---\n\n".join(context_parts)
    
    def answer_question(
        self,
        question: str,
        top_k: int = 3
    ) -> Dict[str, Any]:
        """
        回答问题 (基于检索的简单问答)
        
        Args:
            question: 用户问题
            top_k: 检索的文档数量
            
        Returns:
            问答结果
        """
        # 检索相关文档
        results = self.query(question, top_k)
        
        if not results:
            return {
                'success': False,
                'answer': '抱歉，没有找到相关信息。',
                'sources': []
            }
        
        # 构建回答 (简单版：返回最相关的内容)
        # 生产环境可接入 LLM 生成更自然的回答
        context = results[0]['content']
        sources = [r.get('metadata', {}).get('source', 'Unknown') for r in results]
        context_blocks = [
            {
                'source': r.get('metadata', {}).get('source', 'Unknown'),
                'filename': r.get('metadata', {}).get('filename', 'Unknown'),
                'snippet': r.get('content', ''),
                'relevance_score': r.get('relevance_score'),
            }
            for r in results
        ]
        
        return {
            'success': True,
            'answer': context,
            'context': context_blocks,
            'context_text': self.generate_context(question, top_k),
            'sources': list(set(sources)),
            'relevance_scores': [r['relevance_score'] for r in results]
        }
    
    def get_stats(self) -> Dict[str, Any]:
        """获取向量数据库统计"""
        if self._full_backend_available():
            self._initialize()
            if self.collection is None:
                return {'error': 'Collection not initialized'}

            return {
                'collection_name': self.collection_name,
                'document_count': self.collection.count(),
                'model_name': self.model_name,
                'backend': 'vector',
            }

        fallback = self._ensure_fallback_index_loaded()
        if not fallback:
            return {
                'collection_name': self.collection_name,
                'document_count': 0,
                'model_name': 'tfidf',
                'backend': 'tfidf_fallback',
            }

        return {
            'collection_name': fallback.get('collection_name', self.collection_name),
            'document_count': int(fallback.get('document_count', 0)),
            'model_name': fallback.get('model_name', 'tfidf'),
            'backend': fallback.get('backend', 'tfidf_fallback'),
        }


# 测试代码
if __name__ == "__main__":
    print(f"RAG 依赖可用性: {RAGService.is_available()}")
    
    if RAGService.is_available()['fully_available']:
        # 创建测试文档
        test_docs = [
            Document("LSTM 是一种循环神经网络，适用于时序预测。它通过门控机制解决梯度消失问题。", 
                    {"source": "dl_intro.txt"}),
            Document("Gurobi 是一个商业优化求解器，支持线性规划、整数规划和混合整数规划。",
                    {"source": "gurobi_intro.txt"}),
            Document("SHAP 值用于解释机器学习模型的预测，计算每个特征对预测的贡献。",
                    {"source": "shap_intro.txt"})
        ]
        
        # 初始化 RAG
        rag = RAGService()
        rag.documents = test_docs
        rag.create_embeddings()
        
        # 测试查询
        print("\n🔍 测试查询: '什么是 LSTM？'")
        results = rag.query("什么是 LSTM？", top_k=2)
        for r in results:
            print(f"   相关度: {r['relevance_score']}, 内容: {r['content'][:50]}...")
        
        # 测试问答
        print("\n💬 测试问答")
        answer = rag.answer_question("如何解释模型预测？") 
        print(f"   回答: {answer['answer'][:100]}...")
        print(f"   来源: {answer['sources']}")
