#!/usr/bin/env python3
"""Build sample 산정서 workbooks shaped like the real ones, then run a Python
port of the VBA scan over them to check the anchor logic.

This exercises the algorithm (where the labels and values sit relative to the
[급여 세부내용] anchor, and that a month's day-count does not matter).
It does not execute the VBA itself.
"""
import calendar
import os

from openpyxl import Workbook, load_workbook

HERE = os.path.dirname(os.path.abspath(__file__))
SAMPLE_DIR = os.path.join(os.path.dirname(HERE), "sample")

DAY_COL0 = 6          # day columns start at F, as in the real sheet
BLOCK_H = 8           # rows per person


def _person_block(ws, row, seq, name, box_col, days,
                  work_sum_col, work_box, ot_sum_col, ot_box):
    """One person: the daily grid on the left, the 급여 세부내용 box on the right."""
    ws.cell(row, 1, seq)
    ws.cell(row, 3, name)
    labels = ["구분", "근무시간(시간)", "복무규정시간(시간)", "시간외(시간)",
              "야간(시간)", "휴일(일수)", "출동가산(일수)", "교대시간(분)"]
    for i, lab in enumerate(labels):
        ws.cell(row + i, 5, lab)
    sum_col = DAY_COL0 + days
    for d in range(days):                      # plausible daily numbers
        ws.cell(row + 1, DAY_COL0 + d, 8)
    ws.cell(row + 1, sum_col, work_sum_col)    # 근무시간 합계 열 (읽지 않는 쪽)
    ws.cell(row + 3, sum_col, ot_sum_col)      # 시간외 합계 열 (읽지 않는 쪽)

    # 급여 세부내용 박스 -- 집계가 읽는 유일한 곳
    ws.cell(row, box_col, "급여 세부내용")
    ws.merge_cells(start_row=row, start_column=box_col, end_row=row, end_column=box_col + 1)
    ws.cell(row + 1, box_col, "총 근무시간")
    ws.cell(row + 1, box_col + 1, "총 복무규정시간")
    ws.cell(row + 2, box_col, work_box)        # 집계 대상은 이 값
    ws.cell(row + 2, box_col + 1, 120)
    ws.cell(row + 3, box_col, "시간외(시간)")
    ws.cell(row + 3, box_col + 1, ot_box)      # 집계 대상은 이 값
    ws.cell(row + 4, box_col, "야간(시간)")
    ws.cell(row + 4, box_col + 1, 56)
    ws.cell(row + 5, box_col, "휴일(일수)")
    ws.cell(row + 5, box_col + 1, 2)
    ws.cell(row + 6, box_col, "출동가산(일수)")
    ws.cell(row + 6, box_col + 1, 8)


def _write_header(ws, year, month, ship, days, style):
    """style 'iljip': 일집계 현황 줄이 있는 모양.
       style 'gyeongbi': 일집계 현황 줄이 없고 출동현황 표와 문서번호만 있는 모양."""
    ws.cell(1, 1, "초과근무수당 개인별 산출내역서(%s)" % ship)
    ws.merge_cells(start_row=1, start_column=1, end_row=1, end_column=10)
    if style == "iljip":
        ws.cell(9, 1, "초과근무수당 일집계 현황(%d년 %d월)" % (year, month))
        hdr_row = 10
    else:
        # 연도는 관련근거 문서번호에만, 월은 "__월 출동현황" 에만 나온다
        ws.cell(3, 1, "□ %s %d월 출동현황" % (ship, month))
        ws.cell(4, 4, "'%02d.04.25.~'%02d.%02d.02." % (year % 100, year % 100, month))
        ws.cell(4, 8, "○%s-0494-%d-%02d-00152 \"출항보고\"" % (ship, year, month))
        ws.cell(6, 1, "□ %s %d월 근무현황" % (ship, month))
        hdr_row = 9
    ws.cell(hdr_row, 1, "순번"); ws.cell(hdr_row, 3, "성명"); ws.cell(hdr_row, 5, "일자")
    for d in range(days):
        ws.cell(hdr_row, DAY_COL0 + d, d + 1)
    ws.cell(hdr_row, DAY_COL0 + days, "합계")
    # 요일 줄 -- "월" 이 들어 있어 월 추출을 헷갈리게 할 수 있다
    wd = "월화수목금토일"
    for d in range(days):
        ws.cell(hdr_row + 1, DAY_COL0 + d, wd[d % 7])
    return hdr_row + 2


def make_sample(path, year, month, ship, people, sheet_name,
                decoy=False, style="iljip", sister_sheet=None):
    days = calendar.monthrange(year, month)[1]
    box_col = DAY_COL0 + days + 3
    wb = Workbook()
    ws = wb.active
    ws.title = sheet_name

    row = _write_header(ws, year, month, ship, days, style)
    for seq, person in enumerate(people, start=1):
        _person_block(ws, row, seq, person[0], box_col, days, *person[1:])
        row += BLOCK_H

    if decoy:
        # 같은 제목을 단 두 번째 시트 -- 시트명 규칙이 걸러내야 한다
        w2 = wb.create_sheet("%d월 초과 합계 내역" % month)
        _write_header(w2, year, month, ship, days, style)
        _person_block(w2, 11, 1, "중복", box_col, days, 9999, 9999, 9999, 9999)

    if sister_sheet:
        # 경비함정 옆에 나란히 있는 다른 소속 시트. 역시 같은 제목을 단다.
        w3 = wb.create_sheet(sister_sheet)
        r3 = _write_header(w3, year, month, ship, days, style)
        _person_block(w3, r3, 1, "상황실", box_col, days, 7777, 7777, 7777, 7777)

    os.makedirs(os.path.dirname(path), exist_ok=True)
    wb.save(path)
    return path


# --------------------------------------------------------------------------
# Python port of the VBA scan (same anchors, same relative offsets)
# --------------------------------------------------------------------------
K_TITLE, K_PERIOD, K_BOX = "초과근무수당개인별산출내역서", "일집계현황", "급여세부내용"
K_WORK, K_OT = "총근무시간", "시간외"


def norm(v):
    if not isinstance(v, str):
        return ""
    for ch in (" ", "\t", "\r", "\n", " ", "　"):
        v = v.replace(ch, "")
    return v


def tail_digits(s):
    t = ""
    for ch in reversed(s):
        if ch.isdigit():
            t = ch + t
        else:
            break
    return int(t) if 0 < len(t) <= 4 else 0


def parse_ym(s):
    p, q = s.find("년"), s.find("월")
    if p < 0 or q <= p:
        return 0, 0
    y, m = tail_digits(s[:p]), tail_digits(s[p + 1:q])
    if 0 <= y <= 99:
        y += 2000
    if not (1990 <= y <= 2099) or not (1 <= m <= 12):
        return 0, 0
    return y, m


def try_num(grid, r, c):
    if r < 1 or c < 1 or r > len(grid) or c > len(grid[0]):
        return None
    v = grid[r - 1][c - 1]
    if isinstance(v, bool):
        return None
    if isinstance(v, (int, float)):
        return float(v)
    if isinstance(v, str):
        s = norm(v).replace(",", "")
        try:
            return float(s)
        except ValueError:
            return None
    return None


def pick_num(grid, r1, c1, r2, c2):
    for r, c in ((r1, c1), (r2, c2)):
        d = try_num(grid, r, c)
        if d is not None:
            return d
    return 0.0


def sum_box(grid, r0, c0):
    work = ot = 0.0
    got_w = got_o = False
    for r in range(r0 + 1, min(r0 + 10, len(grid)) + 1):
        for c in range(c0, min(c0 + 2, len(grid[0])) + 1):
            s = norm(grid[r - 1][c - 1])
            if not got_w and s.startswith(K_WORK):
                work += pick_num(grid, r + 1, c, r, c + 1)
                got_w = True
            if not got_o and s.startswith(K_OT):
                ot += pick_num(grid, r, c + 1, r + 1, c)
                got_o = True
        if got_w and got_o:
            break
    return work, ot


HDR_ROWS = 30


def month_from_name(s):
    s = norm(s)
    p = s.find("월")
    if p < 0:
        return 0
    m = tail_digits(s[:p])
    return m if 1 <= m <= 12 else 0


def month_in_block(head):
    best = 0
    for row in head:
        for v in row:
            s = norm(v)
            if "월" not in s:
                continue
            m = month_from_name(s)
            if m:
                if "현황" in s:
                    return m
                best = best or m
    return best


def find_year(text, from_right=False):
    found = 0
    for i in range(len(text) - 3):
        t = text[i:i + 4]
        if not t.isdigit():
            continue
        if i > 0 and text[i - 1].isdigit():
            continue
        if i + 4 < len(text) and text[i + 4].isdigit():
            continue
        if 2000 <= int(t) <= 2099:
            found = int(t)
            if not from_right:
                return found
    return found


def year_in_block(head):
    for row in head:
        for v in row:
            if isinstance(v, str):
                y = find_year(v)
                if y:
                    return y
    return 0


def append_src(s, add):
    return add if not s else s + " + " + add


def sheet_has_title(grid):
    for row in grid[:HDR_ROWS]:
        for v in row[:120]:
            if K_TITLE in norm(v):
                return True
    return False


def _name_matches(s, mode):
    if mode == 1:
        return "경비함정" in s
    if "초과근무수당" in s or "초간근무수당" in s:
        return "합계" not in s and "내역" not in s
    return False


def pick_sheet_by_name(names):
    for mode in (1, 2):                      # 1순위 경비함정, 2순위 초과/초간근무수당
        hits = [n for n in names if _name_matches(norm(n), mode)]
        if len(hits) == 1:
            return hits[0]
    return None


def scan_file(path):
    wb = load_workbook(path, data_only=True, read_only=False)
    grids = {}
    for ws in wb.worksheets:
        grid = [[c.value for c in row] for row in ws.iter_rows()]
        if grid and sheet_has_title(grid):
            grids[ws.title] = grid
    if not grids:
        return {"status": "산출내역서 시트 없음"}
    if len(grids) == 1:
        name = next(iter(grids))
    else:
        name = pick_sheet_by_name(list(grids))
        if name is None:
            return {"status": "대상 시트 판별 실패"}
    grid = grids[name]

    year = month = 0
    ship = ""
    ym_src = ""
    head = grid[:HDR_ROWS]
    for row in head:
        for v in row:
            s = norm(v)
            if not s:
                continue
            if year == 0 and K_PERIOD in s:
                year, month = parse_ym(s)
                if year:
                    ym_src = "일집계현황"
            if not ship and K_TITLE in s and "(" in s and ")" in s:
                ship = s[s.rindex("(") + 1:s.index(")", s.rindex("("))]
    if year == 0:
        for row in head:
            for v in row:
                s = norm(v)
                if "년" in s and "월" in s:
                    year, month = parse_ym(s)
                    if year:
                        ym_src = "머리글(년월)"
                        break
            if year:
                break
    if month == 0:
        month = month_in_block(head)
        if month:
            ym_src = append_src(ym_src, "월:머리글")
    if year == 0:
        year = year_in_block(head)
        if year:
            ym_src = append_src(ym_src, "연:머리글")
    if month == 0:
        month = month_from_name(name)
        if month:
            ym_src = append_src(ym_src, "월:시트명")
    if month == 0:
        month = month_from_name(os.path.basename(path))
        if month:
            ym_src = append_src(ym_src, "월:파일명")
    if year == 0:
        year = find_year(path, from_right=True)
        if year:
            ym_src = append_src(ym_src, "연:경로")

    work = ot = 0.0
    people = 0
    for r in range(1, len(grid) + 1):
        for c in range(1, len(grid[0]) + 1):
            if K_BOX in norm(grid[r - 1][c - 1]):
                people += 1
                w, o = sum_box(grid, r, c)
                work += w
                ot += o
    return {"status": "정상", "sheet": name, "year": year, "month": month,
            "ym_src": ym_src, "ship": ship, "people": people,
            "work": work, "ot": ot}


def main():
    # 왼쪽 합계 열과 박스 값이 다른 사람을 일부러 섞는다.
    # 합계 열을 잘못 읽으면 시간외가 308 로 나오므로 바로 잡힌다.
    # (이름, 근무시간 합계열, 근무시간 박스, 시간외 합계열, 시간외 박스)
    may = [("김근홍", 220, 220, 100, 100),
           ("최영필", 232, 232, 100, 100),
           ("현관용", 208, 208, 108, 100)]
    feb = [("김근홍", 190, 190, 96, 96),
           ("최영필", 205, 205, 130, 100)]
    # 사진의 실제 값: 근무시간도 합계열(170)과 박스(169.5)가 다르다
    gyb = [("박상현", 170, 169.5, 73, 73),
           ("최영필", 208, 207.5, 55, 55),
           ("현관용", 198, 197.5, 55, 55)]

    cases = []

    # (1) 일집계 현황 줄이 있는 모양 + "5월 초과 합계 내역" 미끼 시트
    cases.append((make_sample(
        os.path.join(SAMPLE_DIR, "5월 초과근무수당 산정서(1505함).xlsx"),
        2025, 5, "1505함", may, "5월 초간근무수당", decoy=True),
        dict(sheet="5월 초간근무수당", year=2025, month=5,
             people=3, work=660.0, ot=300.0)))

    # (2) 28일치 -- 박스 열이 왼쪽으로 밀려도 찾아야 한다
    cases.append((make_sample(
        os.path.join(SAMPLE_DIR, "2월 초과근무수당 산정서(1505함).xlsx"),
        2024, 2, "1505함", feb, "2월 초과근무수당"),
        dict(sheet="2월 초과근무수당", year=2024, month=2,
             people=2, work=395.0, ot=196.0)))

    # (3) 경비함정 모양: 일집계 현황 줄이 없고, 시트명에 월도 없다.
    #     연도는 문서번호에서, 월은 "1505함 5월 출동현황" 에서 나와야 하고,
    #     "상황실,파출소,구조대 등" 시트는 골라지면 안 된다.
    cases.append((make_sample(
        os.path.join(SAMPLE_DIR, "초과근무수당산정내역서(1505함).xlsx"),
        2024, 5, "1505함", gyb, "경비함정",
        style="gyeongbi", sister_sheet="상황실,파출소,구조대 등"),
        dict(sheet="경비함정", year=2024, month=5, ship="1505함",
             people=3, work=574.5, ot=183.0)))

    ok = True
    for path, exp in cases:
        got = scan_file(path)
        print(os.path.basename(path))
        print("   ", got)
        for k, v in exp.items():
            if got.get(k) != v:
                print("    MISMATCH %s: got %r want %r" % (k, got.get(k), v))
                ok = False
    print()
    print("sample files ->", SAMPLE_DIR)
    print("RESULT:", "PASS" if ok else "FAIL")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
