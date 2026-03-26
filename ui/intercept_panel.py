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
    """섹션 박스 생성"""
    box = QFrame()
    box.setStyleSheet("""
        QFrame {
            background: rgba(10, 22, 40, 0.6);
            border: 1px solid #1e3a5f;
            border-radius: 6px;
        }
        QLabel { background: transparent; border: none; }
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
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("sectionPanel")
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # 제목
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

        # 내용
        content = QVBoxLayout()
        content.setContentsMargins(6, 4, 6, 4)
        content.setSpacing(6)

        # ═══ 대상 선박 ═══
        target_box, tbl = _make_box("대상 선박")
        r1 = QHBoxLayout(); r1.setSpacing(6)
        r1.addWidget(self._lbl("방위"))
        self.bearing_input = self._input("°"); r1.addWidget(self.bearing_input, 1)
        r1.addSpacing(12)
        r1.addWidget(self._lbl("거리"))
        self.distance_input = self._input("NM"); r1.addWidget(self.distance_input, 1)
        tbl.addLayout(r1)
        r2 = QHBoxLayout(); r2.setSpacing(6)
        r2.addWidget(self._lbl("침로"))
        self.target_course_input = self._input("°"); r2.addWidget(self.target_course_input, 1)
        r2.addSpacing(12)
        r2.addWidget(self._lbl("속력"))
        self.target_speed_input = self._input("kts"); r2.addWidget(self.target_speed_input, 1)
        tbl.addLayout(r2)
        content.addWidget(target_box)

        # ═══ 산출 조건 ═══
        cond_box, cbl = _make_box("산출 조건")
        r3 = QHBoxLayout(); r3.setSpacing(6)
        r3.addWidget(self._lbl("자함 속력"))
        self.own_speed_input = self._input("kts")
        self.own_speed_input.textChanged.connect(self._on_speed_changed)
        r3.addWidget(self.own_speed_input, 1)
        cbl.addLayout(r3)
        r4 = QHBoxLayout(); r4.setSpacing(6)
        r4.addWidget(self._lbl("임검시간"))
        self.rendezvous_time_input = self._input("분")
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
                qproperty-alignment: AlignCenter;
            }
            QPushButton:hover { background: #006688; border-color: #00d4ff; }
        """)
        calc_btn.setCursor(Qt.PointingHandCursor)
        calc_btn.clicked.connect(self._calculate)
        content.addWidget(calc_btn)

        # ═══ 산출 결과 (기본 숨김) ═══
        self._result_box = QFrame()
        self._result_box.setStyleSheet("""
            QFrame#resultBox {
                background: rgba(10, 30, 55, 0.8);
                border: 1px solid rgba(46, 204, 113, 0.3);
                border-radius: 6px;
            }
            QLabel { background: transparent; border: none; }
        """)
        self._result_box.setObjectName("resultBox")
        rbl = QVBoxLayout(self._result_box)
        rbl.setContentsMargins(8, 4, 8, 6)
        rbl.setSpacing(2)

        # 산출 결과 헤더 + 접기/펴기 버튼
        rh = QHBoxLayout()
        rh.addStretch()
        result_header = QLabel("산출 결과")
        result_header.setStyleSheet("""
            color: #2ecc71; font-size: 14px; font-weight: bold;
            font-family: "HY헤드라인M", "HYHeadLineM", "Malgun Gothic", sans-serif;
        """)
        result_header.setAlignment(Qt.AlignCenter)
        rh.addWidget(result_header)
        rh.addStretch()
        self._fold_btn = QPushButton("접기")
        self._fold_btn.setFixedSize(40, 20)
        self._fold_btn.setStyleSheet("""
            QPushButton { background: rgba(30,58,95,0.8); color: #8faabe; border: 1px solid #2a4a6f;
                          border-radius: 3px; font-size: 10px; font-weight: bold; }
            QPushButton:hover { color: #00d4ff; border-color: #00d4ff; }
        """)
        self._fold_btn.setCursor(Qt.PointingHandCursor)
        self._fold_btn.clicked.connect(self._toggle_fold)
        rh.addWidget(self._fold_btn)
        rbl.addLayout(rh)

        # 구분선
        sep = QFrame(); sep.setFixedHeight(1)
        sep.setStyleSheet("background: rgba(46, 204, 113, 0.2);")
        rbl.addWidget(sep)

        # 결과 내용 (접기 대상)
        self._result_content = QWidget()
        rc_layout = QVBoxLayout(self._result_content)
        rc_layout.setContentsMargins(0, 2, 0, 0)
        rc_layout.setSpacing(2)

        result_style = "color: #f0a500; font-size: 13px; font-weight: bold;"
        self._course_label = QLabel("권고침로: -"); self._course_label.setStyleSheet(result_style)
        rc_layout.addWidget(self._course_label)
        self._speed_label = QLabel("권고속력: -"); self._speed_label.setStyleSheet(result_style)
        rc_layout.addWidget(self._speed_label)
        self._time_label = QLabel("임검시간: -"); self._time_label.setStyleSheet(result_style)
        rc_layout.addWidget(self._time_label)
        self._point_label = QLabel("임검지점: -"); self._point_label.setStyleSheet(result_style)
        rc_layout.addWidget(self._point_label)

        # 경과 테이블
        self._progress_table = QFrame()
        self._progress_table.setStyleSheet("""
            QFrame { background: rgba(6, 16, 31, 0.8); border: 1px solid #1a2d4a; border-radius: 4px; }
            QLabel { background: transparent; border: none; }
        """)
        self._progress_grid = QGridLayout(self._progress_table)
        self._progress_grid.setContentsMargins(4, 2, 4, 4)
        self._progress_grid.setSpacing(1)
        self._progress_table.hide()
        rc_layout.addWidget(self._progress_table)

        self._error_label = QLabel("")
        self._error_label.setStyleSheet("color: #e74c3c; font-size: 11px; font-weight: bold;")
        self._error_label.hide()
        rc_layout.addWidget(self._error_label)

        rbl.addWidget(self._result_content)
        self._result_box.hide()
        self._folded = False
        content.addWidget(self._result_box)

        layout.addLayout(content)

    def _lbl(self, text):
        lb = QLabel(text); lb.setStyleSheet(LABEL_STYLE); return lb

    def _input(self, placeholder):
        inp = QLineEdit(); inp.setPlaceholderText(placeholder)
        inp.setFixedHeight(24); inp.setStyleSheet(INPUT_STYLE); return inp

    def _toggle_fold(self):
        self._folded = not self._folded
        self._result_content.setVisible(not self._folded)
        self._fold_btn.setText("펴기" if self._folded else "접기")

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
        try: return float(widget.text().strip())
        except (ValueError, AttributeError): return default

    def _calculate(self):
        bearing = self._get_float(self.bearing_input)
        distance = self._get_float(self.distance_input)
        target_course = self._get_float(self.target_course_input)
        target_speed = self._get_float(self.target_speed_input)

        if any(v is None for v in [bearing, distance, target_course, target_speed]):
            self._show_error("모든 대상 선박 정보를 입력하세요"); return
        if distance <= 0 or target_speed < 0:
            self._show_error("거리와 속력은 양수여야 합니다"); return

        br = math.radians(bearing)
        tx, ty = distance * math.sin(br), distance * math.cos(br)
        tc = math.radians(target_course)
        vxt, vyt = target_speed / 60 * math.sin(tc), target_speed / 60 * math.cos(tc)

        spd = self._get_float(self.own_speed_input)
        tm = self._get_float(self.rendezvous_time_input)

        if spd and spd > 0:
            vs = spd / 60
            a = vs**2 - vxt**2 - vyt**2
            b = -2 * (tx * vxt + ty * vyt)
            c = -(tx**2 + ty**2)
            d = b**2 - 4 * a * c
            if a == 0:
                if b == 0: self._show_error("산출 불가"); return
                t = -c / b
            elif d < 0:
                self._show_error("산출 불가: 자함 속력 부족"); return
            else:
                t1 = (-b + math.sqrt(d)) / (2 * a)
                t2 = (-b - math.sqrt(d)) / (2 * a)
                cands = [v for v in [t1, t2] if v > 0.01]
                if not cands: self._show_error("산출 불가"); return
                t = min(cands)
            mx, my = tx + vxt * t, ty + vyt * t
            crs = math.degrees(math.atan2(mx, my)) % 360
            md = math.sqrt(mx**2 + my**2)
            prog = self._calc_progress(tx, ty, vxt, vyt, crs, spd, t)
            self._show_result(crs, None, t, crs, md, prog)
        elif tm and tm > 0:
            mx, my = tx + vxt * tm, ty + vyt * tm
            md = math.sqrt(mx**2 + my**2)
            os = md / tm * 60
            crs = math.degrees(math.atan2(mx, my)) % 360
            self._show_result(crs, os, None, crs, md, None)
        else:
            self._show_error("자함 속력 또는 임검시간을 입력하세요")

    def _calc_progress(self, tx, ty, vxt, vyt, own_crs, own_spd, total_t):
        ov = own_spd / 60; orad = math.radians(own_crs)
        ovx, ovy = ov * math.sin(orad), ov * math.cos(orad)
        rows = []
        for i in range(1, 6):
            t = total_t * i / 5
            rx, ry = (tx + vxt * t) - ovx * t, (ty + vyt * t) - ovy * t
            brg = math.degrees(math.atan2(rx, ry)) % 360
            dist = math.sqrt(rx**2 + ry**2)
            rows.append((f"{round(t)}분 후", f"{brg:05.1f}°-{dist:.1f}NM"))
        return rows

    def _clear_grid(self):
        while self._progress_grid.count():
            item = self._progress_grid.takeAt(0)
            if item.widget(): item.widget().setParent(None)

    def _show_result(self, course, speed, time_min, mb, md, progress):
        self._error_label.hide()
        self._course_label.setText(f"권고침로: {course:05.1f}°")
        if speed is not None:
            self._speed_label.setText(f"권고속력: {speed:.1f} kts"); self._speed_label.show()
        else: self._speed_label.hide()
        if time_min is not None:
            self._time_label.setText(f"임검시간: 약 {round(time_min)}분 후"); self._time_label.show()
        else: self._time_label.hide()
        self._point_label.setText(f"임검지점: {mb:05.1f}°-{md:.1f}NM")

        self._clear_grid()
        if progress:
            hdr_s = "color: #00d4ff; font-size: 11px; font-weight: bold; padding: 2px 4px;"
            title_s = "color: #00d4ff; font-size: 13px; font-weight: bold; padding: 2px 4px;"
            cell_s = "color: #e0e8f0; font-size: 12px; font-weight: bold; padding: 2px 4px;"
            sep_s = "background: #1a2d4a;"

            # 테이블 제목
            tt = QLabel("경과별 상대 선박 위치")
            tt.setStyleSheet(title_s); tt.setAlignment(Qt.AlignCenter)
            self._progress_grid.addWidget(tt, 0, 0, 1, 2)
            # 구분선
            s1 = QFrame(); s1.setFixedHeight(1); s1.setStyleSheet(sep_s)
            self._progress_grid.addWidget(s1, 1, 0, 1, 2)
            # 헤더
            h1 = QLabel("시간경과"); h1.setStyleSheet(hdr_s); h1.setAlignment(Qt.AlignCenter)
            self._progress_grid.addWidget(h1, 2, 0)
            h2 = QLabel("선박 위치"); h2.setStyleSheet(hdr_s); h2.setAlignment(Qt.AlignCenter)
            self._progress_grid.addWidget(h2, 2, 1)
            s2 = QFrame(); s2.setFixedHeight(1); s2.setStyleSheet(sep_s)
            self._progress_grid.addWidget(s2, 3, 0, 1, 2)
            for i, (ts, ps) in enumerate(progress):
                r = i + 4
                tl = QLabel(ts); tl.setStyleSheet(cell_s); tl.setAlignment(Qt.AlignCenter)
                self._progress_grid.addWidget(tl, r, 0)
                pl = QLabel(ps); pl.setStyleSheet(cell_s); pl.setAlignment(Qt.AlignCenter)
                self._progress_grid.addWidget(pl, r, 1)
            self._progress_table.show()
        else:
            self._progress_table.hide()

        self._result_box.show()
        self._result_content.show()
        self._folded = False
        self._fold_btn.setText("접기")

    def _show_error(self, msg):
        self._course_label.setText("권고침로: -")
        self._speed_label.setText("권고속력: -"); self._speed_label.show()
        self._time_label.setText("임검시간: -"); self._time_label.show()
        self._point_label.setText("임검지점: -")
        self._clear_grid(); self._progress_table.hide()
        self._error_label.setText(msg); self._error_label.show()
        self._result_box.show(); self._result_content.show()
        self._folded = False; self._fold_btn.setText("접기")
