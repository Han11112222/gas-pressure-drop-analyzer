import streamlit as st
import pandas as pd

st.set_page_config(page_title="공동주택 관경 적합성 자동 검토기", layout="wide")

st.title("🏢 공동주택 도시가스 관경 사전 검토기 (Auto-Calc)")

# 도시가스 표준열량 (대성에너지 기준: 10,145 kcal/㎥)
STANDARD_CAL = 10145 

# 관경별 제원표 (내경cm, 밸브환산m, 90도엘보환산m, 티환산m) - 엑셀 [표(관상당)] 시트 참고 세팅
pipe_data = {
    '400P': {'inner_d': 32.92, 'valve': 4.0, 'elbow90': 18.0, 'tee': 25.0},
    '355P': {'inner_d': 29.04, 'valve': 3.5, 'elbow90': 16.0, 'tee': 22.0},
    '280P': {'inner_d': 22.92, 'valve': 2.5, 'elbow90': 11.0, 'tee': 16.0},
    '225P': {'inner_d': 18.50, 'valve': 2.0, 'elbow90': 9.0,  'tee': 13.0},
    '160P': {'inner_d': 13.18, 'valve': 1.1, 'elbow90': 4.8,  'tee': 10.0},
    '90P':  {'inner_d': 7.36,  'valve': 0.5, 'elbow90': 2.4,  'tee': 4.0},
    '65S':  {'inner_d': 6.90,  'valve': 0.43,'elbow90': 2.0,  'tee': 3.2},
    '50S':  {'inner_d': 5.32,  'valve': 0.35,'elbow90': 1.7,  'tee': 2.6},
    '40S':  {'inner_d': 4.21,  'valve': 0.30,'elbow90': 1.4,  'tee': 2.1}
}

st.markdown("---")

# ==========================================
# 1. 상단: 글로벌 변수 입력 (연소기 열량 -> 유량 변환)
# ==========================================
st.markdown("### 1️⃣ 세대당 가스소비량 설정")
col1, col2, col3 = st.columns(3)
boiler_kcal = col1.number_input("보일러 발열량 (kcal/hr)", value=22100, step=100)
range_kcal = col2.number_input("가스레인지 발열량 (kcal/hr)", value=7000, step=100)

total_kcal = boiler_kcal + range_kcal
household_flow = total_kcal / STANDARD_CAL # m3/hr 변환
col3.info(f"💡 **계산된 세대당 유량:**\n\n(총 {total_kcal:,} kcal/hr) ÷ 10,145 = **{household_flow:.4f} ㎥/hr**")

st.markdown("---")

# ==========================================
# 2. 중단: 담당자 도면 물량 직접 입력창
# ==========================================
st.markdown("### 2️⃣ 구간별 도면 물량 입력 (Data Entry)")
st.caption("도면을 보고 각 구간의 세대수, 직관길이, 그리고 부속류(밸브, 엘보, 티)의 개수만 입력하세요.")

# 초기 입력 양식 제공
input_columns = ['구간', '세대수', '동시사용률', '직관길이(m)', '선정관경', '밸브(개)', '90도엘보(개)', '티(개)', '허용압력손실']
default_df = pd.DataFrame([
    ["A-B", 1740, 0.28, 64.0, "400P", 1, 0, 0, 0.0455],
    ["B-C", 1740, 0.28, 94.0, "400P", 0, 2, 0, 0.0522],
    ["C-D", 1740, 0.28, 61.0, "400P", 0, 1, 0, 0.0389]
], columns=input_columns)

# 담당자 입력용 데이터 에디터 (여기서 편집한 값이 최종 계산의 뼈대가 됨)
edited_df = st.data_editor(
    default_df,
    num_rows="dynamic",
    use_container_width=True,
    hide_index=True,
    column_config={
        "선정관경": st.column_config.SelectboxColumn("선정관경", options=list(pipe_data.keys()), required=True),
        "동시사용률": st.column_config.NumberColumn("동시사용률", format="%.2f"),
        "허용압력손실": st.column_config.NumberColumn("허용압력(예산)", format="%.4f"),
    }
)

# ==========================================
# 3. 백엔드: 자동 계산 로직 (엑셀 수식 대체)
# ==========================================
result_data = []
total_actual_drop = 0
total_allowable_drop = 0

for idx, row in edited_df.iterrows():
    pipe_type = row['선정관경']
    p_info = pipe_data.get(pipe_type, pipe_data['400P']) # 매핑 실패 시 400P 기본값
    
    # 1) 부속류 수량을 관상당환산길이(m)로 자동 변환
    eq_length = (row['밸브(개)'] * p_info['valve']) + \
                (row['90도엘보(개)'] * p_info['elbow90']) + \
                (row['티(개)'] * p_info['tee'])
    
    # 2) 총 관길이 = 직관길이 + 환산길이합계
    total_length = row['직관길이(m)'] + eq_length
    
    # 3) 유량 계산 = 세대수 * 동시사용률 * 세대당유량
    q_calc = row['세대수'] * row['동시사용률'] * household_flow
    
    # 4) 실 압력손실 계산 (Pole 공식)
    inner_d = p_info['inner_d']
    p_drop = 0.01222 * (total_length * (q_calc ** 2)) / (inner_d ** 5) if inner_d > 0 else 0
    
    total_actual_drop += p_drop
    total_allowable_drop += row['허용압력손실']
    
    # 결과 행 조립
    result_data.append({
        "구간": row['구간'],
        "세대수 합계": int(row['세대수']),
        "동시사용률": row['동시사용률'],
        "관길이(m)": round(total_length, 2),
        "유량합계(㎥/hr)": round(q_calc, 2),
        "선정관경": pipe_type,
        "실_압력손실(kPa)": round(p_drop, 4),
        "허용압력손실(kPa)": row['허용압력손실']
    })

result_df = pd.DataFrame(result_data)

st.markdown("---")

# ==========================================
# 4. 하단: 최종 산출 결과표 (View Only)
# ==========================================
st.markdown("### 3️⃣ 최종 관경산출표 (Auto-Generated)")
st.caption("위에서 입력한 데이터를 바탕으로 환산길이와 압력손실이 자동 적용된 최종 결과입니다.")

st.dataframe(
    result_df,
    use_container_width=True,
    hide_index=True,
    column_config={
        "관길이(m)": st.column_config.NumberColumn("관길이(m)\n(직관+부속류)", format="%.2f"),
        "실_압력손실(kPa)": st.column_config.NumberColumn("실_압력손실(kPa)", format="%.4f"),
        "허용압력손실(kPa)": st.column_config.NumberColumn("허용압력손실(kPa)", format="%.4f"),
    }
)

# 판정 결과 대시보드
col1, col2, col3 = st.columns([1, 1, 2])
with col1:
    st.metric(label="총 실 압력손실", value=f"{total_actual_drop:.4f} kPa")
with col2:
    budget = total_allowable_drop if total_allowable_drop > 0 else 0.3000
    st.metric(label="총 허용 압력손실", value=f"{budget:.4f} kPa")
with col3:
    if total_actual_drop <= budget and total_actual_drop > 0:
        st.success("✅ **[공사 불필요] 사용 가능** (압력손실 기준치 이내)")
    elif total_actual_drop > budget:
        st.error("🚨 **[공사 필요] 관경 확대 요망** (압력손실 기준치 초과)")
