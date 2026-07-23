"""conditions 模块测试 —— 安全条件求值器。

第一性原理：这个模块替代了原来的 eval，是安全关键点，必须覆盖：
基本比较、与/或组合、括号分组、类型容错、以及拒绝危险输入。
"""

import pytest

from jenpy.conditions import evaluate, ConditionError


# ---------- 基本比较 ----------

def test_eq_true():
    assert evaluate("branch == 'main'", {"branch": "main"}) is True


def test_eq_false():
    assert evaluate("branch == 'main'", {"branch": "dev"}) is False


def test_neq_true():
    assert evaluate("env != 'test'", {"env": "prod"}) is True


def test_neq_false():
    assert evaluate("env != 'test'", {"env": "test"}) is False


def test_double_quoted_string():
    assert evaluate('branch == "main"', {"branch": "main"}) is True


def test_undefined_var_treated_as_none():
    """未定义变量视为 None，与字符串比较应为 False。"""
    assert evaluate("missing == 'x'", {}) is False
    assert evaluate("missing != 'x'", {}) is True


def test_dotted_lookup():
    """支持 a.b.c 点号路径访问嵌套字典。"""
    ctx = {"git": {"ref": "main"}}
    assert evaluate("git.ref == 'main'", ctx) is True


# ---------- 逻辑组合 ----------

def test_and_both_true():
    assert evaluate("a == '1' and b == '2'", {"a": "1", "b": "2"}) is True


def test_and_one_false():
    assert evaluate("a == '1' and b == '2'", {"a": "1", "b": "x"}) is False


def test_or_one_true():
    assert evaluate("a == '1' or b == '2'", {"a": "1", "b": "x"}) is True


def test_or_both_false():
    assert evaluate("a == '1' or b == '2'", {"a": "x", "b": "y"}) is False


def test_precedence_and_over_or():
    """and 优先级高于 or：a=='1' or a=='2' and b=='3'
    等价于 a=='1' or (a=='2' and b=='3')"""
    ctx = {"a": "1", "b": "nope"}
    assert evaluate("a == '1' or a == '2' and b == '3'", ctx) is True


# ---------- 括号分组 ----------

def test_parens_change_precedence():
    """括号改变优先级：(a=='1' or a=='2') and b=='3'"""
    ctx = {"a": "2", "b": "3"}
    assert evaluate("(a == '1' or a == '2') and b == '3'", ctx) is True


def test_nested_parens():
    ctx = {"a": "1", "b": "2", "c": "3"}
    expr = "(a == '1' and b == '2') or (c == '9')"
    assert evaluate(expr, ctx) is True


# ---------- 类型容错 ----------

def test_number_literal():
    assert evaluate("count == 3", {"count": 3}) is True


def test_number_string_coerce():
    """数字与字符串形式宽松比较。"""
    assert evaluate("count == 3", {"count": "3"}) is True


def test_boolean_literal():
    assert evaluate("ok == true", {"ok": True}) is True
    assert evaluate("ok == false", {"ok": True}) is False


# ---------- 空表达式 ----------

def test_empty_expr_is_true():
    assert evaluate("", {}) is True
    assert evaluate("   ", {}) is True


# ---------- 错误输入应被拒绝 ----------

def test_reject_missing_operator():
    """只有标识符没有比较运算符应报错。"""
    with pytest.raises(ConditionError):
        evaluate("branch", {"branch": "main"})


def test_reject_greater_than():
    """不支持 > 运算符（刻意限制语法），应报错。"""
    with pytest.raises(ConditionError):
        evaluate("count > 5", {"count": 10})


def test_reject_unbalanced_parens():
    with pytest.raises(ConditionError):
        evaluate("(a == '1'", {"a": "1"})


def test_reject_invalid_token():
    with pytest.raises(ConditionError):
        evaluate("a == '1' @#$", {"a": "1"})


# ---------- 安全性：绝不能执行任意代码 ----------

def test_no_code_injection_via_function_call():
    """表达式里写函数调用应被拒绝，不能真的执行。"""
    with pytest.raises(ConditionError):
        evaluate("__import__('os').system('rm -rf /') == 'x'", {})


def test_no_attribute_access_execution():
    """点号只用于字典路径查找，不应触发方法调用。"""
    # 这会被当成嵌套字典查找，找不到返回 None，不会执行 system
    result = evaluate("os.system == 'anything'", {"os": {}})
    assert result is False
