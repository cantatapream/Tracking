"""
SPT 설정 탭 - 인원 관리 + 선박 관리 + 장비 관리
"""
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton,
    QComboBox, QScrollArea, QFrame, QSizePolicy, QGridLayout
)
from PySide6.QtCore import Qt, Signal, QPoint
from core.data_manager import DataManager
from core.models import Equipment

RANKS = ["총경", "경정", "경감", "경위", "경사", "경장", "순경"]
DEPARTMENTS = ["함장", "부장", "항해", "안전", "병기", "기관", "구조", "행정", "통신", "조리"]
TEAM_DEPARTMENTS = ["항해", "안전", "병기", "기관", "구조", "행정", "통신", "조리"]
POSITION_DEPARTMENTS = ["함장", "부장"]


def _clear_layout(layout):
    while layout.count():
        item = layout.takeAt(0)
        w = item.widget()
        if w:
            w.setParent(None)


def _make_popup(parent_widget, min_width=320):
    """플로팅 팝업 프레임 생성"""
    popup = QFrame(parent_widget.window(), Qt.Popup | Qt.FramelessWindowHint)
    popup.setMinimumWidth(min_width)
    popup.setStyleSheet("""
        QFrame { background: #0d1f3c; border: 1px solid rgba(0,212,255,0.5); border-radius: 6px; }
        QLabel { background: transparent; border: none; color: #c8d6e5; }
        QLineEdit { background: #0a1628; color: #c8d6e5; border: 1px solid #1e3a5f; border-radius: 4px; padding: 4px 8px; font-size: 12px; }
        QLineEdit:focus { border-color: #00d4ff; }
        QComboBox { background: #0a1628; color: #c8d6e5; border: 1px solid #1e3a5f; border-radius: 4px; padding: 4px 8px; font-size: 12px; }
        QComboBox QAbstractItemView { background: #0d1f3c; color: #c8d6e5; border: 1px solid #1e3a5f; }
        QPushButton { background: #1e3a5f; color: #c8d6e5; border: 1px solid #2a4a6f; border-radius: 4px; padding: 4px 8px; font-size: 11px; font-weight: bold; }
        QPushButton:hover { border-color: #00d4ff; color: #00d4ff; }
        QPushButton#btnAccent { background: #005577; border: 1px solid #0088aa; color: #00d4ff; }
        QPushButton#btnDanger { background: #5f1e1e; border: 1px solid #8b3030; color: #e74c3c; }
    """)
    pl = QVBoxLayout(popup)
    pl.setContentsMargins(8, 6, 8, 6)
    pl.setSpacing(4)
    return popup, pl


# ============================================================
# 인원 편집 카드 - 클릭으로 플로팅 팝업 편집
# ============================================================
class PersonnelEditCard(QFrame):
    removed = Signal(str)
    updated = Signal(str, str, str)
    dept_changed = Signal(str, str)
    actions_opened = Signal(object)

    def __init__(self, pid: str, name: str, rank: str, dept: str = "", parent=None):
        super().__init__(parent)
        self.pid = pid
        self._name = name
        self._rank = rank
        self._dept = dept
        self.setObjectName("personnelCard")
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        self.setCursor(Qt.PointingHandCursor)
        self._setup_ui()

    def _setup_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(6, 3, 6, 3)
        main_layout.setSpacing(2)
        display_row = QHBoxLayout()
        display_row.setSpacing(4)
        self.name_label = QLabel(self._name)
        self.name_label.setObjectName("cardName")
        display_row.addWidget(self.name_label)
        self.rank_label = QLabel(self._rank)
        self.rank_label.setObjectName("cardRank")
        display_row.addWidget(self.rank_label)
        display_row.addStretch()
        main_layout.addLayout(display_row)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self._show_popup()
        super().mousePressEvent(event)

    def _show_popup(self):
        self.actions_opened.emit(self)
        popup, pl = _make_popup(self)

        row1 = QHBoxLayout()
        ni = QLineEdit(self._name)
        ni.setFixedHeight(26)
        row1.addWidget(ni, 2)
        rc = QComboBox()
        rc.setFixedHeight(26)
        rc.addItems(RANKS)
        rc.setCurrentText(self._rank)
        row1.addWidget(rc)
        dc = QComboBox()
        dc.setFixedHeight(26)
        dc.addItems(DEPARTMENTS)
        dc.setCurrentText(self._dept or "항해")
        row1.addWidget(dc)
        pl.addLayout(row1)

        row2 = QHBoxLayout()
        sb = QPushButton("저장")
        sb.setObjectName("btnAccent")
        sb.setFixedHeight(26)
        row2.addWidget(sb)
        db = QPushButton("삭제")
        db.setObjectName("btnDanger")
        db.setFixedHeight(26)
        row2.addWidget(db)
        cb = QPushButton("취소")
        cb.setFixedHeight(26)
        row2.addWidget(cb)
        row2.addStretch()
        pl.addLayout(row2)

        def save():
            n = ni.text().strip()
            r = rc.currentText()
            d = dc.currentText()
            if n:
                self._name = n
                self._rank = r
                self.name_label.setText(n)
                self.rank_label.setText(r)
                self.updated.emit(self.pid, n, r)
                if d != self._dept:
                    self._dept = d
                    self.dept_changed.emit(self.pid, d)
            popup.close()

        def delete():
            popup.close()
            self.removed.emit(self.pid)

        sb.clicked.connect(save)
        db.clicked.connect(delete)
        cb.clicked.connect(popup.close)

        pos = self.mapToGlobal(QPoint(0, self.height()))
        popup.move(pos)
        popup.show()
        ni.setFocus()
        ni.selectAll()

    def close_actions(self):
        pass  # 팝업은 자동 닫힘


# ============================================================
# 장비 카드 - 클릭으로 플로팅 팝업 편집
# ============================================================
class EquipmentCard(QFrame):
    deleted_signal = Signal()
    updated_signal = Signal()
    actions_opened = Signal(object)

    def __init__(self, equipment: Equipment, data_manager: DataManager, parent=None):
        super().__init__(parent)
        self.eq = equipment
        self.dm = data_manager
        self.setObjectName("personnelCard")
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        self.setCursor(Qt.PointingHandCursor)
        self._setup_ui()

    def _get_assignee_text(self):
        if self.eq.assignee_id:
            p = self.dm.get_personnel_by_id(self.eq.assignee_id)
            if p:
                return f"{p.rank} {p.name}"
        return "미지정"

    def _setup_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(4, 2, 4, 2)
        main_layout.setSpacing(1)
        display = QHBoxLayout()
        display.setSpacing(4)
        self.name_label = QLabel(self.eq.name)
        self.name_label.setObjectName("cardName")
        display.addWidget(self.name_label)
        sep = QLabel("|")
        sep.setStyleSheet("color: #5a7a9a; background:transparent; border:none;")
        sep.setFixedWidth(12)
        sep.setAlignment(Qt.AlignCenter)
        display.addWidget(sep)
        self.assignee_label = QLabel(self._get_assignee_text())
        self.assignee_label.setObjectName("cardRank")
        display.addWidget(self.assignee_label)
        display.addStretch()
        main_layout.addLayout(display)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self._show_popup()
        super().mousePressEvent(event)

    def _show_popup(self):
        self.actions_opened.emit(self)
        popup, pl = _make_popup(self, 300)

        row1 = QHBoxLayout()
        ni = QLineEdit(self.eq.name)
        ni.setFixedHeight(26)
        row1.addWidget(ni, 1)
        ac = QComboBox()
        ac.setFixedHeight(26)
        ac.addItem("담당자 없음", "")
        for p in self.dm.personnel:
            ac.addItem(f"{p.name} ({p.rank})", p.id)
        if self.eq.assignee_id:
            for i in range(ac.count()):
                if ac.itemData(i) == self.eq.assignee_id:
                    ac.setCurrentIndex(i)
                    break
        row1.addWidget(ac, 1)
        pl.addLayout(row1)

        row2 = QHBoxLayout()
        sb = QPushButton("저장")
        sb.setObjectName("btnAccent")
        sb.setFixedHeight(26)
        row2.addWidget(sb)
        db = QPushButton("삭제")
        db.setObjectName("btnDanger")
        db.setFixedHeight(26)
        row2.addWidget(db)
        cb = QPushButton("취소")
        cb.setFixedHeight(26)
        row2.addWidget(cb)
        row2.addStretch()
        pl.addLayout(row2)

        def save():
            n = ni.text().strip()
            if n:
                self.eq.name = n
                self.name_label.setText(n)
                pid = ac.currentData() or None
                if pid != self.eq.assignee_id:
                    self.dm.assign_equipment(self.eq.id, pid)
                self.assignee_label.setText(self._get_assignee_text())
                self.dm.save()
                self.updated_signal.emit()
            popup.close()

        def delete():
            popup.close()
            self.dm.remove_equipment(self.eq.id)
            self.dm.add_log(f"장비 '{self.eq.name}' 삭제")
            self.deleted_signal.emit()
            self.setParent(None)

        sb.clicked.connect(save)
        db.clicked.connect(delete)
        cb.clicked.connect(popup.close)

        pos = self.mapToGlobal(QPoint(0, self.height()))
        popup.move(pos)
        popup.show()
        ni.setFocus()
        ni.selectAll()

    def close_actions(self):
        pass


# ============================================================
# 설정 탭
# ============================================================
class SettingsTab(QWidget):
    data_changed = Signal()

    def __init__(self, data_manager: DataManager, parent=None):
        super().__init__(parent)
        self.dm = data_manager
        self.eq_cards: list[EquipmentCard] = []
        self._all_cards = []
        self._setup_ui()
        self.refresh()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 8, 12, 8)
        layout.setSpacing(6)

        # ======== 인원 관리 (제목 + 추가 폼 한 줄) ========
        add_frame = QFrame()
        add_frame.setObjectName("sectionPanel")
        al = QHBoxLayout(add_frame)
        al.setContentsMargins(8, 6, 8, 6)
        al.setSpacing(6)

        title_lbl = QLabel("인원 관리")
        title_lbl.setObjectName("sectionTitle")
        title_lbl.setStyleSheet("border: none;")
        al.addWidget(title_lbl)
        al.addSpacing(12)

        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText("이름")
        self.name_input.setFixedHeight(30)
        al.addWidget(self.name_input, 2)
        self.rank_combo = QComboBox()
        self.rank_combo.setFixedHeight(30)
        self.rank_combo.addItems(RANKS)
        al.addWidget(self.rank_combo)
        self.dept_combo = QComboBox()
        self.dept_combo.setFixedHeight(30)
        self.dept_combo.addItems(DEPARTMENTS)
        self.dept_combo.setCurrentText("항해")
        al.addWidget(self.dept_combo)
        add_btn = QPushButton("인원 추가")
        add_btn.setObjectName("btnAccent")
        add_btn.setFixedHeight(30)
        add_btn.clicked.connect(self._add_personnel)
        al.addWidget(add_btn)
        layout.addWidget(add_frame)

        # 인원 목록 (스크롤)
        self.personnel_scroll = QScrollArea()
        self.personnel_scroll.setWidgetResizable(True)
        self.personnel_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.personnel_scroll.setFrameShape(QFrame.NoFrame)
        self.personnel_content = QWidget()
        self.personnel_content_layout = QVBoxLayout(self.personnel_content)
        self.personnel_content_layout.setContentsMargins(0, 0, 0, 0)
        self.personnel_content_layout.setSpacing(4)

        # 직책 영역 (함장/부장) - 인라인
        self.position_frame = QFrame()
        self.position_frame.setObjectName("sectionPanel")
        pos_layout = QHBoxLayout(self.position_frame)
        pos_layout.setContentsMargins(6, 4, 6, 4)
        pos_layout.setSpacing(8)
        self.captain_widget = QWidget()
        self.captain_layout = QHBoxLayout(self.captain_widget)
        self.captain_layout.setContentsMargins(0, 0, 0, 0)
        self.captain_layout.setSpacing(4)
        pos_layout.addWidget(self.captain_widget, 1)
        self.vice_widget = QWidget()
        self.vice_layout = QHBoxLayout(self.vice_widget)
        self.vice_layout.setContentsMargins(0, 0, 0, 0)
        self.vice_layout.setSpacing(4)
        pos_layout.addWidget(self.vice_widget, 1)
        self.personnel_content_layout.addWidget(self.position_frame)

        # 팀 영역 (8팀) - 8열 가로 배치
        self.team_frame = QFrame()
        self.team_frame.setObjectName("sectionPanel")
        team_grid = QGridLayout(self.team_frame)
        team_grid.setContentsMargins(4, 4, 4, 4)
        team_grid.setSpacing(4)
        self.team_columns = {}
        for i, dept in enumerate(TEAM_DEPARTMENTS):
            col = self._make_dept_column(dept)
            team_grid.addWidget(col, 0, i)
            self.team_columns[dept] = col
        self.personnel_content_layout.addWidget(self.team_frame)
        self.personnel_content_layout.addStretch()
        self.personnel_scroll.setWidget(self.personnel_content)
        layout.addWidget(self.personnel_scroll, 3)

        # ======== 선박 관리 ========
        layout.addWidget(self._make_title("선박 관리"))
        vessel_container = QFrame()
        vessel_container.setObjectName("sectionPanel")
        vm = QHBoxLayout(vessel_container)
        vm.setContentsMargins(8, 8, 8, 8)
        vm.setSpacing(8)

        pf = QFrame()
        pl = QVBoxLayout(pf)
        pl.setContentsMargins(0, 0, 0, 0)
        pl.setSpacing(4)
        h = QLabel("단정")
        h.setObjectName("sectionTitlePatrol")
        h.setMinimumHeight(28)
        pl.addWidget(h)
        preset_row = QHBoxLayout()
        preset_row.setSpacing(4)
        self._selected_patrol_num = None
        self.patrol_preset_btns = []
        for i in range(1, 5):
            btn = QPushButton(f"No. {i} 단정")
            btn.setFixedHeight(30)
            btn.setCheckable(True)
            btn.clicked.connect(lambda checked, n=i, b=btn: self._select_patrol_preset(n, b))
            preset_row.addWidget(btn)
            self.patrol_preset_btns.append(btn)
        pb = QPushButton("추가")
        pb.setObjectName("btnAccent")
        pb.setFixedSize(50, 30)
        pb.clicked.connect(lambda: self._add_patrol_preset())
        preset_row.addWidget(pb)
        pl.addLayout(preset_row)
        ps = QScrollArea()
        ps.setWidgetResizable(True)
        ps.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        ps.setFrameShape(QFrame.NoFrame)
        self.patrol_list_widget = QWidget()
        self.patrol_list_layout = QVBoxLayout(self.patrol_list_widget)
        self.patrol_list_layout.setContentsMargins(0, 0, 0, 0)
        self.patrol_list_layout.setSpacing(3)
        ps.setWidget(self.patrol_list_widget)
        pl.addWidget(ps, 1)
        vm.addWidget(pf, 1)

        vf = QFrame()
        vl = QVBoxLayout(vf)
        vl.setContentsMargins(0, 0, 0, 0)
        vl.setSpacing(4)
        vh = QLabel("등선 대상 선박")
        vh.setObjectName("sectionTitleVessel")
        vh.setMinimumHeight(28)
        vl.addWidget(vh)
        vr = QHBoxLayout()
        self.vessel_name_input = QLineEdit()
        self.vessel_name_input.setPlaceholderText("선박 이름 (예: 중국어선 C)")
        self.vessel_name_input.setFixedHeight(30)
        vr.addWidget(self.vessel_name_input)
        vb = QPushButton("추가")
        vb.setObjectName("btnAccent")
        vb.setFixedSize(50, 30)
        vb.clicked.connect(lambda: self._add_vessel_type("vessel"))
        vr.addWidget(vb)
        vl.addLayout(vr)
        vs = QScrollArea()
        vs.setWidgetResizable(True)
        vs.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        vs.setFrameShape(QFrame.NoFrame)
        self.vessel_list_widget = QWidget()
        self.vessel_list_layout = QVBoxLayout(self.vessel_list_widget)
        self.vessel_list_layout.setContentsMargins(0, 0, 0, 0)
        self.vessel_list_layout.setSpacing(3)
        vs.setWidget(self.vessel_list_widget)
        vl.addWidget(vs, 1)
        vm.addWidget(vf, 1)
        layout.addWidget(vessel_container, 2)

        # ======== 장비 관리 ========
        layout.addWidget(self._make_title("장비 등록 및 관리"))
        eq_add_frame = QFrame()
        eq_add_frame.setObjectName("sectionPanel")
        el = QHBoxLayout(eq_add_frame)
        el.setContentsMargins(10, 8, 10, 8)
        el.setSpacing(6)
        self.eq_name_input = QLineEdit()
        self.eq_name_input.setPlaceholderText("장비 이름")
        self.eq_name_input.setFixedHeight(32)
        el.addWidget(self.eq_name_input, 2)
        self.eq_assignee_combo = QComboBox()
        self.eq_assignee_combo.setFixedHeight(32)
        el.addWidget(self.eq_assignee_combo, 1)
        eab = QPushButton("장비 추가")
        eab.setObjectName("btnAccent")
        eab.setFixedHeight(32)
        eab.clicked.connect(self._add_equipment)
        el.addWidget(eab)
        layout.addWidget(eq_add_frame)

        self.eq_scroll = QScrollArea()
        self.eq_scroll.setWidgetResizable(True)
        self.eq_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.eq_scroll.setFrameShape(QFrame.NoFrame)
        self.eq_scroll.setMinimumHeight(80)
        self.eq_list_widget = QWidget()
        self.eq_grid_layout = QGridLayout(self.eq_list_widget)
        self.eq_grid_layout.setContentsMargins(0, 0, 0, 0)
        self.eq_grid_layout.setSpacing(4)
        self.eq_scroll.setWidget(self.eq_list_widget)
        layout.addWidget(self.eq_scroll, 2)

    def _make_title(self, text):
        lbl = QLabel(text)
        lbl.setObjectName("sectionTitle")
        lbl.setMinimumHeight(28)
        return lbl

    def _make_dept_column(self, dept_name: str) -> QFrame:
        frame = QFrame()
        frame.setObjectName("vesselContainer")
        col_layout = QVBoxLayout(frame)
        col_layout.setContentsMargins(4, 4, 4, 4)
        col_layout.setSpacing(2)
        header_row = QHBoxLayout()
        header_row.setSpacing(4)
        header = QLabel(dept_name)
        header.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        header.setObjectName("vesselHeader")
        header_row.addWidget(header)
        header_row.addStretch()
        count_badge = QLabel("0명")
        count_badge.setObjectName("countBadge")
        count_badge.setAlignment(Qt.AlignCenter)
        header_row.addWidget(count_badge)
        col_layout.addLayout(header_row)
        list_widget = QWidget()
        list_layout = QVBoxLayout(list_widget)
        list_layout.setContentsMargins(0, 0, 0, 0)
        list_layout.setSpacing(2)
        col_layout.addWidget(list_widget, 1)
        frame._list_layout = list_layout
        frame._dept_name = dept_name
        frame._count_badge = count_badge
        return frame

    def _populate_position(self, layout, dept_name, persons):
        _clear_layout(layout)
        lbl = QLabel(dept_name)
        lbl.setFixedWidth(50)
        lbl.setObjectName("vesselHeader")
        layout.addWidget(lbl)
        if persons:
            for p in persons:
                card = PersonnelEditCard(p.id, p.name, p.rank, p.department)
                card.removed.connect(self._remove_personnel)
                card.updated.connect(self._update_personnel)
                card.dept_changed.connect(self._change_dept)
                card.actions_opened.connect(self._close_other_actions)
                self._all_cards.append(card)
                layout.addWidget(card, 1)
        else:
            ph = QLabel("(미배치)")
            ph.setStyleSheet("color: #5a7a9a; font-size: 11px;")
            layout.addWidget(ph)
        layout.addStretch()

    def _close_other_actions(self, opened):
        pass  # 팝업은 자동 닫힘

    # ---- 인원 ----
    def _add_personnel(self):
        name = self.name_input.text().strip()
        if not name:
            return
        self.dm.add_personnel(name, self.rank_combo.currentText(), department=self.dept_combo.currentText())
        self.name_input.clear()
        self.refresh()
        self.data_changed.emit()

    def _remove_personnel(self, pid):
        self.dm.remove_personnel(pid)
        self.refresh()
        self.data_changed.emit()

    def _update_personnel(self, pid, name, rank):
        self.dm.update_personnel(pid, name, rank)
        self.data_changed.emit()

    def _change_dept(self, pid, new_dept):
        self.dm.update_personnel_dept(pid, new_dept)
        self.refresh()
        self.data_changed.emit()

    # ---- 선박 ----
    def _select_patrol_preset(self, num, btn):
        if self._selected_patrol_num == num:
            self._selected_patrol_num = None
            btn.setChecked(False)
        else:
            self._selected_patrol_num = num
            for b in self.patrol_preset_btns:
                b.setChecked(b is btn)

    def _add_patrol_preset(self):
        num = self._selected_patrol_num
        if num is None:
            return
        vid = f"patrol_NO{num}"
        if vid in self.dm.vessels:
            return
        self.dm.add_vessel(vid, f"No. {num} 단정", "patrol")
        self._selected_patrol_num = None
        for b in self.patrol_preset_btns:
            b.setChecked(False)
        self.refresh()
        self.data_changed.emit()

    def _add_vessel_type(self, vtype):
        name = self.vessel_name_input.text().strip()
        if not name:
            return
        self.vessel_name_input.clear()
        suffix = name.upper().replace(" ", "-").replace("(", "").replace(")", "")
        vid = f"vessel_{suffix}"
        c = 1
        bv = vid
        while vid in self.dm.vessels:
            vid = f"{bv}-{c}"; c += 1
        self.dm.add_vessel(vid, name, vtype)
        self.refresh()
        self.data_changed.emit()

    def _remove_vessel(self, vid):
        self.dm.remove_vessel(vid)
        self.refresh()
        self.data_changed.emit()

    def _rename_vessel(self, vid, new_name):
        if vid in self.dm.vessels and new_name.strip():
            self.dm.vessels[vid]["name"] = new_name.strip()
            self.dm.save()
            self.refresh()
            self.data_changed.emit()

    # ---- 장비 ----
    def _add_equipment(self):
        name = self.eq_name_input.text().strip()
        if not name:
            return
        aid = self.eq_assignee_combo.currentData() or ""
        eq = self.dm.add_equipment(name)
        if aid:
            self.dm.assign_equipment(eq.id, aid)
        self.eq_name_input.clear()
        self.refresh()
        self.data_changed.emit()

    def _on_equipment_changed(self):
        self.refresh()
        self.data_changed.emit()

    def _populate_eq_assignee_combo(self):
        self.eq_assignee_combo.blockSignals(True)
        self.eq_assignee_combo.clear()
        self.eq_assignee_combo.addItem("담당자 없음", "")
        for p in self.dm.personnel:
            self.eq_assignee_combo.addItem(f"{p.name} ({p.rank})", p.id)
        self.eq_assignee_combo.blockSignals(False)

    # ---- 새로고침 ----
    def refresh(self):
        from core.data_manager import RANK_ORDER
        self._all_cards = []

        dept_personnel = {dept: [] for dept in DEPARTMENTS}
        for p in sorted(self.dm.personnel, key=lambda x: RANK_ORDER.get(x.rank, 99)):
            dept = p.department if p.department in DEPARTMENTS else "항해"
            dept_personnel[dept].append(p)

        self._populate_position(self.captain_layout, "함장", dept_personnel["함장"])
        self._populate_position(self.vice_layout, "부장", dept_personnel["부장"])

        for dept in TEAM_DEPARTMENTS:
            col = self.team_columns[dept]
            ll = col._list_layout
            while ll.count():
                item = ll.takeAt(0)
                if item.widget():
                    item.widget().setParent(None)
            persons = dept_personnel[dept]
            col._count_badge.setText(f"{len(persons)}명")
            for p in persons:
                card = PersonnelEditCard(p.id, p.name, p.rank, p.department)
                card.removed.connect(self._remove_personnel)
                card.updated.connect(self._update_personnel)
                card.dept_changed.connect(self._change_dept)
                card.actions_opened.connect(self._close_other_actions)
                self._all_cards.append(card)
                ll.addWidget(card)
            ll.addStretch()

        _clear_layout(self.patrol_list_layout)
        for vid, vi in sorted(self.dm.vessels.items()):
            if vi["type"] == "patrol":
                self.patrol_list_layout.addWidget(self._create_vessel_row(vid, vi, "patrol"))
        self.patrol_list_layout.addStretch()

        _clear_layout(self.vessel_list_layout)
        for vid, vi in sorted(self.dm.vessels.items()):
            if vi["type"] == "vessel":
                self.vessel_list_layout.addWidget(self._create_vessel_row(vid, vi, "vessel"))
        self.vessel_list_layout.addStretch()

        # 장비 (4열 그리드)
        self.eq_cards.clear()
        while self.eq_grid_layout.count():
            item = self.eq_grid_layout.takeAt(0)
            if item.widget():
                item.widget().setParent(None)
        for i, eq in enumerate(self.dm.equipment):
            card = EquipmentCard(eq, self.dm)
            card.deleted_signal.connect(self._on_equipment_changed)
            card.updated_signal.connect(self._on_equipment_changed)
            card.actions_opened.connect(self._close_other_actions)
            self.eq_cards.append(card)
            self.eq_grid_layout.addWidget(card, i // 4, i % 4)

        self._populate_eq_assignee_combo()

    def _create_vessel_row(self, vid, vinfo, vtype="vessel"):
        row = QFrame()
        row.setObjectName("personnelCard")
        row.setMinimumHeight(36)
        rl = QHBoxLayout(row)
        rl.setContentsMargins(8, 4, 8, 4)
        rl.setSpacing(6)
        name_label = QLabel(vinfo["name"])
        name_label.setObjectName("cardName")
        rl.addWidget(name_label)
        rl.addStretch()
        count_label = QLabel(f"{len(self.dm.get_personnel_at(vid))}명")
        count_label.setObjectName("cardRank")
        rl.addWidget(count_label)

        if vtype == "patrol":
            # 단정: 삭제만
            del_btn = QPushButton("삭제")
            del_btn.setObjectName("btnDanger")
            del_btn.setFixedSize(50, 24)
            del_btn.clicked.connect(lambda c, v=vid: self._remove_vessel(v))
            rl.addWidget(del_btn)
        else:
            # 등선 대상 선박: 이름 클릭→팝업 수정 + 삭제
            name_label.setCursor(Qt.PointingHandCursor)

            def show_edit_popup(event, v=vid, vi=vinfo, nl=name_label):
                popup, ppl = _make_popup(nl, 260)
                r1 = QHBoxLayout()
                ni = QLineEdit(vi["name"])
                ni.setFixedHeight(26)
                r1.addWidget(ni, 1)
                ppl.addLayout(r1)
                r2 = QHBoxLayout()
                sb = QPushButton("저장")
                sb.setObjectName("btnAccent")
                sb.setFixedHeight(26)
                r2.addWidget(sb)
                dbb = QPushButton("삭제")
                dbb.setObjectName("btnDanger")
                dbb.setFixedHeight(26)
                r2.addWidget(dbb)
                cbb = QPushButton("취소")
                cbb.setFixedHeight(26)
                r2.addWidget(cbb)
                r2.addStretch()
                ppl.addLayout(r2)

                def save():
                    n = ni.text().strip()
                    if n:
                        self._rename_vessel(v, n)
                    popup.close()

                def delete():
                    popup.close()
                    self._remove_vessel(v)

                sb.clicked.connect(save)
                dbb.clicked.connect(delete)
                cbb.clicked.connect(popup.close)
                pos = nl.mapToGlobal(QPoint(0, nl.height()))
                popup.move(pos)
                popup.show()
                ni.setFocus()
                ni.selectAll()

            name_label.mousePressEvent = show_edit_popup

        return row
