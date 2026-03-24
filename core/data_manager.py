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

RANK_ORDER = {"총경": 0, "경정": 1, "경감": 2, "경위": 3, "경사": 4, "경장": 5, "순경": 6}


class DataManager:
    def __init__(self):
        self.personnel: List[Personnel] = []
        self.equipment: List[Equipment] = []
        self.vessels: dict = dict(DEFAULT_VESSELS)
        self.logs: List[dict] = []  # 통합 로그 (작전로그 + 메모)
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

            # 기존 로그에 type 필드 없으면 추가
            for log in self.logs:
                if "type" not in log:
                    log["type"] = "auto"

            # 기존 memos를 logs로 마이그레이션
            old_memos = data.get("memos", [])
            for memo in old_memos:
                self.logs.append({
                    "timestamp": memo["timestamp"],
                    "time_str": memo["time_str"],
                    "message": memo.get("text", ""),
                    "type": "memo"
                })

            # 타임스탬프 순 정렬
            if old_memos:
                self.logs.sort(key=lambda x: x.get("timestamp", 0))

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

    def save(self):
        """status.json에 현재 상태 저장"""
        data = {
            "personnel": [p.to_dict() for p in self.personnel],
            "equipment": [e.to_dict() for e in self.equipment],
            "vessels": self.vessels,
            "logs": self.logs,
            "last_saved": time.time(),
        }
        with open(STATUS_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

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
        """메모 추가 (로그에 통합)"""
        return self.add_log(text, log_type="memo")

    def edit_log(self, log_entry: dict, new_message: str):
        """로그 메시지 수정"""
        log_entry["message"] = new_message
        self.save()

    def delete_log(self, log_entry: dict):
        """로그 삭제"""
        if log_entry in self.logs:
            self.logs.remove(log_entry)
            self.save()

    def get_personnel_by_id(self, pid: str) -> Optional[Personnel]:
        for p in self.personnel:
            if p.id == pid:
                return p
        return None

    def get_personnel_at(self, location: str) -> List[Personnel]:
        result = [p for p in self.personnel if p.location == location]
        return sorted(result, key=lambda p: RANK_ORDER.get(p.rank, 99))

    def get_equipment_at(self, location: str) -> List[Equipment]:
        """특정 위치의 장비 목록"""
        if location == "base":
            return [e for e in self.equipment if e.vessel_id in ("", "base")]
        return [e for e in self.equipment if e.vessel_id == location]

    def move_equipment_batch(self, eids: List[str], target_location: str) -> Optional[str]:
        """장비 일괄 이동"""
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
        """인원 정보 수정"""
        person = self.get_personnel_by_id(pid)
        if person:
            person.name = name
            person.rank = rank
            self.save()

    def remove_personnel(self, pid: str):
        self.personnel = [p for p in self.personnel if p.id != pid]
        self.save()

    def move_personnel(self, pid: str, target_location: str) -> Optional[str]:
        """단일 인원 이동 (개별 로그 생성)"""
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
        """다수 인원 일괄 이동 (로그 하나로 합침)"""
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

        # 작전 로그 시트
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

        # 인원 현황 시트
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
