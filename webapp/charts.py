import sqlite3
import os
import polars as pl
from pathlib import Path
from functools import cache
import polars_distance as pld
import altair as alt
from flask import Flask, g, abort, render_template, request
from typing import *
from collections import defaultdict
from random import Random
import math
import sklearn

U = TypeVar("U")


def correlation_sorting(
    solvers: List[U], corrs: Mapping[Tuple[U, U], float], nb_iteration: int
) -> None:
    """
    Strangely I can't find an easy to use lib creating a well clustered correlation matrix. block modelling.

    We use simulated annealing
    """
    if len(solvers) <= 2:
        return

    r = Random(0)

    def neighbor(i: int) -> float:
        s = 0.0
        n = 0.0
        for off in range(-4, 4):
            if off == 0:
                continue
            # Try to break the symmetry left-right
            if off > 0:
                bias = 0.1
            else:
                bias = 0.0
            if 0 <= i + off and i + off < len(solvers):
                coef = (1.0 + bias) / abs(off)
                s += (1.0 - corrs[solvers[i + off], solvers[i]]) * coef
                n += coef
        # At the bounds there is only one neighbor
        return s / n

    def swap(i: int, j: int) -> None:
        tmp = solvers[i]
        solvers[i] = solvers[j]
        solvers[j] = tmp

    for i in range(0, nb_iteration):
        # Differrent selection heuristics
        if False:
            a = r.randint(0, len(solvers) - 2)
            b = a + 1
        elif False:
            a = r.randint(0, len(solvers) - 1)
            b = r.randint(0, len(solvers) - 2)
            if a <= b:
                b += 1
        else:
            a = r.randint(0, len(solvers) - 2)
            b = r.randint(a + 1, len(solvers) - 1)
        s1 = neighbor(a) + neighbor(b)
        swap(a, b)
        s2 = neighbor(a) + neighbor(b)
        swap(a, b)
        t = 1 - (i / (nb_iteration + 1))
        if s2 < s1 or math.exp((s1 - s2) / t) > r.uniform(0.0, 1.0):
            swap(a, b)


c_query = pl.col("id")
c_eval_name = pl.col("eval_name")
c_solver = pl.col("solver")
c_solver2 = pl.col("solver2")
c_ev_id = pl.col("ev_id")
c_ev_id2 = pl.col("ev_id2")
c_cpuTime = pl.col("cpuTime")
c_cpuTime2 = pl.col("cpuTime2")
c_status = pl.col("status")
c_status2 = pl.col("status2")
c_bucket = pl.col("bucket")
c_bucket2 = pl.col("bucket2")

@cache
def read_feather() -> pl.DataFrame:
    DATABASE = Path(os.environ["SMTLIB_DB"])
    FEATHER = DATABASE.with_suffix(".feather")
    if FEATHER.exists():
        return pl.read_ipc(FEATHER)
    else:
        print("Creation of cached feather file")
        db = sqlite3.connect(DATABASE)
        df = pl.read_database(
            query="""
                SELECT ev.name as eval_name, ev.date, ev.link, ev.id as ev_id, sol.name AS solver_name,
                        sovar.fullName, res.status, res.cpuTime,
                        query.id, bench.logic, sovar.id AS sovar_id
                    FROM Results AS res
                    INNER JOIN Benchmarks AS bench ON bench.id = query.benchmark
                    INNER JOIN Queries AS query ON res.query = query.id
                    INNER JOIN Evaluations AS ev ON res.evaluation = ev.id
                    INNER JOIN SolverVariants AS sovar ON res.solverVariant = sovar.id
                    INNER JOIN Solvers AS sol ON sovar.solver = sol.id
                    """,
            connection=db,
            schema_overrides={"wallclockTime": pl.Float64, "cpuTime": pl.Float64, "solver_name": pl.Categorical, "fullName": pl.Categorical,"sovar_id" : pl.Int32, "status" : pl.Categorical},
        )
        df.write_ipc(FEATHER)
        return df


def init_routes(app, get_db):
    def read_database(logic_name) -> pl.LazyFrame:
        df = read_feather()
        results = (
            df.lazy()
            .filter(c_cpuTime.is_not_null() & (pl.col("logic") == pl.lit(logic_name))
            )
        )
        return results
    @app.route("/charts/<string:logic_name>")
    def show_charts(logic_name):
        details_requested = request.args.get('details', default = False, type = bool)
        virtual_requested = request.args.get('virtual', default = False, type = bool)
        dist_too_few = request.args.get('dist_too_few', default = None, type = (lambda x: None if x == "" else float(x)))
        min_common_benches = request.args.get('min_common_benches', default = 100, type = int)
        results = (
            read_database(logic_name)
            #Remove duplicated results
            .group_by("ev_id","sovar_id","id").last()
            .with_columns(
                solver=pl.concat_str(pl.col("fullName"), c_eval_name, separator=" ").cast(pl.Categorical),
                # solver=pl.col("sovar_id")
            )
        ).select(c_query,c_solver,c_ev_id,c_cpuTime,c_status,"solver_name","date")
        
        #Add virtual best
        if virtual_requested:
            virtual_best=results.group_by(c_query).agg(c_cpuTime.min()).with_columns(solver_name=pl.lit("Virtual Best").cast(pl.Categorical),solver=pl.lit("Virtual Best").cast(pl.Categorical),ev_id=pl.lit(-1).cast(pl.Int64),status=pl.lit("unknown").cast(pl.Categorical),date=pl.lit("now")).select(c_query,c_solver,c_ev_id,c_cpuTime,c_status,"solver_name","date")
            results = pl.concat([results,virtual_best],how="vertical")

        results_with = results.select(
            c_query,
            solver2=c_solver,
            ev_id2=c_ev_id,
            cpuTime2=c_cpuTime,
            status2=c_status,
        )

        cross_results = results.join(results_with, on=[c_query], how="inner")
        
        all = results.group_by(
                c_query,
                c_solver,
            ).agg(c_cpuTime.first())


        nb_common = (
            cross_results.group_by(
                c_solver,
                c_solver2,
            )
            .len()
            .sort("len")
        )

        den=((c_cpuTime*c_cpuTime).sum() * (c_cpuTime2*c_cpuTime2).sum())
        toofew=(pl.len() <= pl.lit(min_common_benches))
        
        nb_enough=(cross_results.group_by(
                c_solver,
                c_solver2
            ).agg(enough=toofew.not_()).group_by(c_solver).agg(pl.col("enough").sum())      
        .filter(pl.col("enough") >= (pl.len() / pl.lit(2)))
        )

        if dist_too_few is None:
            cross_results = cross_results.join(nb_enough,on="solver").join(nb_enough.rename({"solver":"solver2"}),on="solver2")

        cosine_dist = (
            cross_results.group_by(
                c_solver,
                c_solver2,
            )
            .agg(cosine=pl.when(toofew).then(pl.lit(dist_too_few)).when((den==pl.lit(0.))).then(pl.lit(0.)).otherwise(pl.lit(1) - ((c_cpuTime*c_cpuTime2).sum() / 
                         den.sqrt()))
        ))


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


        #coefficient from 0. to 1., 0. oldest to newest for each solver_name separately
        hist_coef = pl.arg_sort_by("date").over("solver_name") / pl.len().over("solver_name")
        results = results.select(c_solver,"solver_name","date").unique().sort("date","solver_name",c_solver).with_columns(hist_coef=hist_coef)

        df_solvers,df_nb_common,df_cosine_dist,df_too_few,df_solver_name= pl.collect_all(
            [
                # cross_results, #df_results
                results,
                nb_common,
                cosine_dist,
                results.join(nb_enough,on="solver",how="anti"),
                results.select(pl.col("solver_name").unique().sort())
            ],engine='streaming'
        )


        print(df_too_few)
        # print(df_nb_common.filter(pl.col("len") < 100))

        # bucket_domain: list[float] = list(df_buckets["bucket"])
        # status_domain: list[int] = list(df_status["status"])
        # status_domain.sort()

        solver_domain: list[str] = list(df_solvers["solver"])
        #solver_domain.sort(key=lambda x: x.lower())
        solver_names=df_solver_name["solver_name"]

        if False:
            # Two provers can have no benchmars in common, their pairs is not in df_corrs
            corrs: DefaultDict[Tuple[str, str], float] = defaultdict(lambda: 0.0)
            for row in df_corr.rows(named=False):
                corrs[row[0], row[1]] = row[2]
            correlation_sorting(solver_domain, corrs, 10000)
        else:
            # df_all2 = df_all.pivot(on="id",index="solver")
            # imputer = sklearn.impute.KNNImputer(n_neighbors=2)
            # impute=imputer.fit_transform(df_all2.drop("solver"))
            df_cosine_dist2 = df_cosine_dist.sort("solver","solver2").pivot(on="solver2",index="solver").fill_null(1.)
            solvers_cosine = df_cosine_dist2.select("solver")
            list_solvers_cosine = list(solvers_cosine["solver"])
            df_cosine_dist2 = df_cosine_dist2.select("solver",*list_solvers_cosine)
            # print("df_cosine_dist2",df_cosine_dist2)
            df_cosine_dist2 = df_cosine_dist2.drop("solver")
            def isomap(components:List[str]) -> Tuple[pl.DataFrame,pl.DataFrame]:
                embedding = sklearn.manifold.Isomap(n_components=len(components),metric="precomputed",n_neighbors=10)
                proj=embedding.fit_transform(df_cosine_dist2.to_numpy())
                df_corr = pl.concat([pl.DataFrame(embedding.dist_matrix_,schema=list_solvers_cosine),solvers_cosine],how = "horizontal").unpivot(index="solver",variable_name="solver2",value_name="corr").with_columns(solver2=pl.col("solver2").cast(pl.Categorical))
                # print(df_corr)
                df_proj=pl.DataFrame(proj,schema=[(c,pl.Float64) for c in components]).with_columns(solvers_cosine)
                return df_proj,df_corr
            
            # df_proj,df_corr = isomap(["proj"])
            # df_proj = df_proj.sort("proj")
            # solver_domain = list(df_proj["solver"])
            
            df_proj,df_corr = isomap(["x","y"])
            
            # print(df_corr.join(df_cosine_dist,on=["solver","solver2"]))
            
            df_proj=df_proj.join(df_solvers,on="solver")
            df_cosine_dist=df_cosine_dist.join(df_solvers,on="solver")
            df_corr=df_corr.join(df_solvers,on="solver")
            df_nb_common=df_nb_common.join(df_solvers,on="solver")
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


            #lle = sklearn.manifold.locally_linear_embedding(df_all)

        # Create heatmap with selection
        solver_name = alt.selection_point(
            fields=["solver_name"],
            name="solver_name"
            , bind='legend'
        )
        g_select_provers = (
            alt.Chart(df_corr, title="smallest distance in neighborhood graph of cosine distance")
            .mark_rect()
            .encode(
                alt.X("solver", title="solver1").scale(domain=solver_domain),
                alt.Y("solver2", title="solver2").scale(
                    domain=list(reversed(solver_domain))
                ),
                alt.Color("corr", scale=alt.Scale(scheme="lightmulti",reverse=True)),
                opacity=alt.when(solver_name).then(alt.value(1.)).otherwise(alt.value(0.3))
            )
            .add_params(solver_name)
        )

        g_select_provers_cosine = (
            alt.Chart(df_cosine_dist, title=f"cosine distance with (set to {dist_too_few} when less than {min_common_benches} common benchs)")
            .mark_rect()
            .encode(
                alt.X("solver", title="solver1").scale(domain=solver_domain),
                alt.Y("solver2", title="solver2").scale(
                    domain=list(reversed(solver_domain))
                ),
                alt.Color("cosine", scale=alt.Scale(scheme="lightmulti",reverse=True)),
                opacity=alt.when(solver_name).then(alt.value(1.)).otherwise(alt.value(0.3))
            )
            .add_params(solver_name)
        )

        g_nb_common_benchs= (
            alt.Chart(df_nb_common, title="number of common benchs")
            .mark_rect()
            .encode(
                alt.X("solver", title="solver1").scale(domain=solver_domain),
                alt.Y("solver2", title="solver2").scale(
                    domain=list(reversed(solver_domain))
                ),
                alt.Color("len", scale=alt.Scale(scheme="lightmulti",reverse=True,type="log")),
                opacity=alt.when(solver_name).then(alt.value(1.)).otherwise(alt.value(0.3))
            )
            .add_params(solver_name)
        )
        
        show_trail=alt.param(bind=alt.binding_checkbox(name="Show trail"),value=True)

        base_isomap=(
            alt.Chart(df_proj, title=f"Isomap for {logic_name}",width=500,height=500).encode(
                alt.X("x"),
                alt.Y("y"),
                alt.Tooltip("solver"),
                alt.Color("solver_name:N").scale(domain=solver_names),
                alt.Shape("solver_name:N").scale(domain=solver_names),
    )
            .add_params(solver_name,show_trail)
        )
        g_isomap = alt.layer(
            # Line layer
            base_isomap.mark_trail().encode(
            alt.Order('hist_coef:Q').sort('ascending'),
            alt.Size('hist_coef:Q').scale(domain=[0., 1.0], range=[1, 12]).legend(None),
            color="solver_name:N",
            opacity=alt.when(solver_name & show_trail).then(alt.value(0.3)).otherwise(alt.value(0.))
            ),
            # Point layer
            base_isomap.mark_point(filled=True).encode(opacity=alt.when(solver_name).then(alt.value(1.)).otherwise(alt.value(0.3))                                            
            )
        ).interactive()

        with alt.data_transformers.disable_max_rows():
            if details_requested:
                all = (g_isomap | g_nb_common_benchs| g_select_provers_cosine  | g_select_provers )
            else:
                all = g_isomap
            charts = all.to_html(fullhtml=False)
            
        return render_template(
            "charts.html",
            logicData=logic_name,
            printed="",
            charts=charts,
            inputs_value=locals(),
        )
