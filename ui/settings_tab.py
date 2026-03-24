"""
SPT 설정 탭 - 인원 등록, 선박 관리
"""
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton,
    QComboBox, QScrollArea, QFrame, QGridLayout, QMessageBox, QSizePolicy
)
from PySide6.QtCore import Qt, Signal
from core.data_manager import DataManager


class PersonnelEditCard(QFrame):
    """인원 편집 카드"""
    removed = Signal(str)

    def __init__(self, pid: str, name: str, rank: str, parent=None):
        super().__init__(parent)
        self.pid = pid
        self.setObjectName("personnelCard")
        self.setFixedHeight(48)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(10, 4, 10, 4)
        layout.setSpacing(8)

        id_label = QLabel(pid)
        id_label.setObjectName("cardRank")
        id_label.setFixedWidth(50)
        layout.addWidget(id_label)

        name_label = QLabel(name)
        name_label.setObjectName("cardName")
        layout.addWidget(name_label)

        rank_label = QLabel(rank)
        rank_label.setObjectName("cardRank")
        layout.addWidget(rank_label)

        layout.addStretch()

        del_btn = QPushButton("삭제")
        del_btn.setObjectName("btnDanger")
        del_btn.setFixedSize(60, 28)
        del_btn.clicked.connect(lambda: self.removed.emit(self.pid))
        layout.addWidget(del_btn)


class SettingsTab(QWidget):
    """설정 탭 - 인원 사전 등록 + 선박 관리"""
    data_changed = Signal()

    def __init__(self, data_manager: DataManager, parent=None):
        super().__init__(parent)
        self.dm = data_manager
        self._setup_ui()
        self.refresh()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(16)

        # === 인원 등록 ===
        personnel_title = QLabel("인원 사전 등록")
        personnel_title.setObjectName("sectionTitle")
        personnel_title.setFixedHeight(36)
        layout.addWidget(personnel_title)

        add_frame = QFrame()
        add_frame.setObjectName("sectionPanel")
        add_layout = QHBoxLayout(add_frame)
        add_layout.setContentsMargins(12, 10, 12, 10)
        add_layout.setSpacing(8)

        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText("이름")
        self.name_input.setFixedHeight(36)
        add_layout.addWidget(self.name_input, 2)

        self.rank_combo = QComboBox()
        self.rank_combo.setFixedHeight(36)
        self.rank_combo.addItems([
            "경정", "경감", "경위", "경장", "순경", "상사", "중사", "하사",
            "소위", "중위", "대위", "소령", "중령"
        ])
        self.rank_combo.setEditable(True)
        add_layout.addWidget(self.rank_combo, 1)

        add_btn = QPushButton("인원 추가")
        add_btn.setObjectName("btnAccent")
        add_btn.setFixedHeight(36)
        add_btn.clicked.connect(self._add_personnel)
        add_layout.addWidget(add_btn)

        layout.addWidget(add_frame)

        # 인원 목록
        self.personnel_scroll = QScrollArea()
        self.personnel_scroll.setWidgetResizable(True)
        self.personnel_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.personnel_scroll.setFrameShape(QFrame.NoFrame)

        self.personnel_list_widget = QWidget()
        self.personnel_list_layout = QVBoxLayout(self.personnel_list_widget)
        self.personnel_list_layout.setContentsMargins(0, 0, 0, 0)
        self.personnel_list_layout.setSpacing(4)
        self.personnel_list_layout.addStretch()

        self.personnel_scroll.setWidget(self.personnel_list_widget)
        layout.addWidget(self.personnel_scroll, 2)

        # === 선박 관리 ===
        vessel_title = QLabel("선박 관리 (단정/어선 추가·삭제)")
        vessel_title.setObjectName("sectionTitle")
        vessel_title.setFixedHeight(36)
        layout.addWidget(vessel_title)

        vessel_frame = QFrame()
        vessel_frame.setObjectName("sectionPanel")
        vessel_layout = QHBoxLayout(vessel_frame)
        vessel_layout.setContentsMargins(12, 10, 12, 10)
        vessel_layout.setSpacing(8)

        self.vessel_name_input = QLineEdit()
        self.vessel_name_input.setPlaceholderText("선박 이름 (예: 단정 5호)")
        self.vessel_name_input.setFixedHeight(36)
        vessel_layout.addWidget(self.vessel_name_input, 2)

        self.vessel_type_combo = QComboBox()
        self.vessel_type_combo.setFixedHeight(36)
        self.vessel_type_combo.addItem("단정 (Patrol)", "patrol")
        self.vessel_type_combo.addItem("중국어선 (Vessel)", "vessel")
        vessel_layout.addWidget(self.vessel_type_combo, 1)

        vessel_add_btn = QPushButton("선박 추가")
        vessel_add_btn.setObjectName("btnAccent")
        vessel_add_btn.setFixedHeight(36)
        vessel_add_btn.clicked.connect(self._add_vessel)
        vessel_layout.addWidget(vessel_add_btn)

        layout.addWidget(vessel_frame)

        # 선박 목록
        self.vessel_scroll = QScrollArea()
        self.vessel_scroll.setWidgetResizable(True)
        self.vessel_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.vessel_scroll.setFrameShape(QFrame.NoFrame)

        self.vessel_list_widget = QWidget()
        self.vessel_list_layout = QVBoxLayout(self.vessel_list_widget)
        self.vessel_list_layout.setContentsMargins(0, 0, 0, 0)
        self.vessel_list_layout.setSpacing(4)
        self.vessel_list_layout.addStretch()

        self.vessel_scroll.setWidget(self.vessel_list_widget)
        layout.addWidget(self.vessel_scroll, 1)

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

    def _add_vessel(self):
        name = self.vessel_name_input.text().strip()
        if not name:
            return
        vtype = self.vessel_type_combo.currentData()
        # ID 생성
        prefix = "patrol_" if vtype == "patrol" else "vessel_"
        existing = [v for v in self.dm.vessels if v.startswith(prefix)]
        suffix = name.upper().replace(" ", "-").replace("(", "").replace(")", "")
        vid = f"{prefix}{suffix}"
        # 중복 방지
        counter = 1
        base_vid = vid
        while vid in self.dm.vessels:
            vid = f"{base_vid}-{counter}"
            counter += 1

        self.dm.add_vessel(vid, name, vtype)
        self.vessel_name_input.clear()
        self.refresh()
        self.data_changed.emit()

    def _remove_vessel(self, vid: str):
        self.dm.remove_vessel(vid)
        self.refresh()
        self.data_changed.emit()

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
            self.personnel_list_layout.addWidget(card)
        self.personnel_list_layout.addStretch()

        # 선박 목록 갱신
        while self.vessel_list_layout.count():
            item = self.vessel_list_layout.takeAt(0)
            if item.widget():
                item.widget().setParent(None)
                item.widget().deleteLater()

        for vid, vinfo in sorted(self.dm.vessels.items()):
            if vid == "base":
                continue  # 본함은 삭제 불가
            row = QFrame()
            row.setObjectName("personnelCard")
            row.setFixedHeight(44)
            row_layout = QHBoxLayout(row)
            row_layout.setContentsMargins(10, 4, 10, 4)
            row_layout.setSpacing(8)

            type_label = QLabel("단정" if vinfo["type"] == "patrol" else "어선")
            type_label.setObjectName("cardRank")
            type_label.setFixedWidth(40)
            row_layout.addWidget(type_label)

            name_label = QLabel(vinfo["name"])
            name_label.setObjectName("cardName")
            row_layout.addWidget(name_label)

            row_layout.addStretch()

            count = len(self.dm.get_personnel_at(vid))
            count_label = QLabel(f"{count}명 탑승")
            count_label.setObjectName("cardRank")
            row_layout.addWidget(count_label)

            del_btn = QPushButton("삭제")
            del_btn.setObjectName("btnDanger")
            del_btn.setFixedSize(60, 28)
            del_btn.clicked.connect(lambda checked, v=vid: self._remove_vessel(v))
            row_layout.addWidget(del_btn)

            self.vessel_list_layout.addWidget(row)
        self.vessel_list_layout.addStretch()
