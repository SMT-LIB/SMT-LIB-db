const std = @import("std");
const fs = std.fs;
const print = std.debug.print;

const compress = @import("compress.zig");
const data = @import("data.zig");
const tokens = @import("tokens.zig");
const symbols = @import("symbols.zig").symbol_map;

const Errors = error{
    ImbalancedParentheses,
    UnexpectedToken,
    OutOfTokens,
    UnsupportedPlatform,
};

const Commands = enum {
    assert,
    check_sat,
    check_sat_assuming,
    declare_const,
    declare_datatype,
    declare_datatypes,
    declare_fun,
    declare_sort,
    define_fun,
    define_fun_rec,
    define_funs_rec,
    define_sort,
    echo,
    exit,
    get_assertions,
    get_assignment,
    get_info,
    get_model,
    get_option,
    get_proof,
    get_unsat_assumptions,
    get_unsat_core,
    get_value,
    pop,
    push,
    reset,
    reset_assertions,
    set_info,
    set_logic,
    set_option,
};

const CmdMap = std.ComptimeStringMap(Commands, .{
    .{ "assert", .assert },
    .{ "check-sat", .check_sat },
    .{ "check-sat-assuming", .check_sat_assuming },
    .{ "declare-const", .declare_const },
    .{ "declare-datatype", .declare_datatype },
    .{ "declare-datatypes", .declare_datatypes },
    .{ "declare-fun", .declare_fun },
    .{ "declare-sort", .declare_sort },
    .{ "define-fun", .define_fun },
    .{ "define-fun-rec", .define_fun_rec },
    .{ "define-funs-rec", .define_funs_rec },
    .{ "define-sort", .define_sort },
    .{ "echo", .echo },
    .{ "exit", .exit },
    .{ "get-assertions", .get_assertions },
    .{ "get-assignment", .get_assignment },
    .{ "get-info", .get_info },
    .{ "get-model", .get_model },
    .{ "get-option", .get_option },
    .{ "get-proof", .get_proof },
    .{ "get-unsat-assumptions", .get_unsat_assumptions },
    .{ "get-unsat-core", .get_unsat_core },
    .{ "get-value", .get_value },
    .{ "pop", .pop },
    .{ "push", .push },
    .{ "reset", .reset },
    .{ "reset-assertions", .reset_assertions },
    .{ "set-info", .set_info },
    .{ "set-logic", .set_logic },
    .{ "set-option", .set_option },
});

const Attribute = enum {
    license,
    category,
    status,
    source,
};

const AttrMap = std.ComptimeStringMap(Attribute, .{
    .{ ":license", .license },
    .{ ":category", .category },
    .{ ":status", .status },
    .{ ":source", .source },
});

fn skip_rest_of_term(
    tokenIt: *tokens.TokenIterator,
) !usize {
    var level: usize = 1;

    while (true) {
        if (tokenIt.next()) |token| {
            switch (token.type) {
                tokens.TokenType.Opening => {
                    level += 1;
                },
                tokens.TokenType.Closing => {
                    level -= 1;
                    if (level == 0)
                        return tokenIt.pos;
                },
                else => {},
            }
        } else return Errors.OutOfTokens;
    }
    return Errors.OutOfTokens;
}

// Reads an term (returns to the same level), and updates benchmark data
fn read_term(
    tokenIt: *tokens.TokenIterator,
    subBench: *data.SubBenchmarkData,
) !usize {
    var level: usize = 0;

    while (true) {
        if (tokenIt.next()) |token| {
            switch (token.type) {
                tokens.TokenType.Opening => {
                    level += 1;
                },
                tokens.TokenType.Closing => {
                    if (level > subBench.maxTermDepth)
                        subBench.maxTermDepth = level;
                    level -= 1;
                    if (level == 0)
                        return tokenIt.pos;
                },
                tokens.TokenType.Symbol => {
                    if (symbols.get(token.span)) |idx| {
                        subBench.symbolFrequency[idx] += 1;
                    }
                    if (level == 0)
                        return tokenIt.pos;
                },
                else => {
                    if (level == 0)
                        return tokenIt.pos;
                },
            }
        } else return Errors.OutOfTokens;
    }
    return Errors.OutOfTokens;
}

fn get_string(tokenIt: *tokens.TokenIterator) ![]const u8 {
    if (tokenIt.next()) |token| {
        if (token.type != tokens.TokenType.String)
            return error.UnexpectedToken;
        return token.span;
    }
    return error.UnexpectedToken;
}

fn print_subproblem(
    out: anytype,
    str: []u8,
    scopes: *std.ArrayList(data.Scope),
    command: []const u8,
) !void {
    for (scopes.items) |scope| {
        var i: usize = 0;
        while (i < scope.intervals.items.len) : ({
            i += 2;
        }) {
            const start = scope.intervals.items[i];
            const end = scope.intervals.items[i + 1];
            try out.print("{s}", .{str[start..end]});
        }
    }
    try out.print("{s}\n", .{command});
}

pub fn main() !u8 {
    var area = std.heap.ArenaAllocator.init(std.heap.page_allocator);
    defer area.deinit();
    const allocator = area.allocator();

    const stdout_file = std.io.getStdOut().writer();
    var bw = std.io.bufferedWriter(stdout_file);
    const stdout = bw.writer();

    if (.windows == @import("builtin").os.tag) {
        print("Windows is not supported.\n", .{});
        return Errors.UnsupportedPlatform;
    }

    if (std.os.argv.len < 2) {
        print("Klammerhammer -- Extract SMT-LIB metadata\n\n", .{});
        print("Usage:\n", .{});
        print("\tklhm FILENAME\n", .{});
        return 1;
    }

    const filename = std.mem.span(std.os.argv[1]);
    const file = try fs.cwd().openFile(filename, .{});
    defer file.close();

    const md = try file.metadata();
    const ptr = try std.os.mmap(
        null,
        md.size(),
        std.os.PROT.READ | std.os.PROT.WRITE,
        std.os.MAP.PRIVATE,
        file.handle,
        0,
    );
    defer std.os.munmap(ptr);

    var tokenIt = tokens.TokenIterator{ .data = ptr };

    var zstd = try compress.init();
    defer zstd.deinit();

    var benchmarkData: data.BenchmarkData = .{};
    benchmarkData.size = ptr.len;

    var scopes = std.ArrayList(data.Scope).init(allocator);
    try scopes.append(data.Scope{ .intervals = std.ArrayList(usize).init(allocator) });
    var top = &scopes.items[scopes.items.len - 1];
    try top.intervals.append(0);

    var idx: usize = 0;
    while (true) {
        if (tokenIt.next()) |token| {
            if (token.type != tokens.TokenType.Opening)
                return Errors.UnexpectedToken;
        } else break;
        idx = tokenIt.pos;
        const level_start_idx = idx - 1;

        if (tokenIt.next()) |token| {
            if (CmdMap.get(token.span)) |cmd| {
                switch (cmd) {
                    .set_logic => {
                        if (tokenIt.next()) |logicToken| {
                            benchmarkData.logic = logicToken.span;
                            idx = try skip_rest_of_term(&tokenIt);
                        } else break;
                    },
                    .set_info => {
                        if (tokenIt.next()) |attrToken| {
                            if (AttrMap.get(attrToken.span)) |attr| {
                                switch (attr) {
                                    .license => {
                                        // TODO: special case for embedded license!
                                        const str = try get_string(&tokenIt);
                                        benchmarkData.license = str;
                                    },
                                    .category => {
                                        const str = try get_string(&tokenIt);
                                        benchmarkData.category = str;
                                    },
                                    .status => {
                                        try if (tokenIt.next()) |x| {
                                            if (x.type != tokens.TokenType.Symbol)
                                                return Errors.UnexpectedToken;
                                            top.data.status = x.span;
                                        } else Errors.OutOfTokens;
                                    },
                                    .source => {
                                        const str = try get_string(&tokenIt);
                                        benchmarkData.set_source(str);
                                    },
                                }
                            }
                        } else break;
                        idx = try skip_rest_of_term(&tokenIt);
                    },
                    .assert => {
                        top.data.assertsCount += 1;
                        _ = try read_term(&tokenIt, &top.data);
                        idx = try skip_rest_of_term(&tokenIt);
                    },
                    .declare_fun => {
                        _ = tokenIt.next(); // name
                        _ = tokenIt.next(); // Skip (
                        if (tokenIt.next()) |tkn| {
                            if (tkn.type == tokens.TokenType.Closing) {
                                top.data.declareConstCount += 1;
                            } else {
                                top.data.declareFunCount += 1;
                                idx = try skip_rest_of_term(&tokenIt);
                            }
                            idx = try skip_rest_of_term(&tokenIt);
                        } else break;
                    },
                    .declare_const => {
                        top.data.declareConstCount += 1;
                        idx = try skip_rest_of_term(&tokenIt);
                    },
                    .declare_sort => {
                        top.data.declareSortCount += 1;
                        idx = try skip_rest_of_term(&tokenIt);
                    },
                    .define_fun => {
                        _ = tokenIt.next(); // name
                        _ = tokenIt.next(); // Skip (
                        if (tokenIt.next()) |tkn| {
                            if (tkn.type == tokens.TokenType.Closing) {
                                top.data.constantFunCount += 1;
                            } else {
                                top.data.defineFunCount += 1;
                                idx = try skip_rest_of_term(&tokenIt);
                            }
                        } else return Errors.OutOfTokens;
                        // Return sort of the defined function
                        _ = try read_term(&tokenIt, &top.data);
                        // Definition
                        _ = try read_term(&tokenIt, &top.data);
                        idx = try skip_rest_of_term(&tokenIt);
                    },
                    .define_sort => {
                        top.data.defineSortCount += 1;
                        idx = try skip_rest_of_term(&tokenIt);
                    },
                    .push => {
                        const old_idx = top.intervals.items[top.intervals.items.len - 1];
                        top.data.normalizedSize += (level_start_idx - old_idx);

                        try top.intervals.append(level_start_idx);

                        idx = try skip_rest_of_term(&tokenIt);

                        const new = data.Scope{
                            .intervals = std.ArrayList(usize).init(allocator),
                            .data = top.data,
                        };
                        try scopes.append(new);
                        top = &scopes.items[scopes.items.len - 1];
                        try top.intervals.append(idx);
                    },
                    .pop => {
                        try top.intervals.append(level_start_idx);
                        idx = try skip_rest_of_term(&tokenIt);
                        top.intervals.deinit();
                        _ = scopes.pop();
                        top = &scopes.items[scopes.items.len - 1];
                        try top.intervals.append(idx);
                    },
                    .check_sat, .check_sat_assuming => {
                        const old_idx = top.intervals.items[top.intervals.items.len - 1];

                        try top.intervals.append(level_start_idx);
                        idx = try skip_rest_of_term(&tokenIt);

                        benchmarkData.subbenchmarkCount += 1;
                        // With check-sat we have to use the idx after the command,
                        // because we want to take its size into account.
                        top.data.normalizedSize += (idx - old_idx);
                        top.data.compressedSize = try zstd.compressedSizeIntervalls(
                            ptr,
                            &scopes,
                            ptr[level_start_idx..idx],
                        );

                        try top.data.print(stdout);
                        // try print_subproblem(stdout, ptr, &scopes, ptr[level_start_idx..idx]);
                        _ = try stdout.write("\n");
                        try bw.flush();

                        try top.intervals.append(idx);
                    },
                    .exit => {
                        break;
                    },
                    else => {
                        idx = try skip_rest_of_term(&tokenIt);
                    },
                }
            } else {
                // Unkown command, do nothing
                idx = try skip_rest_of_term(&tokenIt);
            }
        } else {
            return Errors.OutOfTokens;
        }
    }

    benchmarkData.isIncremental = benchmarkData.subbenchmarkCount > 1;
    benchmarkData.compressedSize = try zstd.compressedSizeSlice(ptr);
    try benchmarkData.print(stdout);
    _ = try stdout.write("\n");
    try bw.flush();
    return 0;
}
