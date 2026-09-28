#!/usr/bin/env python3
"""prolanwo++ — интерпретатор v1."""
import sys


class ProlanwoError(Exception): pass
class ProlanwoSyntaxError(ProlanwoError): pass
class ProlanwoRuntimeError(ProlanwoError): pass


class ReturnSignal(Exception):
    def __init__(self, value): self.value = value


class StopSignal(Exception): pass
class StopFurtSignal(Exception): pass


# ============================================================
# ЛЕКСЕР
# ============================================================
class Token:
    __slots__ = ('type', 'value', 'line', 'col')
    def __init__(self, t, v, line, col):
        self.type = t; self.value = v; self.line = line; self.col = col


KEYWORDS = {
    'variable': 'VARIABLE', 'change': 'CHANGE', 'briout': 'BRIOUT',
    'input': 'INPUT', 'notchan': 'NOTCHAN',
    'true': 'TRUE', 'false': 'FALSE',
    'if': 'IF', 'or': 'OR',
    'replay': 'REPLAY', 'begin': 'BEGIN',
    'function': 'FUNCTION', 'return': 'RETURN',
    'array': 'ARRAY', 'new': 'NEW', 'object': 'OBJECT',
    'import': 'IMPORT', 'history': 'HISTORY', 'rollback': 'ROLLBACK',
    'stop': 'STOP', 'stopfurt': 'STOPFURT',
}
TYPES = {'line', 'number', 'trufal'}


class Lexer:
    def __init__(self, src):
        self.src = src; self.pos = 0
        self.line = 1; self.col = 1
        self.tokens = []

    def error(self, msg):
        raise ProlanwoSyntaxError(
            f"{msg} (строка {self.line}, колонка {self.col})")

    def peek(self, o=0):
        i = self.pos + o
        return self.src[i] if i < len(self.src) else ''

    def advance(self):
        if self.pos >= len(self.src): return ''
        ch = self.src[self.pos]; self.pos += 1
        if ch == '\n': self.line += 1; self.col = 1
        else: self.col += 1
        return ch

    def add(self, t, v):
        self.tokens.append(Token(t, v, self.line, self.col))

    def tokenize(self):
        while self.pos < len(self.src):
            ch = self.peek()
            if ch in ' \t\r\n':
                self.advance(); continue
            if ch == '\\' and self.peek(1) == '"':
                self.read_line_comment(); continue
            if ch == '\\' and self.peek(1) == '$':
                self.read_block_comment(); continue
            if ch == '"':
                self.read_string(); continue
            if ch.isdigit():
                self.read_number(); continue
            if ch.isalpha() or ch == '_':
                self.read_word(); continue

            two = ch + self.peek(1)
            if two == '$$': self.add('AND', '$$'); self.advance(); self.advance(); continue
            if two == '$#': self.add('OROP', '$#'); self.advance(); self.advance(); continue
            if two == '==': self.add('EQEQ', '=='); self.advance(); self.advance(); continue
            if two == '!=': self.add('NEQ', '!='); self.advance(); self.advance(); continue
            if two == '<=': self.add('LE', '<='); self.advance(); self.advance(); continue
            if two == '>=': self.add('GE', '>='); self.advance(); self.advance(); continue

            simple = {
                ';': 'SEMI', '_': 'ASSIGN',
                '[': 'LBRACKET', ']': 'RBRACKET',
                '(': 'LPAREN', ')': 'RPAREN',
                '{': 'LBRACE', '}': 'RBRACE',
                '+': 'PLUS', '-': 'MINUS',
                '*': 'STAR', '/': 'SLASH',
                '.': 'DOT', ',': 'COMMA', ':': 'COLON',
                '=': 'EQ', '<': 'LT', '>': 'GT',
            }
            if ch in simple:
                self.add(simple[ch], ch); self.advance(); continue
            self.error(f"Неизвестный символ: {ch!r}")
        self.add('EOF', None)
        return self.tokens

    def read_string(self):
        self.advance()
        result = []
        while self.pos < len(self.src) and self.peek() != '"':
            if self.peek() == '\\':
                self.advance(); result.append(self.advance())
            else:
                result.append(self.advance())
        if self.pos >= len(self.src):
            self.error("Незакрытая строка")
        self.advance()
        value = ''.join(result).replace('(tr', '\n')
        self.add('STRING', value)

    def read_number(self):
        start = self.pos
        while self.peek().isdigit(): self.advance()
        if self.peek() == '.' and self.peek(1).isdigit():
            self.advance()
            while self.peek().isdigit(): self.advance()
        self.add('NUMBER', self.src[start:self.pos])

    def read_word(self):
        start = self.pos
        while self.peek().isalnum() or self.peek() == '_':
            self.advance()
        word = self.src[start:self.pos]
        low = word.lower()
        if low in KEYWORDS: self.add(KEYWORDS[low], word)
        elif low in TYPES: self.add('TYPE', low)
        else: self.add('IDENT', word)

    def read_line_comment(self):
        self.advance(); self.advance()
        while self.pos < len(self.src):
            if self.peek() == '"' and self.peek(1) == '/':
                self.advance(); self.advance(); return
            self.advance()
        self.error("Незакрытый комментарий")

    def read_block_comment(self):
        self.advance(); self.advance(); self.advance()
        while self.pos < len(self.src):
            if (self.peek() == '"' and self.peek(1) == '$'
                    and self.peek(2) == '/'):
                self.advance(); self.advance(); self.advance(); return
            self.advance()
        self.error("Незакрытый комментарий")


# ============================================================
# AST
# ============================================================
class Node: pass
class Program(Node):
    def __init__(self, s): self.statements = s
class VarDecl(Node):
    def __init__(self, t, n, v, saved=False):
        self.type=t; self.name=n; self.value=v; self.saved=saved
class VarChange(Node):
    def __init__(self, n, v): self.name=n; self.value=v
class Print(Node):
    def __init__(self, e): self.expr=e
class NotChan(Node):
    def __init__(self, n): self.name=n
class If(Node):
    def __init__(self, c, b, e, eb):
        self.cond=c; self.body=b; self.elifs=e; self.else_body=eb
class Replay(Node):
    def __init__(self, c, b): self.cond=c; self.body=b
class FunctionDecl(Node):
    def __init__(self, n, p, b):
        self.name=n; self.params=p; self.body=b
class Return(Node):
    def __init__(self, v): self.value=v
class ArrayDecl(Node):
    def __init__(self, n, e, u=False):
        self.name=n; self.elements=e; self.unlimited=u
class ArrayAdd(Node):
    def __init__(self, n, v): self.name=n; self.value=v
class Import(Node):
    def __init__(self, m, o): self.module=m; self.obj=o
class Rollback(Node):
    def __init__(self, n, i=None): self.name=n; self.index=i
class StopNode(Node): pass
class StopFurtNode(Node): pass


class Number(Node):
    def __init__(self, v): self.value=v
class String(Node):
    def __init__(self, v): self.value=v
class Bool(Node):
    def __init__(self, v): self.value=v
class VarRef(Node):
    def __init__(self, n): self.name=n
class BinOp(Node):
    def __init__(self, op, l, r): self.op=op; self.left=l; self.right=r
class Input(Node):
    def __init__(self, p): self.prompt=p
class Call(Node):
    def __init__(self, n, a): self.name=n; self.args=a
class ArrayAccess(Node):
    def __init__(self, n, i): self.name=n; self.index=i
class RandomNumber(Node):
    def __init__(self, lo, hi): self.low=lo; self.high=hi
class RandomArray(Node):
    def __init__(self, n): self.name=n
class HistoryRef(Node):
    def __init__(self, n): self.name=n


# ============================================================
# ПАРСЕР
# ============================================================
class Parser:
    def __init__(self, tokens):
        self.tokens = tokens; self.pos = 0

    def peek(self, o=0):
        i = self.pos + o
        return self.tokens[i] if i < len(self.tokens) else self.tokens[-1]

    def advance(self):
        tok = self.tokens[self.pos]
        if tok.type != 'EOF': self.pos += 1
        return tok

    def check(self, t): return self.peek().type == t

    def match(self, t):
        if self.check(t): return self.advance()
        return None

    def expect(self, t, m=None):
        if self.check(t): return self.advance()
        tok = self.peek()
        raise ProlanwoSyntaxError(
            f"Ожидалось {m or t}, получено {tok.type} "
            f"{tok.value!r} (строка {tok.line})")

    def parse(self):
        s = []
        while not self.check('EOF'):
            s.append(self.statement())
        return Program(s)

    def statement(self):
        t = self.peek()
        if t.type == 'VARIABLE': return self.var_decl()
        if t.type == 'CHANGE': return self.var_change()
        if t.type == 'BRIOUT': return self.print_stmt()
        if t.type == 'NOTCHAN': return self.notchan_stmt()
        if t.type == 'IF': return self.if_stmt()
        if t.type == 'REPLAY': return self.replay_stmt()
        if t.type == 'FUNCTION': return self.function_decl()
        if t.type == 'RETURN': return self.return_stmt()
        if t.type == 'ARRAY': return self.array_decl()
        if t.type == 'NEW': return self.new_object_stmt()
        if t.type == 'IMPORT': return self.import_stmt()
        if t.type == 'ROLLBACK': return self.rollback_stmt()
        if t.type == 'STOP': self.advance(); self.expect('SEMI'); return StopNode()
        if t.type == 'STOPFURT': self.advance(); self.expect('SEMI'); return StopFurtNode()
        raise ProlanwoSyntaxError(
            f"Неизвестная инструкция: {t.value!r} (строка {t.line})")

    def var_decl(self):
        self.advance()
        ty = self.expect('TYPE').value
        self.expect('LBRACKET')
        name = self.expect('IDENT').value
        self.expect('RBRACKET')
        v = None; saved = False
        if self.match('ASSIGN'):
            if self.check('IDENT') and self.peek().value.lower() == 'savichan':
                saved = True
                self.advance()
                self.expect('LPAREN')
                v = self.expression()
                self.expect('RPAREN')
            else:
                v = self.expression()
        self.expect('SEMI')
        return VarDecl(ty, name, v, saved)

    def var_change(self):
        self.advance(); self.expect('VARIABLE')
        self.expect('LBRACKET')
        n = self.expect('IDENT').value
        self.expect('RBRACKET'); self.expect('ASSIGN')
        v = self.expression()
        self.expect('SEMI')
        return VarChange(n, v)

    def print_stmt(self):
        self.advance(); self.expect('LPAREN')
        e = self.expression()
        self.expect('RPAREN'); self.expect('SEMI')
        return Print(e)

    def notchan_stmt(self):
        self.advance()
        n = self.expect('IDENT').value
        self.expect('SEMI')
        return NotChan(n)

    def if_stmt(self):
        self.advance(); self.expect('LPAREN')
        c = self.expression()
        self.expect('RPAREN'); self.expect('LT')
        b = []
        while not self.check('GT') and not self.check('EOF'):
            b.append(self.statement())
        self.expect('GT')
        el = []; eb = None
        while self.check('OR'):
            self.advance()
            if self.check('IF'):
                self.advance(); self.expect('LPAREN')
                cc = self.expression()
                self.expect('RPAREN'); self.expect('LT')
                bb = []
                while not self.check('GT') and not self.check('EOF'):
                    bb.append(self.statement())
                self.expect('GT')
                el.append((cc, bb))
            else:
                self.expect('LT')
                eb = []
                while not self.check('GT') and not self.check('EOF'):
                    eb.append(self.statement())
                self.expect('GT')
                break
        return If(c, b, el, eb)

    def replay_stmt(self):
        self.advance(); self.expect('LPAREN')
        c = self.expression()
        self.expect('RPAREN'); self.expect('BEGIN'); self.expect('LBRACE')
        b = []
        while not self.check('RBRACE') and not self.check('EOF'):
            b.append(self.statement())
        self.expect('RBRACE')
        return Replay(c, b)

    def function_decl(self):
        self.advance()
        n = self.expect('IDENT', 'имя функции').value
        if not n or not n[0].isupper():
            raise ProlanwoSyntaxError(f"Имя функции должно с большой буквы: {n}")
        self.expect('LPAREN')
        p = []
        if not self.check('RPAREN'):
            while True:
                pt = self.expect('TYPE').value
                self.expect('LBRACKET')
                pn = self.expect('IDENT').value
                self.expect('RBRACKET')
                p.append((pt, pn))
                if not self.match('COMMA'): break
        self.expect('RPAREN'); self.expect('EQ'); self.expect('LPAREN')
        b = []
        while not self.check('RPAREN') and not self.check('EOF'):
            b.append(self.statement())
        self.expect('RPAREN')
        if not self._has_return(b):
            raise ProlanwoSyntaxError(f"Функция {n} должна содержать return")
        return FunctionDecl(n, p, b)

    def _has_return(self, stmts):
        for s in stmts:
            if isinstance(s, Return): return True
            if isinstance(s, If):
                if self._has_return(s.body): return True
                for _, bb in s.elifs:
                    if self._has_return(bb): return True
                if s.else_body and self._has_return(s.else_body): return True
        return False

    def return_stmt(self):
        self.advance()
        v = self.expression()
        self.expect('SEMI')
        return Return(v)

    def array_decl(self):
        self.advance()
        self.expect('LBRACKET')
        n = self.expect('IDENT').value
        self.expect('RBRACKET')
        u = False
        if self.match('ASSIGN'):
            t = self.expect('IDENT')
            if t.value.lower() != 'unlimited':
                raise ProlanwoSyntaxError("Ожидалось unlimited")
            u = True
        self.expect('LBRACKET')
        el = []
        while not self.check('RBRACKET') and not self.check('EOF'):
            el.append(self.expression())
            self.expect('SEMI')
        self.expect('RBRACKET')
        return ArrayDecl(n, el, u)

    def new_object_stmt(self):
        self.advance(); self.expect('OBJECT'); self.expect('ARRAY')
        self.expect('LBRACKET')
        n = self.expect('IDENT').value
        self.expect('RBRACKET'); self.expect('ASSIGN')
        v = self.expression()
        self.expect('SEMI')
        return ArrayAdd(n, v)

    def import_stmt(self):
        self.advance(); self.expect('STAR')
        m = self.expect('IDENT').value
        self.expect('COLON')
        o = self.expect('IDENT').value
        self.expect('LBRACKET'); self.expect('IDENT'); self.expect('RBRACKET')
        self.expect('STAR'); self.expect('SEMI')
        return Import(m, o)

    def rollback_stmt(self):
        self.advance(); self.expect('VARIABLE'); self.expect('LBRACKET')
        n = self.expect('IDENT').value
        self.expect('RBRACKET')
        i = None
        if self.match('LBRACKET'):
            i = self.expression()
            self.expect('RBRACKET')
        self.expect('SEMI')
        return Rollback(n, i)

    def expression(self): return self.logic_or()

    def logic_or(self):
        l = self.logic_and()
        while self.check('OROP'):
            self.advance()
            r = self.logic_and()
            l = BinOp('OROP', l, r)
        return l

    def logic_and(self):
        l = self.comparison()
        while self.check('AND'):
            self.advance()
            r = self.comparison()
            l = BinOp('AND', l, r)
        return l

    def comparison(self):
        l = self.additive()
        while self.peek().type in ('EQEQ', 'NEQ', 'LT', 'GT', 'LE', 'GE'):
            op = self.advance().type
            r = self.additive()
            l = BinOp(op, l, r)
        return l

    def additive(self):
        l = self.multiplicative()
        while self.check('PLUS') or self.check('MINUS'):
            op = self.advance().type
            r = self.multiplicative()
            l = BinOp(op, l, r)
        return l

    def multiplicative(self):
        l = self.primary()
        while self.check('STAR') or self.check('SLASH'):
            op = self.advance().type
            r = self.primary()
            l = BinOp(op, l, r)
        return l

    def primary(self):
        t = self.peek()
        if t.type == 'NUMBER':
            self.advance()
            return Number(float(t.value) if '.' in t.value else int(t.value))
        if t.type == 'STRING': self.advance(); return String(t.value)
        if t.type == 'TRUE': self.advance(); return Bool(True)
        if t.type == 'FALSE': self.advance(); return Bool(False)
        if t.type == 'INPUT':
            self.advance(); self.expect('LPAREN')
            p = None
            if self.check('STRING'): p = self.advance().value
            self.expect('RPAREN')
            return Input(p)
        if t.type == 'HISTORY':
            self.advance(); self.expect('LBRACKET')
            n = self.expect('IDENT').value
            self.expect('RBRACKET')
            return HistoryRef(n)
        if t.type == 'ARRAY':
            self.advance(); self.expect('LBRACKET')
            n = self.expect('IDENT').value
            self.expect('RBRACKET'); self.expect('LBRACKET')
            i = self.expression()
            self.expect('RBRACKET')
            return ArrayAccess(n, i)
        if t.type == 'IDENT':
            if t.value == 'random' and self.peek(1).type == 'DOT':
                self.advance(); self.expect('DOT')
                k = self.expect('IDENT').value.lower()
                self.expect('LBRACKET')
                if k == 'number':
                    lo = self.expression(); self.expect('COMMA')
                    hi = self.expression(); self.expect('RBRACKET')
                    return RandomNumber(lo, hi)
                else:
                    n = self.expect('IDENT').value
                    self.expect('RBRACKET')
                    return RandomArray(n)
            if self.peek(1).type == 'LPAREN':
                n = self.advance().value
                self.expect('LPAREN')
                a = []
                if not self.check('RPAREN'):
                    while True:
                        a.append(self.expression())
                        if not self.match('COMMA'): break
                self.expect('RPAREN')
                return Call(n, a)
            self.advance()
            return VarRef(t.value)
        if t.type == 'LPAREN':
            self.advance()
            e = self.expression()
            self.expect('RPAREN')
            return e
        raise ProlanwoSyntaxError(
            f"Неожиданный токен: {t.type} {t.value!r} (строка {t.line})")


# ============================================================
# ИНТЕРПРЕТАТОР
# ============================================================
class Interpreter:
    def __init__(self):
        self.vars = {}; self.types = {}; self.protected = set()
        self.arrays = {}; self.array_limits = {}
        self.functions = {}
        self.history = {}; self.history_pos = {}; self.saved = set()
        self.modules = set()

    def run(self, program):
        for s in program.statements:
            self.exec_stmt(s)

    def exec_stmt(self, n):
        if isinstance(n, VarDecl): self.exec_var_decl(n)
        elif isinstance(n, VarChange): self.exec_var_change(n)
        elif isinstance(n, Print): self.exec_print(n)
        elif isinstance(n, NotChan): self.exec_notchan(n)
        elif isinstance(n, If): self.exec_if(n)
        elif isinstance(n, Replay): self.exec_replay(n)
        elif isinstance(n, FunctionDecl): self.functions[n.name] = n
        elif isinstance(n, Return): raise ReturnSignal(self.eval(n.value))
        elif isinstance(n, ArrayDecl): self.exec_array_decl(n)
        elif isinstance(n, ArrayAdd): self.exec_array_add(n)
        elif isinstance(n, Import): self.modules.add(n.module)
        elif isinstance(n, Rollback): self.exec_rollback(n)
        elif isinstance(n, StopNode): raise StopSignal()
        elif isinstance(n, StopFurtNode): raise StopFurtSignal()
        else:
            raise ProlanwoRuntimeError(f"Неизвестный узел: {n}")

    def exec_var_decl(self, n):
        if n.name in self.vars:
            raise ProlanwoRuntimeError(f"Переменная {n.name} уже существует")
        v = self.eval(n.value) if n.value is not None else None
        self.check_type(n.type, v, n.name)
        self.vars[n.name] = v
        self.types[n.name] = n.type
        if n.saved:
            self.saved.add(n.name)
            self.history[n.name] = [v]
            self.history_pos[n.name] = 0

    def exec_var_change(self, n):
        if n.name in self.protected:
            raise ProlanwoRuntimeError(f"Переменная {n.name} защищена")
        v = self.eval(n.value)
        if n.name not in self.vars:
            self.vars[n.name] = v
            self.types[n.name] = self.infer_type(v)
        else:
            self.check_type(self.types[n.name], v, n.name)
            self.vars[n.name] = v
            if n.name in self.saved:
                self.history[n.name] = self.history[n.name][:self.history_pos[n.name] + 1]
                self.history[n.name].append(v)
                self.history_pos[n.name] = len(self.history[n.name]) - 1

    def exec_print(self, n):
        print(self.to_string(self.eval(n.expr)))

    def exec_notchan(self, n):
        if n.name not in self.vars:
            raise ProlanwoRuntimeError(f"Переменная {n.name} не найдена")
        self.protected.add(n.name)

    def exec_if(self, n):
        if self.to_bool(self.eval(n.cond)):
            for s in n.body: self.exec_stmt(s)
            return
        for c, b in n.elifs:
            if self.to_bool(self.eval(c)):
                for s in b: self.exec_stmt(s)
                return
        if n.else_body:
            for s in n.else_body: self.exec_stmt(s)

    def exec_replay(self, n):
        while self.to_bool(self.eval(n.cond)):
            stop = False
            for s in n.body:
                try:
                    self.exec_stmt(s)
                except StopSignal:
                    stop = True; break
                except StopFurtSignal:
                    break
            if stop: break

    def exec_array_decl(self, n):
        if n.name in self.arrays:
            raise ProlanwoRuntimeError(f"Массив {n.name} уже есть")
        if not n.unlimited and len(n.elements) > 100000:
            raise ProlanwoRuntimeError("Превышен лимит массива")
        self.arrays[n.name] = [self.eval(e) for e in n.elements]
        self.array_limits[n.name] = None if n.unlimited else 100000

    def exec_array_add(self, n):
        if n.name not in self.arrays:
            raise ProlanwoRuntimeError(f"Массив {n.name} не найден")
        l = self.array_limits.get(n.name)
        if l is not None and len(self.arrays[n.name]) >= l:
            raise ProlanwoRuntimeError(f"Массив {n.name} достиг лимита")
        self.arrays[n.name].append(self.eval(n.value))

    def exec_rollback(self, n):
        if n.name not in self.saved:
            raise ProlanwoRuntimeError(f"Переменная {n.name} не сохранена")
        h = self.history[n.name]
        p = self.history_pos[n.name]
        if n.index is None:
            if p > 0: p -= 1
        else:
            idx = int(self.eval(n.index))
            if 0 <= idx < len(h): p = idx
        self.history_pos[n.name] = p
        self.vars[n.name] = h[p]

    def eval(self, n):
        if isinstance(n, Number): return n.value
        if isinstance(n, String): return n.value
        if isinstance(n, Bool): return n.value
        if isinstance(n, Input):
            if n.prompt: print(n.prompt, end='', flush=True)
            return input()
        if isinstance(n, VarRef):
            if n.name not in self.vars:
                raise ProlanwoRuntimeError(f"Переменная {n.name} не найдена")
            return self.vars[n.name]
        if isinstance(n, BinOp): return self.eval_binop(n)
        if isinstance(n, Call): return self.eval_call(n)
        if isinstance(n, ArrayAccess):
            if n.name not in self.arrays:
                raise ProlanwoRuntimeError(f"Массив {n.name} не найден")
            i = int(self.eval(n.index))
            a = self.arrays[n.name]
            if i < 0 or i >= len(a):
                raise ProlanwoRuntimeError(f"Индекс {i} вне границ")
            return a[i]
        if isinstance(n, RandomNumber):
            import random
            lo = int(self.eval(n.low)); hi = int(self.eval(n.high))
            if hi < lo: lo, hi = hi, lo
            if hi > 100000: raise ProlanwoRuntimeError("Лимит 100000")
            return random.randint(lo, hi)
        if isinstance(n, RandomArray):
            import random
            if n.name not in self.arrays:
                raise ProlanwoRuntimeError("Массив не найден")
            a = self.arrays[n.name]
            if not a: raise ProlanwoRuntimeError("Пустой массив")
            return random.choice(a)
        if isinstance(n, HistoryRef):
            if n.name not in self.history:
                raise ProlanwoRuntimeError("История не найдена")
            return list(self.history[n.name])
        raise ProlanwoRuntimeError(f"Неизвестное выражение")

    def eval_binop(self, n):
        op = n.op
        if op == 'AND':
            if not self.to_bool(self.eval(n.left)): return False
            return self.to_bool(self.eval(n.right))
        if op == 'OROP':
            if self.to_bool(self.eval(n.left)): return True
            return self.to_bool(self.eval(n.right))
        l = self.eval(n.left); r = self.eval(n.right)
        if op == 'PLUS':
            if isinstance(l, str) or isinstance(r, str):
                return self.to_string(l) + self.to_string(r)
            return l + r
        if op == 'MINUS': return l - r
        if op == 'STAR': return l * r
        if op == 'SLASH':
            if r == 0: raise ProlanwoRuntimeError("Деление на ноль")
            return l / r
        if op == 'EQEQ': return l == r
        if op == 'NEQ': return l != r
        if op == 'LT': return l < r
        if op == 'GT': return l > r
        if op == 'LE': return l <= r
        if op == 'GE': return l >= r
        raise ProlanwoRuntimeError(f"Оператор {op}")

    def eval_call(self, n):
        if n.name not in self.functions:
            raise ProlanwoRuntimeError(f"Функция {n.name} не найдена")
        fn = self.functions[n.name]
        if len(n.args) != len(fn.params):
            raise ProlanwoRuntimeError("Неверное число аргументов")
        sv = dict(self.vars); st = dict(self.types)
        for (pt, pn), a in zip(fn.params, n.args):
            v = self.eval(a)
            self.check_type(pt, v, pn)
            self.vars[pn] = v
            self.types[pn] = pt
        try:
            for s in fn.body: self.exec_stmt(s)
            raise ProlanwoRuntimeError(f"Функция {n.name} не вернула значение")
        except ReturnSignal as rs:
            result = rs.value
        finally:
            self.vars = sv; self.types = st
        return result

    def to_bool(self, v):
        if isinstance(v, bool): return v
        if v is None: return False
        if isinstance(v, (int, float)): return v != 0
        if isinstance(v, str): return len(v) > 0
        return bool(v)

    def to_string(self, v):
        if v is None: return ""
        if v is True: return "True"
        if v is False: return "False"
        if isinstance(v, list):
            return "[" + ", ".join(self.to_string(x) for x in v) + "]"
        return str(v)

    def infer_type(self, v):
        if isinstance(v, bool): return 'trufal'
        if isinstance(v, str): return 'line'
        if isinstance(v, (int, float)): return 'number'
        return 'unknown'

    def check_type(self, t, v, n):
        if v is None: return
        if t == 'line' and not isinstance(v, str):
            raise ProlanwoRuntimeError(f"Переменная {n}: нужен line")
        if t == 'number' and (isinstance(v, bool) or not isinstance(v, (int, float))):
            raise ProlanwoRuntimeError(f"Переменная {n}: нужен number")
        if t == 'trufal' and not isinstance(v, bool):
            raise ProlanwoRuntimeError(f"Переменная {n}: нужен TruFal")


# ============================================================
# ЗАПУСК
# ============================================================
def run(source):
    tokens = Lexer(source).tokenize()
    program = Parser(tokens).parse()
    Interpreter().run(program)


def main():
    args = sys.argv[1:]
    if len(args) >= 2 and args[0] == '-e':
        source = args[1]
    elif len(args) >= 1:
        try:
            with open(args[0], 'r', encoding='utf-8') as f:
                source = f.read()
        except FileNotFoundError:
            print(f"Файл не найден: {args[0]}")
            sys.exit(1)
    else:
        source = (
            'variable line[name]_"Гордей";\n'
            'briout("Привет, " + name + "!");\n'
        )
    try:
        run(source)
    except ProlanwoError as e:
        print(f"Ошибка prolanwo++: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == '__main__':
    main()
