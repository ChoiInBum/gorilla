import streamlit as st
from dotenv import load_dotenv
from app import (
    load_documents,
    create_or_load_vectorstore,
    build_qa_chain,
    recommend_card,
    JSON_FILE
)

load_dotenv()

# ----------------------
# QA 체인 초기화
# ----------------------
@st.cache_resource
def init_qa_chain():
    documents = load_documents(JSON_FILE)
    vectordb = create_or_load_vectorstore(documents)
    qa_chain = build_qa_chain(vectordb)
    return qa_chain

qa_chain = init_qa_chain()

# ----------------------
# UI 설정
# ----------------------
st.set_page_config(page_title="카드 추천 챗봇", layout="wide")
st.title("💳 카드 추천 챗봇 (완전 자동 재검색 버전)")

st.markdown("""
💬 **사용 방법**
- 자신의 특징이나 소비 습관을 입력해보세요.
- 예시:
  - "50대 CEO, 주마다 한의원 다님, 명품 좋아하고 자차 있음"  
  - "20대 직장인, 카페 자주 가고 배달앱 많이 씀"  
  - "대학생, 교통비 많고 OTT 결제 자주 함"
""")

# ----------------------
# 세션 상태 초기화
# ----------------------
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []

if "prev_input" not in st.session_state:
    st.session_state.prev_input = ""
if "input_counter" not in st.session_state:
    st.session_state.input_counter = 0

# ----------------------
# 사용자 입력 (자동 재검색용)
# ----------------------
user_input = st.text_input("👉 카드 추천을 위한 조건을 입력하세요:", key=f"user_input_{st.session_state.input_counter}")

# ----------------------
# 입력값이 있을 때 실행
# ----------------------
if user_input:
    # 이전 입력과 같아도 다시 실행
    with st.spinner("💡 맞춤형 카드 분석 중..."):
        meta, all_benefits = recommend_card(qa_chain, user_input)

    # 결과 표시
    if meta:
        benefit_categories = [b.get('category', '기타') for b in all_benefits]
        card_summary = f"💠 **{meta.get('name', '정보 없음')}**\n"
        card_summary += f"- 연회비: {meta.get('fees', '정보 없음')}\n"
        card_summary += f"- 전월 실적: {meta.get('monthly_usage', '정보 없음')}\n"
        card_summary += f"- 브랜드: {meta.get('brand', '정보 없음')}\n"
        card_summary += f"- 주요 혜택 분야: {', '.join(set(benefit_categories)) if benefit_categories else '정보 없음'}"

        card_details = ""
        if all_benefits:
            for b in all_benefits:
                detail_text = b.get('detail_text') or b.get('detail', 'N/A')
                card_details += f"* [{b.get('category', '기타')}] {detail_text}\n\n"
        else:
            card_details = "* 상세 혜택 정보를 불러올 수 없습니다."

        st.session_state.chat_history.append({
            "user": user_input,
            "bot_summary": card_summary,
            "bot_details": card_details
        })
    else:
        st.session_state.chat_history.append({
            "user": user_input,
            "bot_summary": "⚠️ 관련 카드를 찾지 못했습니다.",
            "bot_details": ""
        })

    # 입력값 저장 및 카운터 증가 → 동일 문장 입력 시에도 재검색 가능
    st.session_state.prev_input = user_input
    st.session_state.input_counter += 1
    st.rerun()

# ----------------------
# 대화 표시 (최신순)
# ----------------------
for chat in reversed(st.session_state.chat_history):
    st.chat_message("user").markdown(f"🧍‍♀️ **{chat['user']}**")
    st.chat_message("assistant").markdown(chat["bot_summary"])
    if chat["bot_details"]:
        with st.expander("📋 카드 상세 혜택 보기"):
            st.markdown(chat["bot_details"])