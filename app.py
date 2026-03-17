import streamlit as st
import pandas as pd

st.set_page_config(page_title="공동주택 관경 적합성 자동 검토기", layout="wide")
st.title("🏢 공동주택 도시가스 관경 사전 검토기 (Auto-Calc)")

STANDARD_CAL = 10145 

# 엑셀 [표(관상당)] 시트와 100% 동일하게 부속류 제원표 완벽 동기화 (오류 수정 완료)
pipe_data = {
    '400P': {'inner_d': 32.92, 'ball': 2.36, 'el90': 9.53, 'el45': 4.76, 'tee': 28.50, 'tee14': 9.53, 'red12': 4.05},
    '355P': {'inner_d': 29.04, 'ball': 2.13, 'el90': 8.51, 'el45': 4.25, 'tee': 24.68, 'tee14': 7.66, 'red12': 3.49},
    '280P': {'inner_d': 22.92, 'ball': 1.65, 'el90': 7.28, 'el45': 3.64, 'tee': 18.77, 'tee14': 6.53,  'red12': 2.63},
    '225P': {'inner_d': 18.50, 'ball': 1.31, 'el90': 5.82,  'el45': 2.91, 'tee': 12.74, 'tee14': 5.34,  'red12': 2.18},
    '160P': {'inner_d': 13.18, 'ball': 0.93, 'el90': 4.07,  'el45': 2.04, 'tee': 8.49, 'tee14': 3.65,  'red12': 1.53},
    '90P':  {'inner_d': 7.36,  'ball': 0.49, 'el90': 2.24,  'el45': 1.12, 'tee': 3.79,  'tee14': 1.32,  'red12': 0.84},
    '65S':  {'inner_d': 6.90,  'ball': 0.43, 'el90': 2.00,  'el45': 1.00, 'tee': 3.20,  'tee14': 1.30,  'red12': 0.70},
    '50S':  {'inner_d': 5.32,  'ball': 0.35, 'el90': 1.70,  'el45': 0.85, 'tee': 2.60,  'tee14': 1.00,  'red12': 0.60},
    '40S':  {'inner_d': 4.21,  'ball': 0.30, 'el90': 1.40,  'el45': 0.70, 'tee': 2.10,  'tee14': 0.70,  'red12': 0.45}
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
        df = pd.DataFrame([["A-B", 1740, "400P", 64.0, 0, 1, 0, 0, 0, 0]], columns=input_columns)
else:
    df = pd.DataFrame([["A-B", 1740, "400P", 64.0, 0, 1, 0, 0, 0, 0]], columns=input_columns)

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
st.caption("💡 '직관길이'와 '부속류 수량'을 입력 후 **Enter**를 누르시면, 하단 표에서 **관상당합계**와 **관길이(m)**가 즉시 엑셀과 동일하게 자동 산출됩니다.")

df = df.fillna(0) 

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

edited_df = edited_df.fillna(0) 

# ==========================================
# 4. 백엔드 계산 (관상당합계 & 관길이 정확한 환산율 적용)
# ==========================================
for idx, row in edited_df.iterrows():
    pipe_type = str(row['선정관경']).strip()
    p_info = pipe_data.get(pipe_type, pipe_data['400P']) 
    
    eq_length = (float(row['볼밸브(개)']) * p_info['ball']) + \
                (float(row['90도엘보(개)']) * p_info['el90']) + \
                (float(row['45도엘보(개)']) * p_info['el45']) + \
                (float(row['동경티(개)']) * p_info['tee']) + \
                (float(row['1/4축소티(개)']) * p_info['tee14']) + \
                (float(row['1/2레듀샤(개)']) * p_info['red12'])
                
    total_length = float(row['직관길이(m)']) + eq_length
    
    edited_df.at[idx, '관상당합계'] = eq_length
    edited_df.at[idx, '관길이(m)'] = total_length

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
    
    p_drop = 0.01222 * (관길이 * (q_calc ** 2)) / (inner_d ** 5) if inner_d > 0 else 0
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
st.caption("✅ **수정 완료:** 이제 엑셀의 관상당환산표 기준값과 동일하게 환산길이가 곱해집니다. (예: 400P 90도 엘보 1개 = 9.53m)")

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
