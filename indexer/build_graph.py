import os, gzip, requests, time
from tqdm import tqdm
from py2neo import Graph
from urllib.parse import unquote

neo4j_uri = os.environ.get("NEO4J_URI","bolt://neo4j:7687")
neo4j_user = os.environ.get("NEO4J_USER","neo4j")
neo4j_pwd  = os.environ.get("NEO4J_PASSWORD","neo4j")

CONCEPTNET_URL = "https://s3.amazonaws.com/conceptnet/downloads/2019/edges/conceptnet-assertions-5.7.0.csv.gz"
DATA_DIR = os.environ.get("DATA_DIR", "/data")
CONCEPTNET_FILE = os.path.join(DATA_DIR, "conceptnet-assertions-5.7.0.csv.gz")

# Neo4j 연결 (재시도 로직 추가)
def connect_neo4j(max_retries=10, retry_delay=5):
    """Neo4j 연결 재시도"""
    for attempt in range(1, max_retries + 1):
        try:
            print(f"🔌 Attempting to connect to Neo4j (attempt {attempt}/{max_retries})...")
            graph = Graph(neo4j_uri, auth=(neo4j_user, neo4j_pwd))
            # 연결 테스트
            graph.run("RETURN 1")
            print("✅ Connected to Neo4j successfully!")
            return graph
        except Exception as e:
            print(f"⚠️ Connection failed: {e}")
            if attempt < max_retries:
                print(f"⏳ Retrying in {retry_delay} seconds...")
                time.sleep(retry_delay)
            else:
                print("❌ Failed to connect to Neo4j after all retries")
                raise

graph = connect_neo4j()

print("🔧 Creating indexes and constraints...")
graph.run("CREATE CONSTRAINT IF NOT EXISTS FOR (c:Concept) REQUIRE c.uri IS UNIQUE;")
graph.run("CREATE INDEX IF NOT EXISTS FOR (c:Concept) ON (c.language);")
graph.run("CREATE INDEX IF NOT EXISTS FOR (c:Concept) ON (c.label);")

def download_conceptnet():
    """ConceptNet 데이터 다운로드"""
    if os.path.exists(CONCEPTNET_FILE):
        print(f"✅ ConceptNet file already exists: {CONCEPTNET_FILE}")
        return
    
    print(f"📥 Downloading ConceptNet from {CONCEPTNET_URL}...")
    os.makedirs(DATA_DIR, exist_ok=True)
    
    response = requests.get(CONCEPTNET_URL, stream=True)
    total_size = int(response.headers.get('content-length', 0))
    
    with open(CONCEPTNET_FILE, 'wb') as f, tqdm(
        desc="Downloading",
        total=total_size,
        unit='B',
        unit_scale=True
    ) as pbar:
        for chunk in response.iter_content(chunk_size=8192):
            f.write(chunk)
            pbar.update(len(chunk))
    
    print(f"✅ Download complete: {CONCEPTNET_FILE}")

def parse_conceptnet_uri(uri):
    """ConceptNet URI 파싱 (/c/ko/개 -> language=ko, label=개)"""
    parts = uri.split('/')
    if len(parts) >= 3 and parts[1] == 'c':
        language = parts[2]
        label = unquote(parts[3]) if len(parts) > 3 else ''
        return language, label
    return None, None

def load_korean_concepts():
    """ConceptNet에서 한국어 관계만 Neo4j에 로드"""
    print("📊 Loading Korean concepts from ConceptNet...")
    
    batch_size = 1000
    batch = []
    total_loaded = 0
    skipped = 0
    
    with gzip.open(CONCEPTNET_FILE, 'rt', encoding='utf-8') as f:
        for line in tqdm(f, desc="Processing ConceptNet"):
            try:
                parts = line.strip().split('\t')
                if len(parts) < 4:
                    continue
                
                rel_uri, start_uri, end_uri = parts[0], parts[1], parts[2]
                
                # weight 파싱 (숫자가 아닌 경우 기본값 1.0)
                try:
                    weight = float(parts[3])
                except (ValueError, IndexError):
                    weight = 1.0
                
                # 시작/끝 개념의 언어 파싱
                start_lang, start_label = parse_conceptnet_uri(start_uri)
                end_lang, end_label = parse_conceptnet_uri(end_uri)
                
                # 한국어 관계만 필터링 (시작 또는 끝이 한국어)
                if start_lang != 'ko' and end_lang != 'ko':
                    continue
                
                # 관계 타입 추출 (/r/RelatedTo -> RelatedTo)
                rel_type = rel_uri.split('/')[-1] if '/' in rel_uri else rel_uri
                
                batch.append({
                    'start_uri': start_uri,
                    'start_label': start_label,
                    'start_lang': start_lang,
                    'end_uri': end_uri,
                    'end_label': end_label,
                    'end_lang': end_lang,
                    'rel_type': rel_type,
                    'weight': weight
                })
                
                # 배치 처리
                if len(batch) >= batch_size:
                    insert_batch(batch)
                    total_loaded += len(batch)
                    batch = []
            
            except Exception as e:
                skipped += 1
                if skipped <= 10:  # 처음 10개 에러만 출력
                    print(f"⚠️ Skipping line due to error: {e}")
                continue
    
    # 남은 배치 처리
    if batch:
        insert_batch(batch)
        total_loaded += len(batch)
    
    print(f"✅ Loaded {total_loaded} Korean relations from ConceptNet")
    if skipped > 0:
        print(f"⚠️ Skipped {skipped} lines due to parsing errors")

def insert_batch(batch):
    """배치 단위로 Neo4j에 삽입"""
    query = """
    UNWIND $batch AS row
    MERGE (start:Concept {uri: row.start_uri})
    ON CREATE SET start.label = row.start_label, start.language = row.start_lang
    MERGE (end:Concept {uri: row.end_uri})
    ON CREATE SET end.label = row.end_label, end.language = row.end_lang
    MERGE (start)-[r:RELATED {type: row.rel_type}]->(end)
    ON CREATE SET r.weight = row.weight
    ON MATCH SET r.weight = r.weight + row.weight
    """
    graph.run(query, batch=batch)

# 실행
if __name__ == "__main__":
    download_conceptnet()
    load_korean_concepts()
    print("✅ Graph build finished.")
