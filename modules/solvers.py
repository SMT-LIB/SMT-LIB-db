def setup_solvers(connection):
    create_tables(connection)
    populate_tables(connection)
    connection.commit()


def create_tables(connection):
    connection.execute(
        """CREATE TABLE Solvers(
        id INTEGER PRIMARY KEY,
        name TEXT,
        link TEXT);"""
    )

    # To distinguishe versions etc.
    connection.execute(
        """CREATE TABLE SolverVariants(
        id INTEGER PRIMARY KEY,
        fullName TEXT,
        solver INT,
        evaluation INT,
        FOREIGN KEY(solver) REFERENCES Solvers(id)
        FOREIGN KEY(evaluation) REFERENCES Evaluations(id)
        );"""
    )


# Canonical names of SMT solvers
known_solvers = [
    ("4Simp", ""),
    ("ABC", "https://dl.acm.org/doi/10.1007/978-3-642-14295-6_5"),
    ("Abziz", "https://mabdula.github.io/"),
    ("Algaroba", "https://github.com/uclid-org/algaroba"),
    ("Alt-Ergo", "https://alt-ergo.ocamlpro.com/"),
    ("Amaya", "https://github.com/MichalHe/amaya"),
    ("AProVE", "https://aprove.informatik.rwth-aachen.de/"),
    ("ARIO", "http://smtcomp.cs.uiowa.edu/2005/descriptions/ARIOintro.pdf"),
    ("Argo-Lib", "https://argo.matf.bg.ac.rs/?content=downloads"),
    ("Barcelogic", "https://www.cs.upc.edu/~oliveras/bclt-main.html"),
    ("BAT", "https://www.khoury.northeastern.edu/home/pete/bat/index.html"),
    ("Beaver", "https://doi.org/10.1007/978-3-642-02658-4_53"),
    ("Bitwuzla", "https://bitwuzla.github.io/"),
    (
        "Bitwuzla-MachBV",
        "https://github.com/Andeviking/Bitwuzla-MachBV-at-SMT-COMP-2025",
    ),
    ("Boolector", "https://boolector.github.io/"),
    (
        "Boolector-ReasonLS",
        "https://smt-comp.github.io/2019/system-descriptions/boolector-ReasonLS.pdf",
    ),
    (
        "BVDecide",
        "https://leanprover-community.github.io/mathlib4_docs/Lean/Elab/Tactic/BVDecide.html",
    ),
    ("clsat", "https://homepage.divms.uiowa.edu/~ajreynol/smt09.pdf"),
    ("COLIBRI", "https://colibri.frama-c.com/"),
    ("Colibri2", "https://colibri.frama-c.com/"),
    ("CryptoMiniSat", "https://www.msoos.org/cryptominisat5/"),
    ("Ctrl-Ergo", "https://gitlab.com/iguerNL/Ctrl-Ergo"),
    ("CVC", "https://doi.org/10.1007/3-540-45657-0_40"),
    ("CVC3", "https://cs.nyu.edu/acsys/cvc3/"),
    ("CVC4", "https://cvc4.github.io/"),
    ("cvc5", "https://cvc5.github.io/"),
    ("CVC Lite", "https://doi.org/10.1007/978-3-540-27813-9_49"),
    ("ExtSAT", "http://smtcomp.cs.uiowa.edu/2006/descriptions/extsat_description.pdf"),
    ("Fx7", "https://mmoskal.github.io/smt/en.html"),
    ("HTP", "https://doi.org/10.1007/11817963_42"),
    ("iProver", "https://gitlab.com/korovin/iprover"),
    ("Jat", ""),
    ("Kaluza", "https://doi.org/10.1109/SP.2010.38"),
    ("Kepler_22", "https://doi.org/10.1007/978-3-030-02768-1_19"),
    ("Kleaver", "https://klee-se.org/docs/kleaver-options/"),
    ("LazyBV2Int", "https://github.com/yoni206/lazybv2int"),
    ("MapleSTP", ""),
    ("MathSAT", "https://mathsat.fbk.eu/"),
    ("mc2", "https://github.com/c-cube/mc2"),
    ("MinkeyRink", "https://minkeyrink.com/"),
    ("MiniSmt", "http://cl-informatik.uibk.ac.at/software/minismt/"),
    ("Norn", "https://user.it.uu.se/~jarst116/norn/"),
    ("NRA-LS", "https://github.com/minghao-liu/NRA-LS"),
    ("NuSMV", "https://nusmv.fbk.eu/"),
    ("OpenSMT", "https://verify.inf.usi.ch/opensmt"),
    ("OSTRICH", "https://github.com/uuverifiers/ostrich"),
    ("Par4", "https://github.com/tjark/Par"),
    ("plat-smt", "https://github.com/dewert99/plat-smt"),
    ("ProB", "https://prob.hhu.de/w/index.php?title=Main_Page/"),
    ("Q3B", "https://github.com/martinjonas/Q3B/"),
    ("Q3B-pBNN", "https://www.fi.muni.cz/~xpavlik5/Q3B-pBDD/"),
    ("raSAT", ""),
    ("Redlog", "https://redlog.eu/"),
    ("S3P", "https://trinhmt.github.io/home/S3/"),
    ("Sammy", "http://combination.cs.uiowa.edu/Sammy/"),
    ("Sateen", "http://smtcomp.cs.uiowa.edu/2005/descriptions/sateen.pdf"),
    ("SBT", ""),
    ("Simplics", "https://fm.csl.sri.com/simplics/index.shtml"),
    ("SLENT", "https://github.com/NTU-ALComLab/SLENT"),
    ("SMTInterpol", "https://ultimate.informatik.uni-freiburg.de/smtinterpol"),
    ("SMT-RAT", "https://smtrat.github.io/"),
    ("solmt", "https://github.com/ethereum/solidity/"),
    (
        "SPASS-IQ",
        "https://www.mpi-inf.mpg.de/de/departments/automation-of-logic/software/spass-workbench/spass-iq",
    ),
    ("SONOLAR", "https://www.informatik.uni-bremen.de/agbs/florian/sonolar/"),
    (
        "SPASS-SAT",
        "https://www.mpi-inf.mpg.de/departments/automation-of-logic/software/spass-workbench/spass-satt/",
    ),
    ("Spear", "https://slebok.github.io/proverb/spear.html"),
    ("STP", "https://stp.github.io/"),
    (
        "SVC",
        "https://web.archive.org/web/20050313143635/http://chicory.stanford.edu/SVC/",
    ),
    ("SWORD", "https://www.dm.tzi.de/s_sword.php?lang=en"),
    (
        "Tiffany de Wintermonte",
        "https://smt-comp.github.io/2012/system-descriptions/TDW.pdf",
    ),
    ("Toysmt", "https://github.com/msakai/toysolver/"),
    ("Trau", "https://github.com/diepbp/Trau"),
    (
        "UltimateEliminator",
        "https://ultimate.informatik.uni-freiburg.de/eliminator/",
    ),
    ("Vampire", "https://vprover.github.io/"),
    ("veriT", "https://verit-solver.org/"),
    ("Woorpje", "https://www.informatik.uni-kiel.de/~mku/woorpje/"),
    ("XSat", "https://github.com/zhoulaifu/xsat"),
    ("Yaga", "https://d3s.mff.cuni.cz/software/yaga/"),
    ("Yices2", "https://yices.csl.sri.com/"),
    ("Yices", "https://yices.csl.sri.com/old/yices1-documentation.html"),
    ("Yices-ismt", "https://github.com/MRVAPOR/Yices-ismt"),
    ("YicesLS", "https://smt-comp.github.io/2021/system-descriptions/YicesLS.pdf"),
    ("YicesQS", "https://github.com/disteph/yicesQS"),
    ("Z3alpha", "https://github.com/JohnLyu2/z3alpha"),
    ("Z3++BV", "https://z3-plus-plus.github.io/"),
    ("Z3", "https://github.com/Z3Prover/z3"),
    ("Z3++", "https://z3-plus-plus.github.io/"),
    ("Z3-Noodler", "https://github.com/VeriFIT/z3-noodler"),
    ("Z3-Noodler-Mocha", "https://github.com/Bazoka13/Z3-Noodler-Mocha"),
    ("Z3-Owl", "https://z3-owl.github.io/"),
    ("z3siri", "https://github.com/SoftWiser-group/SiriSMT"),
    ("Z3string", "https://z3string.github.io/"),
    ("Z3-Trau", "https://github.com/diepbp/z3-trau"),
]

solver_count = 1
solver_table = []

# Lists solver variants that are not in scope of a comptetition.
# E.g., those used as "Target Solver"
global_solver_variants = {
    "Barcelogic": ["barcelogic"],
    "Bitwuzla": ["Bitwuzla-wrapped", "bitwuzla", "Bitwuzla (with SymFPU)"],
    "Boolector": ["boolector"],
    "CryptoMiniSat": ["CryptoMinisat"],
    "CVC4": ["CVC4 (with SymFPU)", "cvc4"],
    "cvc5": ["CVC5"],
    "MathSAT": ["Mathsat5", "MathSAT5", "Mathsat"],
    "OSTRICH": ["Ostrich"],
    "Vampire": ["vampire"],
    "Yices2": ["yices2", "Yices 2"],
    "Z3": ["z3", "z3;"],
    "Z3string": ["Z3str2", "Z3-str2", "Z3str3", "Z3-str3", "Z3str4", "Z3str3RE"],
    "Woorpje": ["WOORPJE"],
    "Yices": ["YICES", "yices"],
}

evaluation_solver_variants = {
    "SMT-COMP 2005": [
        ("ARIO", ["Ario"]),
        ("Barcelogic", ["BarcelogicTools"]),
        ("CVC", ["CVC"]),
        ("CVC Lite", ["CVC Lite"]),
        ("HTP", ["HTP"]),
        ("MathSAT", ["MathSat"]),
        ("Sammy", ["Sammy"]),
        ("Sateen", ["Sateen"]),
        ("SBT", ["SBT"]),
        ("Simplics", ["Simplics"]),
        ("SVC", ["SVC"]),
        ("Yices", ["Yices"]),
    ],
    "SMT-COMP 2006": [
        ("ARIO", ["Ario 1.2"]),
        ("Barcelogic", ["Barcelogic 1.1", "Barcelogic 1.0 (2005 winner)"]),
        ("BAT", ["Bat (hors-concours)"]),
        ("CVC", ["CVC"]),
        ("CVC3", ["CVC3"]),
        ("ExtSAT", ["ExtSAT", "ExtSAT 1.1"]),
        ("HTP", ["HTP", "HTP patched (hors-concours)"]),
        ("Jat", ["Jat"]),
        ("MathSAT", ["MathSAT 3.4"]),
        ("NuSMV", ["NuSMV"]),
        ("Sateen", ["Sateen"]),
        ("Simplics", ["Simplics (2005 winner)"]),
        ("STP", ["STP"]),
        ("Yices", ["Yices 1.0", "Yices 0.1 (2005 winner)"]),
    ],
    # For SMTExec years we don't ignore solvers that got patches, since
    # th fixed versions did not run on all divisions.
    "SMT-COMP 2007": [
        ("Argo-Lib", ["ArgoLib v3.5"]),
        ("Barcelogic", ["Barcelogic 1.2"]),
        ("CVC3", ["CVC3 1.2", "CVC3 1.2 (patched)", "CVC3 (2006)"]),
        ("Fx7", ["Fx7"]),
        ("MathSAT", ["MathSAT 4.0"]),
        ("Sateen", ["Sateen"]),
        ("Spear", ["Spear v1.9 (fh-1-2)", "Spear v1.9 (sw-v)"]),
        ("Yices", ["Yices 1.0", "Yices 1.0.10"]),
        ("Z3", ["Z3 0.1", "Z3 0.1 (fixed BV)"]),
    ],
    "SMT-COMP 2008": [
        ("Alt-Ergo", ["Alt-Ergo", "Alt-Ergo (revised)"]),
        ("Barcelogic", ["Barcelogic 1.3"]),
        ("Beaver", ["Beaver-1.0"]),
        ("Boolector", ["Boolector"]),
        ("clsat", ["clsat 0.17f"]),
        ("CVC3", ["CVC3 1.2", "CVC3-1.5"]),
        ("MathSAT", ["MathSAT-4.2"]),
        ("OpenSMT", ["OpenSMT 0.1"]),
        ("Sateen", ["sateen-2.1.1"]),
        ("Spear", ["Spear", "Spear v1.9 (fh-1-2)"]),
        ("SWORD", ["SWORD v0.2"]),
        ("Yices", ["Yices 1.0.10"]),
        ("Yices2", ["Yices2 (proto c)"]),
        ("Z3", ["Z3 0.1", "Z3.2"]),
    ],
    "SMT-COMP 2009": [
        ("Barcelogic", ["Barcelogic 1.3", "barcelogic-QF_NIA"]),
        ("Beaver", ["beaver-smtcomp-2009"]),
        ("Boolector", ["Boolector", "Boolector 1.2"]),
        ("clsat", ["clsat 1.0"]),
        ("CVC3", ["CVC3 2.0"]),
        ("MathSAT", ["MathSAT 4.3", "MathSAT 4.3 (revised)"]),
        ("OpenSMT", ["OpenSMT 0.2"]),
        ("Saten", ["Sateen-3.5"]),
        ("STP", ["STP #101"]),
        ("SWORD", ["sword-1.0"]),
        ("veriT", ["veriT 200907"]),
        ("Yices2", ["Yices 2 proto", "Yices2 (proto c)"]),
        ("Z3", ["Z3.2"]),
    ],
    "SMT-COMP 2010": [
        ("AProVE", ["AProVE NIA 0.2.1"]),
        ("Barcelogic", ["Barcelogic 1.3", "barcelogic-QF_NIA"]),
        ("Boolector", ["Boolector 1.2"]),
        ("CVC3", ["CVC3 2.0", "CVC3 2.3"]),
        ("CVC4", ["CVC4 1.0a0"]),
        ("MathSAT", ["MathSAT 4.3" "MathSAT 5"]),
        ("MiniSmt", ["MiniSmt"]),
        ("OpenSMT", ["OpenSMT-1.0-alpha"]),
        ("Sateen", ["Sateen-3.5"]),
        ("STP", ["simplifyingSTP"]),
        ("SONOLAR", ["SONOLAR r252"]),
        ("veriT", ["veriT 201007"]),
        ("Yices2", ["Yices 2 proto", "Yices2 (proto c)"]),
        ("Z3", ["Z3.2"]),
    ],
    "SMT-COMP 2011": [
        ("AProVE", ["AProVE NIA 0.3"]),
        ("Boolector", ["Boolector 1.5.23-833"]),
        ("CVC3", ["CVC3 v2.4"]),
        ("CVC4", ["CVC4 1.0rc.2026"]),
        ("MathSAT", ["MathSAT 5", "MathSAT5"]),
        ("MiniSmt", ["MiniSmt"]),
        ("OpenSMT", ["opensmt", "OpenSMT-1.0-alpha"]),
        ("STP", ["simplifyingSTP", "STP2"]),
        ("SMTInterpol", ["SMTInterpol 2.0pre"]),
        ("Yices2", ["smtlib2parser+Yices 1.0.29"]),  # TODO: Is this yices 2
        ("SONOLAR", ["SONOLAR"]),
        ("veriT", ["veriT"]),
        ("Z3", ["Z3"]),
    ],
    "SMT-COMP 2012": [
        ("4Simp", ["4Simp"]),
        ("Abziz", ["AbzizPortfolio+BOOLECTOR+MATHSAT+SONOLAR+STP2+Z3_6"]),
        ("Boolector", ["Boolector", "Boolector 1.5.23-833"]),
        ("CVC3", ["CVC3 v2.4", "CVC3 v2.4.2"]),
        ("CVC3", ["CVC4 1.0rc.3931", "CVC4 1.0rc.3970"]),
        ("MathSAT", ["MathSAT 5" "MathSAT5-smtcomp12", "MathSAT-HeavyBV"]),
        ("SMTInterpol", ["SMTInterpol"]),
        ("SONOLAR", ["SONOLAR"]),
        ("STP2", ["STP2"]),
        ("Tiffany de Wintermonte", ["Tiffany de Wintermonte & Sonolar"]),
        ("Z3", ["Z3"]),
    ],
    "SMT Evaluation 2013": [
        ("4Simp", ["4Simp-SMT-COMP-2012 default"]),
        (
            "Abziz",
            [
                "abziz_portfolio_2011_minfeatures_2 default",
                "abziz_portfolio_2011_solvers_2 default",
                "abziz_portfolio_2012_minfeatures default",
                "abziz_portfolio_2012_solvers default",
                "AbzizPortfolio-SMT-COMP-2012 default",
            ],
        ),
        (
            "AProVE",
            ["AProVE-NIA-SMT-COMP-2010 default", "AProVE-NIA-SMT-COMP-2011 default"],
        ),
        (
            "Boolector",
            [
                "Boolector-1.5.118-SMT-EVAL-2013 default",
                "Boolector-SMT-COMP-2011 default",
                "Boolector-SMT-COMP-2012 default",
            ],
        ),
        (
            "CVC3",
            [
                "CVC3-SMT-COMP-2010 default",
                "CVC3-SMT-COMP-2011 default",
                "CVC3-SMT-COMP-2012 default",
            ],
        ),
        (
            "CVC4",
            [
                "CVC4-SMT-COMP-2010 default",
                "CVC4-SMT-COMP-2011 default",
                "CVC4-SMT-COMP-2012-Resubmission default",
                "CVC4-SMT-EVAL-2013 default",
            ],
        ),
        (
            "MathSAT",
            [
                "MathSAT5-5.2.6-SMT-EVAL-2013 default",
                "MathSAT5-HeavyBV-SMT-COMP-2012 default",
                "MathSAT5-SMT-COMP-2010 default",
                "MathSAT5-SMT-COMP-2011 default",
                "MathSAT5-SMT-COMP-2012 default",
                "test_pmathsat-SMT-COMP-2010 default",
            ],
        ),
        (
            "MiniSmt",
            ["MiniSMT-0.5-SMT-EVAL-2013 default", "MiniSMT-SMT-COMP-2010 default"],
        ),
        (
            "OpenSMT",
            [
                "OpenSMT-SMT-COMP-2010 default",
                "OpenSMT-SMT-COMP-2011 default",
                "OpenSMT-SMT-EVAL-2013 default",
            ],
        ),
        (
            "SMTInterpol",
            [
                "SMTInterpol-2.0r8402-SMT-EVAL-2013 default",
                "SMTInterpol-SMT-COMP-2011 default",
                "SMTInterpol-SMT-COMP-2012 default",
            ],
        ),
        (
            "SONOLAR",
            [
                "SONOLAR-2013-05-15-SMT-EVAL-2013 default",
                "SONOLAR-SMT-COMP-2010 default",
                "SONOLAR-SMT-COMP-2011 default",
                "SONOLAR-SMT-COMP-2012 default",
            ],
        ),
        (
            "STP",
            [
                "STP2-SMT-COMP-2011 default",
                "STP2-SMT-COMP-2012 default",
                "simplifyingSTP-SMT-COMP-2010 default",
            ],
        ),
        ("Tiffany de Wintermonte", ["TdW-SMT-COMP-2012 default"]),
        (
            "veriT",
            [
                "veriT-SMT-COMP-2010 default",
                "veriT-SMT-COMP-2011 default",
                "veriT-SMT-EVAL-2013 default",
            ],
        ),
        (
            "Z3",
            [
                "Z3-4.3.2.a054b099c1d6-x64-debian-6.0.6-SMT-EVAL-2013 default",
                "Z3-SMT-COMP-2011 default",
            ],
        ),
    ],
    "SMT-COMP 2014": [
        ("4Simp", ["4Simp - 2014 default"]),
        (
            "Abziz",
            [
                "abziz_portfolio_all_features default",
                "abziz_portfolio_min_features default",
            ],
        ),
        ("AProVE", ["AProVE NIA 2014 default"]),
        (
            "Boolector",
            ["Boolector boolector", "Boolector boolectord", "Boolector boolectorj"],
        ),
        ("CVC3", ["CVC3 default"]),
        # Inconsistency: there is also a "fixed resubmission" version
        ("CVC4", ["CVC4 f7118b2 default"]),
        (
            "Kleaver",
            [
                "Kleaver-indie-more-typed kleaver_indie_1",
                "Kleaver-indie-more-typed kleaver_portfolio",
            ],
        ),
        ("MathSAT", ["MathSAT-5.2.12-Main default"]),
        # Inconsitency: the participant page claims a "14b" verison was used.
        ("OpenSMT", ["opensmt2-2014-06-14c default"]),
        ("raSAT", ["raSAT-main-track-final default.sh"]),
        ("SMTInterpol", ["smtinterpol-2.1-118-g3dada2f default"]),
        ("SONOLAR", ["sonolar_smtcomp-2014 default"]),
        ("STP", ["stp-cryptominisat4 default"]),
        ("veriT", ["veriT-smtcomp2014 default"]),
        ("Yices2", ["Yices-2.2.1-smtcomp2014 default"]),
        ("Z3", ["Z3-4.3.2.a054b099c1d6-x64-debian-6.0.6-SMT-COMP-2014 default"]),
    ],
    "SMT-COMP 2015": [
        ("AProVE", ["AProVE NIA 2014 default"]),
        (
            "Boolector",
            [
                "Boolector SMT15 QF_BV final boolector_qf_bv",
                "Boolector SMT15 QF_AUFBV final boolector_qf_aufbv",
            ],
        ),
        ("CVC3", ["CVC3 default"]),
        (
            "CVC4",
            [
                "CVC4-master-2015-06-15-9b32405-main default",
                "CVC4-experimental-2015-06-15-ff5745a-main default",
            ],
        ),
        ("MathSAT", ["MathSat 5.3.6 main smtcomp2015_main"]),
        ("OpenSMT", ["OpenSMT2 default", "OpenSMT2-parallel default"]),
        ("raSAT", ["raSAT default.sh"]),
        ("SMT-RAT", ["SMT-RAT-final default", "SMT-RAT-NIA-Parallel-final default"]),
        ("SMTInterpol", ["SMTInterpol v2.1-206-g86e9531 default"]),
        (
            "STP",
            [
                "stp-cryptominisat4 default",
                "stp-cmsat4-v15 default",
                "stp-cmsat4-mt-v15 default",
                "stp-minisat-v15 default",
            ],
        ),
        ("veriT", ["veriT default"]),
        ("Yices2", ["Yices default", "Yices2-NL default"]),
        ("Z3", ["Z3-unstable default", "z3-ijcar14 z3-ijcar14", "z3 4.4.0 default"]),
    ],
    "SMT-COMP 2016": [
        ("ABC", ["ABC_default default_abc", "ABC_glucose glucose"]),
        ("AProVE", ["AProVE NIA 2014 default"]),
        ("Boolector", ["Boolector boolector", "Boolector preprop boolector"]),
        ("CVC4", ["CVC4-master-2016-05-27-cfef263-main default"]),
        ("MapleSTP", ["MapleSTP default", "MapleSTP-mt default"]),
        ("MathSAT", ["mathsat-5.3.11-linux-x86_64-Main default"]),
        ("MinkeyRink", ["Minkeyrink  2016 default"]),
        ("OpenSMT", ["OpenSMT2-2016-05-12 default"]),
        ("ProB", ["ProB competition"]),
        ("Q3B", ["Q3B default"]),
        ("raSAT", ["raSAT 0.3 default.sh", "raSAT 0.4 exp - final default.py"]),
        ("SMTInterpol", ["smtinterpol-2.1-258-g92ab3df default"]),
        ("SMT-RAT", ["SMT-RAT default"]),
        (
            "STP",
            [
                "stp-cms-exp-2016 default",
                "stp-cms-mt-2016 default",
                "stp-cms-st-2016 default",
                "stp-minisat-st-2016 default",
            ],
        ),
        ("Toysmt", ["toysmt default"]),
        (
            "Vampire",
            [
                "vampire_smt_4.1 vampire_smtcomp",
                "vampire_smt_4.1_parallel vampire_smtcomp",
            ],
        ),
        ("veriT", ["veriT-dev default"]),
        ("Yices2", ["Yices-2.4.2 default"]),
        ("Z3", ["z3-4.4.1 default"]),
    ],
    "SMT-COMP 2017": [
        ("AProVE", ["AProVE NIA 2014 default"]),
        (
            "Boolector",
            [
                "Boolector+CaDiCaL SMT17 final boolector",
                "Boolector SMT17 final boolector",
            ],
        ),
        ("COLIBRI", ["COLIBRI 18_06_2017 105a81 default"]),
        ("CVC4", ["CVC4-smtcomp2017-main default"]),
        ("MathSAT", ["mathsat-5.4.1-linux-x86_64-Main default"]),
        ("MinkeyRink", ["MinkeyRink 2017.3a default"]),
        ("OpenSMT", ["opensmt2-2017-06-04 default"]),
        ("Q3B", ["Q3B default"]),
        ("Redlog", ["Redlog default"]),
        ("SMTInterpol", ["SMTInterpol default"]),
        ("SMT-RAT", ["SMTRAT-comp2017_2 default"]),
        ("STP", ["stp_st default", "stp_mt default"]),
        ("Vampire", ["vampire4.2-smt vampire"]),
        (
            "veriT",
            [
                "veriT-2017-06-17 default",
                "veriT+raSAT+Redlog default",
                "veriT+Redlog_20170618 default",
            ],
        ),
        ("XSat", ["xsat-smt-comp-2017 default"]),
        ("Yices2", ["Yices2-Main default"]),
        ("Z3", ["z3-4.5.0 default"]),
    ],
    "SMT-COMP 2018": [
        ("Alt-Ergo", ["Alt-Ergo-SMTComp-2018_default"]),
        ("AProVE", ["AProVE NIA 2014_default"]),
        ("Boolector", ["Boolector_default"]),
        ("COLIBRI", ["COLIBRI 10_06_18 v2038_default"]),
        ("Ctrl-Ergo", ["Ctrl-Ergo-SMTComp-2018_default"]),
        # What is this `master-...` version of CVC4? It appears with solver
        # id "19775" on StarExec.  However, it is not listed as a particiapant,
        # but is listed as 2018-CVC4 in 2019.
        (
            "CVC4",
            [
                "CVC4-experimental-idl-2_default",
                "master-2018-06-10-b19c840-competition-default_default",
            ],
        ),
        ("MathSAT", ["mathsat-5.5.2-linux-x86_64-Main_default"]),
        ("MinkeyRink", ["Minkeyrink MT_mt", "Minkeyrink ST_st"]),
        ("OpenSMT", ["opensmt2_default"]),
        ("Q3B", ["Q3B_default"]),
        ("SMTInterpol", ["SMTInterpol-2.5-19-g0d39cdee_default"]),
        ("SMT-RAT", ["SMTRAT-Rat-final_default", "SMTRAT-MCSAT-final_default"]),
        ("SPASS-SATT", ["SPASS-SATT_default"]),
        (
            "STP",
            [
                "STP-CMS-st-2018_default-no-stderr",
                "STP-CMS-mt-2018_multicore-no-stderr",
                "STP-Riss-st-2018_riss-no-stderr",
            ],
        ),
        ("Vampire", ["vampire-4.3-smt_vampire_smtcomp"]),
        ("veriT", ["veriT_default", "veriT+raSAT+Reduce_default"]),
        ("Yices2", ["Yices 2.6.0_default"]),
        ("Z3", ["z3-4.7.1_default"]),
    ],
    "SMT-COMP 2019": [
        ("Alt-Ergo", ["Alt-Ergo-SMTComp-2019-wrapped-sq_default"]),
        ("AProVE", ["AProVE NIA 2014-wrapped-sq_default"]),
        (
            "Boolector",
            [
                "Boolector-wrapped-sq_default",
                "Poolector-wrapped-sq_default",
                "Boolector___default",
                "Boolector incremental-wrapped-inc___default",
            ],
        ),
        (
            "Boolector-ReasonLS",
            [
                "boolector-ReasonLS-wrapped-sq_default",
                "Boolector-ReasonLS-wrapped-inc___default",
            ],
        ),
        ("COLIBRI", ["colibri 2176-fixed-config-file-wrapped-sq_default"]),
        ("Ctrl-Ergo", ["Ctrl-Ergo-2019-wrapped-sq_default"]),
        (
            "CVC4",
            [
                "CVC4-2019-06-03-d350fe1-wrapped-sq_default",
                "CVC4-SymBreak_03_06_2019-wrapped-sq_default",
                "master-2018-06-10-b19c840-competition-default_default",
                "CVC4___default",
                "CVC4-inc-2019-06-03-d350fe1-wrapped-inc___default",
                "CVC4-inc-fixed-2019-06-26-0e351fa-wrapped-inc___default",
            ],
        ),
        (
            "MathSAT",
            [
                "mathsat-20190601-wrapped-sq_default",
                "mathsat-na-20190601-wrapped-sq_default",
                "MathSAT___default",
                "MathSAT-na-wrapped-inc___default",
                "MathSAT-wrapped-inc___default",
            ],
        ),
        (
            "MinkeyRink",
            [
                "MinkeyRink MT-wrapped-sq_default",
                "MinkeyRink ST-wrapped-sq_default",
                "MinkeyRink MT-wrapped-inc___default",
                "MinkeyRink ST-wrapped-inc___default",
            ],
        ),
        ("OpenSMT", ["OpenSMT-wrapped-sq_default"]),
        ("Par4", ["Par4-wrapped-sq_default"]),
        ("ProB", ["ProB-wrapped-sq_default"]),
        (
            "Q3B",
            [
                "Q3B-wrapped-sq_default",
                "Q3B-wrapped-inc___default",
            ],
        ),
        (
            "SMTInterpol",
            [
                "smtinterpol-2.5-514-wrapped-sq_default",
                "smtinterpol-2.5-514-wrapped-inc___default",
            ],
        ),
        (
            "SMT-RAT",
            [
                "SMTRAT-5-wrapped-sq_default",
                "SMTRAT-MCSAT-4-wrapped-sq_default",
                "SMTRAT-Rat-final_default",
            ],
        ),
        ("SPASS-SATT", ["SPASS-SATT-wrapped-sq_default"]),
        (
            "STP",
            [
                "STP-2019-wrapped-sq_default",
                "stp-mergesat-fixed-wrapped-sq_default",
                "stp-minisat-wrapped-sq_default",
                "stp-mt-wrapped-sq_default",
                "stp-portfolio-fixed-wrapped-sq_default",
                "stp-riss-wrapped-sq_default",
                "stp-incremental-2019-v2-wrapped-inc___default",
                "stp-mt-wrapped-inc___default",
            ],
        ),
        (
            "UltimateEliminator",
            [
                "UltimateEliminator+MathSAT-5.5.4-wrapped-sq_default",
                "UltimateEliminator+SMTInterpol-wrapped-sq_default",
                "UltimateEliminator+Yices-2.6.1-wrapped-sq_default",
                "UltimateEliminator+MathSAT-5.5.4-wrapped-inc___default",
                "UltimateEliminator+SMTInterpol-wrapped-inc___default",
                "UltimateEliminator+Yices-2.6.1-wrapped-inc___default",
            ],
        ),
        (
            "Vampire",
            [
                "vampire-4.4-smtcomp-wrapped-sq_default",
                "vampire-4.3-smt_vampire_smtcomp",
            ],
        ),
        (
            "veriT",
            ["veriT-wrapped-sq_default", "veriT+raSAT+Redlog-wrapped-sq_default"],
        ),
        (
            "Yices2",
            [
                "Yices 2.6.0_default",
                "Yices 2.6.2-wrapped-sq_default",
                "Yices 2.6.2 Cadical-wrapped-sq_default",
                "Yices 2.6.2 Cryptominisat-wrapped-sq_default",
                "Yices 2.6.2 MCSAT BV-wrapped-sq_default",
                "Yices 2.6.2 new bvsolver-wrapped-sq_default",
                "Yices 2.6.2 Incremental-wrapped-inc___default",
                "Yices___default",
            ],
        ),
        ("Z3", ["z3-4.8.4-d6df51951f4c-wrapped-sq_default", "z3-4.7.1_default"]),
    ],
    "SMT-COMP 2020": [
        ("Alt-Ergo", ["Alt-Ergo-SMTComp-2020_default"]),
        ("AProVE", ["AProVE NIA 2014_default"]),
        (
            "Bitwuzla",
            [
                "Bitwuzla-fixed_default",
                "Bitwuzla-fixed-wrapped-inc___default",
            ],
        ),
        (
            "Boolector",
            [
                "Boolector-wrapped-sq_default",
                "Poolector-wrapped-sq_default",
                "Boolector___default",
            ],
        ),
        ("COLIBRI", ["COLIBRI 20.5.25_default"]),
        (
            "CVC4",
            [
                "CVC4-sq-final_default",
                "master-2018-06-10-b19c840-competition-default_default",
                "CVC4-2019-06-03-d350fe1-wrapped-sq_default",
                "CVC4___default",
                "CVC4-inc-2019-06-03-d350fe1-wrapped-inc___default",
                "CVC4-inc-final-wrapped-inc___default",
            ],
        ),
        (
            "LazyBV2Int",
            [
                "LazyBV2Int20200523_default.sh",
                "LazyBV2Int20200523-wrapped-inc___default",
            ],
        ),
        (
            "MathSAT",
            [
                "MathSAT5_default.sh",
                "mathsat-20190601-wrapped-sq_default",
                "MathSAT5-wrapped-inc___default",
                "MathSAT___default",
                "MathSAT-na-wrapped-inc___default",
                "MathSAT-wrapped-inc___default",
            ],
        ),
        (
            "MinkeyRink",
            ["MinkeyRink Solver 2020.3.1_default", "MinkeyRink Solver 2020.3_default"],
        ),
        ("OpenSMT", ["OpenSMT_default", "OpenSMT-wrapped-inc___default"]),
        ("Par4", ["Par4-wrapped-sq_default"]),
        (
            "SMTInterpol",
            [
                "smtinterpol-2.5-679-gacfde87a_default",
                "smtinterpol-2.5-679-gacfde87a-wrapped-inc___default",
            ],
        ),
        (
            "SMT-RAT",
            [
                "smtrat-SMTCOMP_default",
                "smtrat-CDCAC_default",
                "smtrat-MCSAT_default",
                "SMTRAT-Rat-final_default",
            ],
        ),
        ("SPASS-SATT", ["SPASS-SATT-wrapped-sq_default"]),
        (
            "STP",
            [
                "STP_default",
                "STP ++ Mergsat v1_default",
                "STP ++ Mergsat v1-wrapped-inc-fixed___default",
                "STP-wrapped-inc___default",
            ],
        ),
        (
            "UltimateEliminator",
            [
                "UltimateEliminator+MathSAT-5.6.3_s_default",
                "UltimateEliminator+MathSAT-5.6.3_s-wrapped-inc___default",
            ],
        ),
        (
            "Vampire",
            [
                "vampire_smt_4.5_vampire_smtcomp",
                "vampire-4.3-smt_vampire_smtcomp",
                "vampire-4.4-smtcomp-wrapped-sq_default",
            ],
        ),
        (
            "veriT",
            ["veriT_default", "veriT+raSAT+Redlog_default", "veriT+vite_default"],
        ),
        (
            "Yices2",
            [
                "Yices 2.6.2 bug fix_default",
                "Yices 2.6.0_default",
                "Yices 2.6.2 bug fix incremental-wrapped-inc___default",
                "Yices 2.6.2 Incremental for SMTCOMP2020-wrapped-inc___default",
                "Yices 2.6.2 Incremental-wrapped-inc___default",
                "Yices___default",
            ],
        ),
        ("Z3string", ["Z3str4 SMTCOMP2020 v1.1_default"]),
        (
            "Z3",
            [
                "z3-4.8.8_default",
                "z3-4.7.1_default",
                "z3-4.8.4-d6df51951f4c-wrapped-sq_default",
                "z3-4.7.4-wrapped-inc___default",
                "z3-4.8.4-wrapped-inc___default",
                "Z3___default",
                "z3-4.8.4-wrapped-inc___default",
                "z3-4.8.8-wrapped-inc___default",
                "Z3___default",
            ],
        ),
    ],
    "SMT-COMP 2021": [
        ("AProVE", ["AProVE NIA 2014_2021"]),
        (
            "Bitwuzla",
            ["Bitwuzla-fixed_default", "Bitwuzla-fixed-wrapped-inc___default"],
        ),
        (
            "COLIBRI",
            [
                "COLIBRI_21_06_23_default",
                "COLIBRI 20.5.25_default",
                "COLIBRI_21_05_28_default",
            ],
        ),
        (
            "CVC4",
            [
                "CVC4-2019-06-03-d350fe1-wrapped-sq_default",
                "CVC4-sq-final_default",
                "master-2018-06-10-b19c840-competition-default_default",
                "CVC4-inc-2019-06-03-d350fe1-wrapped-inc___default",
                "CVC4-inc-final-wrapped-inc___default",
            ],
        ),
        ("cvc5", ["cvc5-fixed_default", "cvc5-inc-wrapped-inc___default"]),
        ("iProver", ["iProver-v3.5-final-fix2_iProver_SMT"]),
        (
            "MathSAT",
            [
                "mathsat-5.6.6_default",
                "mathsat-20190601-wrapped-sq_default",
                "mathsat-5.6.6-wrapped-inc___default",
                "MathSAT5-wrapped-inc___default",
                "MathSAT___default",
            ],
        ),
        ("mc2", ["mc2 2021-06-07_default.sh"]),
        ("OpenSMT", ["OpenSMT-fixed_default", "OpenSMT-wrapped-inc___default"]),
        ("Par4", ["Par4-wrapped-sq_default"]),
        (
            "SMTInterpol",
            [
                "smtinterpol-2.5-823-g881e8631_default",
                "smtinterpol-2.5-514-wrapped-sq_default",
                "smtinterpol-2.5-823-g881e8631-wrapped-inc___default",
            ],
        ),
        ("SMT-RAT", ["smtrat-SMTCOMP_default", "smtrat-MCSAT_default"]),
        ("STP", ["STP 2021.0_default", "STP 2021.0-wrapped-inc___default"]),
        (
            "UltimateEliminator",
            [
                "UltimateEliminator+MathSAT-5.6.6_default",
                "UltimateEliminator+MathSAT-5.6.6-wrapped-inc___default",
            ],
        ),
        (
            "Vampire",
            [
                "vampire_smt_4.6-fixed_vampire_smtcomp",
                "vampire_smt_4.5_vampire_smtcomp",
            ],
        ),
        ("veriT", ["veriT_default", "veriT+raSAT+Redlog_default"]),
        (
            "Yices2",
            [
                "Yices 2.6.2 bug fix_default",
                "Yices 2.6.0_default",
                "Yices 2.6.2 for SMTCOMP2020_default",
                "Yices 2.6.2 bug fix incremental-wrapped-inc___default",
                "Yices 2.6.2 Incremental for SMTCOMP2020-wrapped-inc___default",
                "Yices 2.6.2 incremental for SMTCOMP 2021-wrapped-inc___default",
                "Yices 2.6.2 Incremental-wrapped-inc___default",
                "Yices___default",
            ],
        ),
        ("YicesLS", ["YicesLS_0611_1448_default"]),
        ("YicesQS", ["yices-QS-2021-06-13under10_default"]),
        ("Z3string", ["Z3str4 SMTCOMP 2021 v1.1_default"]),
        (
            "Z3",
            [
                "z3-4.8.11_default",
                "z3-4.7.1_default",
                "z3-4.8.4-d6df51951f4c-wrapped-sq_default",
                "z3-4.8.8_default",
                "z3-4.8.11-wrapped-inc___default",
                "z3-4.8.4-wrapped-inc___default",
                "z3-4.8.8-wrapped-inc___default",
                "Z3___default",
            ],
        ),
    ],
    "SMT-COMP 2022": [
        (
            "Bitwuzla",
            ["Bitwuzla-fixed_default", "Bitwuzla-fixed-wrapped-inc___default"],
        ),
        ("COLIBRI", ["COLIBRI 22_06_18_default"]),
        (
            "CVC4",
            [
                "CVC4-sq-final_default",
                "CVC4-inc-2019-06-03-d350fe1-wrapped-inc___default",
            ],
        ),
        (
            "cvc5",
            [
                "cvc5_default",
                "cvc5-default-2022-07-02-b15e116-wrapped_sq",
                "cvc5-inc-2022-07-02-b15e116-wrapped___incremental",
                "cvc5-inc-wrapped-inc___default",
            ],
        ),
        (
            "MathSAT",
            [
                "MathSAT-5.6.8_default",
                "mathsat-5.6.6-wrapped-inc___default",
                "MathSAT-5.6.8___incremental",
                "MathSAT___default",
            ],
        ),
        ("NRA-LS", ["NRA-LS-FINAL_default"]),
        ("OpenSMT", ["opensmt fixed_default", "OpenSMT-wrapped___incremental"]),
        ("OSTRICH", ["OSTRICH 1.2_def"]),
        ("Par4", ["Par4-wrapped-sq_default"]),
        ("Q3B", ["Q3B_default"]),
        ("Q3B-pBNN", ["Q3B-pBDD SMT-COMP 2022 final_default"]),
        (
            "SMTInterpol",
            [
                "smtinterpol-fixed-2.5-1148-gf2d8e6b0_default",
                "smtinterpol-2.5-1147-g108647d8-wrapped___incremental",
            ],
        ),
        ("SMT-RAT", ["SMT-RAT-MCSAT_default"]),
        (
            "solsmt",
            [
                "solsmt-5b37426cad388922a-wrapped_default",
                "solsmt-5b37426cad388922a-wrapped___incremental",
            ],
        ),
        (
            "STP",
            [
                "STP 2022.4_default",
                "STP 2021.0-wrapped-inc___default",
                "STP 2022.2-wrapped___incremental",
            ],
        ),
        (
            "UltimateEliminator",
            [
                "UltimateEliminator+MathSAT-5.6.7-wrapped_default",
                "UltimateEliminator+MathSAT-5.6.7-wrapped___incremental",
            ],
        ),
        (
            "Vampire",
            [
                "vampire_4.7_smt_fix-wrapped_default",
                "vampire_4.7_smt_fix-wrapped_vampire_smtcomp",
            ],
        ),
        ("veriT", ["veriT_default", "veriT+raSAT+Redlog_default"]),
        (
            "Yices2",
            [
                "Yices 2.6.2 for SMTCOMP 2021_default",
                "Yices 2.6.2 Incremental for SMTCOMP2020-wrapped-inc___default",
                "Yices 2.6.2 incremental for SMTCOMP 2021-wrapped-inc___default",
                "Yices 2.6.2 incremental for SMTCOMP 2021-wrapped___incremental",
            ],
        ),
        ("Yices-ismt", ["yices-ismt-0721_default"]),
        ("YicesQS", ["yicesQS-2022-07-02-optim-under10_default"]),
        ("Z3++BV", ["z3++bv_0702_default"]),
        ("Z3string", ["Z3str4_default"]),
        ("Z3++", ["z3++0715_default"]),
        (
            "Z3",
            [
                "z3-4.8.17_default",
                "z3-4.8.11_default",
                "z3-4.8.11-wrapped-inc___default",
                "z3-4.8.17___incremental",
                "z3-4.8.4-wrapped-inc___default",
                "z3-4.8.8-wrapped-inc___default",
            ],
        ),
    ],
    "SMT-COMP 2023": [
        ("Bitwuzla", ["Bitwuzla-fixed_default", "Bitwuzla-wrapped___incremental"]),
        ("COLIBRI", ["COLIBRI 2023_05_10_default"]),
        ("CVC4", ["CVC4-sq-final_default"]),
        (
            "cvc5",
            [
                "cvc5-default-2023-05-16-ea045f305_sq",
                "cvc5-default-2022-07-02-b15e116-wrapped_sq",
                "cvc5-inc-2023-05-16-ea045f305-wrapped___incremental",
                "cvc5-inc-wrapped-inc___default",
            ],
        ),
        ("iProver", ["iProver-3.8-fix_iprover_SMT"]),
        (
            "MathSAT",
            [
                "mathsat-5.6.6-wrapped-inc___default",
                "MathSAT___default",
            ],
        ),
        ("NRA-LS", ["cvc5-NRA-LS-sq_default"]),
        (
            "OpenSMT",
            [
                "OpenSMT a78dcf01_default",
                "OpenSMT a78dcf01-wrapped___incremental",
            ],
        ),
        ("OSTRICH", ["OSTRICH 1.3 SMT-COMP fixed_def"]),
        ("Par4", ["Par4-wrapped-sq_default"]),
        ("Q3B", ["Q3B_default"]),
        (
            "SMTInterpol",
            [
                "smtinterpol-2.5-1272-g2d6d356c_default",
                "smtinterpol-2.5-1272-g2d6d356c-wrapped___incremental",
            ],
        ),
        ("SMT-RAT", ["SMT-RAT-MCSAT_default"]),
        ("STP", ["STP 2022.4_default", "STP 2022.4-wrapped___incremental"]),
        (
            "UltimateEliminator",
            [
                "UltimateEliminator+MathSAT-5.6.9_default",
                "UltimateIntBlastingWrapper+SMTInterpol_default",
                "UltimateEliminator+MathSAT-5.6.9___incremental",
            ],
        ),
        ("Vampire", ["vampire_4.8_smt_pre_vampire_smtcomp"]),
        ("Yaga", ["Yaga_SMT-COMP-2023_presubmition_default"]),
        (
            "Yices2",
            [
                "Yices 2 for SMTCOMP 2023_default",
                "Yices 2.6.2 for SMTCOMP 2021_default",
                "Yices 2.6.2 incremental for SMTCOMP 2021-wrapped-inc___default",
                "Yices 2.6.2 incremental for SMTCOMP 2021-wrapped___incremental",
                "Yices2 incremental fixed-wrapped___incremental",
                "Yices 2 incremental for SMT COMP 2023-wrapped___incremental",
            ],
        ),
        ("Yices-ismt", ["yices-ismt-sq-0526_default"]),
        ("YicesQS", ["yicesQS-2022-07-02-optim-under10_default"]),
        ("Z3alpha", ["z3alpha_default"]),
        ("Z3-Noodler", ["Z3-Noodler_default"]),
        ("Z3-Owl", ["z3-Owl-Final_default"]),
        ("Z3++", ["z3++0715_default", "Z3++_sq_0526_default"]),
        (
            "Z3",
            [
                "z3-4.8.17_default",
                "z3-4.8.11_default",
                "z3-4.8.11-wrapped-inc___default",
                "z3-4.8.17___incremental",
                "z3-4.8.4-wrapped-inc___default",
                "z3-4.8.8-wrapped-inc___default",
            ],
        ),
    ],
    "SMT-COMP 2024": [
        ("Algaroba", ["Algaroba"]),
        ("Amaya", ["Amaya"]),
        ("Bitwuzla", ["Bitwuzla", "bitwuzla"]),
        ("COLIBRI", ["COLIBRI"]),
        ("cvc5", ["cvc5"]),
        ("iProver", ["iProver v3.9"]),
        ("OpenSMT", ["OpenSMT", "opensmt"]),
        ("OSTRICH", ["OSTRICH"]),
        ("plat-smt", ["plat-smt", "platsmt"]),
        ("SMTInterpol", ["SMTInterpol", "smtinterpol"]),
        ("SMT-RAT", ["SMT-RAT"]),
        ("STP", ["STP", "stp"]),
        ("Yices2", ["Yices2", "yices2"]),
        ("YicesQS", ["YicesQS"]),
        ("Z3alpha", ["Z3-alpha"]),
        ("Z3-Noodler", ["Z3-Noodler"]),
    ],
    "SMT-COMP 2025": [
        ("Amaya", ["Amaya"]),
        ("Bitwuzla", ["Bitwuzla", "Bitwuzla-MachBV-base", "bitwuzla"]),
        ("Bitwuzla-MachBV", ["Bitwuzla-MachBV"]),
        ("BVDecide", ["bv_decide", "bv_decide-nokernel"]),
        ("COLIBRI", ["COLIBRI"]),
        ("Colibri2", ["colibri2"]),
        ("cvc5", ["cvc5"]),
        ("iProver", ["iProver v3.9.3"]),
        ("OpenSMT", ["OpenSMT", "opensmt"]),
        ("OSTRICH", ["OSTRICH"]),
        ("SMTInterpol", ["SMTInterpol", "smtinterpol"]),
        ("SMT-RAT", ["SMT-RAT"]),
        (
            "UltimateEliminator",
            ["UltimateEliminator+MathSAT", "ultimateeliminatormathsat"],
        ),
        ("Yices2", ["Yices2", "yices2"]),
        ("YicesQS", ["YicesQS"]),
        (
            "Z3",
            [
                "Z3-alpha-base",
                "Z3-Noodler-base",
                "Z3-Owl-base",
                "z3siri-base",
                "z3incz3base",
            ],
        ),
        ("Z3alpha", ["Z3-alpha"]),
        ("Z3-Owl", ["Z3-Owl"]),
        ("Z3-Noodler", ["Z3-Noodler", "Z3-Noodler-Mocha-base"]),
        ("Z3-Noodler-Mocha", ["Z3-Noodler-Mocha"]),
        ("z3siri", "z3siri"),
        ("Z3++", "z3incz3"),
    ],
}

global_variant_table = []
global_variant_count = 1

# Helper to insert benchmarks with fewer database queries
global_variant_lookup = {}
for name, url in known_solvers:
    id = solver_count
    solver_count = solver_count + 1
    solver_table.append((id, name, url))

    # Also add the original name as a variant
    global_variant_table.append((global_variant_count, name, id))
    global_variant_lookup[name] = global_variant_count
    global_variant_count = global_variant_count + 1
    try:
        for variant in global_solver_variants[name]:
            global_variant_table.append((global_variant_count, variant, id))
            global_variant_lookup[variant] = global_variant_count
            global_variant_count = global_variant_count + 1
    except KeyError:
        pass


def populate_tables(connetion):
    connetion.executemany(
        "INSERT INTO Solvers(id, name, link) VALUES(?,?,?);", solver_table
    )

    connetion.executemany(
        "INSERT INTO SolverVariants(id, fullName, solver) VALUES(?,?,?);",
        global_variant_table,
    )


def populate_evaluation_solvers(connection, evaluationName, evaluationId):
    solvers = evaluation_solver_variants[evaluationName]
    for solver, variants in solvers:
        solverId = None
        for row in connection.execute(
            "SELECT id FROM Solvers WHERE name=?",
            (solver,),
        ):
            solverId = row[0]
        for variant in variants:
            connection.execute(
                "INSERT INTO SolverVariants(fullName, solver, evaluation) VALUES(?,?,?);",
                (variant, solverId, evaluationId),
            )
