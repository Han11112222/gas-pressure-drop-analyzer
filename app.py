import streamlit as st
import pandas as pd
import io  # 엑셀 파일 변환을 위한 라이브러리 추가

st.set_page_config(page_title="공동주택 관경 적합성 검토기", layout="wide")
st.title("🏢 공동주택 도시가스 관경 사전 검토기")

STANDARD_CAL = 10145 
STANDARD_PRESSURE = 0.3000 

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

if 'reset_data' not in st.session_state:
    st.session_state['reset_data'] = False

with st.sidebar:
    st.header("⚙️ 엑셀 데이터 불러오기")
    uploaded_file = st.file_uploader("관경산출식 엑셀/CSV 업로드", type=['xlsx', 'xls', 'csv'])

input_columns = ['구간', '세대수(세대)', '선정관경', '직관길이(m)', '볼밸브(개)', '90도엘보(개)', '45도엘보(개)', '동경티(개)', '1/4축소티(개)', '1/2레듀샤(개)']

if st.session_state['reset_data']:
    df = pd.DataFrame(columns=input_columns) 
else:
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
        df = pd.DataFrame([
            ["A-B", 1740, "400P", 64.0, 0, 1, 0, 0, 0, 0],
            ["B-C", 1740, "400P", 94.0, 0, 2, 0, 0, 0, 0]
        ], columns=input_columns)

st.markdown("---")

st.markdown("### 1️⃣ 세대당 가스소비량 설정")
col1, col2, col3 = st.columns(3)
boiler_kcal = col1.number_input("보일러 발열량 (kcal/hr)", value=22100, step=100)
range_kcal = col2.number_input("가스레인지 발열량 (kcal/hr)", value=7000, step=100)
household_flow = (boiler_kcal + range_kcal) / STANDARD_CAL 
col3.info(f"💡 산출된 세대당 유량: **{household_flow:.4f} ㎥/hr**")

st.markdown("---")

st.markdown("### 2️⃣ 구간별 도면 물량 입력 (Data Entry)")
st.caption("💡 글자 지우기(백스페이스)로 '구간' 칸을 비우면 해당 줄은 계산에서 완전히 제외됩니다.")

col_btn, _ = st.columns([1, 4])
with col_btn:
    if st.button("🗑️ 표 전체 지우기 (새로 작성)"):
        st.session_state['reset_data'] = True
        st.rerun()

df = df.fillna(0) 

edited_df = st.data_editor(
    df,
    num_rows="dynamic",
    use_container_width=True,
    hide_index=False,
    column_config={
        "선정관경": st.column_config.SelectboxColumn("선정관경", options=list(pipe_data.keys())),
        "직관길이(m)": st.column_config.NumberColumn("직관길이(m)", format="%.2f"),
    }
)

edited_df['구간'] = edited_df['구간'].astype(str).str.strip() 
edited_df = edited_df[~edited_df['구간'].isin(['', '0', 'nan', 'None'])] 
edited_df = edited_df.fillna(0) 

# 계산 로직
for idx, row in edited_df.iterrows():
    pipe_type = str(row['선정관경']).strip()
    if pipe_type not in pipe_data:
        pipe_type = '400P' 
        
    p_info = pipe_data.get(pipe_type)
    
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

for idx, row in edited_df.iterrows():
    pipe_type = str(row['선정관경']).strip()
    if pipe_type not in pipe_data:
        pipe_type = '400P'
        
    p_info = pipe_data.get(pipe_type)
    inner_d = p_info['inner_d']
    
    세대수 = int(row['세대수(세대)'])
    sim_rate = get_sim_rate(세대수)
    q_calc = 세대수 * sim_rate * household_flow
    
    관길이 = row['관길이(m)']
    
    p_drop = 0.01222 * (관길이 * (q_calc ** 2)) / (inner_d ** 5) if inner_d > 0 else 0
    total_actual_drop += p_drop
    
    allowable_drop = STANDARD_PRESSURE * (관길이 / grand_total_length) if grand_total_length > 0 else 0
    
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
        "구간_허용압력(kPa)": round(allowable_drop, 4)
    })

result_df = pd.DataFrame(result_data)

st.markdown("---")

# 엑셀 다운로드를 위한 함수
def convert_df_to_excel(df):
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='관경산출결과')
    return output.getvalue()

col_title, col_download = st.columns([8, 2])
with col_title:
    st.markdown("### 3️⃣ 최종 관경산출표")
with col_download:
    if not result_df.empty:
        excel_data = convert_df_to_excel(result_df)
        st.download_button(
            label="📥 엑셀파일 다운로드",
            data=excel_data,
            file_name="최종관경산출결과.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True
        )

# 포맷팅 적용 (천 단위 콤마 추가 등)
st.dataframe(
    result_df,
    use_container_width=True,
    hide_index=True,
    column_config={
        "세대수(세대)": st.column_config.NumberColumn("세대수(세대)", format="%,d"),
        "유량(㎥/hr)": st.column_config.NumberColumn("유량(㎥/hr)", format="%,.2f"),
        "동시사용률": st.column_config.NumberColumn("동시사용률", format="%.2f"),
        "직관길이(m)": st.column_config.NumberColumn("직관길이(m)", format="%,.2f"),
        "관상당합계": st.column_config.NumberColumn("관상당합계", format="%,.2f"),
        "관길이(m)": st.column_config.NumberColumn("관길이(m)\n(직관+관상당)", format="%,.2f"),
        "실_압력손실(kPa)": st.column_config.NumberColumn("실_압력손실(kPa)\n(실제 지출)", format="%.4f"),
        "구간_허용압력(kPa)": st.column_config.NumberColumn("구간 허용압력(kPa)\n(쪼개진 예산)", format="%.4f"),
    }
)

st.markdown("#### 🎯 최종 판정 결과")
col1, col2, col3 = st.columns([1, 1, 2])
with col1:
    st.metric(label="실압력 손실 (kPa)", value=f"{total_actual_drop:.4f}")
with col2:
    st.metric(label="허용압력 손실 (kPa)", value=f"{STANDARD_PRESSURE:.4f}")
with col3:
    if total_actual_drop == 0:
        st.info("데이터를 입력해 주세요.")
    elif total_actual_drop <= STANDARD_PRESSURE:
        # 적합할 경우 - 녹색 배경에 큰 글씨
        st.markdown("""
        <div style="background-color: #d4edda; padding: 20px; border-radius: 10px; text-align: center; border: 2px solid #c3e6cb;">
            <h2 style="color: #155724; margin: 0; font-size: 2.2rem;">✅ 적 합 (공사 불필요)</h2>
        </div>
        """, unsafe_allow_html=True)
    else:
        # 부적합할 경우 - 빨간색 배경에 큰 글씨
        st.markdown("""
        <div style="background-color: #f8d7da; padding: 20px; border-radius: 10px; text-align: center; border: 2px solid #f5c6cb;">
            <h2 style="color: #721c24; margin: 0; font-size: 2.2rem;">🚨 부 적 합 (관경 확대 요망)</h2>
        </div>
        """, unsafe_allow_html=True)
        
        # 부적합 시 가장 압력손실이 큰 원인 구간 찾아주기
        if not result_df.empty:
            worst_idx = result_df['실_압력손실(kPa)'].idxmax()
            worst_section = result_df.loc[worst_idx, '구간']
            worst_drop = result_df.loc[worst_idx, '실_압력손실(kPa)']
            
            st.markdown(f"""
            <div style="margin-top: 15px; padding: 15px; background-color: #fff3cd; border-left: 5px solid #ffc107; color: #856404;">
                <strong>⚠️ 진단 코멘트:</strong> <span style="font-size:1.1em;"><strong>[{worst_section}]</strong></span> 구간에서 압력손실(<strong>{worst_drop:.4f} kPa</strong>)이 가장 크게 발생하고 있습니다. 해당 구간의 관경 확대를 우선적으로 검토해 보세요!
            </div>
            """, unsafe_allow_html=True)
