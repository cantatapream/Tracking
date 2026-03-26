"""
임검침로 산출 패널
"""
import math
from PySide6.QtWidgets import (
    QFrame, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QSizePolicy, QScrollArea, QWidget
)
from PySide6.QtCore import Qt


class InterceptPanel(QFrame):
    """임검침로 산출 패널 - 사이드바 하단"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("sectionPanel")
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # 제목 영역 (장비 보유 목록과 동일한 스타일/크기)
        title_frame = QFrame()
        title_frame.setObjectName("equipmentSectionHeader")
        title_frame.setMinimumHeight(28)
        title_h = QHBoxLayout(title_frame)
        title_h.setContentsMargins(4, 2, 4, 2)
        title_h.setSpacing(8)
        title_label = QLabel("임검침로 산출")
        title_label.setObjectName("equipmentSectionHeader")
        title_label.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        title_h.addWidget(title_label)
        title_h.addStretch()
        layout.addWidget(title_frame)

        # 스크롤 영역
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll.setFrameShape(QFrame.NoFrame)
        content = QWidget()
        cl = QVBoxLayout(content)
        cl.setContentsMargins(6, 4, 6, 4)
        cl.setSpacing(4)

        input_style = """
            QLineEdit {
                background: #0a1628; color: #e0e8f0; border: 1px solid #1e3a5f;
                border-radius: 3px; padding: 2px 4px; font-size: 12px;
            }
            QLineEdit:focus { border-color: #00d4ff; }
        """
        label_style = "color: #c8d6e5; font-size: 13px; background: transparent; border: none;"
        section_style = "color: #00d4ff; font-size: 15px; font-weight: bold; background: transparent; border: none; padding: 2px 2px;"

        # === 대상 선박 ===
        target_header = QLabel("대상 선박")
        target_header.setStyleSheet(section_style)
        cl.addWidget(target_header)

        # 방위 + 거리
        r1 = QHBoxLayout()
        r1.setSpacing(4)
        lb1 = QLabel("방위")
        lb1.setStyleSheet(label_style)
        r1.addWidget(lb1)
        self.bearing_input = QLineEdit()
        self.bearing_input.setPlaceholderText("°")
        self.bearing_input.setFixedHeight(24)
        self.bearing_input.setMaximumWidth(60)
        self.bearing_input.setStyleSheet(input_style)
        r1.addWidget(self.bearing_input)
        lb2 = QLabel("거리")
        lb2.setStyleSheet(label_style)
        r1.addWidget(lb2)
        self.distance_input = QLineEdit()
        self.distance_input.setPlaceholderText("NM")
        self.distance_input.setFixedHeight(24)
        self.distance_input.setMaximumWidth(60)
        self.distance_input.setStyleSheet(input_style)
        r1.addWidget(self.distance_input)
        r1.addStretch()
        cl.addLayout(r1)

        # 침로 + 속력
        r2 = QHBoxLayout()
        r2.setSpacing(4)
        lb3 = QLabel("침로")
        lb3.setStyleSheet(label_style)
        r2.addWidget(lb3)
        self.target_course_input = QLineEdit()
        self.target_course_input.setPlaceholderText("°")
        self.target_course_input.setFixedHeight(24)
        self.target_course_input.setMaximumWidth(60)
        self.target_course_input.setStyleSheet(input_style)
        r2.addWidget(self.target_course_input)
        lb4 = QLabel("속력")
        lb4.setStyleSheet(label_style)
        r2.addWidget(lb4)
        self.target_speed_input = QLineEdit()
        self.target_speed_input.setPlaceholderText("kts")
        self.target_speed_input.setFixedHeight(24)
        self.target_speed_input.setMaximumWidth(60)
        self.target_speed_input.setStyleSheet(input_style)
        r2.addWidget(self.target_speed_input)
        r2.addStretch()
        cl.addLayout(r2)

        # === 산출 조건 ===
        cond_header = QLabel("산출 조건")
        cond_header.setStyleSheet(section_style)
        cl.addWidget(cond_header)

        # 우리 속력
        r3 = QHBoxLayout()
        r3.setSpacing(4)
        lb5 = QLabel("우리 속력")
        lb5.setStyleSheet(label_style)
        r3.addWidget(lb5)
        self.own_speed_input = QLineEdit()
        self.own_speed_input.setPlaceholderText("kts")
        self.own_speed_input.setFixedHeight(24)
        self.own_speed_input.setMaximumWidth(60)
        self.own_speed_input.setStyleSheet(input_style)
        self.own_speed_input.textChanged.connect(self._on_speed_changed)
        r3.addWidget(self.own_speed_input)
        r3.addStretch()
        cl.addLayout(r3)

        # 상봉시간
        r4 = QHBoxLayout()
        r4.setSpacing(4)
        lb6 = QLabel("상봉시간")
        lb6.setStyleSheet(label_style)
        r4.addWidget(lb6)
        self.rendezvous_time_input = QLineEdit()
        self.rendezvous_time_input.setPlaceholderText("분")
        self.rendezvous_time_input.setFixedHeight(24)
        self.rendezvous_time_input.setMaximumWidth(60)
        self.rendezvous_time_input.setStyleSheet(input_style)
        self.rendezvous_time_input.textChanged.connect(self._on_time_changed)
        r4.addWidget(self.rendezvous_time_input)
        r4.addStretch()
        cl.addLayout(r4)

        # 산출 버튼
        calc_btn = QPushButton("산출")
        calc_btn.setObjectName("btnAccent")
        calc_btn.setFixedHeight(32)
        calc_btn.setCursor(Qt.PointingHandCursor)
        calc_btn.clicked.connect(self._calculate)
        cl.addWidget(calc_btn)

        # === 결과 영역 (기본 숨김) ===
        self._result_frame = QFrame()
        self._result_frame.setStyleSheet("""
            QFrame { background: rgba(15, 35, 65, 0.8); border: 1px solid rgba(0, 212, 255, 0.2);
                     border-radius: 4px; }
            QLabel { background: transparent; border: none; }
        """)
        rf_layout = QVBoxLayout(self._result_frame)
        rf_layout.setContentsMargins(6, 4, 6, 4)
        rf_layout.setSpacing(2)

        result_title = QLabel("산출 결과")
        result_title.setStyleSheet("color: #2ecc71; font-size: 15px; font-weight: bold; padding: 2px 0;")
        rf_layout.addWidget(result_title)

        result_style = "color: #f0a500; font-size: 13px; font-weight: bold;"

        self._course_label = QLabel("권고침로: -")
        self._course_label.setStyleSheet(result_style)
        rf_layout.addWidget(self._course_label)

        self._speed_label = QLabel("권고속력: -")
        self._speed_label.setStyleSheet(result_style)
        rf_layout.addWidget(self._speed_label)

        self._time_label = QLabel("상봉시간: -")
        self._time_label.setStyleSheet(result_style)
        rf_layout.addWidget(self._time_label)

        self._point_label = QLabel("상봉지점: -")
        self._point_label.setStyleSheet(result_style)
        rf_layout.addWidget(self._point_label)

        # 5분할 경과 테이블
        self._progress_label = QLabel("")
        self._progress_label.setStyleSheet("color: #8faabe; font-size: 11px; padding-top: 4px;")
        self._progress_label.setWordWrap(True)
        self._progress_label.hide()
        rf_layout.addWidget(self._progress_label)

        self._error_label = QLabel("")
        self._error_label.setStyleSheet("color: #e74c3c; font-size: 11px; font-weight: bold;")
        self._error_label.hide()
        rf_layout.addWidget(self._error_label)

        self._result_frame.hide()
        cl.addWidget(self._result_frame)
        cl.addStretch()

        scroll.setWidget(content)
        layout.addWidget(scroll, 1)

    def _on_speed_changed(self, text):
        """우리 속력 입력 시 상봉시간 비활성화"""
        if text.strip():
            self.rendezvous_time_input.setEnabled(False)
            self.rendezvous_time_input.setStyleSheet("""
                QLineEdit { background: #0d1520; color: #3a4a5a; border: 1px solid #152030;
                             border-radius: 3px; padding: 2px 4px; font-size: 12px; }
            """)
        else:
            self.rendezvous_time_input.setEnabled(True)
            self.rendezvous_time_input.setStyleSheet("""
                QLineEdit { background: #0a1628; color: #e0e8f0; border: 1px solid #1e3a5f;
                             border-radius: 3px; padding: 2px 4px; font-size: 12px; }
                QLineEdit:focus { border-color: #00d4ff; }
            """)

    def _on_time_changed(self, text):
        """상봉시간 입력 시 우리 속력 비활성화"""
        if text.strip():
            self.own_speed_input.setEnabled(False)
            self.own_speed_input.setStyleSheet("""
                QLineEdit { background: #0d1520; color: #3a4a5a; border: 1px solid #152030;
                             border-radius: 3px; padding: 2px 4px; font-size: 12px; }
            """)
        else:
            self.own_speed_input.setEnabled(True)
            self.own_speed_input.setStyleSheet("""
                QLineEdit { background: #0a1628; color: #e0e8f0; border: 1px solid #1e3a5f;
                             border-radius: 3px; padding: 2px 4px; font-size: 12px; }
                QLineEdit:focus { border-color: #00d4ff; }
            """)

    def _get_float(self, widget, default=None):
        try:
            return float(widget.text().strip())
        except (ValueError, AttributeError):
            return default

    def _calculate(self):
        """임검침로 산출"""
        bearing = self._get_float(self.bearing_input)
        distance = self._get_float(self.distance_input)
        target_course = self._get_float(self.target_course_input)
        target_speed = self._get_float(self.target_speed_input)

        if any(v is None for v in [bearing, distance, target_course, target_speed]):
            self._show_error("모든 대상 선박 정보를 입력하세요")
            return
        if distance <= 0 or target_speed < 0:
            self._show_error("거리와 속력은 양수여야 합니다")
            return

        bearing_rad = math.radians(bearing)
        tx = distance * math.sin(bearing_rad)
        ty = distance * math.cos(bearing_rad)

        tc_rad = math.radians(target_course)
        vx_t = target_speed / 60.0 * math.sin(tc_rad)
        vy_t = target_speed / 60.0 * math.cos(tc_rad)

        own_speed_val = self._get_float(self.own_speed_input)
        time_val = self._get_float(self.rendezvous_time_input)

        if own_speed_val and own_speed_val > 0:
            # 모드 1: 우리 속력 지정
            vs = own_speed_val / 60.0
            a = vs**2 - vx_t**2 - vy_t**2
            b = -2 * (tx * vx_t + ty * vy_t)
            c = -(tx**2 + ty**2)
            discriminant = b**2 - 4 * a * c

            if a == 0:
                if b == 0:
                    self._show_error("산출 불가: 동일 속력/동일 방향")
                    return
                t = -c / b
            elif discriminant < 0:
                self._show_error("산출 불가: 우리 속력이 부족합니다")
                return
            else:
                t1 = (-b + math.sqrt(discriminant)) / (2 * a)
                t2 = (-b - math.sqrt(discriminant)) / (2 * a)
                candidates = [t for t in [t1, t2] if t > 0.01]
                if not candidates:
                    self._show_error("산출 불가: 유효한 해가 없습니다")
                    return
                t = min(candidates)

            meet_x = tx + vx_t * t
            meet_y = ty + vy_t * t
            own_course = math.degrees(math.atan2(meet_x, meet_y)) % 360
            meet_dist = math.sqrt(meet_x**2 + meet_y**2)
            meet_bearing = own_course

            # 5분할 경과 방위/거리
            progress = self._calc_progress(tx, ty, vx_t, vy_t, t)

            self._show_result(own_course, None, t, meet_bearing, meet_dist, progress)

        elif time_val and time_val > 0:
            # 모드 2: 상봉시간 지정
            t = time_val
            meet_x = tx + vx_t * t
            meet_y = ty + vy_t * t
            meet_dist = math.sqrt(meet_x**2 + meet_y**2)
            own_speed = meet_dist / t * 60.0
            own_course = math.degrees(math.atan2(meet_x, meet_y)) % 360
            meet_bearing = own_course

            self._show_result(own_course, own_speed, None, meet_bearing, meet_dist, None)
        else:
            self._show_error("우리 속력 또는 상봉시간을 입력하세요")

    def _calc_progress(self, tx, ty, vx_t, vy_t, total_t):
        """5분할 경과 방위/거리 계산"""
        lines = []
        for i in range(1, 6):
            t = total_t * i / 5
            # t분 후 대상 선박 위치
            px = tx + vx_t * t
            py = ty + vy_t * t
            brg = math.degrees(math.atan2(px, py)) % 360
            dist = math.sqrt(px**2 + py**2)
            mins = int(t)
            secs = int((t - mins) * 60)
            lines.append(f"  {mins:02d}분{secs:02d}초 | 방위 {brg:05.1f}° 거리 {dist:.1f}NM")
        return "\n".join(lines)

    def _show_result(self, course, speed, time_min, meet_bearing, meet_dist, progress):
        """결과 표시"""
        self._error_label.hide()
        self._course_label.setText(f"권고침로: {course:05.1f}°")

        if speed is not None:
            self._speed_label.setText(f"권고속력: {speed:.1f} kts")
            self._speed_label.show()
        else:
            self._speed_label.hide()

        if time_min is not None:
            mins = int(time_min)
            secs = int((time_min - mins) * 60)
            self._time_label.setText(f"상봉시간: 약 {mins}분 {secs}초 후")
            self._time_label.show()
        else:
            self._time_label.hide()

        self._point_label.setText(f"상봉지점: 방위 {meet_bearing:05.1f}° 거리 {meet_dist:.1f}NM")

        if progress:
            self._progress_label.setText(f"── 경과별 상대 위치 ──\n{progress}")
            self._progress_label.show()
        else:
            self._progress_label.hide()

        self._result_frame.show()

    def _show_error(self, msg):
        """에러 표시"""
        self._course_label.setText("권고침로: -")
        self._speed_label.setText("권고속력: -")
        self._time_label.setText("상봉시간: -")
        self._point_label.setText("상봉지점: -")
        self._progress_label.hide()
        self._error_label.setText(msg)
        self._error_label.show()
        self._result_frame.show()
