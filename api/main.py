"""
개선된 GraphRAG API
- 임베딩 기반 의미 검색
- 더 나은 컨텍스트 구성
- 프롬프트 엔지니어링 개선
"""
import os
import requests
from typing import List, Dict
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from py2neo import Graph

from embedding_search import EmbeddingSearcher

# 환경 변수
NEO4J_URI  = os.getenv("NEO4J_URI","bolt://neo4j:7687")
NEO4J_USER = os.getenv("NEO4J_USER","neo4j")
NEO4J_PASS = os.getenv("NEO4J_PASSWORD","neo4j")
OLLAMA_URL = os.getenv("OLLAMA_URL","http://ollama:11434")
LLM_MODEL  = os.getenv("LLM_MODEL","mistral")

# Neo4j 연결
graph = Graph(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASS))

# 임베딩 검색기 초기화
embedder = EmbeddingSearcher(OLLAMA_URL, LLM_MODEL)

# FastAPI 앱
app = FastAPI(
    title="GraphRAG API (Improved)",
    description="ConceptNet 기반 의미 검색 및 질의응답 API",
    version="2.0"
)

@app.get("/")
def root():
    return {
        "status": "ok", 
        "service": "GraphRAG API (Improved)", 
        "version": "2.0",
        "features": [
            "Embedding-based semantic search",
            "LLM keyword extraction",
            "Multi-hop graph traversal",
            "Enhanced prompt engineering"
        ]
    }

@app.get("/health")
def health():
    """서비스 헬스체크"""
    try:
        graph.run("RETURN 1").data()
        neo4j_status = "healthy"
    except Exception as e:
        neo4j_status = f"unhealthy: {str(e)}"
    
    try:
        resp = requests.get(f"{OLLAMA_URL}/api/tags", timeout=5)
        ollama_status = "healthy" if resp.status_code == 200 else "unhealthy"
    except Exception as e:
        ollama_status = f"unhealthy: {str(e)}"
    
    return {
        "status": "ok" if neo4j_status == "healthy" and ollama_status == "healthy" else "degraded",
        "neo4j": neo4j_status,
        "ollama": ollama_status
    }

@app.get("/stats")
def get_stats():
    """그래프 통계 정보"""
    try:
        stats = graph.run("""
            MATCH (c:Concept)
            WITH c.language as lang, count(*) as cnt
            RETURN lang, cnt
            ORDER BY cnt DESC
            """).data()
        
        total_concepts = graph.run("MATCH (c:Concept) RETURN count(c) as cnt").data()[0]['cnt']
        total_relations = graph.run("MATCH ()-[r:RELATED]->() RETURN count(r) as cnt").data()[0]['cnt']
        
        return {
            "total_concepts": total_concepts,
            "total_relations": total_relations,
            "concepts_by_language": stats
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"통계 조회 실패: {str(e)}")

class ChatRequest(BaseModel):
    query: str
    k: int = 8
    search_mode: str = "hybrid"  # "simple", "embedding", "hybrid"
    include_neighbors: bool = True
    max_hops: int = 2

def search_graph_improved(
    question: str, 
    k: int = 8,
    search_mode: str = "hybrid",
    include_neighbors: bool = True,
    max_hops: int = 2
) -> Dict:
    """
    개선된 그래프 검색
    
    Args:
        question: 사용자 질문
        k: 반환할 개념 수
        search_mode: 검색 모드 (simple/embedding/hybrid)
        include_neighbors: 이웃 개념 포함 여부
        max_hops: 최대 탐색 거리
    """
    concepts = []
    keywords = []
    
    # 1. 검색 모드에 따른 개념 추출
    if search_mode == "simple":
        # 단순 문자열 매칭
        concepts = graph.run("""
            MATCH (c:Concept)
            WHERE c.language = 'ko' 
              AND (toLower(c.label) CONTAINS toLower($q))
            RETURN c.uri as uri, c.label as label, c.language as lang
            LIMIT $k
            """, q=question, k=k).data()
    
    elif search_mode == "embedding":
        # 임베딩 기반 검색
        concepts, keywords = embedder.search_with_embedding(graph, question, k)
    
    else:  # hybrid (기본값)
        # 하이브리드: 키워드 추출 + 그래프 탐색
        concepts, keywords = embedder.search_with_embedding(graph, question, k)
    
    if not concepts:
        return {
            "concepts": [],
            "relations": [],
            "neighbors": [],
            "keywords": keywords,
            "search_mode": search_mode
        }
    
    concept_uris = [c['uri'] for c in concepts]
    
    # 2. 관계 추출 (가중치 높은 순)
    relations = graph.run("""
        MATCH (c1:Concept)-[r:RELATED]->(c2:Concept)
        WHERE c1.uri IN $uris OR c2.uri IN $uris
        RETURN c1.label as start, r.type as rel_type, c2.label as end, 
               r.weight as weight, c1.language as start_lang, c2.language as end_lang,
               c1.uri as start_uri, c2.uri as end_uri
        ORDER BY r.weight DESC
        LIMIT $lim
        """, uris=concept_uris, lim=k*10).data()
    
    # 3. 이웃 개념 (n-hop)
    neighbors = []
    if include_neighbors:
        neighbors = graph.run(f"""
            MATCH (c1:Concept)-[:RELATED*1..{max_hops}]-(c2:Concept)
            WHERE c1.uri IN $uris AND c1 <> c2
            RETURN DISTINCT c2.label as label, c2.language as lang, c2.uri as uri
            LIMIT $lim
            """, uris=concept_uris, lim=k*5).data()
    
    # 4. 경로 정보 (추가)
    paths = []
    if len(concepts) >= 2:
        # 두 핵심 개념 간의 최단 경로 찾기
        uri_pairs = [(concepts[0]['uri'], concepts[1]['uri'])]
        
        for uri1, uri2 in uri_pairs:
            path_query = """
                MATCH path = shortestPath((c1:Concept)-[:RELATED*..3]-(c2:Concept))
                WHERE c1.uri = $uri1 AND c2.uri = $uri2
                RETURN [n in nodes(path) | n.label] as node_labels,
                       [r in relationships(path) | r.type] as rel_types
                LIMIT 1
                """
            path_result = graph.run(path_query, uri1=uri1, uri2=uri2).data()
            if path_result:
                paths.append(path_result[0])
    
    return {
        "concepts": concepts,
        "relations": relations,
        "neighbors": neighbors,
        "paths": paths,
        "keywords": keywords,
        "search_mode": search_mode
    }

def build_enhanced_prompt(question: str, context: Dict, keywords: List[str]) -> str:
    """개선된 프롬프트 구성"""
    
    concepts = context.get("concepts", [])
    relations = context.get("relations", [])
    neighbors = context.get("neighbors", [])
    paths = context.get("paths", [])
    
    # 개념 섹션
    concepts_text = ""
    if concepts:
        concepts_text = "**발견된 핵심 개념:**\n"
        for i, c in enumerate(concepts[:8], 1):
            concepts_text += f"{i}. {c['label']} ({c['lang']})\n"
    else:
        concepts_text = "(관련 개념을 찾지 못했습니다)\n"
    
    # 관계 섹션
    relations_text = ""
    if relations:
        relations_text = "\n**개념 간 관계:**\n"
        for r in relations[:10]:
            rel_type = r['rel_type']
            weight = r['weight']
            relations_text += f"• {r['start']} --[{rel_type}]--> {r['end']} (신뢰도: {weight:.2f})\n"
    
    # 경로 섹션
    paths_text = ""
    if paths:
        paths_text = "\n**개념 연결 경로:**\n"
        for p in paths:
            nodes = p.get('node_labels', [])
            rels = p.get('rel_types', [])
            path_str = nodes[0]
            for i, rel in enumerate(rels):
                if i+1 < len(nodes):
                    path_str += f" --[{rel}]--> {nodes[i+1]}"
            paths_text += f"• {path_str}\n"
    
    # 이웃 개념 (간략히)
    neighbors_text = ""
    if neighbors:
        neighbor_labels = [n['label'] for n in neighbors[:10]]
        neighbors_text = f"\n**관련 개념들:** {', '.join(neighbor_labels)}\n"
    
    # 키워드 정보
    keywords_text = ""
    if keywords:
        keywords_text = f"\n**분석된 키워드:** {', '.join(keywords)}\n"
    
    # 최종 프롬프트
    system_instruction = """당신은 ConceptNet 지식 그래프를 활용하는 한국어 AI 어시스턴트입니다.

주어진 지식 그래프 컨텍스트를 바탕으로 질문에 답변하세요:
1. 발견된 개념과 관계를 적극 활용하세요
2. 개념 간의 연결 경로가 있다면 이를 설명에 포함하세요
3. 신뢰도(weight)가 높은 관계를 우선 참고하세요
4. 컨텍스트가 불충분하면 솔직히 말하세요
5. 답변은 한국어로, 명확하고 이해하기 쉽게 작성하세요
"""
    
    context_text = f"""{keywords_text}
{concepts_text}
{relations_text}
{paths_text}
{neighbors_text}"""
    
    prompt = f"""{system_instruction}

【질문】
{question}

【지식 그래프 컨텍스트】
{context_text}

【답변】
"""
    
    return prompt

def call_llm(prompt: str, temperature: float = 0.7) -> str:
    """LLM 호출"""
    try:
        resp = requests.post(
            f"{OLLAMA_URL}/api/generate",
            json={
                "model": LLM_MODEL, 
                "prompt": prompt, 
                "stream": False,
                "options": {
                    "temperature": temperature,
                    "num_predict": 512
                }
            },
            timeout=120
        )
        resp.raise_for_status()
        return resp.json().get("response", "")
    except Exception as e:
        return f"LLM 응답 생성 실패: {str(e)}"

@app.post("/chat")
def chat(req: ChatRequest):
    """개선된 채팅 엔드포인트"""
    try:
        # 1. 그래프 검색
        context = search_graph_improved(
            req.query, 
            req.k,
            req.search_mode,
            req.include_neighbors,
            req.max_hops
        )
        
        # 2. 프롬프트 구성
        keywords = context.get("keywords", [])
        prompt = build_enhanced_prompt(req.query, context, keywords)
        
        # 3. LLM 응답 생성
        answer = call_llm(prompt)
        
        return {
            "answer": answer,
            "context": context,
            "prompt_preview": prompt[:500] + "..." if len(prompt) > 500 else prompt
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"처리 중 오류 발생: {str(e)}")

@app.post("/search")
def search_only(req: ChatRequest):
    """검색만 수행 (LLM 호출 없음)"""
    try:
        context = search_graph_improved(
            req.query, 
            req.k,
            req.search_mode,
            req.include_neighbors,
            req.max_hops
        )
        return context
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"검색 중 오류 발생: {str(e)}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
