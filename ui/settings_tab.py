"""
SPT 설정 탭 - 인원 관리 + 선박 관리(좌: 단정, 우: 중국어선) + 장비 관리
"""
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton,
    QComboBox, QScrollArea, QFrame, QSizePolicy, QGridLayout
)
from PySide6.QtCore import Qt, Signal
from core.data_manager import DataManager
from core.models import Equipment

RANKS = ["총경", "경정", "경감", "경위", "경사", "경장", "순경"]
DEPARTMENTS = ["함장", "부장", "항해", "안전", "병기", "기관"]
TEAM_DEPARTMENTS = ["항해", "안전", "병기", "기관"]
POSITION_DEPARTMENTS = ["함장", "부장"]


def _clear_layout(layout):
    """레이아웃 내 모든 위젯 즉시 제거 (deleteLater 사용 안 함)"""
    while layout.count():
        item = layout.takeAt(0)
        w = item.widget()
        if w:
            w.setParent(None)


# ============================================================
# 인원 편집 카드 (컴팩트)
# ============================================================
class PersonnelEditCard(QFrame):
    removed = Signal(str)
    updated = Signal(str, str, str)

    def __init__(self, pid: str, name: str, rank: str, parent=None):
        super().__init__(parent)
        self.pid = pid
        self._name = name
        self._rank = rank
        self.setObjectName("personnelCard")
        self.setMinimumHeight(34)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        self._setup_ui()

    def _setup_ui(self):
        lo = QHBoxLayout(self)
        lo.setContentsMargins(6, 2, 6, 2)
        lo.setSpacing(4)

        self.name_label = QLabel(self._name)
        self.name_label.setObjectName("cardName")
        lo.addWidget(self.name_label)

        self.rank_label = QLabel(self._rank)
        self.rank_label.setObjectName("cardRank")
        lo.addWidget(self.rank_label)

        lo.addStretch()

        self.name_input = QLineEdit(self._name)
        self.name_input.setFixedHeight(24)
        self.name_input.setFixedWidth(70)
        self.name_input.hide()
        lo.addWidget(self.name_input)

        self.rank_combo = QComboBox()
        self.rank_combo.setFixedHeight(24)
        self.rank_combo.addItems(RANKS)
        self.rank_combo.setCurrentText(self._rank)
        self.rank_combo.hide()
        lo.addWidget(self.rank_combo)

        self.edit_btn = QPushButton("수정")
        self.edit_btn.setFixedSize(40, 24)
        self.edit_btn.clicked.connect(self._toggle_edit)
        lo.addWidget(self.edit_btn)

        self.save_btn = QPushButton("저장")
        self.save_btn.setObjectName("btnAccent")
        self.save_btn.setFixedSize(40, 24)
        self.save_btn.clicked.connect(self._save_edit)
        self.save_btn.hide()
        lo.addWidget(self.save_btn)

        self.cancel_btn = QPushButton("취소")
        self.cancel_btn.setFixedSize(40, 24)
        self.cancel_btn.clicked.connect(self._cancel_edit)
        self.cancel_btn.hide()
        lo.addWidget(self.cancel_btn)

        del_btn = QPushButton("삭제")
        del_btn.setObjectName("btnDanger")
        del_btn.setFixedSize(40, 24)
        del_btn.clicked.connect(lambda: self.removed.emit(self.pid))
        lo.addWidget(del_btn)

    def _toggle_edit(self):
        self.name_label.hide(); self.rank_label.hide(); self.edit_btn.hide()
        self.name_input.setText(self._name)
        self.rank_combo.setCurrentText(self._rank)
        self.name_input.show(); self.rank_combo.show()
        self.save_btn.show(); self.cancel_btn.show()
        self.name_input.setFocus()

    def _save_edit(self):
        n = self.name_input.text().strip()
        r = self.rank_combo.currentText().strip()
        if n:
            self._name = n; self._rank = r
            self.name_label.setText(n); self.rank_label.setText(r)
            self.updated.emit(self.pid, n, r)
        self._cancel_edit()

    def _cancel_edit(self):
        self.name_input.hide(); self.rank_combo.hide()
        self.save_btn.hide(); self.cancel_btn.hide()
        self.name_label.show(); self.rank_label.show(); self.edit_btn.show()


# ============================================================
# 장비 카드 (설정 탭용)
# ============================================================
class EquipmentCard(QFrame):
    deleted_signal = Signal()

    def __init__(self, equipment: Equipment, data_manager: DataManager, parent=None):
        super().__init__(parent)
        self.eq = equipment
        self.dm = data_manager
        self.setMinimumHeight(50)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.setObjectName("equipmentCard")
        self._setup_ui()
        self.update_display()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 8, 10, 8)
        layout.setSpacing(4)

        top_row = QHBoxLayout()
        self.name_label = QLabel(self.eq.name)
        self.name_label.setObjectName("equipmentName")
        top_row.addWidget(self.name_label)
        top_row.addStretch()
        layout.addLayout(top_row)

        self.assignee_label = QLabel("담당자: 미지정")
        self.assignee_label.setObjectName("equipmentCategory")
        layout.addWidget(self.assignee_label)

        btn_row = QHBoxLayout()
        btn_row.setSpacing(4)
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
        if self.eq.assignee_id:
            person = self.dm.get_personnel_by_id(self.eq.assignee_id)
            if person:
                self.assignee_label.setText(f"담당자: {person.name} ({person.rank})")
                return
        self.assignee_label.setText("담당자: 미지정")

    def _on_assignee_changed(self, index):
        pid = self.assign_combo.itemData(index)
        self.dm.assign_equipment(self.eq.id, pid if pid else None)
        self.update_display()

    def _delete(self):
        self.dm.remove_equipment(self.eq.id)
        self.dm.add_log(f"장비 '{self.eq.name}' 삭제")
        self.deleted_signal.emit()
        self.setParent(None)


# ============================================================
# 설정 탭
# ============================================================
class SettingsTab(QWidget):
    data_changed = Signal()

    def __init__(self, data_manager: DataManager, parent=None):
        super().__init__(parent)
        self.dm = data_manager
        self.eq_cards: list[EquipmentCard] = []
        self._setup_ui()
        self.refresh()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 8, 12, 8)
        layout.setSpacing(6)

        # ======== 인원 관리 ========
        layout.addWidget(self._make_title("인원 관리"))

        # 인원 추가 폼
        add_frame = QFrame()
        add_frame.setObjectName("sectionPanel")
        al = QHBoxLayout(add_frame)
        al.setContentsMargins(8, 6, 8, 6)
        al.setSpacing(4)

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

        # 인원 목록 영역 (스크롤)
        self.personnel_scroll = QScrollArea()
        self.personnel_scroll.setWidgetResizable(True)
        self.personnel_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.personnel_scroll.setFrameShape(QFrame.NoFrame)

        self.personnel_content = QWidget()
        self.personnel_content_layout = QVBoxLayout(self.personnel_content)
        self.personnel_content_layout.setContentsMargins(0, 0, 0, 0)
        self.personnel_content_layout.setSpacing(4)

        # 직책 영역 (함장/부장) - 가로 2칸
        self.position_frame = QFrame()
        self.position_frame.setObjectName("sectionPanel")
        pos_layout = QHBoxLayout(self.position_frame)
        pos_layout.setContentsMargins(4, 4, 4, 4)
        pos_layout.setSpacing(4)

        # 함장 컬럼
        self.captain_frame = self._make_dept_column("함장", "#f0a500")
        pos_layout.addWidget(self.captain_frame, 1)

        # 부장 컬럼
        self.vice_frame = self._make_dept_column("부장", "#f0a500")
        pos_layout.addWidget(self.vice_frame, 1)

        self.personnel_content_layout.addWidget(self.position_frame)

        # 팀 영역 (항해/안전/병기/기관) - 가로 4칸
        self.team_frame = QFrame()
        self.team_frame.setObjectName("sectionPanel")
        team_layout = QHBoxLayout(self.team_frame)
        team_layout.setContentsMargins(4, 4, 4, 4)
        team_layout.setSpacing(4)

        self.team_columns = {}
        team_colors = {"항해": "#00d4ff", "안전": "#2ecc71", "병기": "#f39c12", "기관": "#e74c3c"}
        for dept in TEAM_DEPARTMENTS:
            col = self._make_dept_column(dept, team_colors.get(dept, "#00d4ff"))
            team_layout.addWidget(col, 1)
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

        # 단정
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

        # 중국어선
        vf = QFrame()
        vl = QVBoxLayout(vf)
        vl.setContentsMargins(0, 0, 0, 0)
        vl.setSpacing(4)
        vh = QLabel("중국어선")
        vh.setObjectName("sectionTitleVessel")
        vh.setMinimumHeight(28)
        vl.addWidget(vh)
        vr = QHBoxLayout()
        self.vessel_name_input = QLineEdit()
        self.vessel_name_input.setPlaceholderText("어선 이름 (예: 중국어선 C)")
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
        self.eq_list_layout = QVBoxLayout(self.eq_list_widget)
        self.eq_list_layout.setContentsMargins(0, 0, 0, 0)
        self.eq_list_layout.setSpacing(4)
        self.eq_scroll.setWidget(self.eq_list_widget)
        layout.addWidget(self.eq_scroll, 2)

    def _make_title(self, text):
        lbl = QLabel(text)
        lbl.setObjectName("sectionTitle")
        lbl.setMinimumHeight(28)
        return lbl

    def _make_dept_column(self, dept_name: str, color: str) -> QFrame:
        """부서/팀 컬럼 위젯 생성"""
        frame = QFrame()
        frame.setStyleSheet(f"""
            QFrame {{
                background: rgba(13, 31, 60, 0.5);
                border: 1px solid {color}40;
                border-radius: 6px;
            }}
        """)
        col_layout = QVBoxLayout(frame)
        col_layout.setContentsMargins(4, 4, 4, 4)
        col_layout.setSpacing(2)

        header = QLabel(dept_name)
        header.setAlignment(Qt.AlignCenter)
        header.setStyleSheet(f"""
            color: {color}; font-weight: bold; font-size: 12px;
            background: transparent; border: none;
            padding: 2px;
        """)
        col_layout.addWidget(header)

        # 카드 리스트 영역
        list_widget = QWidget()
        list_widget.setStyleSheet("background: transparent; border: none;")
        list_layout = QVBoxLayout(list_widget)
        list_layout.setContentsMargins(0, 0, 0, 0)
        list_layout.setSpacing(2)
        list_layout.addStretch()
        col_layout.addWidget(list_widget, 1)

        # 참조 저장
        frame._list_layout = list_layout
        frame._dept_name = dept_name
        return frame

    # ---- 인원 ----
    def _add_personnel(self):
        name = self.name_input.text().strip()
        if not name:
            return
        dept = self.dept_combo.currentText()
        self.dm.add_personnel(name, self.rank_combo.currentText(), department=dept)
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
        name = f"No. {num} 단정"
        vid = f"patrol_NO{num}"
        if vid in self.dm.vessels:
            return
        self.dm.add_vessel(vid, name, "patrol")
        self._selected_patrol_num = None
        for b in self.patrol_preset_btns:
            b.setChecked(False)
        self.refresh()
        self.data_changed.emit()

    def _add_vessel_type(self, vtype):
        inp = self.vessel_name_input
        name = inp.text().strip()
        if not name:
            return
        inp.clear()
        prefix = "vessel_"
        suffix = name.upper().replace(" ", "-").replace("(", "").replace(")", "")
        vid = f"{prefix}{suffix}"
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

    def _on_equipment_deleted(self):
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

        # 인원을 부서별로 분류
        dept_personnel = {dept: [] for dept in DEPARTMENTS}
        for p in sorted(self.dm.personnel, key=lambda x: RANK_ORDER.get(x.rank, 99)):
            dept = p.department if p.department in DEPARTMENTS else "항해"
            dept_personnel[dept].append(p)

        # 함장 컬럼
        _clear_layout(self.captain_frame._list_layout)
        for p in dept_personnel["함장"]:
            card = PersonnelEditCard(p.id, p.name, p.rank)
            card.removed.connect(self._remove_personnel)
            card.updated.connect(self._update_personnel)
            self.captain_frame._list_layout.addWidget(card)
        self.captain_frame._list_layout.addStretch()

        # 부장 컬럼
        _clear_layout(self.vice_frame._list_layout)
        for p in dept_personnel["부장"]:
            card = PersonnelEditCard(p.id, p.name, p.rank)
            card.removed.connect(self._remove_personnel)
            card.updated.connect(self._update_personnel)
            self.vice_frame._list_layout.addWidget(card)
        self.vice_frame._list_layout.addStretch()

        # 4개 팀 컬럼
        for dept in TEAM_DEPARTMENTS:
            col = self.team_columns[dept]
            _clear_layout(col._list_layout)
            for p in dept_personnel[dept]:
                card = PersonnelEditCard(p.id, p.name, p.rank)
                card.removed.connect(self._remove_personnel)
                card.updated.connect(self._update_personnel)
                col._list_layout.addWidget(card)
            col._list_layout.addStretch()

        # 단정
        _clear_layout(self.patrol_list_layout)
        for vid, vi in sorted(self.dm.vessels.items()):
            if vi["type"] == "patrol":
                self.patrol_list_layout.addWidget(self._create_vessel_row(vid, vi))
        self.patrol_list_layout.addStretch()

        # 중국어선
        _clear_layout(self.vessel_list_layout)
        for vid, vi in sorted(self.dm.vessels.items()):
            if vi["type"] == "vessel":
                self.vessel_list_layout.addWidget(self._create_vessel_row(vid, vi))
        self.vessel_list_layout.addStretch()

        # 장비
        self.eq_cards.clear()
        _clear_layout(self.eq_list_layout)
        for eq in self.dm.equipment:
            card = EquipmentCard(eq, self.dm)
            card.deleted_signal.connect(self._on_equipment_deleted)
            self.eq_cards.append(card)
            self.eq_list_layout.addWidget(card)
        self.eq_list_layout.addStretch()

        self._populate_eq_assignee_combo()

    def _create_vessel_row(self, vid, vinfo):
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

        name_input = QLineEdit(vinfo["name"])
        name_input.setFixedHeight(24)
        name_input.setFixedWidth(120)
        name_input.hide()
        rl.addWidget(name_input)

        edit_btn = QPushButton("수정")
        edit_btn.setFixedSize(50, 24)
        rl.addWidget(edit_btn)

        save_btn = QPushButton("저장")
        save_btn.setObjectName("btnAccent")
        save_btn.setFixedSize(50, 24)
        save_btn.hide()
        rl.addWidget(save_btn)

        cancel_btn = QPushButton("취소")
        cancel_btn.setFixedSize(50, 24)
        cancel_btn.hide()
        rl.addWidget(cancel_btn)

        del_btn = QPushButton("삭제")
        del_btn.setObjectName("btnDanger")
        del_btn.setFixedSize(50, 24)
        del_btn.clicked.connect(lambda c, v=vid: self._remove_vessel(v))
        rl.addWidget(del_btn)

        def start():
            name_label.hide(); count_label.hide(); edit_btn.hide()
            name_input.setText(vinfo["name"]); name_input.show()
            save_btn.show(); cancel_btn.show(); name_input.setFocus()
        def save():
            n = name_input.text().strip()
            if n: self._rename_vessel(vid, n)
        def cancel():
            name_input.hide(); save_btn.hide(); cancel_btn.hide()
            name_label.show(); count_label.show(); edit_btn.show()

        edit_btn.clicked.connect(start)
        save_btn.clicked.connect(save)
        cancel_btn.clicked.connect(cancel)
        return row
