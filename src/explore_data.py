"""Generate reproducible tables and figures for the HDB market analysis."""

from pathlib import Path

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
from matplotlib.ticker import FuncFormatter
import pandas as pd
import seaborn as sns


RENTAL_PATH = Path(
    "data/processed/hdb_rental_analysis_ready.csv"
)
RESALE_PATH = Path(
    "data/processed/hdb_resale_analysis_ready.csv"
)

FIGURE_DIRECTORY = Path("reports/figures")
TABLE_DIRECTORY = Path("reports/tables")

PERIOD_FORMAT = "%Y-%m-%d"
COMPARISON_YEAR = 2025
MIN_MONTHLY_RECORDS = 10

COMMON_GROUPS = [
    "calendar_year",
    "calendar_month",
    "town",
    "flat_type_normalised",
]

EXPECTED_COLUMNS = {
    "rental": {
        "source_row_id",
        "approval_month",
        "town",
        "flat_type_normalised",
        "monthly_rent",
        "calendar_year",
        "calendar_month",
        "nearest_train_distance_km",
        "train_distance_band",
    },
    "resale": {
        "source_row_id",
        "transaction_month",
        "town",
        "flat_type_normalised",
        "resale_price",
        "calendar_year",
        "calendar_month",
        "nearest_train_distance_km",
        "train_distance_band",
    },
}


def configure_plotting() -> None:
    """Apply one consistent plotting style."""

    sns.set_theme(
        style="whitegrid",
        context="notebook",
        palette="colorblind",
    )

    plt.rcParams.update(
        {
            "figure.dpi": 120,
            "savefig.dpi": 180,
            "axes.titleweight": "bold",
            "axes.labelsize": 10,
            "axes.titlesize": 12,
            "figure.titlesize": 15,
            "legend.frameon": False,
        }
    )


def load_dataset(
    path: Path,
    period_column: str,
    dataset_name: str,
) -> pd.DataFrame:
    """Load and validate one analysis-ready dataset."""

    data = pd.read_csv(
        path,
        dtype={"source_row_id": "string"},
    )

    missing_columns = (
        EXPECTED_COLUMNS[dataset_name] - set(data.columns)
    )

    if missing_columns:
        raise ValueError(
            f"{dataset_name.title()} is missing columns: "
            f"{sorted(missing_columns)}"
        )

    periods = pd.to_datetime(
        data[period_column],
        format=PERIOD_FORMAT,
        errors="coerce",
    )

    if periods.isna().any():
        raise ValueError(
            f"{dataset_name.title()} contains "
            f"{periods.isna().sum():,} invalid periods."
        )

    if data["source_row_id"].duplicated().any():
        raise ValueError(
            f"{dataset_name.title()} source_row_id is not unique."
        )

    data = data.copy()
    data["period"] = periods

    return data


def save_table(
    data: pd.DataFrame,
    filename: str,
) -> None:
    """Save a table with stable ordering and formatting."""

    output_path = TABLE_DIRECTORY / filename

    data.to_csv(
        output_path,
        index=False,
        float_format="%.2f",
    )

    print(
        f"Saved table: {output_path} "
        f"({len(data):,} rows)"
    )


def save_figure(
    figure: plt.Figure,
    filename: str,
) -> None:
    """Save and close a completed figure."""

    output_path = FIGURE_DIRECTORY / filename

    figure.savefig(
        output_path,
        bbox_inches="tight",
        facecolor="white",
    )

    plt.close(figure)

    print(f"Saved figure: {output_path}")


def build_monthly_summary(
    data: pd.DataFrame,
    value_column: str,
    median_name: str,
) -> pd.DataFrame:
    """Calculate monthly median values and record counts."""

    return (
        data.groupby(
            "period",
            as_index=False,
            observed=True,
        )
        .agg(
            **{
                median_name: (
                    value_column,
                    "median",
                ),
                "record_count": (
                    value_column,
                    "size",
                ),
            }
        )
        .sort_values("period")
    )



def plot_monthly_trends(
    rental_monthly: pd.DataFrame,
    resale_monthly: pd.DataFrame,
) -> None:
    """Plot overall rental and resale monthly trends."""

    figure, axes = plt.subplots(
        nrows=2,
        figsize=(12, 9),
        sharex=False,
    )

    sns.lineplot(
        data=rental_monthly,
        x="period",
        y="median_monthly_rent",
        ax=axes[0],
        color="#0072B2",
        linewidth=2,
    )

    axes[0].set(
        title="Monthly median approved rent",
        xlabel="",
        ylabel="Median monthly rent (S$)",
    )

    sns.lineplot(
        data=resale_monthly,
        x="period",
        y="median_resale_price",
        ax=axes[1],
        color="#D55E00",
        linewidth=2,
    )

    axes[1].set(
        title="Monthly median resale price",
        xlabel="Transaction month",
        ylabel="Median resale price (S$)",
    )

    rental_end = rental_monthly["period"].max().strftime(
        "%B %Y"
    )
    resale_end = resale_monthly["period"].max().strftime(
        "%B %Y"
    )

    figure.suptitle(
        "HDB rental and resale market trends\n"
        f"Rental through {rental_end}; "
        f"resale through {resale_end}"
    )
    figure.tight_layout()

    save_figure(
        figure,
        "monthly_market_trends.png",
    )

def build_flat_type_summary(
    data: pd.DataFrame,
    value_column: str,
    median_name: str,
) -> pd.DataFrame:
    """Calculate monthly median values by flat type."""

    return (
        data.groupby(
            [
                "period",
                "flat_type_normalised",
            ],
            as_index=False,
            observed=True,
        )
        .agg(
            **{
                median_name: (
                    value_column,
                    "median",
                ),
                "record_count": (
                    value_column,
                    "size",
                ),
            }
        )
        .sort_values(
            [
                "flat_type_normalised",
                "period",
            ]
        )
    )



def plot_flat_type_trends(
    rental_summary: pd.DataFrame,
    resale_summary: pd.DataFrame,
) -> None:
    """Plot sufficiently supported monthly flat-type trends."""

    rental_plot = rental_summary.loc[
        rental_summary["record_count"].ge(
            MIN_MONTHLY_RECORDS
        )
    ].copy()

    resale_plot = resale_summary.loc[
        resale_summary["record_count"].ge(
            MIN_MONTHLY_RECORDS
        )
    ].copy()

    rental_excluded = sorted(
        set(rental_summary["flat_type_normalised"])
        - set(rental_plot["flat_type_normalised"])
    )
    resale_excluded = sorted(
        set(resale_summary["flat_type_normalised"])
        - set(resale_plot["flat_type_normalised"])
    )

    figure, axes = plt.subplots(
        nrows=2,
        figsize=(13, 10),
    )

    sns.lineplot(
        data=rental_plot,
        x="period",
        y="median_monthly_rent",
        hue="flat_type_normalised",
        ax=axes[0],
        linewidth=1.7,
    )

    axes[0].set(
        title="Approved rent by flat type",
        xlabel="",
        ylabel="Median monthly rent (S$)",
    )
    axes[0].legend(
        title="Flat type",
        ncol=2,
    )

    sns.lineplot(
        data=resale_plot,
        x="period",
        y="median_resale_price",
        hue="flat_type_normalised",
        ax=axes[1],
        linewidth=1.7,
    )

    axes[1].set(
        title="Resale price by flat type",
        xlabel="Transaction month",
        ylabel="Median resale price (S$)",
    )
    axes[1].legend(
        title="Flat type",
        ncol=2,
    )

    rental_end = rental_summary["period"].max().strftime(
        "%B %Y"
    )
    resale_end = resale_summary["period"].max().strftime(
        "%B %Y"
    )

    figure.suptitle(
        "HDB market trends by flat type\n"
        f"Rental through {rental_end}; "
        f"resale through {resale_end}"
    )

    exclusion_note = (
        f"Monthly medians require at least "
        f"{MIN_MONTHLY_RECORDS} records. "
        f"Entirely excluded from rental: "
        f"{', '.join(rental_excluded) or 'none'}; "
        f"resale: "
        f"{', '.join(resale_excluded) or 'none'}."
    )

    figure.text(
        0.5,
        0.01,
        exclusion_note,
        ha="center",
        fontsize=9,
    )
    figure.tight_layout(
        rect=(0, 0.05, 1, 0.94)
    )

    save_figure(
        figure,
        "flat_type_market_trends.png",
    )

def build_town_summary(
    data: pd.DataFrame,
    value_column: str,
    median_name: str,
) -> pd.DataFrame:
    """Calculate full-year town medians."""

    comparison_data = data.loc[
        data["calendar_year"].eq(COMPARISON_YEAR)
    ]

    return (
        comparison_data.groupby(
            "town",
            as_index=False,
            observed=True,
        )
        .agg(
            **{
                median_name: (
                    value_column,
                    "median",
                ),
                "record_count": (
                    value_column,
                    "size",
                ),
            }
        )
        .sort_values(
            median_name,
            ascending=False,
        )
    )



def plot_town_comparisons(
    rental_towns: pd.DataFrame,
    resale_towns: pd.DataFrame,
) -> None:
    """Plot the ten highest-median towns in each market."""

    figure, axes = plt.subplots(
        ncols=2,
        figsize=(14, 7),
    )

    rental_top = (
        rental_towns
        .head(10)
        .sort_values("median_monthly_rent")
    )

    resale_top = (
        resale_towns
        .head(10)
        .sort_values("median_resale_price")
    )

    sns.barplot(
        data=rental_top,
        x="median_monthly_rent",
        y="town",
        ax=axes[0],
        color="#0072B2",
    )

    axes[0].set(
        title="Highest median approved rents",
        xlabel="Median monthly rent (S$)",
        ylabel="Town",
    )
    axes[0].xaxis.set_major_formatter(
        FuncFormatter(
            lambda value, position: f"S${value:,.0f}"
        )
    )

    sns.barplot(
        data=resale_top,
        x="median_resale_price",
        y="town",
        ax=axes[1],
        color="#D55E00",
    )

    axes[1].set(
        title="Highest median resale prices",
        xlabel="Median resale price (S$ thousands)",
        ylabel="Town",
    )
    axes[1].xaxis.set_major_formatter(
        FuncFormatter(
            lambda value, position: (
                f"S${value / 1_000:,.0f}k"
            )
        )
    )

    figure.suptitle(
        f"HDB town comparison: {COMPARISON_YEAR}\n"
        "All flat types; descriptive and unadjusted"
    )
    figure.tight_layout()

    save_figure(
        figure,
        "town_medians_2025.png",
    )

def build_distance_summary(
    data: pd.DataFrame,
    value_column: str,
    median_name: str,
) -> pd.DataFrame:
    """Calculate descriptive summaries by train-distance band."""

    return (
        data.groupby(
            "train_distance_band",
            as_index=False,
            observed=True,
            dropna=False,
        )
        .agg(
            **{
                median_name: (
                    value_column,
                    "median",
                ),
                "median_distance_km": (
                    "nearest_train_distance_km",
                    "median",
                ),
                "record_count": (
                    value_column,
                    "size",
                ),
            }
        )
        .sort_values(
            [
                "median_distance_km",
                "train_distance_band",
            ],
            na_position="last",
        )
    )



def plot_distance_comparisons(
    rental_distance: pd.DataFrame,
    resale_distance: pd.DataFrame,
) -> None:
    """Plot values for records matched to train-distance bands."""

    rental_plot = rental_distance.loc[
        rental_distance["train_distance_band"]
        .astype("string")
        .str.casefold()
        .ne("unmatched")
        & rental_distance["train_distance_band"].notna()
    ].copy()

    resale_plot = resale_distance.loc[
        resale_distance["train_distance_band"]
        .astype("string")
        .str.casefold()
        .ne("unmatched")
        & resale_distance["train_distance_band"].notna()
    ].copy()

    figure, axes = plt.subplots(
        ncols=2,
        figsize=(15, 6),
    )

    sns.barplot(
        data=rental_plot,
        x="train_distance_band",
        y="median_monthly_rent",
        ax=axes[0],
        color="#009E73",
    )

    axes[0].set(
        title="Approved rent by train-distance band",
        xlabel="Distance band",
        ylabel="Median monthly rent (S$)",
    )

    sns.barplot(
        data=resale_plot,
        x="train_distance_band",
        y="median_resale_price",
        ax=axes[1],
        color="#CC79A7",
    )

    axes[1].set(
        title="Resale price by train-distance band",
        xlabel="Distance band",
        ylabel="Median resale price (S$)",
    )

    for axis in axes:
        axis.tick_params(
            axis="x",
            labelrotation=35,
        )

    figure.suptitle(
        "Descriptive market comparison by train proximity\n"
        "Matched records only; unadjusted medians"
    )
    figure.text(
        0.5,
        0.01,
        (
            "Distance bands do not isolate the effect of "
            "train proximity and should not be interpreted "
            "as causal estimates."
        ),
        ha="center",
        fontsize=9,
    )
    figure.tight_layout(
        rect=(0, 0.06, 1, 0.93)
    )

    save_figure(
        figure,
        "train_distance_medians.png",
    )

def build_cross_market_panel(
    rental: pd.DataFrame,
    resale: pd.DataFrame,
) -> pd.DataFrame:
    """Create comparable town-flat-type-month observations."""

    rental_panel = (
        rental.groupby(
            COMMON_GROUPS,
            as_index=False,
            observed=True,
        )
        .agg(
            median_monthly_rent=(
                "monthly_rent",
                "median",
            ),
            rental_record_count=(
                "monthly_rent",
                "size",
            ),
        )
    )

    resale_panel = (
        resale.groupby(
            COMMON_GROUPS,
            as_index=False,
            observed=True,
        )
        .agg(
            median_resale_price=(
                "resale_price",
                "median",
            ),
            resale_record_count=(
                "resale_price",
                "size",
            ),
        )
    )

    panel = rental_panel.merge(
        resale_panel,
        on=COMMON_GROUPS,
        how="inner",
        validate="one_to_one",
    )

    panel["period"] = pd.to_datetime(
        {
            "year": panel["calendar_year"],
            "month": panel["calendar_month"],
            "day": 1,
        }
    )

    panel["indicative_gross_yield_pct"] = (
        panel["median_monthly_rent"]
        .mul(12)
        .div(panel["median_resale_price"])
        .mul(100)
    )

    return panel.sort_values(
        COMMON_GROUPS
    )



def plot_cross_market_relationship(
    panel: pd.DataFrame,
) -> None:
    """Plot the pooled descriptive rental-resale relationship."""

    figure, axis = plt.subplots(
        figsize=(10, 7),
    )

    sns.regplot(
        data=panel,
        x="median_resale_price",
        y="median_monthly_rent",
        scatter_kws={
            "alpha": 0.25,
            "s": 20,
        },
        line_kws={
            "color": "#D55E00",
            "linewidth": 2,
        },
        ax=axis,
    )

    correlation = panel[
        [
            "median_resale_price",
            "median_monthly_rent",
        ]
    ].corr().iloc[0, 1]

    axis.set(
        title=(
            "Matched town / flat type / month observations\n"
            f"Pooled Pearson correlation: "
            f"{correlation:.3f}"
        ),
        xlabel="Median resale price (S$)",
        ylabel="Median monthly rent (S$)",
    )

    figure.suptitle(
        "Descriptive relationship between resale prices "
        "and rents\n"
        "Pooled and unadjusted across time, town and flat type"
    )
    figure.text(
        0.5,
        0.01,
        (
            "The fitted line describes association only; "
            "it is not a causal or within-segment estimate."
        ),
        ha="center",
        fontsize=9,
    )
    figure.tight_layout(
        rect=(0, 0.06, 1, 0.91)
    )

    save_figure(
        figure,
        "rental_resale_relationship.png",
    )

def build_yield_summary(
    panel: pd.DataFrame,
) -> pd.DataFrame:
    """Summarise the indicative gross yield proxy for 2025."""

    comparison = panel.loc[
        panel["calendar_year"].eq(COMPARISON_YEAR)
    ]

    return (
        comparison.groupby(
            [
                "town",
                "flat_type_normalised",
            ],
            as_index=False,
            observed=True,
        )
        .agg(
            median_monthly_rent=(
                "median_monthly_rent",
                "median",
            ),
            median_resale_price=(
                "median_resale_price",
                "median",
            ),
            indicative_gross_yield_pct=(
                "indicative_gross_yield_pct",
                "median",
            ),
            comparable_months=(
                "period",
                "nunique",
            ),
            rental_record_count=(
                "rental_record_count",
                "sum",
            ),
            resale_record_count=(
                "resale_record_count",
                "sum",
            ),
        )
        .sort_values(
            "indicative_gross_yield_pct",
            ascending=False,
        )
    )



def plot_yield_proxy(
    yield_summary: pd.DataFrame,
) -> None:
    """Plot the highest indicative gross-yield proxies."""

    eligible = yield_summary.loc[
        yield_summary["comparable_months"].ge(12)
    ].copy()

    top = eligible.head(15).copy()

    top["market_segment"] = (
        top["town"]
        + ", "
        + top["flat_type_normalised"]
    )

    top = top.sort_values(
        "indicative_gross_yield_pct"
    )

    figure, axis = plt.subplots(
        figsize=(11, 8),
    )

    sns.barplot(
        data=top,
        x="indicative_gross_yield_pct",
        y="market_segment",
        color="#56B4E9",
        ax=axis,
    )

    for container in axis.containers:
        axis.bar_label(
            container,
            fmt="%.2f%%",
            padding=3,
            fontsize=8,
        )

    axis.margins(x=0.12)

    axis.set(
        title=(
            "Segments with all 12 comparable months; "
            "descriptive proxy only"
        ),
        xlabel="Indicative annual gross yield proxy (%)",
        ylabel="Town and flat type",
    )

    figure.suptitle(
        f"Indicative HDB gross yield proxy: "
        f"{COMPARISON_YEAR}"
    )
    figure.text(
        0.5,
        0.01,
        (
            "Proxy excludes vacancy, expenses, financing, "
            "remaining lease and eligibility restrictions."
        ),
        ha="center",
        fontsize=9,
    )
    figure.tight_layout(
        rect=(0, 0.05, 1, 0.94)
    )

    save_figure(
        figure,
        "indicative_gross_yield_2025.png",
    )

def main() -> None:
    """Generate all reproducible EDA outputs."""

    FIGURE_DIRECTORY.mkdir(
        parents=True,
        exist_ok=True,
    )
    TABLE_DIRECTORY.mkdir(
        parents=True,
        exist_ok=True,
    )

    configure_plotting()

    rental = load_dataset(
        RENTAL_PATH,
        "approval_month",
        "rental",
    )
    resale = load_dataset(
        RESALE_PATH,
        "transaction_month",
        "resale",
    )

    rental_monthly = build_monthly_summary(
        rental,
        "monthly_rent",
        "median_monthly_rent",
    )
    resale_monthly = build_monthly_summary(
        resale,
        "resale_price",
        "median_resale_price",
    )

    save_table(
        rental_monthly,
        "rental_monthly_trend.csv",
    )
    save_table(
        resale_monthly,
        "resale_monthly_trend.csv",
    )
    plot_monthly_trends(
        rental_monthly,
        resale_monthly,
    )

    rental_flat_types = build_flat_type_summary(
        rental,
        "monthly_rent",
        "median_monthly_rent",
    )
    resale_flat_types = build_flat_type_summary(
        resale,
        "resale_price",
        "median_resale_price",
    )

    save_table(
        rental_flat_types,
        "rental_flat_type_monthly.csv",
    )
    save_table(
        resale_flat_types,
        "resale_flat_type_monthly.csv",
    )
    plot_flat_type_trends(
        rental_flat_types,
        resale_flat_types,
    )

    rental_towns = build_town_summary(
        rental,
        "monthly_rent",
        "median_monthly_rent",
    )
    resale_towns = build_town_summary(
        resale,
        "resale_price",
        "median_resale_price",
    )

    save_table(
        rental_towns,
        "rental_town_summary_2025.csv",
    )
    save_table(
        resale_towns,
        "resale_town_summary_2025.csv",
    )
    plot_town_comparisons(
        rental_towns,
        resale_towns,
    )

    rental_distance = build_distance_summary(
        rental,
        "monthly_rent",
        "median_monthly_rent",
    )
    resale_distance = build_distance_summary(
        resale,
        "resale_price",
        "median_resale_price",
    )

    save_table(
        rental_distance,
        "rental_train_distance_summary.csv",
    )
    save_table(
        resale_distance,
        "resale_train_distance_summary.csv",
    )
    plot_distance_comparisons(
        rental_distance,
        resale_distance,
    )

    cross_market_panel = build_cross_market_panel(
        rental,
        resale,
    )

    save_table(
        cross_market_panel,
        "cross_market_monthly_panel.csv",
    )
    plot_cross_market_relationship(
        cross_market_panel
    )

    yield_summary = build_yield_summary(
        cross_market_panel
    )

    save_table(
        yield_summary,
        "indicative_gross_yield_2025.csv",
    )
    plot_yield_proxy(yield_summary)

    print(
        "\nEDA generation completed successfully."
    )


if __name__ == "__main__":
    main()
