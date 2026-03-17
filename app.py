import streamlit as st
import pandas as pd

st.set_page_config(page_title="공동주택 관경 적합성 검토기", layout="wide")

st.title("🏢 공동주택 도시가스 전환 사전 검토기")

# 1. 개념 설명 및 공사 가능/불가능 가이드 (중학생 수준 직관적 설명)
with st.expander("📖 (필독) 허용압력과 실압력, 어떻게 해석할까요?", expanded=True):
    st.markdown("""
    가스 배관을 **'고속도로'**, 가스를 **'자동차'**, 0.3kPa을 **'사용 가능한 총예산'**이라고 상상해 보세요.
    
    * 💰 **허용압력손실 (예산):** "이 구간에서는 압력을 최대 이만큼까지만 까먹어도 돼!"라고 정해놓은 **할당된 예산**입니다. 관길이가 길수록 예산이 많이 배정됩니다.
    * 💸 **실압력손실 (실제 지출):** 배관(선정관경)의 크기와 가스량에 따라 마찰로 인해 **실제로 잃어버리는 압력(실제 지출)**입니다.
    
    ✅ **[공사 불필요 (사용 가능)]** : **실압력손실(지출) $\le$ 허용압력손실(예산)** 🚨 **[공사 필요 (배관 교체)]** : **실압력손실(지출) > 허용압력손실(예산)** (배관이 좁아 예산 초과!)
    """)

# 기본 컬럼 세팅
default_columns = ['구간', '세대수 합계', '동시사용률', '관길이(m)', '유량합계(㎥/hr)', '계산관경', '선정관경', '실_압력손실(kPa)', '허용압력손실(kPa)']

# 관경별 내경(cm) 매핑 딕셔너리 (Pole 공식 자동 계산용)
pipe_diameters = {
    '400P': 32.92, '355P': 29.04, '280P': 22.92, '225P': 18.50,
    '160P': 13.18, '110P': 9.00, '90P': 7.36, '65S': 6.90, '50S': 5.32, '40S': 4.21
}

# 2. 파일 업로드 로직
with st.sidebar:
    st.header("⚙️ 데이터 불러오기")
    uploaded_file = st.file_uploader("관경산출식 엑셀/CSV 업로드", type=['xlsx', 'xls', 'csv'])
    auto_calc = st.checkbox("🔄 자동 계산 모드 켜기", value=True, help="세대수나 관길이를 수정하면 유량과 실압력손실이 엑셀처럼 자동 계산됩니다.")

if uploaded_file:
    try:
        if uploaded_file.name.endswith('csv'):
            df = pd.read_csv(uploaded_file, skiprows=7)
        else:
            xls = pd.ExcelFile(uploaded_file)
            sheet_names = [s for s in xls.sheet_names if '관경산출식' in s]
            sheet_names = sheet_names if sheet_names else xls.sheet_names
            selected_sheet = st.sidebar.selectbox("불러올 시트 선택", sheet_names)
            df = pd.read_excel(uploaded_file, sheet_name=selected_sheet, skiprows=7)

        # 데이터 정제 및 합계 행 필터링
        df = df.iloc[:, [1, 9, 10, 11, 13, 14, 16, 17, 18]].copy()
        df.columns = default_columns
        df = df.dropna(subset=['구간'])
        df = df[~df['구간'].astype(str).str.contains('계|합')]
        
        for col in ['세대수 합계', '동시사용률', '관길이(m)', '유량합계(㎥/hr)', '계산관경', '실_압력손실(kPa)', '허용압력손실(kPa)']:
            df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
    except Exception:
        df = pd.DataFrame([["A-B", 1740, 0.28, 73.53, 0.0, 0.0, "400P", 0.0, 0.0522]] * 5, columns=default_columns)
else:
    df = pd.DataFrame([["A-B", 1740, 0.28, 73.53, 0.0, 0.0, "400P", 0.0, 0.0522]] * 5, columns=default_columns)

# 3. 데이터 에디터 (입력 화면)
st.markdown("### 📝 관경산출 데이터 (시뮬레이션)")
st.caption("💡 '세대수 합계'와 '관길이(m)'를 수정해 보세요. (자동 계산 모드가 켜져 있으면 압력손실이 즉시 변합니다.)")

edited_df = st.data_editor(
    df,
    num_rows="dynamic",
    use_container_width=True,
    hide_index=True,
    column_config={
        "세대수 합계": st.column_config.NumberColumn("세대수 합계 (입력)", format="%d"),
        "관길이(m)": st.column_config.NumberColumn("관길이(m) (입력)", format="%.2f"),
        "선정관경": st.column_config.SelectboxColumn("선정관경", options=list(pipe_diameters.keys())),
    }
)

# 4. 엑셀 수식 자동화 로직 (Pole 공식 근사치 적용)
if auto_calc:
    for idx, row in edited_df.iterrows():
        # 1) 유량 자동 계산 = 세대수 * 동시사용률 * 2.868(세대당 유량 상수)
        q_calc = row['세대수 합계'] * row['동시사용률'] * 2.868
        edited_df.at[idx, '유량합계(㎥/hr)'] = q_calc
        
        # 2) 실 압력손실 자동 계산 (가스공학 Pole 공식 적용)
        # H = C * (L * Q^2) / (D^5)
        pipe_type = str(row['선정관경']).strip()
        inner_d = pipe_diameters.get(pipe_type, 32.92) # 기본값 400P 내경
        
        if inner_d > 0:
            # 0.01222는 가스비중(0.624) 및 단위를 맞춘 상수
            p_drop = 0.01222 * (row['관길이(m)'] * (q_calc ** 2)) / (inner_d ** 5)
            edited_df.at[idx, '실_압력손실(kPa)'] = round(p_drop, 4)

# 5. 판정 결과 대시보드
total_actual_drop = edited_df['실_압력손실(kPa)'].sum()
total_allowable_drop = edited_df['허용압력손실(kPa)'].sum() # 총 예산 합계

st.markdown("---")
st.subheader("📊 최종 전환 적합성 판정")

col1, col2, col3 = st.columns([1, 1, 2])
with col1:
    st.metric(label="총 실 압력손실 (지출)", value=f"{total_actual_drop:.4f} kPa")
with col2:
    # 허용압력손실 총합이 0이거나 데이터가 없으면 기준치 0.3kPa로 강제 세팅
    budget = total_allowable_drop if total_allowable_drop > 0 else 0.3000
    st.metric(label="총 허용 압력손실 (예산)", value=f"{budget:.4f} kPa")
with col3:
    if total_actual_drop <= budget and total_actual_drop > 0:
        st.success("✅ **[공사 불필요] 사용 가능**\n\n현재 배관 상태 그대로 도시가스 전환이 가능합니다. (안전 기준 충족)")
    elif total_actual_drop > budget:
        st.error("🚨 **[공사 필요] 관경 확대 요망**\n\n압력 손실이 기준치를 초과하여 기존 배관을 사용할 수 없습니다.")
    else:
        st.info("데이터를 입력해 주세요.")
