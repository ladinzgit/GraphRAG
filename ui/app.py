import os, requests, gradio as gr

API_URL = os.getenv("API_URL","http://api:8000")

def format_concept(concept):
    """개념을 이쁘게 포맷팅"""
    label = concept.get('label', 'Unknown')
    lang = concept.get('lang', '??')
    lang_emoji = {
        'ko': '🇰🇷',
        'en': '🇺🇸',
        'ja': '🇯🇵',
        'zh': '🇨🇳',
        'fr': '🇫🇷',
        'de': '🇩🇪',
        'es': '🇪🇸'
    }.get(lang, '🌐')
    return f"{lang_emoji} **{label}**"

def format_relation(rel):
    """관계를 이쁘게 포맷팅"""
    rel_icons = {
        'RelatedTo': '🔗',
        'IsA': '📦',
        'PartOf': '🧩',
        'UsedFor': '🔧',
        'CapableOf': '💪',
        'AtLocation': '📍',
        'Causes': '⚡',
        'HasA': '🎁',
        'MadeOf': '🧱',
        'Desires': '💭',
        'CreatedBy': '✨',
        'DefinedAs': '📖',
        'MannerOf': '🎭',
        'LocatedNear': '🗺️',
        'HasProperty': '⚙️',
        'MotivatedByGoal': '🎯',
        'ObstructedBy': '🚧',
        'HasPrerequisite': '📋',
        'HasSubevent': '🎬',
        'HasFirstSubevent': '🎬',
        'HasLastSubevent': '🎬',
        'CausesDesire': '💡',
        'ReceivesAction': '👋',
        'NotDesires': '🚫',
        'NotCapableOf': '❌',
        'NotHasProperty': '🔒'
    }
    
    start = rel.get('start', '?')
    end = rel.get('end', '?')
    rel_type = rel.get('rel_type', 'Related')
    weight = rel.get('weight', 0)
    icon = rel_icons.get(rel_type, '🔗')
    
    return f"{start} {icon} *{rel_type}* → {end} `({weight:.2f})`"

def talk(q, show_context):
    """질문에 답변"""
    if not q.strip():
        return "❓ 질문을 입력해주세요.", ""
    
    try:
        r = requests.post(f"{API_URL}/chat", json={"query": q, "k": 10}, timeout=120)
        r.raise_for_status()
        j = r.json()
        
        answer = j.get("answer", "답변을 생성할 수 없습니다.")
        context = j.get("context", {})
        
        # 컨텍스트 포맷팅
        context_md = ""
        if show_context:
            concepts = context.get("concepts", [])
            relations = context.get("relations", [])
            neighbors = context.get("neighbors", [])
            
            if concepts:
                context_md += "### 🎯 발견된 핵심 개념\n"
                for c in concepts[:8]:
                    context_md += f"- {format_concept(c)}\n"
                context_md += "\n"
            
            if relations:
                context_md += "### 🕸️ 개념 간 관계\n"
                for r in relations[:10]:
                    context_md += f"- {format_relation(r)}\n"
                context_md += "\n"
            
            if neighbors:
                context_md += "### 🔍 연관 개념\n"
                neighbor_texts = [format_concept(n) for n in neighbors[:8]]
                context_md += ", ".join(neighbor_texts) + "\n"
        
        return answer, context_md
        
    except requests.exceptions.Timeout:
        return "⏱️ 응답 시간이 초과되었습니다. 다시 시도해주세요.", ""
    except requests.exceptions.ConnectionError:
        return "🔌 API 서버에 연결할 수 없습니다.", ""
    except Exception as e:
        return f"❌ 오류 발생: {str(e)}", ""

# Gradio UI 구성
with gr.Blocks(
    title="ConceptNet GraphRAG",
    theme=gr.themes.Soft(
        primary_hue="blue",
        secondary_hue="cyan",
    )
) as demo:
    gr.Markdown("""
    # 🧠 ConceptNet GraphRAG
    
    **ConceptNet 5** 지식 그래프를 활용한 질의응답 시스템
    
    ConceptNet은 일상적인 상식 지식을 담은 다국어 의미 네트워크입니다.
    질문을 입력하면 관련 개념과 관계를 탐색하여 답변합니다.
    """)
    
    with gr.Row():
        with gr.Column(scale=2):
            query_input = gr.Textbox(
                label="💬 질문",
                placeholder="예: 사랑이란 무엇인가요? / 컴퓨터는 무엇에 사용되나요?",
                lines=2
            )
            
            show_context = gr.Checkbox(
                label="📊 지식 그래프 컨텍스트 보기",
                value=True
            )
            
            submit_btn = gr.Button("🚀 질문하기", variant="primary", size="lg")
        
        with gr.Column(scale=1):
            gr.Markdown("""
            ### 💡 예시 질문
            - 사랑이란 무엇인가?
            - 컴퓨터의 용도는?
            - 행복의 의미
            - 음악과 감정의 관계
            - 책은 어디에 있나요?
            """)
    
    answer_output = gr.Markdown(label="📝 답변")
    context_output = gr.Markdown(label="🗂️ 그래프 컨텍스트", visible=True)
    
    # 이벤트 핸들러
    submit_btn.click(
        fn=talk,
        inputs=[query_input, show_context],
        outputs=[answer_output, context_output]
    )
    
    query_input.submit(
        fn=talk,
        inputs=[query_input, show_context],
        outputs=[answer_output, context_output]
    )
    
    gr.Markdown("""
    ---
    
    ### 🔗 관계 타입 설명
    
    | 아이콘 | 관계 | 설명 |
    |-------|------|------|
    | 🔗 | RelatedTo | 일반적 연관 |
    | 📦 | IsA | ~은 ~이다 (상위 개념) |
    | 🧩 | PartOf | ~의 일부 |
    | 🔧 | UsedFor | ~에 사용됨 |
    | 💪 | CapableOf | ~할 수 있음 |
    | 📍 | AtLocation | ~에 위치 |
    | ⚡ | Causes | ~을 유발 |
    | 🎁 | HasA | ~을 가짐 |
    
    **데이터 출처**: [ConceptNet 5.7.0](https://conceptnet.io/)
    """)

demo.launch(server_name="0.0.0.0", server_port=7860)
