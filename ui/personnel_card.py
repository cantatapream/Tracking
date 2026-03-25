"""
SPT 대원 카드 위젯 - 컴팩트 디자인
"""
from PySide6.QtWidgets import (
    QFrame, QHBoxLayout, QVBoxLayout, QLabel, QSizePolicy,
    QPushButton, QDialog, QScrollArea, QWidget
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QPainter, QColor, QPen
from core.models import Personnel
import time


def format_time(seconds: float) -> str:
    """초를 HH:MM:SS 형식으로 변환"""
    if seconds <= 0:
        return "00:00:00"
    h = int(seconds) // 3600
    m = (int(seconds) % 3600) // 60
    s = int(seconds) % 60
    return f"{h:02d}:{m:02d}:{s:02d}"


def format_time_hm(seconds: float) -> str:
    """초를 HH:MM 형식으로 변환"""
    if seconds <= 0:
        return "00:00"
    h = int(seconds) // 3600
    m = (int(seconds) % 3600) // 60
    return f"{h:02d}:{m:02d}"


class HistoryDialog(QDialog):
    """인원 이동 내역 다이얼로그"""
    def __init__(self, personnel: Personnel, parent=None):
        super().__init__(parent)
        self.setWindowTitle(f"{personnel.rank} {personnel.name} - 이동 내역")
        self.setMinimumWidth(340)
        self.setMaximumHeight(500)

        layout = QVBoxLayout(self)
        layout.setSpacing(4)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        content = QWidget()
        cl = QVBoxLayout(content)
        cl.setContentsMargins(8, 8, 8, 8)
        cl.setSpacing(2)

        history = personnel.movement_history
        if not history:
            empty = QLabel("이동 내역이 없습니다.")
            empty.setStyleSheet("color: #5a7a9a; font-size: 12px;")
            cl.addWidget(empty)
        else:
            for i, entry in enumerate(history):
                ts = entry.get("timestamp", 0)
                to_name = entry.get("to_name", entry.get("to", ""))
                to_loc = entry.get("to", "")
                time_str = time.strftime("%m.%d %H:%M", time.localtime(ts))

                # 체류시간 계산
                if i + 1 < len(history):
                    stay_secs = history[i + 1]["timestamp"] - ts
                else:
                    stay_secs = time.time() - ts

                days = int(stay_secs) // 86400
                hours = (int(stay_secs) % 86400) // 3600
                mins = (int(stay_secs) % 3600) // 60
                if days > 0:
                    stay_str = f"{days}일 {hours:02d}:{mins:02d}"
                else:
                    stay_str = f"{hours:02d}:{mins:02d}"

                tl = QLabel(f"[{time_str}]")
                tl.setStyleSheet("color: #5a7a9a; font-size: 11px; font-family: 'Consolas', monospace;")
                cl.addWidget(tl)

                if to_loc == "base":
                    move_text = f"본함으로 이동 (체류시간 {stay_str})"
                else:
                    move_text = f"({to_name})으로 이동 (체류시간 {stay_str})"
                ml = QLabel(move_text)
                ml.setStyleSheet("color: #e0e8f0; font-size: 12px;")
                ml.setWordWrap(True)
                cl.addWidget(ml)

        cl.addStretch()
        scroll.setWidget(content)
        layout.addWidget(scroll, 1)

        close_btn = QPushButton("닫기")
        close_btn.setFixedHeight(28)
        close_btn.clicked.connect(self.accept)
        layout.addWidget(close_btn)


class PersonnelCard(QFrame):
    """대원 카드 위젯 - 컴팩트"""
    clicked = Signal(str, bool)  # (personnel_id, is_ctrl_pressed)

    ALERT_THRESHOLD = 4 * 3600  # 4시간

    def __init__(self, personnel: Personnel, parent=None):
        super().__init__(parent)
        self.personnel = personnel
        self._selected = False
        self._alert = False
        self.setCursor(Qt.PointingHandCursor)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Minimum)
        self._setup_ui()
        self.update_style()

    def _setup_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(5, 4, 5, 4)
        layout.setSpacing(6)

        # 좌측: 계급 + 이름 (고정 크기)
        self.rank_label = QLabel(self.personnel.rank)
        self.rank_label.setObjectName("cardRank")
        layout.addWidget(self.rank_label)

        self.name_label = QLabel(self.personnel.name)
        self.name_label.setObjectName("cardName")
        layout.addWidget(self.name_label)

        # 이동 내역 버튼
        self.history_btn = QPushButton("📋")
        self.history_btn.setFixedSize(22, 22)
        self.history_btn.setCursor(Qt.PointingHandCursor)
        self.history_btn.setStyleSheet("""
            QPushButton { background: transparent; border: none; font-size: 12px; padding: 0; }
            QPushButton:hover { background: rgba(0, 212, 255, 0.15); border-radius: 3px; }
        """)
        self.history_btn.clicked.connect(self._show_history)
        layout.addWidget(self.history_btn)

        # 우측: 타이머 정보 (2줄)
        right_layout = QVBoxLayout()
        right_layout.setContentsMargins(0, 2, 0, 2)
        right_layout.setSpacing(2)

        self.timer_line1 = QLabel("")
        self.timer_line1.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        self.timer_line1.setObjectName("cardTimerInfo")
        right_layout.addWidget(self.timer_line1)

        self.timer_line2 = QLabel("")
        self.timer_line2.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        self.timer_line2.setObjectName("cardTimerInfo2")
        right_layout.addWidget(self.timer_line2)

        layout.addLayout(right_layout, 1)

    def _show_history(self):
        """이동 내역 다이얼로그 표시"""
        dlg = HistoryDialog(self.personnel, self)
        dlg.exec()

    def update_display(self):
        """실시간 정보 업데이트"""
        p = self.personnel
        self.name_label.setText(p.name)
        self.rank_label.setText(p.rank)

        if p.location == "base":
            if p.has_been_deployed:
                rest = p.get_rest_elapsed()
                total = p.total_deploy_seconds
                self.timer_line1.setText(f"복귀 후 경과: {format_time_hm(rest)}")
                self.timer_line1.setObjectName("cardTimerInfo")
                self.timer_line2.setText(f"총 이함 시간: {format_time_hm(total)}")
                self.timer_line2.setObjectName("cardTimerInfo2")
                self.timer_line2.show()
            else:
                self.timer_line1.setText("대기 중")
                self.timer_line1.setObjectName("cardStatusStandby")
                self.timer_line2.setText("")
                self.timer_line2.hide()
            self._alert = False
        else:
            # 단정/어선: 현재 이함 경과 + 총 누적
            elapsed = p.get_deploy_elapsed()
            total_away = p.get_total_away_time()

            self.timer_line1.setText(f"이함 경과: {format_time_hm(elapsed)}")
            self.timer_line1.setObjectName("cardTimerInfo")
            self.timer_line2.setText(f"총 이함 시간: {format_time_hm(total_away)}")
            self.timer_line2.setObjectName("cardTimerInfo2")
            self.timer_line2.show()

            # 위험 알람 (4시간 초과)
            if elapsed >= self.ALERT_THRESHOLD:
                self._alert = True
                self.timer_line1.setObjectName("cardTimerAlert")
            else:
                self._alert = False

        self.update_style()
        # Force style refresh
        self.timer_line1.setStyleSheet(self.timer_line1.styleSheet())
        self.timer_line2.setStyleSheet(self.timer_line2.styleSheet())

    def update_style(self):
        if self._selected:
            self.setObjectName("personnelCardSelected")
        elif self._alert:
            self.setObjectName("personnelCardAlert")
        else:
            self.setObjectName("personnelCard")
        self.setStyleSheet(self.styleSheet())  # force re-apply

    @property
    def selected(self) -> bool:
        return self._selected

    @selected.setter
    def selected(self, value: bool):
        self._selected = value
        self.update_style()

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            ctrl = event.modifiers() & Qt.ControlModifier
            self.clicked.emit(self.personnel.id, bool(ctrl))
        super().mousePressEvent(event)

    def paintEvent(self, event):
        super().paintEvent(event)
        # 선택 시 발광 효과만 그림 (프로필 원형 삭제)
        if self._selected:
            painter = QPainter(self)
            painter.setRenderHint(QPainter.Antialiasing)
            glow_pen = QPen(QColor(0, 212, 255, 60), 4)
            painter.setPen(glow_pen)
            painter.setBrush(Qt.NoBrush)
            painter.drawRoundedRect(self.rect().adjusted(2, 2, -2, -2), 8, 8)
            painter.end()
