"""
SPT 메인 윈도우 - 사이드바 + 페이지 스택
"""
import os
import time
from PySide6.QtWidgets import (
    QMainWindow, QWidget, QHBoxLayout, QVBoxLayout, QLabel, QPushButton,
    QStackedWidget, QFrame, QFileDialog, QSizePolicy, QApplication,
    QLineEdit
)
from PySide6.QtCore import Qt, QTimer, QSize
from PySide6.QtGui import QFont, QIcon, QColor
from core.data_manager import DataManager
from ui.dashboard import DashboardView
from ui.log_panel import LogPanel
from ui.settings_tab import SettingsTab


class MainWindow(QMainWindow):
    def __init__(self, data_manager: DataManager):
        super().__init__()
        self.dm = data_manager
        self.setWindowTitle("작전 통제 현황")
        self.setMinimumSize(1400, 850)
        self.resize(1600, 950)

        # 스타일시트 로드
        self._load_styles()

        # UI 구성
        self._setup_ui()

        # 자동 저장 타이머 (30초)
        self.auto_save_timer = QTimer(self)
        self.auto_save_timer.timeout.connect(self.dm.save)
        self.auto_save_timer.start(30000)

        # 시계 타이머
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
        sidebar = QFrame()
        sidebar.setObjectName("sidebar")
        sidebar.setFixedWidth(180)
        sidebar_layout = QVBoxLayout(sidebar)
        sidebar_layout.setContentsMargins(0, 0, 0, 0)
        sidebar_layout.setSpacing(0)

        # 로고 영역
        logo_frame = QFrame()
        logo_frame.setFixedHeight(70)
        logo_frame.setStyleSheet("""
            background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                stop:0 #0d2137, stop:1 #06101f);
            border-bottom: 1px solid #1a2d4a;
        """)
        logo_layout = QVBoxLayout(logo_frame)
        logo_layout.setContentsMargins(12, 10, 12, 10)
        logo_title = QLabel("SPT")
        logo_title.setStyleSheet("""
            color: #00d4ff; font-size: 22px; font-weight: bold;
            letter-spacing: 4px; background: transparent; border: none;
        """)
        logo_layout.addWidget(logo_title)
        logo_sub = QLabel("작전 통제 현황")
        logo_sub.setStyleSheet("""
            color: #5a7a9a; font-size: 9px; letter-spacing: 1px;
            background: transparent; border: none;
        """)
        logo_layout.addWidget(logo_sub)
        sidebar_layout.addWidget(logo_frame)

        # 탭 버튼
        self.nav_buttons = []
        nav_items = [
            ("dashboard", "대시보드"),
            ("settings", "설정"),
        ]

        for key, label in nav_items:
            btn = QPushButton(f"  {label}")
            btn.setCheckable(True)
            btn.setFixedHeight(48)
            btn.setProperty("nav_key", key)
            btn.clicked.connect(lambda checked, k=key: self._switch_page(k))
            sidebar_layout.addWidget(btn)
            self.nav_buttons.append(btn)

        sidebar_layout.addStretch()

        # Export 버튼
        export_btn = QPushButton("  데이터 내보내기")
        export_btn.setFixedHeight(48)
        export_btn.setStyleSheet("""
            QPushButton {
                background: transparent; border: none; color: #5a7a9a;
                padding: 14px 12px; text-align: left; font-size: 12px;
                border-left: 3px solid transparent;
            }
            QPushButton:hover {
                color: #f0a500; background: rgba(240, 165, 0, 0.05);
                border-left: 3px solid rgba(240, 165, 0, 0.3);
            }
        """)
        export_btn.clicked.connect(self._export_data)
        sidebar_layout.addWidget(export_btn)

        main_layout.addWidget(sidebar)

        # === 콘텐츠 영역 ===
        content_layout = QVBoxLayout()
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.setSpacing(0)

        # 헤더 바 - 클릭하여 제목 편집 가능
        header = QFrame()
        header.setObjectName("headerBar")
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(20, 8, 20, 8)

        # 제목 영역 (클릭으로 편집)
        title_layout = QVBoxLayout()
        title_layout.setSpacing(0)

        # 제목 표시 라벨
        title_text = self.dm.operation_title or "제목을 클릭하여 작전명을 입력하세요"
        self.header_title = QLabel(title_text)
        self.header_title.setObjectName("headerTitle")
        self.header_title.setCursor(Qt.PointingHandCursor)
        self.header_title.mousePressEvent = self._start_title_edit
        title_layout.addWidget(self.header_title)

        # 제목 편집 입력 (숨김)
        self.title_input = QLineEdit()
        self.title_input.setObjectName("headerTitleInput")
        self.title_input.setFixedHeight(32)
        self.title_input.setPlaceholderText("작전명을 입력하세요...")
        self.title_input.returnPressed.connect(self._save_title)
        self.title_input.hide()
        title_layout.addWidget(self.title_input)

        header_layout.addLayout(title_layout, 1)
        header_layout.addStretch()

        # 현재 시각
        clock_layout = QVBoxLayout()
        clock_layout.setSpacing(0)
        self.clock_label = QLabel()
        self.clock_label.setObjectName("headerClock")
        self.clock_label.setAlignment(Qt.AlignRight)
        clock_layout.addWidget(self.clock_label)

        self.date_label = QLabel()
        self.date_label.setObjectName("headerSubtitle")
        self.date_label.setAlignment(Qt.AlignRight)
        clock_layout.addWidget(self.date_label)
        header_layout.addLayout(clock_layout)

        self._update_clock()
        content_layout.addWidget(header)

        # 페이지 스택
        self.page_stack = QStackedWidget()

        # === 대시보드 페이지 ===
        dashboard_page = QWidget()
        dashboard_page_layout = QHBoxLayout(dashboard_page)
        dashboard_page_layout.setContentsMargins(0, 0, 0, 0)
        dashboard_page_layout.setSpacing(0)

        self.dashboard = DashboardView(self.dm)
        dashboard_page_layout.addWidget(self.dashboard, 10)

        self.log_panel = LogPanel(self.dm)
        dashboard_page_layout.addWidget(self.log_panel, 3)

        self.dashboard.log_message.connect(self.log_panel.append_log)

        self.page_stack.addWidget(dashboard_page)  # 0: dashboard

        # === 설정 페이지 ===
        self.settings_tab = SettingsTab(self.dm)
        self.settings_tab.data_changed.connect(self._on_data_changed)
        self.page_stack.addWidget(self.settings_tab)  # 1: settings

        content_layout.addWidget(self.page_stack, 1)
        main_layout.addLayout(content_layout, 1)

        # 첫 번째 탭 활성화
        self._switch_page("dashboard")

    def _start_title_edit(self, event):
        """제목 클릭 → 편집 모드"""
        self.header_title.hide()
        self.title_input.setText(self.dm.operation_title)
        self.title_input.show()
        self.title_input.setFocus()
        self.title_input.selectAll()

    def _save_title(self):
        """제목 저장"""
        title = self.title_input.text().strip()
        self.dm.set_title(title)
        self.header_title.setText(title or "제목을 클릭하여 작전명을 입력하세요")
        self.title_input.hide()
        self.header_title.show()

    def _switch_page(self, key: str):
        page_map = {"dashboard": 0, "settings": 1}
        idx = page_map.get(key, 0)
        self.page_stack.setCurrentIndex(idx)

        for btn in self.nav_buttons:
            is_active = btn.property("nav_key") == key
            btn.setChecked(is_active)
            btn.setProperty("active", "true" if is_active else "false")
            btn.setStyleSheet(btn.styleSheet())

        if key == "dashboard":
            self.dashboard.refresh()
        elif key == "settings":
            self.settings_tab.refresh()

    def _update_clock(self):
        now = time.strftime("%H:%M:%S")
        self.clock_label.setText(now)
        date_str = time.strftime("%Y년 %m월 %d일")
        weekdays = ["월요일", "화요일", "수요일", "목요일", "금요일", "토요일", "일요일"]
        import datetime
        weekday = weekdays[datetime.datetime.now().weekday()]
        self.date_label.setText(f"{date_str} {weekday}")

    def _on_data_changed(self):
        self.dashboard.refresh()

    def _export_data(self):
        filepath, _ = QFileDialog.getSaveFileName(
            self, "데이터 내보내기",
            f"SPT_작전기록_{time.strftime('%Y%m%d_%H%M%S')}",
            "Excel (*.xlsx);;CSV (*.csv)"
        )
        if not filepath:
            return
        if filepath.endswith(".xlsx"):
            self.dm.export_xlsx(filepath)
        else:
            self.dm.export_csv(filepath)
        self.log_panel.append_log(f"데이터 내보내기 완료: {os.path.basename(filepath)}")

    def closeEvent(self, event):
        self.dm.save()
        super().closeEvent(event)
