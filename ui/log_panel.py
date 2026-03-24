"""
SPT 실시간 로그 및 메모 패널
"""
from PySide6.QtWidgets import (
    QWidget, QHBoxLayout, QVBoxLayout, QLabel, QTextEdit, QLineEdit,
    QPushButton, QFrame, QSplitter
)
from PySide6.QtCore import Qt, Signal
from core.data_manager import DataManager


class LogPanel(QWidget):
    """하단 로그 + 메모 패널"""

    def __init__(self, data_manager: DataManager, parent=None):
        super().__init__(parent)
        self.dm = data_manager
        self.setObjectName("logPanel")
        self.setFixedHeight(180)
        self._setup_ui()
        self._load_existing_logs()

    def _setup_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(8, 6, 8, 6)
        layout.setSpacing(8)

        # === 좌측: 실시간 작전 로그 ===
        log_frame = QFrame()
        log_frame.setObjectName("sectionPanel")
        log_layout = QVBoxLayout(log_frame)
        log_layout.setContentsMargins(8, 6, 8, 6)
        log_layout.setSpacing(4)

        log_title = QLabel("  실시간 작전 로그 (OPERATION LOG)")
        log_title.setObjectName("sectionTitle")
        log_title.setFixedHeight(28)
        log_layout.addWidget(log_title)

        self.log_text = QTextEdit()
        self.log_text.setObjectName("logTextArea")
        self.log_text.setReadOnly(True)
        log_layout.addWidget(self.log_text)

        layout.addWidget(log_frame, 3)

        # === 우측: 메모 ===
        memo_frame = QFrame()
        memo_frame.setObjectName("sectionPanel")
        memo_layout = QVBoxLayout(memo_frame)
        memo_layout.setContentsMargins(8, 6, 8, 6)
        memo_layout.setSpacing(4)

        memo_title = QLabel("  메모 (MEMO)")
        memo_title.setObjectName("sectionTitle")
        memo_title.setFixedHeight(28)
        memo_layout.addWidget(memo_title)

        self.memo_text = QTextEdit()
        self.memo_text.setObjectName("logTextArea")
        self.memo_text.setReadOnly(True)
        memo_layout.addWidget(self.memo_text)

        # 메모 입력
        input_row = QHBoxLayout()
        self.memo_input = QLineEdit()
        self.memo_input.setObjectName("memoInput")
        self.memo_input.setPlaceholderText("메모 입력 후 Enter...")
        self.memo_input.setFixedHeight(32)
        self.memo_input.returnPressed.connect(self._add_memo)
        input_row.addWidget(self.memo_input)

        send_btn = QPushButton("입력")
        send_btn.setObjectName("btnAccent")
        send_btn.setFixedHeight(32)
        send_btn.setFixedWidth(60)
        send_btn.clicked.connect(self._add_memo)
        input_row.addWidget(send_btn)

        memo_layout.addLayout(input_row)
        layout.addWidget(memo_frame, 2)

    def _load_existing_logs(self):
        """기존 로그/메모 불러오기"""
        for log in self.dm.logs:
            self.log_text.append(f'[{log["time_str"]}] {log["message"]}')
        for memo in self.dm.memos:
            self.memo_text.append(f'[{memo["time_str"]}] {memo["text"]}')

    def append_log(self, message: str):
        """로그 추가"""
        import time
        time_str = time.strftime("%H:%M:%S")
        self.log_text.append(f'[{time_str}] {message}')
        # 스크롤을 하단으로
        scrollbar = self.log_text.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())

    def _add_memo(self):
        text = self.memo_input.text().strip()
        if not text:
            return
        entry = self.dm.add_memo(text)
        self.memo_text.append(f'[{entry["time_str"]}] {entry["text"]}')
        self.memo_input.clear()
        scrollbar = self.memo_text.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())
