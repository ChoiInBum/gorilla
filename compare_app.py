# compare_app.py
import streamlit as st
import pandas as pd
from io import StringIO
from dotenv import load_dotenv
from openai import OpenAI
from app import (
    load_documents,
    create_or_load_vectorstore,
    build_qa_chain,
    recommend_card,
    JSON_FILE
)

# ----------------------
# 환경설정 로드 및 모델 초기화
# ----------------------
load_dotenv()
client = OpenAI()

st.set_page_config(page_title="모델 비교 평가", layout="wide")
st.title("🧩 Base vs RAG 카드 추천 모델 비교 평가")

# ----------------------
# 평가 가이드라인
# ----------------------
with st.expander("📋 평가 가이드라인 보기"):
    st.markdown("""
    **평가 항목 (참고용)**  
    - 🧾 **사실성**: 추천한 카드가 실제로 존재하며, 모델 설명과 혜택이 일치하는가  
    - 🎯 **적합성**: 제시된 카드가 페르소나/조건에 적합한가  
    - 🔁 **일관성**: 동일 입력에서 유사한 결과가 일관되게 나오는가  

    **최종 평가 기준 (총점 기준)**  
    - 8~9점 → ⭐ 상  
    - 5~7점 → ⚖️ 중  
    - 3~4점 → 👎 하
    """)

# ----------------------
# Session state 초기화
# ----------------------
for key in ["results", "last_input", "base_outputs", "rag_outputs"]:
    if key not in st.session_state:
        st.session_state[key] = []

# ----------------------
# RAG 체인 초기화
# ----------------------
@st.cache_resource
def init_rag_chain():
    documents = load_documents(JSON_FILE)
    vectordb = create_or_load_vectorstore(documents)
    qa_chain = build_qa_chain(vectordb)
    return qa_chain

qa_chain = init_rag_chain()

# ----------------------
# 사용자 입력
# ----------------------
user_input = st.text_input("👉 카드 추천 조건(페르소나 또는 상황)을 입력하세요:")
n_rounds = st.number_input("응답 생성 횟수 (각 모델당)", min_value=1, max_value=20, value=3, step=1)

# 새로운 입력 시 state 초기화
if user_input and user_input != st.session_state.last_input:
    st.session_state.results = []
    st.session_state.base_outputs = []
    st.session_state.rag_outputs = []
    st.session_state.last_input = user_input


# ----------------------
# 실행 버튼
# ----------------------
if st.button("🔍 모델 비교 실행"):
    if not user_input:
        st.warning("질문을 입력해주세요!")
        st.stop()

    col1, col2 = st.columns(2)

    # ---------------------- BASE 모델 ----------------------
    with col1:
        st.subheader("💡 Base 모델 (gpt-4o-mini)")

        if not st.session_state.base_outputs:
            for i in range(n_rounds):
                with st.spinner(f"Base 모델 응답 생성 중... ({i+1}/{n_rounds})"):
                    response = client.responses.create(
                        model="gpt-4o-mini",
                        input=user_input,
                        temperature=0.8
                    )
                    st.session_state.base_outputs.append(response.output_text)

        for i, base_text in enumerate(st.session_state.base_outputs):
            with st.expander(f"📜 Base 응답 {i+1}", expanded=False):
                st.write(base_text)

            st.session_state.results.append({
                "질문": user_input,
                "모델": "Base (gpt-4o-mini)",
                "응답번호": i + 1,
                "응답내용": base_text,
                "사실성": "",
                "적합성": "",
                "일관성": "",
                "총점": "",
                "모델성능": ""
            })

    # ---------------------- RAG 모델 ----------------------
    with col2:
        st.subheader("💳 RAG 모델 (카드DB 기반)")

        if not st.session_state.rag_outputs:
            for i in range(n_rounds):
                with st.spinner(f"RAG 모델 응답 생성 중... ({i+1}/{n_rounds})"):
                    meta, all_benefits = recommend_card(qa_chain, user_input)
                    st.session_state.rag_outputs.append((meta, all_benefits))

        for i, (meta, all_benefits) in enumerate(st.session_state.rag_outputs):
            if not meta:
                card_summary = "❌ 관련 카드를 찾지 못했습니다."
                card_details = ""
            else:
                card_summary = f"💠 **{meta.get('name','정보 없음')}**\n"
                card_summary += f"- 연회비: {meta.get('fees','정보 없음')}\n"
                card_summary += f"- 전월 실적: {meta.get('monthly_usage','정보 없음')}\n"
                card_summary += f"- 브랜드: {meta.get('brand','정보 없음')}\n"
                benefit_categories = [b.get('category','기타') for b in all_benefits]
                if benefit_categories:
                    card_summary += f"- 주요 혜택 분야: {', '.join(set(benefit_categories))}"

                card_details = "\n".join(
                    [f"* [{b.get('category','기타')}] {b.get('detail_text') or b.get('detail','N/A')}" for b in all_benefits]
                )

            with st.expander(f"💳 RAG 응답 {i+1}", expanded=False):
                st.markdown(card_summary)
                if card_details:
                    with st.expander("📂 카드 상세 혜택 더 보기", expanded=False):
                        st.text(card_details)

            st.session_state.results.append({
                "질문": user_input,
                "모델": "RAG (카드DB 기반)",
                "응답번호": i + 1,
                "응답내용": card_summary + "\n" + card_details,
                "사실성": "",
                "적합성": "",
                "일관성": "",
                "총점": "",
                "모델성능": ""
            })

    st.success("✅ 모든 응답이 출력되었습니다. 상태가 자동으로 저장됩니다.")

    # ----------------------
    # CSV 다운로드
    # ----------------------
    if st.session_state.results:
        df = pd.DataFrame(st.session_state.results)
        csv_buffer = StringIO()
        df.to_csv(csv_buffer, index=False, encoding="utf-8-sig")

        st.download_button(
            label="📥 평가 결과 CSV로 다운로드",
            data=csv_buffer.getvalue(),
            file_name=f"model_comparison_results.csv",
            mime="text/csv"
        )