import streamlit as st
import pandas as pd

# 페이지 설정
st.set_page_config(page_title="도시가스 관경 적합성 판단", layout="wide")

st.title("🏢 공동주택 도시가스 전환 적합성 판단기")
st.markdown("기존 배관의 **총 실 압력손실이 0.3kPa 이하**인지 사전에 빠르게 점검하여 공사 필요 여부를 결정하는 도구입니다.")

# 1. 파일 업로드 섹션
uploaded_file = st.file_uploader("관경산출식 엑셀(xls/xlsx) 또는 CSV 파일을 업로드하세요.", type=['csv', 'xlsx', 'xls'])

if uploaded_file is not None:
    try:
        # 엑셀/CSV 읽기 (관경산출식 509동 기준 헤더 스킵)
        if uploaded_file.name.endswith('csv'):
            df = pd.read_csv(uploaded_file, skiprows=7)
        else:
            df = pd.read_excel(uploaded_file, skiprows=7)
        
        # 필요한 컬럼만 추출 (실제 엑셀 양식에 맞춰 유연하게 대처)
        df_clean = df.iloc[:, [1, 9, 10, 11, 12, 14, 15, 17, 18]].copy()
        df_clean.columns = ['구간', '세대수 합계', '동시사용률', '관길이(m)', '유량합계(㎥/hr)', '계산관경', '선정관경', '실_압력손실(kPa)', '허용압력손실(kPa)']
        df_clean = df_clean.dropna(subset=['구간'])
        
        # 숫자형 데이터로 변환
        for col in ['세대수 합계', '동시사용률', '관길이(m)', '유량합계(㎥/hr)', '계산관경', '실_압력손실(kPa)', '허용압력손실(kPa)']:
            df_clean[col] = pd.to_numeric(df_clean[col], errors='coerce').fillna(0)
        
        # 총 압력손실 계산
        total_pressure_drop = df_clean['실_압력손실(kPa)'].sum()
        
        # 2. 최상단 결과 표기 (0.3kPa 기준)
        st.subheader("💡 적합성 판정 결과")
        if total_pressure_drop <= 0.3:
            st.success(f"✅ **사용 가능** (현재 배관 유지 가능)\n\n총 실 압력손실: **{total_pressure_drop:.4f} kPa** (기준치 0.3 kPa 이하)")
        else:
            st.error(f"🚨 **관경 확대 공사 필요** (배관 교체 요망)\n\n총 실 압력손실: **{total_pressure_drop:.4f} kPa** (기준치 0.3 kPa 초과)")

        st.divider()

        # 3. 세부 데이터 확인 (천 단위 콤마 및 중간 정렬 적용)
        st.markdown("### 📊 구간별 세부 데이터")
        
        # Streamlit st.dataframe의 column_config를 활용한 서식 및 정렬 제어
        st.dataframe(
            df_clean,
            use_container_width=True,
            hide_index=True,
            column_config={
                "구간": st.column_config.TextColumn("구간", width="small"),
                "세대수 합계": st.column_config.NumberColumn("세대수 합계", format="%d 세대"),
                "동시사용률": st.column_config.NumberColumn("동시사용률", format="%.2f"),
                "관길이(m)": st.column_config.NumberColumn("관길이(m)", format="%,.2f m"),
                "유량합계(㎥/hr)": st.column_config.NumberColumn("유량합계(㎥/hr)", format="%,.2f"),
                "계산관경": st.column_config.NumberColumn("계산관경", format="%.2f"),
                "선정관경": st.column_config.TextColumn("선정관경"),
                "실_압력손실(kPa)": st.column_config.NumberColumn("실_압력손실(kPa)", format="%.4f"),
                "허용압력손실(kPa)": st.column_config.NumberColumn("허용압력손실(kPa)", format="%.4f"),
            }
        )

    except Exception as e:
        st.error(f"파일을 읽는 중 오류가 발생했습니다. 파일 양식을 확인해주세요.\n\n에러 내용: {e}")

else:
    st.info("파일을 업로드하면 자동으로 판정 결과가 상단에 표시됩니다.")
