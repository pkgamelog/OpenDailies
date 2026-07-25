"""
Comment Panel UI (Modern Card Design).
Displays comments as custom interactive cards with word-wrap and dynamic scaling.
"""
from typing import List
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLineEdit, 
                               QToolButton, QScrollArea, QLabel, QMenu, QFrame, QSizePolicy)
from PySide6.QtCore import Qt, Signal, QPoint, QSize
from PySide6.QtGui import QColor, QIcon, QPixmap, QPainter, QPen, QPolygon
from app.models.entities import Comment

class CommentCard(QWidget):
    """A custom widget representing a single comment card."""
    
    jump_requested = Signal(str)
    edit_requested = Signal(str)
    delete_requested = Signal(str)
    
    def __init__(self, comment: Comment, parent=None):
        super().__init__(parent)
        self.comment_id = comment.id
        self.frame_number = comment.frame_number
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self._init_ui(comment)
        
    def _create_icon(self, draw_func) -> QIcon:
        pix = QPixmap(16, 16)
        pix.fill(Qt.GlobalColor.transparent)
        p = QPainter(pix)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        draw_func(p)
        p.end()
        return QIcon(pix)

    def _init_ui(self, comment: Comment):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 10, 12, 10)
        layout.setSpacing(6)
        
        # Header Row (Author + Timecode)
        header_layout = QHBoxLayout()
        header_layout.setContentsMargins(0, 0, 0, 0)
        header_layout.setSpacing(8)
        
        self.author_label = QLabel(comment.author)
        self.author_label.setStyleSheet("color: #4C8DFF; font-size: 13px; font-weight: 600; background: transparent;")
        header_layout.addWidget(self.author_label)
        header_layout.addStretch()
        
        secs = comment.timecode_ms // 1000
        time_str = f"{secs//60:02d}:{secs%60:02d}"
        self.time_label = QLabel(f"[F:{comment.frame_number}] {time_str}")
        self.time_label.setStyleSheet("color: #A9A9A9; font-size: 11px; background: transparent;")
        header_layout.addWidget(self.time_label)
        
        layout.addLayout(header_layout)
        
        # Body Text
        self.text_label = QLabel(comment.text)
        self.text_label.setWordWrap(True)
        self.text_label.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        self.text_label.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft)
        self.text_label.setStyleSheet("color: #E0E0E0; font-size: 13px; background: transparent;")
        layout.addWidget(self.text_label)
        
        # Footer Row (Status + Actions)
        footer_layout = QHBoxLayout()
        footer_layout.setContentsMargins(0, 4, 0, 0)
        footer_layout.setSpacing(8)
        
        self.status_label = QLabel("✓ Resolved" if comment.is_resolved else "○ Open")
        self.status_label.setStyleSheet(f"color: {'#4CAF50' if comment.is_resolved else '#FFB84D'}; font-size: 11px; font-weight: 600; background: transparent;")
        footer_layout.addWidget(self.status_label)
        footer_layout.addStretch()
        
        # Jump Button
        self.btn_jump = QToolButton()
        self.btn_jump.setIconSize(QSize(16, 16))
        self.btn_jump.setIcon(self._create_icon(lambda p: (p.setBrush(QColor("#4C8DFF")), p.setPen(Qt.PenStyle.NoPen), p.drawPolygon(QPolygon([QPoint(3, 2), QPoint(3, 14), QPoint(13, 8)])))))
        self.btn_jump.setToolTip("Jump to Frame")
        self.btn_jump.setStyleSheet("QToolButton { background: transparent; border: none; padding: 4px; border-radius: 4px; } QToolButton:hover { background-color: #2D2E30; }")
        self.btn_jump.clicked.connect(lambda: self.jump_requested.emit(self.comment_id))
        footer_layout.addWidget(self.btn_jump)
        
        # Edit Button
        self.btn_edit = QToolButton()
        self.btn_edit.setIconSize(QSize(16, 16))
        self.btn_edit.setIcon(self._create_icon(lambda p: (p.setPen(QPen(QColor("#A9A9A9"), 2)), p.drawLine(4, 12, 12, 4), p.drawLine(4, 12, 6, 14), p.drawLine(12, 4, 14, 6))))
        self.btn_edit.setToolTip("Edit Comment")
        self.btn_edit.setStyleSheet("QToolButton { background: transparent; border: none; padding: 4px; border-radius: 4px; } QToolButton:hover { background-color: #2D2E30; }")
        self.btn_edit.clicked.connect(lambda: self.edit_requested.emit(self.comment_id))
        footer_layout.addWidget(self.btn_edit)
        
        # Delete Button
        self.btn_delete = QToolButton()
        self.btn_delete.setIconSize(QSize(16, 16))
        self.btn_delete.setIcon(self._create_icon(lambda p: (p.setPen(QPen(QColor("#FF5A5F"), 2)), p.drawLine(4, 4, 12, 12), p.drawLine(12, 4, 4, 12))))
        self.btn_delete.setToolTip("Delete Comment")
        self.btn_delete.setStyleSheet("QToolButton { background: transparent; border: none; padding: 4px; border-radius: 4px; } QToolButton:hover { background-color: #2D2E30; }")
        self.btn_delete.clicked.connect(lambda: self.delete_requested.emit(self.comment_id))
        footer_layout.addWidget(self.btn_delete)
        
        layout.addLayout(footer_layout)
        
        self.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.customContextMenuRequested.connect(self._show_context_menu)

    def set_highlighted(self, highlighted: bool):
        """Changes the border color to indicate the playhead is at this comment."""
        if highlighted:
            self.setStyleSheet("CommentCard { background-color: #252526; border-radius: 8px; border: 1px solid #4C8DFF; }")
        else:
            self.setStyleSheet("CommentCard { background-color: #202124; border-radius: 8px; border: 1px solid transparent; }")

    def _show_context_menu(self, pos):
        menu = QMenu(self)
        menu.setStyleSheet("""
            QMenu { background-color: #202124; border: 1px solid #2D2E30; border-radius: 8px; padding: 4px; }
            QMenu::item { padding: 8px 24px 8px 16px; border-radius: 4px; color: #FFFFFF; }
            QMenu::item:selected { background-color: #4C8DFF; }
            QMenu::separator { height: 1px; background: #2D2E30; margin: 4px 8px; }
        """)
        
        jump_act = menu.addAction("Jump to Frame")
        menu.addSeparator()
        edit_act = menu.addAction("Edit")
        delete_act = menu.addAction("Delete")
        
        action = menu.exec(self.mapToGlobal(pos))
        
        if action == jump_act:
            self.jump_requested.emit(self.comment_id)
        elif action == edit_act:
            self.edit_requested.emit(self.comment_id)
        elif action == delete_act:
            self.delete_requested.emit(self.comment_id)

class CommentPanel(QWidget):
    """Panel for managing review comments with a modern card layout."""
    
    jump_to_frame_requested = Signal(int)
    add_comment_requested = Signal()
    edit_comment_requested = Signal(str)
    delete_comment_requested = Signal(str)
    
    def __init__(self):
        super().__init__()
        self._cards = []
        self._init_ui()

    def _init_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(8)
        
        # Search Bar
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Search comments...")
        self.search_input.textChanged.connect(self._filter_comments)
        layout.addWidget(self.search_input)
        
        # Scroll Area
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
        self.empty_label = QLabel("No comments yet.\nAdd a comment at the current frame.")
        self.empty_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.empty_label.setStyleSheet("color: #A9A9A9; font-size: 12px; background: transparent;")
        layout.addWidget(self.empty_label, 1)
        
        # Input Area
        input_layout = QHBoxLayout()
        self.input_field = QLineEdit()
        self.input_field.setPlaceholderText("Add comment at current frame...")
        self.input_field.returnPressed.connect(self.add_comment_requested.emit)
        
        self.add_btn = QToolButton()
        self.add_btn.setText("Add")
        self.add_btn.setStyleSheet("""
            QToolButton { background-color: #252526; color: #4C8DFF; border: 1px solid #2D2E30; border-radius: 6px; padding: 6px 12px; font-weight: 600; }
            QToolButton:hover { background-color: #2D2E30; border: 1px solid #4C8DFF; }
        """)
        self.add_btn.clicked.connect(self.add_comment_requested.emit)
        
        input_layout.addWidget(self.input_field)
        input_layout.addWidget(self.add_btn)
        layout.addLayout(input_layout)

    def load_comments(self, comments: List[Comment], frame_rate: float) -> None:
        """Loads comments into the scroll area as cards."""
        self._cards.clear()
        while self.scroll_layout.count() > 1:
            item = self.scroll_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        
        self.empty_label.setVisible(len(comments) == 0)
        self.scroll_area.setVisible(len(comments) > 0)
        
        for c in comments:
            card = CommentCard(c, self.scroll_content)
            card.jump_requested.connect(self._on_jump_requested)
            card.edit_requested.connect(self.edit_comment_requested.emit)
            card.delete_requested.connect(self.delete_comment_requested.emit)
            
            self._cards.append(card)
            self.scroll_layout.insertWidget(self.scroll_layout.count() - 1, card)

    def _on_jump_requested(self, comment_id: str):
        for card in self._cards:
            if card.comment_id == comment_id:
                self.jump_to_frame_requested.emit(card.frame_number)
                break

    def _filter_comments(self) -> None:
        text = self.search_input.text().lower()
        for card in self._cards:
            match = text in card.text_label.text().lower() or text in card.author_label.text().lower()
            card.setVisible(match)

    def highlight_comment_frame(self, frame: int) -> None:
        """Selects the comment matching the current frame."""
        found = False
        for card in self._cards:
            if card.frame_number == frame:
                card.set_highlighted(True)
                # Scroll to the item
                self.scroll_area.ensureWidgetVisible(card)
                found = True
            else:
                card.set_highlighted(False)
        
        # If no comment matches, ensure none are highlighted
        if not found:
            for card in self._cards:
                card.set_highlighted(False)