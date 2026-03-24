"""
SPT 장비 관리 탭
"""
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton,
    QComboBox, QScrollArea, QFrame, QGridLayout, QMessageBox, QSizePolicy
)
from PySide6.QtCore import Qt, Signal, QTimer
from core.data_manager import DataManager
from core.models import Equipment
from ui.personnel_card import format_time


class EquipmentCard(QFrame):
    """장비 카드"""
    def __init__(self, equipment: Equipment, data_manager: DataManager, parent=None):
        super().__init__(parent)
        self.eq = equipment
        self.dm = data_manager
        self.setMinimumHeight(100)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self._setup_ui()
        self.update_display()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 10, 12, 10)
        layout.setSpacing(6)

        # 상단: 이름 + 카테고리
        top_row = QHBoxLayout()
        self.name_label = QLabel(self.eq.name)
        self.name_label.setObjectName("equipmentName")
        top_row.addWidget(self.name_label)

        self.category_label = QLabel(self.eq.category)
        self.category_label.setObjectName("equipmentCategory")
        top_row.addWidget(self.category_label)
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
        btn_row.setSpacing(6)

        self.toggle_btn = QPushButton("가동 시작")
        self.toggle_btn.setObjectName("btnSuccess")
        self.toggle_btn.setFixedHeight(30)
        self.toggle_btn.clicked.connect(self._toggle_running)
        btn_row.addWidget(self.toggle_btn)

        self.reset_btn = QPushButton("리셋")
        self.reset_btn.setFixedHeight(30)
        self.reset_btn.clicked.connect(self._reset_timer)
        btn_row.addWidget(self.reset_btn)

        self.assign_combo = QComboBox()
        self.assign_combo.setFixedHeight(30)
        self.assign_combo.setMinimumWidth(120)
        self._populate_assignee_combo()
        self.assign_combo.currentIndexChanged.connect(self._on_assignee_changed)
        btn_row.addWidget(self.assign_combo)

        self.delete_btn = QPushButton("삭제")
        self.delete_btn.setObjectName("btnDanger")
        self.delete_btn.setFixedHeight(30)
        self.delete_btn.clicked.connect(self._delete)
        btn_row.addWidget(self.delete_btn)

        layout.addLayout(btn_row)

    def _populate_assignee_combo(self):
        self.assign_combo.blockSignals(True)
        self.assign_combo.clear()
        self.assign_combo.addItem("담당자 선택...", "")
        for p in self.dm.personnel:
            self.assign_combo.addItem(f"{p.name} ({p.rank})", p.id)
        # 현재 담당자 선택
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


class EquipmentTab(QWidget):
    """장비 관리 탭"""
    def __init__(self, data_manager: DataManager, parent=None):
        super().__init__(parent)
        self.dm = data_manager
        self.eq_cards: list[EquipmentCard] = []
        self._setup_ui()
        self._setup_timer()
        self.refresh()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        # 제목
        title = QLabel("장비 등록 및 관리")
        title.setObjectName("sectionTitle")
        title.setFixedHeight(36)
        layout.addWidget(title)

        # 장비 추가 영역
        add_frame = QFrame()
        add_frame.setObjectName("sectionPanel")
        add_layout = QHBoxLayout(add_frame)
        add_layout.setContentsMargins(12, 10, 12, 10)
        add_layout.setSpacing(8)

        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText("장비 이름")
        self.name_input.setFixedHeight(36)
        add_layout.addWidget(self.name_input, 2)

        self.category_combo = QComboBox()
        self.category_combo.setFixedHeight(36)
        self.category_combo.addItems(["엔진", "통신기기", "GPS", "레이더", "기타"])
        self.category_combo.setEditable(True)
        add_layout.addWidget(self.category_combo, 1)

        self.vessel_combo = QComboBox()
        self.vessel_combo.setFixedHeight(36)
        self._populate_vessel_combo()
        add_layout.addWidget(self.vessel_combo, 1)

        add_btn = QPushButton("장비 추가")
        add_btn.setObjectName("btnAccent")
        add_btn.setFixedHeight(36)
        add_btn.clicked.connect(self._add_equipment)
        add_layout.addWidget(add_btn)

        layout.addWidget(add_frame)

        # 장비 목록
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll.setFrameShape(QFrame.NoFrame)

        self.list_widget = QWidget()
        self.list_layout = QVBoxLayout(self.list_widget)
        self.list_layout.setContentsMargins(0, 0, 0, 0)
        self.list_layout.setSpacing(6)
        self.list_layout.addStretch()

        scroll.setWidget(self.list_widget)
        layout.addWidget(scroll)

    def _populate_vessel_combo(self):
        self.vessel_combo.clear()
        self.vessel_combo.addItem("소속 선택...", "")
        for vid, vinfo in sorted(self.dm.vessels.items()):
            self.vessel_combo.addItem(vinfo["name"], vid)

    def _add_equipment(self):
        name = self.name_input.text().strip()
        if not name:
            return
        category = self.category_combo.currentText()
        vessel_id = self.vessel_combo.currentData() or ""
        self.dm.add_equipment(name, category, vessel_id)
        self.name_input.clear()
        self.refresh()

    def refresh(self):
        """장비 목록 새로고침"""
        # 기존 카드 제거
        for card in self.eq_cards:
            card.setParent(None)
            card.deleteLater()
        self.eq_cards.clear()

        while self.list_layout.count():
            item = self.list_layout.takeAt(0)
            if item.widget():
                item.widget().setParent(None)

        for eq in self.dm.equipment:
            card = EquipmentCard(eq, self.dm)
            self.eq_cards.append(card)
            self.list_layout.addWidget(card)

        self.list_layout.addStretch()
        self._populate_vessel_combo()

    def _setup_timer(self):
        self.timer = QTimer(self)
        self.timer.timeout.connect(self._tick)
        self.timer.start(1000)

    def _tick(self):
        for card in self.eq_cards:
            card.update_display()
