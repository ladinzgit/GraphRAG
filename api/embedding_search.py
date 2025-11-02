"""
임베딩 기반 의미 검색 모듈
Ollama를 활용하여 질문의 의미를 이해하고 유사한 개념을 찾습니다.
"""
import requests
import numpy as np
from typing import List, Dict, Tuple

class EmbeddingSearcher:
    def __init__(self, ollama_url: str, model: str = "mistral"):
        self.ollama_url = ollama_url
        self.model = model
    
    def get_embedding(self, text: str) -> List[float]:
        """텍스트의 임베딩 벡터 생성"""
        try:
            resp = requests.post(
                f"{self.ollama_url}/api/embeddings",
                json={"model": self.model, "prompt": text},
                timeout=30
            )
            resp.raise_for_status()
            return resp.json().get("embedding", [])
        except Exception as e:
            print(f"임베딩 생성 실패: {e}")
            return []
    
    def cosine_similarity(self, vec1: List[float], vec2: List[float]) -> float:
        """코사인 유사도 계산"""
        if not vec1 or not vec2:
            return 0.0
        
        a = np.array(vec1)
        b = np.array(vec2)
        
        norm_a = np.linalg.norm(a)
        norm_b = np.linalg.norm(b)
        
        if norm_a == 0 or norm_b == 0:
            return 0.0
        
        return float(np.dot(a, b) / (norm_a * norm_b))
    
    def extract_keywords(self, query: str) -> List[str]:
        """LLM을 사용하여 핵심 키워드 추출"""
        prompt = f"""다음 질문에서 핵심 개념 키워드를 추출하세요. 
질문: {query}

핵심 키워드만 쉼표로 구분하여 나열하세요. 조사나 불필요한 단어는 제외합니다.
예: 사랑이란 무엇인가? -> 사랑, 감정, 의미

키워드:"""
        
        try:
            resp = requests.post(
                f"{self.ollama_url}/api/generate",
                json={"model": self.model, "prompt": prompt, "stream": False},
                timeout=30
            )
            resp.raise_for_status()
            keywords_text = resp.json().get("response", "").strip()
            
            # 쉼표로 분리하고 정리
            keywords = [k.strip() for k in keywords_text.split(',')]
            keywords = [k for k in keywords if k and len(k) > 1]
            
            return keywords[:5]  # 최대 5개
        except Exception as e:
            print(f"키워드 추출 실패: {e}")
            # 폴백: 단순 공백 분리
            return [w for w in query.split() if len(w) > 1][:3]
    
    def search_with_embedding(
        self, 
        graph, 
        query: str, 
        k: int = 8
    ) -> Tuple[List[Dict], List[str]]:
        """
        임베딩 기반 개념 검색
        
        Returns:
            (concepts, keywords): 찾은 개념 리스트와 사용된 키워드
        """
        # 1. 키워드 추출
        keywords = self.extract_keywords(query)
        print(f"🔍 추출된 키워드: {keywords}")
        
        # 2. 각 키워드로 개념 검색
        all_concepts = []
        seen_uris = set()
        
        for keyword in keywords:
            # 한국어 개념 우선 검색
            concepts = graph.run("""
                MATCH (c:Concept)
                WHERE c.language = 'ko' 
                  AND (toLower(c.label) CONTAINS toLower($kw)
                       OR toLower(c.label) = toLower($kw))
                RETURN c.uri as uri, c.label as label, c.language as lang
                LIMIT $k
                """, kw=keyword, k=k).data()
            
            for c in concepts:
                if c['uri'] not in seen_uris:
                    all_concepts.append(c)
                    seen_uris.add(c['uri'])
            
            # 연관 개념도 탐색 (1-hop)
            if concepts:
                uris = [c['uri'] for c in concepts]
                related = graph.run("""
                    MATCH (c1:Concept)-[:RELATED]-(c2:Concept)
                    WHERE c1.uri IN $uris AND c2 <> c1
                    RETURN DISTINCT c2.uri as uri, c2.label as label, c2.language as lang
                    LIMIT $k
                    """, uris=uris, k=k).data()
                
                for c in related:
                    if c['uri'] not in seen_uris:
                        all_concepts.append(c)
                        seen_uris.add(c['uri'])
        
        # 3. 임베딩 기반 재순위화 (옵션)
        # 시간이 오래 걸리므로 개념이 많을 때만 사용
        if len(all_concepts) > k * 2:
            query_emb = self.get_embedding(query)
            if query_emb:
                concept_scores = []
                for c in all_concepts:
                    label_emb = self.get_embedding(c['label'])
                    similarity = self.cosine_similarity(query_emb, label_emb)
                    concept_scores.append((c, similarity))
                
                # 유사도 순으로 정렬
                concept_scores.sort(key=lambda x: x[1], reverse=True)
                all_concepts = [c for c, _ in concept_scores[:k*2]]
        
        return all_concepts[:k*2], keywords
