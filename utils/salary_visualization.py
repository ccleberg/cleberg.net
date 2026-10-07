"""
Visualize salary data from theme/static/salary.csv with plotly.

Usage:
    python utils/salary_visualization.py                      # open in a browser
    python utils/salary_visualization.py light.webp           # write an image (needs kaleido)
    python utils/salary_visualization.py light.webp dark.webp # light and dark variants
"""

import sys
from datetime import UTC, datetime

import pandas as pd
import plotly.graph_objs as go

CSV_PATH = "~/git/cmc/cleberg.net/theme/static/salary.csv"

# Surfaces match theme/static/styles.css. Series colors are one per company in
# order of first appearance; the dark steps are the same hues re-stepped for
# the dark surface.
THEMES = {
    "light": {
        "surface": "#ffffff",
        "text": "#0b0b0b",
        "muted": "#52514e",
        "grid": "#f0efec",
        "band": "#f8f8f6",
        "palette": ["#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4", "#008300"],
    },
    "dark": {
        "surface": "#181a1b",
        "text": "#ffffff",
        "muted": "#c3c2b7",
        "grid": "#262829",
        "band": "#1f2122",
        "palette": ["#3987e5", "#d95926", "#199e70", "#c98500", "#d55181", "#008300"],
    },
}
DASH = {"salaried": "solid", "hourly": "dot"}
HOURS_PER_YEAR = 2080


def load() -> pd.DataFrame:
    df = pd.read_csv(CSV_PATH)
    df["Start"] = pd.to_datetime(df["Start"])
    df["End"] = pd.to_datetime(df["End"])
    return df.sort_values(["Start", "End"]).reset_index(drop=True)


def label(row: pd.Series, muted: str) -> str:
    salary = f"${row['Salary']:,.0f}"
    detail = row["Title"]
    if row["PayType"] == "hourly":
        # A second "$" in one string makes plotly parse it as LaTeX.
        detail = f"&#36;{row['Salary'] / HOURS_PER_YEAR:,.0f}/hr · " + detail
    if row["PercentChange"]:
        detail += f" · {row['PercentChange'] * 100:+.1f}%"
    return f"<b>{salary}</b> <span style='font-size:12px;color:{muted}'>{detail}</span>"


def build_figure(df: pd.DataFrame, theme: str = "light") -> go.Figure:
    t = THEMES[theme]
    fig = go.Figure()
    companies = list(dict.fromkeys(df["Company"]))
    colors = dict(zip(companies, t["palette"]))

    # Thin connectors between a job's end and the next job's start, drawn
    # first so the salary segments sit on top. Concurrent jobs get none.
    ends = {row["End"]: row for _, row in df.iterrows()}
    for _, row in df.iterrows():
        prev = ends.get(row["Start"])
        if prev is None:
            continue
        fig.add_trace(
            go.Scatter(
                x=[row["Start"], row["Start"]],
                y=[prev["Salary"], row["Salary"]],
                mode="lines",
                line={"color": t["grid"], "width": 1.5},
                hoverinfo="skip",
                showlegend=False,
            )
        )

    # One trace per company and pay type. Hourly jobs are dotted. Legend
    # entries are separate dummy traces so every company swatch is solid.
    for (company, pay), rows in df.groupby(["Company", "PayType"]):
        xs: list = []
        ys: list = []
        for _, row in rows.iterrows():
            xs += [row["Start"], row["End"], None]
            ys += [row["Salary"], row["Salary"], None]
        fig.add_trace(
            go.Scatter(
                x=xs,
                y=ys,
                mode="lines",
                line={"color": colors[company], "width": 4, "dash": DASH[pay]},
                hoverinfo="skip",
                showlegend=False,
            )
        )
    entries = [(c, colors[c], "solid") for c in companies]
    entries += [(pay.capitalize(), t["muted"], dash) for pay, dash in DASH.items()]
    for name, color, dash in entries:
        fig.add_trace(
            go.Scatter(
                x=[None],
                y=[None],
                mode="lines",
                name=name,
                line={"color": color, "width": 4, "dash": dash},
            )
        )

    # Direct labels above each segment, starting at the segment's left end so
    # they extend over the empty space under the next, higher step. The last
    # segment anchors on its right end so the label stays inside the plot. A
    # label moves below its segment when a later segment at a similar salary
    # starts within the label's reach (the concurrent 2017 jobs).
    y_gap = df["Salary"].max() * 0.035
    last = len(df) - 1
    for i, row in df.iterrows():
        later = df.iloc[i + 1 :]
        above = not (
            ((later["Start"] - row["Start"]).dt.days < 400)
            & ((later["Salary"] - row["Salary"]).abs() < y_gap)
        ).any()
        fig.add_annotation(
            x=row["End"] if i == last else row["Start"],
            xanchor="right" if i == last else "left",
            y=row["Salary"],
            yanchor="bottom" if above else "top",
            yshift=5 if above else -5,
            text=label(row, t["muted"]),
            showarrow=False,
            font={"color": t["text"], "size": 14},
        )

    # Shade everything after today so the current job's end reads as projected.
    today = datetime.now(tz=UTC).date()
    fig.add_vrect(
        x0=today,
        x1=df["End"].max(),
        fillcolor=t["band"],
        line_width=0,
        layer="below",
    )
    fig.add_annotation(
        x=today,
        y=0,
        yref="paper",
        text="today",
        showarrow=False,
        xanchor="left",
        xshift=4,
        yanchor="bottom",
        yshift=4,
        font={"color": t["muted"], "size": 12},
    )
    fig.add_annotation(
        x=0,
        y=-0.2,
        xref="paper",
        yref="paper",
        text=(
            f"Hourly rates annualized at {HOURS_PER_YEAR:,} hours. "
            "Percent change is against the preceding job. "
            "Shaded area is after today."
        ),
        showarrow=False,
        xanchor="left",
        yanchor="top",
        font={"color": t["muted"], "size": 12},
    )

    pad = pd.Timedelta(days=180)
    fig.update_layout(
        title={
            "text": f"Annualized pay by job, {df['Start'].min().year}–{df['End'].max().year}",
            "x": 0.03,
        },
        template="plotly_white",
        paper_bgcolor=t["surface"],
        plot_bgcolor=t["surface"],
        font={"family": "monospace", "size": 14, "color": t["text"]},
        margin={"l": 90, "r": 40, "t": 70, "b": 150},
        width=1600,
        height=800,
        xaxis={
            "showgrid": True,
            "gridcolor": t["grid"],
            "dtick": "M12",
            "tickformat": "%Y",
            "linecolor": t["muted"],
            "range": [df["Start"].min() - pad, df["End"].max() + pad],
        },
        yaxis={
            "showgrid": True,
            "gridcolor": t["grid"],
            "tickformat": "$,.0f",
            "rangemode": "tozero",
        },
        legend={
            "orientation": "h",
            "yanchor": "top",
            "y": -0.09,
            "xanchor": "center",
            "x": 0.5,
            "title": None,
        },
    )
    return fig


def main() -> None:
    df = load()
    paths = sys.argv[1:]
    if not paths:
        build_figure(df).show()
    for path, theme in zip(paths, THEMES):
        build_figure(df, theme).write_image(path, scale=2)


if __name__ == "__main__":
    main()
