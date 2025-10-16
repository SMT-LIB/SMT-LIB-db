import sqlite3
import os
import polars as pl

pl.enable_string_cache()
from pathlib import Path
from functools import cache
import altair as alt
from flask import Flask, g, abort, render_template, request
from typing import *
from collections import defaultdict
from random import Random
import math
import sklearn

c_query = pl.col("id")
c_eval_name = pl.col("eval_name")
c_solver = pl.col("solver")
c_solver2 = pl.col("solver2")
c_ev_id = pl.col("ev_id")
c_ev_id2 = pl.col("ev_id2")
c_time = pl.col("time")
c_time2 = pl.col("time2")
c_status = pl.col("status")
c_status2 = pl.col("status2")
c_bucket = pl.col("bucket")
c_bucket2 = pl.col("bucket2")


@cache
def read_feather(DATABASE: Path) -> pl.DataFrame:
    FEATHER = DATABASE.with_suffix(".feather")
    if FEATHER.exists():
        return pl.read_ipc(FEATHER)
    else:
        print("Creation of cached feather file")
        db = sqlite3.connect(DATABASE)
        df = pl.read_database(
            query="""
                SELECT ev.name as eval_name, ev.date, ev.link, ev.id as ev_id, sol.name AS solver_name,
                        sovar.fullName, res.status, res.wallclockTime, res.cpuTime,
                        query.id, bench.logic, sovar.id AS sovar_id,
                        ev.wallclockLimit
                    FROM Results AS res
                    INNER JOIN Benchmarks AS bench ON bench.id = query.benchmark
                    INNER JOIN Queries AS query ON res.query = query.id
                    INNER JOIN Evaluations AS ev ON res.evaluation = ev.id
                    INNER JOIN SolverVariants AS sovar ON res.solverVariant = sovar.id
                    INNER JOIN Solvers AS sol ON sovar.solver = sol.id
                    """,
            connection=db,
            schema_overrides={
                "wallclockTime": pl.Float64,
                "cpuTime": pl.Float64,
                "wallclockTime": pl.Float64,
                "wallclockLimit": pl.Float64,
                "solver_name": pl.Categorical,
                "fullName": pl.Categorical,
                "sovar_id": pl.Int32,
                "status": pl.Categorical,
            },
        )
        df.write_ipc(FEATHER)
        return df


def list_logics(database):
    return list(read_feather(database)["logic"].unique())


def read_database(logic_name, database: Path) -> pl.LazyFrame:
    df = read_feather(database)
    results = df.lazy().filter((pl.col("logic") == pl.lit(logic_name)))
    return results


def compute_charts(
    logic_name,
    details_requested: bool,
    virtual_requested: bool,
    dist_too_few: float | None,
    min_common_benches: int,
    par4: bool = False,
    isomap_requested: bool = False,
    euclidean_requested: bool = False,
    database: Path | None = None,
):
    if database is None:
        database = Path(os.environ["SMTLIB_DB"])
    year = pl.col("date").str.split("-").list.first()
    solver_name = pl.concat_str(pl.col("solver_name"), year, separator=" ").cast(
        pl.Categorical
    )
    results = (
        read_database(logic_name, database)
        # Remove duplicated results
        .group_by("ev_id", "sovar_id", "id")
        .last()
        # .with_columns(
        #     solver=pl.concat_str(pl.col("fullName"), c_eval_name, separator=" ").cast(
        #         pl.Categorical
        #     ),
        #     # solver=pl.col("sovar_id")
        # )
        .select(
            c_query,
            c_ev_id,
            c_status,
            "solver_name",
            "date",
            time="wallclockTime",
            year=year,
        )
        .filter(c_time.is_not_null())
        .group_by(c_query, "solver_name", c_ev_id)
        .agg(time=c_time.median(), date=pl.col("date").first(), status=c_status.first())
        .with_columns(solver=solver_name, year=year)
    )

    # Add virtual best
    if virtual_requested:
        virtual_best = (
            results.group_by(c_query)
            .agg(c_time.min())
            .with_columns(
                solver_name=pl.lit("Virtual Best").cast(pl.Categorical),
                solver=pl.lit("Virtual Best").cast(pl.Categorical),
                ev_id=pl.lit(-1).cast(pl.Int64),
                status=pl.lit("unknown").cast(pl.Categorical),
                date=pl.lit("now"),
            )
            .select(c_query, c_solver, c_ev_id, c_time, c_status, "solver_name", "date")
        )
        results = pl.concat([results, virtual_best], how="vertical")

    if par4:
        results = results.with_columns(
            time=pl.when(c_status.is_in(["sat", "unsat"]))
            .then(c_time)
            .otherwise(pl.max_horizontal(c_time, pl.lit(60 * 20 * 2)))
        )

    # Computing the cross
    results_with = results.select(
        c_query,
        solver2=c_solver,
        ev_id2=c_ev_id,
        time2=c_time,
        status2=c_status,
    )

    cross_results = results.join(results_with, on=[c_query], how="inner")

    nb_common = (
        cross_results.group_by(
            c_solver,
            c_solver2,
        )
        .len()
        .sort("len")
    )

    toofew = pl.len() <= pl.lit(min_common_benches)

    nb_enough = (
        cross_results.group_by(c_solver, c_solver2)
        .agg(enough=toofew.not_())
        .group_by(c_solver)
        .agg(pl.col("enough").sum())
        .filter(pl.col("enough") >= (pl.len() / pl.lit(2)))
        .select(c_solver)
    )

    if dist_too_few is None:
        cross_results = cross_results.join(nb_enough, on="solver").join(
            nb_enough.rename({"solver": "solver2"}), on="solver2"
        )

    if euclidean_requested:
        cosine_dist = cross_results.group_by(
            c_solver,
            c_solver2,
        ).agg(
            # We divide by the number of elements to counter balance the different number of common benchmarks
            cosine=((((c_time - c_time2).pow(2).sum() / pl.len()).sqrt()))
        )
    else:
        den = (c_time * c_time).sum() * (c_time2 * c_time2).sum()
        cosine_dist = cross_results.group_by(
            c_solver,
            c_solver2,
        ).agg(
            cosine=pl.when(toofew)
            .then(pl.lit(dist_too_few))
            .when((den == pl.lit(0.0)))
            .then(pl.lit(0.0))
            .otherwise(pl.lit(1) - ((c_time * c_time2).sum() / den.sqrt()))
        )

    cross_results = (
        cross_results.group_by(
            c_solver,
            c_solver2,
            c_status,
            c_status2,
            c_bucket,
            c_bucket2,
        )
        .len()
        .sort(c_solver, c_solver2)
    )

    # coefficient from 0. to 1., 0. oldest to newest for each solver_name separately
    hist_coef = pl.arg_sort_by("date").over("solver_name") / pl.len().over(
        "solver_name"
    )
    results = (
        results.select(
            c_solver,
            "solver_name",
            "date",
            ratio_solved=(c_status.is_in(["sat", "unsat"]).sum() / pl.len()).over(
                "solver"
            ),
        )
        .unique()
        .sort("date", "solver_name", c_solver)
        .with_columns(hist_coef=hist_coef, year=year)
    )

    df_solvers, df_nb_common, df_cosine_dist, df_too_few, df_solver_name = (
        pl.collect_all(
            [
                # cross_results, #df_results
                results,
                nb_common,
                cosine_dist,
                results.join(nb_enough, on="solver", how="anti"),
                results.join(nb_enough, on="solver").select(pl.col("solver_name").unique().sort()),
            ],
            engine="streaming",
        )
    )
    
    # print(df_too_few)
    # print(df_nb_common.filter(pl.col("len") < 100))

    # bucket_domain: list[float] = list(df_buckets["bucket"])
    # status_domain: list[int] = list(df_status["status"])
    # status_domain.sort()

    solver_domain: list[str] = list(df_solvers["solver"])
    # solver_domain.sort(key=lambda x: x.lower())
    solver_names = list(df_solver_name["solver_name"])
    solver_names.sort(key=lambda x: x.lower())
    

    # df_all2 = df_all.pivot(on="id",index="solver")
    # imputer = sklearn.impute.KNNImputer(n_neighbors=2)
    # impute=imputer.fit_transform(df_all2.drop("solver"))
    df_cosine_dist2 = (
        df_cosine_dist.sort("solver", "solver2")
        .pivot(on="solver2", index="solver")
        .fill_null(1.0)
    )
    solvers_cosine = df_cosine_dist2.select("solver")
    list_solvers_cosine = list(solvers_cosine["solver"])
    df_cosine_dist2 = df_cosine_dist2.select("solver", *list_solvers_cosine)
    # print("df_cosine_dist2",df_cosine_dist2)
    df_cosine_dist2 = df_cosine_dist2.drop("solver")

    def isomap(components: List[str]) -> Tuple[pl.DataFrame, pl.DataFrame]:
        if isomap_requested:
            embedding = sklearn.manifold.Isomap(
                n_components=len(components),
                metric="precomputed",
                n_neighbors=min(10, len(list_solvers_cosine) - 1),
            )
        else:
            embedding = sklearn.manifold.MDS(
                n_components=len(components),
                dissimilarity="precomputed",
                random_state=42,
            )

        proj = embedding.fit_transform(df_cosine_dist2.to_numpy())

        if isomap_requested:
            dist_matrix = embedding.dist_matrix_
        else:
            dist_matrix = embedding.dissimilarity_matrix_

        df_corr = (
            pl.concat(
                [
                    pl.DataFrame(dist_matrix, schema=list_solvers_cosine),
                    solvers_cosine,
                ],
                how="horizontal",
            )
            .unpivot(index="solver", variable_name="solver2", value_name="corr")
            .with_columns(solver2=pl.col("solver2").cast(pl.Categorical))
        )
        # print(df_corr)
        df_proj = pl.DataFrame(
            proj, schema=[(c, pl.Float64) for c in components]
        ).with_columns(solvers_cosine)
        return df_proj, df_corr

    # df_proj,df_corr = isomap(["proj"])
    # df_proj = df_proj.sort("proj")
    # solver_domain = list(df_proj["solver"])

    df_proj, df_corr = isomap(["x", "y"])

    # print(df_corr.join(df_cosine_dist,on=["solver","solver2"]))

    df_proj = df_proj.join(df_solvers, on="solver")
    df_cosine_dist = df_cosine_dist.join(df_solvers, on="solver")
    df_corr = df_corr.join(df_solvers, on="solver")
    df_nb_common = df_nb_common.join(df_solvers, on="solver")
    # print("agglomeration")
    # model = sklearn.cluster.AgglomerativeClustering(distance_threshold=0, n_clusters=None).fit(impute)
    # solvers = list(df_all2["solver"])
    # n_samples = len(solvers)
    # for i, merge in enumerate(model.children_):
    #     print("id:",i+n_samples)
    #     for child_idx in merge:
    #         if child_idx < n_samples:
    #             print(solvers[child_idx])
    #         else:
    #             print(child_idx)

    # lle = sklearn.manifold.locally_linear_embedding(df_all)

    technic = "Isomap" if isomap_requested else "MDS"
    distance = "euclidean" if euclidean_requested else "cosine"

    # Create heatmap with selection
    sel_solver_name = alt.selection_point(
        fields=["solver_name"], name="solver_name", bind="legend"
    )
    g_select_provers = (
        alt.Chart(
            df_corr,
            title=f"smallest distance in neighborhood graph of {distance} distance",
        )
        .mark_rect()
        .encode(
            alt.X("solver", title="solver1").scale(domain=solver_domain),
            alt.Y("solver2", title="solver2").scale(
                domain=list(reversed(solver_domain))
            ),
            alt.Color("corr", scale=alt.Scale(scheme="lightmulti", reverse=True)),
            opacity=alt.when(sel_solver_name)
            .then(alt.value(1.0))
            .otherwise(alt.value(0.3)),
        )
        .add_params(sel_solver_name)
    )

    g_select_provers_cosine = (
        alt.Chart(
            df_cosine_dist,
            title=f"{distance} distance with (set to {dist_too_few} when less than {min_common_benches} common benchs)",
        )
        .mark_rect()
        .encode(
            alt.X("solver", title="solver1").scale(domain=solver_domain),
            alt.Y("solver2", title="solver2").scale(
                domain=list(reversed(solver_domain))
            ),
            alt.Color("cosine", scale=alt.Scale(scheme="lightmulti", reverse=True)),
            opacity=alt.when(sel_solver_name)
            .then(alt.value(1.0))
            .otherwise(alt.value(0.3)),
        )
        .add_params(sel_solver_name)
    )

    g_nb_common_benchs = (
        alt.Chart(df_nb_common, title="number of common benchs")
        .mark_rect()
        .encode(
            alt.X("solver", title="solver1").scale(domain=solver_domain),
            alt.Y("solver2", title="solver2").scale(
                domain=list(reversed(solver_domain))
            ),
            alt.Color(
                "len", scale=alt.Scale(scheme="lightmulti", reverse=True, type="log")
            ),
            opacity=alt.when(sel_solver_name)
            .then(alt.value(1.0))
            .otherwise(alt.value(0.3)),
        )
        .add_params(sel_solver_name)
    )

    show_trail = alt.param(bind=alt.binding_checkbox(name="Show trail "), value=True)

    base_isomap = (
        alt.Chart(
            df_proj,
            title=f"{technic} with {distance} for {logic_name}",
            width=500,
            height=500,
        )
        .encode(
            alt.X("x"),
            alt.Y("y"),
            alt.Tooltip("solver"),
            alt.Color("solver_name:N").scale(domain=list(solver_names)),
            alt.Shape("solver_name:N").scale(domain=list(solver_names)),
        )
        .add_params(sel_solver_name, show_trail)
    )
    max_ratio = df_proj["ratio_solved"].max()
    g_isomap = alt.layer(
        # Line layer
        base_isomap.mark_trail().encode(
            alt.Order("hist_coef:Q").sort("ascending"),
            alt.Size("hist_coef:Q")
            .scale(domain=[0.0, 1.0], range=[1, 12])
            .legend(None),
            color="solver_name:N",
            opacity=alt.when(sel_solver_name & show_trail)
            .then(alt.value(0.3))
            .otherwise(alt.value(0.0)),
        ),
        # Point layer
        base_isomap.mark_point(filled=True).encode(
            size=alt.value(100),
            #            alt.Size("ratio_solved:Q"),
            #            .scale(domain=[0.0, max_ratio], range=[2, 100]).legend(),
            opacity=alt.when(sel_solver_name)
            .then(alt.value(1.0))
            .otherwise(alt.value(0.3)),
        ),
    ).interactive()

    if details_requested:
        all = g_isomap | g_nb_common_benchs | g_select_provers_cosine | g_select_provers
    else:
        all = g_isomap

    return locals()
