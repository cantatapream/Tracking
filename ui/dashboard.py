"""
SPT 메인 대시보드 - 3단 컬럼 (본함 / 단정 / 어선) + 장비 이동
"""
from PySide6.QtWidgets import (
    QWidget, QHBoxLayout, QVBoxLayout, QLabel, QScrollArea, QFrame,
    QSizePolicy, QSplitter
)
from PySide6.QtCore import Qt, Signal, QTimer
from ui.vessel_container import VesselContainer, EquipmentMiniCard
from core.data_manager import DataManager
from typing import List, Set


class DashboardView(QWidget):
    """3단 컬럼 대시보드"""
    log_message = Signal(str)

    def __init__(self, data_manager: DataManager, parent=None):
        super().__init__(parent)
        self.dm = data_manager
        self.selected_ids: Set[str] = set()
        self.selected_eq_ids: Set[str] = set()
        self.containers: dict[str, VesselContainer] = {}
        self.base_eq_cards: dict[str, EquipmentMiniCard] = {}
        self._setup_ui()
        self._setup_timer()
        self.refresh()

    def _setup_ui(self):
        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(8, 8, 8, 8)
        main_layout.setSpacing(8)

        # === 좌측: 본함 (인원 3/4 + 장비 1/4) ===
        self.base_panel = self._create_base_section()
        main_layout.addWidget(self.base_panel, 1)

        # === 중앙: 단정 ===
        self.patrol_panel = self._create_section_multi(
            "단정 운영 상태 (PATROL BOATS)", "sectionTitlePatrol", "patrol"
        )
        main_layout.addWidget(self.patrol_panel, 1)

        # === 우측: 어선 ===
        self.vessel_panel = self._create_section_multi(
            "승선 확인 선박 (BOARDED VESSELS)", "sectionTitleVessel", "vessel"
        )
        main_layout.addWidget(self.vessel_panel, 1)

    def _create_base_section(self) -> QFrame:
        """본함 섹션: 인원(상) + 장비(하) 분리"""
        panel = QFrame()
        panel.setObjectName("sectionPanel")
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # 제목
        title_label = QLabel("  본함 (BASE SHIP)")
        title_label.setObjectName("sectionTitle")
        title_label.setFixedHeight(36)
        layout.addWidget(title_label)

        # 인원 컨테이너 (3/4)
        container = VesselContainer("base", "본함 (KCG 3012)", "base")
        container.header_clicked.connect(self._on_container_clicked)
        container.card_clicked.connect(self._on_card_clicked)
        container.eq_card_clicked.connect(self._on_eq_card_clicked)
        self.containers["base"] = container
        layout.addWidget(container, 3)

        # 장비 영역 (1/4, 고정)
        eq_frame = QFrame()
        eq_frame.setObjectName("vesselContainer")
        eq_layout = QVBoxLayout(eq_frame)
        eq_layout.setContentsMargins(6, 4, 6, 6)
        eq_layout.setSpacing(3)

        eq_header = QLabel("  장비 (EQUIPMENT)")
        eq_header.setObjectName("equipmentSectionHeader")
        eq_header.setFixedHeight(24)
        eq_layout.addWidget(eq_header)

        eq_scroll = QScrollArea()
        eq_scroll.setWidgetResizable(True)
        eq_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        eq_scroll.setFrameShape(QFrame.NoFrame)
        eq_scroll.setStyleSheet("background: transparent;")

        self.base_eq_widget = QWidget()
        self.base_eq_layout = QVBoxLayout(self.base_eq_widget)
        self.base_eq_layout.setContentsMargins(0, 0, 0, 0)
        self.base_eq_layout.setSpacing(2)
        self.base_eq_layout.addStretch()

        eq_scroll.setWidget(self.base_eq_widget)
        eq_layout.addWidget(eq_scroll)

        layout.addWidget(eq_frame, 1)

        return panel

    def _create_section_multi(self, title: str, title_style: str, section_type: str) -> QFrame:
        """단정/어선용 다중 컨테이너 섹션"""
        panel = QFrame()
        panel.setObjectName("sectionPanel")
        panel_layout = QVBoxLayout(panel)
        panel_layout.setContentsMargins(0, 0, 0, 0)
        panel_layout.setSpacing(0)

        title_label = QLabel(f"  {title}")
        title_label.setObjectName(title_style)
        title_label.setFixedHeight(36)
        panel_layout.addWidget(title_label)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll.setFrameShape(QFrame.NoFrame)

        self._scroll_widgets = getattr(self, '_scroll_widgets', {})
        scroll_widget = QWidget()
        scroll_layout = QVBoxLayout(scroll_widget)
        scroll_layout.setContentsMargins(4, 4, 4, 4)
        scroll_layout.setSpacing(6)
        scroll_layout.addStretch()

        self._scroll_widgets[section_type] = (scroll_widget, scroll_layout)
        scroll.setWidget(scroll_widget)
        panel_layout.addWidget(scroll)

        return panel

    def rebuild_containers(self):
        """선박 목록 변경 시 컨테이너 재구성"""
        for vid in list(self.containers.keys()):
            if vid != "base":
                c = self.containers.pop(vid)
                c.setParent(None)
                c.hide()

        if "patrol" in self._scroll_widgets:
            widget, layout = self._scroll_widgets["patrol"]
            while layout.count():
                item = layout.takeAt(0)
                w = item.widget()
                if w:
                    w.setParent(None); w.hide()

            for vid, vinfo in sorted(self.dm.vessels.items()):
                if vinfo["type"] == "patrol":
                    c = VesselContainer(vid, vinfo["name"], "patrol")
                    c.header_clicked.connect(self._on_container_clicked)
                    c.card_clicked.connect(self._on_card_clicked)
                    c.eq_card_clicked.connect(self._on_eq_card_clicked)
                    self.containers[vid] = c
                    layout.addWidget(c)
            layout.addStretch()

        if "vessel" in self._scroll_widgets:
            widget, layout = self._scroll_widgets["vessel"]
            while layout.count():
                item = layout.takeAt(0)
                w = item.widget()
                if w:
                    w.setParent(None); w.hide()

            for vid, vinfo in sorted(self.dm.vessels.items()):
                if vinfo["type"] == "vessel":
                    c = VesselContainer(vid, vinfo["name"], "vessel")
                    c.header_clicked.connect(self._on_container_clicked)
                    c.card_clicked.connect(self._on_card_clicked)
                    c.eq_card_clicked.connect(self._on_eq_card_clicked)
                    self.containers[vid] = c
                    layout.addWidget(c)
            layout.addStretch()

    def _refresh_base_equipment(self):
        """본함 장비 영역 갱신"""
        for card in self.base_eq_cards.values():
            card.setParent(None)
        self.base_eq_cards.clear()

        while self.base_eq_layout.count():
            item = self.base_eq_layout.takeAt(0)
            w = item.widget()
            if w:
                w.setParent(None)

        equipment = self.dm.get_equipment_at("base")
        for eq in equipment:
            card = EquipmentMiniCard(eq)
            card.clicked.connect(self._on_eq_card_clicked)
            self.base_eq_cards[eq.id] = card
            self.base_eq_layout.addWidget(card)
        self.base_eq_layout.addStretch()

    def refresh(self):
        """전체 데이터 새로고침"""
        self.rebuild_containers()
        for vid, container in self.containers.items():
            personnel = self.dm.get_personnel_at(vid)
            container.set_personnel(personnel)

            # 단정/어선에만 장비 인라인 표시 (본함은 별도 영역)
            if vid != "base":
                equipment = self.dm.get_equipment_at(vid)
                container.set_equipment(equipment)

            container.update_timers()
            for pid in self.selected_ids:
                container.set_card_selected(pid, True)

        # 본함 장비 영역
        self._refresh_base_equipment()
        for eid in self.selected_eq_ids:
            if eid in self.base_eq_cards:
                self.base_eq_cards[eid].selected = True
            for container in self.containers.values():
                container.set_eq_card_selected(eid, True)

    def _setup_timer(self):
        self.update_timer = QTimer(self)
        self.update_timer.timeout.connect(self._tick)
        self.update_timer.start(1000)

    def _tick(self):
        for container in self.containers.values():
            container.update_timers()

    def _on_card_clicked(self, pid: str, ctrl: bool):
        if pid in self.selected_ids:
            self.selected_ids.discard(pid)
            self._set_card_selected(pid, False)
        else:
            self.selected_ids.add(pid)
            self._set_card_selected(pid, True)
        self._update_move_targets()

    def _on_eq_card_clicked(self, eid: str, ctrl: bool):
        if eid in self.selected_eq_ids:
            self.selected_eq_ids.discard(eid)
            self._set_eq_card_selected(eid, False)
        else:
            self.selected_eq_ids.add(eid)
            self._set_eq_card_selected(eid, True)
        self._update_move_targets()

    def _on_container_clicked(self, vessel_id: str):
        if not self.selected_ids and not self.selected_eq_ids:
            return
        msgs = []
        if self.selected_ids:
            msg = self.dm.move_personnel_batch(list(self.selected_ids), vessel_id)
            if msg: msgs.append(msg)
        if self.selected_eq_ids:
            msg = self.dm.move_equipment_batch(list(self.selected_eq_ids), vessel_id)
            if msg: msgs.append(msg)
        if msgs:
            self.selected_ids.clear()
            self.selected_eq_ids.clear()
            self.refresh()
            for msg in msgs:
                self.log_message.emit(msg)

    def _set_card_selected(self, pid: str, selected: bool):
        for container in self.containers.values():
            container.set_card_selected(pid, selected)

    def _set_eq_card_selected(self, eid: str, selected: bool):
        # 본함 장비 영역
        if eid in self.base_eq_cards:
            self.base_eq_cards[eid].selected = selected
        # 단정/어선 장비
        for container in self.containers.values():
            container.set_eq_card_selected(eid, selected)

    def _update_move_targets(self):
        has_sel = len(self.selected_ids) > 0 or len(self.selected_eq_ids) > 0
        for vid, container in self.containers.items():
            has_p = any(pid in self.selected_ids for pid in container.cards)
            has_e = any(eid in self.selected_eq_ids for eid in container.eq_cards)
            has_be = any(eid in self.selected_eq_ids for eid in self.base_eq_cards)
            if has_sel and not has_p and not has_e and not (vid == "base" and has_be):
                container.set_move_target(True)
            else:
                container.set_move_target(False)
