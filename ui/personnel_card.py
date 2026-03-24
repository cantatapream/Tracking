"""
SPT 대원 카드 위젯 - 프리미엄 디자인
"""
from PySide6.QtWidgets import (
    QFrame, QHBoxLayout, QVBoxLayout, QLabel, QSizePolicy
)
from PySide6.QtCore import Qt, Signal, QPropertyAnimation, QEasingCurve, Property
from PySide6.QtGui import QPainter, QColor, QPen, QBrush, QLinearGradient, QFont
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


class PersonnelCard(QFrame):
    """대원 카드 위젯"""
    clicked = Signal(str, bool)  # (personnel_id, is_ctrl_pressed)

    ALERT_THRESHOLD = 4 * 3600  # 4시간

    def __init__(self, personnel: Personnel, parent=None):
        super().__init__(parent)
        self.personnel = personnel
        self._selected = False
        self._alert = False
        self._glow_opacity = 0.0
        self.setCursor(Qt.PointingHandCursor)
        self.setMinimumHeight(72)
        self.setMaximumHeight(90)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self._setup_ui()
        self.update_style()

    def _setup_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(10, 8, 10, 8)
        layout.setSpacing(10)

        # 프로필 아이콘 (원형)
        self.profile_frame = QFrame()
        self.profile_frame.setFixedSize(44, 44)
        self.profile_frame.setStyleSheet("background: transparent; border: none;")
        layout.addWidget(self.profile_frame)

        # 정보 영역
        info_layout = QVBoxLayout()
        info_layout.setContentsMargins(0, 0, 0, 0)
        info_layout.setSpacing(1)

        # 이름 + 계급 행
        name_row = QHBoxLayout()
        name_row.setSpacing(6)
        self.name_label = QLabel(self.personnel.name)
        self.name_label.setObjectName("cardName")
        name_row.addWidget(self.name_label)

        self.rank_label = QLabel(self.personnel.rank)
        self.rank_label.setObjectName("cardRank")
        name_row.addWidget(self.rank_label)
        name_row.addStretch()

        # 상태 뱃지
        self.status_label = QLabel()
        self.status_label.setObjectName("cardStatus")
        name_row.addWidget(self.status_label)

        info_layout.addLayout(name_row)

        # 하단 정보 (타이머 / 휴식)
        bottom_row = QHBoxLayout()
        bottom_row.setSpacing(8)

        self.timer_label = QLabel("")
        self.timer_label.setObjectName("cardTimer")
        bottom_row.addWidget(self.timer_label)

        self.rest_label = QLabel("")
        self.rest_label.setObjectName("cardRestInfo")
        bottom_row.addWidget(self.rest_label)

        self.total_deploy_label = QLabel("")
        self.total_deploy_label.setObjectName("cardTotalDeploy")
        bottom_row.addWidget(self.total_deploy_label)

        bottom_row.addStretch()
        info_layout.addLayout(bottom_row)

        layout.addLayout(info_layout, 1)

        # 우측 타이머 (큰 글씨)
        self.big_timer = QLabel("")
        self.big_timer.setObjectName("cardTimer")
        self.big_timer.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        layout.addWidget(self.big_timer)

    def update_display(self):
        """실시간 정보 업데이트"""
        p = self.personnel
        self.name_label.setText(p.name)
        self.rank_label.setText(p.rank)

        if p.location == "base":
            if p.has_been_deployed:
                self.status_label.setText("휴식 중")
                self.status_label.setObjectName("cardRestInfo")
                rest = p.get_rest_elapsed()
                self.big_timer.setText(format_time(rest))
                self.big_timer.setObjectName("cardTimer")
                self.rest_label.setText(f"복귀 후 {format_time(rest)}")
                # 총 탑승 시간
                if p.total_deploy_seconds > 0:
                    self.total_deploy_label.setText(
                        f"총 탑승 {format_time(p.total_deploy_seconds)}"
                    )
                    self.total_deploy_label.show()
                else:
                    self.total_deploy_label.hide()
            else:
                self.status_label.setText("대기 중")
                self.status_label.setObjectName("cardStatusStandby")
                self.big_timer.setText("")
                self.rest_label.setText("")
                self.total_deploy_label.hide()
            self.timer_label.hide()
            self._alert = False
        else:
            elapsed = p.get_deploy_elapsed()
            self.status_label.setText("ACTIVE")
            self.status_label.setObjectName("liveBadge")
            self.big_timer.setText(format_time(elapsed))
            self.timer_label.hide()
            self.rest_label.setText("")
            self.total_deploy_label.hide()

            # 위험 알람 (4시간 초과)
            if elapsed >= self.ALERT_THRESHOLD:
                self._alert = True
                self.big_timer.setObjectName("cardTimerAlert")
            else:
                self._alert = False
                self.big_timer.setObjectName("cardTimer")

        self.update_style()
        # Force style refresh
        self.status_label.setStyleSheet(self.status_label.styleSheet())
        self.big_timer.setStyleSheet(self.big_timer.styleSheet())

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
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        # 프로필 원형 아이콘
        profile_rect = self.profile_frame.geometry()
        cx = profile_rect.center().x()
        cy = profile_rect.center().y()
        radius = 19

        # 외곽 테두리 색상
        if self.personnel.location == "base":
            border_color = QColor("#00d4ff")
        elif self.personnel.location.startswith("patrol"):
            border_color = QColor("#2ecc71")
        else:
            border_color = QColor("#f39c12")

        # 테두리
        pen = QPen(border_color, 2)
        painter.setPen(pen)
        painter.setBrush(QBrush(QColor("#152d4a")))
        painter.drawEllipse(cx - radius, cy - radius, radius * 2, radius * 2)

        # 이니셜
        painter.setPen(QPen(QColor("#ffffff"), 1))
        font = QFont("Malgun Gothic", 14, QFont.Bold)
        painter.setFont(font)
        painter.drawText(
            cx - radius, cy - radius, radius * 2, radius * 2,
            Qt.AlignCenter, self.personnel.name[0] if self.personnel.name else "?"
        )

        # 선택 시 발광 효과
        if self._selected:
            glow_pen = QPen(QColor(0, 212, 255, 60), 6)
            painter.setPen(glow_pen)
            painter.setBrush(Qt.NoBrush)
            painter.drawRoundedRect(self.rect().adjusted(2, 2, -2, -2), 8, 8)

        painter.end()
