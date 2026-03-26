"""
임검침로 산출 패널
"""
import math
from PySide6.QtWidgets import (
    QFrame, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QRadioButton, QButtonGroup, QSizePolicy
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
        layout.setContentsMargins(6, 4, 6, 6)
        layout.setSpacing(4)

        # 제목
        title = QLabel("임검침로 산출")
        title.setStyleSheet("""
            color: #f0a500; font-size: 14px; font-weight: bold;
            font-family: "HY헤드라인M", "HYHeadLineM", "Malgun Gothic", sans-serif;
            padding: 2px 0; border: none; background: transparent;
        """)
        layout.addWidget(title)

        # 구분선
        sep = QFrame()
        sep.setFixedHeight(1)
        sep.setStyleSheet("background: rgba(240, 165, 0, 0.3);")
        layout.addWidget(sep)

        input_style = """
            QLineEdit {
                background: #0a1628; color: #e0e8f0; border: 1px solid #1e3a5f;
                border-radius: 3px; padding: 2px 4px; font-size: 12px;
            }
            QLineEdit:focus { border-color: #00d4ff; }
        """
        label_style = "color: #8faabe; font-size: 11px; background: transparent; border: none;"

        # === 대상 선박 정보 ===
        target_header = QLabel("▶ 대상 선박")
        target_header.setStyleSheet("color: #00d4ff; font-size: 11px; font-weight: bold; background: transparent; border: none; padding-top: 2px;")
        layout.addWidget(target_header)

        # 방위 + 거리 (한 줄)
        r1 = QHBoxLayout()
        r1.setSpacing(4)
        lb1 = QLabel("방위")
        lb1.setStyleSheet(label_style)
        lb1.setFixedWidth(28)
        r1.addWidget(lb1)
        self.bearing_input = QLineEdit()
        self.bearing_input.setPlaceholderText("°")
        self.bearing_input.setFixedHeight(24)
        self.bearing_input.setStyleSheet(input_style)
        r1.addWidget(self.bearing_input, 1)
        lb2 = QLabel("거리")
        lb2.setStyleSheet(label_style)
        lb2.setFixedWidth(28)
        r1.addWidget(lb2)
        self.distance_input = QLineEdit()
        self.distance_input.setPlaceholderText("NM")
        self.distance_input.setFixedHeight(24)
        self.distance_input.setStyleSheet(input_style)
        r1.addWidget(self.distance_input, 1)
        layout.addLayout(r1)

        # 침로 + 속력 (한 줄)
        r2 = QHBoxLayout()
        r2.setSpacing(4)
        lb3 = QLabel("침로")
        lb3.setStyleSheet(label_style)
        lb3.setFixedWidth(28)
        r2.addWidget(lb3)
        self.target_course_input = QLineEdit()
        self.target_course_input.setPlaceholderText("°")
        self.target_course_input.setFixedHeight(24)
        self.target_course_input.setStyleSheet(input_style)
        r2.addWidget(self.target_course_input, 1)
        lb4 = QLabel("속력")
        lb4.setStyleSheet(label_style)
        lb4.setFixedWidth(28)
        r2.addWidget(lb4)
        self.target_speed_input = QLineEdit()
        self.target_speed_input.setPlaceholderText("kts")
        self.target_speed_input.setFixedHeight(24)
        self.target_speed_input.setStyleSheet(input_style)
        r2.addWidget(self.target_speed_input, 1)
        layout.addLayout(r2)

        # === 산출 조건 ===
        cond_header = QLabel("▶ 산출 조건")
        cond_header.setStyleSheet("color: #00d4ff; font-size: 11px; font-weight: bold; background: transparent; border: none; padding-top: 2px;")
        layout.addWidget(cond_header)

        # 라디오 버튼
        self._mode_group = QButtonGroup(self)

        r3 = QHBoxLayout()
        r3.setSpacing(4)
        self.radio_speed = QRadioButton("우리 속력")
        self.radio_speed.setStyleSheet("color: #c8d6e5; font-size: 11px; background: transparent;")
        self.radio_speed.setChecked(True)
        self._mode_group.addButton(self.radio_speed, 0)
        r3.addWidget(self.radio_speed)
        self.own_speed_input = QLineEdit()
        self.own_speed_input.setPlaceholderText("kts")
        self.own_speed_input.setFixedHeight(24)
        self.own_speed_input.setStyleSheet(input_style)
        r3.addWidget(self.own_speed_input, 1)
        layout.addLayout(r3)

        r4 = QHBoxLayout()
        r4.setSpacing(4)
        self.radio_time = QRadioButton("상봉시간")
        self.radio_time.setStyleSheet("color: #c8d6e5; font-size: 11px; background: transparent;")
        self._mode_group.addButton(self.radio_time, 1)
        r4.addWidget(self.radio_time)
        self.rendezvous_time_input = QLineEdit()
        self.rendezvous_time_input.setPlaceholderText("분")
        self.rendezvous_time_input.setFixedHeight(24)
        self.rendezvous_time_input.setStyleSheet(input_style)
        self.rendezvous_time_input.setEnabled(False)
        r4.addWidget(self.rendezvous_time_input, 1)
        layout.addLayout(r4)

        # 라디오 전환 시 입력 활성화/비활성화
        self.radio_speed.toggled.connect(lambda c: self.own_speed_input.setEnabled(c))
        self.radio_speed.toggled.connect(lambda c: self.rendezvous_time_input.setEnabled(not c))

        # 산출 버튼
        calc_btn = QPushButton("산출")
        calc_btn.setObjectName("btnAccent")
        calc_btn.setFixedHeight(28)
        calc_btn.setCursor(Qt.PointingHandCursor)
        calc_btn.clicked.connect(self._calculate)
        layout.addWidget(calc_btn)

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

        result_title = QLabel("▶ 산출 결과")
        result_title.setStyleSheet("color: #2ecc71; font-size: 11px; font-weight: bold;")
        rf_layout.addWidget(result_title)

        self._course_label = QLabel("권고침로: -")
        self._course_label.setStyleSheet("color: #f0a500; font-size: 13px; font-weight: bold;")
        rf_layout.addWidget(self._course_label)

        self._speed_label = QLabel("권고속력: -")
        self._speed_label.setStyleSheet("color: #f0a500; font-size: 13px; font-weight: bold;")
        rf_layout.addWidget(self._speed_label)

        self._time_label = QLabel("상봉시간: -")
        self._time_label.setStyleSheet("color: #3498db; font-size: 12px; font-weight: bold;")
        rf_layout.addWidget(self._time_label)

        self._point_label = QLabel("상봉지점: -")
        self._point_label.setStyleSheet("color: #c8d6e5; font-size: 11px;")
        rf_layout.addWidget(self._point_label)

        self._error_label = QLabel("")
        self._error_label.setStyleSheet("color: #e74c3c; font-size: 11px; font-weight: bold;")
        self._error_label.hide()
        rf_layout.addWidget(self._error_label)

        self._result_frame.hide()
        layout.addWidget(self._result_frame)

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

        # 대상 선박 상대 위치 (NM 단위, 북쪽=Y+, 동쪽=X+)
        bearing_rad = math.radians(bearing)
        tx = distance * math.sin(bearing_rad)
        ty = distance * math.cos(bearing_rad)

        # 대상 선박 속도 벡터 (NM/분)
        tc_rad = math.radians(target_course)
        vx_t = target_speed / 60.0 * math.sin(tc_rad)
        vy_t = target_speed / 60.0 * math.cos(tc_rad)

        is_speed_mode = self.radio_speed.isChecked()

        if is_speed_mode:
            # 모드 1: 우리 속력 지정 → 침로/상봉시간 산출
            own_speed = self._get_float(self.own_speed_input)
            if own_speed is None or own_speed <= 0:
                self._show_error("우리 속력을 입력하세요 (양수)")
                return

            vs = own_speed / 60.0  # NM/분

            # 2차 방정식: (vs² - vt²)t² - 2(tx·vx_t + ty·vy_t)t - (tx² + ty²) = 0
            # (vx_t² + vy_t²)t² + 2(tx·vx_t + ty·vy_t)t + (tx² + ty²) = vs²·t²
            # → (vs² - vx_t² - vy_t²)t² - 2(tx·vx_t + ty·vy_t)t - (tx² + ty²) = 0
            a = vs**2 - vx_t**2 - vy_t**2
            b = -2 * (tx * vx_t + ty * vy_t)
            c = -(tx**2 + ty**2)

            discriminant = b**2 - 4 * a * c

            if a == 0:
                # 선형 방정식
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
                # 양수 중 최소값
                candidates = [t for t in [t1, t2] if t > 0.01]
                if not candidates:
                    self._show_error("산출 불가: 유효한 해가 없습니다")
                    return
                t = min(candidates)

            # 상봉 지점
            meet_x = tx + vx_t * t
            meet_y = ty + vy_t * t

            # 우리 침로
            own_course = math.degrees(math.atan2(meet_x, meet_y)) % 360

            # 상봉 지점 방위/거리
            meet_dist = math.sqrt(meet_x**2 + meet_y**2)
            meet_bearing = math.degrees(math.atan2(meet_x, meet_y)) % 360

            self._show_result(
                course=own_course,
                speed=None,
                time_min=t,
                meet_bearing=meet_bearing,
                meet_dist=meet_dist
            )
        else:
            # 모드 2: 상봉시간 지정 → 침로/속력 산출
            t_min = self._get_float(self.rendezvous_time_input)
            if t_min is None or t_min <= 0:
                self._show_error("상봉시간을 입력하세요 (양수, 분)")
                return

            t = t_min

            # t분 후 대상 위치
            meet_x = tx + vx_t * t
            meet_y = ty + vy_t * t

            # 필요 속력 (NM/분 → 노트)
            meet_dist = math.sqrt(meet_x**2 + meet_y**2)
            own_speed = meet_dist / t * 60.0

            # 우리 침로
            own_course = math.degrees(math.atan2(meet_x, meet_y)) % 360

            # 상봉 지점 방위/거리
            meet_bearing = math.degrees(math.atan2(meet_x, meet_y)) % 360

            self._show_result(
                course=own_course,
                speed=own_speed,
                time_min=None,
                meet_bearing=meet_bearing,
                meet_dist=meet_dist
            )

    def _show_result(self, course, speed, time_min, meet_bearing, meet_dist):
        """결과 표시"""
        self._error_label.hide()
        self._course_label.setText(f"권고침로: {course:06.1f}°")

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

        self._point_label.setText(f"상봉지점: 방위 {meet_bearing:06.1f}° 거리 {meet_dist:.1f} NM")
        self._result_frame.show()

    def _show_error(self, msg):
        """에러 표시"""
        self._course_label.setText("권고침로: -")
        self._speed_label.setText("권고속력: -")
        self._time_label.setText("상봉시간: -")
        self._point_label.setText("상봉지점: -")
        self._error_label.setText(msg)
        self._error_label.show()
        self._result_frame.show()
