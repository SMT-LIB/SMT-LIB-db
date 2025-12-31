const std = @import("std");
const testing = std.testing;

const symbols_file = @embedFile("./smtlib-symbols");

const map_type = struct { []const u8, usize };

const symbols = blk: {
    @setEvalBranchQuota(10000);

    var idx: usize = 0;
    var symbol_list: []const map_type = &.{};
    var symbol_iterator = std.mem.splitScalar(u8, symbols_file, '\n');
    while (symbol_iterator.next()) |symbol| {
        if (symbol.len == 0) continue;
        if (symbol[0] != ';') {
            symbol_list = symbol_list ++ &[_]map_type{.{ symbol, idx }};
            idx += 1;
        }
    }

    break :blk symbol_list;
};

pub const symbol_map = blk: {
    @setEvalBranchQuota(10000);
    break :blk std.StaticStringMap(usize).initComptime(symbols);
};

test "symbol_map" {
    try testing.expectEqual(204, symbol_map.kvs.len);
}
