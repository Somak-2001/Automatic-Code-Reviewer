from __future__ import annotations

import time
from collections import Counter

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st


st.set_page_config(
    page_title="CodeReview AI",
    page_icon="🧠",
    layout="wide",
    initial_sidebar_state="expanded",
)


MODELS = ["GPT-4", "Claude", "Gemini", "Llama"]
SEVERITY_COLORS = {
    "critical": "#ff5c7c",
    "warning": "#f6c85f",
    "info": "#4ecdc4",
    "good": "#37d67a",
}


def inject_styles() -> None:
    st.markdown(
        """
        <style>
        @import url('https://fonts.googleapis.com/css2?family=Manrope:wght@400;500;600;700;800&display=swap');

        html, body, [class*="css"] {
            font-family: 'Manrope', sans-serif;
        }

        .stApp {
            background:
                radial-gradient(circle at top left, rgba(0, 196, 140, 0.12), transparent 26%),
                radial-gradient(circle at top right, rgba(255, 92, 124, 0.12), transparent 24%),
                linear-gradient(180deg, #08111f 0%, #0d1726 44%, #111c2d 100%);
            color: #ebf1ff;
        }

        section[data-testid="stSidebar"] {
            background: linear-gradient(180deg, rgba(12, 19, 33, 0.96) 0%, rgba(9, 15, 27, 0.98) 100%);
            border-right: 1px solid rgba(151, 170, 210, 0.15);
        }

        .block-container {
            padding-top: 1.5rem;
            padding-bottom: 2rem;
            max-width: 1500px;
        }

        div[data-testid="stVerticalBlock"] div:has(> .glass-card) {
            width: 100%;
        }

        .hero {
            padding: 1.6rem 1.8rem;
            border-radius: 24px;
            background: linear-gradient(135deg, rgba(16, 27, 46, 0.94), rgba(14, 54, 68, 0.86));
            border: 1px solid rgba(151, 170, 210, 0.16);
            box-shadow: 0 30px 60px rgba(0, 0, 0, 0.22);
            margin-bottom: 1rem;
        }

        .hero-title {
            font-size: 2.2rem;
            font-weight: 800;
            letter-spacing: -0.04em;
            margin: 0;
            color: #f7fbff;
            text-shadow: 0 6px 24px rgba(0, 0, 0, 0.35);
        }

        .hero-subtitle {
            color: #99abc9;
            font-size: 1rem;
            margin-top: 0.45rem;
            margin-bottom: 0;
        }

        .glass-card {
            background: linear-gradient(180deg, rgba(16, 24, 39, 0.9), rgba(11, 17, 28, 0.96));
            border: 1px solid rgba(151, 170, 210, 0.14);
            border-radius: 22px;
            padding: 1.1rem 1.2rem;
            box-shadow: 0 18px 40px rgba(0, 0, 0, 0.16);
        }

        .section-title {
            font-size: 1rem;
            font-weight: 700;
            margin-bottom: 0.9rem;
            color: #f4f7ff;
        }

        .stat-card {
            background: linear-gradient(180deg, rgba(18, 29, 48, 0.95), rgba(10, 18, 30, 0.98));
            border: 1px solid rgba(151, 170, 210, 0.12);
            border-radius: 22px;
            padding: 1.1rem 1.2rem;
            min-height: 168px;
        }

        .stat-label {
            color: #8ea4c7;
            font-size: 0.92rem;
            margin-bottom: 0.7rem;
        }

        .stat-value {
            font-size: 2.2rem;
            font-weight: 800;
            line-height: 1;
            margin-bottom: 0.45rem;
        }

        .stat-foot {
            color: #9eb2d0;
            font-size: 0.92rem;
        }

        .pill-row {
            display: flex;
            flex-wrap: wrap;
            gap: 0.55rem;
            margin-top: 0.6rem;
        }

        .pill {
            padding: 0.45rem 0.75rem;
            border-radius: 999px;
            border: 1px solid rgba(151, 170, 210, 0.16);
            background: rgba(255, 255, 255, 0.04);
            color: #dbe7ff;
            font-size: 0.84rem;
        }

        .severity-dot {
            display: inline-block;
            width: 10px;
            height: 10px;
            border-radius: 50%;
            margin-right: 0.5rem;
        }

        .mini-note {
            color: #8ea4c7;
            font-size: 0.88rem;
        }

        .risk-item {
            padding: 0.85rem 0;
            border-bottom: 1px solid rgba(151, 170, 210, 0.1);
        }

        .risk-item:last-child {
            border-bottom: none;
            padding-bottom: 0;
        }

        .risk-title {
            font-size: 0.95rem;
            font-weight: 700;
            color: #f2f6ff;
            margin-bottom: 0.22rem;
        }

        .risk-meta {
            color: #8ea4c7;
            font-size: 0.84rem;
        }

        div[data-testid="stDataFrame"] {
            border-radius: 18px;
            overflow: hidden;
            border: 1px solid rgba(151, 170, 210, 0.12);
        }

        .stTabs [data-baseweb="tab-list"] {
            gap: 0.5rem;
        }

        .stTabs [data-baseweb="tab"] {
            background: rgba(255, 255, 255, 0.04);
            border-radius: 999px;
            padding: 0.55rem 1rem;
            color: #dce6fb;
        }

        .stTabs [aria-selected="true"] {
            background: linear-gradient(135deg, rgba(0, 196, 140, 0.24), rgba(34, 197, 94, 0.18));
        }

        .stTextInput label, .stMultiSelect label {
            color: #dbe7ff !important;
            font-weight: 600;
        }

        .stButton > button {
            border: none;
            border-radius: 14px;
            background: linear-gradient(135deg, #00c48c, #11a6a0);
            color: white;
            font-weight: 700;
            padding: 0.7rem 1.15rem;
            box-shadow: 0 14px 28px rgba(0, 196, 140, 0.25);
        }

        .stProgress > div > div {
            background: linear-gradient(90deg, #00c48c, #4ecdc4);
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def initialize_state() -> None:
    if "review_started" not in st.session_state:
        st.session_state.review_started = False
    if "review_complete" not in st.session_state:
        st.session_state.review_complete = False
    if "selected_models" not in st.session_state:
        st.session_state.selected_models = ["GPT-4", "Claude", "Gemini"]


def make_issue_data() -> pd.DataFrame:
    rows = [
        ("app/auth.py", "Hardcoded fallback credential path", "critical", "High consensus", "GPT-4"),
        ("app/auth.py", "Session token rotation missing", "warning", "Medium consensus", "Claude"),
        ("app/review_orchestrator.py", "Retry strategy may amplify rate limits", "warning", "High consensus", "Gemini"),
        ("app/review_orchestrator.py", "Long-running task visibility is limited", "info", "High consensus", "Llama"),
        ("app/repo_loader.py", "Archive extraction boundary not explicit", "critical", "High consensus", "GPT-4"),
        ("app/repo_loader.py", "Large repository memory pressure risk", "warning", "Medium consensus", "Gemini"),
        ("app/report_writer.py", "Markdown escaping incomplete for edge cases", "info", "Medium consensus", "Claude"),
        ("app/static_analyzer.py", "Regex rules may miss multiline secrets", "warning", "High consensus", "GPT-4"),
        ("app/static_analyzer.py", "False-positive suppression is basic", "info", "Low consensus", "Llama"),
        ("tests/test_review.py", "Regression coverage gaps in consensus logic", "warning", "High consensus", "Claude"),
        ("tests/test_api.py", "Missing auth failure-path tests", "warning", "Medium consensus", "Gemini"),
        ("infra/deploy.yml", "Production secret source not validated", "critical", "High consensus", "GPT-4"),
    ]
    return pd.DataFrame(
        rows,
        columns=["File name", "Issue type", "Severity", "Consensus", "Model"],
    )


def build_stats(issue_df: pd.DataFrame) -> dict[str, int]:
    counts = Counter(issue_df["Severity"])
    critical = counts.get("critical", 0)
    warning = counts.get("warning", 0)
    info = counts.get("info", 0)
    repository_health = max(100 - (critical * 13 + warning * 5 + info * 2), 36)
    risk_score = min(critical * 22 + warning * 11 + info * 4, 94)
    return {
        "critical": critical,
        "warning": warning,
        "info": info,
        "repository_health": repository_health,
        "risk_score": risk_score,
    }


def render_sidebar() -> str:
    with st.sidebar:
        st.markdown("## 🧭 Navigation")
        section = st.radio(
            "Go to",
            ["Dashboard", "Reports", "Integrations", "Settings"],
            label_visibility="collapsed",
        )
        st.markdown("### 🤖 Review Models")
        selected_models = st.multiselect(
            "Models",
            MODELS,
            default=st.session_state.selected_models,
            label_visibility="collapsed",
        )
        st.session_state.selected_models = selected_models or ["GPT-4"]

        st.markdown("### 🚦 Status")
        st.markdown(
            """
            <div class="glass-card">
                <div class="mini-note">Pipeline readiness</div>
                <div style="font-size: 1.8rem; font-weight: 800; margin: 0.25rem 0;">97%</div>
                <div class="mini-note">Mock mode enabled for demo-safe runs</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
    return section


def render_hero(repo_url: str, branch: str) -> None:
    st.markdown(
        f"""
        <div class="hero">
            <p class="hero-title">CodeReview AI</p>
            <p class="hero-subtitle">
                Multi-model repository diagnostics, risk analysis, and consensus reporting for modern engineering teams.
            </p>
            <div class="pill-row">
                <span class="pill">🔗 {repo_url}</span>
                <span class="pill">🌿 {branch}</span>
                <span class="pill">🧠 {' • '.join(st.session_state.selected_models)}</span>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_inputs(default_repo: str, default_branch: str) -> tuple[str, str, bool]:
    input_col, info_col = st.columns([1.8, 1.05], gap="large")

    with input_col:
        st.markdown('<div class="glass-card">', unsafe_allow_html=True)
        st.markdown('<div class="section-title">Repository Review Input</div>', unsafe_allow_html=True)
        repo_url = st.text_input("GitHub Repository", value=default_repo, placeholder="https://github.com/org/repo")
        branch = st.text_input("Branch", value=default_branch, placeholder="main")
        run_review = st.button("Run Review", use_container_width=False)
        st.markdown("</div>", unsafe_allow_html=True)

    with info_col:
        st.markdown(
            """
            <div class="glass-card">
                <div class="section-title">Live Review Scope</div>
                <div class="pill-row">
                    <span class="pill">🛡️ Security focus</span>
                    <span class="pill">⚙️ Architecture signals</span>
                    <span class="pill">📈 Performance heuristics</span>
                    <span class="pill">🤝 Consensus merge</span>
                </div>
                <p class="mini-note" style="margin-top: 1rem;">
                    This mock dashboard mirrors a SaaS analytics panel while keeping the review flow ready to connect to your backend.
                </p>
            </div>
            """,
            unsafe_allow_html=True,
        )

    return repo_url, branch, run_review


def run_progress() -> None:
    st.session_state.review_started = True
    progress_container = st.container()
    with progress_container:
        st.markdown('<div class="glass-card">', unsafe_allow_html=True)
        st.markdown('<div class="section-title">Review Progress</div>', unsafe_allow_html=True)
        progress_bar = st.progress(0)
        status = st.empty()
        steps = [
            ("🔍 Scanning Repository", 33),
            ("🧠 Model Analysis", 72),
            ("🧩 Aggregation", 100),
        ]
        for label, value in steps:
            status.markdown(f"**{label}**")
            progress_bar.progress(value)
            time.sleep(0.35)
        st.success("Review complete. Dashboard updated with mock insights.")
        st.markdown("</div>", unsafe_allow_html=True)
    st.session_state.review_complete = True


def metric_card(title: str, value: str, footnote: str, accent: str) -> str:
    return f"""
        <div class="stat-card">
            <div class="stat-label">{title}</div>
            <div class="stat-value" style="color: {accent};">{value}</div>
            <div class="stat-foot">{footnote}</div>
        </div>
    """


def build_gauge(risk_score: int) -> go.Figure:
    fig = go.Figure(
        go.Indicator(
            mode="gauge+number",
            value=risk_score,
            number={"font": {"size": 34, "color": "#f7fbff"}},
            gauge={
                "axis": {"range": [0, 100], "tickcolor": "#8ea4c7"},
                "bar": {"color": "#ff5c7c"},
                "bgcolor": "rgba(255,255,255,0.04)",
                "borderwidth": 0,
                "steps": [
                    {"range": [0, 35], "color": "rgba(55, 214, 122, 0.35)"},
                    {"range": [35, 70], "color": "rgba(246, 200, 95, 0.35)"},
                    {"range": [70, 100], "color": "rgba(255, 92, 124, 0.38)"},
                ],
            },
            title={"text": "Risk Score", "font": {"size": 18, "color": "#dce6fb"}},
        )
    )
    fig.update_layout(
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        margin=dict(l=20, r=20, t=60, b=10),
        height=250,
    )
    return fig


def build_bar_chart(issue_df: pd.DataFrame) -> go.Figure:
    order = ["critical", "warning", "info"]
    grouped = (
        issue_df.groupby(["Model", "Severity"])
        .size()
        .reset_index(name="Count")
    )
    grouped["Severity"] = pd.Categorical(grouped["Severity"], categories=order, ordered=True)
    grouped = grouped.sort_values(["Model", "Severity"])
    fig = px.bar(
        grouped,
        x="Model",
        y="Count",
        color="Severity",
        barmode="group",
        color_discrete_map={
            "critical": SEVERITY_COLORS["critical"],
            "warning": SEVERITY_COLORS["warning"],
            "info": SEVERITY_COLORS["info"],
        },
    )
    fig.update_layout(
        height=320,
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        margin=dict(l=10, r=10, t=30, b=10),
        legend_title_text="Severity",
        font=dict(color="#dce6fb"),
    )
    fig.update_xaxes(showgrid=False, title="")
    fig.update_yaxes(gridcolor="rgba(151, 170, 210, 0.12)", title="")
    return fig


def build_pie_chart(issue_df: pd.DataFrame) -> go.Figure:
    categories = pd.DataFrame(
        {
            "Issue type": ["Security", "Performance", "Testing", "Maintainability", "Architecture"],
            "Count": [4, 2, 3, 2, 1],
        }
    )
    fig = px.pie(
        categories,
        values="Count",
        names="Issue type",
        hole=0.65,
        color_discrete_sequence=["#ff5c7c", "#f6c85f", "#4ecdc4", "#7fb3ff", "#37d67a"],
    )
    fig.update_traces(textposition="inside", textinfo="percent+label")
    fig.update_layout(
        height=320,
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        margin=dict(l=10, r=10, t=30, b=10),
        font=dict(color="#dce6fb"),
        showlegend=False,
    )
    return fig


def render_stats(stats: dict[str, int]) -> None:
    col1, col2, col3 = st.columns([1, 1, 1.15], gap="large")
    with col1:
        st.markdown(
            metric_card(
                "Repository Health",
                f"{stats['repository_health']}/100",
                "🟢 Stable baseline with concentrated hotspots",
                SEVERITY_COLORS["good"],
            ),
            unsafe_allow_html=True,
        )
    with col2:
        st.markdown(
            metric_card(
                "Total Issues",
                f"{stats['critical'] + stats['warning'] + stats['info']}",
                f"🔴 {stats['critical']} critical  •  🟡 {stats['warning']} warning  •  🔵 {stats['info']} info",
                "#f7fbff",
            ),
            unsafe_allow_html=True,
        )
    with col3:
        st.markdown('<div class="glass-card">', unsafe_allow_html=True)
        st.plotly_chart(build_gauge(stats["risk_score"]), use_container_width=True, config={"displayModeBar": False})
        st.markdown("</div>", unsafe_allow_html=True)


def render_charts(issue_df: pd.DataFrame) -> None:
    bar_col, pie_col = st.columns([1.35, 1], gap="large")
    with bar_col:
        st.markdown('<div class="glass-card">', unsafe_allow_html=True)
        st.markdown('<div class="section-title">Issue Breakdown by Model</div>', unsafe_allow_html=True)
        st.plotly_chart(build_bar_chart(issue_df), use_container_width=True, config={"displayModeBar": False})
        st.markdown("</div>", unsafe_allow_html=True)
    with pie_col:
        st.markdown('<div class="glass-card">', unsafe_allow_html=True)
        st.markdown('<div class="section-title">Issue Types</div>', unsafe_allow_html=True)
        st.plotly_chart(build_pie_chart(issue_df), use_container_width=True, config={"displayModeBar": False})
        st.markdown("</div>", unsafe_allow_html=True)


def render_reports(issue_df: pd.DataFrame) -> None:
    report_col, side_col = st.columns([1.75, 0.95], gap="large")

    with report_col:
        st.markdown('<div class="glass-card">', unsafe_allow_html=True)
        st.markdown('<div class="section-title">Review Report</div>', unsafe_allow_html=True)
        summary_tab, issues_tab, perf_tab, security_tab, consensus_tab = st.tabs(
            ["Summary", "Issues by File", "Performance", "Security", "Consensus"]
        )

        with summary_tab:
            st.markdown(
                """
                ### Executive Summary
                The repository shows strong modularity, but the review surface still contains a few concentrated security and reliability risks.
                Multi-model agreement is strongest around authentication boundaries, repository ingestion safety, and gaps in failure-path testing.

                ### Recommended Next Actions
                1. Prioritize secret handling and repository ingestion hardening.
                2. Add regression tests around consensus logic and auth edge cases.
                3. Instrument retry and queue execution for better operational visibility.
                """
            )

        with issues_tab:
            table_df = issue_df[["File name", "Issue type", "Severity", "Consensus"]].copy()
            severity_order = {"critical": 0, "warning": 1, "info": 2}
            table_df["sort_key"] = table_df["Severity"].map(severity_order)
            table_df = table_df.sort_values(["sort_key", "File name"]).drop(columns=["sort_key"])
            st.dataframe(table_df, use_container_width=True, hide_index=True)

        with perf_tab:
            perf_df = pd.DataFrame(
                {
                    "Stage": ["Clone", "Static Analysis", "LLM Calls", "Aggregation"],
                    "Seconds": [6.4, 8.1, 21.7, 4.2],
                }
            )
            perf_fig = px.area(
                perf_df,
                x="Stage",
                y="Seconds",
                markers=True,
                color_discrete_sequence=["#4ecdc4"],
            )
            perf_fig.update_layout(
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(0,0,0,0)",
                font=dict(color="#dce6fb"),
                margin=dict(l=10, r=10, t=10, b=10),
                height=320,
            )
            st.plotly_chart(perf_fig, use_container_width=True, config={"displayModeBar": False})

        with security_tab:
            st.markdown(
                """
                ### High-Risk Security Signals
                - Ingestion boundary checks need stricter validation around archive extraction and path handling.
                - Secret scanning rules should expand beyond single-line regex coverage.
                - Production deployment config should validate secret provenance before release.
                """
            )

        with consensus_tab:
            consensus_points = pd.DataFrame(
                {
                    "Theme": ["Auth hardening", "Repository safety", "Testing coverage", "Observability"],
                    "Agreement": [0.92, 0.87, 0.81, 0.63],
                }
            )
            consensus_fig = px.bar(
                consensus_points,
                x="Theme",
                y="Agreement",
                color="Agreement",
                color_continuous_scale=["#21413a", "#00c48c", "#7ce7c8"],
            )
            consensus_fig.update_layout(
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(0,0,0,0)",
                font=dict(color="#dce6fb"),
                margin=dict(l=10, r=10, t=10, b=10),
                height=320,
                coloraxis_showscale=False,
            )
            st.plotly_chart(consensus_fig, use_container_width=True, config={"displayModeBar": False})
        st.markdown("</div>", unsafe_allow_html=True)

    with side_col:
        top_risk = [
            ("Hardcoded fallback credential path", "app/auth.py", "critical"),
            ("Production secret source not validated", "infra/deploy.yml", "critical"),
            ("Archive extraction boundary not explicit", "app/repo_loader.py", "critical"),
        ]
        highlights = [
            "GPT-4 and Claude align strongly on auth and secret handling risk.",
            "Gemini highlights testing blind spots around failure paths and retries.",
            "Consensus confidence is highest in ingestion and deployment layers.",
        ]

        st.markdown(
            '<div class="glass-card"><div class="section-title">Top Risk Issues</div>',
            unsafe_allow_html=True,
        )
        for title, file_name, severity in top_risk:
            accent = SEVERITY_COLORS["critical"] if severity == "critical" else SEVERITY_COLORS["warning"]
            st.markdown(
                f"""
                <div class="risk-item">
                    <div class="risk-title"><span class="severity-dot" style="background:{accent};"></span>{title}</div>
                    <div class="risk-meta">{file_name} • {severity.title()}</div>
                </div>
                """,
                unsafe_allow_html=True,
            )
        st.markdown("</div>", unsafe_allow_html=True)

        st.markdown(
            """
            <div class="glass-card" style="margin-top: 1rem;">
                <div class="section-title">Consensus Highlights</div>
            """,
            unsafe_allow_html=True,
        )
        for point in highlights:
            st.markdown(f"- {point}")
        st.markdown("</div>", unsafe_allow_html=True)


def render_placeholder(section: str) -> None:
    notes = {
        "Reports": "Use this view for historical review runs, export access, and traceable report comparison.",
        "Integrations": "Connect GitHub webhooks, Slack alerts, and ticketing systems to operationalize review output.",
        "Settings": "Tune model routing, severity thresholds, branch defaults, and organization-wide review policies.",
    }
    st.markdown(
        f"""
        <div class="glass-card">
            <div class="section-title">{section}</div>
            <p style="color:#dce6fb; font-size:1rem;">{notes[section]}</p>
            <p class="mini-note">The primary dashboard below remains fully interactive so the SaaS admin-panel experience stays visible during demos.</p>
        </div>
        """,
        unsafe_allow_html=True,
    )


def main() -> None:
    initialize_state()
    inject_styles()
    section = render_sidebar()

    default_repo = "https://github.com/acme/ai-code-reviewer"
    default_branch = "main"
    repo_url, branch, run_review = render_inputs(default_repo, default_branch)
    render_hero(repo_url, branch)

    if section != "Dashboard":
        render_placeholder(section)

    if run_review:
        run_progress()

    issue_df = make_issue_data()
    if st.session_state.selected_models:
        issue_df = issue_df[issue_df["Model"].isin(st.session_state.selected_models)]

    stats = build_stats(issue_df)
    render_stats(stats)
    st.write("")
    render_charts(issue_df)
    st.write("")
    render_reports(issue_df)


if __name__ == "__main__":
    main()
