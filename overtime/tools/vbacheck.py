#!/usr/bin/env python3
"""Static checks on the VBA module, for the things VBA refuses to compile.

Excel is the only real compiler, but these three classes of mistake are
cheap to catch here and expensive to catch by hand:

  1. identifiers that collide with a VBA reserved word (VBA is case-
     insensitive, so `tO` is the keyword `To`)
  2. unbalanced block statements (If/End If, For/Next, With/End With, ...)
  3. calls to procedures that do not exist, or with the wrong argument count
  4. On Error GoTo targets with no matching label
"""
import os
import re
import sys

BAS = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                   "OvertimeReport.bas")

RESERVED = set(w.lower() for w in """
Abs AddressOf Alias And As Attribute Boolean ByRef Byte ByVal Call Case CBool CByte
CCur CDate CDbl CDec CInt CLng Close Const Currency CVar CVErr Date Debug Decimal
Declare Dim Dir Do Double Each Else ElseIf Empty End Enum Eqv Erase Err Error Event
Exit False Fix For Friend Function Get Global GoSub GoTo If Imp Implements In InStr
Int Integer Is Len Let Lib Like Line Load Long Loop LSet Me Mid Mod New Next Not
Nothing Null Object On Open Option Optional Or ParamArray Preserve Print Private
Property Public Put RaiseEvent ReDim Rem Resume Return RSet Seek Select Set Single
Spc Static Step Stop String Sub Tab Then Time To True Type TypeOf Unload Until
Variant Wend While With WithEvents Write Xor Left Right Trim Val Str Format Replace
Split Join Array IsArray IsEmpty IsNumeric CStr Now Cells Range Rows Columns Sheets
""".split())


def logical_lines(raw):
    """Strip comments, join `_` continuations; yields (first_lineno, text)."""
    out = []
    buf, start = "", None
    for ln, line in enumerate(raw, 1):
        if line.lstrip().startswith("'"):
            body = ""
        else:
            body = re.sub(r'"[^"]*"', lambda m: "\x00" * len(m.group(0)), line)
            cut = body.find("'")
            body = line[:cut].rstrip() if cut >= 0 else line.rstrip()
        if start is None:
            start = ln
        if body.endswith("_"):
            buf += body[:-1]
            continue
        out.append((start, buf + body))
        buf, start = "", None
    if buf:
        out.append((start, buf))
    return out


def split_statements(text):
    """VBA allows `a = 1: b = 2` -- split on `:` outside quotes, but keep labels."""
    parts, cur, in_str = [], "", False
    for ch in text:
        if ch == '"':
            in_str = not in_str
        if ch == ":" and not in_str:
            parts.append(cur)
            cur = ""
        else:
            cur += ch
    parts.append(cur)
    return parts


def check(path):
    raw = open(path, encoding="utf-8").read().split("\n")
    lines = logical_lines(raw)
    problems = []

    # ---- procedure table -------------------------------------------------
    procs = {}
    for ln, s in lines:
        m = re.match(r"\s*(?:Public\s+|Private\s+)?(Sub|Function)\s+([A-Za-z_]\w*)\s*\((.*?)\)",
                     s)
        if m:
            args = [a for a in m.group(3).split(",") if a.strip()]
            required = sum(0 if re.search(r"\bOptional\b", a) else 1 for a in args)
            procs[m.group(2).lower()] = (m.group(2), required, len(args), ln)

    # ---- declared identifiers vs reserved words --------------------------
    for ln, s in lines:
        decls = []
        m = re.match(r"\s*(?:Dim|Static)\s+(.*)", s)
        if m:
            decls = m.group(1).split(",")
        m = re.search(r"\b(?:Sub|Function)\s+[A-Za-z_]\w*\s*\((.*?)\)", s)
        if m and m.group(1).strip():
            decls += m.group(1).split(",")
        for part in decls:
            nm = re.search(r"(?:ByVal\s+|ByRef\s+|Optional\s+|ParamArray\s+)*([A-Za-z_]\w*)",
                           part)
            if nm and nm.group(1).lower() in RESERVED:
                problems.append((ln, "예약어를 변수명으로 사용: %s" % nm.group(1)))

    # ---- block balance, labels, calls, per procedure ----------------------
    OPEN = [
        (r"^\s*(?:Public\s+|Private\s+)?(?:Sub|Function)\s+\w+", "Sub/Function"),
        (r"^\s*With\b", "With"),
        (r"^\s*(?:Do\s+(?:While|Until)\b|Do\s*$)", "Do"),
        (r"^\s*Select\s+Case\b", "Select"),
        (r"^\s*For\b", "For"),
    ]
    CLOSE = {
        r"^\s*End\s+(?:Sub|Function)\b": "Sub/Function",
        r"^\s*End\s+With\b": "With",
        r"^\s*Loop\b": "Do",
        r"^\s*End\s+Select\b": "Select",
        r"^\s*Next\b": "For",
    }

    stack = []
    cur_proc = None
    labels, gotos = set(), []
    for ln, s in lines:
        for stmt in split_statements(s):
            st = stmt.strip()
            if not st:
                continue

            if re.match(r"^\s*(?:Public\s+|Private\s+)?(?:Sub|Function)\s+\w+", st):
                if cur_proc:
                    problems.append((ln, "이전 프로시저가 안 닫힘: %s" % cur_proc))
                cur_proc = st
                labels, gotos = set(), []

            # If / End If, allowing the single-line form
            m = re.match(r"^\s*If\b.*\bThen\b(.*)$", st, re.IGNORECASE)
            if m:
                if not m.group(1).strip():
                    stack.append(("If", ln))
                continue
            if re.match(r"^\s*End\s+If\b", st, re.IGNORECASE):
                if not stack or stack[-1][0] != "If":
                    problems.append((ln, "짝이 맞지 않는 End If"))
                else:
                    stack.pop()
                continue
            if re.match(r"^\s*(?:Else|ElseIf)\b", st, re.IGNORECASE):
                continue

            opened = False
            for pat, kind in OPEN:
                if re.match(pat, st, re.IGNORECASE):
                    stack.append((kind, ln))
                    opened = True
                    break
            if opened:
                continue
            for pat, kind in CLOSE.items():
                if re.match(pat, st, re.IGNORECASE):
                    if not stack or stack[-1][0] != kind:
                        got = stack[-1][0] if stack else "없음"
                        problems.append((ln, "블록이 맞지 않음: %s 를 닫는데 열린 것은 %s"
                                         % (kind, got)))
                    else:
                        stack.pop()
                    if kind == "Sub/Function":
                        for g_ln, g in gotos:
                            if g not in labels:
                                problems.append((g_ln, "없는 레이블로 이동: %s" % g))
                        cur_proc = None
                    break
            else:
                lab = re.match(r"^\s*([A-Za-z_]\w*)\s*$", stmt.rstrip())
                if lab and stmt.rstrip().endswith(lab.group(1)) and ":" in s:
                    labels.add(lab.group(1))
                g = re.search(r"\bGoTo\s+([A-Za-z_]\w*)", st, re.IGNORECASE)
                if g and g.group(1) != "0":
                    gotos.append((ln, g.group(1)))

            # calls to our own procedures
            m = re.match(r"^\s*([A-Za-z_]\w*)\s+(?!=)(.*)$", st)
            name, arglist = (m.group(1), m.group(2)) if m else (None, None)
            m2 = re.match(r"^\s*(?:Call\s+)?([A-Za-z_]\w*)\s*\((.*)\)\s*$", st)
            if m2 and m2.group(1).lower() in procs:
                name, arglist = m2.group(1), m2.group(2)
            if name and name.lower() in procs and name.lower() not in (
                    "dim", "set", "const", "static", "exit", "end"):
                depth, count, in_str = 0, (1 if arglist.strip() else 0), False
                for ch in arglist:
                    if ch == '"':
                        in_str = not in_str
                    elif not in_str:
                        if ch in "([":
                            depth += 1
                        elif ch in ")]":
                            depth -= 1
                        elif ch == "," and depth == 0:
                            count += 1
                real, req, total, dln = procs[name.lower()]
                if not (req <= count <= total):
                    problems.append((ln, "%s 인자 %d개 전달, 정의는 %d~%d개 (정의 %d행)"
                                     % (real, count, req, total, dln)))

    for kind, ln in stack:
        problems.append((ln, "닫히지 않은 블록: %s" % kind))

    # ---- report ----------------------------------------------------------
    print("프로시저 %d개, 논리행 %d줄 검사" % (len(procs), len(lines)))
    if problems:
        print("\n문제 %d건:" % len(problems))
        for ln, msg in sorted(set(problems)):
            print("  %4d| %s" % (ln, msg))
            print("      | %s" % raw[ln - 1].strip())
        return 1
    print("문제 없음")
    return 0


if __name__ == "__main__":
    sys.exit(check(sys.argv[1] if len(sys.argv) > 1 else BAS))
