const std = @import("std");
const print = std.debug.print;
const testing = std.testing;

pub const TokenType = enum {
    Symbol, // Includes constants etc.
    Opening,
    Closing,
    String, // Includes |.| symbols
};
pub const Token = struct { type: TokenType, span: []const u8 };

pub const TokenIterator = struct {
    data: []const u8,
    pos: usize = 0,
    cached: ?Token = null,

    pub fn next(self: *TokenIterator) ?Token {
        if (self.cached) |old| {
            self.cached = null;
            return old;
        }
        if (self.pos >= self.data.len) {
            // End of stream
            return null;
        }

        // Skip whitespace
        var in_comment = false;
        self.pos = while (self.pos < self.data.len) : ({
            self.pos += 1;
        }) {
            const char = self.data[self.pos];
            if (char == ';') {
                in_comment = true;
                continue;
            }
            if (in_comment and char == '\n') {
                in_comment = false;
                continue;
            }
            if (!in_comment and !(char == 9 or char == 10 or char == 13 or char == 32)) {
                break self.pos;
            }
        } else self.pos;

        if (self.pos == self.data.len)
            return null;
        switch (self.data[self.pos]) {
            '(' => {
                const ret: Token = .{
                    .type = TokenType.Opening,
                    .span = self.data[self.pos .. self.pos + 1],
                };
                self.pos += 1;
                return ret;
            },
            ')' => {
                const ret: Token = .{
                    .type = TokenType.Closing,
                    .span = self.data[self.pos .. self.pos + 1],
                };
                self.pos += 1;
                return ret;
            },
            '|' => {
                self.pos += 1;
                const start = self.pos;
                while (self.pos < self.data.len and self.data[self.pos] != '|')
                    self.pos += 1;
                const ret: Token = .{
                    .type = TokenType.String,
                    .span = self.data[start..self.pos],
                };
                self.pos += 1;
                return ret;
            },
            '"' => {
                self.pos += 1;
                const start = self.pos;
                while (self.pos < self.data.len) {
                    if (self.data[self.pos] == '"') {
                        if (self.pos < self.data.len - 1 and self.data[self.pos + 1] == '"') {
                            self.pos += 2;
                            continue;
                        }
                        break;
                    }
                    self.pos += 1;
                }
                const ret: Token = .{
                    .type = TokenType.String,
                    .span = self.data[start..self.pos],
                };
                self.pos += 1;
                return ret;
            },
            else => {},
        }

        // Symbol?
        const start = self.pos;
        while (self.pos < self.data.len) : ({
            self.pos += 1;
        }) {
            // TODO: this might be incomplete and lead to hangs:
            // everything that is not a whitespace and is not matched here.
            const char = self.data[self.pos];
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
                char == '#' or // Bitvector constant start
                (char >= '0' and char <= '9') or
                (char >= 'a' and char <= 'z') or
                (char >= 'A' and char <= 'Z')))
                break;
        }
        return .{ .type = TokenType.Symbol, .span = self.data[start..self.pos] };
    }

    pub fn peek(self: *TokenIterator) ?Token {
        if (self.cached) |old| {
            return old;
        }
        const token = self.next();
        self.cached = token;
        return token;
    }
};

test "tokenize" {
    const string =
        \\(foo "test")(bar)
        \\ (|bazbaz| "la""la")()
    ;

    var tkn = TokenIterator{ .data = string };

    var T = tkn.peek();
    try testing.expectEqual(TokenType.Opening, T.?.type);
    try testing.expectEqualStrings("(", T.?.span);
    T = tkn.next();
    try testing.expectEqual(TokenType.Opening, T.?.type);
    try testing.expectEqualStrings("(", T.?.span);
    T = tkn.next();
    try testing.expectEqual(TokenType.Symbol, T.?.type);
    try testing.expectEqualStrings("foo", T.?.span);
    T = tkn.next();
    try testing.expectEqual(TokenType.String, T.?.type);
    try testing.expectEqualStrings("test", T.?.span);
    T = tkn.next();
    try testing.expectEqual(TokenType.Closing, T.?.type);
    try testing.expectEqualStrings(")", T.?.span);
    T = tkn.next();
    try testing.expectEqual(TokenType.Opening, T.?.type);
    try testing.expectEqualStrings("(", T.?.span);
    T = tkn.next();
    try testing.expectEqual(TokenType.Symbol, T.?.type);
    try testing.expectEqualStrings("bar", T.?.span);
    T = tkn.next();
    try testing.expectEqual(TokenType.Closing, T.?.type);
    try testing.expectEqualStrings(")", T.?.span);
    T = tkn.next();
    try testing.expectEqual(TokenType.Opening, T.?.type);
    try testing.expectEqualStrings("(", T.?.span);
    T = tkn.next();
    try testing.expectEqual(TokenType.String, T.?.type);
    try testing.expectEqualStrings("bazbaz", T.?.span);
    T = tkn.next();
    try testing.expectEqual(TokenType.String, T.?.type);
    try testing.expectEqualStrings("la\"\"la", T.?.span);
    T = tkn.next();
    try testing.expectEqual(TokenType.Closing, T.?.type);
    try testing.expectEqualStrings(")", T.?.span);
    T = tkn.next();
    try testing.expectEqual(TokenType.Opening, T.?.type);
    try testing.expectEqualStrings("(", T.?.span);
    T = tkn.next();
    try testing.expectEqual(TokenType.Closing, T.?.type);
    try testing.expectEqualStrings(")", T.?.span);
}
