import os, requests
from typing import List, Dict
from fastapi import FastAPI
from pydantic import BaseModel
from py2neo import Graph

NEO4J_URI  = os.getenv("NEO4J_URI","bolt://neo4j:7687")
NEO4J_USER = os.getenv("NEO4J_USER","neo4j")
NEO4J_PASS = os.getenv("NEO4J_PASSWORD","neo4j")
OLLAMA_URL = os.getenv("OLLAMA_URL","http://ollama:11434")
LLM_MODEL  = os.getenv("LLM_MODEL","mistral")

graph = Graph(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASS))
app = FastAPI(title="GraphRAG API")

@app.get("/")
def root():
    return {"status": "ok", "service": "GraphRAG API", "version": "1.0"}

@app.get("/health")
def health():
    try:
        # Neo4j 연결 테스트
        graph.run("RETURN 1").data()
        neo4j_status = "healthy"
    except Exception as e:
        neo4j_status = f"unhealthy: {str(e)}"
    
    try:
        # Ollama 연결 테스트
        resp = requests.get(f"{OLLAMA_URL}/api/tags", timeout=5)
        ollama_status = "healthy" if resp.status_code == 200 else "unhealthy"
    except Exception as e:
        ollama_status = f"unhealthy: {str(e)}"
    
    return {
        "status": "ok" if neo4j_status == "healthy" and ollama_status == "healthy" else "degraded",
        "neo4j": neo4j_status,
        "ollama": ollama_status
    }

class ChatRequest(BaseModel):
    query: str
    k: int = 8  # 그래프에서 수집할 엔티티/문서 수

def search_graph(question: str, k: int = 8) -> Dict:
    # 1) 한국어 개념 검색 (ConceptNet 스키마)
    concepts = graph.run("""
        MATCH (c:Concept)
        WHERE c.language = 'ko' 
          AND (toLower(c.label) CONTAINS toLower($q))
        RETURN c.uri as uri, c.label as label, c.language as lang
        LIMIT $k
        """, q=question, k=k).data()
    
    if not concepts:
        # 한국어 개념이 없으면 연관된 다른 언어 개념도 검색
        concepts = graph.run("""
            MATCH (c1:Concept)-[:RELATED]-(c2:Concept)
            WHERE c1.language = 'ko' AND toLower(c1.label) CONTAINS toLower($q)
            RETURN DISTINCT c2.uri as uri, c2.label as label, c2.language as lang
            LIMIT $k
            """, q=question, k=k).data()
    
    concept_uris = [c['uri'] for c in concepts]
    
    # 2) 관련 개념들과의 관계 가져오기
    if concept_uris:
        relations = graph.run("""
            MATCH (c1:Concept)-[r:RELATED]->(c2:Concept)
            WHERE c1.uri IN $uris OR c2.uri IN $uris
            RETURN c1.label as start, r.type as rel_type, c2.label as end, 
                   r.weight as weight, c1.language as start_lang, c2.language as end_lang
            ORDER BY r.weight DESC
            LIMIT $lim
            """, uris=concept_uris, lim=k*10).data()
        
        # 3) 2-hop 이웃 개념 (더 넓은 컨텍스트)
        neighbors = graph.run("""
            MATCH (c1:Concept)-[:RELATED*1..2]-(c2:Concept)
            WHERE c1.uri IN $uris AND c1 <> c2
            RETURN DISTINCT c2.label as label, c2.language as lang, c2.uri as uri
            LIMIT $lim
            """, uris=concept_uris, lim=k*5).data()
    else:
        relations = []
        neighbors = []

    context = {
        "concepts": concepts,
        "relations": relations,
        "neighbors": neighbors
    }
    return context

def call_llm(prompt: str) -> str:
    # Ollama /api/generate
    resp = requests.post(f"{OLLAMA_URL}/api/generate",
                         json={"model": LLM_MODEL, "prompt": prompt, "stream": False})
    resp.raise_for_status()
    return resp.json().get("response","")

@app.post("/chat")
def chat(req: ChatRequest):
    ctx = search_graph(req.query, req.k)
    
    # 컨텍스트를 프롬프트에 삽입 (ConceptNet 기반)
    concepts_text = "\n".join(
        f"- {c['label']} ({c['lang']})" for c in ctx["concepts"][:req.k]
    ) if ctx["concepts"] else "(검색 결과 없음)"
    
    relations_text = "\n".join(
        f"- {r['start']} --[{r['rel_type']}]--> {r['end']} (weight: {r['weight']:.2f})"
        for r in ctx["relations"][:req.k*2]
    ) if ctx["relations"] else "(관계 없음)"
    
    neighbors_text = "\n".join(
        f"- {n['label']} ({n['lang']})" for n in ctx["neighbors"][:req.k]
    ) if ctx["neighbors"] else "(주변 개념 없음)"
    
    context_text = f"""[발견된 개념들]
{concepts_text}

[개념 간 관계]
{relations_text}

[연관 개념들]
{neighbors_text}"""
    
    system = (
        "You are a Korean assistant that answers using the provided ConceptNet knowledge graph context. "
        "Use the concepts and their relationships to provide an informative answer. "
        "Cite relevant concepts in your answer. If the context is insufficient, say so honestly."
    )
    prompt = f"{system}\n\n[질문]\n{req.query}\n\n[지식 그래프 컨텍스트]\n{context_text}\n\n[답변]\n"
    answer = call_llm(prompt)
    return {"answer": answer, "context": ctx}
