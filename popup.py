"""Lightweight popup to display focus nudges."""
from __future__ import annotations

import os
import threading

from PySide6 import QtCore, QtGui, QtWidgets


def _create_popup_widget(text: str, config: dict) -> QtWidgets.QWidget:
    widget = QtWidgets.QWidget()
    widget.setWindowFlags(
        QtCore.Qt.Tool
        | QtCore.Qt.FramelessWindowHint
        | QtCore.Qt.WindowStaysOnTopHint
        | QtCore.Qt.NoDropShadowWindowHint
    )
    widget.setAttribute(QtCore.Qt.WA_ShowWithoutActivating)
    widget.setStyleSheet("background-color: #111827; color: #E5E7EB; border-radius: 10px;")

    layout = QtWidgets.QHBoxLayout(widget)
    layout.setContentsMargins(12, 10, 12, 10)
    layout.setSpacing(10)

    image_path = (config.get("popup") or {}).get("character_image_path")
    if image_path and os.path.exists(image_path):
        pixmap = QtGui.QPixmap(image_path).scaled(48, 48, QtCore.Qt.KeepAspectRatio, QtCore.Qt.SmoothTransformation)
        image_label = QtWidgets.QLabel()
        image_label.setPixmap(pixmap)
        layout.addWidget(image_label)

    label = QtWidgets.QLabel(text)
    label.setWordWrap(True)
    layout.addWidget(label)

    widget.adjustSize()
    # position bottom-right
    screen = QtGui.QGuiApplication.primaryScreen()
    geometry = screen.availableGeometry()
    widget_width = widget.sizeHint().width()
    widget_height = widget.sizeHint().height()
    x = geometry.right() - widget_width - 20
    y = geometry.bottom() - widget_height - 40
    widget.move(x, y)
    return widget


def show_popup(text: str, config: dict):
    def _run():
        app = QtWidgets.QApplication.instance()
        created_app = False
        if app is None:
            app = QtWidgets.QApplication([])
            created_app = True

        widget = _create_popup_widget(text, config)
        widget.show()
        duration = int((config.get("popup") or {}).get("duration_ms", 2000))
        QtCore.QTimer.singleShot(duration, widget.close)

        if created_app:
            QtCore.QTimer.singleShot(duration + 250, app.quit)
            app.exec()
    threading.Thread(target=_run, daemon=True).start()