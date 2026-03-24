"""
SPT 메인 윈도우 - 사이드바 + 페이지 스택
"""
import os
import time
import datetime
from PySide6.QtWidgets import (
    QMainWindow, QWidget, QHBoxLayout, QVBoxLayout, QLabel, QPushButton,
    QStackedWidget, QFrame, QFileDialog, QSizePolicy, QApplication,
    QLineEdit
)
from PySide6.QtCore import Qt, QTimer, QSize
from PySide6.QtGui import QFont, QIcon, QColor, QPixmap
from core.data_manager import DataManager
from ui.dashboard import DashboardView
from ui.log_panel import LogPanel
from ui.settings_tab import SettingsTab


class MainWindow(QMainWindow):
    def __init__(self, data_manager: DataManager):
        super().__init__()
        self.dm = data_manager
        self.setWindowTitle("작전 현황")
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
        sidebar = QFrame()
        sidebar.setObjectName("sidebar")
        sidebar.setFixedWidth(180)
        sidebar_layout = QVBoxLayout(sidebar)
        sidebar_layout.setContentsMargins(0, 0, 0, 0)
        sidebar_layout.setSpacing(0)

        # 로고 영역 - 해양경찰 마크 + 작전 현황
        logo_frame = QFrame()
        logo_frame.setFixedHeight(60)
        logo_frame.setStyleSheet("""
            background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                stop:0 #0d2137, stop:1 #06101f);
            border-bottom: 1px solid #1a2d4a;
        """)
        logo_h = QHBoxLayout(logo_frame)
        logo_h.setContentsMargins(10, 8, 10, 8)
        logo_h.setSpacing(8)

        # 해양경찰 마크 (이미지)
        mark = QLabel()
        img_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "resources", "0504_sbimg2.png"
        )
        if os.path.exists(img_path):
            pixmap = QPixmap(img_path)
            mark.setPixmap(pixmap.scaled(36, 36, Qt.KeepAspectRatio, Qt.SmoothTransformation))
        mark.setStyleSheet("background: transparent; border: none;")
        mark.setFixedSize(40, 40)
        logo_h.addWidget(mark)

        logo_title = QLabel("작전 현황")
        logo_title.setStyleSheet("""
            color: #00d4ff; font-size: 14px; font-weight: bold;
            font-family: "HY헤드라인M", "HYHeadLineM", "Malgun Gothic", sans-serif;
            letter-spacing: 2px; background: transparent; border: none;
        """)
        logo_h.addWidget(logo_title)
        logo_h.addStretch()

        sidebar_layout.addWidget(logo_frame)

        # 탭 버튼
        self.nav_buttons = []
        for key, label in [("dashboard", "  대시보드"), ("settings", "  설정")]:
            btn = QPushButton(f"  {label}")
            btn.setCheckable(True)
            btn.setFixedHeight(44)
            btn.setProperty("nav_key", key)
            btn.clicked.connect(lambda checked, k=key: self._switch_page(k))
            sidebar_layout.addWidget(btn)
            self.nav_buttons.append(btn)

        sidebar_layout.addStretch()
        main_layout.addWidget(sidebar)

        # === 콘텐츠 영역 ===
        content_layout = QVBoxLayout()
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.setSpacing(0)

        # 헤더 바
        header = QFrame()
        header.setObjectName("headerBar")
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(20, 6, 20, 6)

        # 작전명 (클릭으로 편집)
        title_layout = QVBoxLayout()
        title_layout.setSpacing(0)

        title_text = self.dm.operation_title or "클릭하여 작전명을 입력하세요"
        self.header_title = QLabel(title_text)
        self.header_title.setObjectName("headerTitle")
        self.header_title.setCursor(Qt.PointingHandCursor)
        self.header_title.mousePressEvent = self._start_title_edit
        title_layout.addWidget(self.header_title)

        self.title_input = QLineEdit()
        self.title_input.setObjectName("headerTitleInput")
        self.title_input.setFixedHeight(30)
        self.title_input.setPlaceholderText("작전명을 입력하세요...")
        self.title_input.returnPressed.connect(self._save_title)
        self.title_input.hide()
        title_layout.addWidget(self.title_input)

        header_layout.addLayout(title_layout, 1)
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
        dp_layout.setContentsMargins(0, 0, 0, 0)
        dp_layout.setSpacing(0)

        self.dashboard = DashboardView(self.dm)
        dp_layout.addWidget(self.dashboard, 10)

        self.log_panel = LogPanel(self.dm)
        dp_layout.addWidget(self.log_panel, 3)

        self.dashboard.log_message.connect(self.log_panel.append_log)
        self.log_panel.export_requested.connect(self._export_data)
        self.page_stack.addWidget(dashboard_page)

        self.settings_tab = SettingsTab(self.dm)
        self.settings_tab.data_changed.connect(self._on_data_changed)
        self.page_stack.addWidget(self.settings_tab)

        content_layout.addWidget(self.page_stack, 1)
        main_layout.addLayout(content_layout, 1)

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

        if key == "dashboard":
            self.dashboard.refresh()
        elif key == "settings":
            self.settings_tab.refresh()

    def _update_clock(self):
        self.clock_label.setText(time.strftime("%H:%M:%S"))
        weekdays = ["월", "화", "수", "목", "금", "토", "일"]
        wd = weekdays[datetime.datetime.now().weekday()]
        self.date_label.setText(time.strftime(f"%Y.%m.%d ({wd})"))

    def _on_data_changed(self):
        self.dashboard.refresh()

    def _export_data(self):
        filepath, _ = QFileDialog.getSaveFileName(
            self, "데이터 내보내기",
            f"SPT_작전기록_{time.strftime('%Y%m%d_%H%M%S')}",
            "Excel (*.xlsx);;CSV (*.csv)"
        )
        if not filepath: return
        if filepath.endswith(".xlsx"):
            self.dm.export_xlsx(filepath)
        else:
            self.dm.export_csv(filepath)
        self.log_panel.append_log(f"데이터 내보내기 완료: {os.path.basename(filepath)}")

    def closeEvent(self, event):
        self.dm.save()
        super().closeEvent(event)
