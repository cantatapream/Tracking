#!/usr/bin/env python3
"""
SPT - SEAGNAL Personnel Tracker
해양경찰 인원 및 장비 현황 관리 시스템

실행: python spt_app.py
필요 패키지: pip install PySide6 openpyxl
"""
import sys
import os

# 프로젝트 루트를 path에 추가
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from PySide6.QtWidgets import QApplication
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont
from ui.main_window import MainWindow


def main():
    # High DPI 지원
    os.environ.setdefault("QT_ENABLE_HIGHDPI_SCALING", "1")

    app = QApplication(sys.argv)
    app.setApplicationName("SPT - SEAGNAL Personnel Tracker")
    app.setOrganizationName("KCG")

    # 기본 폰트 설정
    font = QFont("Malgun Gothic", 10)
    font.setStyleHint(QFont.SansSerif)
    app.setFont(font)

    window = MainWindow()
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
