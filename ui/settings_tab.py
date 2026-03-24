"""
SPT 설정 탭 - 인원 관리 + 선박 관리(좌: 단정, 우: 중국어선) + 장비 관리
"""
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton,
    QComboBox, QScrollArea, QFrame, QSizePolicy
)
from PySide6.QtCore import Qt, Signal, QTimer
from core.data_manager import DataManager
from core.models import Equipment
from ui.personnel_card import format_time


# ============================================================
# 인원 편집 카드
# ============================================================
class PersonnelEditCard(QFrame):
    """인원 편집 카드 - 수정/삭제 지원"""
    removed = Signal(str)
    updated = Signal(str, str, str)  # pid, name, rank

    def __init__(self, pid: str, name: str, rank: str, parent=None):
        super().__init__(parent)
        self.pid = pid
        self._name = name
        self._rank = rank
        self._editing = False
        self.setObjectName("personnelCard")
        self.setFixedHeight(44)
        self._setup_ui()

    def _setup_ui(self):
        self.layout_main = QHBoxLayout(self)
        self.layout_main.setContentsMargins(10, 4, 10, 4)
        self.layout_main.setSpacing(8)

        # 일반 모드 위젯
        self.id_label = QLabel(self.pid)
        self.id_label.setObjectName("cardRank")
        self.id_label.setFixedWidth(50)
        self.layout_main.addWidget(self.id_label)

        self.name_label = QLabel(self._name)
        self.name_label.setObjectName("cardName")
        self.layout_main.addWidget(self.name_label)

        self.rank_label = QLabel(self._rank)
        self.rank_label.setObjectName("cardRank")
        self.layout_main.addWidget(self.rank_label)

        self.layout_main.addStretch()

        # 수정 모드 위젯 (숨김)
        self.name_input = QLineEdit(self._name)
        self.name_input.setFixedHeight(28)
        self.name_input.setFixedWidth(80)
        self.name_input.hide()
        self.layout_main.addWidget(self.name_input)

        self.rank_combo = QComboBox()
        self.rank_combo.setFixedHeight(28)
        self.rank_combo.addItems([
            "경정", "경감", "경위", "경장", "순경", "상사", "중사", "하사",
            "소위", "중위", "대위", "소령", "중령"
        ])
        self.rank_combo.setEditable(True)
        self.rank_combo.setCurrentText(self._rank)
        self.rank_combo.hide()
        self.layout_main.addWidget(self.rank_combo)

        # 버튼: 수정 / 삭제
        self.edit_btn = QPushButton("수정")
        self.edit_btn.setFixedSize(50, 28)
        self.edit_btn.clicked.connect(self._toggle_edit)
        self.layout_main.addWidget(self.edit_btn)

        self.save_btn = QPushButton("저장")
        self.save_btn.setObjectName("btnAccent")
        self.save_btn.setFixedSize(50, 28)
        self.save_btn.clicked.connect(self._save_edit)
        self.save_btn.hide()
        self.layout_main.addWidget(self.save_btn)

        self.cancel_btn = QPushButton("취소")
        self.cancel_btn.setFixedSize(50, 28)
        self.cancel_btn.clicked.connect(self._cancel_edit)
        self.cancel_btn.hide()
        self.layout_main.addWidget(self.cancel_btn)

        del_btn = QPushButton("삭제")
        del_btn.setObjectName("btnDanger")
        del_btn.setFixedSize(50, 28)
        del_btn.clicked.connect(lambda: self.removed.emit(self.pid))
        self.layout_main.addWidget(del_btn)

    def _toggle_edit(self):
        self._editing = True
        self.name_label.hide()
        self.rank_label.hide()
        self.edit_btn.hide()
        self.name_input.setText(self._name)
        self.rank_combo.setCurrentText(self._rank)
        self.name_input.show()
        self.rank_combo.show()
        self.save_btn.show()
        self.cancel_btn.show()
        self.name_input.setFocus()

    def _save_edit(self):
        new_name = self.name_input.text().strip()
        new_rank = self.rank_combo.currentText().strip()
        if new_name:
            self._name = new_name
            self._rank = new_rank
            self.name_label.setText(new_name)
            self.rank_label.setText(new_rank)
            self.updated.emit(self.pid, new_name, new_rank)
        self._cancel_edit()

    def _cancel_edit(self):
        self._editing = False
        self.name_input.hide()
        self.rank_combo.hide()
        self.save_btn.hide()
        self.cancel_btn.hide()
        self.name_label.show()
        self.rank_label.show()
        self.edit_btn.show()


# ============================================================
# 장비 카드 (간소화)
# ============================================================
class EquipmentCard(QFrame):
    """장비 카드 - 간소화"""
    def __init__(self, equipment: Equipment, data_manager: DataManager, parent=None):
        super().__init__(parent)
        self.eq = equipment
        self.dm = data_manager
        self.setMinimumHeight(80)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self._setup_ui()
        self.update_display()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 8, 10, 8)
        layout.setSpacing(4)

        # 상단: 이름 + 타이머
        top_row = QHBoxLayout()
        self.name_label = QLabel(self.eq.name)
        self.name_label.setObjectName("equipmentName")
        top_row.addWidget(self.name_label)
        top_row.addStretch()

        self.timer_label = QLabel("00:00:00")
        self.timer_label.setObjectName("equipmentTimer")
        top_row.addWidget(self.timer_label)
        layout.addLayout(top_row)

        # 중간: 담당자 정보
        self.assignee_label = QLabel("담당자: 미지정")
        self.assignee_label.setObjectName("equipmentCategory")
        layout.addWidget(self.assignee_label)

        # 하단: 버튼들
        btn_row = QHBoxLayout()
        btn_row.setSpacing(4)

        self.toggle_btn = QPushButton("가동 시작")
        self.toggle_btn.setObjectName("btnSuccess")
        self.toggle_btn.setFixedHeight(28)
        self.toggle_btn.clicked.connect(self._toggle_running)
        btn_row.addWidget(self.toggle_btn)

        self.reset_btn = QPushButton("리셋")
        self.reset_btn.setFixedHeight(28)
        self.reset_btn.clicked.connect(self._reset_timer)
        btn_row.addWidget(self.reset_btn)

        self.assign_combo = QComboBox()
        self.assign_combo.setFixedHeight(28)
        self.assign_combo.setMinimumWidth(100)
        self._populate_assignee_combo()
        self.assign_combo.currentIndexChanged.connect(self._on_assignee_changed)
        btn_row.addWidget(self.assign_combo)

        self.delete_btn = QPushButton("삭제")
        self.delete_btn.setObjectName("btnDanger")
        self.delete_btn.setFixedHeight(28)
        self.delete_btn.clicked.connect(self._delete)
        btn_row.addWidget(self.delete_btn)

        layout.addLayout(btn_row)

    def _populate_assignee_combo(self):
        self.assign_combo.blockSignals(True)
        self.assign_combo.clear()
        self.assign_combo.addItem("담당자 없음", "")
        for p in self.dm.personnel:
            self.assign_combo.addItem(f"{p.name} ({p.rank})", p.id)
        if self.eq.assignee_id:
            for i in range(self.assign_combo.count()):
                if self.assign_combo.itemData(i) == self.eq.assignee_id:
                    self.assign_combo.setCurrentIndex(i)
                    break
        self.assign_combo.blockSignals(False)

    def update_display(self):
        elapsed = self.eq.get_run_elapsed()
        self.timer_label.setText(format_time(elapsed))

        if self.eq.is_running:
            self.setObjectName("equipmentRunning")
            self.toggle_btn.setText("가동 중지")
            self.toggle_btn.setObjectName("btnDanger")
        else:
            self.setObjectName("equipmentCard")
            self.toggle_btn.setText("가동 시작")
            self.toggle_btn.setObjectName("btnSuccess")

        if self.eq.assignee_id:
            person = self.dm.get_personnel_by_id(self.eq.assignee_id)
            if person:
                self.assignee_label.setText(f"담당자: {person.name} ({person.rank})")
            else:
                self.assignee_label.setText("담당자: 미지정")
        else:
            self.assignee_label.setText("담당자: 미지정")

        self.setStyleSheet(self.styleSheet())
        self.toggle_btn.setStyleSheet(self.toggle_btn.styleSheet())

    def _toggle_running(self):
        if self.eq.is_running:
            self.eq.stop()
            self.dm.add_log(f"장비 '{self.eq.name}' 가동 중지 (누적: {format_time(self.eq.total_run_seconds)})")
        else:
            self.eq.start()
            self.dm.add_log(f"장비 '{self.eq.name}' 가동 시작")
        self.dm.save()
        self.update_display()

    def _reset_timer(self):
        self.eq.reset_timer()
        self.dm.add_log(f"장비 '{self.eq.name}' 타이머 리셋")
        self.dm.save()
        self.update_display()

    def _on_assignee_changed(self, index):
        pid = self.assign_combo.itemData(index)
        self.dm.assign_equipment(self.eq.id, pid if pid else None)
        self.update_display()

    def _delete(self):
        self.dm.remove_equipment(self.eq.id)
        self.dm.add_log(f"장비 '{self.eq.name}' 삭제")
        self.setParent(None)
        self.deleteLater()


# ============================================================
# 설정 탭 (통합: 인원관리 + 선박관리 + 장비관리)
# ============================================================
class SettingsTab(QWidget):
    """설정 탭 - 인원 관리 + 선박 관리(좌우 분할) + 장비 관리"""
    data_changed = Signal()

    def __init__(self, data_manager: DataManager, parent=None):
        super().__init__(parent)
        self.dm = data_manager
        self.eq_cards: list[EquipmentCard] = []
        self._setup_ui()
        self._setup_timer()
        self.refresh()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(8)

        # ===== 섹션 1: 인원 관리 =====
        personnel_title = QLabel("인원 관리")
        personnel_title.setObjectName("sectionTitle")
        personnel_title.setFixedHeight(32)
        layout.addWidget(personnel_title)

        add_frame = QFrame()
        add_frame.setObjectName("sectionPanel")
        add_layout = QHBoxLayout(add_frame)
        add_layout.setContentsMargins(10, 8, 10, 8)
        add_layout.setSpacing(6)

        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText("이름")
        self.name_input.setFixedHeight(32)
        add_layout.addWidget(self.name_input, 2)

        self.rank_combo = QComboBox()
        self.rank_combo.setFixedHeight(32)
        self.rank_combo.addItems([
            "경정", "경감", "경위", "경장", "순경", "상사", "중사", "하사",
            "소위", "중위", "대위", "소령", "중령"
        ])
        self.rank_combo.setEditable(True)
        add_layout.addWidget(self.rank_combo, 1)

        add_btn = QPushButton("인원 추가")
        add_btn.setObjectName("btnAccent")
        add_btn.setFixedHeight(32)
        add_btn.clicked.connect(self._add_personnel)
        add_layout.addWidget(add_btn)

        layout.addWidget(add_frame)

        # 인원 목록 스크롤
        self.personnel_scroll = QScrollArea()
        self.personnel_scroll.setWidgetResizable(True)
        self.personnel_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.personnel_scroll.setFrameShape(QFrame.NoFrame)

        self.personnel_list_widget = QWidget()
        self.personnel_list_layout = QVBoxLayout(self.personnel_list_widget)
        self.personnel_list_layout.setContentsMargins(0, 0, 0, 0)
        self.personnel_list_layout.setSpacing(3)
        self.personnel_list_layout.addStretch()

        self.personnel_scroll.setWidget(self.personnel_list_widget)
        layout.addWidget(self.personnel_scroll, 2)

        # ===== 섹션 2: 선박 관리 (좌: 단정, 우: 중국어선) =====
        vessel_title = QLabel("선박 관리")
        vessel_title.setObjectName("sectionTitle")
        vessel_title.setFixedHeight(32)
        layout.addWidget(vessel_title)

        vessel_container = QFrame()
        vessel_container.setObjectName("sectionPanel")
        vessel_main_layout = QHBoxLayout(vessel_container)
        vessel_main_layout.setContentsMargins(8, 8, 8, 8)
        vessel_main_layout.setSpacing(8)

        # 좌측: 단정
        patrol_frame = QFrame()
        patrol_layout = QVBoxLayout(patrol_frame)
        patrol_layout.setContentsMargins(0, 0, 0, 0)
        patrol_layout.setSpacing(4)

        patrol_header = QLabel("단정")
        patrol_header.setObjectName("sectionTitlePatrol")
        patrol_header.setFixedHeight(28)
        patrol_layout.addWidget(patrol_header)

        patrol_add_row = QHBoxLayout()
        self.patrol_name_input = QLineEdit()
        self.patrol_name_input.setPlaceholderText("단정 이름 (예: 단정 5호)")
        self.patrol_name_input.setFixedHeight(30)
        patrol_add_row.addWidget(self.patrol_name_input)

        patrol_add_btn = QPushButton("추가")
        patrol_add_btn.setObjectName("btnAccent")
        patrol_add_btn.setFixedHeight(30)
        patrol_add_btn.setFixedWidth(50)
        patrol_add_btn.clicked.connect(lambda: self._add_vessel_type("patrol"))
        patrol_add_row.addWidget(patrol_add_btn)
        patrol_layout.addLayout(patrol_add_row)

        # 단정 목록 스크롤
        patrol_scroll = QScrollArea()
        patrol_scroll.setWidgetResizable(True)
        patrol_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        patrol_scroll.setFrameShape(QFrame.NoFrame)

        self.patrol_list_widget = QWidget()
        self.patrol_list_layout = QVBoxLayout(self.patrol_list_widget)
        self.patrol_list_layout.setContentsMargins(0, 0, 0, 0)
        self.patrol_list_layout.setSpacing(3)
        self.patrol_list_layout.addStretch()

        patrol_scroll.setWidget(self.patrol_list_widget)
        patrol_layout.addWidget(patrol_scroll, 1)
        vessel_main_layout.addWidget(patrol_frame, 1)

        # 우측: 중국어선
        vessel_frame = QFrame()
        vessel_layout_inner = QVBoxLayout(vessel_frame)
        vessel_layout_inner.setContentsMargins(0, 0, 0, 0)
        vessel_layout_inner.setSpacing(4)

        vessel_header = QLabel("중국어선")
        vessel_header.setObjectName("sectionTitleVessel")
        vessel_header.setFixedHeight(28)
        vessel_layout_inner.addWidget(vessel_header)

        vessel_add_row = QHBoxLayout()
        self.vessel_name_input = QLineEdit()
        self.vessel_name_input.setPlaceholderText("어선 이름 (예: 중국어선 C)")
        self.vessel_name_input.setFixedHeight(30)
        vessel_add_row.addWidget(self.vessel_name_input)

        vessel_add_btn = QPushButton("추가")
        vessel_add_btn.setObjectName("btnAccent")
        vessel_add_btn.setFixedHeight(30)
        vessel_add_btn.setFixedWidth(50)
        vessel_add_btn.clicked.connect(lambda: self._add_vessel_type("vessel"))
        vessel_add_row.addWidget(vessel_add_btn)
        vessel_layout_inner.addLayout(vessel_add_row)

        # 중국어선 목록 스크롤
        vessel_scroll = QScrollArea()
        vessel_scroll.setWidgetResizable(True)
        vessel_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        vessel_scroll.setFrameShape(QFrame.NoFrame)

        self.vessel_list_widget = QWidget()
        self.vessel_list_layout = QVBoxLayout(self.vessel_list_widget)
        self.vessel_list_layout.setContentsMargins(0, 0, 0, 0)
        self.vessel_list_layout.setSpacing(3)
        self.vessel_list_layout.addStretch()

        vessel_scroll.setWidget(self.vessel_list_widget)
        vessel_layout_inner.addWidget(vessel_scroll, 1)
        vessel_main_layout.addWidget(vessel_frame, 1)

        layout.addWidget(vessel_container, 2)

        # ===== 섹션 3: 장비 관리 =====
        equip_title = QLabel("장비 등록 및 관리")
        equip_title.setObjectName("sectionTitle")
        equip_title.setFixedHeight(32)
        layout.addWidget(equip_title)

        eq_add_frame = QFrame()
        eq_add_frame.setObjectName("sectionPanel")
        eq_add_layout = QHBoxLayout(eq_add_frame)
        eq_add_layout.setContentsMargins(10, 8, 10, 8)
        eq_add_layout.setSpacing(6)

        self.eq_name_input = QLineEdit()
        self.eq_name_input.setPlaceholderText("장비 이름")
        self.eq_name_input.setFixedHeight(32)
        eq_add_layout.addWidget(self.eq_name_input, 2)

        self.eq_assignee_combo = QComboBox()
        self.eq_assignee_combo.setFixedHeight(32)
        eq_add_layout.addWidget(self.eq_assignee_combo, 1)

        eq_add_btn = QPushButton("장비 추가")
        eq_add_btn.setObjectName("btnAccent")
        eq_add_btn.setFixedHeight(32)
        eq_add_btn.clicked.connect(self._add_equipment)
        eq_add_layout.addWidget(eq_add_btn)

        layout.addWidget(eq_add_frame)

        # 장비 목록 스크롤
        self.eq_scroll = QScrollArea()
        self.eq_scroll.setWidgetResizable(True)
        self.eq_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.eq_scroll.setFrameShape(QFrame.NoFrame)

        self.eq_list_widget = QWidget()
        self.eq_list_layout = QVBoxLayout(self.eq_list_widget)
        self.eq_list_layout.setContentsMargins(0, 0, 0, 0)
        self.eq_list_layout.setSpacing(4)
        self.eq_list_layout.addStretch()

        self.eq_scroll.setWidget(self.eq_list_widget)
        layout.addWidget(self.eq_scroll, 2)

    def _setup_timer(self):
        self.timer = QTimer(self)
        self.timer.timeout.connect(self._tick)
        self.timer.start(1000)

    def _tick(self):
        for card in self.eq_cards:
            card.update_display()

    # ---- 인원 관리 ----
    def _add_personnel(self):
        name = self.name_input.text().strip()
        if not name:
            return
        rank = self.rank_combo.currentText()
        self.dm.add_personnel(name, rank)
        self.name_input.clear()
        self.refresh()
        self.data_changed.emit()

    def _remove_personnel(self, pid: str):
        self.dm.remove_personnel(pid)
        self.refresh()
        self.data_changed.emit()

    def _update_personnel(self, pid: str, name: str, rank: str):
        self.dm.update_personnel(pid, name, rank)
        self.data_changed.emit()

    # ---- 선박 관리 ----
    def _add_vessel_type(self, vtype: str):
        if vtype == "patrol":
            name = self.patrol_name_input.text().strip()
            if not name:
                return
            self.patrol_name_input.clear()
        else:
            name = self.vessel_name_input.text().strip()
            if not name:
                return
            self.vessel_name_input.clear()

        prefix = "patrol_" if vtype == "patrol" else "vessel_"
        suffix = name.upper().replace(" ", "-").replace("(", "").replace(")", "")
        vid = f"{prefix}{suffix}"
        counter = 1
        base_vid = vid
        while vid in self.dm.vessels:
            vid = f"{base_vid}-{counter}"
            counter += 1

        self.dm.add_vessel(vid, name, vtype)
        self.refresh()
        self.data_changed.emit()

    def _remove_vessel(self, vid: str):
        self.dm.remove_vessel(vid)
        self.refresh()
        self.data_changed.emit()

    # ---- 장비 관리 ----
    def _add_equipment(self):
        name = self.eq_name_input.text().strip()
        if not name:
            return
        assignee_id = self.eq_assignee_combo.currentData() or ""
        eq = self.dm.add_equipment(name)
        if assignee_id:
            self.dm.assign_equipment(eq.id, assignee_id)
        self.eq_name_input.clear()
        self.refresh()

    def _populate_eq_assignee_combo(self):
        self.eq_assignee_combo.blockSignals(True)
        self.eq_assignee_combo.clear()
        self.eq_assignee_combo.addItem("담당자 없음", "")
        for p in self.dm.personnel:
            self.eq_assignee_combo.addItem(f"{p.name} ({p.rank})", p.id)
        self.eq_assignee_combo.blockSignals(False)

    # ---- 새로고침 ----
    def refresh(self):
        # 인원 목록 갱신
        while self.personnel_list_layout.count():
            item = self.personnel_list_layout.takeAt(0)
            if item.widget():
                item.widget().setParent(None)
                item.widget().deleteLater()

        for p in self.dm.personnel:
            card = PersonnelEditCard(p.id, p.name, p.rank)
            card.removed.connect(self._remove_personnel)
            card.updated.connect(self._update_personnel)
            self.personnel_list_layout.addWidget(card)
        self.personnel_list_layout.addStretch()

        # 단정 목록 갱신
        while self.patrol_list_layout.count():
            item = self.patrol_list_layout.takeAt(0)
            if item.widget():
                item.widget().setParent(None)
                item.widget().deleteLater()

        for vid, vinfo in sorted(self.dm.vessels.items()):
            if vinfo["type"] == "patrol":
                row = self._create_vessel_row(vid, vinfo)
                self.patrol_list_layout.addWidget(row)
        self.patrol_list_layout.addStretch()

        # 중국어선 목록 갱신
        while self.vessel_list_layout.count():
            item = self.vessel_list_layout.takeAt(0)
            if item.widget():
                item.widget().setParent(None)
                item.widget().deleteLater()

        for vid, vinfo in sorted(self.dm.vessels.items()):
            if vinfo["type"] == "vessel":
                row = self._create_vessel_row(vid, vinfo)
                self.vessel_list_layout.addWidget(row)
        self.vessel_list_layout.addStretch()

        # 장비 목록 갱신
        for card in self.eq_cards:
            card.setParent(None)
            card.deleteLater()
        self.eq_cards.clear()

        while self.eq_list_layout.count():
            item = self.eq_list_layout.takeAt(0)
            if item.widget():
                item.widget().setParent(None)

        for eq in self.dm.equipment:
            card = EquipmentCard(eq, self.dm)
            self.eq_cards.append(card)
            self.eq_list_layout.addWidget(card)
        self.eq_list_layout.addStretch()

        # 장비 담당자 콤보 갱신
        self._populate_eq_assignee_combo()

    def _create_vessel_row(self, vid: str, vinfo: dict) -> QFrame:
        """선박 한 줄 위젯"""
        row = QFrame()
        row.setObjectName("personnelCard")
        row.setFixedHeight(40)
        row_layout = QHBoxLayout(row)
        row_layout.setContentsMargins(8, 4, 8, 4)
        row_layout.setSpacing(6)

        name_label = QLabel(vinfo["name"])
        name_label.setObjectName("cardName")
        row_layout.addWidget(name_label)

        row_layout.addStretch()

        count = len(self.dm.get_personnel_at(vid))
        count_label = QLabel(f"{count}명")
        count_label.setObjectName("cardRank")
        row_layout.addWidget(count_label)

        del_btn = QPushButton("삭제")
        del_btn.setObjectName("btnDanger")
        del_btn.setFixedSize(50, 24)
        del_btn.clicked.connect(lambda checked, v=vid: self._remove_vessel(v))
        row_layout.addWidget(del_btn)

        return row
