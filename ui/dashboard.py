"""
SPT 메인 대시보드 - 3단 컬럼 (본함 / 단정 / 어선) + 장비 이동
"""
from PySide6.QtWidgets import (
    QWidget, QHBoxLayout, QVBoxLayout, QLabel, QScrollArea, QFrame,
    QSizePolicy, QSplitter
)
from PySide6.QtCore import Qt, Signal, QTimer
from ui.vessel_container import VesselContainer
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
        self._setup_ui()
        self._setup_timer()
        self.refresh()

    def _setup_ui(self):
        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(8, 8, 8, 8)
        main_layout.setSpacing(8)

        # === 좌측: 본함 ===
        self.base_panel = self._create_section("본함 (BASE SHIP)", "sectionTitle", "base")
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

    def _create_section(self, title: str, title_style: str, section_type: str) -> QFrame:
        """본함용 단일 섹션"""
        panel = QFrame()
        panel.setObjectName("sectionPanel")
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # 제목
        title_label = QLabel(f"  {title}")
        title_label.setObjectName(title_style)
        title_label.setFixedHeight(40)
        layout.addWidget(title_label)

        # 본함 컨테이너
        container = VesselContainer("base", "본함 (KCG 3012)", "base")
        container.header_clicked.connect(self._on_container_clicked)
        container.card_clicked.connect(self._on_card_clicked)
        container.eq_card_clicked.connect(self._on_eq_card_clicked)
        self.containers["base"] = container
        layout.addWidget(container)

        return panel

    def _create_section_multi(self, title: str, title_style: str, section_type: str) -> QFrame:
        """단정/어선용 다중 컨테이너 섹션"""
        panel = QFrame()
        panel.setObjectName("sectionPanel")
        panel_layout = QVBoxLayout(panel)
        panel_layout.setContentsMargins(0, 0, 0, 0)
        panel_layout.setSpacing(0)

        # 제목
        title_label = QLabel(f"  {title}")
        title_label.setObjectName(title_style)
        title_label.setFixedHeight(40)
        panel_layout.addWidget(title_label)

        # 스크롤 영역
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
        # 기존 단정/어선 컨테이너 제거
        for vid in list(self.containers.keys()):
            if vid != "base":
                container = self.containers.pop(vid)
                container.setParent(None)
                container.deleteLater()

        # 단정 컨테이너 재생성
        if "patrol" in self._scroll_widgets:
            widget, layout = self._scroll_widgets["patrol"]
            while layout.count():
                item = layout.takeAt(0)
                if item.widget():
                    item.widget().setParent(None)

            for vid, vinfo in sorted(self.dm.vessels.items()):
                if vinfo["type"] == "patrol":
                    container = VesselContainer(vid, vinfo["name"], "patrol")
                    container.header_clicked.connect(self._on_container_clicked)
                    container.card_clicked.connect(self._on_card_clicked)
                    container.eq_card_clicked.connect(self._on_eq_card_clicked)
                    self.containers[vid] = container
                    layout.addWidget(container)
            layout.addStretch()

        # 어선 컨테이너 재생성
        if "vessel" in self._scroll_widgets:
            widget, layout = self._scroll_widgets["vessel"]
            while layout.count():
                item = layout.takeAt(0)
                if item.widget():
                    item.widget().setParent(None)

            for vid, vinfo in sorted(self.dm.vessels.items()):
                if vinfo["type"] == "vessel":
                    container = VesselContainer(vid, vinfo["name"], "vessel")
                    container.header_clicked.connect(self._on_container_clicked)
                    container.card_clicked.connect(self._on_card_clicked)
                    container.eq_card_clicked.connect(self._on_eq_card_clicked)
                    self.containers[vid] = container
                    layout.addWidget(container)
            layout.addStretch()

    def refresh(self):
        """전체 데이터 새로고침"""
        self.rebuild_containers()
        for vid, container in self.containers.items():
            personnel = self.dm.get_personnel_at(vid)
            container.set_personnel(personnel)

            # 장비 표시
            equipment = self.dm.get_equipment_at(vid)
            container.set_equipment(equipment)

            container.update_timers()
            # 선택 상태 복원
            for pid in self.selected_ids:
                container.set_card_selected(pid, True)
            for eid in self.selected_eq_ids:
                container.set_eq_card_selected(eid, True)

    def _setup_timer(self):
        """1초 타이머 - 실시간 업데이트"""
        self.update_timer = QTimer(self)
        self.update_timer.timeout.connect(self._tick)
        self.update_timer.start(1000)

    def _tick(self):
        """매초 타이머 업데이트"""
        for container in self.containers.values():
            container.update_timers()

    def _on_card_clicked(self, pid: str, ctrl: bool):
        """대원 카드 클릭 - 항상 토글"""
        if pid in self.selected_ids:
            self.selected_ids.discard(pid)
            self._set_card_selected(pid, False)
        else:
            self.selected_ids.add(pid)
            self._set_card_selected(pid, True)

        self._update_move_targets()

    def _on_eq_card_clicked(self, eid: str, ctrl: bool):
        """장비 카드 클릭 - 토글"""
        if eid in self.selected_eq_ids:
            self.selected_eq_ids.discard(eid)
            self._set_eq_card_selected(eid, False)
        else:
            self.selected_eq_ids.add(eid)
            self._set_eq_card_selected(eid, True)

        self._update_move_targets()

    def _on_container_clicked(self, vessel_id: str):
        """컨테이너 헤더 클릭 → 선택된 대원/장비를 해당 선박으로 일괄 이동"""
        if not self.selected_ids and not self.selected_eq_ids:
            return

        msgs = []

        if self.selected_ids:
            pids = list(self.selected_ids)
            msg = self.dm.move_personnel_batch(pids, vessel_id)
            if msg:
                msgs.append(msg)

        if self.selected_eq_ids:
            eids = list(self.selected_eq_ids)
            msg = self.dm.move_equipment_batch(eids, vessel_id)
            if msg:
                msgs.append(msg)

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
        for container in self.containers.values():
            container.set_eq_card_selected(eid, selected)

    def _clear_all_selection(self):
        self.selected_ids.clear()
        self.selected_eq_ids.clear()
        for container in self.containers.values():
            container.clear_selection()
        self._update_move_targets()

    def _update_move_targets(self):
        """선택 상태에 따라 이동 대상 하이라이트"""
        has_selection = len(self.selected_ids) > 0 or len(self.selected_eq_ids) > 0
        for vid, container in self.containers.items():
            has_selected_here = any(pid in self.selected_ids for pid in container.cards)
            has_eq_selected_here = any(eid in self.selected_eq_ids for eid in container.eq_cards)
            if has_selection and not has_selected_here and not has_eq_selected_here:
                container.set_move_target(True)
            else:
                container.set_move_target(False)
