"""
SPT 실시간 로그 패널 - 채팅창 스타일 (클릭으로 액션 표시, Shift+클릭 다중 선택)
"""
import re
import html as html_mod
from PySide6.QtWidgets import (
    QWidget, QHBoxLayout, QVBoxLayout, QLabel, QLineEdit,
    QPushButton, QFrame, QScrollArea, QSizePolicy, QApplication,
    QTextEdit
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QWheelEvent, QKeyEvent
from core.data_manager import DataManager

# 로그 텍스트 폰트 크기 (전역, Ctrl+휠로 조절)
_log_font_size = 11


def _wrap_html(text: str, font_size: int = None) -> str:
    """HTML로 감싸서 word-break: break-all 적용"""
    sz = font_size or _log_font_size
    escaped = html_mod.escape(text)
    return f'<div style="word-break:break-all;white-space:pre-wrap;font-size:{sz}px;">{escaped}</div>'


class LogEntryWidget(QFrame):
    """개별 로그 항목 - 클릭 시 아래에 액션 버튼 표시"""
    deleted = Signal(object)
    edited = Signal(object, str)
    checked_changed = Signal(object, bool)
    actions_opened = Signal(object)
    entry_clicked = Signal(object, object)  # (widget, QMouseEvent) - LogPanel에서 처리

    def __init__(self, log_entry: dict, parent=None):
        super().__init__(parent)
        self.log_entry = log_entry
        self._editing = False
        self._actions_visible = False
        self._confirm_delete = False
        self._checked = log_entry.get("checked", False)
        self._multi_selected = False
        self.setObjectName("logEntryChecked" if self._checked else "logEntry")
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

        # 시간 라벨 (위) - 메모인 경우 [메모] 표시
        time_text = f'[{time_str}]'
        if is_memo:
            time_text = f'[{time_str}] [메모]'
        self.time_label = QLabel(time_text)
        self.time_label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Minimum)
        if self._checked:
            self.time_label.setObjectName("logTimeChecked")
        else:
            self.time_label.setObjectName("logTimeMemo" if is_memo else "logTime")
        self.time_label.setStyleSheet(self.time_label.styleSheet())
        main_layout.addWidget(self.time_label)

        # 메시지 라벨 (아래) - Rich text로 word-break:break-all 적용
        self.text_label = QLabel()
        self.text_label.setTextFormat(Qt.RichText)
        self.text_label.setText(_wrap_html(msg))
        if is_memo:
            self.text_label.setObjectName("logEntryMemo")
        else:
            self.text_label.setObjectName("logEntryText")
        self.text_label.setWordWrap(True)
        self.text_label.setMinimumWidth(50)
        self.text_label.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Minimum)
        main_layout.addWidget(self.text_label)

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
        action_layout.setContentsMargins(0, 0, 0, 0)
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
        del_btn.clicked.connect(self._request_delete)
        action_layout.addWidget(del_btn)

        action_layout.addStretch()
        self.action_frame.hide()
        main_layout.addWidget(self.action_frame)

        # 삭제 확인 프레임 (숨김)
        self.confirm_frame = QFrame()
        self.confirm_frame.setObjectName("logActionFrame")
        confirm_layout = QHBoxLayout(self.confirm_frame)
        confirm_layout.setContentsMargins(0, 0, 0, 0)
        confirm_layout.setSpacing(4)

        confirm_label = QLabel("정말 삭제하시겠습니까?")
        confirm_label.setStyleSheet("color: #e74c3c; font-size: 11px; font-weight: bold;")
        confirm_layout.addWidget(confirm_label)

        yes_btn = QPushButton("확인")
        yes_btn.setObjectName("logActionBtnDanger")
        yes_btn.setFixedHeight(22)
        yes_btn.setFixedWidth(40)
        yes_btn.clicked.connect(self._confirm_delete_action)
        confirm_layout.addWidget(yes_btn)

        no_btn = QPushButton("취소")
        no_btn.setObjectName("logActionBtn")
        no_btn.setFixedHeight(22)
        no_btn.setFixedWidth(40)
        no_btn.clicked.connect(self._cancel_delete)
        confirm_layout.addWidget(no_btn)

        confirm_layout.addStretch()
        self.confirm_frame.hide()
        main_layout.addWidget(self.confirm_frame)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton and not self._editing:
            # Shift 키: 다중 선택 모드 → LogPanel에서 처리
            if event.modifiers() & Qt.ShiftModifier:
                self.entry_clicked.emit(self, event)
                return
            # 일반 클릭: 기존 단일 선택 토글
            self.entry_clicked.emit(self, event)
        super().mousePressEvent(event)

    def _toggle_actions(self):
        if self._confirm_delete:
            return
        self._actions_visible = not self._actions_visible
        if self._actions_visible:
            self.action_frame.show()
            self.actions_opened.emit(self)
        else:
            self.action_frame.hide()

    def set_multi_selected(self, selected: bool, position: str = "single"):
        """다중 선택 상태 설정 (position: first, middle, last, single)"""
        self._multi_selected = selected
        if selected:
            # 자기 자신에만 적용 (자식 QFrame 제외를 위해 > 직접 objectName 사용)
            name = self.objectName() or "logEntry"
            common = "background: transparent; margin: 0; padding: 2px 6px;"
            if position == "first":
                self.setStyleSheet(f"#{name} {{ border: 2px dashed #f0a500; border-bottom: none; border-radius: 0; {common} }} #{name} QFrame {{ border: none; }}")
            elif position == "middle":
                self.setStyleSheet(f"#{name} {{ border-left: 2px dashed #f0a500; border-right: 2px dashed #f0a500; border-top: none; border-bottom: none; border-radius: 0; {common} }} #{name} QFrame {{ border: none; }}")
            elif position == "last":
                self.setStyleSheet(f"#{name} {{ border: 2px dashed #f0a500; border-top: none; border-radius: 0; {common} }} #{name} QFrame {{ border: none; }}")
            else:
                self.setStyleSheet(f"#{name} {{ border: 2px dashed #f0a500; border-radius: 4px; {common} }} #{name} QFrame {{ border: none; }}")
        else:
            self.setStyleSheet("")

    def close_actions(self):
        """외부에서 호출하여 액션 패널 닫기"""
        if self._actions_visible:
            self._actions_visible = False
            self.action_frame.hide()
        if self._confirm_delete:
            self._cancel_delete()

    def _show_toast(self, message: str):
        """액션 영역에 토스트 메시지 표시 (0.5초)"""
        from PySide6.QtCore import QTimer
        self.action_frame.hide()
        self._actions_visible = False

        toast = QLabel(message)
        toast.setAlignment(Qt.AlignCenter)
        toast.setStyleSheet("""
            background: rgba(0, 212, 255, 0.15);
            color: #00d4ff;
            border: 1px solid rgba(0, 212, 255, 0.3);
            border-radius: 4px;
            padding: 4px 8px;
            font-size: 11px;
            font-weight: bold;
        """)
        self.layout().addWidget(toast)
        QTimer.singleShot(800, lambda: (toast.setParent(None), toast.deleteLater()))

    def _copy(self):
        clipboard = QApplication.clipboard()
        msg = self.log_entry.get("message", "")
        clipboard.setText(f'[{self.log_entry.get("time_str", "")}] {msg}')
        self._show_toast("복사되었습니다")

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
            self.text_label.setText(_wrap_html(new_msg))
        self._editing = False
        self.edit_input.hide()
        self.text_label.show()

    def _toggle_check(self):
        self._checked = not self._checked
        self.log_entry["checked"] = self._checked
        self.checked_changed.emit(self.log_entry, self._checked)
        if self._checked:
            self.setObjectName("logEntryChecked")
            self.time_label.setObjectName("logTimeChecked")
            self.check_btn.setObjectName("logCheckBtnActive")
        else:
            self.setObjectName("logEntry")
            self.time_label.setObjectName("logTime")
            self.check_btn.setObjectName("logCheckBtn")
        self.setStyleSheet(self.styleSheet())
        self.time_label.setStyleSheet(self.time_label.styleSheet())
        self.check_btn.setStyleSheet(self.check_btn.styleSheet())

    def _request_delete(self):
        """삭제 확인 요청"""
        self._confirm_delete = True
        self.action_frame.hide()
        self.confirm_frame.show()

    def _confirm_delete_action(self):
        """삭제 확인"""
        self._confirm_delete = False
        self.confirm_frame.hide()
        self._show_toast("삭제되었습니다")
        from PySide6.QtCore import QTimer
        QTimer.singleShot(800, lambda: self.deleted.emit(self.log_entry))

    def _cancel_delete(self):
        """삭제 취소"""
        self._confirm_delete = False
        self.confirm_frame.hide()
        self.action_frame.show()
        self._actions_visible = True


class LogPanel(QWidget):
    """세로형 로그 패널 - 채팅창 스타일, Ctrl+휠로 텍스트 확대/축소, Shift+클릭 다중 선택"""
    export_requested = Signal()

    def __init__(self, data_manager: DataManager, parent=None):
        super().__init__(parent)
        self.dm = data_manager
        self.entry_widgets: list[LogEntryWidget] = []
        self._font_size = _log_font_size
        self._multi_selected: list[LogEntryWidget] = []
        self._last_clicked_widget = None  # Shift 선택 기준점
        self.setObjectName("logPanelVertical")
        self.setFocusPolicy(Qt.StrongFocus)
        self._setup_ui()
        self._load_existing_logs()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # 제목 행: 작전 로그 + 내보내기 버튼 (대시보드 섹션 헤더와 동일 높이)
        self.title_frame = QFrame()
        self.title_frame.setObjectName("logTitleFrame")
        self.title_frame.setStyleSheet("""
            #logTitleFrame {
                border-bottom: 1px solid rgba(0, 212, 255, 0.12);
                background: transparent;
            }
        """)
        title_h = QHBoxLayout(self.title_frame)
        title_h.setContentsMargins(12, 6, 12, 6)
        title_h.setSpacing(8)

        self._title_label = QLabel("작전 로그")
        self._title_base_font_size = 16
        self._title_label.setStyleSheet(f"""
            color: #00d4ff; font-size: {self._title_base_font_size}px; font-weight: bold;
            font-family: "HY헤드라인M", "HYHeadLineM", "Malgun Gothic", sans-serif;
            padding: 0; letter-spacing: 1px; background: transparent; border: none;
        """)
        self._title_label.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        title_h.addWidget(self._title_label)
        title_h.addStretch()

        export_btn = QPushButton("내보내기")
        export_btn.setObjectName("headerConfirmBtn")
        export_btn.setFixedHeight(24)
        export_btn.setCursor(Qt.PointingHandCursor)
        export_btn.clicked.connect(self.export_requested.emit)
        title_h.addWidget(export_btn)

        layout.addWidget(self.title_frame)

        # 다중 선택 액션 바 (기본 숨김)
        self._multi_action_frame = QFrame()
        self._multi_action_frame.setStyleSheet("""
            background: rgba(0, 80, 120, 0.4);
            border-bottom: 1px solid rgba(0, 212, 255, 0.3);
        """)
        ma_layout = QHBoxLayout(self._multi_action_frame)
        ma_layout.setContentsMargins(8, 4, 8, 4)
        ma_layout.setSpacing(6)

        self._multi_count_label = QLabel("0개 선택")
        self._multi_count_label.setStyleSheet("color: #00d4ff; font-size: 11px; font-weight: bold; background: transparent; border: none;")
        ma_layout.addWidget(self._multi_count_label)
        ma_layout.addStretch()

        multi_check_btn = QPushButton("✓ 체크")
        multi_check_btn.setObjectName("logCheckBtn")
        multi_check_btn.setFixedHeight(22)
        multi_check_btn.setFixedWidth(56)
        multi_check_btn.clicked.connect(self._multi_check)
        ma_layout.addWidget(multi_check_btn)

        multi_copy_btn = QPushButton("복사")
        multi_copy_btn.setObjectName("logActionBtn")
        multi_copy_btn.setFixedHeight(22)
        multi_copy_btn.setFixedWidth(40)
        multi_copy_btn.clicked.connect(self._multi_copy)
        ma_layout.addWidget(multi_copy_btn)

        multi_del_btn = QPushButton("삭제")
        multi_del_btn.setObjectName("logActionBtnDanger")
        multi_del_btn.setFixedHeight(22)
        multi_del_btn.setFixedWidth(40)
        multi_del_btn.clicked.connect(self._multi_delete)
        ma_layout.addWidget(multi_del_btn)

        multi_cancel_btn = QPushButton("취소")
        multi_cancel_btn.setObjectName("logActionBtn")
        multi_cancel_btn.setFixedHeight(22)
        multi_cancel_btn.setFixedWidth(40)
        multi_cancel_btn.clicked.connect(self._clear_multi_selection)
        ma_layout.addWidget(multi_cancel_btn)

        self._multi_action_frame.hide()
        # 레이아웃에 추가하지 않음 → _update_multi_action_bar에서 동적 삽입

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

        input_frame = QFrame()
        input_frame.setObjectName("logInputFrame")
        input_layout = QHBoxLayout(input_frame)
        input_layout.setContentsMargins(6, 4, 6, 4)
        input_layout.setSpacing(4)

        self.memo_input = QTextEdit()
        self.memo_input.setObjectName("memoInput")
        self.memo_input.setPlaceholderText("메모 입력 후 Enter로 전송... (Alt+Enter: 줄바꿈)")
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

        self.memo_input.installEventFilter(self)
        self.scroll.installEventFilter(self)

    # ---- 다중 선택 ----
    def _on_entry_clicked(self, widget: LogEntryWidget, event):
        """로그 항목 클릭 처리 (단일/Shift 다중 선택)"""
        if event.modifiers() & Qt.ShiftModifier and self._last_clicked_widget:
            # Shift+클릭: 범위 선택
            start_idx = self._get_widget_index(self._last_clicked_widget)
            end_idx = self._get_widget_index(widget)
            if start_idx is not None and end_idx is not None:
                lo, hi = min(start_idx, end_idx), max(start_idx, end_idx)
                # 기존 다중 선택 해제
                for w in self._multi_selected:
                    w.set_multi_selected(False)
                    w.close_actions()
                self._multi_selected.clear()
                # 범위 내 항목 선택 (위치별 테두리 구분)
                count = hi - lo + 1
                for i in range(lo, hi + 1):
                    w = self.entry_widgets[i]
                    if count == 1:
                        pos = "single"
                    elif i == lo:
                        pos = "first"
                    elif i == hi:
                        pos = "last"
                    else:
                        pos = "middle"
                    w.set_multi_selected(True, pos)
                    w.close_actions()
                    self._multi_selected.append(w)
                self._update_multi_action_bar()
                return
        else:
            # 일반 클릭: 다중 선택 해제 + 단일 액션 토글
            if self._multi_selected:
                self._clear_multi_selection()
            self._last_clicked_widget = widget
            widget._toggle_actions()
            self._close_other_actions(widget)

    def _get_widget_index(self, widget):
        try:
            return self.entry_widgets.index(widget)
        except ValueError:
            return None

    def _update_multi_action_bar(self):
        count = len(self._multi_selected)
        if count > 1:
            self._multi_count_label.setText(f"{count}개 선택")
            # 첫 번째 선택 항목 바로 위에 삽입
            first = self._multi_selected[0]
            first_idx = self._get_widget_index(first)
            if first_idx is not None:
                # 기존 위치에서 제거 후 재삽입
                self._multi_action_frame.setParent(None)
                # log_layout에서 해당 위치 찾기
                for i in range(self.log_layout.count()):
                    item = self.log_layout.itemAt(i)
                    if item and item.widget() is first:
                        self.log_layout.insertWidget(i, self._multi_action_frame)
                        break
            self._multi_action_frame.show()
        else:
            self._multi_action_frame.hide()
            self._multi_action_frame.setParent(None)

    def _clear_multi_selection(self):
        for w in self._multi_selected:
            w.set_multi_selected(False)
        self._multi_selected.clear()
        self._multi_action_frame.hide()
        self._multi_action_frame.setParent(None)

    def _multi_check(self):
        """선택된 항목 모두 체크/해제 토글"""
        # 하나라도 미체크면 모두 체크, 모두 체크면 모두 해제
        all_checked = all(w._checked for w in self._multi_selected)
        for w in self._multi_selected:
            if all_checked:
                if w._checked:
                    w._toggle_check()
            else:
                if not w._checked:
                    w._toggle_check()
        self.dm.save()
        self._clear_multi_selection()

    def _multi_copy(self):
        """선택된 항목 모두 복사"""
        lines = []
        for w in self._multi_selected:
            msg = w.log_entry.get("message", "")
            ts = w.log_entry.get("time_str", "")
            lines.append(f"[{ts}] {msg}")
        clipboard = QApplication.clipboard()
        clipboard.setText("\n".join(lines))
        self._clear_multi_selection()

    def _multi_delete(self):
        """선택된 항목 모두 삭제"""
        for w in self._multi_selected:
            self.dm.delete_log(w.log_entry)
        self._multi_selected.clear()
        self._multi_action_frame.hide()
        self._rebuild_entries()

    # ---- 기존 로직 ----
    def eventFilter(self, obj, event):
        if obj == self.memo_input and event.type() == event.Type.KeyPress:
            if event.key() in (Qt.Key_Return, Qt.Key_Enter):
                if event.modifiers() & Qt.AltModifier:
                    self.memo_input.insertPlainText("\n")
                    return True
                else:
                    self._add_memo()
                    return True
        if obj == self.scroll and event.type() == event.Type.Wheel:
            if event.modifiers() & Qt.ControlModifier:
                self.wheelEvent(event)
                return True
        return super().eventFilter(obj, event)

    def keyPressEvent(self, event: QKeyEvent):
        """Del 키로 선택된 로그 삭제"""
        if event.key() == Qt.Key_Delete:
            if self._multi_selected:
                self._multi_delete()
                return
            # 단일 선택 (액션 열린 항목)
            for w in self.entry_widgets:
                if w._actions_visible:
                    self.dm.delete_log(w.log_entry)
                    self._rebuild_entries()
                    return
        super().keyPressEvent(event)

    def _load_existing_logs(self):
        for log in self.dm.logs:
            self._add_entry_widget(log)
        self._last_log_count = len(self.dm.logs)
        self._scroll_to_bottom()

    def _add_entry_widget(self, log_entry: dict):
        if log_entry.get("type") == "date_separator":
            sep = QLabel(log_entry.get("message", ""))
            sep.setAlignment(Qt.AlignCenter)
            sep.setStyleSheet("color: #5a7a9a; font-size: 12px; padding: 8px 0; font-weight: bold;")
            idx = self.log_layout.count() - 1
            self.log_layout.insertWidget(idx, sep)
            return

        widget = LogEntryWidget(log_entry)
        widget.deleted.connect(self._on_delete)
        widget.edited.connect(self._on_edit)
        widget.checked_changed.connect(self._on_checked)
        widget.actions_opened.connect(self._close_other_actions)
        widget.entry_clicked.connect(self._on_entry_clicked)
        self.entry_widgets.append(widget)
        idx = self.log_layout.count() - 1
        self.log_layout.insertWidget(idx, widget)

    def _close_other_actions(self, opened_widget):
        for w in self.entry_widgets:
            if w is not opened_widget:
                w.close_actions()

    def append_log(self, message: str):
        count = getattr(self, '_last_log_count', 0)
        for i in range(count, len(self.dm.logs)):
            self._add_entry_widget(self.dm.logs[i])
        self._last_log_count = len(self.dm.logs)
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

    def wheelEvent(self, event: QWheelEvent):
        """Ctrl+휠로 로그 텍스트 확대/축소"""
        if event.modifiers() & Qt.ControlModifier:
            global _log_font_size
            delta = event.angleDelta().y()
            if delta > 0:
                self._font_size = min(self._font_size + 1, 24)
            elif delta < 0:
                self._font_size = max(self._font_size - 1, 8)
            _log_font_size = self._font_size
            self._apply_font_size()
            event.accept()
        else:
            super().wheelEvent(event)

    def update_title_font(self, content_font_size: int):
        """대시보드 섹션 타이틀과 동기화 (Ctrl+휠)"""
        title_sz = max(12, int(content_font_size * 16 / 13))
        if hasattr(self, '_title_label'):
            self._title_label.setStyleSheet(f"""
                color: #00d4ff; font-size: {title_sz}px; font-weight: bold;
                font-family: "HY헤드라인M", "HYHeadLineM", "Malgun Gothic", sans-serif;
                padding: 0; letter-spacing: 1px; background: transparent; border: none;
            """)

    def _apply_font_size(self):
        """로그 본문 폰트 크기 적용 (로그 패널 자체 Ctrl+휠)"""
        sz = self._font_size
        for widget in self.entry_widgets:
            widget.time_label.setStyleSheet(
                widget.time_label.styleSheet().replace(
                    widget.time_label.styleSheet(), ""
                )
            )
            ts = f"font-size: {sz}px;"
            widget.time_label.setStyleSheet(ts)
            msg = widget.log_entry.get("message", "")
            widget.text_label.setText(_wrap_html(msg, sz))

    def _scroll_to_bottom(self):
        from PySide6.QtCore import QTimer
        QTimer.singleShot(50, lambda: self.scroll.verticalScrollBar().setValue(
            self.scroll.verticalScrollBar().maximum()
        ))
