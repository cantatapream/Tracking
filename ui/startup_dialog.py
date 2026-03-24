"""
SPT 시작 대화상자 - 새 작전 / 과거 작전 열기
"""
import time
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QFrame, QScrollArea, QWidget, QSizePolicy
)
from PySide6.QtCore import Qt
from core.data_manager import DataManager


class OperationListItem(QFrame):
    """과거 작전 항목"""
    def __init__(self, op_info: dict, parent=None):
        super().__init__(parent)
        self.op_info = op_info
        self.filepath = op_info["filepath"]
        self._selected = False
        self.setObjectName("opListItem")
        self.setCursor(Qt.PointingHandCursor)
        self.setFixedHeight(60)
        self._setup_ui()

    def _setup_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 8, 12, 8)
        layout.setSpacing(8)

        # 좌측: 날짜 + 제목
        info_layout = QVBoxLayout()
        info_layout.setSpacing(2)

        # 생성 시간
        created = self.op_info.get("created_at", self.op_info.get("last_saved", 0))
        if created:
            date_str = time.strftime("%Y.%m.%d  %H:%M", time.localtime(created))
        else:
            date_str = "날짜 미상"
        date_label = QLabel(date_str)
        date_label.setStyleSheet(
            "color: #5a7a9a; font-size: 11px; background: transparent; border: none;"
        )
        info_layout.addWidget(date_label)

        # 제목
        title = self.op_info.get("title", "제목 없음")
        if not title:
            title = "제목 없음"
        title_label = QLabel(title)
        title_label.setStyleSheet(
            "color: #c8d6e5; font-size: 14px; font-weight: bold; "
            "background: transparent; border: none;"
        )
        info_layout.addWidget(title_label)

        layout.addLayout(info_layout, 1)

        # 우측: 삭제 버튼
        self.del_btn = QPushButton("삭제")
        self.del_btn.setObjectName("btnDanger")
        self.del_btn.setFixedSize(50, 28)
        layout.addWidget(self.del_btn)


class PastOperationsDialog(QDialog):
    """과거 작전 열기 대화상자"""
    def __init__(self, data_manager: DataManager, parent=None):
        super().__init__(parent)
        self.dm = data_manager
        self.selected_filepath = None
        self.setWindowTitle("과거 작전 열기")
        self.setFixedSize(500, 500)
        self._setup_ui()
        self._load_list()

    def _setup_ui(self):
        self.setStyleSheet("""
            QDialog {
                background: #0a1628;
            }
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(12)

        title = QLabel("과거 작전 열기")
        title.setAlignment(Qt.AlignCenter)
        title.setStyleSheet(
            "color: #00d4ff; font-size: 18px; font-weight: bold; "
            "letter-spacing: 2px;"
        )
        layout.addWidget(title)

        # 스크롤 영역
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll.setFrameShape(QFrame.NoFrame)

        self.list_widget = QWidget()
        self.list_layout = QVBoxLayout(self.list_widget)
        self.list_layout.setContentsMargins(0, 0, 0, 0)
        self.list_layout.setSpacing(4)
        self.list_layout.addStretch()

        scroll.setWidget(self.list_widget)
        layout.addWidget(scroll, 1)

        # 하단 버튼
        btn_row = QHBoxLayout()
        btn_row.addStretch()

        cancel_btn = QPushButton("취소")
        cancel_btn.setFixedSize(80, 36)
        cancel_btn.clicked.connect(self.reject)
        btn_row.addWidget(cancel_btn)

        layout.addLayout(btn_row)

    def _load_list(self):
        # 기존 항목 제거
        while self.list_layout.count():
            item = self.list_layout.takeAt(0)
            if item.widget():
                item.widget().setParent(None)
                item.widget().deleteLater()

        ops = self.dm.list_operations()

        if not ops:
            empty = QLabel("저장된 작전이 없습니다.")
            empty.setAlignment(Qt.AlignCenter)
            empty.setStyleSheet("color: #5a7a9a; font-size: 13px; padding: 40px;")
            self.list_layout.addWidget(empty)
        else:
            for op in ops:
                item = OperationListItem(op)
                item.mousePressEvent = lambda e, f=op["filepath"]: self._select_op(f)
                item.del_btn.clicked.connect(
                    lambda checked, f=op["filepath"]: self._delete_op(f)
                )
                self.list_layout.addWidget(item)

        self.list_layout.addStretch()

    def _select_op(self, filepath):
        self.selected_filepath = filepath
        self.accept()

    def _delete_op(self, filepath):
        self.dm.delete_operation(filepath)
        self._load_list()


class StartupDialog(QDialog):
    """시작 대화상자 - 새 작전 / 과거 작전 열기"""
    def __init__(self, data_manager: DataManager, parent=None):
        super().__init__(parent)
        self.dm = data_manager
        self.result_action = None  # "new" or "load"
        self.setWindowTitle("작전 현황")
        self.setFixedSize(400, 300)
        self.setWindowFlags(Qt.Dialog | Qt.WindowTitleHint)
        self._setup_ui()

    def _setup_ui(self):
        self.setStyleSheet("""
            QDialog {
                background: #0a1628;
                border: 1px solid #1a2d4a;
            }
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(40, 40, 40, 40)
        layout.setSpacing(20)

        # 제목
        title = QLabel("작전 현황")
        title.setAlignment(Qt.AlignCenter)
        title.setStyleSheet(
            "color: #00d4ff; font-size: 22px; font-weight: bold; "
            "letter-spacing: 4px;"
        )
        layout.addWidget(title)

        layout.addStretch()

        # 새 작전 버튼
        new_btn = QPushButton("새로운 작전")
        new_btn.setFixedHeight(48)
        new_btn.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #005577, stop:1 #004466);
                border: 1px solid #0088aa;
                color: #00d4ff;
                border-radius: 8px;
                font-size: 15px;
                font-weight: bold;
            }
            QPushButton:hover {
                background: #006688;
                border-color: #00d4ff;
            }
        """)
        new_btn.clicked.connect(self._new_operation)
        layout.addWidget(new_btn)

        # 과거 작전 열기 버튼
        load_btn = QPushButton("과거 작전 열기")
        load_btn.setFixedHeight(48)
        load_btn.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #1e3a5f, stop:1 #152d4a);
                border: 1px solid #2a4a6f;
                color: #c8d6e5;
                border-radius: 8px;
                font-size: 15px;
                font-weight: bold;
            }
            QPushButton:hover {
                background: #2a4a6f;
                border-color: #00d4ff;
                color: #00d4ff;
            }
        """)
        load_btn.clicked.connect(self._load_operation)
        layout.addWidget(load_btn)

        layout.addStretch()

    def _new_operation(self):
        self.result_action = "new"
        self.accept()

    def _load_operation(self):
        dialog = PastOperationsDialog(self.dm, self)
        if dialog.exec() == QDialog.Accepted and dialog.selected_filepath:
            self.dm.load_operation(dialog.selected_filepath)
            self.result_action = "load"
            self.accept()
