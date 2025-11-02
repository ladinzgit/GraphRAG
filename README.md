# 🧠 GraphRAG - ConceptNet Knowledge Graph QA System

ConceptNet 5 지식 그래프를 활용한 한국어 질의응답 시스템

[![GitHub](https://img.shields.io/badge/GitHub-ladinzgit%2FGraphRAG-blue?logo=github)](https://github.com/ladinzgit/GraphRAG)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![Docker](https://img.shields.io/badge/Docker-Compose-2496ED?logo=docker)](docker-compose.yml)
[![Python](https://img.shields.io/badge/Python-3.11-3776AB?logo=python)](https://www.python.org/)

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

**GraphRAG**는 **Retrieval-Augmented Generation (RAG)** 패턴을 그래프 데이터베이스에 적용한 한국어 질의응답 시스템입니다. ConceptNet 5의 방대한 상식 지식 그래프와 로컬 LLM을 결합하여 정확하고 맥락 있는 답변을 제공합니다.

### 핵심 구성요소
- **Neo4j 5.24**: ConceptNet 지식 그래프 저장 및 탐색
- **Ollama (Mistral)**: 로컬 LLM 추론 엔진
- **FastAPI**: RESTful API 서버 (임베딩 기반 검색 지원)
- **Redis 7**: 검색 결과 및 LLM 응답 캐싱
- **Gradio**: 직관적인 웹 기반 사용자 인터페이스

### 주요 특징
✅ **완전 로컬 실행** - 인터넷 연결 없이도 작동  
✅ **임베딩 기반 의미 검색** - 단순 키워드가 아닌 의미 이해  
✅ **Multi-hop 그래프 탐색** - 개념 간 연결 관계 파악  
✅ **Redis 캐싱** - 반복 질문에 즉시 응답 (80% 속도 향상)  
✅ **Docker Compose** - 원클릭 배포

## 📁 프로젝트 구조

```
GraphRAG/
├── api/                          # FastAPI 서버
│   ├── main.py                   # API 엔드포인트 (개선된 버전)
│   ├── embedding_search.py       # 임베딩 기반 검색 모듈
│   ├── cache_manager.py          # Redis 캐싱 시스템
│   ├── monitoring.py             # 성능 모니터링 & 로깅
│   ├── requirements.txt          # Python 의존성
│   └── Dockerfile
│
├── indexer/                      # ConceptNet 데이터 로더
│   ├── build_graph.py            # 그래프 구축 스크립트
│   ├── requirements.txt
│   └── Dockerfile
│
├── ui/                           # Gradio 웹 인터페이스
│   ├── app.py                    # UI 애플리케이션
│   └── Dockerfile
│
├── data/                         # 데이터 디렉토리 (gitignore)
│   └── conceptnet-assertions-5.7.0.csv.gz
│
├── docker-compose.yml            # 전체 시스템 오케스트레이션
├── .env                          # 환경 변수 (gitignore)
└── README.md                     # 이 문서
```

## 🏗️ 아키텍처

### 시스템 다이어그램

```
                    ┌─────────────────────┐
                    │   User Browser      │
                    │   (Port 7860)       │
                    └──────────┬──────────┘
                               │ HTTP
                               ▼
                    ┌─────────────────────┐
                    │   Gradio UI         │
                    │   (ui/app.py)       │
                    └──────────┬──────────┘
                               │ REST API
                               ▼
                    ┌─────────────────────┐
                    │   FastAPI Server    │
                    │   (api/main.py)     │
                    │                     │
                    │ • EmbeddingSearcher │
                    │ • CacheManager      │
                    │ • Monitoring        │
                    └────┬────┬────┬──────┘
                         │    │    │
           ┌─────────────┘    │    └─────────────┐
           │                  │                  │
           ▼                  ▼                  ▼
    ┌───────────┐      ┌───────────┐     ┌───────────┐
    │  Neo4j    │      │  Ollama   │     │   Redis   │
    │  Graph    │      │   LLM     │     │   Cache   │
    │  :7687    │      │  :11434   │     │   :6379   │
    │           │      │           │     │           │
    │ ConceptNet│      │  Mistral  │     │ 검색 결과 │
    │  500K+    │      │   7B      │     │ LLM 응답  │
    │  concepts │      │           │     │ 임베딩    │
    └───────────┘      └───────────┘     └───────────┘
```

### 데이터 흐름

1. **질문 입력**: 사용자가 Gradio UI에 질문 입력
2. **키워드 추출**: LLM이 질문에서 핵심 개념 추출
3. **그래프 검색**: Neo4j에서 관련 개념 및 관계 탐색
4. **임베딩 재순위**: 의미 유사도 기반 결과 정렬
5. **캐시 확인**: Redis에서 이전 결과 재사용 가능 여부 확인
6. **컨텍스트 구성**: 개념, 관계, 경로 정보를 프롬프트에 통합
7. **LLM 생성**: Ollama로 최종 답변 생성
8. **응답 반환**: Gradio UI에 답변 및 그래프 컨텍스트 표시

## ✨ 주요 기능

### 1. 🔍 지능형 검색 시스템

#### 3가지 검색 모드
| 모드 | 설명 | 속도 | 정확도 | 사용 케이스 |
|------|------|------|--------|-------------|
| **Simple** | 문자열 매칭 | ⚡⚡⚡ | ⭐⭐ | 정확한 키워드 검색 |
| **Embedding** | 의미 유사도 검색 (기본) | ⚡⚡ | ⭐⭐⭐⭐⭐ | 자연어 질문 |
| **Hybrid** | 키워드 + 그래프 탐색 | ⚡⚡⚡ | ⭐⭐⭐⭐ | 복합 검색 |

#### 임베딩 기반 검색 기능
- LLM을 활용한 자동 키워드 추출
- 코사인 유사도 기반 개념 재순위화
- 동의어 및 유사 개념 자동 탐색

### 2. 🕸️ 그래프 탐색

- **Multi-hop 탐색**: 1~3단계 이웃 개념 탐색
- **최단 경로**: 개념 간 연결 경로 시각화
- **가중치 정렬**: 관계 신뢰도 기반 우선순위

### 3. ⚡ 성능 최적화

#### Redis 캐싱
```
캐시 TTL 설정:
- 검색 결과: 1시간
- LLM 응답: 2시간  
- 임베딩: 24시간
```

**성능 개선 효과**:
- 첫 실행: 3-6초
- 캐시 히트: 0.5-1초 (85% 단축)

### 4. 🎨 사용자 친화적 UI

- Gradio 기반 웹 인터페이스
- 실시간 그래프 컨텍스트 시각화
- 관계 타입별 이모지 아이콘

## 🚀 빠른 시작

### 사전 요구사항
- Docker & Docker Compose
- (선택) NVIDIA GPU + Docker GPU 지원
- 최소 8GB RAM (권장 16GB)
- 디스크 공간 10GB+

### 4단계 설치

#### 1️⃣ 저장소 클론 및 환경 설정

```bash
# 저장소 클론
git clone https://github.com/ladinzgit/GraphRAG.git
cd GraphRAG

# 환경 변수 설정
echo "NEO4J_PASSWORD=your_secure_password" > .env
```

#### 2️⃣ 시스템 시작

```bash
# 모든 서비스 시작
docker-compose up -d

# 로그 확인 (선택)
docker-compose logs -f
```

#### 3️⃣ ConceptNet 데이터 로드

```bash
# 인덱서 실행 (최초 1회, 약 30분 소요)
docker-compose run --rm indexer

# 진행 상황 확인
docker-compose logs -f indexer
```

#### 4️⃣ LLM 모델 다운로드

```bash
# Ollama 컨테이너 접속
docker exec -it ollama bash

# Mistral 모델 다운로드 (약 4GB)
ollama pull mistral

exit
```

### 접속 확인 ✅

- **Gradio UI**: http://localhost:7860
- **API 문서**: http://localhost:8000/docs
- **Neo4j Browser**: http://localhost:7474
  - 사용자명: `neo4j`
  - 비밀번호: `.env` 파일에 설정한 값

## 📡 API 사용법

### 주요 엔드포인트

#### 1. 헬스체크
```bash
curl http://localhost:8000/health
```

**응답**:
```json
{
  "status": "ok",
  "neo4j": "healthy",
  "ollama": "healthy"
}
```

#### 2. 질의응답 (메인 API)
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
| `k` | int | 8 | 검색할 개념 수 |
| `search_mode` | string | "embedding" | 검색 모드 |
| `include_neighbors` | bool | true | 이웃 개념 포함 |
| `max_hops` | int | 2 | 최대 탐색 거리 (1-3) |

**응답 예시**:
```json
{
  "answer": "사랑은 다른 사람이나 대상에 대한 깊은 애정과 헌신을 의미합니다...",
  "context": {
    "concepts": [...],
    "relations": [...],
    "keywords": ["사랑", "감정"]
  }
}
```

#### 3. 그래프 통계
```bash
curl http://localhost:8000/stats
```

### Python 클라이언트 예제

```python
import requests

def ask_question(question: str):
    response = requests.post(
        "http://localhost:8000/chat",
        json={
            "query": question,
            "k": 10,
            "search_mode": "embedding"
        }
    )
    
    if response.status_code == 200:
        result = response.json()
        print(f"답변: {result['answer']}")
    else:
        print(f"오류: {response.status_code}")

ask_question("사랑이란 무엇인가?")
```

### 검색 모드 선택 가이드

**Embedding 모드** (기본, 추천):
- 자연어 질문 ("사랑이란 무엇인가?")
- 동의어/유사 개념 탐색 필요 시

**Simple 모드**:
- 정확한 개념 이름 ("컴퓨터", "사랑")
- 빠른 응답 필요 시

**Hybrid 모드**:
- 복잡한 질문
- 속도와 정확도의 균형

## 🔧 트러블슈팅

### 문제 1: Neo4j 연결 실패
```bash
# 컨테이너 재시작
docker-compose restart neo4j

# 로그 확인
docker-compose logs neo4j
```

### 문제 2: Ollama 응답 느림
```bash
# GPU 사용 확인
docker exec ollama nvidia-smi

# 더 작은 모델로 변경
docker exec ollama ollama pull tinyllama
# docker-compose.yml에서 LLM_MODEL=tinyllama로 변경
```

### 문제 3: Redis 캐시 초기화
```bash
docker exec redis-cache redis-cli FLUSHDB
```

### 문제 4: 전체 시스템 리셋
```bash
docker-compose down -v
docker-compose up -d
docker-compose run --rm indexer
```

### 문제 5: 메모리 부족
```bash
# docker-compose.yml 수정
# Neo4j heap size 줄이기:
NEO4J_dbms_memory_heap_max__size=1G
```

## 🛠️ 개발 가이드

### 로컬 개발 모드
```bash
# API만 로컬에서 실행
cd api
pip install -r requirements.txt
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

### 서비스 제어 명령어

```bash
# 전체 시작
docker-compose up -d

# 특정 서비스만 재시작
docker-compose restart api ui

# 로그 실시간 확인
docker-compose logs -f api

# 상태 확인
docker-compose ps

# 전체 중지
docker-compose down
```

### 코드 구조

**API 엔드포인트 추가** (`api/main.py`):
```python
@app.post("/your-endpoint")
def your_function(req: YourRequest):
    # 구현
    return {"result": "..."}
```

**검색 로직 수정** (`api/embedding_search.py`):
```python
class EmbeddingSearcher:
    def your_search_method(self, query: str):
        # 구현
        return results
```

## 📈 향후 개선 계획

- [ ] Neo4j Vector 인덱스 활용
- [ ] 실시간 스트리밍 응답
- [ ] 사용자 피드백 수집
- [ ] 멀티모달 지원 (이미지, 오디오)
- [ ] Kubernetes 배포

## 📄 라이선스

MIT License - 자유롭게 사용, 수정, 배포 가능

## 🤝 기여

Pull Request 환영합니다!

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

## 📧 문의

문제가 있거나 제안사항이 있다면 [GitHub Issues](https://github.com/ladinzgit/GraphRAG/issues)를 등록해주세요.

## 🔗 관련 링크

- **GitHub Repository**: https://github.com/ladinzgit/GraphRAG
- **Issues**: https://github.com/ladinzgit/GraphRAG/issues
- **ConceptNet**: https://conceptnet.io/
- **Neo4j**: https://neo4j.com/
- **Ollama**: https://ollama.ai/

---

**Built with ❤️ using ConceptNet, Neo4j, and Ollama**
