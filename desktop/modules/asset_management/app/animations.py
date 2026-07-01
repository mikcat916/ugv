# -*- coding: utf-8 -*-
"""Reusable click animations for Qt buttons via QAbstractAnimation groups."""

from PyQt5.QtCore import (
    QAbstractAnimation,
    QEvent,
    QObject,
    QEasingCurve,
    QPropertyAnimation,
    QSequentialAnimationGroup,
)
from PyQt5.QtWidgets import QGraphicsOpacityEffect, QPushButton, QWidget


class _ButtonClickAnimator(QObject):
    """Attach click animations to a QPushButton."""

    def __init__(self, button: QPushButton):
        super().__init__(button)
        self.button = button
        self.effect = button.graphicsEffect()
        if not isinstance(self.effect, QGraphicsOpacityEffect):
            self.effect = QGraphicsOpacityEffect(button)
            self.effect.setOpacity(1.0)
            button.setGraphicsEffect(self.effect)

        # QSequentialAnimationGroup is a QAbstractAnimation implementation.
        self.press_group = QSequentialAnimationGroup(self)
        self.press_anim = QPropertyAnimation(self.effect, b"opacity", self.press_group)
        self.press_anim.setDuration(90)
        self.press_anim.setStartValue(1.0)
        self.press_anim.setEndValue(0.78)
        self.press_anim.setEasingCurve(QEasingCurve.OutCubic)
        self.press_group.addAnimation(self.press_anim)

        self.release_group = QSequentialAnimationGroup(self)
        self.release_anim = QPropertyAnimation(self.effect, b"opacity", self.release_group)
        self.release_anim.setDuration(140)
        self.release_anim.setStartValue(0.78)
        self.release_anim.setEndValue(1.0)
        self.release_anim.setEasingCurve(QEasingCurve.OutCubic)
        self.release_group.addAnimation(self.release_anim)

        button.installEventFilter(self)

    def _stop_group(self, group: QSequentialAnimationGroup):
        if group.state() == QAbstractAnimation.Running:
            group.stop()

    def _play_press(self):
        self._stop_group(self.release_group)
        self._stop_group(self.press_group)
        self.press_anim.setStartValue(self.effect.opacity())
        self.press_anim.setEndValue(0.78)
        self.press_group.start()

    def _play_release(self):
        self._stop_group(self.press_group)
        self._stop_group(self.release_group)
        self.release_anim.setStartValue(self.effect.opacity())
        self.release_anim.setEndValue(1.0)
        self.release_group.start()

    def eventFilter(self, obj, event):
        if obj is self.button:
            if event.type() == QEvent.MouseButtonPress:
                self._play_press()
            elif event.type() in (QEvent.MouseButtonRelease, QEvent.Leave, QEvent.FocusOut):
                self._play_release()
        return super().eventFilter(obj, event)


def enable_click_animations(parent: QWidget):
    """Enable click animations for all QPushButton children under parent."""
    for button in parent.findChildren(QPushButton):
        # Keep a strong reference on the button to avoid GC.
        if not hasattr(button, "_click_animator"):
            button._click_animator = _ButtonClickAnimator(button)
