"""
SPT 데이터 매니저 - JSON 저장/로드, Excel/CSV Export
"""
import json
import os
import time
from typing import List, Optional
from core.models import Personnel, Equipment, DEFAULT_VESSELS, DEFAULT_PERSONNEL


DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")
STATUS_FILE = os.path.join(DATA_DIR, "status.json")


class DataManager:
    def __init__(self):
        self.personnel: List[Personnel] = []
        self.equipment: List[Equipment] = []
        self.vessels: dict = dict(DEFAULT_VESSELS)
        self.logs: List[dict] = []
        self.memos: List[dict] = []
        os.makedirs(DATA_DIR, exist_ok=True)

    def load(self) -> bool:
        """status.json에서 데이터 로드. 성공 시 True."""
        if not os.path.exists(STATUS_FILE):
            self._init_defaults()
            return False
        try:
            with open(STATUS_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
            self.personnel = [Personnel.from_dict(p) for p in data.get("personnel", [])]
            self.equipment = [Equipment.from_dict(e) for e in data.get("equipment", [])]
            self.vessels = data.get("vessels", dict(DEFAULT_VESSELS))
            self.logs = data.get("logs", [])
            self.memos = data.get("memos", [])
            return True
        except (json.JSONDecodeError, KeyError):
            self._init_defaults()
            return False

    def _init_defaults(self):
        self.personnel = [Personnel(
            id=p.id, name=p.name, rank=p.rank, department=p.department
        ) for p in DEFAULT_PERSONNEL]
        self.equipment = []
        self.vessels = dict(DEFAULT_VESSELS)
        self.logs = []
        self.memos = []

    def save(self):
        """status.json에 현재 상태 저장"""
        data = {
            "personnel": [p.to_dict() for p in self.personnel],
            "equipment": [e.to_dict() for e in self.equipment],
            "vessels": self.vessels,
            "logs": self.logs,
            "memos": self.memos,
            "last_saved": time.time(),
        }
        with open(STATUS_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    def add_log(self, message: str):
        entry = {
            "timestamp": time.time(),
            "time_str": time.strftime("%H:%M:%S"),
            "message": message,
        }
        self.logs.append(entry)
        self.save()
        return entry

    def add_memo(self, text: str):
        entry = {
            "timestamp": time.time(),
            "time_str": time.strftime("%H:%M:%S"),
            "text": text,
        }
        self.memos.append(entry)
        self.save()
        return entry

    def get_personnel_by_id(self, pid: str) -> Optional[Personnel]:
        for p in self.personnel:
            if p.id == pid:
                return p
        return None

    def get_personnel_at(self, location: str) -> List[Personnel]:
        return [p for p in self.personnel if p.location == location]

    def add_personnel(self, name: str, rank: str, department: str = "본함") -> Personnel:
        max_num = 0
        for p in self.personnel:
            try:
                num = int(p.id.replace("P", ""))
                max_num = max(max_num, num)
            except ValueError:
                pass
        new_id = f"P{max_num + 1:03d}"
        person = Personnel(id=new_id, name=name, rank=rank, department=department)
        self.personnel.append(person)
        self.save()
        return person

    def remove_personnel(self, pid: str):
        self.personnel = [p for p in self.personnel if p.id != pid]
        self.save()

    def move_personnel(self, pid: str, target_location: str) -> Optional[str]:
        person = self.get_personnel_by_id(pid)
        if not person:
            return None
        old_loc = person.deploy_to(target_location)
        old_name = self.get_location_display_name(old_loc)
        new_name = self.get_location_display_name(target_location)
        log_msg = f"{person.name} {person.rank} 이동: {old_name} → {new_name}"
        self.add_log(log_msg)
        self.save()
        return log_msg

    def get_location_display_name(self, location: str) -> str:
        if location in self.vessels:
            return self.vessels[location]["name"]
        return location

    def add_equipment(self, name: str, category: str = "", vessel_id: str = "") -> Equipment:
        max_num = 0
        for e in self.equipment:
            try:
                num = int(e.id.replace("E", ""))
                max_num = max(max_num, num)
            except ValueError:
                pass
        new_id = f"E{max_num + 1:03d}"
        eq = Equipment(id=new_id, name=name, category=category, vessel_id=vessel_id)
        self.equipment.append(eq)
        self.save()
        return eq

    def remove_equipment(self, eid: str):
        self.equipment = [e for e in self.equipment if e.id != eid]
        self.save()

    def assign_equipment(self, eid: str, assignee_id: Optional[str]):
        for e in self.equipment:
            if e.id == eid:
                old = e.assignee_id
                e.assignee_id = assignee_id
                if assignee_id:
                    person = self.get_personnel_by_id(assignee_id)
                    pname = person.name if person else assignee_id
                    self.add_log(f"장비 '{e.name}' 담당자 지정: {pname}")
                else:
                    self.add_log(f"장비 '{e.name}' 담당자 해제")
                self.save()
                return old
        return None

    def add_vessel(self, vessel_id: str, name: str, vessel_type: str):
        self.vessels[vessel_id] = {"name": name, "type": vessel_type}
        self.save()

    def remove_vessel(self, vessel_id: str):
        if vessel_id in self.vessels and vessel_id != "base":
            # 해당 선박의 대원들을 본함으로 복귀
            for p in self.get_personnel_at(vessel_id):
                self.move_personnel(p.id, "base")
            del self.vessels[vessel_id]
            self.save()

    def export_csv(self, filepath: str):
        import csv
        with open(filepath, "w", newline="", encoding="utf-8-sig") as f:
            writer = csv.writer(f)
            writer.writerow(["시각", "내용"])
            for log in self.logs:
                writer.writerow([log["time_str"], log["message"]])
            writer.writerow([])
            writer.writerow(["메모 시각", "메모 내용"])
            for memo in self.memos:
                writer.writerow([memo["time_str"], memo["text"]])

    def export_xlsx(self, filepath: str):
        try:
            from openpyxl import Workbook
            from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
        except ImportError:
            self.export_csv(filepath.replace(".xlsx", ".csv"))
            return

        wb = Workbook()

        # 작전 로그 시트
        ws_log = wb.active
        ws_log.title = "작전 로그"
        header_font = Font(bold=True, color="FFFFFF", size=11)
        header_fill = PatternFill(start_color="1B2838", end_color="1B2838", fill_type="solid")
        thin_border = Border(
            left=Side(style="thin"), right=Side(style="thin"),
            top=Side(style="thin"), bottom=Side(style="thin")
        )

        headers = ["번호", "시각", "내용"]
        for col, h in enumerate(headers, 1):
            cell = ws_log.cell(row=1, column=col, value=h)
            cell.font = header_font
            cell.fill = header_fill
            cell.alignment = Alignment(horizontal="center")
            cell.border = thin_border

        for i, log in enumerate(self.logs, 1):
            ws_log.cell(row=i + 1, column=1, value=i).border = thin_border
            ws_log.cell(row=i + 1, column=2, value=log["time_str"]).border = thin_border
            ws_log.cell(row=i + 1, column=3, value=log["message"]).border = thin_border

        ws_log.column_dimensions["A"].width = 8
        ws_log.column_dimensions["B"].width = 12
        ws_log.column_dimensions["C"].width = 50

        # 인원 현황 시트
        ws_per = wb.create_sheet("인원 현황")
        per_headers = ["ID", "이름", "계급", "현재 위치", "상태", "누적 탑승(분)"]
        for col, h in enumerate(per_headers, 1):
            cell = ws_per.cell(row=1, column=col, value=h)
            cell.font = header_font
            cell.fill = header_fill
            cell.alignment = Alignment(horizontal="center")
            cell.border = thin_border

        for i, p in enumerate(self.personnel, 1):
            loc_name = self.get_location_display_name(p.location)
            ws_per.cell(row=i + 1, column=1, value=p.id).border = thin_border
            ws_per.cell(row=i + 1, column=2, value=p.name).border = thin_border
            ws_per.cell(row=i + 1, column=3, value=p.rank).border = thin_border
            ws_per.cell(row=i + 1, column=4, value=loc_name).border = thin_border
            ws_per.cell(row=i + 1, column=5, value=p.status).border = thin_border
            ws_per.cell(row=i + 1, column=6, value=round(p.total_deploy_seconds / 60, 1)).border = thin_border

        # 메모 시트
        ws_memo = wb.create_sheet("메모")
        memo_headers = ["시각", "내용"]
        for col, h in enumerate(memo_headers, 1):
            cell = ws_memo.cell(row=1, column=col, value=h)
            cell.font = header_font
            cell.fill = header_fill
            cell.border = thin_border
        for i, memo in enumerate(self.memos, 1):
            ws_memo.cell(row=i + 1, column=1, value=memo["time_str"]).border = thin_border
            ws_memo.cell(row=i + 1, column=2, value=memo["text"]).border = thin_border

        wb.save(filepath)
