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
from typing import Dict, List, Optional, Any, Union
from pathlib import Path
import warnings

# 延迟加载变量
_SENTENCE_TRANSFORMERS_AVAILABLE = None
_CHROMADB_AVAILABLE = None
SentenceTransformer = None
chromadb = None
Settings = None

# NumPy 用于向量计算
import numpy as np


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
        
        # 不再在初始化时强制加载，改为按需加载或检查
        # self._initialize() 将在第一次使用功能时尝试运行
    
    @staticmethod
    def _ensure_dependencies():
        """延迟加载依赖"""
        global _SENTENCE_TRANSFORMERS_AVAILABLE, _CHROMADB_AVAILABLE
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

        return {
            'sentence_transformers': _SENTENCE_TRANSFORMERS_AVAILABLE,
            'chromadb': _CHROMADB_AVAILABLE
        }

    def _initialize(self):
        """初始化模型和数据库 (如果尚未初始化)"""
        self._ensure_dependencies()
        
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
        return {
            'sentence_transformers': deps['sentence_transformers'],
            'chromadb': deps['chromadb'],
            'fully_available': deps['sentence_transformers'] and deps['chromadb']
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
                    if file_path.is_file() and file_path.suffix in ['.txt', '.md', '.py', '.json']:
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
        if not SENTENCE_TRANSFORMERS_AVAILABLE or not CHROMADB_AVAILABLE:
            raise RuntimeError("需要 sentence-transformers 和 chromadb 依赖")
        
        if documents is None:
            documents = self.documents
        
        if not documents:
            print("⚠️ 没有文档需要嵌入")
            return 0
        
        print(f"🔢 创建向量嵌入 ({len(documents)} 文档)...")
        
        # 提取文本
        texts = [doc.content for doc in documents]
        
        # 批量嵌入
        embeddings = self.model.encode(texts, show_progress_bar=True)
        
        # 存入 ChromaDB
        ids = [f"doc_{i}" for i in range(len(documents))]
        metadatas = [doc.metadata for doc in documents]
        
        self.collection.add(
            ids=ids,
            embeddings=embeddings.tolist(),
            documents=texts,
            metadatas=metadatas
        )
        
        print(f"   ✓ 已添加 {len(documents)} 个嵌入到向量数据库")
        return len(documents)
    
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
        if not SENTENCE_TRANSFORMERS_AVAILABLE or not CHROMADB_AVAILABLE:
            raise RuntimeError("需要 sentence-transformers 和 chromadb 依赖")
        
        # 嵌入问题
        question_embedding = self.model.encode([question])[0]
        
        # 检索
        results = self.collection.query(
            query_embeddings=[question_embedding.tolist()],
            n_results=top_k,
            include=['documents', 'metadatas', 'distances']
        )
        
        # 格式化结果
        formatted = []
        for i in range(len(results['ids'][0])):
            item = {
                'id': results['ids'][0][i],
                'content': results['documents'][0][i],
                'distance': results['distances'][0][i],
                'relevance_score': round(1 - results['distances'][0][i], 4)
            }
            if include_metadata and results['metadatas']:
                item['metadata'] = results['metadatas'][0][i]
            formatted.append(item)
        
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
        
        return {
            'success': True,
            'answer': context,
            'context': self.generate_context(question, top_k),
            'sources': list(set(sources)),
            'relevance_scores': [r['relevance_score'] for r in results]
        }
    
    def get_stats(self) -> Dict[str, Any]:
        """获取向量数据库统计"""
        if self.collection is None:
            return {'error': 'Collection not initialized'}
        
        return {
            'collection_name': self.collection_name,
            'document_count': self.collection.count(),
            'model_name': self.model_name
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
