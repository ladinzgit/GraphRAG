# 🧠 GraphRAG - ConceptNet Knowledge Graph QA System

ConceptNet 5 지식 그래프를 활용한 한국어 질의응답 시스템

## 📋 목차
- [시스템 개요](#시스템-개요)
- [아키텍처](#아키텍처)
- [주요 기능](#주요-기능)
- [설치 및 실행](#설치-및-실행)
- [API 사용법](#api-사용법)
- [성능 최적화](#성능-최적화)
- [트러블슈팅](#트러블슈팅)

## 🎯 시스템 개요

GraphRAG는 **Retrieval-Augmented Generation (RAG)** 패턴을 그래프 데이터베이스에 적용한 시스템입니다.

### 핵심 구성요소
- **Neo4j**: ConceptNet 지식 그래프 저장
- **Ollama**: 로컬 LLM (Mistral) 추론
- **FastAPI**: RESTful API 서버
- **Redis**: 검색 결과 및 응답 캐싱
- **Gradio**: 사용자 인터페이스

## 🏗️ 아키텍처

```
┌─────────────┐
│   User UI   │ (Gradio - Port 7860)
└──────┬──────┘
       │
       ▼
┌─────────────┐
│  API Server │ (FastAPI - Port 8000)
└──────┬──────┘
       │
       ├──────────┐
       ▼          ▼
┌──────────┐  ┌──────────┐  ┌──────────┐
│  Neo4j   │  │  Ollama  │  │  Redis   │
│  Graph   │  │   LLM    │  │  Cache   │
│  :7687   │  │  :11434  │  │  :6379   │
└──────────┘  └──────────┘  └──────────┘
```

## ✨ 주요 기능

### 1. **지능형 검색** 🔍
- ✅ **Simple Search**: 문자열 매칭 기반 빠른 검색
- ✅ **Embedding Search**: 의미 유사도 기반 검색 (권장)
- ✅ **Hybrid Search**: 키워드 추출 + 그래프 탐색 (기본값)

### 2. **그래프 탐색** 🕸️
- Multi-hop 이웃 탐색 (1~3 hop)
- 최단 경로 탐색 (개념 간 연결 시각화)
- 관계 가중치 기반 우선순위 정렬

### 3. **성능 최적화** ⚡
- Redis 캐싱 (응답 시간 80% 감소)
- 배치 처리 및 비동기 I/O
- 구조화된 로깅 및 모니터링

### 4. **다국어 지원** 🌏
- 한국어 우선 검색
- 영어, 일본어, 중국어 등 ConceptNet 지원 언어

## 🚀 설치 및 실행

### 사전 요구사항
- Docker & Docker Compose
- (선택) NVIDIA GPU + Docker GPU 지원
- 최소 8GB RAM (권장 16GB)
- 디스크 공간 10GB+

### 1. 환경 변수 설정

`.env` 파일 생성:
```bash
NEO4J_PASSWORD=your_secure_password
```

### 2. 시스템 시작

```bash
# 전체 시스템 시작
docker-compose up -d

# 로그 확인
docker-compose logs -f

# 특정 서비스만 시작
docker-compose up -d neo4j redis
```

### 3. ConceptNet 데이터 로드

```bash
# 인덱서 실행 (최초 1회, 약 30분 소요)
docker-compose run --rm indexer

# 진행 상황 확인
docker-compose logs -f indexer
```

### 4. Ollama 모델 다운로드

```bash
# Ollama 컨테이너 접속
docker exec -it ollama bash

# Mistral 모델 다운로드 (약 4GB)
ollama pull mistral

# (선택) 다른 모델
# ollama pull llama2-ko
# ollama pull gemma:7b

exit
```

### 5. 접속 확인

- **API 문서**: http://localhost:8000/docs
- **Gradio UI**: http://localhost:7860
- **Neo4j Browser**: http://localhost:7474 (ID: neo4j, PW: 설정한 비밀번호)

## 📡 API 사용법

### 헬스체크
```bash
curl http://localhost:8000/health
```

### 기본 질의응답
```bash
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{
    "query": "사랑이란 무엇인가?",
    "k": 8,
    "search_mode": "hybrid"
  }'
```

### 검색만 수행 (LLM 없이)
```bash
curl -X POST http://localhost:8000/search \
  -H "Content-Type: application/json" \
  -d '{
    "query": "컴퓨터",
    "k": 10,
    "search_mode": "embedding"
  }'
```

### 그래프 통계
```bash
curl http://localhost:8000/stats
```

### Request 파라미터

| 파라미터 | 타입 | 기본값 | 설명 |
|---------|------|-------|------|
| `query` | string | (필수) | 사용자 질문 |
| `k` | int | 8 | 검색할 개념 수 |
| `search_mode` | string | "hybrid" | 검색 모드 (simple/embedding/hybrid) |
| `include_neighbors` | bool | true | 이웃 개념 포함 여부 |
| `max_hops` | int | 2 | 최대 탐색 거리 |

## ⚡ 성능 최적화

### 검색 모드 비교

| 모드 | 속도 | 정확도 | 추천 상황 |
|------|------|--------|-----------|
| **simple** | ⚡⚡⚡ | ⭐⭐ | 정확한 키워드 검색 |
| **embedding** | ⚡⚡ | ⭐⭐⭐⭐⭐ | 의미 기반 검색 (최고 품질) |
| **hybrid** | ⚡⚡⚡ | ⭐⭐⭐⭐ | 균형잡힌 선택 (기본값) |

### 캐시 전략

Redis 캐싱 TTL:
- 검색 결과: 1시간
- LLM 응답: 2시간
- 임베딩: 24시간

캐시 히트율 목표: **60%+**

### 벤치마크 실행

```bash
# 시스템 벤치마크
python test_benchmark.py

# 결과: benchmark_results.json
```

**예상 성능** (hybrid 모드, 캐시 미스):
- 검색: 200-500ms
- LLM 생성: 2-5초
- 전체 응답: 3-6초

## 🔧 트러블슈팅

### 1. Neo4j 연결 실패
```bash
# Neo4j 컨테이너 재시작
docker-compose restart neo4j

# 로그 확인
docker-compose logs neo4j

# 헬스체크
curl http://localhost:7474
```

### 2. Ollama 응답 느림
```bash
# GPU 사용 확인
docker exec ollama nvidia-smi

# 모델 로드 상태
docker exec ollama ollama list

# 메모리 부족 시 더 작은 모델 사용
# docker exec ollama ollama pull tinyllama
```

### 3. Redis 캐시 초기화
```bash
docker exec redis-cache redis-cli FLUSHDB
```

### 4. 전체 시스템 리셋
```bash
# 모든 컨테이너 및 볼륨 삭제
docker-compose down -v

# 재시작
docker-compose up -d
docker-compose run --rm indexer
```

### 5. 메모리 부족
```bash
# Docker 메모리 제한 확인
docker stats

# docker-compose.yml에서 메모리 제한 조정
# Neo4j heap size 줄이기:
# NEO4J_dbms_memory_heap_max__size=1G
```

## 📊 모니터링

### 성능 메트릭 확인
```bash
curl http://localhost:8000/metrics
```

### 로그 분석
```bash
# 구조화된 JSON 로그
docker-compose logs api | grep "elapsed_ms"

# 에러 로그만
docker-compose logs api | grep "ERROR"
```

## 🔐 보안 고려사항

1. **환경 변수**: `.env` 파일을 git에 커밋하지 마세요
2. **Neo4j 인증**: 강력한 비밀번호 사용
3. **포트 노출**: 프로덕션 환경에서는 방화벽 설정 필수
4. **API 인증**: 필요시 JWT 토큰 인증 추가

## 🛠️ 개발 가이드

### 로컬 개발 모드
```bash
# API만 로컬에서 실행
cd api
pip install -r requirements.txt
uvicorn main_improved:app --reload
```

### 새 기능 추가
1. `api/main_improved.py`에 엔드포인트 추가
2. `api/embedding_search.py`에 검색 로직 추가
3. `test_benchmark.py`에 테스트 추가

### 데이터베이스 스키마 확인
```cypher
// Neo4j Browser에서 실행
CALL db.schema.visualization()

// 인덱스 확인
SHOW INDEXES
```

## 📈 향후 개선 계획

- [ ] Vector 인덱스 활용 (Neo4j 5.x)
- [ ] 실시간 스트리밍 응답
- [ ] 사용자 피드백 수집 및 학습
- [ ] 멀티모달 지원 (이미지, 오디오)
- [ ] 클러스터 배포 (Kubernetes)

## 📄 라이선스

MIT License

## 🤝 기여

Pull Request 환영합니다!

1. Fork the repository
2. Create your feature branch
3. Commit your changes
4. Push to the branch
5. Open a Pull Request

## 📧 문의

문제가 있거나 제안사항이 있다면 이슈를 등록해주세요.

---

**Built with ❤️ using ConceptNet, Neo4j, and Ollama**
