#!/usr/bin/env python3
"""
SPT - 작전 통제 현황
해양경찰 인원 및 장비 현황 관리 시스템

실행: python spt_app.py
필요 패키지: pip install PySide6 openpyxl
"""
import sys
import os

# 프로젝트 루트를 path에 추가
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from PySide6.QtWidgets import QApplication, QDialog
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont
from core.data_manager import DataManager
from ui.startup_dialog import StartupDialog
from ui.main_window import MainWindow


def main():
    # High DPI 지원
    os.environ.setdefault("QT_ENABLE_HIGHDPI_SCALING", "1")

    app = QApplication(sys.argv)
    app.setApplicationName("작전 통제 현황")
    app.setOrganizationName("KCG")

    # 기본 폰트 설정
    font = QFont("Malgun Gothic", 10)
    font.setStyleHint(QFont.SansSerif)
    app.setFont(font)

    # 데이터 매니저 생성
    dm = DataManager()

    # 시작 대화상자
    startup = StartupDialog(dm)
    result = startup.exec()

    if result != QDialog.Accepted:
        sys.exit(0)

    if startup.result_action == "new":
        dm.new_operation()
    # "load"인 경우 이미 dm.load_operation()이 호출됨

    window = MainWindow(dm)
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
