"""
SPT 실시간 로그 패널 - 채팅창 스타일 (클릭으로 액션 표시)
"""
from PySide6.QtWidgets import (
    QWidget, QHBoxLayout, QVBoxLayout, QLabel, QLineEdit,
    QPushButton, QFrame, QScrollArea, QSizePolicy, QApplication,
    QTextEdit
)
from PySide6.QtCore import Qt, Signal
from core.data_manager import DataManager


class LogEntryWidget(QFrame):
    """개별 로그 항목 - 클릭 시 아래에 액션 버튼 표시"""
    deleted = Signal(object)
    edited = Signal(object, str)
    checked_changed = Signal(object, bool)

    def __init__(self, log_entry: dict, parent=None):
        super().__init__(parent)
        self.log_entry = log_entry
        self._editing = False
        self._actions_visible = False
        self._checked = log_entry.get("checked", False)
        self.setObjectName("logEntry")
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Minimum)
        self.setMinimumHeight(26)
        self.setCursor(Qt.PointingHandCursor)
        self._setup_ui()

    def _setup_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(6, 3, 6, 3)
        main_layout.setSpacing(2)

        msg = self.log_entry.get("message", "")
        time_str = self.log_entry.get("time_str", "")
        is_memo = self.log_entry.get("type") == "memo"

        # 본문 행
        content_row = QHBoxLayout()
        content_row.setSpacing(4)

        # 시간 라벨
        self.time_label = QLabel(f'[{time_str}]')
        self.time_label.setMinimumWidth(62)
        self.time_label.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Minimum)
        if self._checked:
            self.time_label.setObjectName("logTimeChecked")
        else:
            self.time_label.setObjectName("logTime")
        self.time_label.setStyleSheet(self.time_label.styleSheet())
        content_row.addWidget(self.time_label, 0, Qt.AlignTop)

        # 메시지 라벨
        prefix = "[메모] " if is_memo else ""
        self.text_label = QLabel(f'{prefix}{msg}')
        if is_memo:
            self.text_label.setObjectName("logEntryMemo")
        else:
            self.text_label.setObjectName("logEntryText")
        self.text_label.setWordWrap(True)
        self.text_label.setTextInteractionFlags(Qt.TextSelectableByMouse)
        self.text_label.setMinimumWidth(50)
        self.text_label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Minimum)
        content_row.addWidget(self.text_label, 1)

        main_layout.addLayout(content_row)

        # 수정용 입력 (숨김)
        self.edit_input = QLineEdit(msg)
        self.edit_input.setObjectName("logEditInput")
        self.edit_input.setFixedHeight(24)
        self.edit_input.hide()
        self.edit_input.returnPressed.connect(self._save_edit)
        main_layout.addWidget(self.edit_input)

        # 액션 버튼 행 (숨김, 클릭 시 표시)
        self.action_frame = QFrame()
        self.action_frame.setObjectName("logActionFrame")
        action_layout = QHBoxLayout(self.action_frame)
        action_layout.setContentsMargins(62, 0, 0, 0)
        action_layout.setSpacing(4)

        self.check_btn = QPushButton("✓ 체크")
        self.check_btn.setObjectName("logCheckBtn" if not self._checked else "logCheckBtnActive")
        self.check_btn.setFixedHeight(22)
        self.check_btn.setFixedWidth(56)
        self.check_btn.clicked.connect(self._toggle_check)
        action_layout.addWidget(self.check_btn)

        copy_btn = QPushButton("복사")
        copy_btn.setObjectName("logActionBtn")
        copy_btn.setFixedHeight(22)
        copy_btn.setFixedWidth(40)
        copy_btn.clicked.connect(self._copy)
        action_layout.addWidget(copy_btn)

        edit_btn = QPushButton("수정")
        edit_btn.setObjectName("logActionBtn")
        edit_btn.setFixedHeight(22)
        edit_btn.setFixedWidth(40)
        edit_btn.clicked.connect(self._start_edit)
        action_layout.addWidget(edit_btn)

        del_btn = QPushButton("삭제")
        del_btn.setObjectName("logActionBtnDanger")
        del_btn.setFixedHeight(22)
        del_btn.setFixedWidth(40)
        del_btn.clicked.connect(lambda: self.deleted.emit(self.log_entry))
        action_layout.addWidget(del_btn)

        action_layout.addStretch()
        self.action_frame.hide()
        main_layout.addWidget(self.action_frame)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton and not self._editing:
            self._toggle_actions()
        super().mousePressEvent(event)

    def _toggle_actions(self):
        self._actions_visible = not self._actions_visible
        if self._actions_visible:
            self.action_frame.show()
        else:
            self.action_frame.hide()

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
        self.action_frame.hide()
        self._actions_visible = False

    def _save_edit(self):
        new_msg = self.edit_input.text().strip()
        if new_msg:
            self.edited.emit(self.log_entry, new_msg)
            is_memo = self.log_entry.get("type") == "memo"
            prefix = "[메모] " if is_memo else ""
            self.text_label.setText(f'{prefix}{new_msg}')
        self._editing = False
        self.edit_input.hide()
        self.text_label.show()

    def _toggle_check(self):
        self._checked = not self._checked
        self.log_entry["checked"] = self._checked
        self.checked_changed.emit(self.log_entry, self._checked)
        if self._checked:
            self.time_label.setObjectName("logTimeChecked")
            self.check_btn.setObjectName("logCheckBtnActive")
        else:
            self.time_label.setObjectName("logTime")
            self.check_btn.setObjectName("logCheckBtn")
        self.time_label.setStyleSheet(self.time_label.styleSheet())
        self.check_btn.setStyleSheet(self.check_btn.styleSheet())


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

        # 하단 메모 입력 영역 (4줄 이상)
        input_frame = QFrame()
        input_frame.setObjectName("logInputFrame")
        input_layout = QHBoxLayout(input_frame)
        input_layout.setContentsMargins(6, 4, 6, 4)
        input_layout.setSpacing(4)

        self.memo_input = QTextEdit()
        self.memo_input.setObjectName("memoInput")
        self.memo_input.setPlaceholderText("메모 입력 후 Ctrl+Enter로 전송...")
        self.memo_input.setFixedHeight(80)
        self.memo_input.setAcceptRichText(False)
        input_layout.addWidget(self.memo_input)

        send_btn = QPushButton("입력")
        send_btn.setObjectName("btnAccent")
        send_btn.setFixedHeight(80)
        send_btn.setFixedWidth(50)
        send_btn.clicked.connect(self._add_memo)
        input_layout.addWidget(send_btn)

        layout.addWidget(input_frame)

        # Ctrl+Enter 전송
        self.memo_input.installEventFilter(self)

    def eventFilter(self, obj, event):
        if obj == self.memo_input and event.type() == event.Type.KeyPress:
            if event.key() in (Qt.Key_Return, Qt.Key_Enter):
                if event.modifiers() & Qt.ControlModifier:
                    self._add_memo()
                    return True
        return super().eventFilter(obj, event)

    def _load_existing_logs(self):
        for log in self.dm.logs:
            self._add_entry_widget(log)
        self._scroll_to_bottom()

    def _add_entry_widget(self, log_entry: dict):
        widget = LogEntryWidget(log_entry)
        widget.deleted.connect(self._on_delete)
        widget.edited.connect(self._on_edit)
        widget.checked_changed.connect(self._on_checked)
        self.entry_widgets.append(widget)
        idx = self.log_layout.count() - 1
        self.log_layout.insertWidget(idx, widget)

    def append_log(self, message: str):
        if self.dm.logs:
            last_log = self.dm.logs[-1]
            if not self.entry_widgets or self.entry_widgets[-1].log_entry is not last_log:
                self._add_entry_widget(last_log)
        self._scroll_to_bottom()

    def _add_memo(self):
        text = self.memo_input.toPlainText().strip()
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

    def _on_checked(self, log_entry, checked):
        self.dm.save()

    def _rebuild_entries(self):
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
        from PySide6.QtCore import QTimer
        QTimer.singleShot(50, lambda: self.scroll.verticalScrollBar().setValue(
            self.scroll.verticalScrollBar().maximum()
        ))
