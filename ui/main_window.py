"""
SPT 메인 윈도우 - 사이드바 + 페이지 스택
"""
import os
import time
import datetime
from PySide6.QtWidgets import (
    QMainWindow, QWidget, QHBoxLayout, QVBoxLayout, QLabel, QPushButton,
    QStackedWidget, QFrame, QFileDialog, QSizePolicy, QApplication,
    QLineEdit, QDialog, QDateEdit
)
from PySide6.QtCore import Qt, QTimer, QSize, QDate
from PySide6.QtGui import QFont, QIcon, QColor, QPixmap, QPainter
from core.data_manager import DataManager
from ui.dashboard import DashboardView, EquipmentInventoryPanel
from ui.log_panel import LogPanel
from ui.settings_tab import SettingsTab
from ui.intercept_panel import InterceptPanel


class ExportDateDialog(QDialog):
    """내보내기 일자 선택 다이얼로그"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("내보내기 - 일자 선택")
        self.setFixedSize(320, 160)

        layout = QVBoxLayout(self)
        layout.setSpacing(12)

        label = QLabel("조회할 일자를 선택하세요:")
        layout.addWidget(label)

        self.date_edit = QDateEdit()
        self.date_edit.setCalendarPopup(True)
        self.date_edit.setDate(QDate.currentDate())
        self.date_edit.setDisplayFormat("yyyy.MM.dd")
        self.date_edit.setFixedHeight(32)
        layout.addWidget(self.date_edit)

        btn_layout = QHBoxLayout()
        btn_layout.addStretch()

        extract_btn = QPushButton("추출")
        extract_btn.setObjectName("btnAccent")
        extract_btn.setFixedSize(80, 32)
        extract_btn.clicked.connect(self.accept)
        btn_layout.addWidget(extract_btn)

        cancel_btn = QPushButton("취소")
        cancel_btn.setFixedSize(80, 32)
        cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(cancel_btn)

        layout.addLayout(btn_layout)

    def get_selected_date(self):
        return self.date_edit.date().toPython()


class SidebarFrame(QFrame):
    """사이드바 프레임 (고정 크기)"""
    def __init__(self, parent=None):
        super().__init__(parent)


class WatermarkWidget(QWidget):
    """전체 화면 중앙 워터마크 위젯 - 앞에 배치하되 마우스 투과"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self._bg_pixmap = None
        self.setAttribute(Qt.WA_TransparentForMouseEvents, True)
        self.setAttribute(Qt.WA_TranslucentBackground, True)

    def set_background_mark(self, pixmap):
        self._bg_pixmap = pixmap

    def paintEvent(self, event):
        if self._bg_pixmap:
            painter = QPainter(self)
            painter.setOpacity(0.07)
            size = int(min(self.width(), self.height()) * 0.55)
            size = max(size, 300)
            scaled = self._bg_pixmap.scaled(size, size, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            x = (self.width() - scaled.width()) // 2
            y = (self.height() - scaled.height()) // 2
            painter.drawPixmap(x, y, scaled)
            painter.end()


class MainWindow(QMainWindow):
    def __init__(self, data_manager: DataManager):
        super().__init__()
        self.dm = data_manager
        self.setWindowTitle("BridgeBoard")
        self.setMinimumSize(1400, 850)
        self.resize(1600, 950)

        self._load_styles()
        self._setup_ui()

        self.auto_save_timer = QTimer(self)
        self.auto_save_timer.timeout.connect(self.dm.save)
        self.auto_save_timer.start(30000)

        self.clock_timer = QTimer(self)
        self.clock_timer.timeout.connect(self._update_clock)
        self.clock_timer.start(1000)

    def _load_styles(self):
        style_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "resources", "styles.qss"
        )
        if os.path.exists(style_path):
            with open(style_path, "r", encoding="utf-8") as f:
                self.setStyleSheet(f.read())

    def _setup_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QHBoxLayout(central)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # === 사이드바 ===
        sidebar = SidebarFrame()
        sidebar.setObjectName("sidebar")
        sidebar.setFixedWidth(240)
        sidebar_layout = QVBoxLayout(sidebar)
        sidebar_layout.setContentsMargins(0, 0, 0, 0)
        sidebar_layout.setSpacing(0)

        # 로고 영역 - BridgeBoard + 버전 정보
        logo_frame = QFrame()
        logo_frame.setFixedHeight(64)
        logo_frame.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        logo_frame.setFixedWidth(240)
        logo_frame.setStyleSheet("""
            background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                stop:0 #0d2137, stop:1 #06101f);
            border-bottom: 1px solid #1a2d4a;
        """)
        logo_v = QVBoxLayout(logo_frame)
        logo_v.setContentsMargins(6, 10, 10, 6)
        logo_v.setSpacing(0)

        # 상단: BridgeBoard + Ver. 1
        logo_top = QHBoxLayout()
        logo_top.setSpacing(6)

        logo_title = QLabel("BridgeBoard")
        logo_title.setStyleSheet("""
            color: #00d4ff; font-size: 20px; font-weight: bold;
            font-family: "HY헤드라인M", "HYHeadLineM", "Malgun Gothic", sans-serif;
            letter-spacing: 2px; background: transparent; border: none;
        """)
        logo_top.addWidget(logo_title)

        ver_label = QLabel("Ver. 1")
        ver_label.setStyleSheet("color: #5a7a9a; font-size: 10px; font-weight: bold; background: transparent; border: none;")
        logo_top.addWidget(ver_label)
        logo_top.addStretch()

        logo_v.addLayout(logo_top)

        # 하단: Made by JS Shin (#6 간격 축소 + bold)
        credit_label = QLabel("Made by JS Shin")
        credit_label.setStyleSheet("color: #3a5a7a; font-size: 9px; font-weight: bold; background: transparent; border: none;")
        logo_v.addWidget(credit_label)

        sidebar_layout.addWidget(logo_frame)

        # 해양경찰 마크 경로 저장 (워터마크용)
        self._mark_pixmap = None
        img_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "resources", "0504_sbimg2.png"
        )
        if os.path.exists(img_path):
            self._mark_pixmap = QPixmap(img_path)

        # 탭 버튼 (간격 추가)
        self.nav_buttons = []
        for key, label in [("dashboard", "  대시보드"), ("settings", "  설정")]:
            btn = QPushButton(label)
            btn.setCheckable(True)
            btn.setFixedHeight(40)
            btn.setMaximumHeight(40)
            btn.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
            btn.setProperty("nav_key", key)
            btn.clicked.connect(lambda checked, k=key: self._switch_page(k))
            sidebar_layout.addWidget(btn)
            self.nav_buttons.append(btn)
            # 탭 사이 구분선
            sep = QFrame()
            sep.setFixedHeight(1)
            sep.setStyleSheet("background: #1a2d4a;")
            sidebar_layout.addWidget(sep)

        # 설정과 장비 패널 사이 간격 (#9)
        spacer = QFrame()
        spacer.setFixedHeight(12)
        spacer.setStyleSheet("background: transparent; border: none;")
        sidebar_layout.addWidget(spacer)

        # 장비 보유 목록 (사이드바)
        self.eq_inventory_panel = EquipmentInventoryPanel()
        sidebar_layout.addWidget(self.eq_inventory_panel, 1)

        # 임검침로 산출 패널 (장비 보유 목록 하단)
        self.intercept_panel = InterceptPanel()
        sidebar_layout.addWidget(self.intercept_panel, 0)

        # 사이드바 하단 stretch (장비 패널 숨김 시 빈 공간 채움)
        self._sidebar_stretch = QWidget()
        self._sidebar_stretch.setStyleSheet("background: transparent; border: none;")
        sidebar_layout.addWidget(self._sidebar_stretch, 1)

        main_layout.addWidget(sidebar)

        # === 콘텐츠 영역 ===
        content_layout = QVBoxLayout()
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.setSpacing(0)

        # 헤더 바 (높이 확대)
        header = QFrame()
        header.setObjectName("headerBar")
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(20, 8, 20, 8)

        # 작전명 (클릭으로 편집) - 넓은 영역
        title_layout = QVBoxLayout()
        title_layout.setSpacing(0)

        title_text = self.dm.operation_title or "클릭하여 작전명을 입력하세요"
        self.header_title = QLabel(title_text)
        self.header_title.setObjectName("headerTitle")
        self.header_title.setStyleSheet("""
            font-size: 27px; font-weight: bold; color: #e0e8f0; letter-spacing: 2px;
            font-family: "HY헤드라인M", "HYHeadLineM", "Malgun Gothic", sans-serif;
        """)
        self.header_title.setCursor(Qt.PointingHandCursor)
        self.header_title.mousePressEvent = self._start_title_edit
        title_layout.addWidget(self.header_title)

        self.title_input = QLineEdit()
        self.title_input.setObjectName("headerTitleInput")
        self.title_input.setFixedHeight(36)
        self.title_input.setStyleSheet("""
            font-size: 27px; font-weight: bold;
            font-family: "HY헤드라인M", "HYHeadLineM", "Malgun Gothic", sans-serif;
        """)
        self.title_input.setPlaceholderText("작전명을 입력하세요...")
        self.title_input.returnPressed.connect(self._save_title)
        self.title_input.hide()
        title_layout.addWidget(self.title_input)

        header_layout.addLayout(title_layout, 2)
        header_layout.addStretch()

        # 시계
        clock_layout = QVBoxLayout()
        clock_layout.setSpacing(0)
        self.clock_label = QLabel()
        self.clock_label.setObjectName("headerClock")
        self.clock_label.setAlignment(Qt.AlignRight)
        clock_layout.addWidget(self.clock_label)

        self.date_label = QLabel()
        self.date_label.setObjectName("headerDate")
        self.date_label.setAlignment(Qt.AlignRight)
        clock_layout.addWidget(self.date_label)
        header_layout.addLayout(clock_layout)

        self._update_clock()
        content_layout.addWidget(header)

        # 페이지 스택
        self.page_stack = QStackedWidget()

        dashboard_page = QWidget()
        dp_layout = QHBoxLayout(dashboard_page)
        dp_layout.setContentsMargins(8, 8, 8, 8)
        dp_layout.setSpacing(8)

        self.dashboard = DashboardView(self.dm)
        self.dashboard.set_equipment_panel(self.eq_inventory_panel)
        dp_layout.addWidget(self.dashboard, 3)

        # 로그 패널: 대시보드와 동일 레벨 + sectionPanel 래퍼
        log_wrapper = QFrame()
        log_wrapper.setObjectName("sectionPanel")
        lw_layout = QVBoxLayout(log_wrapper)
        lw_layout.setContentsMargins(0, 0, 0, 0)
        lw_layout.setSpacing(0)
        self.log_panel = LogPanel(self.dm)
        lw_layout.addWidget(self.log_panel)
        dp_layout.addWidget(log_wrapper, 1)

        self.dashboard.refresh()

        self.dashboard.log_message.connect(self.log_panel.append_log)
        self.log_panel.export_requested.connect(self._export_data)
        self.page_stack.addWidget(dashboard_page)

        self.settings_tab = SettingsTab(self.dm)
        self.settings_tab.data_changed.connect(self._on_data_changed)
        self.page_stack.addWidget(self.settings_tab)

        content_layout.addWidget(self.page_stack, 1)
        main_layout.addLayout(content_layout, 1)

        # 워터마크 오버레이 (전체 화면 중앙, 앞에 배치하되 마우스 투과)
        self._watermark = WatermarkWidget(self)
        if self._mark_pixmap:
            self._watermark.set_background_mark(self._mark_pixmap)
        self._watermark.raise_()

        # 저장된 폰트 크기 복원
        saved_font = self.dm.ui_settings.get("content_font_size")
        if saved_font:
            self._content_font_size = saved_font
            self._apply_content_font()

        self._switch_page("dashboard")

    def _start_title_edit(self, event):
        self.header_title.hide()
        if self.dm.operation_title:
            self.title_input.setText(self.dm.operation_title)
        else:
            # 날짜 자동 입력
            date_prefix = time.strftime("[%y.%m.%d] ")
            self.title_input.setText(date_prefix)
        self.title_input.show()
        self.title_input.setFocus()
        # 커서를 맨 뒤로
        self.title_input.setCursorPosition(len(self.title_input.text()))

    def _save_title(self):
        title = self.title_input.text().strip()
        self.dm.set_title(title)
        self.header_title.setText(title or "클릭하여 작전명을 입력하세요")
        self.title_input.hide()
        self.header_title.show()

    def _switch_page(self, key: str):
        idx = {"dashboard": 0, "settings": 1}.get(key, 0)
        self.page_stack.setCurrentIndex(idx)

        for btn in self.nav_buttons:
            is_active = btn.property("nav_key") == key
            btn.setChecked(is_active)
            btn.setProperty("active", "true" if is_active else "false")
            btn.setStyleSheet(btn.styleSheet())

        # 장비 보유 목록은 대시보드에서만 표출 (#3)
        self.eq_inventory_panel.setVisible(key == "dashboard")

        if key == "dashboard":
            self.dashboard.refresh()
        elif key == "settings":
            self.settings_tab.refresh()

    def _update_clock(self):
        self.clock_label.setText(time.strftime("%H:%M:%S"))
        weekdays = ["월", "화", "수", "목", "금", "토", "일"]
        wd = weekdays[datetime.datetime.now().weekday()]
        self.date_label.setText(time.strftime(f"%m.%d ({wd})"))

    def _on_data_changed(self):
        self.dashboard.refresh()

    def _export_data(self):
        dialog = ExportDateDialog(self)
        if dialog.exec() != QDialog.Accepted:
            return
        selected_date = dialog.get_selected_date()

        filepath, _ = QFileDialog.getSaveFileName(
            self, "데이터 내보내기",
            f"SPT_작전기록_{selected_date.strftime('%Y%m%d')}",
            "Excel (*.xlsx);;CSV (*.csv)"
        )
        if not filepath:
            return
        if filepath.endswith(".xlsx"):
            self.dm.export_xlsx(filepath, filter_date=selected_date)
        else:
            self.dm.export_csv(filepath, filter_date=selected_date)
        self.log_panel.append_log(f"데이터 내보내기 완료: {os.path.basename(filepath)}")

    def resizeEvent(self, event):
        """창 크기 변경 시 워터마크 리사이즈 + 초기 폰트 계산"""
        super().resizeEvent(event)

        # 워터마크 위치 업데이트 (전체 화면 중앙, 항상 맨 앞)
        if hasattr(self, '_watermark'):
            self._watermark.setGeometry(0, 0, self.width(), self.height())
            self._watermark.raise_()

        # 폰트 크기가 아직 설정되지 않은 경우 (최초 리사이즈)만 자동 계산
        if not hasattr(self, '_content_font_size'):
            base_width = 1600
            base_height = 950
            base_font = 13.0
            w = self.width()
            h = self.height()
            scale = min(w / base_width, h / base_height)
            scale = max(0.6, min(scale, 1.5))
            self._content_font_size = max(9, int(base_font * scale))
            self._apply_content_font()

    def wheelEvent(self, event):
        """Ctrl+휠로 대시보드+로그 패널 폰트 동시 확대/축소"""
        if event.modifiers() & Qt.ControlModifier:
            if not hasattr(self, '_content_font_size'):
                self._content_font_size = 13
            delta = event.angleDelta().y()
            if delta > 0:
                self._content_font_size = min(self._content_font_size + 1, 24)
            elif delta < 0:
                self._content_font_size = max(self._content_font_size - 1, 8)
            self._apply_content_font()
            # 설정 저장
            self.dm.ui_settings["content_font_size"] = self._content_font_size
            event.accept()
        else:
            super().wheelEvent(event)

    def _apply_content_font(self):
        """대시보드(3섹션)에만 폰트 적용, 제목/뱃지는 고정"""
        sz = self._content_font_size
        font_style = f"QWidget {{ font-size: {sz}px; }}"
        self.dashboard.setStyleSheet(font_style)
        # 제목/뱃지 폰트 고정 복원
        self.dashboard.restore_fixed_fonts()
        self.log_panel.update_title_font(sz)

    def closeEvent(self, event):
        self.dm.save()
        super().closeEvent(event)
