import streamlit as st
import pandas as pd

# 1. 기본 페이지 설정
st.set_page_config(page_title="공동주택 관경 적합성 사전 검토기", layout="wide")

st.title("🏢 공동주택 도시가스 전환 사전 검토기")
st.markdown("엑셀 파일을 업로드하여 기존 데이터를 불러오거나, 아래 표의 빈칸에 직접 데이터를 입력하여 **총 실 압력손실(0.3kPa 기준)**을 점검하세요.")

# '관경산출식-509동' 기준 표준 컬럼
default_columns = ['구간', '세대수 합계', '동시사용률', '관길이(m)', '유량합계(㎥/hr)', '계산관경', '선정관경', '실_압력손실(kPa)', '허용압력손실(kPa)']

# 2. 파일 업로드 (선택 사항)
with st.sidebar:
    st.header("⚙️ 데이터 불러오기")
    uploaded_file = st.file_uploader("기존 엑셀 파일이 있다면 업로드하세요.", type=['xlsx', 'xls', 'csv'])
    st.info("파일을 업로드하지 않아도 우측 표에 직접 입력하여 계산할 수 있습니다.")

# 데이터프레임 초기화
if uploaded_file:
    try:
        if uploaded_file.name.endswith('csv'):
            df = pd.read_csv(uploaded_file, skiprows=7)
        else:
            xls = pd.ExcelFile(uploaded_file)
            # 관경산출식 시트 자동 필터링
            sheet_names = [s for s in xls.sheet_names if '관경산출식' in s]
            if not sheet_names:
                sheet_names = xls.sheet_names
            
            selected_sheet = st.sidebar.selectbox("불러올 시트 선택", sheet_names)
            df = pd.read_excel(uploaded_file, sheet_name=selected_sheet, skiprows=7)

        # 509동 엑셀 양식의 실제 데이터 위치 인덱스 추출
        df = df.iloc[:, [1, 9, 10, 11, 12, 14, 15, 17, 18]].copy()
        df.columns = default_columns
        df = df.dropna(subset=['구간'])
        
        # 숫자형 변환
        for col in ['세대수 합계', '동시사용률', '관길이(m)', '유량합계(㎥/hr)', '계산관경', '실_압력손실(kPa)', '허용압력손실(kPa)']:
            df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
            
    except Exception as e:
        st.sidebar.error(f"파일 양식이 맞지 않습니다. 직접 입력 모드로 전환합니다. ({e})")
        df = pd.DataFrame([["A-B", 0, 0.0, 0.0, 0.0, 0.0, "", 0.0, 0.0]] * 5, columns=default_columns)
else:
    # 파일을 안 올렸을 때 제공되는 기본 입력 폼 (5줄 빈칸)
    df = pd.DataFrame([["", 0, 0.0, 0.0, 0.0, 0.0, "400P", 0.0000, 0.0000]] * 5, columns=default_columns)

# 3. 데이터 에디터 (담당자 직접 입력 공간)
st.markdown("### 📝 관경산출 데이터 입력 및 수정")
st.caption("💡 표의 빈칸을 더블클릭하여 값을 직접 수정하거나, 맨 아래를 클릭해 새로운 행을 추가할 수 있습니다.")

# st.data_editor를 통해 엑셀처럼 자유로운 수정, 행 추가/삭제 지원
edited_df = st.data_editor(
    df,
    num_rows="dynamic",  # 행 추가/삭제 기능 활성화
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

# 메트릭 디자인으로 직관적인 결과 표시
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
