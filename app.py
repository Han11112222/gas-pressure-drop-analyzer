import streamlit as st
import pandas as pd

st.set_page_config(page_title="공동주택 관경 적합성 자동 검토기", layout="wide")

st.title("🏢 공동주택 도시가스 관경 사전 검토기 (Auto-Calc)")

# 도시가스 표준열량
STANDARD_CAL = 10145 

# 관경별 제원표
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

# 동시사용률 자동 산출 함수 (도시가스 공동주택 설계 기준)
def get_sim_rate(n):
    if n <= 0: return 0.0
    elif n <= 2: return 1.0
    elif n <= 5: return 0.80
    elif n <= 10: return 0.65
    elif n <= 15: return 0.58
    elif n <= 30: return 0.44
    elif n <= 45: return 0.39
    elif n <= 60: return 0.36
    elif n <= 75: return 0.35
    elif n <= 90: return 0.34
    elif n <= 105: return 0.33
    elif n <= 120: return 0.33
    elif n <= 150: return 0.31
    elif n <= 200: return 0.30
    elif n <= 300: return 0.29
    else: return 0.28

# ==========================================
# 1. 좌측 사이드바: 엑셀 파일 업로드
# ==========================================
with st.sidebar:
    st.header("⚙️ 엑셀 데이터 불러오기")
    uploaded_file = st.file_uploader("관경산출식 엑셀/CSV 업로드", type=['xlsx', 'xls', 'csv'])
    st.info("파일을 업로드하면 기존 구간과 세대수 정보가 자동으로 입력됩니다.")

# 데이터프레임 초기화
input_columns = ['구간', '세대수', '직관길이(m)', '선정관경', '밸브(개)', '90도엘보(개)', '티(개)', '허용압력손실']

if uploaded_file:
    try:
        # 엑셀 파일 읽기 및 시트 선택
        xls = pd.ExcelFile(uploaded_file)
        sheet_names = [s for s in xls.sheet_names if '관경산출식' in s]
        sheet_names = sheet_names if sheet_names else xls.sheet_names
        selected_sheet = st.sidebar.selectbox("불러올 시트 선택", sheet_names)
        df_excel = pd.read_excel(uploaded_file, sheet_name=selected_sheet, skiprows=7)

        # 엑셀 데이터 매핑 (1:구간, 9:세대수, 11:관길이, 16:선정관경, 18:허용압력)
        df = df_excel.iloc[:, [1, 9, 11, 16, 18]].copy()
        df.columns = ['구간', '세대수', '직관길이(m)', '선정관경', '허용압력손실']
        
        # 필터링
        df = df.dropna(subset=['구간'])
        df = df[~df['구간'].astype(str).str.contains('계|합')]
        
        # 부속류 기본값 0 추가
        df['밸브(개)'] = 0
        df['90도엘보(개)'] = 0
        df['티(개)'] = 0
        
        # 컬럼 순서 정렬
        df = df[input_columns]
        
        # 숫자형 변환
        for col in ['세대수', '직관길이(m)', '허용압력손실']:
            df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)

    except Exception as e:
        st.sidebar.error(f"엑셀을 읽는 중 오류가 발생했습니다. 직접 입력 모드로 진행합니다. ({e})")
        df = pd.DataFrame([["A-B", 1740, 64.0, "400P", 1, 0, 0, 0.0455]], columns=input_columns)
else:
    df = pd.DataFrame([["A-B", 1740, 64.0, "400P", 1, 0, 0, 0.0455]], columns=input_columns)

st.markdown("---")

# ==========================================
# 2. 상단: 글로벌 변수 입력 (연소기 열량 -> 유량 변환)
# ==========================================
st.markdown("### 1️⃣ 세대당 가스소비량 설정")
col1, col2, col3 = st.columns(3)
boiler_kcal = col1.number_input("보일러 발열량 (kcal/hr)", value=22100, step=100)
range_kcal = col2.number_input("가스레인지 발열량 (kcal/hr)", value=7000, step=100)

total_kcal = boiler_kcal + range_kcal
household_flow = total_kcal / STANDARD_CAL 
col3.info(f"💡 **계산된 세대당 유량:**\n\n(총 {total_kcal:,} kcal/hr) ÷ 10,145 = **{household_flow:.4f} ㎥/hr**")

st.markdown("---")

# ==========================================
# 3. 중단: 담당자 물량 직접 입력창 (동시사용률 제외됨)
# ==========================================
st.markdown("### 2️⃣ 구간별 데이터 입력 (Data Entry)")
st.caption("엑셀에서 불러온 데이터를 확인하거나, 직접 **세대수**, **직관길이**, **부속류**를 수정하세요. 동시사용률은 자동 계산됩니다.")

edited_df = st.data_editor(
    df,
    num_rows="dynamic",
    use_container_width=True,
    hide_index=True,
    column_config={
        "세대수": st.column_config.NumberColumn("세대수 (입력)", format="%d"),
        "선정관경": st.column_config.SelectboxColumn("선정관경", options=list(pipe_data.keys()), required=True),
        "허용압력손실": st.column_config.NumberColumn("허용압력(예산)", format="%.4f"),
    }
)

# ==========================================
# 4. 백엔드: 자동 계산 로직
# ==========================================
result_data = []
total_actual_drop = 0
total_allowable_drop = 0

for idx, row in edited_df.iterrows():
    pipe_type = str(row['선정관경']).strip()
    p_info = pipe_data.get(pipe_type, pipe_data['400P']) 
    
    # 1) 세대수 기반 동시사용률 자동 산출
    sim_rate = get_sim_rate(int(row['세대수']))
    
    # 2) 부속류 수량을 관상당환산길이(m)로 변환
    eq_length = (row['밸브(개)'] * p_info['valve']) + \
                (row['90도엘보(개)'] * p_info['elbow90']) + \
                (row['티(개)'] * p_info['tee'])
    
    # 3) 총 관길이
    total_length = row['직관길이(m)'] + eq_length
    
    # 4) 유량 계산 (세대수 * 동시사용률 * 세대당유량)
    q_calc = row['세대수'] * sim_rate * household_flow
    
    # 5) 실 압력손실 계산
    inner_d = p_info['inner_d']
    p_drop = 0.01222 * (total_length * (q_calc ** 2)) / (inner_d ** 5) if inner_d > 0 else 0
    
    total_actual_drop += p_drop
    total_allowable_drop += row['허용압력손실']
    
    result_data.append({
        "구간": row['구간'],
        "세대수": int(row['세대수']),
        "동시사용률": sim_rate,  # 자동 산출된 값 표시
        "관길이(m)": round(total_length, 2),
        "유량합계(㎥/hr)": round(q_calc, 2),
        "선정관경": pipe_type,
        "실_압력손실(kPa)": round(p_drop, 4),
        "허용압력손실(kPa)": row['허용압력손실']
    })

result_df = pd.DataFrame(result_data)

st.markdown("---")

# ==========================================
# 5. 하단: 최종 산출 결과표
# ==========================================
st.markdown("### 3️⃣ 최종 관경산출표 (Auto-Generated)")
st.caption("담당자가 입력한 세대수와 물량을 바탕으로 **동시사용률, 환산길이, 압력손실**이 자동 적용된 결과입니다.")

st.dataframe(
    result_df,
    use_container_width=True,
    hide_index=True,
    column_config={
        "동시사용률": st.column_config.NumberColumn("동시사용률 (자동)", format="%.2f"),
        "관길이(m)": st.column_config.NumberColumn("총 관길이(m)", format="%.2f"),
        "실_압력손실(kPa)": st.column_config.NumberColumn("실_압력손실(kPa)", format="%.4f"),
        "허용압력손실(kPa)": st.column_config.NumberColumn("허용압력손실(kPa)", format="%.4f"),
    }
)

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
