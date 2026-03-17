import streamlit as st
import pandas as pd

# 1. 기본 페이지 설정
st.set_page_config(page_title="공동주택 관경 적합성 사전 검토기", layout="wide")

st.title("🏢 공동주택 도시가스 전환 사전 검토기")
st.markdown("엑셀 파일을 업로드하거나 빈칸에 데이터를 직접 입력하여 **총 실 압력손실(0.3kPa 기준)**을 점검하세요.")

# '관경산출식' 기준 표준 컬럼
default_columns = ['구간', '세대수 합계', '동시사용률', '관길이(m)', '유량합계(㎥/hr)', '계산관경', '선정관경', '실_압력손실(kPa)', '허용압력손실(kPa)']

# 2. 파일 업로드 (선택 사항)
with st.sidebar:
    st.header("⚙️ 데이터 불러오기")
    uploaded_file = st.file_uploader("관경산출식 엑셀/CSV 업로드", type=['xlsx', 'xls', 'csv'])
    st.info("파일을 업로드하지 않으면 우측 표에 직접 입력하여 시뮬레이션할 수 있습니다.")

# 데이터프레임 초기화 로직
if uploaded_file:
    try:
        if uploaded_file.name.endswith('csv'):
            df = pd.read_csv(uploaded_file, skiprows=7)
        else:
            xls = pd.ExcelFile(uploaded_file)
            sheet_names = [s for s in xls.sheet_names if '관경산출식' in s]
            if not sheet_names:
                sheet_names = xls.sheet_names
            
            selected_sheet = st.sidebar.selectbox("불러올 시트 선택", sheet_names)
            df = pd.read_excel(uploaded_file, sheet_name=selected_sheet, skiprows=7)

        # 엑셀 양식의 실제 데이터 위치 인덱스 추출 (유량, 선정관경 위치 보정)
        df = df.iloc[:, [1, 9, 10, 11, 13, 14, 16, 17, 18]].copy()
        df.columns = default_columns
        
        # [안전장치 1] 빈칸 행 제거
        df = df.dropna(subset=['구간'])
        
        # [안전장치 2] 실무자가 합계 행을 포함해서 올렸을 경우를 대비해 '계'나 '합'이 들어간 행 자동 필터링
        df = df[~df['구간'].astype(str).str.contains('계|합')]
        
        # 숫자형 변환
        for col in ['세대수 합계', '동시사용률', '관길이(m)', '유량합계(㎥/hr)', '계산관경', '실_압력손실(kPa)', '허용압력손실(kPa)']:
            df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
            
    except Exception as e:
        st.sidebar.error("파일 양식이 맞지 않습니다. 직접 입력 모드로 전환합니다.")
        df = pd.DataFrame([["A-B", 0, 0.0, 0.0, 0.0, 0.0, "", 0.0, 0.0]] * 5, columns=default_columns)
else:
    df = pd.DataFrame([["", 0, 0.0, 0.0, 0.0, 0.0, "400P", 0.0000, 0.0000]] * 5, columns=default_columns)

# 3. 데이터 에디터 (담당자 직접 수정 공간)
st.markdown("### 📝 관경산출 데이터 확인 및 수정")
st.caption("💡 업로드된 엑셀 데이터를 확인하거나 빈칸을 더블클릭하여 수정할 수 있습니다.")

edited_df = st.data_editor(
    df,
    num_rows="dynamic",
    use_container_width=True,
    hide_index=True,
    column_config={
        "구간": st.column_config.TextColumn("구간", required=True),
        "세대수 합계": st.column_config.NumberColumn("세대수 합계", format="%d"),
        "실_압력손실(kPa)": st.column_config.NumberColumn("실_압력손실(kPa)", format="%.4f"),
    }
)

# 4. 실시간 판정 로직
total_pressure_drop = edited_df['실_압력손실(kPa)'].sum()

st.markdown("---")
st.subheader("💡 사전 검토 결과")

col1, col2 = st.columns([1, 2])
with col1:
    st.metric(label="총 실 압력손실 합계", value=f"{total_pressure_drop:.4f} kPa")

with col2:
    if total_pressure_drop == 0:
        st.info("데이터를 입력하시면 판정 결과가 여기에 표시됩니다.")
    elif total_pressure_drop <= 0.3:
        st.success("✅ **공사 불필요 (사용 가능)**\n\n현재 배관 상태로 전환이 가능합니다. (기준치 0.3kPa 이하 만족)")
    else:
        st.error("🚨 **관경 확대 공사 필요**\n\n기존 배관으로 전환 시 압력 손실이 큽니다. (기준치 0.3kPa 초과)")
