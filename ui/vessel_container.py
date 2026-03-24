"""
SPT 선박 컨테이너 위젯 - 단정/어선 하나의 독립 컨테이너
"""
from PySide6.QtWidgets import (
    QFrame, QVBoxLayout, QHBoxLayout, QLabel, QScrollArea, QWidget, QSizePolicy
)
from PySide6.QtCore import Qt, Signal
from ui.personnel_card import PersonnelCard
from core.models import Personnel
from typing import List


class VesselContainer(QFrame):
    """개별 선박(단정/어선) 컨테이너"""
    header_clicked = Signal(str)  # vessel_id
    card_clicked = Signal(str, bool)  # personnel_id, ctrl

    def __init__(self, vessel_id: str, vessel_name: str, vessel_type: str, parent=None):
        super().__init__(parent)
        self.vessel_id = vessel_id
        self.vessel_name = vessel_name
        self.vessel_type = vessel_type  # "base", "patrol", "vessel"
        self.cards: dict[str, PersonnelCard] = {}
        self._move_target_mode = False
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
        header_layout.addWidget(self.header_label)

        header_layout.addStretch()

        self.count_badge = QLabel("0명")
        self.count_badge.setObjectName(badge_name)
        header_layout.addWidget(self.count_badge)

        layout.addLayout(header_layout)

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

        # stretch 제거
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

        self.cards_layout.addStretch()
        self.count_badge.setText(f"{len(personnel_list)}명")

    def update_timers(self):
        """모든 카드의 타이머 업데이트"""
        for card in self.cards.values():
            card.update_display()

    def set_card_selected(self, pid: str, selected: bool):
        if pid in self.cards:
            self.cards[pid].selected = selected

    def clear_selection(self):
        for card in self.cards.values():
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

    def _on_card_clicked(self, pid: str, ctrl: bool):
        self.card_clicked.emit(pid, ctrl)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.header_clicked.emit(self.vessel_id)
        super().mousePressEvent(event)
