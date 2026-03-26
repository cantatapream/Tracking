"""
임검침로 산출 패널
"""
import math
from PySide6.QtWidgets import (
    QFrame, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QSizePolicy, QGridLayout, QWidget
)
from PySide6.QtCore import Qt


def _make_box(title_text):
    """섹션 박스 (테두리 + 제목) 생성"""
    box = QFrame()
    box.setStyleSheet("""
        QFrame {
            background: rgba(10, 22, 40, 0.6);
            border: 1px solid #1e3a5f;
            border-radius: 6px;
        }
        QLabel { background: transparent; border: none; }
        QLineEdit { background: transparent; border: none; }
    """)
    bl = QVBoxLayout(box)
    bl.setContentsMargins(8, 4, 8, 6)
    bl.setSpacing(4)

    header = QLabel(title_text)
    header.setStyleSheet("""
        color: #00d4ff; font-size: 14px; font-weight: bold;
        font-family: "HY헤드라인M", "HYHeadLineM", "Malgun Gothic", sans-serif;
        padding: 0; border: none;
    """)
    bl.addWidget(header)
    return box, bl


INPUT_STYLE = """
    QLineEdit {
        background: #0a1628; color: #e0e8f0; border: 1px solid #1e3a5f;
        border-radius: 3px; padding: 2px 4px; font-size: 12px;
    }
    QLineEdit:focus { border-color: #00d4ff; }
"""
DISABLED_STYLE = """
    QLineEdit {
        background: #0d1520; color: #3a4a5a; border: 1px solid #152030;
        border-radius: 3px; padding: 2px 4px; font-size: 12px;
    }
"""
LABEL_STYLE = "color: #c8d6e5; font-size: 13px; background: transparent; border: none;"


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

        # 제목 영역 (장비 보유 목록과 동일)
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

        # 내용 영역
        content = QVBoxLayout()
        content.setContentsMargins(6, 4, 6, 4)
        content.setSpacing(6)

        # ═══ 대상 선박 박스 ═══
        target_box, tbl = _make_box("대상 선박")

        r1 = QHBoxLayout()
        r1.setSpacing(6)
        lb1 = QLabel("방위")
        lb1.setStyleSheet(LABEL_STYLE)
        r1.addWidget(lb1)
        self.bearing_input = QLineEdit()
        self.bearing_input.setPlaceholderText("°")
        self.bearing_input.setFixedHeight(24)
        self.bearing_input.setStyleSheet(INPUT_STYLE)
        r1.addWidget(self.bearing_input, 1)
        r1.addSpacing(12)
        lb2 = QLabel("거리")
        lb2.setStyleSheet(LABEL_STYLE)
        r1.addWidget(lb2)
        self.distance_input = QLineEdit()
        self.distance_input.setPlaceholderText("NM")
        self.distance_input.setFixedHeight(24)
        self.distance_input.setStyleSheet(INPUT_STYLE)
        r1.addWidget(self.distance_input, 1)
        tbl.addLayout(r1)

        r2 = QHBoxLayout()
        r2.setSpacing(6)
        lb3 = QLabel("침로")
        lb3.setStyleSheet(LABEL_STYLE)
        r2.addWidget(lb3)
        self.target_course_input = QLineEdit()
        self.target_course_input.setPlaceholderText("°")
        self.target_course_input.setFixedHeight(24)
        self.target_course_input.setStyleSheet(INPUT_STYLE)
        r2.addWidget(self.target_course_input, 1)
        r2.addSpacing(12)
        lb4 = QLabel("속력")
        lb4.setStyleSheet(LABEL_STYLE)
        r2.addWidget(lb4)
        self.target_speed_input = QLineEdit()
        self.target_speed_input.setPlaceholderText("kts")
        self.target_speed_input.setFixedHeight(24)
        self.target_speed_input.setStyleSheet(INPUT_STYLE)
        r2.addWidget(self.target_speed_input, 1)
        tbl.addLayout(r2)

        content.addWidget(target_box)

        # ═══ 산출 조건 박스 ═══
        cond_box, cbl = _make_box("산출 조건")

        r3 = QHBoxLayout()
        r3.setSpacing(6)
        lb5 = QLabel("자함 속력")
        lb5.setStyleSheet(LABEL_STYLE)
        r3.addWidget(lb5)
        self.own_speed_input = QLineEdit()
        self.own_speed_input.setPlaceholderText("kts")
        self.own_speed_input.setFixedHeight(24)
        self.own_speed_input.setStyleSheet(INPUT_STYLE)
        self.own_speed_input.textChanged.connect(self._on_speed_changed)
        r3.addWidget(self.own_speed_input, 1)
        cbl.addLayout(r3)

        r4 = QHBoxLayout()
        r4.setSpacing(6)
        lb6 = QLabel("임검시간")
        lb6.setStyleSheet(LABEL_STYLE)
        r4.addWidget(lb6)
        self.rendezvous_time_input = QLineEdit()
        self.rendezvous_time_input.setPlaceholderText("분")
        self.rendezvous_time_input.setFixedHeight(24)
        self.rendezvous_time_input.setStyleSheet(INPUT_STYLE)
        self.rendezvous_time_input.textChanged.connect(self._on_time_changed)
        r4.addWidget(self.rendezvous_time_input, 1)
        cbl.addLayout(r4)

        content.addWidget(cond_box)

        # ═══ 산출 버튼 ═══
        calc_btn = QPushButton("산  출")
        calc_btn.setFixedHeight(36)
        calc_btn.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #005577, stop:1 #004466);
                border: 1px solid #0088aa; color: #00d4ff; border-radius: 6px;
                font-size: 14px; font-weight: bold;
            }
            QPushButton:hover { background: #006688; border-color: #00d4ff; }
        """)
        calc_btn.setCursor(Qt.PointingHandCursor)
        calc_btn.clicked.connect(self._calculate)
        content.addWidget(calc_btn)

        # ═══ 산출 결과 박스 (기본 숨김) ═══
        self._result_box, self._rbl = _make_box("산출 결과")
        self._result_box.setStyleSheet("""
            QFrame {
                background: rgba(10, 30, 55, 0.8);
                border: 1px solid rgba(46, 204, 113, 0.3);
                border-radius: 6px;
            }
            QLabel { background: transparent; border: none; }
        """)
        # 결과 제목 재설정
        result_header = self._rbl.itemAt(0).widget()
        result_header.setStyleSheet("""
            color: #2ecc71; font-size: 14px; font-weight: bold;
            font-family: "HY헤드라인M", "HYHeadLineM", "Malgun Gothic", sans-serif;
            padding: 0; border: none;
        """)

        result_style = "color: #f0a500; font-size: 13px; font-weight: bold;"

        self._course_label = QLabel("권고침로: -")
        self._course_label.setStyleSheet(result_style)
        self._rbl.addWidget(self._course_label)

        self._speed_label = QLabel("권고속력: -")
        self._speed_label.setStyleSheet(result_style)
        self._rbl.addWidget(self._speed_label)

        self._time_label = QLabel("임검시간: -")
        self._time_label.setStyleSheet(result_style)
        self._rbl.addWidget(self._time_label)

        self._point_label = QLabel("임검지점: -")
        self._point_label.setStyleSheet(result_style)
        self._rbl.addWidget(self._point_label)

        # 경과별 상대 위치 테이블
        self._progress_title = QLabel("경과별 상대선박 위치")
        self._progress_title.setStyleSheet("color: #8faabe; font-size: 12px; font-weight: bold; padding-top: 4px;")
        self._progress_title.hide()
        self._rbl.addWidget(self._progress_title)

        self._progress_table = QFrame()
        self._progress_table.setStyleSheet("""
            QFrame { background: rgba(6, 16, 31, 0.8); border: 1px solid #1a2d4a; border-radius: 4px; }
            QLabel { background: transparent; border: none; }
        """)
        self._progress_grid = QGridLayout(self._progress_table)
        self._progress_grid.setContentsMargins(4, 2, 4, 2)
        self._progress_grid.setSpacing(1)
        self._progress_table.hide()
        self._rbl.addWidget(self._progress_table)

        self._error_label = QLabel("")
        self._error_label.setStyleSheet("color: #e74c3c; font-size: 11px; font-weight: bold;")
        self._error_label.hide()
        self._rbl.addWidget(self._error_label)

        self._result_box.hide()
        content.addWidget(self._result_box)

        layout.addLayout(content)

    def _on_speed_changed(self, text):
        if text.strip():
            self.rendezvous_time_input.setEnabled(False)
            self.rendezvous_time_input.setStyleSheet(DISABLED_STYLE)
        else:
            self.rendezvous_time_input.setEnabled(True)
            self.rendezvous_time_input.setStyleSheet(INPUT_STYLE)

    def _on_time_changed(self, text):
        if text.strip():
            self.own_speed_input.setEnabled(False)
            self.own_speed_input.setStyleSheet(DISABLED_STYLE)
        else:
            self.own_speed_input.setEnabled(True)
            self.own_speed_input.setStyleSheet(INPUT_STYLE)

    def _get_float(self, widget, default=None):
        try:
            return float(widget.text().strip())
        except (ValueError, AttributeError):
            return default

    def _calculate(self):
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
                self._show_error("산출 불가: 자함 속력이 부족합니다")
                return
            else:
                t1 = (-b + math.sqrt(discriminant)) / (2 * a)
                t2 = (-b - math.sqrt(discriminant)) / (2 * a)
                candidates = [v for v in [t1, t2] if v > 0.01]
                if not candidates:
                    self._show_error("산출 불가: 유효한 해가 없습니다")
                    return
                t = min(candidates)

            meet_x = tx + vx_t * t
            meet_y = ty + vy_t * t
            own_course = math.degrees(math.atan2(meet_x, meet_y)) % 360
            meet_dist = math.sqrt(meet_x**2 + meet_y**2)

            progress = self._calc_progress(tx, ty, vx_t, vy_t, own_course, own_speed_val, t)
            self._show_result(own_course, None, t, own_course, meet_dist, progress)

        elif time_val and time_val > 0:
            t = time_val
            meet_x = tx + vx_t * t
            meet_y = ty + vy_t * t
            meet_dist = math.sqrt(meet_x**2 + meet_y**2)
            own_speed = meet_dist / t * 60.0
            own_course = math.degrees(math.atan2(meet_x, meet_y)) % 360

            self._show_result(own_course, own_speed, None, own_course, meet_dist, None)
        else:
            self._show_error("자함 속력 또는 임검시간을 입력하세요")

    def _calc_progress(self, tx, ty, vx_t, vy_t, own_course, own_speed_kts, total_t):
        """5분할: 우리 함 기준 대상 선박의 상대 방위/거리"""
        own_rad = math.radians(own_course)
        own_vx = own_speed_kts / 60.0 * math.sin(own_rad)
        own_vy = own_speed_kts / 60.0 * math.cos(own_rad)
        rows = []
        for i in range(1, 6):
            t = total_t * i / 5
            rel_x = (tx + vx_t * t) - own_vx * t
            rel_y = (ty + vy_t * t) - own_vy * t
            brg = math.degrees(math.atan2(rel_x, rel_y)) % 360
            dist = math.sqrt(rel_x**2 + rel_y**2)
            t_round = round(t)
            rows.append((f"{t_round}분 후", f"{brg:05.1f}°-{dist:.1f}NM"))
        return rows

    def _clear_progress_table(self):
        while self._progress_grid.count():
            item = self._progress_grid.takeAt(0)
            if item.widget():
                item.widget().setParent(None)

    def _show_result(self, course, speed, time_min, meet_bearing, meet_dist, progress):
        self._error_label.hide()
        self._course_label.setText(f"권고침로: {course:05.1f}°")

        if speed is not None:
            self._speed_label.setText(f"권고속력: {speed:.1f} kts")
            self._speed_label.show()
        else:
            self._speed_label.hide()

        if time_min is not None:
            self._time_label.setText(f"임검시간: 약 {round(time_min)}분 후")
            self._time_label.show()
        else:
            self._time_label.hide()

        self._point_label.setText(f"임검지점: {meet_bearing:05.1f}°-{meet_dist:.1f}NM")

        self._clear_progress_table()
        if progress:
            hdr_style = "color: #00d4ff; font-size: 11px; font-weight: bold; padding: 2px 4px;"
            cell_style = "color: #e0e8f0; font-size: 12px; font-weight: bold; padding: 2px 4px;"
            sep_style = "background: #1a2d4a;"

            # 헤더
            h1 = QLabel("시간경과")
            h1.setStyleSheet(hdr_style)
            h1.setAlignment(Qt.AlignCenter)
            self._progress_grid.addWidget(h1, 0, 0)
            h2 = QLabel("선박 위치")
            h2.setStyleSheet(hdr_style)
            h2.setAlignment(Qt.AlignCenter)
            self._progress_grid.addWidget(h2, 0, 1)

            # 헤더 구분선
            sep = QFrame()
            sep.setFixedHeight(1)
            sep.setStyleSheet(sep_style)
            self._progress_grid.addWidget(sep, 1, 0, 1, 2)

            for i, (time_str, pos_str) in enumerate(progress):
                row = i + 2
                t_label = QLabel(time_str)
                t_label.setStyleSheet(cell_style)
                t_label.setAlignment(Qt.AlignCenter)
                self._progress_grid.addWidget(t_label, row, 0)
                p_label = QLabel(pos_str)
                p_label.setStyleSheet(cell_style)
                p_label.setAlignment(Qt.AlignCenter)
                self._progress_grid.addWidget(p_label, row, 1)

            self._progress_title.show()
            self._progress_table.show()
        else:
            self._progress_title.hide()
            self._progress_table.hide()

        self._result_box.show()
        # 영역 확장을 위해 레이아웃 갱신
        self.updateGeometry()
        if self.parent():
            self.parent().updateGeometry()

    def _show_error(self, msg):
        self._course_label.setText("권고침로: -")
        self._speed_label.setText("권고속력: -")
        self._time_label.setText("임검시간: -")
        self._point_label.setText("임검지점: -")
        self._clear_progress_table()
        self._progress_title.hide()
        self._progress_table.hide()
        self._error_label.setText(msg)
        self._error_label.show()
        self._result_box.show()
        self.updateGeometry()
        if self.parent():
            self.parent().updateGeometry()
