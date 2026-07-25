"""
Bookmark Panel UI (Modern Card Design).
Displays bookmarks as custom interactive cards with word-wrap and dynamic scaling.
"""
from typing import List
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QToolButton, 
                               QScrollArea, QLabel, QMenu, QFrame, QSizePolicy)
from PySide6.QtCore import Qt, Signal, QPoint, QSize
from PySide6.QtGui import QAction, QColor, QPalette, QIcon, QPixmap, QPainter, QPen, QPolygon
from app.models.entities import Bookmark

class BookmarkCard(QWidget):
    """A custom widget representing a single bookmark card."""
    
    jump_requested = Signal(str)
    delete_requested = Signal(str)
    rename_requested = Signal(str)
    
    def __init__(self, bookmark: Bookmark, parent=None):
        super().__init__(parent)
        self.bookmark_id = bookmark.id
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self._init_ui(bookmark)
        
    def _create_icon(self, draw_func) -> QIcon:
        pix = QPixmap(20, 20)
        pix.fill(Qt.GlobalColor.transparent)
        p = QPainter(pix)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        draw_func(p)
        p.end()
        return QIcon(pix)

    def _init_ui(self, bookmark: Bookmark):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 8, 12, 8)
        layout.setSpacing(12)
        
        # Color Tag Indicator
        self.color_tag = QFrame()
        self.color_tag.setFixedWidth(4)
        self.color_tag.setStyleSheet(f"background-color: {bookmark.color}; border-radius: 2px;")
        layout.addWidget(self.color_tag)
        
        # Info Container
        info_widget = QWidget()
        info_layout = QVBoxLayout(info_widget)
        info_layout.setContentsMargins(0, 0, 0, 0)
        info_layout.setSpacing(2)
        
        self.title_label = QLabel(bookmark.name)
        self.title_label.setWordWrap(True)
        # FIX: Force the label to shrink horizontally and wrap, preventing layout expansion
        self.title_label.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Preferred)
        self.title_label.setStyleSheet("color: #FFFFFF; font-size: 13px; font-weight: 600; background: transparent;")
        info_layout.addWidget(self.title_label)
        
        self.frame_label = QLabel(f"Frame: {bookmark.frame_number}")
        self.frame_label.setStyleSheet("color: #A9A9A9; font-size: 11px; background: transparent;")
        info_layout.addWidget(self.frame_label)
        
        layout.addWidget(info_widget, 1)
        
        # Actions Container
        actions_widget = QWidget()
        actions_layout = QHBoxLayout(actions_widget)
        actions_layout.setContentsMargins(0, 0, 0, 0)
        actions_layout.setSpacing(4)
        
        # Jump Button (Icon)
        self.btn_jump = QToolButton()
        self.btn_jump.setIconSize(QSize(18, 18))
        self.btn_jump.setIcon(self._create_icon(lambda p: (p.setBrush(QColor("#4C8DFF")), p.setPen(Qt.PenStyle.NoPen), p.drawPolygon(QPolygon([QPoint(4, 2), QPoint(4, 18), QPoint(16, 10)])))))
        self.btn_jump.setToolTip("Jump to Frame")
        self.btn_jump.setStyleSheet("QToolButton { background: transparent; border: none; padding: 4px; border-radius: 4px; } QToolButton:hover { background-color: #2D2E30; }")
        self.btn_jump.clicked.connect(lambda: self.jump_requested.emit(self.bookmark_id))
        actions_layout.addWidget(self.btn_jump)
        
        # Delete Button (Icon)
        self.btn_delete = QToolButton()
        self.btn_delete.setIconSize(QSize(18, 18))
        self.btn_delete.setIcon(self._create_icon(lambda p: (p.setPen(QPen(QColor("#FF5A5F"), 2)), p.drawLine(4, 4, 16, 16), p.drawLine(16, 4, 4, 16))))
        self.btn_delete.setToolTip("Delete Bookmark")
        self.btn_delete.setStyleSheet("QToolButton { background: transparent; border: none; padding: 4px; border-radius: 4px; } QToolButton:hover { background-color: #2D2E30; }")
        self.btn_delete.clicked.connect(lambda: self.delete_requested.emit(self.bookmark_id))
        actions_layout.addWidget(self.btn_delete)
        
        layout.addWidget(actions_widget)
        
        self.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.customContextMenuRequested.connect(self._show_context_menu)

    def _show_context_menu(self, pos):
        menu = QMenu(self)
        menu.setStyleSheet("""
            QMenu { background-color: #202124; border: 1px solid #2D2E30; border-radius: 8px; padding: 4px; }
            QMenu::item { padding: 8px 24px 8px 16px; border-radius: 4px; color: #FFFFFF; }
            QMenu::item:selected { background-color: #4C8DFF; }
        """)
        
        rename_act = menu.addAction("Rename")
        action = menu.exec(self.mapToGlobal(pos))
        
        if action == rename_act:
            self.rename_requested.emit(self.bookmark_id)

class BookmarkPanel(QWidget):
    """Panel for managing bookmarks with a modern card layout."""
    
    jump_to_frame_requested = Signal(int)
    add_bookmark_requested = Signal()
    rename_bookmark_requested = Signal(str, str)
    delete_bookmark_requested = Signal(str)

    def __init__(self):
        super().__init__()
        self._cards = [] 
        self._init_ui()

    def _init_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(8)
        
        # Header / Add Button
        header_layout = QHBoxLayout()
        header_label = QLabel("Bookmarks")
        header_label.setStyleSheet("color: #FFFFFF; font-size: 15px; font-weight: 600; background: transparent;")
        header_layout.addWidget(header_label)
        header_layout.addStretch()
        
        add_btn = QToolButton()
        add_btn.setText("+ Add at Playhead")
        add_btn.setStyleSheet("""
            QToolButton { background-color: #252526; color: #4C8DFF; border: 1px solid #2D2E30; border-radius: 6px; padding: 6px 12px; font-weight: 600; }
            QToolButton:hover { background-color: #2D2E30; border: 1px solid #4C8DFF; }
        """)
        add_btn.clicked.connect(self.add_bookmark_requested.emit)
        header_layout.addWidget(add_btn)
        
        layout.addLayout(header_layout)
        
        # FIX: Use QScrollArea with horizontal scrollbar forced off
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.scroll_area.setStyleSheet("QScrollArea { background: transparent; border: none; } QScrollBar:vertical { background: transparent; width: 8px; } QScrollBar::handle:vertical { background: #3e3e3e; border-radius: 4px; }")
        
        self.scroll_content = QWidget()
        self.scroll_content.setStyleSheet("background: transparent;")
        self.scroll_layout = QVBoxLayout(self.scroll_content)
        self.scroll_layout.setContentsMargins(0, 0, 0, 0)
        self.scroll_layout.setSpacing(6)
        self.scroll_layout.addStretch(1) 
        self.scroll_area.setWidget(self.scroll_content)
        
        layout.addWidget(self.scroll_area, 1)
        
        # Empty State Label
        self.empty_label = QLabel("No bookmarks yet.\nJump to a frame and click 'Add'.")
        self.empty_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.empty_label.setStyleSheet("color: #A9A9A9; font-size: 12px; background: transparent;")
        layout.addWidget(self.empty_label, 1)

    def load_bookmarks(self, bookmarks: List[Bookmark]) -> None:
        self._cards.clear()
        while self.scroll_layout.count() > 1:
            item = self.scroll_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        
        self.empty_label.setVisible(len(bookmarks) == 0)
        self.scroll_area.setVisible(len(bookmarks) > 0)
        
        for bm in bookmarks:
            card = BookmarkCard(bm, self.scroll_content)
            card.jump_requested.connect(self._on_jump_requested)
            card.delete_requested.connect(self.delete_bookmark_requested.emit)
            card.rename_requested.connect(self._on_rename_requested)
            
            self._cards.append(card)
            self.scroll_layout.insertWidget(self.scroll_layout.count() - 1, card)

    def _on_jump_requested(self, bookmark_id: str):
        for card in self._cards:
            if card.bookmark_id == bookmark_id:
                frame_text = card.frame_label.text().replace("Frame: ", "")
                self.jump_to_frame_requested.emit(int(frame_text))
                break

    def _on_rename_requested(self, bookmark_id: str):
        self.rename_bookmark_requested.emit(bookmark_id, "")