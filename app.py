import streamlit as st
import pandas as pd

st.set_page_config(page_title="공동주택 관경 적합성 자동 검토기", layout="wide")
st.title("🏢 공동주택 도시가스 관경 사전 검토기 (Auto-Calc)")

STANDARD_CAL = 10145 

pipe_data = {
    '400P': {'inner_d': 32.92, 'ball': 4.0, 'el90': 18.0, 'el45': 9.0, 'tee': 25.0, 'tee14': 12.0, 'red12': 9.0},
    '355P': {'inner_d': 29.04, 'ball': 3.5, 'el90': 16.0, 'el45': 8.0, 'tee': 22.0, 'tee14': 10.0, 'red12': 8.0},
    '280P': {'inner_d': 22.92, 'ball': 2.5, 'el90': 11.0, 'el45': 5.5, 'tee': 16.0, 'tee14': 7.0,  'red12': 5.0},
    '225P': {'inner_d': 18.50, 'ball': 2.0, 'el90': 9.0,  'el45': 4.5, 'tee': 13.0, 'tee14': 6.0,  'red12': 4.0},
    '160P': {'inner_d': 13.18, 'ball': 1.1, 'el90': 4.8,  'el45': 2.4, 'tee': 10.0, 'tee14': 4.3,  'red12': 1.8},
    '90P':  {'inner_d': 7.36,  'ball': 0.5, 'el90': 2.4,  'el45': 1.2, 'tee': 4.0,  'tee14': 1.5,  'red12': 0.9},
    '65S':  {'inner_d': 6.90,  'ball': 0.43,'el90': 2.0,  'el45': 1.0, 'tee': 3.2,  'tee14': 1.3,  'red12': 0.7},
    '50S':  {'inner_d': 5.32,  'ball': 0.35,'el90': 1.7,  'el45': 0.85,'tee': 2.6,  'tee14': 1.0,  'red12': 0.6},
    '40S':  {'inner_d': 4.21,  'ball': 0.30,'el90': 1.4,  'el45': 0.7, 'tee': 2.1,  'tee14': 0.7,  'red12': 0.45}
}

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

# 1. 파일 업로드 로직
with st.sidebar:
    st.header("⚙️ 엑셀 데이터 불러오기")
    uploaded_file = st.file_uploader("관경산출식 엑셀/CSV 업로드", type=['xlsx', 'xls', 'csv'])

input_columns = ['구간', '세대수', '직관길이(m)', '선정관경', '볼밸브', '90도엘보', '45도엘보', '동경티', '1/4축소티', '1/2레듀샤', '허용압력손실']

if uploaded_file:
    try:
        xls = pd.ExcelFile(uploaded_file)
        sheet_names = [s for s in xls.sheet_names if '관경산출식' in s]
        selected_sheet = st.sidebar.selectbox("불러올 시트 선택", sheet_names if sheet_names else xls.sheet_names)
        df_excel = pd.read_excel(uploaded_file, sheet_name=selected_sheet, skiprows=7)

        df = df_excel.iloc[:, [1, 9, 11, 16, 18]].copy()
        df.columns = ['구간', '세대수', '직관길이(m)', '선정관경', '허용압력손실']
        df = df.dropna(subset=['구간'])
        df = df[~df['구간'].astype(str).str.contains('계|합')]
        
        for fitting in ['볼밸브', '90도엘보', '45도엘보', '동경티', '1/4축소티', '1/2레듀샤']:
            df[fitting] = 0
            
        df = df[input_columns]
        for col in ['세대수', '직관길이(m)', '허용압력손실']:
            df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
    except Exception:
        df = pd.DataFrame([["A-B", 1740, 64.0, "400P", 1, 0, 0, 0, 0, 0, 0.0455]], columns=input_columns)
else:
    df = pd.DataFrame([["A-B", 1740, 64.0, "400P", 1, 0, 0, 0, 0, 0, 0.0455]], columns=input_columns)

st.markdown("---")

# 2. 열량 변환
st.markdown("### 1️⃣ 세대당 가스소비량 설정")
col1, col2, col3 = st.columns(3)
boiler_kcal = col1.number_input("보일러 발열량 (kcal/hr)", value=22100, step=100)
range_kcal = col2.number_input("가스레인지 발열량 (kcal/hr)", value=7000, step=100)
household_flow = (boiler_kcal + range_kcal) / STANDARD_CAL 
col3.info(f"💡 계산된 세대당 유량: **{household_flow:.4f} ㎥/hr**")

st.markdown("---")

# 3. 도면 물량 직접 입력
st.markdown("### 2️⃣ 구간별 도면 물량 입력 (에디터)")
st.caption("💡 '세대수'나 '부속류 개수'를 수정하고 **Enter**를 누르시면 아래 표에 즉시 연동됩니다. (빈칸은 0으로 자동 처리됩니다.)")

edited_df = st.data_editor(
    df,
    num_rows="dynamic",
    use_container_width=True,
    hide_index=True,
    column_config={
        "선정관경": st.column_config.SelectboxColumn("선정관경", options=list(pipe_data.keys()), required=True),
        "허용압력손실": st.column_config.NumberColumn("허용압력손실", format="%.4f"),
    }
)

# 4. 백엔드 계산 (빈칸 방어 로직 추가)
# 에디터에서 발생한 결측치(None, NaN)를 모두 0으로 강제 변환하여 수식 에러 방지
edited_df = edited_df.fillna(0)

result_data = []
total_actual_drop = 0
total_allowable_drop = 0

for idx, row in edited_df.iterrows():
    pipe_type = str(row['선정관경']).strip()
    p_info = pipe_data.get(pipe_type, pipe_data['400P']) 
    
    # 숫자형 데이터 안전 추출
    세대수 = int(row['세대수']) if pd.notnull(row['세대수']) and row['세대수'] != '' else 0
    직관길이 = float(row['직관길이(m)']) if pd.notnull(row['직관길이(m)']) and row['직관길이(m)'] != '' else 0.0
    허용압력 = float(row['허용압력손실']) if pd.notnull(row['허용압력손실']) and row['허용압력손실'] != '' else 0.0
    
    sim_rate = get_sim_rate(세대수)
    
    # 부속류 환산길이 계산
    eq_length = (float(row['볼밸브']) * p_info['ball']) + \
                (float(row['90도엘보']) * p_info['el90']) + \
                (float(row['45도엘보']) * p_info['el45']) + \
                (float(row['동경티']) * p_info['tee']) + \
                (float(row['1/4축소티']) * p_info['tee14']) + \
                (float(row['1/2레듀샤']) * p_info['red12'])
                
    # 총길이 = 직관길이 + 관상당합계
    total_length = 직관길이 + eq_length
    q_calc = 세대수 * sim_rate * household_flow
    
    inner_d = p_info['inner_d']
    p_drop = 0.01222 * (total_length * (q_calc ** 2)) / (inner_d ** 5) if inner_d > 0 else 0
    
    total_actual_drop += p_drop
    total_allowable_drop += 허용압력
    
    # 3번 표에 보여줄 데이터 조립 (직관, 부속, 총길이 분리)
    result_data.append({
        "구간": row['구간'],
        "세대수": 세대수,
        "동시사용률": sim_rate,
        "선정관경": pipe_type,
        "직관길이(m)": round(직관길이, 2),
        "관상당합계(m)": round(eq_length, 2),
        "총관길이(m)": round(total_length, 2),
        "유량(㎥/hr)": round(q_calc, 2),
        "실_압력손실": round(p_drop, 4),
        "허용압력손실": 허용압력
    })

result_df = pd.DataFrame(result_data)

st.markdown("---")

# 5. 최종 결과 표 (뷰어)
st.markdown("### 3️⃣ 최종 관경산출표 (자동 계산 결과)")

st.dataframe(
    result_df,
    use_container_width=True,
    hide_index=True,
    column_config={
        "동시사용률": st.column_config.NumberColumn("동시사용률", format="%.2f"),
        "직관길이(m)": st.column_config.NumberColumn("직관길이(m)", format="%.2f"),
        "관상당합계(m)": st.column_config.NumberColumn("관상당합계(m)", format="%.2f"),
        "총관길이(m)": st.column_config.NumberColumn("총관길이(직관+부속)", format="%.2f"),
        "실_압력손실": st.column_config.NumberColumn("실_압력손실(계산치)", format="%.4f kPa"),
        "허용압력손실": st.column_config.NumberColumn("허용압력손실(목표치)", format="%.4f kPa"),
    }
)

col1, col2, col3 = st.columns([1, 1, 2])
with col1:
    st.metric(label="총 실 압력손실 (계산치)", value=f"{total_actual_drop:.4f} kPa")
with col2:
    budget = total_allowable_drop if total_allowable_drop > 0 else 0.3000
    st.metric(label="총 허용 압력손실 (목표치)", value=f"{budget:.4f} kPa")
with col3:
    if total_actual_drop <= budget and total_actual_drop > 0:
        st.success("✅ **[공사 불필요] 사용 가능** (압력손실 기준치 이내)")
    elif total_actual_drop > budget:
        st.error("🚨 **[공사 필요] 관경 확대 요망** (압력손실 기준치 초과)")
