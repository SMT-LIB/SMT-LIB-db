"""
Module to fix benchmark identifying information for past iterations of
SMT-COMP.
Sometimes benchmarks were moved or renamed.  We try to search for
benchmarks using `guess_benchmark_id`.  However, this is sometimes not
enough.  Here are some hard coded rules for these cases.
Note that some benchmarks were also removed for non-compliance.
"""


def fix_smt_comp_early(logic, family, filename):
    if family == "sal":
        if filename.startswith("inf-bakery"):
            return (logic, family, "bakery/" + filename)
        if filename.startswith("lpsat-goal"):
            return (logic, family, "lpsat/" + filename)
        if filename.startswith("windowreal-no"):
            return (logic, family, "windowreal/" + filename)
        if filename.startswith("tgc_io"):
            return (logic, family, "tgc/" + filename)
        if filename.startswith("gasburner-prop3"):
            return (logic, family, "gasburner/" + filename)
        if filename.startswith("pursuit-safety"):
            return (logic, family, "pursuit/" + filename)
        if filename.startswith("Carpark2"):
            return (logic, family, "carpark/" + filename)
    if family == "array_benchmarks":
        if filename.startswith("pipeline-invalid"):
            return (logic, family, "misc/" + filename)
        if filename.startswith("stack-"):
            return (logic, family, "misc/" + filename)
        if filename.startswith("queue-"):
            return (logic, family, "misc/" + filename)
        if filename.startswith("pointer-"):
            return (logic, family, "pointer/" + filename)
        if filename.startswith("qlock-"):
            return (logic, family, "qlock/" + filename)
    if family == "CIRC":
        if not filename[0].isupper():
            return (logic, family, filename)
        if filename.startswith("MULTIPLIER_PRIME"):
            return (logic, family, "multiplier_prime/" + filename)
        prefix = filename[: filename.find("_")]
        return (logic, family, prefix.lower() + "/" + filename)
    if family == "mathsat":
        if logic == "QF_IDL" and filename.startswith("FISCHER"):
            return (logic, family, "fischer/" + filename)
        if filename.startswith("PO"):
            return (logic, family, "post_office/" + filename)
    if family == "sep":
        if filename.startswith("LD_ST") or filename.startswith("cache_neg"):
            return (logic, family, "hardware/" + filename)
    if family == "check" and filename == "int_incompleteness1.smt2":
        if logic == "QF_AUFLIA":
            return ("QF_LIA", family, filename)
        if logic == "QF_UFIDL":
            return ("QF_IDL", family, filename)
    if family == "egt":
        index = filename.find("/")
        if index >= 0:
            return ("QF_BV", "egt", filename[index + 1 :])
    return (logic, family, filename)


def fix_2017_preiner(logic, family, filename):
    if family == "2017-Preiner":
        index = filename.find("/")
        if index >= 0:
            return (logic, "2017-Preiner-" + filename[:index], filename[index + 1 :])
    return (logic, family, filename)
