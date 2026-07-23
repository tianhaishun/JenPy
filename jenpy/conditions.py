"""when 条件的安全求值器。

第一性原理：when 条件只需要回答一个问题——「某些变量的值，是否满足给定的等式/不等式」。
因此不需要 Python eval 的全部能力，只支持一个极小的、无副作用的语法子集即可。

支持的语法（刻意保持极小）：
  - 比较原子：  标识符 == 字面量   |   标识符 != 字面量
  - 字面量：    '...' 或 "..." 或 数字或 true/false/null
  - 组合：      <原子> and <原子>  |  <原子> or <原子>  |  ( ... )

例：
  branch == 'main'
  branch == 'main' and env != 'test'
  (branch == 'main' or branch == 'release') and env == 'prod'

实现方式：手写递归下降解析器。不调用 eval/exec，不导入任何东西，
因此即使配置文件来自不可信来源也不会有代码注入风险。
"""

from __future__ import annotations
import re
from typing import Any


class ConditionError(Exception):
    """条件表达式语法错误。"""


# ----------------- 词法 -----------------

_TOKEN_RE = re.compile(r"""
    \s*(
        (?:==|!=)              # 比较运算符
      | \(|\)                   # 括号
      | and\b|or\b              # 逻辑连接词
      | true\b|false\b|null\b   # 字面量
      | '(?:[^'\\]|\\.)*'       # 单引号字符串
      | "(?:[^"\\]|\\.)*"       # 双引号字符串
      | -?\d+(?:\.\d+)?         # 数字
      | [A-Za-z_][A-Za-z0-9_.]* # 标识符（含点号，支持 a.b.c）
    )
""", re.VERBOSE)


def _tokenize(expr: str) -> list:
    """把表达式切成 token 列表。"""
    tokens = []
    pos = 0
    while pos < len(expr):
        m = _TOKEN_RE.match(expr, pos)
        if not m or m.start(1) == -1:
            # 跳过纯空白
            if expr[pos].isspace():
                pos += 1
                continue
            raise ConditionError(f"无法解析的字符 '{expr[pos]}' 于位置 {pos}")
        tok = m.group(1)
        if tok is not None and tok != "":
            tokens.append(tok)
        pos = m.end()
    return tokens


# ----------------- 解析（递归下降） -----------------

class _Parser:
    """递归下降解析器，把 token 列表解析成布尔结果。

    文法：
      or_expr  := and_expr ( 'or' and_expr )*
      and_expr := not_expr ( 'and' not_expr )*
      atom     := '(' or_expr ')' | comparison
      comparison := IDENT ( '==' | '!=' ) literal
      literal  := STRING | NUMBER | 'true' | 'false' | 'null'
    """

    def __init__(self, tokens, context):
        self.tokens = tokens
        self.pos = 0
        self.context = context

    def _peek(self):
        return self.tokens[self.pos] if self.pos < len(self.tokens) else None

    def _next(self):
        tok = self._peek()
        self.pos += 1
        return tok

    def parse(self) -> bool:
        result = self._or_expr()
        if self.pos != len(self.tokens):
            raise ConditionError(f"表达式末尾有意外的 token: {self._peek()}")
        return result

    def _or_expr(self) -> bool:
        val = self._and_expr()
        while self._peek() == "or":
            self._next()
            rhs = self._and_expr()
            val = val or rhs
        return val

    def _and_expr(self) -> bool:
        val = self._atom()
        while self._peek() == "and":
            self._next()
            rhs = self._atom()
            val = val and rhs
        return val

    def _atom(self) -> bool:
        tok = self._peek()
        if tok == "(":
            self._next()
            val = self._or_expr()
            if self._peek() != ")":
                raise ConditionError("缺少右括号 ')'")
            self._next()
            return val
        return self._comparison()

    def _comparison(self) -> bool:
        ident = self._next()
        if ident is None:
            raise ConditionError("缺少左操作数")
        if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_.]*", ident):
            raise ConditionError(f"无效的标识符: {ident}")

        op = self._next()
        if op not in ("==", "!="):
            raise ConditionError(
                f"期望 '==' 或 '!='，得到 '{op}'。只支持相等/不等比较"
            )

        lit_tok = self._next()
        if lit_tok is None:
            raise ConditionError("缺少右操作数")

        left_val = _lookup(ident, self.context)
        right_val = _parse_literal(lit_tok)

        if op == "==":
            return _values_equal(left_val, right_val)
        return not _values_equal(left_val, right_val)


# ----------------- 值处理 -----------------

def _lookup(name: str, context: dict) -> Any:
    """从 context 取变量值；支持 a.b.c 点号路径；未定义返回 None。"""
    parts = name.split(".")
    cur = context
    for p in parts:
        if isinstance(cur, dict) and p in cur:
            cur = cur[p]
        else:
            return None
    return cur


def _parse_literal(tok: str):
    """把 token 解析成 Python 值。"""
    if tok in ("true", "false"):
        return tok == "true"
    if tok == "null":
        return None
    if tok.startswith("'") or tok.startswith('"'):
        # 去掉引号，反转义
        return _unescape(tok[1:-1])
    if re.fullmatch(r"-?\d+", tok):
        return int(tok)
    if re.fullmatch(r"-?\d+\.\d+", tok):
        return float(tok)
    # 未加引号的裸词，按字符串处理（容错）
    return tok


def _unescape(s: str) -> str:
    """简单反转义 \\' \\" \\\\ \\n。"""
    out = []
    i = 0
    while i < len(s):
        if s[i] == "\\" and i + 1 < len(s):
            nxt = s[i + 1]
            out.append({"n": "\n", "t": "\t", "\\": "\\",
                        "'": "'", '"': '"'}.get(nxt, nxt))
            i += 2
        else:
            out.append(s[i])
            i += 1
    return "".join(out)


def _values_equal(a, b) -> bool:
    """宽松相等：类型不同时尝试字符串比较，避免 'main' == main 的坑。"""
    if a == b:
        return True
    # 数字与字符串形式比较
    try:
        if isinstance(a, (int, float)) and isinstance(b, str):
            return str(a) == b
        if isinstance(b, (int, float)) and isinstance(a, str):
            return a == str(b)
    except Exception:
        pass
    return str(a) == str(b) if a is not None and b is not None else False


# ----------------- 公共入口 -----------------

def evaluate(expr: str, context: dict) -> bool:
    """求值 when 条件表达式，返回布尔结果。

    Args:
        expr: 条件表达式，如 "branch == 'main' and env != 'test'"
        context: 变量上下文

    Raises:
        ConditionError: 表达式语法不符合本模块支持的子集
    """
    expr = expr.strip()
    if not expr:
        return True
    tokens = _tokenize(expr)
    if not tokens:
        return True
    return _Parser(tokens, context).parse()
