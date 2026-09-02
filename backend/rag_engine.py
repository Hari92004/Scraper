"""
Hugging Face RAG (Retrieval-Augmented Generation) Engine
Handles text chunking, vector indexing, semantic search, and Hugging Face LLM generation.
"""

import os
import re
from typing import List, Dict, Any, Optional
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

try:
    from huggingface_hub import InferenceClient
    HF_AVAILABLE = True
except ImportError:
    HF_AVAILABLE = False


DEFAULT_SYSTEM_PROMPT = (
    "You are an expert AI Research Assistant specialized in answering questions about scraped web content. "
    "Your answers must be STRICTLY GROUNDED in the provided context. "
    "If the answer cannot be found in the context, politely state that the information is not present on the webpage. "
    "Include chunk references like [Chunk 1] or [Chunk 2] when citing specific facts. "
    "You can respond in English or Hindi/Hinglish according to the user's question language."
)


class TextChunk:
    def __init__(self, chunk_id: int, text: str, start_char: int, end_char: int):
        self.chunk_id = chunk_id
        self.text = text
        self.start_char = start_char
        self.end_char = end_char

    def to_dict(self) -> Dict[str, Any]:
        return {
            "chunk_id": self.chunk_id,
            "text": self.text,
            "char_range": [self.start_char, self.end_char]
        }


class RAGEngine:
    def __init__(self, hf_token: Optional[str] = None, model_name: str = "Qwen/Qwen2.5-7B-Instruct", system_prompt: Optional[str] = None):
        self.hf_token = hf_token or os.getenv("HF_TOKEN") or os.getenv("HUGGINGFACE_API_KEY")
        self.model_name = model_name
        self.system_prompt = system_prompt or DEFAULT_SYSTEM_PROMPT
        self.chunks: List[TextChunk] = []
        self.vectorizer: Optional[TfidfVectorizer] = None
        self.tfidf_matrix = None
        self.context_metadata: Dict[str, Any] = {}

    def set_system_prompt(self, prompt: str):
        """Update system prompt dynamically."""
        if prompt and prompt.strip():
            self.system_prompt = prompt.strip()

    def set_hf_token(self, token: str):
        """Update Hugging Face token dynamically."""
        if token and token.strip():
            self.hf_token = token.strip()

    def set_model_name(self, model: str):
        """Update target model."""
        if model and model.strip():
            self.model_name = model.strip()

    def chunk_document(self, text: str, chunk_size: int = 600, overlap: int = 100) -> List[TextChunk]:
        """Split document into overlapping semantic chunks."""
        if not text or not text.strip():
            return []

        # Clean multiple whitespaces while keeping structure
        cleaned_text = re.sub(r'\n{3,}', '\n\n', text.strip())
        
        # Split by paragraphs or sentences
        paragraphs = cleaned_text.split('\n')
        chunks: List[TextChunk] = []
        current_chunk = ""
        current_start = 0
        char_idx = 0
        chunk_id = 1

        for para in paragraphs:
            para = para.strip()
            if not para:
                continue

            if len(current_chunk) + len(para) <= chunk_size:
                current_chunk += (" " if current_chunk else "") + para
            else:
                if current_chunk:
                    chunks.append(TextChunk(chunk_id, current_chunk, current_start, current_start + len(current_chunk)))
                    chunk_id += 1
                    # Keep overlap from previous chunk
                    overlap_text = current_chunk[-overlap:] if len(current_chunk) > overlap else current_chunk
                    current_start += len(current_chunk) - len(overlap_text)
                    current_chunk = overlap_text + " " + para
                else:
                    # Paragraph itself is longer than chunk_size, split by sentences
                    sentences = re.split(r'(?<=[.?!])\s+', para)
                    for sent in sentences:
                        if len(current_chunk) + len(sent) <= chunk_size:
                            current_chunk += (" " if current_chunk else "") + sent
                        else:
                            if current_chunk:
                                chunks.append(TextChunk(chunk_id, current_chunk, current_start, current_start + len(current_chunk)))
                                chunk_id += 1
                                current_start += len(current_chunk)
                            current_chunk = sent

        if current_chunk:
            chunks.append(TextChunk(chunk_id, current_chunk, current_start, current_start + len(current_chunk)))

        return chunks

    def build_index(self, text: str, metadata: Optional[Dict[str, Any]] = None):
        """Chunk text and build TF-IDF / Vector index for semantic retrieval."""
        self.context_metadata = metadata or {}
        self.chunks = self.chunk_document(text)
        
        if not self.chunks:
            self.vectorizer = None
            self.tfidf_matrix = None
            return

        corpus = [c.text for c in self.chunks]
        self.vectorizer = TfidfVectorizer(
            stop_words='english',
            ngram_range=(1, 2),
            sublinear_tf=True
        )
        self.tfidf_matrix = self.vectorizer.fit_transform(corpus)

    def retrieve(self, query: str, top_k: int = 4) -> List[Dict[str, Any]]:
        """Retrieve most relevant chunks for user query using vector similarity."""
        if not self.chunks or not self.vectorizer or self.tfidf_matrix is None:
            return []

        query_vec = self.vectorizer.transform([query])
        similarities = cosine_similarity(query_vec, self.tfidf_matrix).flatten()

        # Get top-k indices sorted by score descending
        top_indices = np.argsort(similarities)[::-1][:top_k]
        
        results = []
        for idx in top_indices:
            score = float(similarities[idx])
            chunk = self.chunks[idx]
            results.append({
                "chunk_id": chunk.chunk_id,
                "text": chunk.text,
                "score": round(score, 4),
                "char_range": [chunk.start_char, chunk.end_char]
            })

        return results

    def _call_huggingface_llm(self, prompt: str, system_prompt: str) -> str:
        """Call Hugging Face Inference API with fallback handling."""
        if not HF_AVAILABLE or not self.hf_token:
            raise ValueError("Hugging Face token not provided or client not initialized.")

        client = InferenceClient(api_key=self.hf_token)
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": prompt}
        ]

        try:
            # Try chat completion first
            response = client.chat.completions.create(
                model=self.model_name,
                messages=messages,
                max_tokens=800,
                temperature=0.2
            )
            return response.choices[0].message.content.strip()
        except Exception as e:
            # Fallback to text_generation if chat endpoint is not supported on chosen model
            try:
                full_prompt = f"System: {system_prompt}\nUser: {prompt}\nAssistant:"
                res = client.text_generation(
                    full_prompt,
                    model=self.model_name,
                    max_new_tokens=600,
                    temperature=0.2
                )
                return res.strip()
            except Exception as e2:
                raise RuntimeError(f"Hugging Face API Error: {str(e)} | Fallback Error: {str(e2)}")

    def _extractive_smart_answer(self, query: str, retrieved_chunks: List[Dict[str, Any]]) -> str:
        """Zero-API-key offline fallback: extracts and highlights direct answers from retrieved chunks."""
        if not retrieved_chunks or retrieved_chunks[0]["score"] == 0:
            return (
                "Scraped website content me is question ke baare me specific information nahi mili. "
                "Aap please page ka topic check karein ya dusra sawal poochein."
            )

        top_chunk = retrieved_chunks[0]["text"]
        sentences = re.split(r'(?<=[.?!])\s+', top_chunk)
        
        # Filter sentences with query keywords
        query_words = set(re.findall(r'\w+', query.lower())) - {"what", "is", "the", "a", "an", "how", "why", "where", "who", "kya", "hai", "kaise"}
        
        relevant_sentences = []
        for s in sentences:
            s_words = set(re.findall(r'\w+', s.lower()))
            if s_words & query_words:
                relevant_sentences.append(s.strip())

        if not relevant_sentences:
            relevant_sentences = sentences[:3]

        answer_summary = " ".join(relevant_sentences[:4])
        return f"{answer_summary}\n\n*(Extracted directly from scraped context using semantic matching)*"

    def query(self, question: str, top_k: int = 4) -> Dict[str, Any]:
        """Perform full RAG: Retrieve context chunks and generate grounded answer."""
        if not self.chunks:
            return {
                "answer": "Pehle kisi website ka URL enter karke 'Scrape' karein, uske baad aap us content se sawal pooch sakte hain.",
                "citations": [],
                "model_used": "None",
                "success": False
            }

        retrieved_chunks = self.retrieve(question, top_k=top_k)
        
        # Construct Context block with chunk labels
        context_parts = []
        citations = []
        for c in retrieved_chunks:
            context_parts.append(f"[Chunk {c['chunk_id']}]:\n{c['text']}")
            citations.append({
                "chunk_id": c["chunk_id"],
                "score": c["score"],
                "snippet": c["text"][:180] + "..." if len(c["text"]) > 180 else c["text"]
            })

        context_str = "\n\n".join(context_parts)
        page_title = self.context_metadata.get("title", "Web Page")
        page_url = self.context_metadata.get("url", "")

        system_prompt = (
            "You are an expert AI Research Assistant specialized in answering questions about scraped web content. "
            "Your answers must be STRICTLY GROUNDED in the provided context. "
            "If the answer cannot be found in the context, politely state that the information is not present on the webpage. "
            "Include chunk references like [Chunk 1] or [Chunk 2] when citing specific facts. "
            "You can respond in English or Hindi/Hinglish according to the user's question language."
        )

        user_prompt = f"""
Webpage Title: {page_title}
Webpage URL: {page_url}

--- CONTEXT EXTRACTED FROM WEBPAGE ---
{context_str}
--------------------------------------

Question: {question}

Please provide a clear, accurate, and concise answer based ONLY on the context above:
"""

        model_used = self.model_name if self.hf_token else "Local Semantic Extractor (Offline)"
        
        if self.hf_token:
            try:
                answer = self._call_huggingface_llm(user_prompt, system_prompt)
            except Exception as e:
                # Graceful fallback if token error or rate limit
                answer = (
                    f"⚠️ *Hugging Face API Notice: {str(e)}*\n\n"
                    f"**Local Extractive RAG Response:**\n"
                    + self._extractive_smart_answer(question, retrieved_chunks)
                )
                model_used = "Local Fallback (HF API Error)"
        else:
            answer = self._extractive_smart_answer(question, retrieved_chunks)

        return {
            "answer": answer,
            "citations": citations,
            "model_used": model_used,
            "total_chunks_indexed": len(self.chunks),
            "success": True
        }


if __name__ == "__main__":
    rag = RAGEngine()
    sample_text = """
    Web scraping is data scraping used for extracting data from websites. 
    The web scraping software may directly access the World Wide Web using the Hypertext Transfer Protocol or a web browser.
    Web scraping is closely related to web indexing, which indexes content on the web using a bot or web crawler.
    Common uses of web scraping include web monitoring, web data extraction, price comparison, and website change detection.
    Modern scrapers also use machine learning and RAG systems to parse unstructured HTML into structured knowledge graphs.
    """
    rag.build_index(sample_text, {"title": "Web Scraping Article"})
    print("Chunks created:", len(rag.chunks))
    res = rag.query("What are common uses of web scraping?")
    print("Answer:", res["answer"])
    print("Citations:", res["citations"])
