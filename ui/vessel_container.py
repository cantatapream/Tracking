"""
SPT 선박 컨테이너 위젯 - 단정/어선 하나의 독립 컨테이너 + 장비 표시
"""
from PySide6.QtWidgets import (
    QFrame, QVBoxLayout, QHBoxLayout, QLabel, QScrollArea, QWidget, QSizePolicy,
    QLineEdit
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QPainter, QColor, QPen
from ui.personnel_card import PersonnelCard
from core.models import Personnel, Equipment
from typing import List


class EquipmentMiniCard(QFrame):
    """장비 미니 카드 - 대시보드용"""
    clicked = Signal(str, bool)  # equipment_id, ctrl

    def __init__(self, equipment: Equipment, parent=None):
        super().__init__(parent)
        self.equipment = equipment
        self._selected = False
        self.setCursor(Qt.PointingHandCursor)
        self.setFixedHeight(32)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.setObjectName("equipmentMiniCard")
        self._setup_ui()

    def _setup_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(10, 4, 10, 4)
        layout.setSpacing(8)

        icon_label = QLabel("⚙")
        icon_label.setFixedWidth(16)
        icon_label.setStyleSheet("color: #5a7a9a; font-size: 12px; background: transparent; border: none;")
        layout.addWidget(icon_label)

        self.name_label = QLabel(self.equipment.name)
        self.name_label.setObjectName("equipmentMiniName")
        layout.addWidget(self.name_label)
        layout.addStretch()

    @property
    def selected(self) -> bool:
        return self._selected

    @selected.setter
    def selected(self, value: bool):
        self._selected = value
        if value:
            self.setObjectName("equipmentMiniCardSelected")
        else:
            self.setObjectName("equipmentMiniCard")
        self.setStyleSheet(self.styleSheet())

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            ctrl = event.modifiers() & Qt.ControlModifier
            self.clicked.emit(self.equipment.id, bool(ctrl))
        super().mousePressEvent(event)

    def paintEvent(self, event):
        super().paintEvent(event)
        if self._selected:
            painter = QPainter(self)
            painter.setRenderHint(QPainter.Antialiasing)
            glow_pen = QPen(QColor(0, 212, 255, 60), 3)
            painter.setPen(glow_pen)
            painter.setBrush(Qt.NoBrush)
            painter.drawRoundedRect(self.rect().adjusted(1, 1, -1, -1), 4, 4)
            painter.end()


class VesselContainer(QFrame):
    """개별 선박(단정/어선) 컨테이너"""
    header_clicked = Signal(str)  # vessel_id
    card_clicked = Signal(str, bool)  # personnel_id, ctrl
    eq_card_clicked = Signal(str, bool)  # equipment_id, ctrl
    name_changed = Signal(str, str)  # vessel_id, new_name

    def __init__(self, vessel_id: str, vessel_name: str, vessel_type: str, parent=None, hide_header: bool = False):
        super().__init__(parent)
        self.vessel_id = vessel_id
        self.vessel_name = vessel_name
        self.vessel_type = vessel_type  # "base", "patrol", "vessel"
        self._hide_header = hide_header
        self.cards: dict[str, PersonnelCard] = {}
        self.eq_cards: dict[str, EquipmentMiniCard] = {}
        self._eq_header = None
        self._move_target_mode = False
        self._editing_name = False
        self.setCursor(Qt.PointingHandCursor)
        self._setup_ui()

    def _setup_ui(self):
        if self.vessel_type == "patrol":
            self.setObjectName("vesselContainerPatrol")
        elif self.vessel_type == "vessel":
            self.setObjectName("vesselContainerVessel")
        else:
            self.setObjectName("vesselContainer")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(6, 4, 6, 6)
        layout.setSpacing(4)

        # 헤더
        header_layout = QHBoxLayout()
        header_layout.setSpacing(8)

        if self.vessel_type == "patrol":
            header_name = "vesselHeaderPatrol"
            badge_name = "countBadgePatrol"
        elif self.vessel_type == "vessel":
            header_name = "vesselHeaderVessel"
            badge_name = "countBadgeVessel"
        else:
            header_name = "vesselHeader"
            badge_name = "countBadge"

        self.header_label = QLabel(self.vessel_name)
        self.header_label.setObjectName(header_name)
        if self.vessel_type == "base":
            self.header_label.setCursor(Qt.PointingHandCursor)
            self.header_label.mouseDoubleClickEvent = self._start_name_edit
        header_layout.addWidget(self.header_label)

        # 본함 이름 편집 입력
        self.name_input = QLineEdit(self.vessel_name)
        self.name_input.setFixedHeight(26)
        self.name_input.setObjectName("headerTitleInput")
        self.name_input.returnPressed.connect(self._save_name_edit)
        self.name_input.hide()
        header_layout.addWidget(self.name_input)

        header_layout.addStretch()

        self.count_badge = QLabel("0명")
        self.count_badge.setObjectName(badge_name)
        header_layout.addWidget(self.count_badge)

        if self._hide_header:
            # 헤더 위젯들 숨김
            self.header_label.hide()
            self.name_input.hide()
            self.count_badge.hide()
            # 헤더 레이아웃은 추가하되 높이 0
        layout.addLayout(header_layout)

        if self._hide_header:
            # 헤더 영역 높이 최소화
            self.header_label.setFixedHeight(0)
            self.count_badge.setFixedHeight(0)

        # 카드 영역
        self.cards_widget = QWidget()
        self.cards_layout = QVBoxLayout(self.cards_widget)
        self.cards_layout.setContentsMargins(0, 0, 0, 0)
        self.cards_layout.setSpacing(3)
        self.cards_layout.addStretch()

        scroll = QScrollArea()
        scroll.setWidget(self.cards_widget)
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setStyleSheet("background: transparent;")
        layout.addWidget(scroll)

    def set_personnel(self, personnel_list: List[Personnel]):
        """대원 카드 갱신"""
        # 기존 카드 제거
        for card in self.cards.values():
            card.setParent(None)
            card.deleteLater()
        self.cards.clear()

        # 기존 장비 카드도 제거
        for card in self.eq_cards.values():
            card.setParent(None)
            card.deleteLater()
        self.eq_cards.clear()

        if self._eq_header:
            self._eq_header.setParent(None)
            self._eq_header.deleteLater()
            self._eq_header = None

        # 레이아웃 클리어
        while self.cards_layout.count():
            item = self.cards_layout.takeAt(0)
            if item.widget():
                item.widget().setParent(None)

        # 새 카드 추가
        for p in personnel_list:
            card = PersonnelCard(p)
            card.clicked.connect(self._on_card_clicked)
            self.cards[p.id] = card
            self.cards_layout.addWidget(card)

        # stretch는 set_equipment 후에 추가
        self.cards_layout.addStretch()
        self.count_badge.setText(f"{len(personnel_list)}명")

    def set_equipment(self, equipment_list: List[Equipment]):
        """장비 카드 추가 (set_personnel 이후 호출)"""
        # 기존 장비 카드 제거
        for card in self.eq_cards.values():
            card.setParent(None)
            card.deleteLater()
        self.eq_cards.clear()

        if self._eq_header:
            self._eq_header.setParent(None)
            self._eq_header.deleteLater()
            self._eq_header = None

        if not equipment_list:
            return

        # 마지막 stretch 제거
        last_idx = self.cards_layout.count() - 1
        if last_idx >= 0:
            item = self.cards_layout.takeAt(last_idx)

        # 장비 섹션 헤더
        self._eq_header = QLabel("  장비")
        self._eq_header.setObjectName("equipmentSectionHeaderInline")
        self._eq_header.setFixedHeight(22)
        self.cards_layout.addWidget(self._eq_header)

        # 장비 카드 추가
        for eq in equipment_list:
            card = EquipmentMiniCard(eq)
            card.clicked.connect(self._on_eq_card_clicked)
            self.eq_cards[eq.id] = card
            self.cards_layout.addWidget(card)

        # stretch 다시 추가
        self.cards_layout.addStretch()

    def update_timers(self):
        """모든 카드의 타이머 업데이트"""
        for card in self.cards.values():
            card.update_display()

    def set_card_selected(self, pid: str, selected: bool):
        if pid in self.cards:
            self.cards[pid].selected = selected

    def set_eq_card_selected(self, eid: str, selected: bool):
        if eid in self.eq_cards:
            self.eq_cards[eid].selected = selected

    def clear_selection(self):
        for card in self.cards.values():
            card.selected = False
        for card in self.eq_cards.values():
            card.selected = False

    def set_move_target(self, active: bool):
        """이동 대상 모드 표시"""
        self._move_target_mode = active
        if active:
            if self.vessel_type == "patrol":
                self.setObjectName("moveTargetPatrol")
            elif self.vessel_type == "vessel":
                self.setObjectName("moveTargetVessel")
            else:
                self.setObjectName("moveTarget")
        else:
            if self.vessel_type == "patrol":
                self.setObjectName("vesselContainerPatrol")
            elif self.vessel_type == "vessel":
                self.setObjectName("vesselContainerVessel")
            else:
                self.setObjectName("vesselContainer")
        self.setStyleSheet(self.styleSheet())

    def _start_name_edit(self, event=None):
        """본함 이름 편집 시작 (더블클릭)"""
        if self.vessel_type != "base":
            return
        self._editing_name = True
        self.header_label.hide()
        self.name_input.setText(self.vessel_name)
        self.name_input.show()
        self.name_input.setFocus()
        self.name_input.selectAll()

    def _save_name_edit(self):
        """본함 이름 편집 저장"""
        new_name = self.name_input.text().strip()
        if new_name:
            self.vessel_name = new_name
            self.header_label.setText(new_name)
            self.name_changed.emit(self.vessel_id, new_name)
        self.name_input.hide()
        self.header_label.show()
        self._editing_name = False

    def _on_card_clicked(self, pid: str, ctrl: bool):
        self.card_clicked.emit(pid, ctrl)

    def _on_eq_card_clicked(self, eid: str, ctrl: bool):
        self.eq_card_clicked.emit(eid, ctrl)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.header_clicked.emit(self.vessel_id)
        super().mousePressEvent(event)
