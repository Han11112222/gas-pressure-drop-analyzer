import streamlit as st
import pandas as pd

st.set_page_config(page_title="공동주택 관경 적합성 자동 검토기", layout="wide")
st.title("🏢 공동주택 도시가스 관경 사전 검토기 (Auto-Calc)")

STANDARD_CAL = 10145 

# 관상당 환산길이 기준표 (단위: m)
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

# ==========================================
# 1. 파일 업로드 로직
# ==========================================
with st.sidebar:
    st.header("⚙️ 엑셀 데이터 불러오기")
    uploaded_file = st.file_uploader("관경산출식 엑셀/CSV 업로드", type=['xlsx', 'xls', 'csv'])

input_columns = ['구간', '세대수(세대)', '선정관경', '직관길이(m)', '볼밸브(개)', '90도엘보(개)', '45도엘보(개)', '동경티(개)', '1/4축소티(개)', '1/2레듀샤(개)']

if uploaded_file:
    try:
        xls = pd.ExcelFile(uploaded_file)
        sheet_names = [s for s in xls.sheet_names if '관경산출식' in s]
        selected_sheet = st.sidebar.selectbox("불러올 시트 선택", sheet_names if sheet_names else xls.sheet_names)
        df_excel = pd.read_excel(uploaded_file, sheet_name=selected_sheet, skiprows=7)

        df = df_excel.iloc[:, [1, 9, 16, 11]].copy()
        df.columns = ['구간', '세대수(세대)', '선정관경', '직관길이(m)']
        df = df.dropna(subset=['구간'])
        df = df[~df['구간'].astype(str).str.contains('계|합')]
        
        for fitting in ['볼밸브(개)', '90도엘보(개)', '45도엘보(개)', '동경티(개)', '1/4축소티(개)', '1/2레듀샤(개)']:
            df[fitting] = 0
            
        df = df[input_columns]
        for col in ['세대수(세대)', '직관길이(m)']:
            df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
    except Exception:
        df = pd.DataFrame([["A-B", 1740, "400P", 64.0, 1, 0, 0, 0, 0, 0]], columns=input_columns)
else:
    df = pd.DataFrame([["A-B", 1740, "400P", 64.0, 1, 0, 0, 0, 0, 0]], columns=input_columns)

st.markdown("---")

# ==========================================
# 2. 열량 변환
# ==========================================
st.markdown("### 1️⃣ 세대당 가스소비량 설정")
col1, col2, col3 = st.columns(3)
boiler_kcal = col1.number_input("보일러 발열량 (kcal/hr)", value=22100, step=100)
range_kcal = col2.number_input("가스레인지 발열량 (kcal/hr)", value=7000, step=100)
household_flow = (boiler_kcal + range_kcal) / STANDARD_CAL 
col3.info(f"💡 산출된 세대당 유량: **{household_flow:.4f} ㎥/hr**")

st.markdown("---")

# ==========================================
# 3. 도면 물량 직접 입력 (에디터)
# ==========================================
st.markdown("### 2️⃣ 구간별 도면 물량 입력 (Data Entry)")
st.caption("💡 '직관길이'와 '부속류 수량'을 입력 후 **Enter**를 누르시면, 하단 표에서 **관상당합계**와 **관길이(m)**가 즉시 자동 산출됩니다.")

df = df.fillna(0) # 에디터 초기화 시 결측치 0으로 강제 변환

edited_df = st.data_editor(
    df,
    num_rows="dynamic",
    use_container_width=True,
    hide_index=True,
    column_config={
        "선정관경": st.column_config.SelectboxColumn("선정관경", options=list(pipe_data.keys()), required=True),
        "직관길이(m)": st.column_config.NumberColumn("직관길이(m)", format="%.2f"),
    }
)

edited_df = edited_df.fillna(0) # 에디터 수정 후 결측치 발생 시 0으로 변환 (에러 원천 차단)

# ==========================================
# 4. 백엔드 계산 (관상당합계 & 관길이 산출)
# ==========================================
for idx, row in edited_df.iterrows():
    pipe_type = str(row['선정관경']).strip()
    p_info = pipe_data.get(pipe_type, pipe_data['400P']) 
    
    # 엑셀의 '관상당합계' 수식 구현
    eq_length = (float(row['볼밸브(개)']) * p_info['ball']) + \
                (float(row['90도엘보(개)']) * p_info['el90']) + \
                (float(row['45도엘보(개)']) * p_info['el45']) + \
                (float(row['동경티(개)']) * p_info['tee']) + \
                (float(row['1/4축소티(개)']) * p_info['tee14']) + \
                (float(row['1/2레듀샤(개)']) * p_info['red12'])
                
    total_length = float(row['직관길이(m)']) + eq_length
    
    edited_df.at[idx, '관상당합계'] = eq_length
    edited_df.at[idx, '관길이(m)'] = total_length

# 허용압력손실 분배를 위한 전체 관길이 합산
grand_total_length = edited_df['관길이(m)'].sum()

result_data = []
total_actual_drop = 0
total_allowable_drop = 0

for idx, row in edited_df.iterrows():
    pipe_type = str(row['선정관경']).strip()
    p_info = pipe_data.get(pipe_type, pipe_data['400P']) 
    inner_d = p_info['inner_d']
    
    세대수 = int(row['세대수(세대)'])
    sim_rate = get_sim_rate(세대수)
    q_calc = 세대수 * sim_rate * household_flow
    
    관길이 = row['관길이(m)']
    
    # 실 압력손실 (Pole 공식)
    p_drop = 0.01222 * (관길이 * (q_calc ** 2)) / (inner_d ** 5) if inner_d > 0 else 0
    
    # 허용압력손실 자동 분배
    allowable_drop = 0.3 * (관길이 / grand_total_length) if grand_total_length > 0 else 0
    
    total_actual_drop += p_drop
    total_allowable_drop += allowable_drop
    
    result_data.append({
        "구간": row['구간'],
        "선정관경": pipe_type,
        "세대수(세대)": 세대수,
        "동시사용률": sim_rate,
        "직관길이(m)": round(row['직관길이(m)'], 2),
        "관상당합계": round(row['관상당합계'], 2),
        "관길이(m)": round(관길이, 2),
        "유량(㎥/hr)": round(q_calc, 2),
        "실_압력손실(kPa)": round(p_drop, 4),
        "허용압력손실(kPa)": round(allowable_drop, 4)
    })

result_df = pd.DataFrame(result_data)

st.markdown("---")

# ==========================================
# 5. 최종 결과 표 (뷰어)
# ==========================================
st.markdown("### 3️⃣ 최종 관경산출표")
st.caption("**직관길이 + 관상당합계 = 관길이(m)** 로직이 적용되어 엑셀과 동일한 명칭과 계산값으로 도출됩니다.")

st.dataframe(
    result_df,
    use_container_width=True,
    hide_index=True,
    column_config={
        "동시사용률": st.column_config.NumberColumn("동시사용률", format="%.2f"),
        "직관길이(m)": st.column_config.NumberColumn("직관길이(m)", format="%.2f"),
        "관상당합계": st.column_config.NumberColumn("관상당합계\n(환산수치)", format="%.2f"),
        "관길이(m)": st.column_config.NumberColumn("관길이(m)\n(직관+관상당)", format="%.2f"),
        "실_압력손실(kPa)": st.column_config.NumberColumn("실_압력손실(kPa)", format="%.4f"),
        "허용압력손실(kPa)": st.column_config.NumberColumn("허용압력손실(kPa)", format="%.4f"),
    }
)

col1, col2, col3 = st.columns([1, 1, 2])
with col1:
    st.metric(label="총 실 압력손실 합계", value=f"{total_actual_drop:.4f} kPa")
with col2:
    st.metric(label="총 허용 압력손실 합계", value=f"{total_allowable_drop:.4f} kPa")
with col3:
    if total_actual_drop <= 0.3 and total_actual_drop > 0:
        st.success("✅ **[공사 불필요] 적합 판정** (총 압력손실 0.3kPa 이내 만족)")
    elif total_actual_drop > 0.3:
        st.error("🚨 **[공사 필요] 부적합 (관경 확대 요망)** (총 압력손실 0.3kPa 초과)")
