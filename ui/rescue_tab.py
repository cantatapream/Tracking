"""
SPT 구조현황 탭 - 구조/인계/인수 관리
"""
import time
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QLineEdit, QComboBox, QFrame, QScrollArea, QSizePolicy,
    QGridLayout, QTextEdit, QDialog, QStackedWidget
)
from PySide6.QtCore import Qt, Signal
from core.data_manager import DataManager


SEVERITY_COLORS = {
    "지연": "#8faabe",
    "긴급": "#e74c3c",
    "응급": "#f39c12",
    "비응급": "#2ecc71",
}

TYPE_BADGE_COLORS = {
    "rescue": "#00d4ff",
    "transfer_out": "#f39c12",
    "transfer_in": "#2ecc71",
}

TYPE_LABELS = {
    "rescue": "구조",
    "transfer_out": "인계",
    "transfer_in": "인수",
}


class TreatmentEditDialog(QDialog):
    """조치 및 경과 편집 다이얼로그"""
    def __init__(self, current_text: str, name: str, parent=None):
        super().__init__(parent)
        self.setWindowTitle(f"조치 및 경과 - {name}")
        self.setFixedSize(400, 250)
        self.setStyleSheet("""
            QDialog { background: #0d1f3c; border: 1px solid rgba(0,212,255,0.5); border-radius: 6px; }
            QLabel { background: transparent; border: none; color: #c8d6e5; }
        """)

        layout = QVBoxLayout(self)
        layout.setSpacing(8)

        label = QLabel(f"{name} - 조치 및 경과")
        label.setStyleSheet("font-size: 14px; font-weight: bold; color: #00d4ff;")
        layout.addWidget(label)

        self.text_edit = QTextEdit()
        self.text_edit.setPlainText(current_text)
        self.text_edit.setStyleSheet("""
            QTextEdit { background: #0a1628; color: #c8d6e5; border: 1px solid #1e3a5f;
                        border-radius: 4px; padding: 6px; font-size: 12px; }
            QTextEdit:focus { border-color: #00d4ff; }
        """)
        layout.addWidget(self.text_edit, 1)

        btn_row = QHBoxLayout()
        btn_row.addStretch()
        save_btn = QPushButton("저장")
        save_btn.setObjectName("btnAccent")
        save_btn.setFixedSize(80, 30)
        save_btn.clicked.connect(self.accept)
        btn_row.addWidget(save_btn)

        cancel_btn = QPushButton("취소")
        cancel_btn.setFixedSize(80, 30)
        cancel_btn.clicked.connect(self.reject)
        btn_row.addWidget(cancel_btn)
        layout.addLayout(btn_row)

    def get_text(self) -> str:
        return self.text_edit.toPlainText().strip()


class RescueTab(QWidget):
    """구조현황 탭"""
    log_message = Signal(str)
    records_changed = Signal()

    def __init__(self, data_manager: DataManager, parent=None):
        super().__init__(parent)
        self.dm = data_manager
        self._current_mode = "rescue"  # rescue / transfer_out / transfer_in
        self._current_filter = "all"   # all / current / rescue / transfer_out / transfer_in
        self._setup_ui()

    def _setup_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # Wrap everything in a panel
        panel = QFrame()
        panel.setStyleSheet("QFrame { background: transparent; border: none; }")
        panel_layout = QVBoxLayout(panel)
        panel_layout.setContentsMargins(4, 4, 4, 4)
        panel_layout.setSpacing(8)

        # Title
        title = QLabel("구조현황")
        title.setStyleSheet("""
            color: #00d4ff; font-size: 18px; font-weight: bold;
            font-family: "HY헤드라인M", "HYHeadLineM", "Malgun Gothic", sans-serif;
            padding: 4px 0; letter-spacing: 1px; background: transparent; border: none;
            border-bottom: 1px solid rgba(0, 212, 255, 0.12);
        """)
        panel_layout.addWidget(title)

        # === Top: Mode buttons (왼쪽 세로) + Input form (오른쪽 2줄) + Apply ===
        top_frame = QFrame()
        top_frame.setStyleSheet("""
            QFrame { background: transparent; border: 1px solid #1e3a5f; border-radius: 6px; padding: 6px; }
        """)
        top_h = QHBoxLayout(top_frame)
        top_h.setContentsMargins(6, 6, 6, 6)
        top_h.setSpacing(8)

        # 왼쪽: 모드 버튼 (세로 배치)
        mode_col = QVBoxLayout()
        mode_col.setSpacing(3)
        self.mode_buttons = {}
        for key, label in [("rescue", "구조"), ("transfer_out", "인계"), ("transfer_in", "인수")]:
            btn = QPushButton(label)
            btn.setCheckable(True)
            btn.setFixedHeight(28)
            btn.setFixedWidth(50)
            btn.clicked.connect(lambda checked, k=key: self._set_mode(k))
            mode_col.addWidget(btn)
            self.mode_buttons[key] = btn
        mode_col.addStretch()
        top_h.addLayout(mode_col)

        # 오른쪽: 입력 폼 (2줄) + 적용 버튼
        right_col = QVBoxLayout()
        right_col.setSpacing(4)

        # 입력 폼 영역 (모드에 따라 변경)
        self.input_container = QWidget()
        self.input_main_layout = QVBoxLayout(self.input_container)
        self.input_main_layout.setContentsMargins(0, 0, 0, 0)
        self.input_main_layout.setSpacing(4)
        right_col.addWidget(self.input_container)

        top_h.addLayout(right_col, 1)

        # 적용 버튼 (오른쪽 끝)
        apply_col = QVBoxLayout()
        apply_col.addStretch()
        self.apply_btn = QPushButton("구조\n등록")
        self.apply_btn.setObjectName("btnAccent")
        self.apply_btn.setFixedSize(60, 60)
        self.apply_btn.clicked.connect(self._apply_record)
        apply_col.addWidget(self.apply_btn)
        apply_col.addStretch()
        top_h.addLayout(apply_col)

        panel_layout.addWidget(top_frame)

        # === Filter buttons row ===
        filter_row = QHBoxLayout()
        filter_row.setSpacing(4)
        self.filter_buttons = {}
        for key, label in [("all", "전체"), ("current", "현재"),
                           ("rescue", "본함구조"), ("transfer_out", "인계현황"),
                           ("transfer_in", "인수현황")]:
            btn = QPushButton(label)
            btn.setCheckable(True)
            btn.setFixedHeight(30)
            btn.setMinimumWidth(70)
            btn.clicked.connect(lambda checked, k=key: self._set_filter(k))
            filter_row.addWidget(btn)
            self.filter_buttons[key] = btn
        filter_row.addStretch()
        panel_layout.addLayout(filter_row)

        # === Table area (scrollable) ===
        self.table_scroll = QScrollArea()
        self.table_scroll.setWidgetResizable(True)
        self.table_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.table_scroll.setFrameShape(QFrame.NoFrame)

        self.table_widget = QWidget()
        self.table_layout = QVBoxLayout(self.table_widget)
        self.table_layout.setContentsMargins(0, 0, 0, 0)
        self.table_layout.setSpacing(0)
        self.table_layout.addStretch()
        self.table_scroll.setWidget(self.table_widget)
        panel_layout.addWidget(self.table_scroll, 1)

        main_layout.addWidget(panel, 1)

        # Initialize mode and filter
        self._set_mode("rescue")
        self._set_filter("all")

    def _clear_input_form(self):
        """Clear and rebuild input form based on current mode"""
        while self.input_main_layout.count():
            item = self.input_main_layout.takeAt(0)
            if item.layout():
                while item.layout().count():
                    sub = item.layout().takeAt(0)
                    if sub.widget():
                        sub.widget().setParent(None)
            elif item.widget():
                item.widget().setParent(None)

    def _make_time_input(self, placeholder="MM.DD HH:MM"):
        """시각 입력란 + [지금] 버튼 내장"""
        frame = QFrame()
        frame.setStyleSheet("QFrame { border: 1px solid #1e3a5f; border-radius: 4px; background: #0a1628; } QLabel { border: none; }")
        fl = QHBoxLayout(frame)
        fl.setContentsMargins(4, 2, 2, 2)
        fl.setSpacing(2)
        inp = QLineEdit()
        inp.setPlaceholderText(placeholder)
        inp.setStyleSheet("border: none; background: transparent; color: #e0e8f0; font-size: 12px; padding: 2px;")
        fl.addWidget(inp, 1)
        now_btn = QPushButton("지금")
        now_btn.setFixedSize(38, 26)
        now_btn.setStyleSheet("""
            QPushButton { background: #1e3a5f; color: #00d4ff; border: 1px solid #2a4a6f;
                          border-radius: 3px; font-size: 11px; font-weight: bold; padding: 0; }
            QPushButton:hover { background: #2a4a6f; }
        """)
        now_btn.clicked.connect(lambda: inp.setText(time.strftime("%m.%d %H:%M")))
        fl.addWidget(now_btn)
        frame.setFixedHeight(34)
        return frame, inp

    def _build_rescue_form(self):
        """구조 모드 입력 폼 (그리드 2줄)"""
        self._clear_input_form()

        grid = QGridLayout()
        grid.setHorizontalSpacing(20)
        grid.setVerticalSpacing(16)
        grid.setContentsMargins(0, 0, 0, 0)

        # Col: 0=라벨 1=시각/이름 2=라벨 3=성별/연령 4=중증도(라벨+콤보) 5=라벨 6=최초상태/구조위치

        # Row 0: 시각 | 성별 | 중증도(라벨) | 최초상태
        grid.addWidget(self._make_label("시각"), 0, 0)
        time_frame, self.time_input = self._make_time_input()
        time_frame.setMaximumWidth(180)
        grid.addWidget(time_frame, 0, 1)

        grid.addWidget(self._make_label("성별"), 0, 2)
        self.gender_combo = QComboBox()
        self.gender_combo.addItems(["남", "여"])
        self.gender_combo.setFixedWidth(60)
        self.gender_combo.setFixedHeight(34)
        grid.addWidget(self.gender_combo, 0, 3)

        sev_label = self._make_label("중증도")
        sev_label.setAlignment(Qt.AlignCenter)
        grid.addWidget(sev_label, 0, 4)

        grid.addWidget(self._make_label("최초상태"), 0, 5)
        self.state_input = QLineEdit()
        self.state_input.setPlaceholderText("")
        self.state_input.setFixedHeight(34)
        grid.addWidget(self.state_input, 0, 6)

        # Row 1: 이름 | 연령 | 중증도(드롭다운) | 구조위치
        grid.addWidget(self._make_label("이름"), 1, 0)
        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText("미입력시 미상")
        self.name_input.setMaximumWidth(180)
        self.name_input.setFixedHeight(34)
        grid.addWidget(self.name_input, 1, 1)

        grid.addWidget(self._make_label("연령"), 1, 2)
        self.age_input = QLineEdit()
        self.age_input.setPlaceholderText("미상")
        self.age_input.setFixedWidth(60)
        self.age_input.setFixedHeight(34)
        grid.addWidget(self.age_input, 1, 3)

        self.severity_combo = QComboBox()
        self.severity_combo.addItems(["지연", "긴급", "응급", "비응급"])
        self.severity_combo.setFixedWidth(80)
        self.severity_combo.setFixedHeight(34)
        grid.addWidget(self.severity_combo, 1, 4)

        grid.addWidget(self._make_label("구조위치"), 1, 5)
        self.location_input = QLineEdit()
        self.location_input.setPlaceholderText("")
        self.location_input.setFixedHeight(34)
        grid.addWidget(self.location_input, 1, 6)

        # 열 비율: 최초상태/구조위치 확장
        grid.setColumnStretch(6, 2)

        self.input_main_layout.addLayout(grid)

    def _build_transfer_out_form(self):
        """인계 모드 입력 폼 (2줄)"""
        self._clear_input_form()

        info_style = "color: #e0e8f0; font-size: 13px; font-weight: bold; background: #0a1628; border: 1px solid #1e3a5f; border-radius: 4px; padding: 4px 8px;"

        # 1줄: 인계시각 | 대상자 | 성별 | 연령
        row1 = QHBoxLayout()
        row1.setSpacing(10)
        row1.addWidget(self._make_label("시각"))
        time_frame, self.time_input = self._make_time_input()
        time_frame.setFixedWidth(180)
        row1.addWidget(time_frame)
        row1.addWidget(self._make_label("대상자"))
        self.target_combo = QComboBox()
        self.target_combo.setMinimumWidth(160)
        self.target_combo.setFixedHeight(34)
        self._populate_passenger_combo()
        self.target_combo.currentIndexChanged.connect(self._on_passenger_selected)
        row1.addWidget(self.target_combo)
        row1.addWidget(self._make_label("성별"))
        self.gender_label = QLabel("남")
        self.gender_label.setFixedWidth(40)
        self.gender_label.setFixedHeight(34)
        self.gender_label.setAlignment(Qt.AlignCenter)
        self.gender_label.setStyleSheet(info_style)
        row1.addWidget(self.gender_label)
        row1.addWidget(self._make_label("연령"))
        self.age_label = QLabel("미상")
        self.age_label.setFixedWidth(50)
        self.age_label.setFixedHeight(34)
        self.age_label.setAlignment(Qt.AlignCenter)
        self.age_label.setStyleSheet(info_style)
        row1.addWidget(self.age_label)
        row1.addStretch()
        self.input_main_layout.addLayout(row1)

        # 2줄: 인계대상 | 기타사항
        row2 = QHBoxLayout()
        row2.setSpacing(10)
        row2.addWidget(self._make_label("인계대상"))
        self.transfer_target_input = QLineEdit()
        self.transfer_target_input.setPlaceholderText("세력/기관")
        self.transfer_target_input.setFixedHeight(34)
        row2.addWidget(self.transfer_target_input, 1)
        row2.addWidget(self._make_label("기타사항"))
        self.etc_input = QLineEdit()
        self.etc_input.setPlaceholderText("")
        self.etc_input.setFixedHeight(34)
        row2.addWidget(self.etc_input, 3)
        self.input_main_layout.addLayout(row2)

        self._on_passenger_selected(0)

    def _build_transfer_in_form(self):
        """인수 모드 입력 폼 (2줄)"""
        self._clear_input_form()

        # 1줄: 인수시각 | 이름 | 성별 | 연령 | 중증도
        row1 = QHBoxLayout()
        row1.setSpacing(8)
        row1.addWidget(self._make_label("시각"))
        time_frame, self.time_input = self._make_time_input()
        time_frame.setFixedWidth(180)
        row1.addWidget(time_frame)
        row1.addWidget(self._make_label("이름"))
        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText("미입력시 미상")
        self.name_input.setMinimumWidth(100)
        self.name_input.setFixedHeight(34)
        row1.addWidget(self.name_input, 1)
        row1.addWidget(self._make_label("성별"))
        self.gender_combo = QComboBox()
        self.gender_combo.addItems(["남", "여"])
        self.gender_combo.setFixedWidth(60)
        self.gender_combo.setFixedHeight(34)
        row1.addWidget(self.gender_combo)
        row1.addWidget(self._make_label("연령"))
        self.age_input = QLineEdit()
        self.age_input.setPlaceholderText("미상")
        self.age_input.setFixedWidth(60)
        self.age_input.setFixedHeight(34)
        row1.addWidget(self.age_input)
        row1.addWidget(self._make_label("중증도"))
        self.severity_combo = QComboBox()
        self.severity_combo.addItems(["지연", "긴급", "응급", "비응급"])
        self.severity_combo.setFixedWidth(80)
        self.severity_combo.setFixedHeight(34)
        row1.addWidget(self.severity_combo)
        self.input_main_layout.addLayout(row1)

        # 2줄: 인수당시상태 | 인수세력
        row2 = QHBoxLayout()
        row2.setSpacing(8)
        row2.addWidget(self._make_label("인수세력"))
        self.transfer_target_input = QLineEdit()
        self.transfer_target_input.setPlaceholderText("")
        self.transfer_target_input.setFixedHeight(34)
        row2.addWidget(self.transfer_target_input, 1)
        row2.addSpacing(8)
        row2.addWidget(self._make_label("인수당시 상태"))
        self.state_input = QLineEdit()
        self.state_input.setPlaceholderText("미입력시 공란")
        self.state_input.setFixedHeight(34)
        row2.addWidget(self.state_input, 3)
        self.input_main_layout.addLayout(row2)

    def _populate_passenger_combo(self):
        """현재 탑승자 드롭다운 갱신"""
        if not hasattr(self, 'target_combo'):
            return
        self.target_combo.clear()
        passengers = self._get_current_passengers()
        for rec in passengers:
            self.target_combo.addItem(
                f"{rec['name']} ({rec['gender']}/{rec['age']})",
                rec["id"]
            )

    def _get_current_passengers(self) -> list:
        """현재 탑승자: rescue(not transferred) + transfer_in"""
        result = []
        for r in self.dm.rescue_records:
            if r["type"] == "rescue" and not r.get("transferred", False):
                result.append(r)
            elif r["type"] == "transfer_in":
                result.append(r)
        return result

    def _on_passenger_selected(self, index):
        """인계 대상자 선택 시 성별/연령 자동 채움"""
        if not hasattr(self, 'target_combo') or not hasattr(self, 'gender_label'):
            return
        record_id = self.target_combo.currentData()
        if record_id:
            for r in self.dm.rescue_records:
                if r["id"] == record_id:
                    self.gender_label.setText(r.get("gender", "남"))
                    self.age_label.setText(r.get("age", "미상"))
                    return
        self.gender_label.setText("남")
        self.age_label.setText("미상")

    def _make_label(self, text: str) -> QLabel:
        lbl = QLabel(text)
        lbl.setStyleSheet("color: #e0e8f0; font-size: 14px; font-weight: bold; background: transparent; border: none;")
        return lbl

    def _set_mode(self, mode: str):
        self._current_mode = mode
        for key, btn in self.mode_buttons.items():
            is_active = key == mode
            btn.setChecked(is_active)
            if is_active:
                color = TYPE_BADGE_COLORS.get(key, "#00d4ff")
                btn.setStyleSheet(f"""
                    QPushButton {{ background: rgba({self._hex_to_rgb(color)}, 0.2);
                    border: 2px solid {color}; color: {color}; font-weight: bold;
                    border-radius: 4px; font-size: 12px; }}
                """)
            else:
                btn.setStyleSheet("")

        # 적용 버튼 텍스트 변경
        mode_btn_labels = {
            "rescue": "구조\n등록",
            "transfer_out": "인계\n등록",
            "transfer_in": "인수\n등록",
        }
        self.apply_btn.setText(mode_btn_labels.get(mode, "등록"))

        if mode == "rescue":
            self._build_rescue_form()
        elif mode == "transfer_out":
            self._build_transfer_out_form()
        elif mode == "transfer_in":
            self._build_transfer_in_form()

    def _set_filter(self, filter_key: str):
        self._current_filter = filter_key
        for key, btn in self.filter_buttons.items():
            is_active = key == filter_key
            btn.setChecked(is_active)
            if is_active:
                btn.setStyleSheet("""
                    QPushButton { background: rgba(0, 212, 255, 0.15);
                    border: 1px solid #00d4ff; color: #00d4ff; font-weight: bold;
                    border-radius: 4px; font-size: 13px; }
                """)
            else:
                btn.setStyleSheet("QPushButton { font-size: 13px; }")
        self._refresh_table()

    def _apply_record(self):
        """적용 버튼 클릭"""
        mode = self._current_mode

        if mode == "rescue":
            self._apply_rescue()
        elif mode == "transfer_out":
            self._apply_transfer_out()
        elif mode == "transfer_in":
            self._apply_transfer_in()

    def _apply_rescue(self):
        """구조 기록 추가"""
        name = self.name_input.text().strip()
        if not name:
            name = self.dm.get_next_unknown_name()

        age = self.age_input.text().strip() if hasattr(self, 'age_input') else "미상"
        if not age:
            age = "미상"

        data = {
            "type": "rescue",
            "timestamp": self.time_input.text().strip(),
            "location": self.location_input.text().strip(),
            "name": name,
            "gender": self.gender_combo.currentText(),
            "age": age,
            "severity": self.severity_combo.currentText(),
            "initial_state": self.state_input.text().strip(),
        }
        record = self.dm.add_rescue_record(data)
        self.log_message.emit(f"[구조] {name} ({data['gender']}/{age}) {data['severity']} - {data.get('location', '')}")

        # Clear inputs
        self.time_input.clear()
        self.location_input.clear()
        self.name_input.clear()
        if hasattr(self, 'age_input'):
            self.age_input.clear()
        self.state_input.clear()
        self.severity_combo.setCurrentIndex(0)

        self._refresh_table()
        self.records_changed.emit()

    def _apply_transfer_out(self):
        """인계 기록 추가"""
        if not hasattr(self, 'target_combo') or self.target_combo.count() == 0:
            return

        source_id = self.target_combo.currentData()
        if not source_id:
            return

        # Find source record
        source_rec = None
        for r in self.dm.rescue_records:
            if r["id"] == source_id:
                source_rec = r
                break
        if not source_rec:
            return

        timestamp = self.time_input.text().strip()
        transfer_target = self.transfer_target_input.text().strip()

        # Create transfer_out record
        data = {
            "type": "transfer_out",
            "timestamp": timestamp,
            "name": source_rec["name"],
            "gender": source_rec["gender"],
            "age": source_rec["age"],
            "severity": source_rec["severity"],
            "initial_state": source_rec.get("initial_state", ""),
            "treatment": source_rec.get("treatment", ""),
            "transfer_target": transfer_target,
            "source_record_id": source_id,
        }
        record = self.dm.add_rescue_record(data)

        # Mark original as transferred
        self.dm.update_rescue_record(source_id, "transferred", True)
        self.dm.update_rescue_record(source_id, "transfer_target", transfer_target)
        self.dm.update_rescue_record(source_id, "transfer_timestamp", timestamp)

        self.log_message.emit(f"[인계] {source_rec['name']} → {transfer_target}")

        # Clear inputs
        self.time_input.clear()
        self.transfer_target_input.clear()

        # Refresh passenger combo
        self._populate_passenger_combo()
        self._refresh_table()
        self.records_changed.emit()

    def _apply_transfer_in(self):
        """인수 기록 추가"""
        name = self.name_input.text().strip()
        if not name:
            name = self.dm.get_next_unknown_name()

        age = ""
        if hasattr(self, 'age_input'):
            age = self.age_input.text().strip()
        elif hasattr(self, 'age_combo'):
            age = self.age_combo.currentText()
        if not age:
            age = "미상"

        transfer_target = self.transfer_target_input.text().strip()

        data = {
            "type": "transfer_in",
            "timestamp": self.time_input.text().strip(),
            "name": name,
            "gender": self.gender_combo.currentText(),
            "age": age,
            "severity": self.severity_combo.currentText(),
            "initial_state": self.state_input.text().strip(),
            "treatment": "",
            "transfer_target": transfer_target,
        }
        record = self.dm.add_rescue_record(data)
        self.log_message.emit(f"[인수] {name} ({data['gender']}/{age}) {data['severity']} ← {transfer_target}")

        # Clear inputs
        self.time_input.clear()
        self.name_input.clear()
        if hasattr(self, 'age_input'):
            self.age_input.clear()
        elif hasattr(self, 'age_combo'):
            self.age_combo.setCurrentIndex(0)
        self.state_input.clear()
        self.transfer_target_input.clear()
        self.severity_combo.setCurrentIndex(0)

        self._refresh_table()
        self.records_changed.emit()

    def _get_filtered_records(self) -> list:
        """현재 필터에 따른 레코드 반환"""
        f = self._current_filter
        records = self.dm.rescue_records

        if f == "all":
            return list(records)
        elif f == "current":
            return [r for r in records
                    if (r["type"] == "rescue" and not r.get("transferred", False))
                    or r["type"] == "transfer_in"]
        elif f == "rescue":
            return [r for r in records if r["type"] == "rescue"]
        elif f == "transfer_out":
            return [r for r in records if r["type"] == "transfer_out"]
        elif f == "transfer_in":
            return [r for r in records if r["type"] == "transfer_in"]
        return list(records)

    def _get_columns_for_filter(self) -> list:
        """현재 필터에 따른 컬럼 목록"""
        f = self._current_filter
        if f == "rescue":
            return ["일시", "구조위치", "이름", "성별", "연령", "중증도", "최초상태", "조치경과", "인계", "인계대상"]
        elif f == "transfer_out":
            return ["인계일시", "이름", "성별", "연령", "중증도", "최초상태", "조치경과", "인계대상"]
        elif f == "transfer_in":
            return ["인수일시", "이름", "성별", "연령", "중증도", "인수당시 상태", "조치경과", "인수세력"]
        else:
            # all / current
            return ["유형", "일시", "이름", "성별", "연령", "중증도", "최초상태", "조치경과", "비고"]

    def _refresh_table(self):
        """테이블 갱신"""
        # Clear table
        while self.table_layout.count():
            item = self.table_layout.takeAt(0)
            w = item.widget()
            if w:
                w.setParent(None)

        records = self._get_filtered_records()
        columns = self._get_columns_for_filter()

        # Header row
        header_frame = QFrame()
        header_frame.setStyleSheet("""
            QFrame { background: rgba(0, 212, 255, 0.08); border-bottom: 1px solid #1a2d4a;
                     border-radius: 0; }
        """)
        header_grid = QHBoxLayout(header_frame)
        header_grid.setContentsMargins(8, 4, 8, 4)
        header_grid.setSpacing(2)

        col_widths = self._get_col_widths(columns)
        for i, col in enumerate(columns):
            lbl = QLabel(col)
            lbl.setStyleSheet("color: #00d4ff; font-size: 13px; font-weight: bold; background: transparent; border: none;")
            lbl.setAlignment(Qt.AlignCenter)
            if col_widths[i] == -1:
                header_grid.addWidget(lbl, 1)
            else:
                lbl.setFixedWidth(col_widths[i])
                header_grid.addWidget(lbl)
        self.table_layout.addWidget(header_frame)

        # Data rows
        for record in records:
            row_widget = self._create_row_widget(record, columns, col_widths)
            self.table_layout.addWidget(row_widget)

        self.table_layout.addStretch()

    def _get_col_widths(self, columns: list) -> list:
        """컬럼별 너비 (-1은 stretch 대상)"""
        width_map = {
            "유형": 55, "일시": 100, "인계일시": 100, "인수일시": 100,
            "구조위치": 100, "이름": 80, "성별": 35, "연령": 40,
            "중증도": 65, "최초상태": -1, "인수당시 상태": -1,
            "조치경과": -1, "인계": 35,
            "인계대상": 100, "인수세력": 100, "비고": 100,
        }
        return [width_map.get(c, 80) for c in columns]

    def _make_editable_cell(self, record, field, display_text, width, stretch=False, edit_type="text", options=None):
        """인라인 편집 가능한 셀 생성"""
        from PySide6.QtWidgets import QStackedWidget

        stack = QStackedWidget()
        if not stretch and width > 0:
            stack.setFixedWidth(width)

        stack.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Maximum)

        # --- Page 0: 표시 모드 ---
        display_frame = QFrame()
        display_frame.setStyleSheet("QFrame { background: transparent; border: none; }")
        df_layout = QHBoxLayout(display_frame)
        df_layout.setContentsMargins(0, 0, 0, 0)
        df_layout.setSpacing(2)

        if field == "severity":
            sev_color = SEVERITY_COLORS.get(display_text, "#8faabe")
            lbl = QLabel(display_text)
            lbl.setStyleSheet(f"color: {sev_color}; font-size: 13px; font-weight: bold; background: transparent; border: none;")
        elif edit_type == "dialog":
            lbl = QLabel(display_text if display_text else "")
            lbl.setStyleSheet("color: #ffffff; font-size: 13px; font-weight: bold; background: transparent; border: none;")
        else:
            lbl = QLabel(display_text)
            lbl.setStyleSheet("color: #ffffff; font-size: 13px; font-weight: bold; background: transparent; border: none;")
        lbl.setAlignment(Qt.AlignCenter)
        df_layout.addWidget(lbl, 1)

        edit_btn = QPushButton("수정")
        edit_btn.setFixedSize(32, 18)
        edit_btn.setStyleSheet("""
            QPushButton { background: rgba(0,212,255,0.15); color: #00d4ff; border: 1px solid rgba(0,212,255,0.4);
                          border-radius: 3px; font-size: 10px; font-weight: bold; padding: 0; }
            QPushButton:hover { background: rgba(0,212,255,0.3); }
        """)
        edit_btn.hide()
        df_layout.addWidget(edit_btn)

        display_frame.enterEvent = lambda e: edit_btn.show()
        display_frame.leaveEvent = lambda e: edit_btn.hide()

        stack.addWidget(display_frame)

        # --- Page 1: 편집 모드 ---
        edit_frame = QFrame()
        edit_frame.setStyleSheet("QFrame { background: transparent; border: none; }")
        ef_layout = QHBoxLayout(edit_frame)
        ef_layout.setContentsMargins(0, 0, 0, 0)
        ef_layout.setSpacing(2)

        if edit_type == "dialog":
            # 조치경과 / 최초상태: 다이얼로그 팝업
            edit_btn.clicked.connect(lambda: self._edit_field_dialog(record, field, lbl))
            stack.addWidget(edit_frame)  # placeholder, 실제 사용 안 함
        elif edit_type == "combo":
            combo = QComboBox()
            combo.addItems(options or [])
            combo.setFixedHeight(22)
            combo.setStyleSheet("QComboBox { background: #0a1628; color: #e0e8f0; border: 1px solid #00d4ff; border-radius: 3px; font-size: 12px; padding: 1px; }")
            ef_layout.addWidget(combo, 1)
            ok_btn = QPushButton("확인")
            ok_btn.setFixedSize(32, 20)
            ok_btn.setStyleSheet("""
                QPushButton { background: rgba(0,212,255,0.2); color: #00d4ff; border: 1px solid #00d4ff;
                              border-radius: 3px; font-size: 10px; font-weight: bold; }
                QPushButton:hover { background: rgba(0,212,255,0.4); }
            """)
            ef_layout.addWidget(ok_btn)
            stack.addWidget(edit_frame)

            def start_combo_edit():
                combo.setCurrentText(lbl.text())
                stack.setCurrentIndex(1)
            def finish_combo_edit():
                new_val = combo.currentText()
                self.dm.update_rescue_record(record["id"], field, new_val)
                if field == "severity":
                    sev_c = SEVERITY_COLORS.get(new_val, "#8faabe")
                    lbl.setStyleSheet(f"color: {sev_c}; font-size: 13px; font-weight: bold; background: transparent; border: none;")
                lbl.setText(new_val)
                stack.setCurrentIndex(0)
                self.records_changed.emit()

            edit_btn.clicked.connect(start_combo_edit)
            ok_btn.clicked.connect(finish_combo_edit)
        else:
            # 텍스트 인라인 편집
            inp = QLineEdit()
            inp.setFixedHeight(22)
            inp.setStyleSheet("QLineEdit { background: #0a1628; color: #e0e8f0; border: 1px solid #00d4ff; border-radius: 3px; font-size: 12px; padding: 1px; }")
            ef_layout.addWidget(inp, 1)
            ok_btn = QPushButton("확인")
            ok_btn.setFixedSize(32, 20)
            ok_btn.setStyleSheet("""
                QPushButton { background: rgba(0,212,255,0.2); color: #00d4ff; border: 1px solid #00d4ff;
                              border-radius: 3px; font-size: 10px; font-weight: bold; }
                QPushButton:hover { background: rgba(0,212,255,0.4); }
            """)
            ef_layout.addWidget(ok_btn)
            stack.addWidget(edit_frame)

            def start_text_edit():
                inp.setText(lbl.text())
                stack.setCurrentIndex(1)
                inp.setFocus()
                inp.selectAll()
            def finish_text_edit():
                new_val = inp.text().strip()
                if field == "transfer_target":
                    self._sync_transfer_target(record, new_val)
                else:
                    self.dm.update_rescue_record(record["id"], field, new_val)
                lbl.setText(new_val)
                stack.setCurrentIndex(0)
                self.records_changed.emit()

            edit_btn.clicked.connect(start_text_edit)
            ok_btn.clicked.connect(finish_text_edit)
            inp.returnPressed.connect(finish_text_edit)

        return stack

    def _sync_transfer_target(self, record, new_val):
        """인계대상 수정 시 rescue ↔ transfer_out 양쪽 동기화"""
        rec_id = record["id"]
        rec_type = record.get("type", "")
        self.dm.update_rescue_record(rec_id, "transfer_target", new_val)
        if rec_type == "rescue":
            # rescue → 대응하는 transfer_out도 수정
            for r in self.dm.rescue_records:
                if r.get("source_record_id") == rec_id:
                    self.dm.update_rescue_record(r["id"], "transfer_target", new_val)
        elif rec_type == "transfer_out":
            # transfer_out → 원본 rescue도 수정
            source_id = record.get("source_record_id")
            if source_id:
                self.dm.update_rescue_record(source_id, "transfer_target", new_val)

    def _edit_field_dialog(self, record, field, label_widget):
        """다이얼로그 방식 편집 (조치경과, 최초상태)"""
        field_names = {"treatment": "조치 및 경과", "initial_state": "최초상태"}
        dlg = TreatmentEditDialog(
            record.get(field, ""),
            f"{record.get('name', '')} - {field_names.get(field, field)}",
            self
        )
        if dlg.exec() == QDialog.Accepted:
            new_text = dlg.get_text()
            self.dm.update_rescue_record(record["id"], field, new_text)
            label_widget.setText(new_text)
            self.records_changed.emit()

    def _create_row_widget(self, record: dict, columns: list, col_widths: list) -> QFrame:
        """테이블 행 위젯 생성"""
        row = QFrame()
        row.setStyleSheet("""
            QFrame { background: transparent; border-bottom: 1px solid rgba(0, 212, 255, 0.12);
                     border-radius: 0; }
            QFrame:hover { background: rgba(0, 212, 255, 0.04); }
        """)
        row_layout = QHBoxLayout(row)
        row_layout.setContentsMargins(8, 2, 8, 2)
        row_layout.setSpacing(2)

        rec_type = record.get("type", "rescue")

        # 컬럼→(data_field, edit_type, options) 매핑
        col_config = {
            "일시": ("timestamp", "text", None),
            "인계일시": ("timestamp", "text", None),
            "인수일시": ("timestamp", "text", None),
            "구조위치": ("location", "text", None),
            "이름": ("name", "text", None),
            "성별": ("gender", "combo", ["남", "여"]),
            "연령": ("age", "text", None),
            "중증도": ("severity", "combo", ["지연", "긴급", "응급", "비응급"]),
            "최초상태": ("initial_state", "dialog", None),
            "인수당시 상태": ("initial_state", "dialog", None),
            "조치경과": ("treatment", "dialog", None),
            "인계대상": ("transfer_target", "text", None),
            "인수세력": ("transfer_target", "text", None),
        }

        for i, col in enumerate(columns):
            w = col_widths[i]
            is_stretch = (w == -1)

            if col == "유형":
                badge = QLabel(TYPE_LABELS.get(rec_type, "구조"))
                badge_color = TYPE_BADGE_COLORS.get(rec_type, "#00d4ff")
                badge.setStyleSheet(f"""
                    QLabel {{ background: rgba({self._hex_to_rgb(badge_color)}, 0.15);
                    color: {badge_color}; font-size: 12px; font-weight: bold;
                    border: 1px solid rgba({self._hex_to_rgb(badge_color)}, 0.4);
                    border-radius: 3px; padding: 2px 6px; }}
                """)
                badge.setAlignment(Qt.AlignCenter)
                badge.setFixedWidth(w)
                row_layout.addWidget(badge)
            elif col == "인계":
                transferred = record.get("transferred", False)
                lbl = QLabel("O" if transferred else "X")
                color = "#2ecc71" if transferred else "#5a7a9a"
                lbl.setStyleSheet(f"color: {color}; font-size: 13px; font-weight: bold; background: transparent; border: none;")
                lbl.setAlignment(Qt.AlignCenter)
                lbl.setFixedWidth(w)
                row_layout.addWidget(lbl)
            elif col == "비고":
                text = ""
                if rec_type == "rescue":
                    if record.get("transferred"):
                        text = f"→{record.get('transfer_target', '')}"
                    else:
                        text = record.get("location", "")
                elif rec_type in ("transfer_out", "transfer_in"):
                    text = record.get("transfer_target", "")
                lbl = QLabel(text)
                lbl.setStyleSheet("color: #ffffff; font-size: 13px; font-weight: bold; background: transparent; border: none;")
                lbl.setAlignment(Qt.AlignCenter)
                lbl.setFixedWidth(w)
                row_layout.addWidget(lbl)
            elif col in col_config:
                field, edit_type, options = col_config[col]
                display_text = record.get(field, "")
                cell = self._make_editable_cell(record, field, display_text, w, stretch=is_stretch, edit_type=edit_type, options=options)
                if is_stretch:
                    row_layout.addWidget(cell, 1)
                else:
                    row_layout.addWidget(cell)
            else:
                lbl = QLabel("")
                if not is_stretch and w > 0:
                    lbl.setFixedWidth(w)
                row_layout.addWidget(lbl, 1 if is_stretch else 0)

        return row

    def refresh(self):
        """외부에서 호출 가능한 갱신"""
        if self._current_mode == "transfer_out":
            self._populate_passenger_combo()
        self._refresh_table()
        self.records_changed.emit()

    def get_summary_data(self) -> dict:
        """사이드바 요약 카드용 데이터"""
        records = self.dm.rescue_records
        severities = ["지연", "긴급", "응급", "비응급"]

        def count_by_severity(rec_list):
            counts = {}
            for s in severities:
                counts[s] = sum(1 for r in rec_list if r.get("severity") == s)
            return counts

        # 현재원: rescue(not transferred) + transfer_in
        current = [r for r in records
                   if (r["type"] == "rescue" and not r.get("transferred", False))
                   or r["type"] == "transfer_in"]
        rescue_only = [r for r in records if r["type"] == "rescue"]
        transfer_out = [r for r in records if r["type"] == "transfer_out"]
        transfer_in = [r for r in records if r["type"] == "transfer_in"]

        return {
            "현재원": {"total": len(current), "by_severity": count_by_severity(current)},
            "본함구조": {"total": len(rescue_only), "by_severity": count_by_severity(rescue_only)},
            "인계현황": {"total": len(transfer_out), "by_severity": count_by_severity(transfer_out)},
            "인수현황": {"total": len(transfer_in), "by_severity": count_by_severity(transfer_in)},
        }

    @staticmethod
    def _hex_to_rgb(hex_color: str) -> str:
        """#RRGGBB -> R, G, B"""
        h = hex_color.lstrip("#")
        return f"{int(h[0:2], 16)}, {int(h[2:4], 16)}, {int(h[4:6], 16)}"
