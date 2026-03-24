"""
SPT 메인 대시보드 - 3단 컬럼 (본함 / 단정 / 어선) + 장비 이동
"""
from PySide6.QtWidgets import (
    QWidget, QHBoxLayout, QVBoxLayout, QLabel, QScrollArea, QFrame,
    QSizePolicy, QSplitter, QLineEdit
)
from PySide6.QtCore import Qt, Signal, QTimer
from PySide6.QtGui import QWheelEvent
from ui.vessel_container import VesselContainer, EquipmentMiniCard, DraggableVesselList
from core.data_manager import DataManager
from typing import List, Set
import re


def _patrol_sort_key(item):
    """단정을 번호 오름차순으로 정렬"""
    vid, vinfo = item
    name = vinfo.get("name", "")
    m = re.search(r'(\d+)', name)
    return int(m.group(1)) if m else 999


class DashboardView(QWidget):
    """3단 컬럼 대시보드"""
    log_message = Signal(str)

    _dashboard_font_size = 13  # 전역 폰트 크기

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

        # === 좌측: 본함 (인원 3/4 + 장비 1/4) ===
        self.base_panel = self._create_base_section()
        main_layout.addWidget(self.base_panel, 1)

        # === 중앙: 단정 ===
        self.patrol_panel = self._create_section_multi(
            "단정 운용 상태", "sectionTitlePatrol", "patrol"
        )
        main_layout.addWidget(self.patrol_panel, 1)

        # === 우측: 어선 ===
        self.vessel_panel = self._create_section_multi(
            "검문검색 선박", "sectionTitleVessel", "vessel"
        )
        main_layout.addWidget(self.vessel_panel, 1)

    def _create_base_section(self) -> QFrame:
        """본함 섹션"""
        panel = QFrame()
        panel.setObjectName("sectionPanel")
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # 제목 행: 본함 이름 (클릭 편집) + 인원 뱃지
        title_frame = QFrame()
        title_frame.setObjectName("sectionTitle")
        title_frame.setMinimumHeight(56)
        title_h = QHBoxLayout(title_frame)
        title_h.setContentsMargins(12, 6, 12, 6)
        title_h.setSpacing(8)

        base_name = self.dm.vessels.get("base", {}).get("name", "본함 (KCG 3012)")
        self.base_title_label = QLabel(base_name)
        self.base_title_label.setObjectName("sectionTitle")
        self.base_title_label.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        self.base_title_label.setCursor(Qt.PointingHandCursor)
        self.base_title_label.mouseDoubleClickEvent = self._start_base_name_edit
        title_h.addWidget(self.base_title_label)

        self.base_title_input = QLineEdit(base_name)
        self.base_title_input.setObjectName("headerTitleInput")
        self.base_title_input.setMinimumHeight(28)
        self.base_title_input.returnPressed.connect(self._save_base_name_edit)
        self.base_title_input.hide()
        title_h.addWidget(self.base_title_input)

        # 확인 버튼
        from PySide6.QtWidgets import QPushButton
        self.base_title_confirm_btn = QPushButton("확인")
        self.base_title_confirm_btn.setObjectName("headerConfirmBtn")
        self.base_title_confirm_btn.setMinimumHeight(28)
        self.base_title_confirm_btn.setFixedWidth(50)
        self.base_title_confirm_btn.setCursor(Qt.PointingHandCursor)
        self.base_title_confirm_btn.clicked.connect(self._save_base_name_edit)
        self.base_title_confirm_btn.hide()
        title_h.addWidget(self.base_title_confirm_btn)

        title_h.addStretch()

        self.base_count_badge = QLabel("0명")
        self.base_count_badge.setObjectName("countBadge")
        title_h.addWidget(self.base_count_badge)

        layout.addWidget(title_frame)

        # 인원 컨테이너 (헤더 숨김)
        container = VesselContainer("base", base_name, "base", hide_header=True)
        container.header_clicked.connect(self._on_container_clicked)
        container.card_clicked.connect(self._on_card_clicked)
        container.eq_card_clicked.connect(self._on_eq_card_clicked)
        self.containers["base"] = container
        layout.addWidget(container, 1)

        return panel

    def _start_base_name_edit(self, event=None):
        """본함 이름 편집 시작"""
        self.base_title_label.hide()
        base_name = self.dm.vessels.get("base", {}).get("name", "본함 (KCG 3012)")
        self.base_title_input.setText(base_name)
        self.base_title_input.show()
        self.base_title_confirm_btn.show()
        self.base_title_input.setFocus()
        self.base_title_input.selectAll()

    def _save_base_name_edit(self):
        """본함 이름 편집 저장"""
        new_name = self.base_title_input.text().strip()
        if new_name and "base" in self.dm.vessels:
            self.dm.vessels["base"]["name"] = new_name
            self.dm.save()
            self.base_title_label.setText(new_name)
        self.base_title_input.hide()
        self.base_title_confirm_btn.hide()
        self.base_title_label.show()

    def _create_section_multi(self, title: str, title_style: str, section_type: str) -> QFrame:
        """단정/어선용 다중 컨테이너 섹션"""
        panel = QFrame()
        panel.setObjectName("sectionPanel")
        panel_layout = QVBoxLayout(panel)
        panel_layout.setContentsMargins(0, 0, 0, 0)
        panel_layout.setSpacing(0)

        # 제목 행: 타이틀 + 총인원 뱃지
        title_frame = QFrame()
        title_frame.setObjectName(title_style)
        title_frame.setMinimumHeight(56)
        title_h = QHBoxLayout(title_frame)
        title_h.setContentsMargins(12, 6, 12, 6)
        title_h.setSpacing(8)

        title_label = QLabel(title)
        title_label.setObjectName(title_style)
        title_label.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        title_h.addWidget(title_label)
        title_h.addStretch()

        badge_name = "countBadgePatrol" if section_type == "patrol" else "countBadgeVessel"
        total_badge = QLabel("0명")
        total_badge.setObjectName(badge_name)
        title_h.addWidget(total_badge)

        # 뱃지 참조 저장
        if not hasattr(self, '_section_badges'):
            self._section_badges = {}
        self._section_badges[section_type] = total_badge

        panel_layout.addWidget(title_frame)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll.setFrameShape(QFrame.NoFrame)

        self._scroll_widgets = getattr(self, '_scroll_widgets', {})

        if section_type == "vessel":
            # 어선: 드래그 순서 변경 가능한 위젯 사용
            draggable = DraggableVesselList()
            draggable.order_changed.connect(self._on_vessel_order_changed)
            self._scroll_widgets[section_type] = draggable
            scroll.setWidget(draggable)
        else:
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

            patrol_items = [(vid, vinfo) for vid, vinfo in self.dm.vessels.items() if vinfo["type"] == "patrol"]
            patrol_items.sort(key=_patrol_sort_key)
            for vid, vinfo in patrol_items:
                    c = VesselContainer(vid, vinfo["name"], "patrol")
                    c.header_clicked.connect(self._on_container_clicked)
                    c.card_clicked.connect(self._on_card_clicked)
                    c.eq_card_clicked.connect(self._on_eq_card_clicked)
                    self.containers[vid] = c
                    layout.addWidget(c)
            layout.addStretch()

        if "vessel" in self._scroll_widgets:
            draggable = self._scroll_widgets["vessel"]
            draggable.clear()

            vessel_order = self.dm.get_vessel_order()
            for vid in vessel_order:
                vinfo = self.dm.vessels.get(vid)
                if vinfo and vinfo["type"] == "vessel":
                    c = VesselContainer(vid, vinfo["name"], "vessel")
                    c.header_clicked.connect(self._on_container_clicked)
                    c.card_clicked.connect(self._on_card_clicked)
                    c.eq_card_clicked.connect(self._on_eq_card_clicked)
                    self.containers[vid] = c
                    draggable.add_container(c)

    def refresh(self):
        """전체 데이터 새로고침"""
        self.rebuild_containers()
        patrol_total = 0
        vessel_total = 0

        for vid, container in self.containers.items():
            personnel = self.dm.get_personnel_at(vid)
            container.set_personnel(personnel)

            # 모든 위치에 장비 인라인 표시
            equipment = self.dm.get_equipment_at(vid)
            container.set_equipment(equipment)

            container.update_timers()
            for pid in self.selected_ids:
                container.set_card_selected(pid, True)

            # 섹션별 총인원 집계
            vinfo = self.dm.vessels.get(vid, {})
            if vinfo.get("type") == "patrol":
                patrol_total += len(personnel)
            elif vinfo.get("type") == "vessel":
                vessel_total += len(personnel)
            elif vid == "base":
                self.base_count_badge.setText(f"{len(personnel)}명")

        # 섹션 총인원 뱃지 업데이트
        if hasattr(self, '_section_badges'):
            if "patrol" in self._section_badges:
                self._section_badges["patrol"].setText(f"{patrol_total}명")
            if "vessel" in self._section_badges:
                self._section_badges["vessel"].setText(f"{vessel_total}명")

        for eid in self.selected_eq_ids:
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
        for container in self.containers.values():
            container.set_eq_card_selected(eid, selected)

    def _on_vessel_name_changed(self, vessel_id: str, new_name: str):
        """선박 이름 변경 저장"""
        if vessel_id in self.dm.vessels:
            self.dm.vessels[vessel_id]["name"] = new_name
            self.dm.save()

    def _on_vessel_order_changed(self, order: list):
        """어선 순서 변경 저장"""
        self.dm.set_vessel_order(order)

    def wheelEvent(self, event: QWheelEvent):
        """Ctrl+휠로 대시보드 전체 폰트 확대/축소"""
        if event.modifiers() & Qt.ControlModifier:
            delta = event.angleDelta().y()
            if delta > 0:
                DashboardView._dashboard_font_size = min(DashboardView._dashboard_font_size + 1, 22)
            elif delta < 0:
                DashboardView._dashboard_font_size = max(DashboardView._dashboard_font_size - 1, 9)
            sz = DashboardView._dashboard_font_size
            self.setStyleSheet(f"QWidget {{ font-size: {sz}px; }}")
            event.accept()
        else:
            super().wheelEvent(event)

    def _update_move_targets(self):
        has_sel = len(self.selected_ids) > 0 or len(self.selected_eq_ids) > 0
        for vid, container in self.containers.items():
            has_p = any(pid in self.selected_ids for pid in container.cards)
            has_e = any(eid in self.selected_eq_ids for eid in container.eq_cards)
            if has_sel and not has_p and not has_e:
                container.set_move_target(True)
            else:
                container.set_move_target(False)
