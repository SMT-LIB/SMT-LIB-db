const std = @import("std");
const symbols = @import("symbols.zig").symbol_map;

pub const BenchmarkData = struct {
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
    queryCount: usize = 0,
    isIncremental: bool = false,

    pub fn print(self: BenchmarkData, out: anytype) !void {
        const options = std.json.StringifyOptions{ .whitespace = .minified };
        try std.json.stringify(self, options, out);
    }

    const SourceField = enum {
        generatedBy,
        generatedOn,
        application,
        targetSolver,
        generator,
    };

    const SourceMap = std.ComptimeStringMap(SourceField, .{
        .{ "Generated by", .generatedBy },
        .{ "Generated on", .generatedOn },
        .{ "Application", .application },
        .{ "Target solver", .targetSolver },
        .{ "Generator", .generator },
        // Alternative capitalization
        .{ "Generated By", .generatedBy },
        .{ "Generated On", .generatedOn },
        .{ "Target Solver", .targetSolver },
    });

    pub fn set_source(self: *BenchmarkData, str: []const u8) void {
        var idx: usize = 0;
        var line_start: usize = 0;
        var colon: usize = 0;
        while (idx <= str.len) : (idx += 1) {
            if (idx == str.len or str[idx] == '\n') {
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
            } else {
                if (colon == 0 and str[idx] == ':')
                    colon = idx;
            }
        }
        // At least one character left
        if ((idx + 1) < str.len) {
            const text = std.mem.trim(u8, str[idx..str.len], " \t\n\r");
            self.description = text;
        }
    }
};

pub const QueryData = struct {
    normalizedSize: usize = 0,
    compressedSize: usize = 0,
    assertsCount: usize = 0,
    declareFunCount: usize = 0,
    declareConstCount: usize = 0, // Also count funs without argument
    declareSortCount: usize = 0,
    defineFunCount: usize = 0,
    defineFunRecCount: usize = 0,
    constantFunCount: usize = 0, // Count defined funs without argument
    defineSortCount: usize = 0,
    declareDatatypeCount: usize = 0,
    maxTermDepth: usize = 0,
    status: ?[]const u8 = null,
    symbolFrequency: [symbols.kvs.len]usize = [_]usize{0} ** symbols.kvs.len,

    pub fn print(self: QueryData, out: anytype) !void {
        const options = std.json.StringifyOptions{ .whitespace = .minified };
        try std.json.stringify(self, options, out);
    }
};

pub const Scope = struct {
    intervals: std.ArrayList(usize),
    data: QueryData = .{},
};
