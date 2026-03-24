"""
SPT 데이터 매니저 - JSON 저장/로드, Excel/CSV Export, 작전 관리
"""
import json
import os
import time
import shutil
from typing import List, Optional
from core.models import Personnel, Equipment, DEFAULT_VESSELS, DEFAULT_PERSONNEL


DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")
OPERATIONS_DIR = os.path.join(DATA_DIR, "operations")
STATUS_FILE = os.path.join(DATA_DIR, "status.json")

RANK_ORDER = {"총경": 0, "경정": 1, "경감": 2, "경위": 3, "경사": 4, "경장": 5, "순경": 6}


class DataManager:
    def __init__(self):
        self.personnel: List[Personnel] = []
        self.equipment: List[Equipment] = []
        self.vessels: dict = dict(DEFAULT_VESSELS)
        self.logs: List[dict] = []
        self.operation_title: str = ""
        self._created_at: float = 0.0
        self._current_file: str = STATUS_FILE
        os.makedirs(DATA_DIR, exist_ok=True)
        os.makedirs(OPERATIONS_DIR, exist_ok=True)

    # ---- 작전 관리 ----
    def new_operation(self):
        """새 작전 시작"""
        self._init_defaults()
        self.operation_title = ""
        self._created_at = time.time()
        ts = time.strftime("%Y%m%d_%H%M%S")
        self._current_file = os.path.join(OPERATIONS_DIR, f"op_{ts}.json")
        self.save()

    def load_operation(self, filepath: str) -> bool:
        """과거 작전 불러오기"""
        self._current_file = filepath
        return self._load_from_file(filepath)

    def list_operations(self) -> List[dict]:
        """과거 작전 목록 (최근 순)"""
        ops = []
        for f in os.listdir(OPERATIONS_DIR):
            if f.endswith(".json"):
                filepath = os.path.join(OPERATIONS_DIR, f)
                try:
                    with open(filepath, "r", encoding="utf-8") as fh:
                        data = json.load(fh)
                    ops.append({
                        "title": data.get("operation_title", "제목 없음"),
                        "filepath": filepath,
                        "created_at": data.get("created_at", data.get("last_saved", 0)),
                        "last_saved": data.get("last_saved", 0),
                        "personnel_count": len(data.get("personnel", [])),
                        "log_count": len(data.get("logs", [])),
                    })
                except (json.JSONDecodeError, OSError):
                    pass
        ops.sort(key=lambda x: x["last_saved"], reverse=True)
        return ops

    def delete_operation(self, filepath: str):
        """작전 삭제"""
        if os.path.exists(filepath) and filepath != self._current_file:
            os.remove(filepath)

    def set_title(self, title: str):
        """작전 제목 설정"""
        self.operation_title = title
        self.save()

    # ---- 데이터 로드/저장 ----
    def load(self) -> bool:
        """기본 status.json에서 데이터 로드 (하위 호환)"""
        if not os.path.exists(STATUS_FILE):
            self._init_defaults()
            return False
        return self._load_from_file(STATUS_FILE)

    def _load_from_file(self, filepath: str) -> bool:
        """특정 파일에서 데이터 로드"""
        if not os.path.exists(filepath):
            self._init_defaults()
            return False
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                data = json.load(f)
            self.personnel = [Personnel.from_dict(p) for p in data.get("personnel", [])]
            self.equipment = [Equipment.from_dict(e) for e in data.get("equipment", [])]
            self.vessels = data.get("vessels", dict(DEFAULT_VESSELS))
            self.logs = data.get("logs", [])
            self.operation_title = data.get("operation_title", "")
            self._created_at = data.get("created_at", data.get("last_saved", 0))

            for log in self.logs:
                if "type" not in log:
                    log["type"] = "auto"

            # 기존 memos 마이그레이션
            old_memos = data.get("memos", [])
            for memo in old_memos:
                self.logs.append({
                    "timestamp": memo["timestamp"],
                    "time_str": memo["time_str"],
                    "message": memo.get("text", ""),
                    "type": "memo"
                })
            if old_memos:
                self.logs.sort(key=lambda x: x.get("timestamp", 0))

            self._current_file = filepath
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
        self.operation_title = ""

    def save(self):
        """현재 작전 파일에 저장"""
        data = {
            "personnel": [p.to_dict() for p in self.personnel],
            "equipment": [e.to_dict() for e in self.equipment],
            "vessels": self.vessels,
            "logs": self.logs,
            "operation_title": self.operation_title,
            "created_at": self._created_at or time.time(),
            "last_saved": time.time(),
        }
        with open(self._current_file, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    # ---- 로그 ----
    def add_log(self, message: str, log_type: str = "auto"):
        entry = {
            "timestamp": time.time(),
            "time_str": time.strftime("%H:%M:%S"),
            "message": message,
            "type": log_type,
        }
        self.logs.append(entry)
        self.save()
        return entry

    def add_memo(self, text: str):
        return self.add_log(text, log_type="memo")

    def edit_log(self, log_entry: dict, new_message: str):
        log_entry["message"] = new_message
        self.save()

    def delete_log(self, log_entry: dict):
        if log_entry in self.logs:
            self.logs.remove(log_entry)
            self.save()

    # ---- 인원 ----
    def get_personnel_by_id(self, pid: str) -> Optional[Personnel]:
        for p in self.personnel:
            if p.id == pid:
                return p
        return None

    def get_personnel_at(self, location: str) -> List[Personnel]:
        result = [p for p in self.personnel if p.location == location]
        return sorted(result, key=lambda p: RANK_ORDER.get(p.rank, 99))

    def get_equipment_at(self, location: str) -> List[Equipment]:
        if location == "base":
            return [e for e in self.equipment if e.vessel_id in ("", "base")]
        return [e for e in self.equipment if e.vessel_id == location]

    def move_equipment_batch(self, eids: List[str], target_location: str) -> Optional[str]:
        names = []
        for eid in eids:
            eq = next((e for e in self.equipment if e.id == eid), None)
            if eq:
                old_loc = eq.vessel_id or "base"
                if old_loc != target_location:
                    eq.vessel_id = target_location
                    names.append(eq.name)
        if not names:
            return None
        target_name = self.get_location_display_name(target_location)
        log_msg = f"장비 이동: {', '.join(names)} → {target_name}"
        self.add_log(log_msg)
        self.save()
        return log_msg

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

    def update_personnel(self, pid: str, name: str, rank: str):
        person = self.get_personnel_by_id(pid)
        if person:
            person.name = name
            person.rank = rank
            self.save()

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
        log_msg = f"{person.name} {person.rank} : {old_name} → {new_name}"
        self.add_log(log_msg)
        self.save()
        return log_msg

    def move_personnel_batch(self, pids: List[str], target_location: str) -> Optional[str]:
        names = []
        for pid in pids:
            person = self.get_personnel_by_id(pid)
            if person and person.location != target_location:
                person.deploy_to(target_location)
                names.append(f"{person.name} {person.rank}")
        if not names:
            return None
        target_name = self.get_location_display_name(target_location)
        log_msg = f"{', '.join(names)} → {target_name}"
        self.add_log(log_msg)
        self.save()
        return log_msg

    def get_location_display_name(self, location: str) -> str:
        if location in self.vessels:
            return self.vessels[location]["name"]
        return location

    # ---- 장비 ----
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

    # ---- 선박 ----
    def add_vessel(self, vessel_id: str, name: str, vessel_type: str):
        self.vessels[vessel_id] = {"name": name, "type": vessel_type}
        self.save()

    def remove_vessel(self, vessel_id: str):
        if vessel_id in self.vessels and vessel_id != "base":
            for p in self.get_personnel_at(vessel_id):
                self.move_personnel(p.id, "base")
            del self.vessels[vessel_id]
            self.save()

    # ---- 내보내기 ----
    def export_csv(self, filepath: str):
        import csv
        with open(filepath, "w", newline="", encoding="utf-8-sig") as f:
            writer = csv.writer(f)
            writer.writerow(["시각", "유형", "내용"])
            for log in self.logs:
                log_type = "메모" if log.get("type") == "memo" else "작전"
                writer.writerow([log["time_str"], log_type, log["message"]])

    def export_xlsx(self, filepath: str):
        try:
            from openpyxl import Workbook
            from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
        except ImportError:
            self.export_csv(filepath.replace(".xlsx", ".csv"))
            return

        wb = Workbook()
        ws_log = wb.active
        ws_log.title = "작전 로그"
        header_font = Font(bold=True, color="FFFFFF", size=11)
        header_fill = PatternFill(start_color="1B2838", end_color="1B2838", fill_type="solid")
        thin_border = Border(
            left=Side(style="thin"), right=Side(style="thin"),
            top=Side(style="thin"), bottom=Side(style="thin")
        )

        headers = ["번호", "시각", "유형", "내용"]
        for col, h in enumerate(headers, 1):
            cell = ws_log.cell(row=1, column=col, value=h)
            cell.font = header_font
            cell.fill = header_fill
            cell.alignment = Alignment(horizontal="center")
            cell.border = thin_border

        for i, log in enumerate(self.logs, 1):
            log_type = "메모" if log.get("type") == "memo" else "작전"
            ws_log.cell(row=i + 1, column=1, value=i).border = thin_border
            ws_log.cell(row=i + 1, column=2, value=log["time_str"]).border = thin_border
            ws_log.cell(row=i + 1, column=3, value=log_type).border = thin_border
            ws_log.cell(row=i + 1, column=4, value=log["message"]).border = thin_border

        ws_log.column_dimensions["A"].width = 8
        ws_log.column_dimensions["B"].width = 12
        ws_log.column_dimensions["C"].width = 8
        ws_log.column_dimensions["D"].width = 50

        ws_per = wb.create_sheet("인원 현황")
        per_headers = ["ID", "이름", "계급", "현재 위치", "상태", "누적 이함(분)"]
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

        wb.save(filepath)
