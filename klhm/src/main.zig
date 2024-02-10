const std = @import("std");
const fs = std.fs;
const print = std.debug.print;

const BenchmarkData = struct {
    logic: ?[]const u8 = null,
    size: usize = 0,
    compressedSize: usize = 0,
    license: ?[]const u8 = null,
    generatedOn: ?[]const u8 = null,
    generatedBy: ?[]const u8 = null,
    targetSolver: ?[]const u8 = null,
    generator: ?[]const u8 = null,
    application: ?[]const u8 = null,
    description: ?[]const u8 = null,
    category: ?[]const u8 = null,
    subbenchmarkCount: usize = 0,
    isIncremental: bool = false,

    fn print(self: BenchmarkData, out: anytype) !void {
        if (self.logic) |logic|
            try out.print("Logic:              {s}\n", .{logic});
        if (self.size != 0)
            try out.print("Size:               {}\n", .{self.size});
        if (self.compressedSize != 0)
            try out.print("Compressed size:    {}\n", .{self.compressedSize});
        if (self.license) |license|
            try out.print("License:            {s}\n", .{license});
        if (self.generatedOn) |generatedOn|
            try out.print("Generated on:       {s}\n", .{generatedOn});
        if (self.generatedBy) |generatedBy|
            try out.print("Generated by:       {s}\n", .{generatedBy});
        if (self.generator) |generator|
            try out.print("Generator:          {s}\n", .{generator});
        if (self.application) |application|
            try out.print("Application:        {s}\n", .{application});
        if (self.targetSolver) |targetSolver|
            try out.print("Target solver:      {s}\n", .{targetSolver});
        if (self.generator) |generator|
            try out.print("Generator:          {s}\n", .{generator});
        if (self.description) |description|
            try out.print("Description:        {s}\n", .{description});
        if (self.category) |category|
            try out.print("Category:           {s}\n", .{category});
        if (self.subbenchmarkCount != 0)
            try out.print("Subbenchmark count: {}\n", .{self.subbenchmarkCount});
        try out.print("Is incremental:     {}\n", .{self.isIncremental});
    }

    const SourceField = enum { generatedBy, generatedOn, application, targetSolver, generator };

    const SourceMap = std.ComptimeStringMap(SourceField, .{ .{ "Generated by", .generatedBy }, .{ "Generated on", .generatedOn }, .{ "Application", .application }, .{ "Target solver", .targetSolver }, .{ "Generator", .generator } });

    fn set_source(self: *BenchmarkData, str: []const u8) void {
        var idx: usize = 0;
        var line_start: usize = 0;
        var colon: usize = 0;
        while (idx < str.len) : (idx += 1) {
            if (str[idx] == '\n') {
                if (colon != 0) {
                    const left = std.mem.trim(u8, str[line_start..colon], " \t\n\r");
                    // also trim some extra cruft
                    const right = std.mem.trim(u8, str[colon + 1 .. idx], " \t\n\r,;:");
                    if (SourceMap.get(left)) |field| {
                        switch (field) {
                            .generatedBy => {
                                self.generatedBy = right;
                            },
                            .generatedOn => {
                                self.generatedOn = right;
                            },
                            .application => {
                                self.application = right;
                            },
                            .targetSolver => {
                                self.targetSolver = right;
                            },
                            .generator => {
                                self.generator = right;
                            },
                        }
                        colon = 0;
                        line_start = idx + 1;
                        continue;
                    } else {
                        //jump back and finish headers
                        idx = line_start;
                        break;
                    }
                } else {
                    const line = std.mem.trim(u8, str[line_start..idx], " \t\n\r");
                    // not empty!
                    if (line.len > 0) {
                        idx = line_start;
                        break;
                    }
                }
            }
            if (colon == 0 and str[idx] == ':')
                colon = idx;
        }
        self.description = str[idx..str.len];
    }
};

const SubBenchmarkData = struct {
    normalizedSize: ?usize = null,
    compressedSize: ?usize = null,
    assertsCount: ?usize = null,
    declareFunCount: ?usize = null,
    declareSortCount: ?usize = null,
    defineFunCount: ?usize = null,
    defineSortCount: ?usize = null,
    maxTermDepth: ?usize = null,
};

const Scope = struct {
    intervals: std.ArrayList(usize),
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

fn skip_to_level(str: []u8, start_idx: usize, start_level: usize, target_level: usize) ?usize {
    var level: usize = start_level;
    var idx = start_idx;

    var in_str: bool = false;
    var in_symb: bool = false;
    var in_comment: bool = false;
    while (idx < str.len) : ({
        idx += 1;
    }) {
        const chr = str[idx];
        switch (chr) {
            '\n' => {
                if (in_comment) in_comment = false;
            },
            ';' => {
                if (!(in_str or in_comment or in_symb)) in_comment = true;
            },
            '|' => {
                if (in_comment or in_str) continue;
                in_symb = !in_symb;
            },
            '"' => {
                if (in_comment or in_symb) continue;
                in_str = !in_str;
            },
            '(' => {
                if (in_comment or in_symb or in_str) continue;
                level += 1;
                if (level == target_level)
                    return idx + 1;
            },
            ')' => {
                if (in_comment or in_symb or in_str) continue;
                if (level == 0)
                    return null;
                level -= 1;
                if (level == target_level)
                    return idx + 1;
            },
            else => {},
        }
    }
    return null;
}

const span = struct { start: usize, end: usize };

fn skip_whitespace(str: []const u8, start_idx: usize) usize {
    var idx = start_idx;

    var in_comment = false;
    while (idx < str.len) : ({
        idx += 1;
    }) {
        const char = str[idx];
        if (char == ';') {
            in_comment = true;
            continue;
        }
        if (in_comment and char == '\n') {
            in_comment = false;
            continue;
        }
        if (!in_comment and !(char == 9 or char == 10 or char == 13 or char == 32)) {
            break;
        }
    }
    return idx;
}

// scans the next symbol (also covers numerals and attributes)
fn get_symbol(str: []u8, start_idx: usize) span {
    var idx = skip_whitespace(str, start_idx);
    const cmd_start = idx;
    while (idx < str.len) : ({
        idx += 1;
    }) {
        const char = str[idx];
        if (!(char == '~' or
            char == '!' or
            char == '@' or
            char == '$' or
            char == '%' or
            char == '^' or
            char == '&' or
            char == '*' or
            char == '_' or
            char == '-' or
            char == '+' or
            char == '=' or
            char == '<' or
            char == '>' or
            char == '.' or
            char == '?' or
            char == '/' or
            char == ':' or
            char == '.' or
            (char >= '0' and char <= '9') or
            (char >= 'a' and char <= 'z') or
            (char >= 'A' and char <= 'Z')))
            break;
    }
    return .{ .start = cmd_start, .end = idx };
}

// scans the next string or quoted symbol
fn get_string(str: []u8, start_idx: usize) ?span {
    var idx = skip_whitespace(str, start_idx);
    var in_symb = false;
    var in_str = false;
    switch (str[idx]) {
        '|' => {
            in_symb = true;
        },
        '"' => {
            in_str = true;
        },
        else => {
            return null;
        },
    }
    idx += 1;
    const cmd_start = idx;

    while (idx < str.len) : ({
        idx += 1;
    }) {
        const char = str[idx];
        if (in_str and char == '"') {
            // Escaped
            if (idx < str.len - 1 and str[idx + 1] == '"')
                continue;
            break;
        }
        if (in_symb and char == '|')
            break;
    }
    return .{ .start = cmd_start, .end = idx };
}

fn print_subproblem(out: anytype, str: []u8, scopes: *std.ArrayList(Scope), command: []const u8) !void {
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
        return 1;
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

    var benchmarkData: BenchmarkData = .{};
    benchmarkData.size = ptr.len;

    var scopes = std.ArrayList(Scope).init(allocator);
    try scopes.append(Scope{ .intervals = std.ArrayList(usize).init(allocator) });
    var top = &scopes.items[scopes.items.len - 1];
    try top.intervals.append(0);

    var idx: usize = 0;
    while (idx < ptr.len) {
        idx = skip_to_level(ptr, idx, 0, 1) orelse break;
        const level_start_idx = idx - 1;

        const cmdSpan = get_symbol(ptr, idx);
        const cmdStr = ptr[cmdSpan.start..cmdSpan.end];

        if (CmdMap.get(cmdStr)) |cmd| {
            switch (cmd) {
                .set_logic => {
                    const logicSpan = get_symbol(ptr, cmdSpan.end);
                    benchmarkData.logic = ptr[logicSpan.start..logicSpan.end];
                    idx = skip_to_level(ptr, cmdSpan.end, 1, 0) orelse break;
                },
                .set_info => {
                    const attrSpan = get_symbol(ptr, cmdSpan.end);
                    if (AttrMap.get(ptr[attrSpan.start..attrSpan.end])) |attr| {
                        switch (attr) {
                            .license => {
                                // TODO: special case for embedded license!
                                if (get_string(ptr, attrSpan.end)) |x|
                                    benchmarkData.license = ptr[x.start..x.end];
                            },
                            .category => {
                                if (get_string(ptr, attrSpan.end)) |x|
                                    benchmarkData.category = ptr[x.start..x.end];
                            },
                            .status => {
                                // TODO: this is per subbenchmark!
                            },
                            .source => {
                                if (get_string(ptr, attrSpan.end)) |x|
                                    benchmarkData.set_source(ptr[x.start..x.end]);
                            },
                        }
                    }
                    // TODO: the skip starts too early
                    idx = skip_to_level(ptr, cmdSpan.end, 1, 0) orelse break;
                },
                .push => {
                    // calculate end of old level
                    try top.intervals.append(level_start_idx);
                    idx = skip_to_level(ptr, cmdSpan.end, 1, 0) orelse break;
                    try scopes.append(Scope{ .intervals = std.ArrayList(usize).init(allocator) });
                    top = &scopes.items[scopes.items.len - 1];
                    try top.intervals.append(idx);
                },
                .pop => {
                    try top.intervals.append(level_start_idx);
                    idx = skip_to_level(ptr, cmdSpan.end, 1, 0) orelse break;
                    top.intervals.deinit();
                    _ = scopes.pop();
                    top = &scopes.items[scopes.items.len - 1];
                    try top.intervals.append(idx);
                },
                .check_sat, .check_sat_assuming => {
                    try top.intervals.append(level_start_idx);
                    idx = skip_to_level(ptr, cmdSpan.end, 1, 0) orelse break;

                    try stdout.print("---------\n", .{});
                    try print_subproblem(stdout, ptr, &scopes, ptr[level_start_idx..idx]);
                    try stdout.print("---------\n", .{});
                    try bw.flush();
                    benchmarkData.subbenchmarkCount += 1;

                    try top.intervals.append(idx);
                },
                .exit => {
                    break;
                },
                else => {
                    idx = skip_to_level(ptr, cmdSpan.end, 1, 0) orelse break;
                },
            }
        } else {
            // Unkown command, do nothing
            idx = skip_to_level(ptr, cmdSpan.end, 1, 0) orelse break;
        }
    }

    benchmarkData.isIncremental = benchmarkData.subbenchmarkCount > 1;
    try benchmarkData.print(stdout);
    try bw.flush();
    return 0;
}
