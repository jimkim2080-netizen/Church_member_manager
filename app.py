# -*- coding: utf-8 -*-
"""
가나한인교회 교인관리 Streamlit Web App
Korean Community Church of Ghana - Member Management Web App

실행:
    streamlit run app.py

requirements.txt:
    streamlit
    pandas
    pillow
    openpyxl

주의:
- Streamlit Community Cloud에서 SQLite DB와 업로드 사진은 간단 테스트용으로 사용 가능합니다.
- 장기 운영/여러 사람이 동시에 사용하는 경우 Supabase, Google Sheets, Firebase 같은 외부 DB 연결을 권장합니다.
"""

import os
import sqlite3
from datetime import date, datetime
from pathlib import Path

import pandas as pd
import streamlit as st
from PIL import Image


APP_TITLE = "가나한인교회 교인관리"
DB_FILE = "church_members_web.db"
PHOTO_DIR = Path("member_photos")


st.set_page_config(
    page_title=APP_TITLE,
    page_icon="✝️",
    layout="wide",
    initial_sidebar_state="expanded"
)


CUSTOM_CSS = """
<style>
    .main {
        background-color: #F7F4EF;
    }
    .block-container {
        padding-top: 1.5rem;
        padding-bottom: 2rem;
    }
    .title-box {
        background: linear-gradient(90deg, #DCEEFF, #E5F4E3, #FFF4CC);
        padding: 22px;
        border-radius: 20px;
        border: 1px solid #E4E4E4;
        margin-bottom: 18px;
    }
    .title-box h1 {
        margin: 0;
        color: #2D3748;
        font-size: 34px;
    }
    .title-box p {
        color: #4A5568;
        font-size: 17px;
        margin-top: 6px;
    }
    .metric-card {
        background-color: white;
        padding: 20px;
        border-radius: 18px;
        border: 1px solid #E6E6E6;
        box-shadow: 0 2px 8px rgba(0,0,0,0.04);
        text-align: center;
    }
    .small-note {
        color: #667085;
        font-size: 14px;
    }
    .stTabs [data-baseweb="tab-list"] {
        gap: 8px;
    }
    .stTabs [data-baseweb="tab"] {
        background-color: #FFFFFF;
        border-radius: 14px 14px 0 0;
        padding: 12px 18px;
        font-weight: 700;
    }
</style>
"""
st.markdown(CUSTOM_CSS, unsafe_allow_html=True)


def today_str():
    return date.today().strftime("%Y-%m-%d")


def now_stamp():
    return datetime.now().strftime("%Y%m%d_%H%M%S")


def init_db():
    PHOTO_DIR.mkdir(exist_ok=True)
    conn = sqlite3.connect(DB_FILE)
    cur = conn.cursor()

    cur.execute("""
        CREATE TABLE IF NOT EXISTS members (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT,
            position TEXT,
            gender TEXT,
            department TEXT,
            birth_date TEXT,
            age TEXT,
            address TEXT,
            mobile TEXT,
            job TEXT,
            register_date TEXT,
            guide TEXT,
            baptism TEXT,
            family TEXT,
            notes TEXT,
            prayer_topics TEXT,
            photo_path TEXT,
            created_at TEXT,
            updated_at TEXT
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS visits (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            member_id INTEGER,
            visit_date TEXT,
            hymn TEXT,
            scripture TEXT,
            visitors TEXT,
            prayer_topic TEXT,
            remarks TEXT,
            created_at TEXT,
            FOREIGN KEY(member_id) REFERENCES members(id)
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS education (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            member_id INTEGER,
            course TEXT,
            completion_date TEXT,
            teacher TEXT,
            remarks TEXT,
            created_at TEXT,
            FOREIGN KEY(member_id) REFERENCES members(id)
        )
    """)

    conn.commit()
    conn.close()


def get_conn():
    return sqlite3.connect(DB_FILE, check_same_thread=False)


def read_df(query, params=()):
    conn = get_conn()
    df = pd.read_sql_query(query, conn, params=params)
    conn.close()
    return df


def execute(query, params=()):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(query, params)
    conn.commit()
    last_id = cur.lastrowid
    conn.close()
    return last_id


def execute_many(query, values):
    conn = get_conn()
    cur = conn.cursor()
    cur.executemany(query, values)
    conn.commit()
    conn.close()


def parse_date_string(value, default_today=True):
    if not value:
        return date.today() if default_today else None
    try:
        return datetime.strptime(str(value)[:10], "%Y-%m-%d").date()
    except Exception:
        return date.today() if default_today else None


def save_uploaded_photo(uploaded_file, member_name):
    if not uploaded_file:
        return ""
    ext = Path(uploaded_file.name).suffix.lower() or ".jpg"
    safe_name = "".join(ch for ch in member_name if ch.isalnum() or ch in ("_", "-")) or "member"
    filename = f"{safe_name}_{now_stamp()}{ext}"
    path = PHOTO_DIR / filename
    path.write_bytes(uploaded_file.getbuffer())
    return str(path)


def get_members_df(keyword=""):
    if keyword:
        like = f"%{keyword}%"
        return read_df("""
            SELECT * FROM members
            WHERE name LIKE ? OR mobile LIKE ? OR department LIKE ? OR address LIKE ?
            ORDER BY name
        """, (like, like, like, like))
    return read_df("SELECT * FROM members ORDER BY name")


def get_member(member_id):
    df = read_df("SELECT * FROM members WHERE id=?", (member_id,))
    if df.empty:
        return None
    return df.iloc[0].to_dict()


def member_select_box(members_df, label="교인 선택"):
    if members_df.empty:
        st.info("아직 등록된 교인이 없습니다.")
        return None

    options = {
        f"{row['name']} / {row.get('mobile','')} / {row.get('department','')}": int(row["id"])
        for _, row in members_df.iterrows()
    }
    selected_label = st.selectbox(label, list(options.keys()))
    return options[selected_label]


def delete_member(member_id):
    execute("DELETE FROM visits WHERE member_id=?", (member_id,))
    execute("DELETE FROM education WHERE member_id=?", (member_id,))
    execute("DELETE FROM members WHERE id=?", (member_id,))


def render_header():
    st.markdown(
        """
        <div class="title-box">
            <h1>✝ 가나한인교회 교인관리</h1>
            <p>교인등록 · 심방사항 · 교육사항 · 모바일 Web App</p>
        </div>
        """,
        unsafe_allow_html=True
    )


def render_dashboard():
    members = read_df("SELECT * FROM members")
    visits = read_df("SELECT * FROM visits")
    edu = read_df("SELECT * FROM education")

    this_month = date.today().strftime("%m")
    birthday_count = 0
    birthday_df = pd.DataFrame()

    if not members.empty and "birth_date" in members.columns:
        birthday_df = members[members["birth_date"].fillna("").str[5:7] == this_month]
        birthday_count = len(birthday_df)

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("전체 교인", len(members))
    c2.metric("심방 기록", len(visits))
    c3.metric("교육 기록", len(edu))
    c4.metric("이번달 생일", birthday_count)

    col1, col2 = st.columns(2)

    with col1:
        st.subheader("🎂 이번달 생일자")
        if birthday_df.empty:
            st.caption("이번달 생일자가 없습니다.")
        else:
            st.dataframe(
                birthday_df[["name", "birth_date", "mobile", "department"]].rename(
                    columns={"name": "성명", "birth_date": "생년월일", "mobile": "연락처", "department": "부서"}
                ),
                use_container_width=True,
                hide_index=True
            )

    with col2:
        st.subheader("🏠 최근 심방 기록")
        recent = read_df("""
            SELECT v.visit_date, m.name, v.visitors, v.scripture
            FROM visits v
            JOIN members m ON v.member_id = m.id
            ORDER BY v.visit_date DESC, v.id DESC
            LIMIT 10
        """)
        if recent.empty:
            st.caption("심방 기록이 없습니다.")
        else:
            st.dataframe(
                recent.rename(columns={"visit_date": "날짜", "name": "성명", "visitors": "심방자", "scripture": "말씀"}),
                use_container_width=True,
                hide_index=True
            )


def render_member_registration():
    st.subheader("👤 교인등록카드")

    members_df = get_members_df()
    mode = st.radio("작업 선택", ["새 교인 등록", "기존 교인 수정"], horizontal=True)

    selected_member = None
    selected_id = None

    if mode == "기존 교인 수정":
        selected_id = member_select_box(members_df)
        if selected_id:
            selected_member = get_member(selected_id)

    def default(key, fallback=""):
        if selected_member:
            return selected_member.get(key) or fallback
        return fallback

    with st.form("member_form", clear_on_submit=False):
        col1, col2, col3 = st.columns([2, 2, 1.2])

        with col1:
            name = st.text_input("성명 *", value=default("name"))
            position = st.text_input("직분", value=default("position"))
            gender = st.selectbox(
                "성별",
                ["", "남", "여"],
                index=["", "남", "여"].index(default("gender")) if default("gender") in ["", "남", "여"] else 0
            )
            department = st.text_input("부서/소속", value=default("department"))
            birth_date = st.date_input("생년월일", value=parse_date_string(default("birth_date"), default_today=False))
            age = st.text_input("나이", value=default("age"))

        with col2:
            mobile = st.text_input("휴대폰", value=default("mobile"))
            job = st.text_input("직업/직장", value=default("job"))
            register_date = st.date_input("작성일/등록일", value=parse_date_string(default("register_date")))
            guide = st.text_input("인도자", value=default("guide"))
            baptism = st.text_input("세례/입교", value=default("baptism"))
            address = st.text_area("주소", value=default("address"), height=100)

        with col3:
            st.write("증명사진")
            current_photo = default("photo_path")
            if current_photo and os.path.exists(current_photo):
                st.image(current_photo, width=160)
            photo = st.file_uploader("사진 선택", type=["jpg", "jpeg", "png"], label_visibility="collapsed")
            st.caption("모바일에서도 사진 업로드 가능")

        family = st.text_area("동반 등록가족", value=default("family"), height=100)
        notes = st.text_area("심방사항", value=default("notes"), height=100)
        prayer_topics = st.text_area("기도제목", value=default("prayer_topics"), height=100)

        submitted = st.form_submit_button("💾 저장 / 수정", use_container_width=True)

    if submitted:
        if not name.strip():
            st.error("성명을 입력해 주세요.")
            return

        photo_path = default("photo_path")
        if photo:
            photo_path = save_uploaded_photo(photo, name)

        birth_str = birth_date.strftime("%Y-%m-%d") if birth_date else ""
        reg_str = register_date.strftime("%Y-%m-%d") if register_date else today_str()

        if mode == "새 교인 등록":
            execute("""
                INSERT INTO members
                (name, position, gender, department, birth_date, age, address, mobile, job,
                 register_date, guide, baptism, family, notes, prayer_topics, photo_path, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                name, position, gender, department, birth_str, age, address, mobile, job,
                reg_str, guide, baptism, family, notes, prayer_topics, photo_path, today_str(), today_str()
            ))
            st.success("새 교인이 등록되었습니다.")
            st.rerun()
        else:
            execute("""
                UPDATE members SET
                name=?, position=?, gender=?, department=?, birth_date=?, age=?, address=?,
                mobile=?, job=?, register_date=?, guide=?, baptism=?, family=?, notes=?,
                prayer_topics=?, photo_path=?, updated_at=?
                WHERE id=?
            """, (
                name, position, gender, department, birth_str, age, address, mobile, job,
                reg_str, guide, baptism, family, notes, prayer_topics, photo_path, today_str(), selected_id
            ))
            st.success("교인 정보가 수정되었습니다.")
            st.rerun()

    if mode == "기존 교인 수정" and selected_id:
        st.divider()
        if st.button("🗑️ 선택 교인 삭제", type="secondary"):
            delete_member(selected_id)
            st.success("삭제되었습니다.")
            st.rerun()


def render_visit_management():
    st.subheader("🏠 심방사항")
    members_df = get_members_df()
    member_id = member_select_box(members_df)
    if not member_id:
        return

    member = get_member(member_id)
    st.info(f"선택 교인: {member['name']}")

    with st.form("visit_form", clear_on_submit=True):
        col1, col2, col3, col4 = st.columns(4)
        visit_date = col1.date_input("날짜", value=date.today())
        hymn = col2.text_input("찬송")
        scripture = col3.text_input("말씀")
        visitors = col4.text_input("심방자")
        prayer_topic = st.text_area("기도제목", height=90)
        remarks = st.text_area("비고", height=90)
        submitted = st.form_submit_button("➕ 심방 기록 추가", use_container_width=True)

    if submitted:
        execute("""
            INSERT INTO visits
            (member_id, visit_date, hymn, scripture, visitors, prayer_topic, remarks, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            member_id, visit_date.strftime("%Y-%m-%d"), hymn, scripture, visitors,
            prayer_topic, remarks, today_str()
        ))
        st.success("심방 기록이 추가되었습니다.")
        st.rerun()

    st.subheader("누적 심방 기록")
    visits = read_df("SELECT * FROM visits WHERE member_id=? ORDER BY visit_date DESC, id DESC", (member_id,))
    if visits.empty:
        st.caption("등록된 심방 기록이 없습니다.")
    else:
        st.dataframe(
            visits[["id", "visit_date", "hymn", "scripture", "visitors", "prayer_topic", "remarks"]].rename(
                columns={
                    "id": "번호", "visit_date": "날짜", "hymn": "찬송", "scripture": "말씀",
                    "visitors": "심방자", "prayer_topic": "기도제목", "remarks": "비고"
                }
            ),
            use_container_width=True,
            hide_index=True
        )
        delete_id = st.number_input("삭제할 심방 기록 번호", min_value=0, step=1)
        if st.button("선택 심방 기록 삭제"):
            if delete_id > 0:
                execute("DELETE FROM visits WHERE id=? AND member_id=?", (int(delete_id), member_id))
                st.success("삭제되었습니다.")
                st.rerun()


def render_education_management():
    st.subheader("📚 교육사항")
    members_df = get_members_df()
    member_id = member_select_box(members_df)
    if not member_id:
        return

    member = get_member(member_id)
    st.info(f"선택 교인: {member['name']}")

    with st.form("education_form", clear_on_submit=True):
        col1, col2, col3 = st.columns(3)
        course = col1.text_input("교육과목")
        completion_date = col2.date_input("수료일자", value=date.today())
        teacher = col3.text_input("강사")
        remarks = st.text_area("비고", height=100)
        submitted = st.form_submit_button("➕ 교육 기록 추가", use_container_width=True)

    if submitted:
        execute("""
            INSERT INTO education
            (member_id, course, completion_date, teacher, remarks, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (
            member_id, course, completion_date.strftime("%Y-%m-%d"),
            teacher, remarks, today_str()
        ))
        st.success("교육 기록이 추가되었습니다.")
        st.rerun()

    st.subheader("누적 교육 기록")
    edu = read_df("SELECT * FROM education WHERE member_id=? ORDER BY completion_date DESC, id DESC", (member_id,))
    if edu.empty:
        st.caption("등록된 교육 기록이 없습니다.")
    else:
        st.dataframe(
            edu[["id", "course", "completion_date", "teacher", "remarks"]].rename(
                columns={"id": "번호", "course": "교육과목", "completion_date": "수료일자", "teacher": "강사", "remarks": "비고"}
            ),
            use_container_width=True,
            hide_index=True
        )
        delete_id = st.number_input("삭제할 교육 기록 번호", min_value=0, step=1)
        if st.button("선택 교육 기록 삭제"):
            if delete_id > 0:
                execute("DELETE FROM education WHERE id=? AND member_id=?", (int(delete_id), member_id))
                st.success("삭제되었습니다.")
                st.rerun()


def to_excel_bytes(sheets):
    from io import BytesIO
    output = BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        for sheet_name, df in sheets.items():
            df.to_excel(writer, sheet_name=sheet_name, index=False)
    return output.getvalue()


def render_reports():
    st.subheader("📊 보고서 / Excel")

    members = read_df("SELECT * FROM members ORDER BY name")
    visits = read_df("""
        SELECT v.id, m.name, v.visit_date, v.hymn, v.scripture, v.visitors, v.prayer_topic, v.remarks
        FROM visits v
        JOIN members m ON v.member_id = m.id
        ORDER BY v.visit_date DESC, v.id DESC
    """)
    edu = read_df("""
        SELECT e.id, m.name, e.course, e.completion_date, e.teacher, e.remarks
        FROM education e
        JOIN members m ON e.member_id = m.id
        ORDER BY e.completion_date DESC, e.id DESC
    """)

    tab1, tab2, tab3, tab4 = st.tabs(["전체 교인명단", "심방현황", "교육현황", "백업/다운로드"])

    with tab1:
        if members.empty:
            st.caption("등록된 교인이 없습니다.")
        else:
            display_cols = ["id", "name", "position", "gender", "department", "birth_date", "mobile", "register_date", "guide", "baptism", "address"]
            st.dataframe(
                members[display_cols].rename(columns={
                    "id": "번호", "name": "성명", "position": "직분", "gender": "성별",
                    "department": "부서", "birth_date": "생년월일", "mobile": "연락처",
                    "register_date": "등록일", "guide": "인도자", "baptism": "세례/입교", "address": "주소"
                }),
                use_container_width=True,
                hide_index=True
            )

    with tab2:
        if visits.empty:
            st.caption("심방 기록이 없습니다.")
        else:
            st.dataframe(
                visits.rename(columns={
                    "id": "번호", "name": "성명", "visit_date": "날짜", "hymn": "찬송",
                    "scripture": "말씀", "visitors": "심방자", "prayer_topic": "기도제목", "remarks": "비고"
                }),
                use_container_width=True,
                hide_index=True
            )

    with tab3:
        if edu.empty:
            st.caption("교육 기록이 없습니다.")
        else:
            st.dataframe(
                edu.rename(columns={
                    "id": "번호", "name": "성명", "course": "교육과목",
                    "completion_date": "수료일자", "teacher": "강사", "remarks": "비고"
                }),
                use_container_width=True,
                hide_index=True
            )

    with tab4:
        excel_data = to_excel_bytes({
            "교인명단": members,
            "심방기록": visits,
            "교육기록": edu
        })
        st.download_button(
            "📥 전체 자료 Excel 다운로드",
            data=excel_data,
            file_name=f"church_members_backup_{now_stamp()}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True
        )

        if os.path.exists(DB_FILE):
            with open(DB_FILE, "rb") as f:
                st.download_button(
                    "📥 SQLite DB 다운로드",
                    data=f.read(),
                    file_name=f"church_members_web_{now_stamp()}.db",
                    mime="application/octet-stream",
                    use_container_width=True
                )

        st.warning("Streamlit Cloud에서 SQLite DB는 장기 보관용으로는 안전하지 않을 수 있습니다. 정기적으로 Excel 또는 DB 다운로드 백업을 권장합니다.")


def render_search():
    st.subheader("🔎 교인 검색")
    keyword = st.text_input("성명, 연락처, 부서, 주소 검색")
    members = get_members_df(keyword)
    if members.empty:
        st.caption("검색 결과가 없습니다.")
        return

    for _, row in members.iterrows():
        with st.expander(f"{row['name']} / {row.get('mobile','')} / {row.get('department','')}"):
            col1, col2 = st.columns([1, 3])
            with col1:
                photo_path = row.get("photo_path", "")
                if photo_path and os.path.exists(photo_path):
                    st.image(photo_path, width=140)
                else:
                    st.caption("사진 없음")
            with col2:
                st.write(f"**직분:** {row.get('position','')}")
                st.write(f"**생년월일:** {row.get('birth_date','')}")
                st.write(f"**주소:** {row.get('address','')}")
                st.write(f"**기도제목:** {row.get('prayer_topics','')}")

            visits = read_df("SELECT visit_date, scripture, visitors, prayer_topic FROM visits WHERE member_id=? ORDER BY visit_date DESC LIMIT 5", (int(row["id"]),))
            if not visits.empty:
                st.write("최근 심방")
                st.dataframe(visits.rename(columns={
                    "visit_date": "날짜", "scripture": "말씀", "visitors": "심방자", "prayer_topic": "기도제목"
                }), hide_index=True, use_container_width=True)


def main():
    init_db()
    render_header()

    with st.sidebar:
        st.image("https://img.icons8.com/fluency/96/church.png", width=70)
        st.title("메뉴")
        menu = st.radio(
            "이동",
            ["홈 / 현황", "교인등록", "심방사항", "교육사항", "교인검색", "보고서"],
            label_visibility="collapsed"
        )
        st.divider()
        st.caption("Korean Community Church of Ghana")
        st.caption("Mobile-friendly Streamlit App")

    if menu == "홈 / 현황":
        render_dashboard()
    elif menu == "교인등록":
        render_member_registration()
    elif menu == "심방사항":
        render_visit_management()
    elif menu == "교육사항":
        render_education_management()
    elif menu == "교인검색":
        render_search()
    elif menu == "보고서":
        render_reports()


if __name__ == "__main__":
    main()
