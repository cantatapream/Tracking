"""
SPT 대원 카드 위젯 - 컴팩트 디자인
"""
from PySide6.QtWidgets import (
    QFrame, QHBoxLayout, QVBoxLayout, QLabel, QSizePolicy
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
        layout.setContentsMargins(10, 4, 10, 4)
        layout.setSpacing(8)

        # 좌측: 계급 + 이름
        left_layout = QHBoxLayout()
        left_layout.setSpacing(4)

        self.rank_label = QLabel(self.personnel.rank)
        self.rank_label.setObjectName("cardRank")
        left_layout.addWidget(self.rank_label)

        self.name_label = QLabel(self.personnel.name)
        self.name_label.setObjectName("cardName")
        left_layout.addWidget(self.name_label)

        left_layout.addStretch()
        layout.addLayout(left_layout, 1)

        # 우측: 타이머 정보 (2줄)
        right_layout = QVBoxLayout()
        right_layout.setContentsMargins(0, 2, 0, 2)
        right_layout.setSpacing(2)

        self.timer_line1 = QLabel("")
        self.timer_line1.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        self.timer_line1.setObjectName("cardTimerInfo")
        self.timer_line1.setWordWrap(True)
        right_layout.addWidget(self.timer_line1)

        self.timer_line2 = QLabel("")
        self.timer_line2.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        self.timer_line2.setObjectName("cardTimerInfo2")
        self.timer_line2.setWordWrap(True)
        right_layout.addWidget(self.timer_line2)

        layout.addLayout(right_layout, 1)

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
