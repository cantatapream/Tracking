"""
SPT 실시간 로그 패널 - 채팅창 스타일 (세로 배치)
"""
from PySide6.QtWidgets import (
    QWidget, QHBoxLayout, QVBoxLayout, QLabel, QLineEdit,
    QPushButton, QFrame, QScrollArea, QSizePolicy, QApplication
)
from PySide6.QtCore import Qt, Signal
from core.data_manager import DataManager


class LogEntryWidget(QFrame):
    """개별 로그 항목 위젯 - 호버 시 복사/수정/삭제 버튼 표시"""
    deleted = Signal(object)  # log_entry dict
    edited = Signal(object, str)  # log_entry dict, new_message

    def __init__(self, log_entry: dict, parent=None):
        super().__init__(parent)
        self.log_entry = log_entry
        self._editing = False
        self.setObjectName("logEntry")
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.setMinimumHeight(26)
        self._setup_ui()

    def _setup_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(6, 2, 6, 2)
        layout.setSpacing(4)

        msg = self.log_entry.get("message", "")
        time_str = self.log_entry.get("time_str", "")
        is_memo = self.log_entry.get("type") == "memo"

        prefix = "[메모] " if is_memo else ""
        self.text_label = QLabel(f'[{time_str}] {prefix}{msg}')
        if is_memo:
            self.text_label.setObjectName("logEntryMemo")
        else:
            self.text_label.setObjectName("logEntryText")
        self.text_label.setWordWrap(True)
        layout.addWidget(self.text_label, 1)

        # 수정용 입력 (평소 숨김)
        self.edit_input = QLineEdit(msg)
        self.edit_input.setObjectName("logEditInput")
        self.edit_input.setFixedHeight(22)
        self.edit_input.hide()
        self.edit_input.returnPressed.connect(self._save_edit)
        layout.addWidget(self.edit_input, 1)

        # 액션 버튼 (평소 숨김, 호버 시 표시)
        self.btn_frame = QWidget()
        self.btn_frame.setObjectName("logActionFrame")
        btn_layout = QHBoxLayout(self.btn_frame)
        btn_layout.setContentsMargins(0, 0, 0, 0)
        btn_layout.setSpacing(2)

        self.copy_btn = QPushButton("복사")
        self.copy_btn.setObjectName("logActionBtn")
        self.copy_btn.setFixedSize(34, 20)
        self.copy_btn.clicked.connect(self._copy)
        btn_layout.addWidget(self.copy_btn)

        self.edit_btn = QPushButton("수정")
        self.edit_btn.setObjectName("logActionBtn")
        self.edit_btn.setFixedSize(34, 20)
        self.edit_btn.clicked.connect(self._start_edit)
        btn_layout.addWidget(self.edit_btn)

        self.del_btn = QPushButton("삭제")
        self.del_btn.setObjectName("logActionBtnDanger")
        self.del_btn.setFixedSize(34, 20)
        self.del_btn.clicked.connect(lambda: self.deleted.emit(self.log_entry))
        btn_layout.addWidget(self.del_btn)

        self.btn_frame.hide()
        layout.addWidget(self.btn_frame)

    def enterEvent(self, event):
        if not self._editing:
            self.btn_frame.show()
        super().enterEvent(event)

    def leaveEvent(self, event):
        if not self._editing:
            self.btn_frame.hide()
        super().leaveEvent(event)

    def _copy(self):
        clipboard = QApplication.clipboard()
        msg = self.log_entry.get("message", "")
        clipboard.setText(f'[{self.log_entry.get("time_str", "")}] {msg}')

    def _start_edit(self):
        self._editing = True
        self.text_label.hide()
        self.edit_input.setText(self.log_entry.get("message", ""))
        self.edit_input.show()
        self.edit_input.setFocus()
        self.btn_frame.hide()

    def _save_edit(self):
        new_msg = self.edit_input.text().strip()
        if new_msg:
            self.edited.emit(self.log_entry, new_msg)
            is_memo = self.log_entry.get("type") == "memo"
            prefix = "[메모] " if is_memo else ""
            time_str = self.log_entry.get("time_str", "")
            self.text_label.setText(f'[{time_str}] {prefix}{new_msg}')
        self._editing = False
        self.edit_input.hide()
        self.text_label.show()


class LogPanel(QWidget):
    """세로형 로그 패널 - 채팅창 스타일"""

    def __init__(self, data_manager: DataManager, parent=None):
        super().__init__(parent)
        self.dm = data_manager
        self.entry_widgets: list[LogEntryWidget] = []
        self.setObjectName("logPanelVertical")
        self._setup_ui()
        self._load_existing_logs()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # 제목
        title_label = QLabel("  작전 로그 (OPERATION LOG)")
        title_label.setObjectName("sectionTitle")
        title_label.setFixedHeight(36)
        layout.addWidget(title_label)

        # 스크롤 가능한 로그 영역
        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.scroll.setFrameShape(QFrame.NoFrame)

        self.log_container = QWidget()
        self.log_layout = QVBoxLayout(self.log_container)
        self.log_layout.setContentsMargins(4, 4, 4, 4)
        self.log_layout.setSpacing(2)
        self.log_layout.addStretch()

        self.scroll.setWidget(self.log_container)
        layout.addWidget(self.scroll, 1)

        # 하단 메모 입력 영역
        input_frame = QFrame()
        input_frame.setObjectName("logInputFrame")
        input_layout = QHBoxLayout(input_frame)
        input_layout.setContentsMargins(6, 4, 6, 4)
        input_layout.setSpacing(4)

        self.memo_input = QLineEdit()
        self.memo_input.setObjectName("memoInput")
        self.memo_input.setPlaceholderText("메모 입력 후 Enter...")
        self.memo_input.setFixedHeight(32)
        self.memo_input.returnPressed.connect(self._add_memo)
        input_layout.addWidget(self.memo_input)

        send_btn = QPushButton("입력")
        send_btn.setObjectName("btnAccent")
        send_btn.setFixedHeight(32)
        send_btn.setFixedWidth(50)
        send_btn.clicked.connect(self._add_memo)
        input_layout.addWidget(send_btn)

        layout.addWidget(input_frame)

    def _load_existing_logs(self):
        """기존 로그 불러오기"""
        for log in self.dm.logs:
            self._add_entry_widget(log)
        self._scroll_to_bottom()

    def _add_entry_widget(self, log_entry: dict):
        """로그 항목 위젯 추가"""
        widget = LogEntryWidget(log_entry)
        widget.deleted.connect(self._on_delete)
        widget.edited.connect(self._on_edit)
        self.entry_widgets.append(widget)
        # stretch 앞에 삽입
        idx = self.log_layout.count() - 1  # stretch 위치
        self.log_layout.insertWidget(idx, widget)

    def append_log(self, message: str):
        """새 로그 추가 (외부에서 호출)"""
        # dm.add_log는 이미 호출된 상태이므로, 마지막 로그 항목을 위젯으로 추가
        if self.dm.logs:
            last_log = self.dm.logs[-1]
            # 이미 위젯이 있는지 확인
            if not self.entry_widgets or self.entry_widgets[-1].log_entry is not last_log:
                self._add_entry_widget(last_log)
        self._scroll_to_bottom()

    def _add_memo(self):
        text = self.memo_input.text().strip()
        if not text:
            return
        entry = self.dm.add_memo(text)
        self._add_entry_widget(entry)
        self.memo_input.clear()
        self._scroll_to_bottom()

    def _on_delete(self, log_entry):
        self.dm.delete_log(log_entry)
        self._rebuild_entries()

    def _on_edit(self, log_entry, new_msg):
        self.dm.edit_log(log_entry, new_msg)

    def _rebuild_entries(self):
        """전체 로그 항목 다시 구성"""
        for w in self.entry_widgets:
            w.setParent(None)
            w.deleteLater()
        self.entry_widgets.clear()

        while self.log_layout.count():
            item = self.log_layout.takeAt(0)
            if item.widget():
                item.widget().setParent(None)

        self.log_layout.addStretch()
        for log in self.dm.logs:
            self._add_entry_widget(log)
        self._scroll_to_bottom()

    def _scroll_to_bottom(self):
        """스크롤을 맨 아래로"""
        from PySide6.QtCore import QTimer
        QTimer.singleShot(50, lambda: self.scroll.verticalScrollBar().setValue(
            self.scroll.verticalScrollBar().maximum()
        ))
