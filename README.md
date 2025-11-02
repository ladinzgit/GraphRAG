# 🧠 GraphRAG - ConceptNet Knowledge Graph QA System

ConceptNet 5 지식 그래프를 활용한 한국어 질의응답 시스템

[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![Docker](https://img.shields.io/badge/Docker-Compose-2496ED?logo=docker)](docker-compose.yml)
[![Python](https://img.shields.io/badge/Python-3.11-3776AB?logo=python)](https://www.python.org/)
[![Neo4j](https://img.shields.io/badge/Neo4j-5.24-008CC1?logo=neo4j)](https://neo4j.com/)

## 📋 목차
- [시스템 개요](#-시스템-개요)
- [프로젝트 구조](#-프로젝트-구조)
- [아키텍처](#%EF%B8%8F-아키텍처)
- [주요 기능](#-주요-기능)
- [빠른 시작](#-빠른-시작)
- [API 사용법](#-api-사용법)
- [트러블슈팅](#-트러블슈팅)
- [개발 가이드](#%EF%B8%8F-개발-가이드)

## 🎯 시스템 개요

**GraphRAG**는 **Retrieval-Augmented Generation (RAG)** 패턴을 그래프 데이터베이스에 적용한 한국어 질의응답 시스템입니다. ConceptNet 5의 방대한 상식 지식 그래프와 로컬 LLM(Ollama)을 결합하여 정확하고 맥락 있는 답변을 제공합니다.

### 핵심 구성요소
- **Neo4j 5.24 Community**: ConceptNet 지식 그래프 저장 및 탐색
- **Ollama (Mistral)**: 로컬 LLM 추론 엔진 (GPU 가속 지원)
- **FastAPI**: RESTful API 서버 (임베딩 기반 검색, 캐싱)
- **Redis 7 Alpine**: 검색 결과 및 LLM 응답 캐싱 (LRU 정책)
- **Gradio**: 직관적인 웹 기반 사용자 인터페이스

### 주요 특징
✅ **완전 로컬 실행** - 데이터가 외부로 전송되지 않음  
✅ **임베딩 기반 의미 검색** - 자연어 이해 및 개념 매칭  
✅ **Multi-hop 그래프 탐색** - 최대 3단계 개념 연결 추적  
✅ **Redis 캐싱** - 반복 질문 최대 85% 속도 향상  
✅ **Docker Compose** - 5개 서비스 통합 오케스트레이션  
✅ **다양한 검색 모드** - Simple / Embedding / Hybrid 선택 가능

## 📁 프로젝트 구조

```
GraphRAG/
├── api/                          # FastAPI 백엔드 서버
│   ├── main.py                   # API 엔드포인트 정의
│   ├── embedding_search.py       # 임베딩 기반 의미 검색
│   ├── cache_manager.py          # Redis 캐싱 시스템
│   ├── requirements.txt          # Python 의존성
│   └── Dockerfile                # API 서버 컨테이너
│
├── indexer/                      # ConceptNet 데이터 로더
│   ├── build_graph.py            # 그래프 구축 스크립트
│   ├── requirements.txt          # Python 의존성
│   └── Dockerfile                # 인덱서 컨테이너
│
├── ui/                           # Gradio 웹 인터페이스
│   ├── app.py                    # UI 애플리케이션
│   └── Dockerfile                # UI 서버 컨테이너
│
├── data/                         # 데이터 디렉토리 (gitignore)
│   ├── conceptnet-assertions-5.7.0.csv.gz  # ConceptNet 데이터
│   └── korpora/                  # 나무위키 텍스트 데이터
│       └── namuwikitext/
│
├── docker-compose.yml            # 전체 시스템 오케스트레이션
├── .env                          # 환경 변수 (gitignore)
├── LICENSE                       # MIT 라이선스
└── README.md                     # 프로젝트 문서
```

### 주요 파일 설명

| 파일 | 역할 | 주요 기능 |
|------|------|-----------|
| `api/main.py` | API 서버 | `/chat`, `/search`, `/health`, `/stats` 엔드포인트 |
| `api/embedding_search.py` | 의미 검색 | LLM 키워드 추출, 임베딩 생성, 코사인 유사도 계산 |
| `api/cache_manager.py` | 캐싱 시스템 | Redis 기반 비동기 캐싱, TTL 관리 |
| `indexer/build_graph.py` | 데이터 로더 | ConceptNet CSV → Neo4j 그래프 변환 |
| `ui/app.py` | 웹 UI | Gradio 기반 채팅 인터페이스 |
| `docker-compose.yml` | 컨테이너 관리 | Neo4j, Ollama, Redis, API, UI 서비스 정의 |

## 🏗️ 아키텍처

### 시스템 다이어그램

```
                    ┌──────────────────────┐
                    │   User Browser       │
                    │   localhost:7860     │
                    └──────────┬───────────┘
                               │ HTTP
                               ▼
                    ┌──────────────────────┐
                    │   Gradio UI          │
                    │   (ui/app.py)        │
                    │   Port: 7860         │
                    └──────────┬───────────┘
                               │ REST API
                               ▼
                    ┌──────────────────────┐
                    │   FastAPI Server     │
                    │   (api/main.py)      │
                    │   Port: 8000         │
                    │                      │
                    │ • EmbeddingSearcher  │
                    │ • CacheManager       │
                    │ • LLM Integration    │
                    └────┬────┬────┬───────┘
                         │    │    │
           ┌─────────────┘    │    └─────────────┐
           │                  │                  │
           ▼                  ▼                  ▼
    ┌────────────┐     ┌────────────┐    ┌────────────┐
    │  Neo4j     │     │  Ollama    │    │   Redis    │
    │  Graph DB  │     │   LLM      │    │   Cache    │
    │  :7474     │     │  :11434    │    │   :6379    │
    │  :7687     │     │            │    │            │
    │            │     │  Model:    │    │  Strategy: │
    │ ConceptNet │     │  Mistral   │    │  LRU       │
    │  500K+     │     │  7B        │    │  512MB     │
    │  concepts  │     │            │    │            │
    │  2.8M+     │     │  GPU       │    │  TTL:      │
    │  relations │     │  Support   │    │  1-24h     │
    └────────────┘     └────────────┘    └────────────┘
```

### 데이터 흐름

**질문 처리 파이프라인:**

```
1. 질문 입력
   └─> Gradio UI에 사용자가 질문 입력
   
2. API 호출
   └─> FastAPI /chat 엔드포인트로 POST 요청
   
3. 캐시 확인 (CacheManager)
   ├─> Redis에 동일 질문 결과 있음 → 즉시 반환
   └─> 캐시 미스 → 4단계 진행
   
4. 키워드 추출 (EmbeddingSearcher)
   └─> LLM을 사용하여 질문에서 핵심 개념 추출
       예: "사랑이란 무엇인가?" → ["사랑", "감정", "의미"]
   
5. 그래프 검색 (Neo4j)
   ├─> Simple: 문자열 매칭
   ├─> Embedding: 의미 유사도 기반 검색
   └─> Hybrid: 키워드 + 그래프 탐색 결합
   
6. 임베딩 재순위 (EmbeddingSearcher)
   └─> 코사인 유사도 기반 결과 정렬
   
7. 컨텍스트 구성
   └─> 발견된 개념, 관계, 경로 정보를 프롬프트에 통합
   
8. LLM 생성 (Ollama)
   └─> 구성된 컨텍스트와 함께 프롬프트를 LLM에 전달
   
9. 캐싱 (Redis)
   └─> 결과를 Redis에 저장 (TTL: 2시간)
   
10. 응답 반환
    └─> Gradio UI에 답변 + 그래프 컨텍스트 표시
```

## ✨ 주요 기능

### 1. 🔍 지능형 검색 시스템

#### 3가지 검색 모드
| 모드 | 설명 | 속도 | 정확도 | 사용 케이스 |
|------|------|------|--------|-------------|
| **Simple** | 문자열 매칭 | ⚡⚡⚡ | ⭐⭐ | 정확한 키워드 검색 |
| **Embedding** | 의미 유사도 검색 (기본) | ⚡⚡ | ⭐⭐⭐⭐⭐ | 자연어 질문 |
| **Hybrid** | 키워드 + 그래프 탐색 | ⚡⚡⚡ | ⭐⭐⭐⭐ | 복합 검색 |

#### 임베딩 기반 검색 기능
- **자동 키워드 추출**: LLM이 질문에서 핵심 개념 자동 추출
- **의미 유사도 계산**: 코사인 유사도 기반 개념 재순위화
- **동의어 탐색**: 유사 개념 및 관련 용어 자동 발견
- **다국어 지원**: 한국어, 영어, 일본어, 중국어 등 개념 통합 검색

### 2. 🕸️ 그래프 탐색

- **Multi-hop 탐색**: 1~3단계 이웃 개념 탐색 (설정 가능)
- **최단 경로 탐색**: 개념 간 연결 경로 시각화
- **가중치 기반 정렬**: 관계 신뢰도(weight)에 따른 우선순위
- **관계 타입 분류**: 34가지 ConceptNet 관계 타입 지원
  - RelatedTo, IsA, PartOf, UsedFor, CapableOf 등

### 3. ⚡ 성능 최적화

#### Redis 캐싱 전략
```
캐시 레이어 구조:
┌─────────────────────────────┐
│ L1: 검색 결과 (TTL: 1시간)  │
├─────────────────────────────┤
│ L2: LLM 응답 (TTL: 2시간)   │
├─────────────────────────────┤
│ L3: 임베딩 (TTL: 24시간)    │
└─────────────────────────────┘

메모리 관리: LRU (Least Recently Used)
최대 크기: 512MB
```

**성능 개선 효과**:
- 첫 실행: 3-6초 (그래프 검색 + LLM 생성)
- 캐시 히트: 0.5-1초 (85% 단축)
- 메모리 사용: 50-200MB (질문 100개 기준)

### 4. 🎨 사용자 친화적 UI

- **Gradio 기반**: 웹 브라우저에서 즉시 사용 가능
- **실시간 피드백**: 답변 생성 과정 표시
- **그래프 컨텍스트 시각화**: 
  - 발견된 핵심 개념 (국기 이모지로 언어 표시)
  - 개념 간 관계 (관계 타입별 아이콘)
  - 연관 개념 목록
- **토글 가능**: 컨텍스트 표시/숨김 선택

### 5. 📊 모니터링 & 통계

- **헬스체크 엔드포인트**: Neo4j, Ollama 상태 확인
- **그래프 통계**: 
  - 총 개념 수 (언어별 분포)
  - 총 관계 수
  - 인덱스 상태
- **API 문서**: FastAPI 자동 생성 Swagger UI

## 🚀 빠른 시작

### 사전 요구사항
- **Docker** & **Docker Compose** (v2.0 이상)
- **(선택) NVIDIA GPU** + NVIDIA Container Toolkit (GPU 가속용)
- **최소 메모리**: 8GB RAM (권장: 16GB)
- **디스크 공간**: 약 10GB
  - ConceptNet 데이터: ~1GB
  - Neo4j 데이터베이스: ~3GB
  - Ollama 모델 (Mistral): ~4GB
  - Docker 이미지들: ~2GB

### 설치 및 실행 (4단계)

#### 1️⃣ 저장소 클론 및 환경 설정

```bash
# 저장소 클론
git clone https://github.com/ladinzgit/GraphRAG.git
cd GraphRAG

# 환경 변수 설정
echo "NEO4J_PASSWORD=your_secure_password_here" > .env

# (Windows PowerShell)
Set-Content -Path .env -Value "NEO4J_PASSWORD=your_secure_password_here"
```

> **보안 권장사항**: `NEO4J_PASSWORD`는 최소 12자 이상의 강력한 비밀번호를 사용하세요.

#### 2️⃣ 시스템 시작

```bash
# 모든 서비스 시작 (백그라운드 실행)
docker-compose up -d

# 서비스 상태 확인
docker-compose ps

# 로그 실시간 확인 (선택)
docker-compose logs -f
```

**예상 실행 시간**: 첫 실행 시 약 2-3분 (이미지 다운로드 포함)

#### 3️⃣ ConceptNet 데이터 로드

```bash
# 인덱서 실행 (최초 1회만 필요)
docker-compose run --rm indexer

# 진행 상황 확인
docker-compose logs -f indexer
```

**예상 소요 시간**: 약 20-40분 (하드웨어 성능에 따라 다름)

데이터 로딩 과정:
1. ConceptNet CSV 파일 다운로드 (~1GB)
2. Neo4j 인덱스 생성
3. 2.8M+ 관계 데이터 삽입
4. 인덱스 최적화

#### 4️⃣ LLM 모델 다운로드

```bash
# Ollama 컨테이너에 접속
docker exec -it ollama bash

# Mistral 모델 다운로드 (약 4GB)
ollama pull mistral

# 모델 설치 확인
ollama list

# 컨테이너 종료
exit
```

**대안 모델** (메모리가 부족한 경우):
```bash
# 더 작은 모델 옵션
ollama pull tinyllama    # 1.1GB
ollama pull phi          # 2.7GB
ollama pull gemma:2b     # 1.4GB

# docker-compose.yml 파일에서 LLM_MODEL 환경변수 변경 필요
```

### 접속 확인 ✅

시스템이 정상적으로 실행되면 다음 URL로 접속할 수 있습니다:

| 서비스 | URL | 설명 |
|--------|-----|------|
| **Gradio UI** | http://localhost:7860 | 메인 사용자 인터페이스 |
| **API 문서** | http://localhost:8000/docs | Swagger UI (API 테스트) |
| **Neo4j Browser** | http://localhost:7474 | 그래프 데이터베이스 브라우저 |
| **API 헬스체크** | http://localhost:8000/health | 서비스 상태 확인 |

**Neo4j 로그인 정보**:
- 사용자명: `neo4j`
- 비밀번호: `.env` 파일에 설정한 값

### 첫 질문 테스트

Gradio UI (http://localhost:7860)에 접속하여 다음 질문들을 시도해보세요:

```
✅ 추천 질문 예시:
- 사랑이란 무엇인가?
- 컴퓨터는 무엇에 사용되나요?
- 행복의 의미는?
- 음악과 감정의 관계는?
- 책은 어디에 있나요?
```

## 📡 API 사용법

### 주요 엔드포인트

#### 1. 헬스체크
시스템 상태를 확인합니다.

```bash
curl http://localhost:8000/health
```

**응답 예시**:
```json
{
  "status": "ok",
  "neo4j": "healthy",
  "ollama": "healthy"
}
```

#### 2. 질의응답 (메인 API)
질문을 입력하고 답변을 받습니다.

```bash
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{
    "query": "사랑이란 무엇인가?",
    "k": 10,
    "search_mode": "embedding"
  }'
```

**Request 파라미터**:
| 파라미터 | 타입 | 기본값 | 설명 |
|---------|------|-------|------|
| `query` | string | (필수) | 사용자 질문 |
| `k` | int | 8 | 검색할 개념 수 (1-50) |
| `search_mode` | string | "hybrid" | 검색 모드 (simple/embedding/hybrid) |
| `include_neighbors` | bool | true | 이웃 개념 포함 여부 |
| `max_hops` | int | 2 | 최대 탐색 거리 (1-3) |

**응답 예시**:
```json
{
  "answer": "사랑은 다른 사람이나 대상에 대한 깊은 애정과 헌신을 의미합니다. ConceptNet에 따르면, 사랑은 감정(emotion)의 한 종류이며, 행복(happiness)과 밀접한 관련이 있습니다...",
  "context": {
    "concepts": [
      {
        "uri": "/c/ko/사랑",
        "label": "사랑",
        "lang": "ko"
      }
    ],
    "relations": [
      {
        "start": "사랑",
        "rel_type": "IsA",
        "end": "감정",
        "weight": 2.82
      }
    ],
    "neighbors": [...],
    "paths": [...],
    "keywords": ["사랑", "감정"],
    "search_mode": "embedding"
  },
  "prompt_preview": "당신은 ConceptNet 지식 그래프를 활용하는..."
}
```

#### 3. 검색만 수행 (LLM 없이)
LLM 호출 없이 그래프 검색 결과만 반환합니다.

```bash
curl -X POST http://localhost:8000/search \
  -H "Content-Type: application/json" \
  -d '{
    "query": "컴퓨터",
    "k": 5,
    "search_mode": "simple"
  }'
```

#### 4. 그래프 통계
Neo4j 데이터베이스 통계를 조회합니다.

```bash
curl http://localhost:8000/stats
```

**응답 예시**:
```json
{
  "total_concepts": 1398983,
  "total_relations": 2897820,
  "concepts_by_language": [
    {"lang": "en", "cnt": 550000},
    {"lang": "ko", "cnt": 120000},
    {"lang": "ja", "cnt": 95000}
  ]
}
```

### Python 클라이언트 예제

#### 기본 사용법
```python
import requests

API_BASE = "http://localhost:8000"

def ask_question(question: str, search_mode: str = "embedding"):
    """질문을 보내고 답변을 받습니다."""
    response = requests.post(
        f"{API_BASE}/chat",
        json={
            "query": question,
            "k": 10,
            "search_mode": search_mode,
            "include_neighbors": True,
            "max_hops": 2
        },
        timeout=120
    )
    
    if response.status_code == 200:
        result = response.json()
        return result
    else:
        raise Exception(f"API 오류: {response.status_code}")

# 사용 예시
result = ask_question("사랑이란 무엇인가?")
print("답변:", result["answer"])
print("키워드:", result["context"]["keywords"])
```

#### 고급 사용법 (배치 처리)
```python
import requests
from typing import List, Dict

class GraphRAGClient:
    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url
        self.session = requests.Session()
    
    def health_check(self) -> bool:
        """서비스 상태 확인"""
        try:
            resp = self.session.get(f"{self.base_url}/health", timeout=5)
            return resp.status_code == 200
        except:
            return False
    
    def batch_query(self, questions: List[str]) -> List[Dict]:
        """여러 질문을 순차적으로 처리"""
        results = []
        for q in questions:
            try:
                resp = self.session.post(
                    f"{self.base_url}/chat",
                    json={"query": q, "k": 8, "search_mode": "embedding"},
                    timeout=120
                )
                results.append(resp.json())
            except Exception as e:
                results.append({"error": str(e)})
        return results

# 사용 예시
client = GraphRAGClient()

if client.health_check():
    questions = [
        "사랑이란 무엇인가?",
        "컴퓨터의 용도는?",
        "행복의 의미는?"
    ]
    results = client.batch_query(questions)
    
    for q, r in zip(questions, results):
        print(f"\nQ: {q}")
        print(f"A: {r.get('answer', r.get('error'))[:100]}...")
```

### 검색 모드 선택 가이드

| 상황 | 추천 모드 | 이유 |
|------|----------|------|
| 자연어 질문 ("~이란 무엇인가?") | **embedding** | 의미 이해 필요 |
| 정확한 개념 검색 ("컴퓨터") | **simple** | 빠른 응답 |
| 복잡한 질문 (여러 개념 포함) | **hybrid** | 균형잡힌 검색 |
| 탐색적 질문 | **embedding** | 관련 개념 발견 |

### JavaScript/TypeScript 예제

```typescript
// fetch API 사용
async function askGraphRAG(query: string): Promise<any> {
  const response = await fetch('http://localhost:8000/chat', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({
      query: query,
      k: 10,
      search_mode: 'embedding'
    })
  });
  
  if (!response.ok) {
    throw new Error(`HTTP error! status: ${response.status}`);
  }
  
  return await response.json();
}

// 사용 예시
askGraphRAG("사랑이란 무엇인가?")
  .then(result => {
    console.log("답변:", result.answer);
    console.log("개념 수:", result.context.concepts.length);
  })
  .catch(error => console.error("오류:", error));
```

## 🔧 트러블슈팅

### 일반적인 문제 해결

#### 문제 1: Neo4j 연결 실패
**증상**: `Failed to connect to Neo4j` 오류

**해결방법**:
```bash
# 1. Neo4j 컨테이너 상태 확인
docker-compose ps neo4j

# 2. 로그 확인
docker-compose logs neo4j

# 3. 컨테이너 재시작
docker-compose restart neo4j

# 4. 헬스체크 확인 (40초 대기)
Start-Sleep -Seconds 40
docker-compose ps
```

**추가 체크사항**:
- `.env` 파일에 `NEO4J_PASSWORD`가 설정되어 있는지 확인
- 포트 7687, 7474가 다른 프로그램에서 사용 중인지 확인

#### 문제 2: Ollama 응답 느림
**증상**: LLM 응답이 30초 이상 걸림

**해결방법**:
```bash
# GPU 사용 확인 (NVIDIA GPU가 있는 경우)
docker exec ollama nvidia-smi

# GPU를 사용하지 못하는 경우 -> CPU 사용 중
# 더 작은 모델로 변경 권장

# 1. 작은 모델 다운로드
docker exec ollama ollama pull tinyllama

# 2. docker-compose.yml 수정
# LLM_MODEL=mistral → LLM_MODEL=tinyllama

# 3. API 서비스 재시작
docker-compose restart api
```

**모델 크기 비교**:
| 모델 | 크기 | 속도 | 품질 | 권장 환경 |
|------|------|------|------|-----------|
| tinyllama | 1.1GB | ⚡⚡⚡ | ⭐⭐ | CPU, 8GB RAM |
| phi | 2.7GB | ⚡⚡ | ⭐⭐⭐ | CPU, 16GB RAM |
| mistral | 4GB | ⚡ | ⭐⭐⭐⭐ | GPU 권장 |
| llama2:13b | 7GB | ⚡ | ⭐⭐⭐⭐⭐ | GPU 필수 |

#### 문제 3: Redis 캐시 문제
**증상**: 오래된 답변이 계속 반환됨

**해결방법**:
```bash
# Redis 캐시 완전 초기화
docker exec redis-cache redis-cli FLUSHDB

# 특정 키 패턴만 삭제 (예: chat으로 시작하는 키)
docker exec redis-cache redis-cli --scan --pattern "chat:*" | xargs docker exec -i redis-cache redis-cli DEL

# Redis 연결 확인
docker exec redis-cache redis-cli PING
# 응답: PONG
```

#### 문제 4: 인덱서 실행 실패
**증상**: `docker-compose run indexer` 명령이 오류로 종료됨

**해결방법**:
```bash
# 1. Neo4j가 완전히 시작될 때까지 대기
docker-compose up -d neo4j
Start-Sleep -Seconds 40

# 2. Neo4j 연결 테스트
docker exec neo4j cypher-shell -u neo4j -p $env:NEO4J_PASSWORD "RETURN 1;"

# 3. data 디렉토리 권한 확인
# Windows에서는 Docker Desktop 설정에서 파일 공유 확인

# 4. 인덱서 재실행
docker-compose run --rm indexer

# 5. 실시간 로그 확인
docker-compose logs -f indexer
```

#### 문제 5: 메모리 부족 (OOM)
**증상**: Docker 컨테이너가 자꾸 재시작됨

**해결방법**:

1. **Neo4j 메모리 제한**:
   
   `docker-compose.yml` 수정:
   ```yaml
   neo4j:
     environment:
       - NEO4J_dbms_memory_heap_initial__size=512M
       - NEO4J_dbms_memory_heap_max__size=1G  # 기본 2G에서 줄임
   ```

2. **Redis 메모리 제한**:
   ```yaml
   redis:
     command: redis-server --maxmemory 256mb  # 기본 512mb에서 줄임
   ```

3. **Docker 전체 메모리 증가** (Docker Desktop 설정):
   - Settings → Resources → Memory
   - 최소 8GB 권장 (가능하면 12GB)

4. **서비스 재시작**:
   ```bash
   docker-compose down
   docker-compose up -d
   ```

#### 문제 6: 포트 충돌
**증상**: `Port is already allocated` 오류

**해결방법**:
```bash
# Windows에서 포트 사용 확인
netstat -ano | findstr :7860  # Gradio
netstat -ano | findstr :8000  # API
netstat -ano | findstr :7474  # Neo4j HTTP
netstat -ano | findstr :7687  # Neo4j Bolt
netstat -ano | findstr :11434 # Ollama

# 포트를 사용하는 프로세스 종료 (PID 확인 후)
Stop-Process -Id <PID> -Force

# 또는 docker-compose.yml에서 포트 변경
# 예: "7860:7860" → "7861:7860"
```

#### 문제 7: 전체 시스템 리셋
**모든 것을 처음부터 다시 시작**:

```bash
# 1. 모든 컨테이너 중지 및 볼륨 삭제
docker-compose down -v

# 2. 이미지 재빌드 (선택)
docker-compose build --no-cache

# 3. 시스템 재시작
docker-compose up -d

# 4. 서비스 안정화 대기
Start-Sleep -Seconds 30

# 5. 데이터 로드
docker-compose run --rm indexer

# 6. LLM 모델 다운로드
docker exec ollama ollama pull mistral
```

### 로그 확인 방법

```bash
# 전체 로그
docker-compose logs

# 특정 서비스 로그
docker-compose logs api
docker-compose logs neo4j
docker-compose logs ollama

# 실시간 로그 (Ctrl+C로 종료)
docker-compose logs -f

# 최근 100줄만
docker-compose logs --tail=100

# 타임스탬프 포함
docker-compose logs -t
```

### 성능 최적화 팁

1. **SSD 사용**: Neo4j 데이터는 SSD에 저장 권장
2. **GPU 활용**: NVIDIA GPU가 있다면 Ollama에서 자동 활용
3. **메모리 튜닝**: 시스템 메모리에 따라 heap size 조정
4. **캐시 활용**: 동일한 질문은 Redis에서 즉시 응답
5. **검색 모드 선택**: simple 모드가 가장 빠름

## 🛠️ 개발 가이드

### 로컬 개발 환경 설정

#### API 서버 로컬 실행
```bash
# Neo4j, Ollama, Redis만 Docker로 실행
docker-compose up -d neo4j ollama redis

# Python 가상환경 생성
cd api
python -m venv venv

# 가상환경 활성화 (Windows PowerShell)
.\venv\Scripts\Activate.ps1

# 의존성 설치
pip install -r requirements.txt

# 환경 변수 설정
$env:NEO4J_URI = "bolt://localhost:7687"
$env:NEO4J_USER = "neo4j"
$env:NEO4J_PASSWORD = "your_password"
$env:OLLAMA_URL = "http://localhost:11434"
$env:LLM_MODEL = "mistral"
$env:REDIS_URL = "redis://localhost:6379/0"

# 개발 모드로 실행 (자동 리로드)
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

#### UI 서버 로컬 실행
```bash
cd ui
pip install gradio requests

# 환경 변수 설정
$env:API_URL = "http://localhost:8000"

# 실행
python app.py
```

### 서비스 제어 명령어

```bash
# === 시작/중지 ===
docker-compose up -d              # 전체 시작 (백그라운드)
docker-compose up                 # 전체 시작 (포그라운드, 로그 표시)
docker-compose down               # 전체 중지 및 삭제
docker-compose down -v            # 볼륨까지 삭제 (데이터 초기화)

# === 재시작 ===
docker-compose restart            # 전체 재시작
docker-compose restart api ui     # 특정 서비스만 재시작

# === 로그 확인 ===
docker-compose logs -f api        # API 로그 실시간 확인
docker-compose logs --tail=50     # 최근 50줄
docker-compose logs -t            # 타임스탬프 포함

# === 상태 확인 ===
docker-compose ps                 # 서비스 상태 확인
docker-compose top                # 리소스 사용량

# === 개별 서비스 제어 ===
docker-compose stop neo4j         # 중지 (데이터 보존)
docker-compose start neo4j        # 시작
docker-compose rm neo4j           # 삭제 (중지 후)

# === 빌드 ===
docker-compose build              # 이미지 재빌드
docker-compose build --no-cache   # 캐시 없이 빌드
docker-compose up -d --build      # 빌드 후 시작
```

### 코드 구조 및 확장

#### API 엔드포인트 추가

`api/main.py`에 새 엔드포인트 추가:

```python
from pydantic import BaseModel

class CustomRequest(BaseModel):
    param1: str
    param2: int = 10

@app.post("/your-endpoint")
def your_function(req: CustomRequest):
    """
    새로운 API 엔드포인트
    """
    try:
        # 비즈니스 로직
        result = process_data(req.param1, req.param2)
        
        return {
            "status": "success",
            "data": result
        }
    except Exception as e:
        raise HTTPException(
            status_code=500, 
            detail=f"처리 실패: {str(e)}"
        )
```

#### 검색 로직 수정

`api/embedding_search.py`에서 검색 알고리즘 커스터마이징:

```python
class EmbeddingSearcher:
    def custom_search(self, query: str, graph, k: int = 10):
        """
        커스텀 검색 로직
        """
        # 1. 전처리
        processed_query = self.preprocess(query)
        
        # 2. 임베딩 생성
        embedding = self.get_embedding(processed_query)
        
        # 3. Neo4j 쿼리
        results = graph.run("""
            MATCH (c:Concept)
            WHERE c.language = 'ko'
            RETURN c.label as label, c.uri as uri
            LIMIT $k
        """, k=k).data()
        
        # 4. 재순위화
        ranked = self.rerank_by_similarity(results, embedding)
        
        return ranked
```

#### 캐싱 전략 변경

`api/cache_manager.py`에서 TTL 및 캐싱 로직 수정:

```python
class CacheManager:
    async def set_with_custom_ttl(
        self, 
        key: str, 
        value: Any, 
        ttl_seconds: int = 3600
    ):
        """
        커스텀 TTL로 캐시 저장
        """
        if not self.enabled or not self.client:
            return
        
        try:
            value_json = json.dumps(value, ensure_ascii=False)
            await self.client.setex(
                key, 
                ttl_seconds, 
                value_json
            )
        except Exception as e:
            print(f"캐시 저장 실패: {e}")
```

### 데이터베이스 쿼리 예제

#### Neo4j Cypher 쿼리
```bash
# Neo4j 컨테이너 접속
docker exec -it neo4j cypher-shell -u neo4j -p your_password

# 쿼리 예시
# 1. 한국어 개념 수 확인
MATCH (c:Concept {language: 'ko'}) RETURN count(c);

# 2. 특정 개념의 모든 관계 조회
MATCH (c:Concept {label: '사랑'})-[r:RELATED]-(other)
RETURN c.label, type(r), r.type, other.label, r.weight
ORDER BY r.weight DESC
LIMIT 20;

# 3. 두 개념 간 최단 경로
MATCH path = shortestPath(
  (a:Concept {label: '컴퓨터'})-[*..5]-(b:Concept {label: '인공지능'})
)
RETURN path;

# 4. 가장 연결이 많은 개념 (허브)
MATCH (c:Concept)-[r]-()
WHERE c.language = 'ko'
RETURN c.label, count(r) as connections
ORDER BY connections DESC
LIMIT 10;

# 종료
:exit
```

### 테스트

#### API 테스트
```bash
# pytest 설치
pip install pytest httpx

# 테스트 파일 생성: api/test_main.py
```

```python
import pytest
from fastapi.testclient import TestClient
from main import app

client = TestClient(app)

def test_health():
    response = client.get("/health")
    assert response.status_code == 200
    assert "status" in response.json()

def test_chat():
    response = client.post(
        "/chat",
        json={
            "query": "사랑이란?",
            "k": 5,
            "search_mode": "simple"
        }
    )
    assert response.status_code == 200
    data = response.json()
    assert "answer" in data
    assert "context" in data

# 실행: pytest api/test_main.py
```

### 배포

#### Docker Hub 배포
```bash
# 이미지 빌드 및 태그
docker build -t yourusername/graphrag-api:latest ./api
docker build -t yourusername/graphrag-ui:latest ./ui

# Docker Hub 로그인
docker login

# 푸시
docker push yourusername/graphrag-api:latest
docker push yourusername/graphrag-ui:latest
```

#### 환경 변수 관리
프로덕션 환경에서는 `.env` 파일 대신 시스템 환경 변수 사용:

```bash
# 환경 변수 설정
export NEO4J_PASSWORD="strong_password"
export REDIS_URL="redis://redis-server:6379/0"

# docker-compose 실행
docker-compose up -d
```

### 기여 가이드라인

1. **브랜치 전략**:
   - `main`: 안정 버전
   - `develop`: 개발 버전
   - `feature/*`: 새 기능
   - `bugfix/*`: 버그 수정

2. **커밋 메시지 규칙**:
   ```
   [타입] 제목 (50자 이내)
   
   상세 설명 (선택)
   
   타입: feat, fix, docs, style, refactor, test, chore
   ```

3. **Pull Request**:
   - 명확한 제목과 설명
   - 변경사항 요약
   - 테스트 결과 포함

### 디버깅 팁

```bash
# API 서버 디버깅
docker-compose logs -f api

# Python 디버거 사용 (main.py에 추가)
import pdb; pdb.set_trace()

# Neo4j 쿼리 성능 분석
PROFILE MATCH (c:Concept)-[r:RELATED]->(other)
WHERE c.label = '사랑'
RETURN c, r, other;

# Redis 모니터링
docker exec redis-cache redis-cli MONITOR
```

## 📈 향후 개선 계획

### 단기 목표 (Q1 2025)
- [ ] **Neo4j Vector 인덱스**: 임베딩 벡터 네이티브 저장 및 검색
- [ ] **스트리밍 응답**: LLM 답변 실시간 스트리밍 (SSE 또는 WebSocket)
- [ ] **사용자 피드백**: 답변 품질 평가 및 학습 데이터 수집
- [ ] **다국어 UI**: 영어, 일본어 인터페이스 지원
- [ ] **API 인증**: JWT 기반 사용자 인증 시스템

### 중기 목표 (Q2-Q3 2025)
- [ ] **멀티모달 지원**: 이미지, 오디오 입력 처리
- [ ] **커스텀 지식 그래프**: 사용자 정의 개념 및 관계 추가
- [ ] **대화 이력 관리**: 세션 기반 컨텍스트 유지
- [ ] **성능 대시보드**: Grafana + Prometheus 모니터링
- [ ] **A/B 테스팅**: 검색 알고리즘 성능 비교

### 장기 목표 (Q4 2025)
- [ ] **Kubernetes 배포**: 프로덕션 레벨 오케스트레이션
- [ ] **분산 처리**: 대규모 그래프 처리를 위한 샤딩
- [ ] **추천 시스템**: 사용자 관심사 기반 개념 추천
- [ ] **모바일 앱**: iOS/Android 네이티브 앱
- [ ] **API 마켓플레이스**: 공개 API 서비스 제공

### 기술 부채
- [ ] 단위 테스트 커버리지 80% 이상
- [ ] API 응답 시간 최적화 (p95 < 2초)
- [ ] 에러 핸들링 개선
- [ ] 문서 자동화 (OpenAPI 스키마)

## 📄 라이선스

MIT License

Copyright (c) 2025 ladinzgit

본 소프트웨어는 MIT 라이선스 하에 배포됩니다. 자유롭게 사용, 수정, 배포할 수 있습니다.

전체 라이선스 내용은 [LICENSE](LICENSE) 파일을 참조하세요.

## 🤝 기여

Pull Request를 환영합니다! 기여하기 전에 다음을 확인해주세요:

### 기여 방법

1. **이슈 확인**: [GitHub Issues](https://github.com/ladinzgit/GraphRAG/issues)에서 작업할 이슈 선택
2. **Fork**: 리포지토리를 개인 계정으로 포크
3. **브랜치 생성**: 
   ```bash
   git checkout -b feature/amazing-feature
   ```
4. **변경사항 커밋**:
   ```bash
   git commit -m '[feat] Add some amazing feature'
   ```
5. **푸시**:
   ```bash
   git push origin feature/amazing-feature
   ```
6. **Pull Request 생성**: GitHub에서 PR 생성 및 설명 작성

### 코드 스타일
- Python: PEP 8 준수
- 타입 힌팅 사용 권장
- Docstring 작성 (Google Style)
- 변수명: snake_case
- 클래스명: PascalCase

### 기여 분야
- 🐛 버그 수정
- ✨ 새 기능 개발
- � 문서 개선
- 🎨 UI/UX 개선
- ⚡ 성능 최적화
- 🌐 번역 (i18n)

## �📧 문의 및 지원

### 문제 보고
버그나 문제를 발견하셨나요? [GitHub Issues](https://github.com/ladinzgit/GraphRAG/issues)에 보고해주세요.

**이슈 작성 시 포함할 내용**:
- 문제 설명
- 재현 방법
- 예상 동작 vs 실제 동작
- 환경 정보 (OS, Docker 버전 등)
- 스크린샷 (있다면)

### 기능 요청
새로운 기능을 제안하고 싶으신가요? [Feature Request](https://github.com/ladinzgit/GraphRAG/issues/new?labels=enhancement) 이슈를 생성해주세요.

### 질문
일반적인 질문은 [Discussions](https://github.com/ladinzgit/GraphRAG/discussions)에서 나눠주세요.

## 🙏 감사의 말

이 프로젝트는 다음 오픈소스 프로젝트들의 도움으로 만들어졌습니다:

- **[ConceptNet](https://conceptnet.io/)** - 상식 지식 그래프 데이터 제공
- **[Neo4j](https://neo4j.com/)** - 그래프 데이터베이스 엔진
- **[Ollama](https://ollama.ai/)** - 로컬 LLM 실행 환경
- **[FastAPI](https://fastapi.tiangolo.com/)** - 현대적인 Python 웹 프레임워크
- **[Gradio](https://gradio.app/)** - ML 모델 UI 프레임워크
- **[Redis](https://redis.io/)** - 인메모리 데이터 스토어

## 🔗 관련 링크

### 공식 문서
- **ConceptNet API**: https://github.com/commonsense/conceptnet5/wiki
- **Neo4j Cypher**: https://neo4j.com/docs/cypher-manual/current/
- **Ollama Models**: https://ollama.ai/library
- **FastAPI Guide**: https://fastapi.tiangolo.com/tutorial/

### 학술 자료
- **ConceptNet 5 Paper**: https://arxiv.org/abs/1612.03975
- **RAG Paper**: https://arxiv.org/abs/2005.11401
- **Graph Neural Networks**: https://arxiv.org/abs/1901.00596

### 커뮤니티
- **Neo4j Community**: https://community.neo4j.com/
- **Ollama Discord**: https://discord.gg/ollama
- **FastAPI Discord**: https://discord.com/invite/VQjSZaeJmf

## 📊 프로젝트 통계

![GitHub stars](https://img.shields.io/github/stars/ladinzgit/GraphRAG?style=social)
![GitHub forks](https://img.shields.io/github/forks/ladinzgit/GraphRAG?style=social)
![GitHub issues](https://img.shields.io/github/issues/ladinzgit/GraphRAG)
![GitHub pull requests](https://img.shields.io/github/issues-pr/ladinzgit/GraphRAG)
![GitHub last commit](https://img.shields.io/github/last-commit/ladinzgit/GraphRAG)

---

<div align="center">

**Built with ❤️ using ConceptNet, Neo4j, and Ollama**

⭐ 이 프로젝트가 유용하다면 Star를 눌러주세요! ⭐

[🏠 홈](https://github.com/ladinzgit/GraphRAG) • 
[📚 문서](https://github.com/ladinzgit/GraphRAG/wiki) • 
[🐛 이슈](https://github.com/ladinzgit/GraphRAG/issues) • 
[💬 토론](https://github.com/ladinzgit/GraphRAG/discussions)

</div>
