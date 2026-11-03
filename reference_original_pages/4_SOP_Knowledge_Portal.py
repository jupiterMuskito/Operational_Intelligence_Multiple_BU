import streamlit as st

from src.portal.data_store import (
    EQUIPMENT_FILE,
    GUIDE_FILE,
    LESSONS_FILE,
    ROOT,
    SOP_FILE,
    load_csv,
)

# --------------------------------------------------
# PAGE CONFIG
# --------------------------------------------------

st.set_page_config(
    page_title="SOP & Knowledge Portal",
    page_icon="📚",
    layout="wide"
)

# --------------------------------------------------
# HELPERS
# --------------------------------------------------

def keyword_filter(df, keyword):

    if not keyword:
        return df

    mask = df.astype(str).apply(
        lambda col: col.str.contains(
            keyword,
            case=False,
            na=False,
            regex=False
        )
    ).any(axis=1)

    return df[mask]


# --------------------------------------------------
# LOAD DATA
# --------------------------------------------------

equipment_df = load_csv(EQUIPMENT_FILE)

sop_df = load_csv(SOP_FILE)

guide_df = load_csv(GUIDE_FILE)

lessons_df = load_csv(LESSONS_FILE)

# --------------------------------------------------
# HEADER
# --------------------------------------------------

st.title("📚 SOP & Knowledge Portal")

st.caption(
    """
Centralized operational knowledge platform for:

• SOPs

• Equipment Knowledge

• Troubleshooting

• Lessons Learned

• Operator Familiarization

• Knowledge Retention
"""
)

st.warning(
    "Sample content: SOP titles, statuses, troubleshooting entries and lessons learned "
    "are illustrative until the approved unit documents are added."
)

st.divider()

# --------------------------------------------------
# GLOBAL KNOWLEDGE SEARCH
# --------------------------------------------------

st.subheader("🔎 Knowledge Search")

search_term = st.text_input(
    "Search Equipment, Tags, SOPs, Procedures, Issues..."
)

if search_term:

    st.markdown("### Equipment References")

    equipment_results = keyword_filter(
        equipment_df,
        search_term
    )

    st.dataframe(
        equipment_results,
        width="stretch",
        hide_index=True
    )

    st.markdown("### SOP Library")

    sop_results = keyword_filter(
        sop_df,
        search_term
    )

    st.dataframe(
        sop_results,
        width="stretch",
        hide_index=True
    )

    st.markdown("### Troubleshooting Guide")

    guide_results = keyword_filter(
        guide_df,
        search_term
    )

    st.dataframe(
        guide_results,
        width="stretch",
        hide_index=True
    )

    st.markdown("### Lessons Learned")

    lesson_results = keyword_filter(
        lessons_df,
        search_term
    )

    st.dataframe(
        lesson_results,
        width="stretch",
        hide_index=True
    )

st.divider()

# --------------------------------------------------
# EQUIPMENT KNOWLEDGE CENTRE
# --------------------------------------------------

st.subheader("🏭 Equipment Knowledge Centre")

col1, col2 = st.columns(2)

with col1:

    section_filter = st.selectbox(
        "Section",
        ["All"] +
        sorted(
            equipment_df["section"]
            .dropna()
            .unique()
        )
        if not equipment_df.empty
        else ["All"]
    )

with col2:

    equipment_filter = st.selectbox(
        "Equipment",
        ["All"] +
        sorted(
            equipment_df["equipment"]
            .dropna()
            .unique()
        )
        if not equipment_df.empty
        else ["All"]
    )

filtered_equipment = equipment_df.copy()

if section_filter != "All":

    filtered_equipment = filtered_equipment[
        filtered_equipment["section"]
        == section_filter
    ]

if equipment_filter != "All":

    filtered_equipment = filtered_equipment[
        filtered_equipment["equipment"]
        == equipment_filter
    ]

st.dataframe(
    filtered_equipment,
    width="stretch",
    hide_index=True
)

st.divider()

# --------------------------------------------------
# SOP LIBRARY
# --------------------------------------------------

st.subheader("📘 SOP Library")

col1, col2 = st.columns(2)

with col1:

    sop_category = st.selectbox(
        "Category Filter",
        ["All"] +
        sorted(
            sop_df["category"]
            .dropna()
            .unique()
        )
        if not sop_df.empty
        else ["All"]
    )

with col2:

    sop_search = st.text_input(
        "Search SOP"
    )

filtered_sop = sop_df.copy()

if sop_category != "All":

    filtered_sop = filtered_sop[
        filtered_sop["category"]
        == sop_category
    ]

filtered_sop = keyword_filter(
    filtered_sop,
    sop_search
)

st.dataframe(
    filtered_sop.drop(columns=["document_path"]),
    width="stretch",
    hide_index=True
)

documents = filtered_sop[
    filtered_sop["document_path"].notna()
]

for _, sop in documents.iterrows():

    document = ROOT / sop["document_path"]

    if document.exists():

        st.download_button(
            f"Open {sop['sop_id']} - {sop['title']}",
            document.read_bytes(),
            file_name=document.name
        )

if documents.empty:
    st.caption(
        "Documents appear here once a file path is added to the document_path "
        "column of data/sample/sop_library.csv."
    )

st.divider()

# --------------------------------------------------
# TROUBLESHOOTING GUIDE
# --------------------------------------------------

st.subheader("🛠 Troubleshooting Guide")

guide_search = st.text_input(
    "Search Issue or Symptom"
)

filtered_guide = keyword_filter(
    guide_df,
    guide_search
)

st.dataframe(
    filtered_guide,
    width="stretch",
    hide_index=True
)

if not filtered_guide.empty:

    issue = st.selectbox(
        "Select Troubleshooting Topic",
        filtered_guide["issue"]
    )

    selected_issue = filtered_guide[
        filtered_guide["issue"] == issue
    ].iloc[0]

    st.markdown(
        f"""
### Symptoms

{selected_issue['symptoms']}

### Possible Causes

{selected_issue['possible_causes']}

### Recommended Actions

{selected_issue['recommended_actions']}
"""
    )

st.divider()

# --------------------------------------------------
# LESSONS LEARNED
# --------------------------------------------------

st.subheader("🧠 Lessons Learned")

col1, col2 = st.columns(2)

with col1:

    lesson_area = st.selectbox(
        "Area",
        ["All"] +
        sorted(
            lessons_df["area"]
            .dropna()
            .unique()
        )
        if not lessons_df.empty
        else ["All"]
    )

with col2:

    lesson_search = st.text_input(
        "Search Lessons Learned"
    )

filtered_lessons = lessons_df.copy()

if lesson_area != "All":

    filtered_lessons = filtered_lessons[
        filtered_lessons["area"]
        == lesson_area
    ]

filtered_lessons = keyword_filter(
    filtered_lessons,
    lesson_search
)

st.dataframe(
    filtered_lessons,
    width="stretch",
    hide_index=True
)

if not filtered_lessons.empty:

    selected_lesson = st.selectbox(
        "Select Lesson",
        filtered_lessons["title"]
    )

    lesson = filtered_lessons[
        filtered_lessons["title"]
        == selected_lesson
    ].iloc[0]

    st.markdown(
        f"""
### Observation

{lesson['observation']}

### Resolution

{lesson['resolution']}

### Recommendation

{lesson['recommendation']}
"""
    )

st.divider()

# --------------------------------------------------
# TRAINING & KNOWLEDGE VALUE
# --------------------------------------------------

st.subheader("🎓 Training & Knowledge Benefits")

left, right = st.columns(2)

with left:

    st.success(
        """
✓ Faster Troubleshooting

✓ Improved Equipment Familiarity

✓ Improved Tag Familiarity

✓ Better Shift Handover Quality

✓ Reduced Dependence on Individuals

✓ Knowledge Retention
"""
    )

with right:

    st.success(
        """
✓ Faster Operator Development

✓ Improved Operational Consistency

✓ Centralized Knowledge Repository

✓ Better Decision Making

✓ Reduced Repeated Errors

✓ Improved Operational Readiness
"""
    )

st.divider()

# --------------------------------------------------
# OPERATIONS EXCELLENCE
# --------------------------------------------------

st.subheader("🚀 Operations Excellence Journey")

st.markdown(
    """
### Monitor

Page 1 – Unit Overview

### Analyze

Page 2 – Feed → Process → Product Analytics

### Verify

Page 3 – Digital Operator Rounds & Verification

### Learn

Page 4 – SOP & Knowledge Portal

### Improve

Future Optimization & Operations Intelligence
"""
)

st.divider()

with st.expander("About This Page"):

    st.markdown(
        """
This Knowledge Portal demonstrates how the platform can become a
central repository for operational knowledge.

It combines:

• SOP Management

• Equipment Knowledge

• Troubleshooting Support

• Lessons Learned

• Operator Familiarization

• Knowledge Retention

into a single searchable platform.
"""
    )