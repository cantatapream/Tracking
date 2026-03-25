"""
SPT 메인 대시보드 - 3단 컬럼 (본함 / 단정 / 어선) + 장비 이동
"""
from PySide6.QtWidgets import (
    QWidget, QHBoxLayout, QVBoxLayout, QLabel, QScrollArea, QFrame,
    QSizePolicy, QSplitter, QLineEdit, QPushButton, QGridLayout
)
from PySide6.QtCore import Qt, Signal, QTimer
from PySide6.QtGui import QWheelEvent, QPainter, QColor, QPen
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


class EquipmentInventoryPanel(QFrame):
    """본함 장비 보유 목록 패널"""
    eq_card_clicked = Signal(str, bool)  # equipment_id, ctrl
    panel_clicked = Signal(str)  # "base"를 emit

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("sectionPanel")
        self.setCursor(Qt.PointingHandCursor)
        self.eq_cards: dict[str, EquipmentMiniCard] = {}
        self._move_target_mode = False
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # 제목 행
        title_frame = QFrame()
        title_frame.setObjectName("equipmentSectionHeader")
        title_frame.setMinimumHeight(28)
        title_h = QHBoxLayout(title_frame)
        title_h.setContentsMargins(8, 2, 8, 2)
        title_h.setSpacing(8)

        title_label = QLabel("장비 보유 목록")
        title_label.setObjectName("equipmentSectionHeader")
        title_label.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        title_h.addWidget(title_label)
        title_h.addStretch()

        self.eq_count_badge = QLabel("0개")
        self.eq_count_badge.setObjectName("countBadge")
        title_h.addWidget(self.eq_count_badge)

        layout.addWidget(title_frame)

        # 장비 목록 (1열, 스크롤)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll.setFrameShape(QFrame.NoFrame)

        self._list_widget = QWidget()
        self._list_layout = QVBoxLayout(self._list_widget)
        self._list_layout.setContentsMargins(4, 2, 4, 2)
        self._list_layout.setSpacing(2)
        self._list_layout.addStretch()
        scroll.setWidget(self._list_widget)
        layout.addWidget(scroll, 1)

    def set_equipment(self, equipment_list):
        """장비 목록 갱신"""
        for card in self.eq_cards.values():
            card.setParent(None)
            card.deleteLater()
        self.eq_cards.clear()

        while self._list_layout.count():
            item = self._list_layout.takeAt(0)
            if item.widget():
                item.widget().setParent(None)

        for eq in equipment_list:
            card = EquipmentMiniCard(eq)
            card.clicked.connect(self._on_eq_card_clicked)
            self.eq_cards[eq.id] = card
            self._list_layout.addWidget(card)

        self._list_layout.addStretch()
        self.eq_count_badge.setText(f"{len(equipment_list)}개")

    def set_eq_card_selected(self, eid: str, selected: bool):
        if eid in self.eq_cards:
            self.eq_cards[eid].selected = selected

    def set_move_target(self, active: bool):
        """이동 대상 모드 표시"""
        self._move_target_mode = active
        if active:
            self.setObjectName("moveTarget")
        else:
            self.setObjectName("sectionPanel")
        self.setStyleSheet(self.styleSheet())

    def _on_eq_card_clicked(self, eid: str, ctrl: bool):
        self.eq_card_clicked.emit(eid, ctrl)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.panel_clicked.emit("base")
        super().mousePressEvent(event)


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
        self.eq_inventory_panel = None  # 외부에서 set_equipment_panel()으로 설정
        self._setup_ui()
        self._setup_timer()

    def _setup_ui(self):
        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(8)

        # === 좌측: 본함 ===
        self.base_panel = self._create_base_section()
        self.base_panel.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Preferred)
        main_layout.addWidget(self.base_panel, 1)

        # === 중앙: 단정 ===
        self.patrol_panel = self._create_section_multi(
            "단정 운용 상태", "sectionTitlePatrol", "patrol"
        )
        self.patrol_panel.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Preferred)
        main_layout.addWidget(self.patrol_panel, 1)

        # === 우측: 어선 ===
        self.vessel_panel = self._create_section_multi(
            "등선 대상 선박", "sectionTitleVessel", "vessel"
        )
        self.vessel_panel.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Preferred)
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
        title_h.setContentsMargins(6, 6, 8, 6)
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

        # 직별 필터 버튼 (2줄)
        filter_frame = QFrame()
        filter_frame.setStyleSheet("background: transparent; border: none;")
        filter_v = QVBoxLayout(filter_frame)
        filter_v.setContentsMargins(8, 2, 8, 2)
        filter_v.setSpacing(2)

        self._dept_filter = None  # None = 전체
        self._filter_buttons = []

        row1_depts = ["전체", "항해", "안전", "병기", "기관"]
        row2_depts = ["구조", "행정", "통신", "조리"]

        btn_style = """
            QPushButton {
                font-size: 12px; padding: 3px 8px; border-radius: 4px;
                border: 1px solid #1e3a5f; background: rgba(15, 35, 65, 0.6);
                color: #8faabe; font-weight: bold;
            }
            QPushButton:hover { border-color: rgba(0, 212, 255, 0.4); color: #c8d6e5; }
            QPushButton:checked { background: rgba(0, 212, 255, 0.2); border: 1px solid #00d4ff; color: #00d4ff; }
        """

        for row_depts in [row1_depts, row2_depts]:
            row_layout = QHBoxLayout()
            row_layout.setSpacing(4)
            for dept in row_depts:
                btn = QPushButton(dept)
                btn.setCheckable(True)
                btn.setFixedHeight(26)
                btn.setStyleSheet(btn_style)
                if dept == "전체":
                    btn.setChecked(True)
                btn.clicked.connect(lambda checked, d=dept, b=btn: self._on_dept_filter(d, b))
                row_layout.addWidget(btn, 1)  # 균등 배분
                self._filter_buttons.append(btn)
            filter_v.addLayout(row_layout)

        layout.addWidget(filter_frame)

        # 인원 컨테이너 (헤더 숨김) - 기타 직별 제외
        container = VesselContainer("base", base_name, "base", hide_header=True)
        container.header_clicked.connect(self._on_base_or_inventory_clicked)
        container.card_clicked.connect(self._on_card_clicked)
        self.containers["base"] = container
        layout.addWidget(container, 3)

        # 기타 직별 전용 서브 영역 (본함 하단, 최대 1/4 크기)
        custom_dept = self.dm.custom_dept_name if hasattr(self.dm, 'custom_dept_name') else "기타"
        self._custom_dept_frame = QFrame()
        self._custom_dept_frame.setObjectName("vesselContainer")
        self._custom_dept_frame.setMaximumHeight(200)
        cd_layout = QVBoxLayout(self._custom_dept_frame)
        cd_layout.setContentsMargins(4, 4, 4, 4)
        cd_layout.setSpacing(2)

        cd_header = QHBoxLayout()
        cd_header.setSpacing(4)
        self._custom_dept_title = QLabel(custom_dept)
        self._custom_dept_title.setObjectName("vesselHeader")
        cd_header.addWidget(self._custom_dept_title)
        cd_header.addStretch()
        self._custom_dept_badge = QLabel("0명")
        self._custom_dept_badge.setObjectName("countBadge")
        cd_header.addWidget(self._custom_dept_badge)
        cd_layout.addLayout(cd_header)

        # 기타 직별 인원 컨테이너
        self._custom_dept_container = VesselContainer(
            "base_custom", base_name, "base", hide_header=True
        )
        self._custom_dept_container.header_clicked.connect(self._on_base_or_inventory_clicked)
        self._custom_dept_container.card_clicked.connect(self._on_card_clicked)
        cd_layout.addWidget(self._custom_dept_container, 1)

        self._custom_dept_frame.hide()  # 기타 인원 없으면 숨김
        layout.addWidget(self._custom_dept_frame, 1)

        return panel

    def set_equipment_panel(self, panel: EquipmentInventoryPanel):
        """외부 장비 인벤토리 패널 연결 (사이드바에서 사용)"""
        self.eq_inventory_panel = panel
        panel.eq_card_clicked.connect(self._on_eq_card_clicked)
        panel.panel_clicked.connect(self._on_base_or_inventory_clicked)

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
        title_h.setContentsMargins(6, 6, 8, 6)
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

    def _add_custom_sub(self, vid, parent_container, parent_layout):
        """단정/등선대상선박용 기타 직별 서브 컨테이너 생성"""
        if not hasattr(self, '_custom_subs'):
            self._custom_subs = {}
        custom_dept = self.dm.custom_dept_name if hasattr(self.dm, 'custom_dept_name') else "기타"

        # 서브 컨테이너를 parent_container 내부에 추가
        vtype = self.dm.vessels.get(vid, {}).get("type", "patrol")
        frame = QFrame()
        frame.setObjectName("vesselContainer")
        fl = QVBoxLayout(frame)
        fl.setContentsMargins(4, 4, 4, 4)
        fl.setSpacing(2)

        hdr = QHBoxLayout()
        hdr.setSpacing(4)
        title = QLabel(custom_dept)
        title.setObjectName("vesselHeader")
        title.setStyleSheet("font-weight: bold;")
        hdr.addWidget(title)
        hdr.addStretch()
        badge = QLabel("0명")
        badge.setObjectName("countBadge")
        hdr.addWidget(badge)
        fl.addLayout(hdr)

        sub_vid = f"{vid}__custom"
        sub_container = VesselContainer(sub_vid, "", vtype, hide_header=True)
        sub_container.header_clicked.connect(self._on_container_clicked)
        sub_container.card_clicked.connect(self._on_card_clicked)
        if hasattr(sub_container, 'eq_card_clicked'):
            sub_container.eq_card_clicked.connect(self._on_eq_card_clicked)
        fl.addWidget(sub_container, 1)

        frame.hide()
        self._custom_subs[vid] = {"frame": frame, "container": sub_container, "title": title, "badge": badge}

        # VesselContainer 내부 cards_layout의 stretch 앞에 삽입
        cl = parent_container.cards_layout
        idx = cl.count() - 1  # stretch 앞
        cl.insertWidget(idx, frame)

    def rebuild_containers(self):
        """선박 목록 변경 시 컨테이너 재구성"""
        # 기타 서브 컨테이너 정리
        if hasattr(self, '_custom_subs'):
            for info in self._custom_subs.values():
                info["frame"].setParent(None)
                info["frame"].deleteLater()
            self._custom_subs = {}

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
                    # 기타 직별 서브 컨테이너
                    self._add_custom_sub(vid, c, layout)
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
                    # 기타 직별 서브 컨테이너 (vessel용)
                    self._add_custom_sub(vid, c, draggable)

    def refresh(self):
        """전체 데이터 새로고침"""
        self.rebuild_containers()
        patrol_total = 0
        vessel_total = 0

        custom_dept = self.dm.custom_dept_name if hasattr(self.dm, 'custom_dept_name') else "기타"

        for vid, container in self.containers.items():
            personnel = self.dm.get_personnel_at(vid)

            if vid == "base":
                # 본함: 기타 직별 인원 분리
                base_normal = [p for p in personnel if p.department != custom_dept]
                base_custom = [p for p in personnel if p.department == custom_dept]
                container.set_personnel(base_normal)

                # 기타 직별 서브 영역 업데이트
                if hasattr(self, '_custom_dept_container'):
                    self._custom_dept_container.set_personnel(base_custom)
                    self._custom_dept_container.update_timers()
                    for pid in self.selected_ids:
                        self._custom_dept_container.set_card_selected(pid, True)
                    self._custom_dept_title.setText(custom_dept)
                    self._custom_dept_badge.setText(f"{len(base_custom)}명")
                    if base_custom:
                        self._custom_dept_frame.show()
                        self.base_count_badge.setText(f"{len(base_normal)} + {len(base_custom)}명")
                    else:
                        self._custom_dept_frame.hide()
                        self.base_count_badge.setText(f"{len(base_normal)}명")
            else:
                # 단정/선박: 기타 인원 분리
                normal = [p for p in personnel if p.department != custom_dept]
                custom = [p for p in personnel if p.department == custom_dept]
                container.set_personnel(normal)
                equipment = self.dm.get_equipment_at(vid)
                container.set_equipment(equipment)

                # 기타 서브 컨테이너 업데이트
                if hasattr(self, '_custom_subs') and vid in self._custom_subs:
                    sub = self._custom_subs[vid]
                    sub["container"].set_personnel(custom)
                    sub["container"].update_timers()
                    sub["title"].setText(custom_dept)
                    sub["badge"].setText(f"{len(custom)}명")
                    for pid in self.selected_ids:
                        sub["container"].set_card_selected(pid, True)
                    sub["frame"].setVisible(len(custom) > 0)

            container.update_timers()
            for pid in self.selected_ids:
                container.set_card_selected(pid, True)

            # 섹션별 총인원 집계
            vinfo = self.dm.vessels.get(vid, {})
            if vinfo.get("type") == "patrol":
                normal_count = len([p for p in personnel if p.department != custom_dept])
                custom_count = len([p for p in personnel if p.department == custom_dept])
                patrol_total += len(personnel)
            elif vinfo.get("type") == "vessel":
                normal_count = len([p for p in personnel if p.department != custom_dept])
                custom_count = len([p for p in personnel if p.department == custom_dept])
                vessel_total += len(personnel)

        # 본함 장비 → 인벤토리 패널
        if self.eq_inventory_panel:
            base_equipment = self.dm.get_equipment_at("base")
            self.eq_inventory_panel.set_equipment(base_equipment)
            # 선택 없으면 이동 대상 테두리 초기화
            if not self.selected_ids and not self.selected_eq_ids:
                self.eq_inventory_panel.set_move_target(False)

        # 섹션 총인원 뱃지 업데이트 (기타 인원 포함 시 ## + #명)
        if hasattr(self, '_section_badges'):
            for stype, total in [("patrol", patrol_total), ("vessel", vessel_total)]:
                if stype in self._section_badges:
                    # 기타 인원 합산
                    custom_total = 0
                    normal_total = 0
                    for vid, container in self.containers.items():
                        vinfo = self.dm.vessels.get(vid, {})
                        if vinfo.get("type") == stype:
                            personnel = self.dm.get_personnel_at(vid)
                            custom_total += len([p for p in personnel if p.department == custom_dept])
                            normal_total += len([p for p in personnel if p.department != custom_dept])
                    if custom_total > 0:
                        self._section_badges[stype].setText(f"{normal_total} + {custom_total}명")
                    else:
                        self._section_badges[stype].setText(f"{total}명")

        # 장비 선택 상태 복원
        for eid in self.selected_eq_ids:
            if self.eq_inventory_panel:
                self.eq_inventory_panel.set_eq_card_selected(eid, True)
            for container in self.containers.values():
                container.set_eq_card_selected(eid, True)

        # 직별 필터 재적용
        if hasattr(self, '_dept_filter'):
            self._apply_base_filter()

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

    def _on_base_or_inventory_clicked(self, vessel_id: str):
        """본함 영역 또는 장비 인벤토리 클릭 → 인원은 base, 장비도 base(인벤토리)로 이동"""
        if not self.selected_ids and not self.selected_eq_ids:
            return
        msgs = []
        if self.selected_ids:
            msg = self.dm.move_personnel_batch(list(self.selected_ids), "base")
            if msg: msgs.append(msg)
        if self.selected_eq_ids:
            msg = self.dm.move_equipment_batch(list(self.selected_eq_ids), "base")
            if msg: msgs.append(msg)
        if msgs:
            self.selected_ids.clear()
            self.selected_eq_ids.clear()
            self.refresh()
            for msg in msgs:
                self.log_message.emit(msg)

    def _on_container_clicked(self, vessel_id: str):
        # __custom 접미사 제거 (기타 서브 컨테이너 → 원본 vessel로 이동)
        real_vid = vessel_id.replace("__custom", "") if "__custom" in vessel_id else vessel_id
        if not self.selected_ids and not self.selected_eq_ids:
            return
        msgs = []
        if self.selected_ids:
            msg = self.dm.move_personnel_batch(list(self.selected_ids), real_vid)
            if msg: msgs.append(msg)
        if self.selected_eq_ids:
            msg = self.dm.move_equipment_batch(list(self.selected_eq_ids), real_vid)
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
        # 본함 기타 서브 컨테이너
        if hasattr(self, '_custom_dept_container'):
            self._custom_dept_container.set_card_selected(pid, selected)
        # 단정/선박 기타 서브 컨테이너
        if hasattr(self, '_custom_subs'):
            for sub in self._custom_subs.values():
                sub["container"].set_card_selected(pid, selected)

    def _set_eq_card_selected(self, eid: str, selected: bool):
        if self.eq_inventory_panel:
            self.eq_inventory_panel.set_eq_card_selected(eid, selected)
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

    def _on_dept_filter(self, dept: str, btn):
        """직별 필터 버튼 클릭"""
        if dept == "전체":
            self._dept_filter = None
        else:
            self._dept_filter = dept
        for b in self._filter_buttons:
            b.setChecked(b is btn)
        self._apply_base_filter()

    def _apply_base_filter(self):
        """본함 컨테이너에 직별 필터 적용"""
        base_container = self.containers.get("base")
        if not base_container:
            return
        for pid, card in base_container.cards.items():
            if self._dept_filter is None:
                card.show()
            else:
                if card.personnel.department == self._dept_filter:
                    card.show()
                else:
                    card.hide()

    def _update_move_targets(self):
        has_sel = len(self.selected_ids) > 0 or len(self.selected_eq_ids) > 0
        # 장비만 선택된 경우 (인원 미선택)
        only_eq_sel = len(self.selected_eq_ids) > 0 and len(self.selected_ids) == 0
        for vid, container in self.containers.items():
            has_p = any(pid in self.selected_ids for pid in container.cards)
            has_e = any(eid in self.selected_eq_ids for eid in container.eq_cards)
            if has_sel and not has_p and not has_e:
                # 장비만 선택 + 인벤토리 장비 선택 시 본함은 제외
                if vid == "base" and only_eq_sel:
                    inv_sel = self.eq_inventory_panel and any(
                        eid in self.selected_eq_ids for eid in self.eq_inventory_panel.eq_cards
                    )
                    if inv_sel:
                        container.set_move_target(False)
                        continue
                container.set_move_target(True)
            else:
                container.set_move_target(False)

        # 인벤토리 패널: 장비가 선택된 경우에만 이동 대상 표시 (사람 선택 시 제외)
        if self.eq_inventory_panel:
            has_inv_e = any(eid in self.selected_eq_ids for eid in self.eq_inventory_panel.eq_cards)
            if only_eq_sel and not has_inv_e:
                self.eq_inventory_panel.set_move_target(True)
            else:
                self.eq_inventory_panel.set_move_target(False)
