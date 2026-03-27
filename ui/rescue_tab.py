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
        self._selected_record = None   # 현재 선택된 행의 record
        self._selected_row_widget = None  # 현재 선택된 행 위젯
        self._active_edit_stack = None  # 현재 편집 중인 스택 위젯
        self._sort_col = None  # 현재 정렬 컬럼
        self._sort_asc = True  # 오름차순 여부
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

        self.sort_reset_btn = QPushButton("정렬 초기화")
        self.sort_reset_btn.setFixedHeight(30)
        self.sort_reset_btn.setStyleSheet("""
            QPushButton { background: #27ae60; color: #ffffff; font-size: 12px; font-weight: bold;
                          border: 1px solid #2ecc71; border-radius: 4px; padding: 0 8px; }
            QPushButton:hover { background: #2ecc71; }
        """)
        self.sort_reset_btn.clicked.connect(self._reset_sort)
        self.sort_reset_btn.hide()
        filter_row.addWidget(self.sort_reset_btn)

        self.delete_btn = QPushButton("삭제")
        self.delete_btn.setFixedHeight(30)
        self.delete_btn.setFixedWidth(55)
        self.delete_btn.setStyleSheet("""
            QPushButton { background: #c0392b; color: #ffffff; font-size: 13px; font-weight: bold;
                          border: 1px solid #e74c3c; border-radius: 4px; }
            QPushButton:hover { background: #e74c3c; }
            QPushButton:disabled { background: #555555; color: #888888; border-color: #666666; }
        """)
        self.delete_btn.setEnabled(False)
        self.delete_btn.clicked.connect(self._delete_selected_record)
        filter_row.addWidget(self.delete_btn)

        panel_layout.addLayout(filter_row)

        # === 고정 헤더 ===
        self.header_container = QWidget()
        self.header_layout = QVBoxLayout(self.header_container)
        self.header_layout.setContentsMargins(0, 0, 0, 0)
        self.header_layout.setSpacing(0)
        panel_layout.addWidget(self.header_container)

        # === Table area (scrollable, 데이터만) ===
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

        # 2줄: 인수당시상태 | 인수대상
        row2 = QHBoxLayout()
        row2.setSpacing(8)
        row2.addWidget(self._make_label("인수대상"))
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
        ts = data['timestamp']
        state = data.get('initial_state', '')
        parts = [f"{name}({data['gender']}, {self._fmt_age(age)})", data['severity']]
        if state:
            parts.append(state)
        msg = ", ".join(parts)
        prefix = f"{ts} " if ts else ""
        self._emit_log(f"{prefix}[구조] {msg}")

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
        if not transfer_target:
            self._show_toast("인계대상을 입력해주세요")
            return

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

        etc = self.etc_input.text().strip() if hasattr(self, 'etc_input') else ""
        parts = [f"{source_rec['name']}({source_rec['gender']}, {self._fmt_age(source_rec['age'])})", source_rec['severity']]
        if etc:
            parts.append(etc)
        msg = ", ".join(parts)
        prefix = f"{timestamp} " if timestamp else ""
        self._emit_log(f"{prefix}[{transfer_target}에 인계] {msg}")

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
        if not transfer_target:
            self._show_toast("인수대상을 지정해주세요")
            return

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
        ts = data['timestamp']
        state = data.get('initial_state', '')
        parts = [f"{name}({data['gender']}, {self._fmt_age(age)})", data['severity']]
        if state:
            parts.append(state)
        msg = ", ".join(parts)
        prefix = f"{ts} " if ts else ""
        self._emit_log(f"{prefix}[{transfer_target}으로부터 인수] {msg}")

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

    def _show_toast(self, message: str):
        """토스트 메시지 표시"""
        from PySide6.QtCore import QTimer
        toast = QLabel(message, self)
        toast.setStyleSheet("""
            QLabel { background: rgba(231, 76, 60, 0.9); color: #ffffff; font-size: 13px;
                     font-weight: bold; padding: 8px 16px; border-radius: 6px; }
        """)
        toast.setAlignment(Qt.AlignCenter)
        toast.adjustSize()
        toast.move((self.width() - toast.width()) // 2, 80)
        toast.show()
        QTimer.singleShot(2000, lambda: (toast.hide(), toast.deleteLater()))

    _FIELD_NAMES = {
        "timestamp": "일시", "location": "구조위치", "name": "이름",
        "gender": "성별", "age": "연령", "severity": "중증도",
        "initial_state": "최초상태", "treatment": "조치경과",
        "transfer_target": "인계/인수대상", "transferred": "인계여부",
    }

    def _get_field_display_name(self, record: dict, field: str) -> str:
        """레코드 유형에 따른 필드 표시명"""
        rec_type = record.get("type", "rescue")
        if field == "timestamp":
            if rec_type == "rescue":
                return "구조일시"
            elif rec_type == "transfer_out":
                return "인계일시"
            elif rec_type == "transfer_in":
                return "인수일시"
            return "일시"
        if field == "initial_state":
            if rec_type == "transfer_in":
                return "인수당시 상태"
            return "최초상태"
        return self._FIELD_NAMES.get(field, field)

    def _log_edit(self, record: dict, field: str, old_val, new_val):
        """수정 내역을 작전 로그에 기록"""
        # 이름 변경 시 이전 이름 기준으로 표시
        if field == "name":
            display_name = old_val if old_val else "미상"
        else:
            display_name = record.get("name", "미상")

        field_name = self._get_field_display_name(record, field)

        # 여러 줄 필드: 수정 전/후 형식
        if field in ("initial_state", "treatment"):
            old_display = old_val if old_val else "(빈값)"
            new_display = new_val if new_val else "(빈값)"
            self._emit_log(
                f"[수정] {display_name} {field_name} 변경\n"
                f"[수정 전]\n{old_display}\n"
                f"[수정 후]\n{new_display}"
            )
        else:
            old_short = str(old_val)[:20] if old_val else "(빈값)"
            new_short = str(new_val)[:20] if new_val else "(빈값)"
            self._emit_log(f"[수정] {display_name} {field_name} 변경 : {old_short} → {new_short}")

    def _fmt_age(self, age: str) -> str:
        """연령 표시: 미상 → '연령 미상', 숫자 → 그대로"""
        if not age or age == "미상":
            return "연령 미상"
        return age

    def _emit_log(self, message: str):
        """작전 로그에 기록 + 시그널 발행"""
        self.dm.add_log(message)
        self.log_message.emit(message)

    def _record_history(self, record: dict, field: str, old_val, new_val):
        """변경 이력 기록"""
        if old_val == new_val:
            return
        if "_history" not in record:
            record["_history"] = []
        record["_history"].append({
            "time": time.strftime("%m.%d %H:%M:%S"),
            "field": field,
            "old": str(old_val),
            "new": str(new_val),
        })

    def _toggle_sort(self, col: str):
        """헤더 클릭 시 정렬 토글"""
        if self._sort_col == col:
            self._sort_asc = not self._sort_asc
        else:
            self._sort_col = col
            self._sort_asc = True
        self.sort_reset_btn.show()
        self._refresh_table()

    def _reset_sort(self):
        """정렬 초기화"""
        self._sort_col = None
        self._sort_asc = True
        self.sort_reset_btn.hide()
        self._refresh_table()

    def _sort_records(self, records: list) -> list:
        """현재 정렬 설정에 따라 레코드 정렬"""
        if not self._sort_col:
            return records

        # 컬럼→데이터필드 매핑
        col_field = {
            "유형": "type", "일시": "timestamp", "인계일시": "timestamp", "인수일시": "timestamp",
            "성별": "gender", "연령": "age", "중증도": "severity",
            "인계": "transferred", "인계대상": "transfer_target",
            "인수대상": "transfer_target", "인계/인수": "transfer_target",
        }
        field = col_field.get(self._sort_col)
        if not field:
            return records

        # 중증도 정렬 우선순위
        sev_order = {"지연": 0, "긴급": 1, "응급": 2, "비응급": 3}
        type_order = {"rescue": 0, "transfer_out": 1, "transfer_in": 2}

        def sort_key(r):
            val = r.get(field, "")
            if field == "severity":
                return sev_order.get(val, 99)
            elif field == "type":
                return type_order.get(val, 99)
            elif field == "age":
                try:
                    return int(val) if val and val != "미상" else 9999
                except ValueError:
                    return 9999
            elif field == "transferred":
                return 0 if val else 1
            return str(val or "")

        return sorted(records, key=sort_key, reverse=not self._sort_asc)

    def _get_filtered_records(self) -> list:
        """현재 필터에 따른 레코드 반환"""
        f = self._current_filter
        records = self.dm.rescue_records

        if f == "all":
            result = list(records)
        elif f == "current":
            result = [r for r in records
                      if (r["type"] == "rescue" and not r.get("transferred", False))
                      or r["type"] == "transfer_in"]
        elif f == "rescue":
            result = [r for r in records if r["type"] == "rescue"]
        elif f == "transfer_out":
            result = [r for r in records if r["type"] == "transfer_out"]
        elif f == "transfer_in":
            result = [r for r in records if r["type"] == "transfer_in"]
        else:
            result = list(records)

        return self._sort_records(result)

    def _get_columns_for_filter(self) -> list:
        """현재 필터에 따른 컬럼 목록"""
        f = self._current_filter
        if f == "rescue":
            return ["일시", "구조위치", "이름", "성별", "연령", "중증도", "최초상태", "조치경과", "인계대상"]
        elif f == "transfer_out":
            return ["인계일시", "이름", "성별", "연령", "중증도", "최초상태", "조치경과", "인계대상"]
        elif f == "transfer_in":
            return ["인수일시", "이름", "성별", "연령", "중증도", "인수당시 상태", "조치경과", "인수대상"]
        else:
            # all / current
            return ["유형", "일시", "구조위치", "이름", "성별", "연령", "중증도", "최초/인수당시 상태", "조치경과", "인계/인수"]

    def _refresh_table(self):
        """테이블 갱신"""
        # 선택 초기화
        self._selected_record = None
        self._selected_row_widget = None
        self.delete_btn.setEnabled(False)
        # Clear header
        while self.header_layout.count():
            item = self.header_layout.takeAt(0)
            w = item.widget()
            if w:
                w.setParent(None)
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
        header_grid.setSpacing(0)

        # 정렬 가능 컬럼
        sortable = {"유형", "일시", "인계일시", "인수일시", "성별", "연령", "중증도", "인계대상", "인수대상", "인계/인수"}

        col_widths = self._get_col_widths(columns)
        for i, col in enumerate(columns):
            if i > 0:
                sep = QFrame()
                sep.setFixedWidth(1)
                sep.setStyleSheet("background: rgba(0, 212, 255, 0.08);")
                header_grid.addWidget(sep)

            if col in sortable:
                btn = QPushButton(col)
                active_style = "text-decoration: underline;" if self._sort_col == col else ""
                btn.setStyleSheet(f"""
                    QPushButton {{ color: #00d4ff; font-size: 13px; font-weight: bold;
                        background: transparent; border: none; padding: 0 2px; {active_style} }}
                    QPushButton:hover {{ color: #ffffff; }}
                """)
                btn.setCursor(Qt.PointingHandCursor)
                btn.clicked.connect(lambda checked, c=col: self._toggle_sort(c))
                if col_widths[i] == -1:
                    header_grid.addWidget(btn, 1)
                else:
                    btn.setFixedWidth(col_widths[i])
                    header_grid.addWidget(btn)
            else:
                lbl = QLabel(col)
                lbl.setStyleSheet("color: #00d4ff; font-size: 13px; font-weight: bold; background: transparent; border: none; padding: 0 2px;")
                lbl.setAlignment(Qt.AlignCenter)
                if col_widths[i] == -1:
                    header_grid.addWidget(lbl, 1)
                else:
                    lbl.setFixedWidth(col_widths[i])
                    header_grid.addWidget(lbl)

        # 이력 헤더
        sep = QFrame()
        sep.setFixedWidth(1)
        sep.setStyleSheet("background: rgba(0, 212, 255, 0.08);")
        header_grid.addWidget(sep)
        history_lbl = QLabel("이력")
        history_lbl.setStyleSheet("color: #00d4ff; font-size: 13px; font-weight: bold; background: transparent; border: none; padding: 0 2px;")
        history_lbl.setAlignment(Qt.AlignCenter)
        history_lbl.setFixedWidth(30)
        header_grid.addWidget(history_lbl)

        self.header_layout.addWidget(header_frame)

        # Data rows
        for record in records:
            row_widget = self._create_row_widget(record, columns, col_widths)
            self.table_layout.addWidget(row_widget)

        self.table_layout.addStretch()

    def _get_col_widths(self, columns: list) -> list:
        """컬럼별 너비 (-1은 stretch 대상)"""
        width_map = {
            "유형": 42, "일시": 90, "인계일시": 90, "인수일시": 90,
            "구조위치": 80, "이름": 65, "성별": 28, "연령": 32,
            "중증도": 52, "최초상태": -1, "인수당시 상태": -1, "최초/인수당시 상태": -1,
            "조치경과": -1, "인계": 28,
            "인계대상": 80, "인수대상": 80, "인계/인수": 80,
        }
        return [width_map.get(c, 80) for c in columns]

    def _make_editable_cell(self, record, field, display_text, width, stretch=False, edit_type="text", options=None):
        """인라인 편집 가능한 셀 생성 - 더블클릭 시 편집 모드 진입"""
        stack = QStackedWidget()
        if not stretch and width > 0:
            stack.setFixedWidth(width)
        stack.setFixedHeight(24)
        stack.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Fixed)

        # 텍스트 정렬: 최초상태/인수당시상태/조치경과는 왼쪽, 나머지는 가운데
        align = Qt.AlignLeft | Qt.AlignVCenter if field in ("initial_state", "treatment") else Qt.AlignCenter

        # --- Page 0: 표시 모드 ---
        if field == "severity":
            sev_color = SEVERITY_COLORS.get(display_text, "#8faabe")
            lbl = QLabel(display_text)
            lbl.setStyleSheet(f"color: {sev_color}; font-size: 13px; font-weight: bold; background: transparent; border: none;")
        else:
            # 첫 줄만 표시 (여러 줄 데이터 방지)
            first_line = (display_text or "").split("\n")[0]
            lbl = QLabel(first_line)
            lbl.setStyleSheet("color: #ffffff; font-size: 13px; font-weight: bold; background: transparent; border: none;")
        lbl.setAlignment(align)
        lbl.setWordWrap(False)
        lbl.setTextFormat(Qt.PlainText)
        stack.addWidget(lbl)

        # --- 편집 모드 ---
        start_edit_fn = None

        if edit_type == "dialog":
            start_edit_fn = lambda: self._edit_field_dialog(record, field, lbl)
        elif edit_type == "combo":
            edit_frame = QFrame()
            edit_frame.setStyleSheet("QFrame { background: transparent; border: none; }")
            ef_layout = QHBoxLayout(edit_frame)
            ef_layout.setContentsMargins(0, 0, 0, 0)
            ef_layout.setSpacing(0)
            combo = QComboBox()
            combo.addItems(options or [])
            combo.setFixedHeight(22)
            combo.setStyleSheet("QComboBox { background: #0a1628; color: #e0e8f0; border: 1px solid #00d4ff; border-radius: 3px; font-size: 12px; padding: 1px; }")
            ef_layout.addWidget(combo, 1)
            stack.addWidget(edit_frame)

            def start_combo_edit():
                combo.setCurrentText(lbl.text())
                stack.setCurrentIndex(1)
                combo.showPopup()
            def finish_combo_edit(index=None):
                new_val = combo.currentText()
                old_val = record.get(field, "")
                if old_val == new_val:
                    stack.setCurrentIndex(0)
                    return
                self._record_history(record, field, old_val, new_val)
                self.dm.update_rescue_record(record["id"], field, new_val)
                if field == "severity":
                    sev_c = SEVERITY_COLORS.get(new_val, "#8faabe")
                    lbl.setStyleSheet(f"color: {sev_c}; font-size: 13px; font-weight: bold; background: transparent; border: none;")
                lbl.setText(new_val)
                stack.setCurrentIndex(0)
                self._active_edit_stack = None
                self._log_edit(record, field, old_val, new_val)
                self.records_changed.emit()

            start_edit_fn = start_combo_edit
            combo.activated.connect(finish_combo_edit)
        else:
            edit_frame = QFrame()
            edit_frame.setStyleSheet("QFrame { background: transparent; border: none; }")
            ef_layout = QHBoxLayout(edit_frame)
            ef_layout.setContentsMargins(0, 0, 0, 0)
            ef_layout.setSpacing(0)
            inp = QLineEdit()
            inp.setFixedHeight(22)
            inp.setStyleSheet("QLineEdit { background: #0a1628; color: #e0e8f0; border: 1px solid #00d4ff; border-radius: 3px; font-size: 12px; padding: 1px; }")
            ef_layout.addWidget(inp, 1)
            stack.addWidget(edit_frame)

            def start_text_edit():
                inp.setText(lbl.text())
                stack.setCurrentIndex(1)
                inp.setFocus()
                inp.selectAll()
            def finish_text_edit():
                if stack.currentIndex() != 1:
                    return
                new_val = inp.text().strip()
                old_val = record.get(field, "")
                if old_val == new_val:
                    stack.setCurrentIndex(0)
                    return
                self._record_history(record, field, old_val, new_val)
                if field == "transfer_target":
                    self._sync_transfer_target(record, new_val)
                else:
                    self.dm.update_rescue_record(record["id"], field, new_val)
                lbl.setText(new_val)
                stack.setCurrentIndex(0)
                self._active_edit_stack = None
                self._log_edit(record, field, old_val, new_val)
                self.records_changed.emit()

            start_edit_fn = start_text_edit
            inp.returnPressed.connect(finish_text_edit)
            inp.editingFinished.connect(finish_text_edit)

        # 더블클릭으로 편집 시작 (기존 편집 취소 후)
        if start_edit_fn:
            fn = start_edit_fn
            def on_double_click(e, _fn=fn, _stack=stack):
                # 기존 편집 중인 스택 취소
                if self._active_edit_stack and self._active_edit_stack is not _stack:
                    self._active_edit_stack.setCurrentIndex(0)
                self._active_edit_stack = _stack
                _fn()
            lbl.mouseDoubleClickEvent = on_double_click

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
            old_text = record.get(field, "")
            if old_text != new_text:
                self._record_history(record, field, old_text, new_text)
                self.dm.update_rescue_record(record["id"], field, new_text)
                label_widget.setText(new_text.split("\n")[0] if new_text else "")
                self._log_edit(record, field, old_text, new_text)
                self.records_changed.emit()

    def _select_row(self, row_widget, record):
        """행 선택/해제"""
        # 이전 선택 해제
        if self._selected_row_widget and self._selected_row_widget is not row_widget:
            self._selected_row_widget.setStyleSheet("""
                QFrame { background: transparent; border-bottom: 1px solid rgba(0, 212, 255, 0.12);
                         border-radius: 0; }
                QFrame:hover { background: rgba(0, 212, 255, 0.04); }
            """)

        if self._selected_record and self._selected_record.get("id") == record.get("id"):
            # 같은 행 다시 클릭 → 선택 해제
            row_widget.setStyleSheet("""
                QFrame { background: transparent; border-bottom: 1px solid rgba(0, 212, 255, 0.12);
                         border-radius: 0; }
                QFrame:hover { background: rgba(0, 212, 255, 0.04); }
            """)
            self._selected_record = None
            self._selected_row_widget = None
            self.delete_btn.setEnabled(False)
        else:
            # 새 행 선택
            row_widget.setStyleSheet("""
                QFrame { background: rgba(0, 212, 255, 0.1); border-bottom: 1px solid rgba(0, 212, 255, 0.12);
                         border-radius: 0; }
            """)
            self._selected_record = record
            self._selected_row_widget = row_widget
            self.delete_btn.setEnabled(True)

    def _create_row_widget(self, record: dict, columns: list, col_widths: list) -> QFrame:
        """테이블 행 위젯 생성"""
        row = QFrame()
        row.setStyleSheet("""
            QFrame { background: transparent; border-bottom: 1px solid rgba(0, 212, 255, 0.12);
                     border-radius: 0; }
            QFrame:hover { background: rgba(0, 212, 255, 0.04); }
        """)
        row.setCursor(Qt.PointingHandCursor)
        row.mousePressEvent = lambda e, r=record, w=row: self._select_row(w, r)
        row_layout = QHBoxLayout(row)
        row_layout.setContentsMargins(8, 2, 8, 2)
        row_layout.setSpacing(0)

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
            "최초/인수당시 상태": ("initial_state", "dialog", None),
            "조치경과": ("treatment", "dialog", None),
            "인계대상": ("transfer_target", "text", None),
            "인수대상": ("transfer_target", "text", None),
        }

        for i, col in enumerate(columns):
            # 세로 구분선 (첫 번째 컬럼 제외)
            if i > 0:
                sep = QFrame()
                sep.setFixedWidth(1)
                sep.setStyleSheet("background: rgba(0, 212, 255, 0.08);")
                row_layout.addWidget(sep)

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
            elif col == "인계/인수":
                text = "-"
                if rec_type == "transfer_out":
                    text = f"→{record.get('transfer_target', '')}"
                elif rec_type == "transfer_in":
                    text = f"←{record.get('transfer_target', '')}"
                elif rec_type == "rescue" and record.get("transferred"):
                    text = f"→{record.get('transfer_target', '')}"
                lbl = QLabel(text)
                lbl.setStyleSheet("color: #ffffff; font-size: 13px; font-weight: bold; background: transparent; border: none;")
                lbl.setAlignment(Qt.AlignCenter)
                lbl.setFixedWidth(w)
                lbl.setFixedHeight(24)
                row_layout.addWidget(lbl)
            elif col in col_config:
                field, edit_type, options = col_config[col]
                display_text = record.get(field, "")
                # 인계대상: 인계되지 않은 구조 기록은 "-"
                if col == "인계대상" and rec_type == "rescue" and not record.get("transferred", False):
                    display_text = "-"
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

        # 이력 버튼 (맨 오른쪽)
        sep = QFrame()
        sep.setFixedWidth(1)
        sep.setStyleSheet("background: rgba(0, 212, 255, 0.08);")
        row_layout.addWidget(sep)
        history_btn = QPushButton("📋")
        history_btn.setFixedSize(30, 24)
        history_btn.setStyleSheet("""
            QPushButton { background: transparent; border: none; font-size: 14px; padding: 0; }
            QPushButton:hover { background: rgba(0,212,255,0.1); border-radius: 3px; }
        """)
        history_btn.setCursor(Qt.PointingHandCursor)
        history_btn.clicked.connect(lambda checked, r=record: self._show_history(r))
        row_layout.addWidget(history_btn)

        return row

    def _show_history(self, record: dict):
        """변경 이력 다이얼로그"""
        name = record.get("name", "미상")
        history = record.get("_history", [])

        dlg = QDialog(self.window())
        dlg.setWindowTitle(f"변경 이력 - {name}")
        dlg.setFixedSize(400, 300)
        dlg.setStyleSheet("""
            QDialog { background: #0d1f3c; border: 2px solid rgba(0,212,255,0.5); border-radius: 8px; }
            QLabel { background: transparent; border: none; color: #c8d6e5; }
        """)
        layout = QVBoxLayout(dlg)
        layout.setSpacing(8)
        layout.setContentsMargins(12, 10, 12, 10)

        title = QLabel(f"{name} - 변경 이력")
        title.setStyleSheet("color: #00d4ff; font-size: 15px; font-weight: bold;")
        layout.addWidget(title)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        content = QWidget()
        cl = QVBoxLayout(content)
        cl.setContentsMargins(0, 0, 0, 0)
        cl.setSpacing(4)

        # 여러 줄 가능한 필드
        multiline_fields = {"treatment", "initial_state"}

        if not history:
            lbl = QLabel("변경 이력이 없습니다.")
            lbl.setStyleSheet("color: #5a7a9a; font-size: 12px;")
            lbl.setAlignment(Qt.AlignCenter)
            cl.addWidget(lbl)
        else:
            for h in history:
                raw_field = h.get("field", "")
                field = self._get_field_display_name(record, raw_field)
                old_val = h.get("old", "")
                new_val = h.get("new", "")
                ts = h.get("time", "")

                if raw_field in multiline_fields:
                    # 여러 줄 필드: 기존/수정 후 박스 표시
                    box = QFrame()
                    box.setStyleSheet("QFrame { background: rgba(0,0,0,0.2); border: 1px solid #1a2d4a; border-radius: 4px; } QLabel { border: none; }")
                    bl = QVBoxLayout(box)
                    bl.setContentsMargins(8, 6, 8, 6)
                    bl.setSpacing(4)

                    ts_lbl = QLabel(f"[{ts}] {field}")
                    ts_lbl.setStyleSheet("color: #00d4ff; font-size: 12px; font-weight: bold;")
                    bl.addWidget(ts_lbl)

                    # 기존
                    old_header = QLabel("기존")
                    old_header.setStyleSheet("color: #5a7a9a; font-size: 11px; font-weight: bold; border-bottom: 1px solid #1a2d4a; padding-bottom: 2px;")
                    bl.addWidget(old_header)
                    old_lbl = QLabel(old_val if old_val else "(빈값)")
                    old_lbl.setStyleSheet("color: #8faabe; font-size: 12px;")
                    old_lbl.setWordWrap(True)
                    bl.addWidget(old_lbl)

                    # 수정 후
                    new_header = QLabel("수정 후")
                    new_header.setStyleSheet("color: #5a7a9a; font-size: 11px; font-weight: bold; border-bottom: 1px solid #1a2d4a; padding-bottom: 2px;")
                    bl.addWidget(new_header)
                    new_lbl = QLabel(new_val if new_val else "(빈값)")
                    new_lbl.setStyleSheet("color: #e0e8f0; font-size: 12px;")
                    new_lbl.setWordWrap(True)
                    bl.addWidget(new_lbl)

                    cl.addWidget(box)
                else:
                    # 한 줄 필드: 시안 헤더 + 회색 기존값 + 밝은 수정값
                    old_display = old_val if old_val else "(빈값)"
                    new_display = new_val if new_val else "(빈값)"
                    entry = QLabel()
                    entry.setTextFormat(Qt.RichText)
                    entry.setText(
                        f'<span style="color:#00d4ff; font-weight:bold;">[{ts}] {field}:</span> '
                        f'<span style="color:#8faabe;">{old_display}</span> '
                        f'<span style="color:#5a7a9a;">→</span> '
                        f'<span style="color:#e0e8f0; font-weight:bold;">{new_display}</span>'
                    )
                    entry.setStyleSheet("font-size: 12px; background: rgba(0,0,0,0.2); border-radius: 3px; padding: 4px;")
                    entry.setWordWrap(True)
                    cl.addWidget(entry)

        cl.addStretch()
        scroll.setWidget(content)
        layout.addWidget(scroll, 1)

        close_btn = QPushButton("닫기")
        close_btn.setFixedSize(60, 28)
        close_btn.clicked.connect(dlg.accept)
        btn_row = QHBoxLayout()
        btn_row.addStretch()
        btn_row.addWidget(close_btn)
        layout.addLayout(btn_row)

        # 스크롤을 맨 아래로
        from PySide6.QtCore import QTimer
        QTimer.singleShot(50, lambda: scroll.verticalScrollBar().setValue(scroll.verticalScrollBar().maximum()))

        dlg.exec()

    def _delete_selected_record(self):
        """선택된 행 삭제 (확인 다이얼로그)"""
        if not self._selected_record:
            return
        record = self._selected_record
        rec_type = record.get("type", "rescue")
        name = record.get("name", "미상")
        gender = record.get("gender", "")
        age = record.get("age", "미상")
        severity = record.get("severity", "")
        timestamp = record.get("timestamp", "")
        state = record.get("initial_state", "")

        sev_color = SEVERITY_COLORS.get(severity, "#8faabe")
        type_label = TYPE_LABELS.get(rec_type, "구조")

        # 확인 다이얼로그
        dlg = QDialog(self.window())
        dlg.setWindowTitle("기록 삭제 확인")
        dlg.setFixedSize(340, 220)
        dlg.setStyleSheet("""
            QDialog { background: #0d1f3c; border: 2px solid #c0392b; border-radius: 8px; }
            QLabel { background: transparent; border: none; color: #c8d6e5; }
        """)
        layout = QVBoxLayout(dlg)
        layout.setSpacing(10)
        layout.setContentsMargins(16, 12, 16, 12)

        # 제목
        title = QLabel("정말 삭제하시겠습니까?")
        title.setStyleSheet("color: #e74c3c; font-size: 16px; font-weight: bold;")
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)

        # 인적사항 정보
        info_frame = QFrame()
        info_frame.setStyleSheet("QFrame { background: rgba(0,0,0,0.3); border: 1px solid #1a2d4a; border-radius: 6px; }")
        info_layout = QGridLayout(info_frame)
        info_layout.setContentsMargins(12, 8, 12, 8)
        info_layout.setSpacing(6)

        info_items = [
            ("유형", type_label), ("일시", timestamp),
            ("이름", name), ("성별/연령", f"{gender} / {age}"),
            ("중증도", severity), ("상태", state),
        ]
        for idx, (label_text, value_text) in enumerate(info_items):
            r, c = idx // 2, (idx % 2) * 2
            lbl = QLabel(label_text)
            lbl.setStyleSheet("color: #5a7a9a; font-size: 12px;")
            info_layout.addWidget(lbl, r, c)
            val = QLabel(value_text)
            if label_text == "중증도":
                val.setStyleSheet(f"color: {sev_color}; font-size: 13px; font-weight: bold;")
            else:
                val.setStyleSheet("color: #ffffff; font-size: 13px; font-weight: bold;")
            info_layout.addWidget(val, r, c + 1)

        layout.addWidget(info_frame)

        # 부가 안내 (인계 기록 동반 삭제 시)
        if rec_type == "rescue" and record.get("transferred", False):
            warn = QLabel("※ 연결된 인계 기록도 함께 삭제됩니다.")
            warn.setStyleSheet("color: #f39c12; font-size: 11px;")
            warn.setAlignment(Qt.AlignCenter)
            layout.addWidget(warn)

        # 버튼
        btn_row = QHBoxLayout()
        btn_row.addStretch()
        cancel_btn = QPushButton("취소")
        cancel_btn.setFixedSize(70, 30)
        cancel_btn.clicked.connect(dlg.reject)
        btn_row.addWidget(cancel_btn)
        confirm_btn = QPushButton("삭제")
        confirm_btn.setFixedSize(70, 30)
        confirm_btn.setStyleSheet("""
            QPushButton { background: #c0392b; color: #ffffff; font-size: 13px; font-weight: bold;
                          border: 1px solid #e74c3c; border-radius: 4px; }
            QPushButton:hover { background: #e74c3c; }
        """)
        confirm_btn.clicked.connect(dlg.accept)
        btn_row.addWidget(confirm_btn)
        layout.addLayout(btn_row)

        if dlg.exec() != QDialog.Accepted:
            return

        # 실제 삭제
        rec_id = record["id"]
        if rec_type == "rescue":
            # 인계된 경우 transfer_out도 삭제
            if record.get("transferred", False):
                for r in list(self.dm.rescue_records):
                    if r.get("source_record_id") == rec_id:
                        self.dm.delete_rescue_record(r["id"])
            self.dm.delete_rescue_record(rec_id)
            self._emit_log(f"[삭제] 구조 기록 - {name}")
        elif rec_type == "transfer_out":
            # 원본 rescue 인계 상태 복원
            source_id = record.get("source_record_id")
            if source_id:
                self.dm.update_rescue_record(source_id, "transferred", False)
                self.dm.update_rescue_record(source_id, "transfer_target", "")
                self.dm.update_rescue_record(source_id, "transfer_timestamp", "")
            self.dm.delete_rescue_record(rec_id)
            self._emit_log(f"[삭제] 인계 기록 - {name}")
        elif rec_type == "transfer_in":
            self.dm.delete_rescue_record(rec_id)
            self._emit_log(f"[삭제] 인수 기록 - {name}")

        self._selected_record = None
        self._selected_row_widget = None
        self.delete_btn.setEnabled(False)
        self._refresh_table()
        self.records_changed.emit()

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

        def names_by_severity(rec_list):
            names = {}
            for s in severities:
                names[s] = [f"{r.get('name', '미상')}({r.get('gender', '')}, {r.get('age', '미상')})"
                            for r in rec_list if r.get("severity") == s]
            return names

        # 현재원: rescue(not transferred) + transfer_in
        current = [r for r in records
                   if (r["type"] == "rescue" and not r.get("transferred", False))
                   or r["type"] == "transfer_in"]
        rescue_only = [r for r in records if r["type"] == "rescue"]
        transfer_out = [r for r in records if r["type"] == "transfer_out"]
        transfer_in = [r for r in records if r["type"] == "transfer_in"]

        def make_data(rec_list):
            return {"total": len(rec_list), "by_severity": count_by_severity(rec_list),
                    "names_by_severity": names_by_severity(rec_list)}

        return {
            "현재원": make_data(current),
            "본함구조": make_data(rescue_only),
            "인계현황": make_data(transfer_out),
            "인수현황": make_data(transfer_in),
        }

    @staticmethod
    def _hex_to_rgb(hex_color: str) -> str:
        """#RRGGBB -> R, G, B"""
        h = hex_color.lstrip("#")
        return f"{int(h[0:2], 16)}, {int(h[2:4], 16)}, {int(h[4:6], 16)}"
