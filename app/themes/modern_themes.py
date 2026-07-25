"""
Modern Theme Manager for OpenDailies.
Contains QSS (Qt Style Sheets) for Dark and Light modes.
"""
from PySide6.QtGui import QPalette, QColor
from PySide6.QtWidgets import QApplication

def apply_modern_theme(app: QApplication, theme: str = "dark"):
    """Applies the selected theme to the application."""
    if theme == "light":
        _apply_light(app)
    else:
        _apply_dark(app)

def _apply_dark(app: QApplication):
    palette = QPalette()
    palette.setColor(QPalette.ColorRole.Window, QColor("#171717"))
    palette.setColor(QPalette.ColorRole.WindowText, QColor("#FFFFFF"))
    palette.setColor(QPalette.ColorRole.Base, QColor("#202124"))
    palette.setColor(QPalette.ColorRole.AlternateBase, QColor("#252526"))
    palette.setColor(QPalette.ColorRole.Text, QColor("#FFFFFF"))
    palette.setColor(QPalette.ColorRole.Button, QColor("#252526"))
    palette.setColor(QPalette.ColorRole.ButtonText, QColor("#FFFFFF"))
    palette.setColor(QPalette.ColorRole.Highlight, QColor("#3B82F6"))
    palette.setColor(QPalette.ColorRole.HighlightedText, QColor("#FFFFFF"))
    app.setPalette(palette)

    qss = """
    /* ==========================================
       GLOBAL TYPOGRAPHY & SPACING
       ========================================== */
    QWidget {
        background-color: #171717;
        color: #FFFFFF;
        font-family: "SF Pro Display", "Inter", "Segoe UI Variable", sans-serif;
        font-size: 13px;
    }

    /* ==========================================
       FLOATING WINDOW & PANELS (Glassmorphism)
       ========================================== */
    QFrame#AppBody {
        background-color: #171717;
        border-radius: 12px;
        border: 1px solid #2D2E30;
    }
    QFrame#Sidebar {
        background-color: #202124;
        border-top-left-radius: 12px;
        border-bottom-left-radius: 12px;
        border-right: 1px solid #2D2E30;
    }
    QFrame#PanelCard {
        background-color: #202124;
        border-radius: 12px;
        border: 1px solid #2D2E30;
    }

    /* ==========================================
       BUTTONS & TOOLBARS
       ========================================== */
    QToolBar {
        background: transparent;
        border: none;
        spacing: 8px;
        padding: 8px;
    }
    QToolButton, QPushButton {
        background: transparent;
        color: #A9A9A9;
        border: none;
        border-radius: 8px;
        padding: 8px 12px;
    }
    QToolButton:hover, QPushButton:hover {
        background: #2D2E30;
        color: #FFFFFF;
    }
    QToolButton:pressed, QPushButton:pressed {
        background: #4C8DFF;
        color: #FFFFFF;
    }
    QToolButton:checked {
        background: #252526;
        color: #4C8DFF;
        border: 1px solid #2D2E30;
    }

    /* ==========================================
       INPUTS, DROPDOWNS & LISTS
       ========================================== */
    QListWidget, QTreeWidget, QTextEdit, QLineEdit, QComboBox, QSpinBox {
        background-color: #252526;
        color: #FFFFFF;
        border: 1px solid #2D2E30;
        padding: 8px;
        border-radius: 8px;
        selection-background-color: #3B82F6;
        selection-color: #FFFFFF;
    }
    QLineEdit:focus, QComboBox:focus, QSpinBox:focus {
        border: 1px solid #4C8DFF;
    }
    QComboBox::drop-down { border: none; width: 24px; }
    QComboBox QAbstractItemView {
        background-color: #202124;
        border: 1px solid #2D2E30;
        border-radius: 8px;
        padding: 4px;
        selection-background-color: #4C8DFF;
    }

    /* Modern Card Design for Comments & Bookmarks */
    QListWidget#CommentList::item, QListWidget#BookmarkList::item {
        background-color: #202124;
        border-radius: 8px;
        margin: 4px 8px;
        padding: 8px;
        border: 1px solid transparent;
    }
    QListWidget#CommentList::item:hover, QListWidget#BookmarkList::item:hover {
        background-color: #252526;
        border: 1px solid #2D2E30;
    }
    QListWidget#CommentList::item:selected, QListWidget#BookmarkList::item:selected {
        background-color: #252526;
        border: 1px solid #4C8DFF;
        color: #FFFFFF;
    }

    /* ==========================================
       SCROLLBARS (Minimal Overlay Style)
       ========================================== */
    QScrollBar:vertical, QScrollBar:horizontal {
        background: transparent;
        border: none;
        margin: 0;
    }
    QScrollBar::handle:vertical, QScrollBar::handle:horizontal {
        background: #2D2E30;
        border-radius: 4px;
        min-height: 30px;
        min-width: 30px;
    }
    QScrollBar::handle:vertical:hover, QScrollBar::handle:horizontal:hover {
        background: #4C8DFF;
    }
    QScrollBar::add-line, QScrollBar::sub-line { background: none; border: none; height: 0px; width: 0px; }

    /* ==========================================
       TABS & DOCKS
       ========================================== */
    QTabWidget::pane { border: none; top: -1px; }
    QTabBar::tab {
        background: transparent;
        color: #A9A9A9;
        border: none;
        padding: 8px 16px;
        border-bottom: 2px solid transparent;
    }
    QTabBar::tab:selected { color: #FFFFFF; border-bottom: 2px solid #4C8DFF; }
    QTabBar::tab:hover:!selected { color: #FFFFFF; }

    QStatusBar { background: transparent; border-top: 1px solid #2D2E30; color: #A9A9A9; }
    QStatusBar::item { border: none; }

    /* ==========================================
       CUSTOM TITLE BAR
       ========================================== */
    #TitleBar { background: transparent; border-bottom: 1px solid #2D2E30; }
    QLabel#timeLabel {
        background: #252526;
        color: #4C8DFF;
        font-family: "SF Mono", "Consolas", monospace;
        padding: 6px 12px;
        border-radius: 6px;
        border: 1px solid #2D2E30;
    }

    /* ==========================================
       MENUS
       ========================================== */
    QMenuBar { background: transparent; color: #A9A9A9; border-bottom: 1px solid #2D2E30; padding: 2px; }
    QMenuBar::item:selected { background: #2D2E30; border-radius: 4px; color: #FFFFFF; }
    QMenu { background: #202124; border: 1px solid #2D2E30; border-radius: 8px; padding: 4px; }
    QMenu::item { padding: 8px 24px 8px 16px; border-radius: 4px; }
    QMenu::item:selected { background: #4C8DFF; color: #FFFFFF; }
    QMenu::separator { height: 1px; background: #2D2E30; margin: 4px 8px; }
    """
    app.setStyleSheet(qss)

def _apply_light(app: QApplication):
    palette = QPalette()
    palette.setColor(QPalette.ColorRole.Window, QColor("#F2F2F2"))
    palette.setColor(QPalette.ColorRole.WindowText, QColor("#1E1E1E"))
    palette.setColor(QPalette.ColorRole.Base, QColor("#FFFFFF"))
    palette.setColor(QPalette.ColorRole.AlternateBase, QColor("#E6E6E6"))
    palette.setColor(QPalette.ColorRole.ToolTipBase, QColor("#FFFFFF"))
    palette.setColor(QPalette.ColorRole.ToolTipText, QColor("#1E1E1E"))
    palette.setColor(QPalette.ColorRole.Text, QColor("#1E1E1E"))
    palette.setColor(QPalette.ColorRole.Button, QColor("#E0E0E0"))
    palette.setColor(QPalette.ColorRole.ButtonText, QColor("#1E1E1E"))
    palette.setColor(QPalette.ColorRole.BrightText, QColor("#FF0000"))
    palette.setColor(QPalette.ColorRole.Highlight, QColor("#0078D7")) # Windows 11 Blue
    palette.setColor(QPalette.ColorRole.HighlightedText, QColor("#FFFFFF"))
    app.setPalette(palette)

    qss = """
    QWidget { 
        background-color: #F2F2F2; 
        color: #1E1E1E; 
        font-family: "SF Pro Display", "Inter", "Segoe UI Variable", sans-serif; 
        font-size: 13px; 
    }
    QFrame#AppBody {
        background-color: #F2F2F2;
        border-radius: 12px;
        border: 1px solid #D0D0D0;
    }
    QFrame#Sidebar {
        background-color: #E6E6E6;
        border-top-left-radius: 12px;
        border-bottom-left-radius: 12px;
        border-right: 1px solid #D0D0D0;
    }
    QFrame#PanelCard {
        background-color: #FFFFFF;
        border-radius: 12px;
        border: 1px solid #D0D0D0;
    }
    QToolBar { 
        background: transparent; 
        border: none; 
        border-top: 1px solid #D0D0D0; 
        spacing: 8px; 
        padding: 8px; 
    }
    QToolButton, QPushButton { 
        background-color: transparent; 
        color: #444444; 
        border: none; 
        border-radius: 8px; 
        padding: 8px 12px; 
    }
    QToolButton:hover, QPushButton:hover { 
        background: #E0E0E0; 
        color: #1E1E1E; 
    }
    QToolButton:pressed, QPushButton:pressed { 
        background: #0078D7; 
        color: #FFFFFF; 
    }
    QToolButton:checked { 
        background: #D0D0D0; 
        color: #0078D7; 
        border: 1px solid #B0B0B0;
    }
    QListWidget, QTreeWidget, QTextEdit, QLineEdit, QComboBox, QSpinBox { 
        background-color: #FFFFFF; 
        color: #1E1E1E; 
        border: 1px solid #CCCCCC; 
        padding: 8px; 
        border-radius: 8px; 
        selection-background-color: #0078D7; 
        selection-color: #FFFFFF; 
    }
    QLineEdit:focus, QComboBox:focus, QSpinBox:focus {
        border: 1px solid #0078D7;
    }
    QComboBox::drop-down { 
        border: none; 
        width: 24px; 
    }
    QComboBox QAbstractItemView {
        background-color: #FFFFFF;
        border: 1px solid #CCCCCC;
        border-radius: 8px;
        selection-background-color: #0078D7;
        selection-color: #FFFFFF;
    }
    QListWidget#CommentList::item, QListWidget#BookmarkList::item {
        background-color: #FFFFFF;
        border-radius: 8px;
        margin: 4px 8px;
        padding: 8px;
        border: 1px solid transparent;
    }
    QListWidget#CommentList::item:hover, QListWidget#BookmarkList::item:hover {
        background-color: #F0F0F0;
        border: 1px solid #D0D0D0;
    }
    QListWidget#CommentList::item:selected, QListWidget#BookmarkList::item:selected {
        background-color: #F0F0F0;
        border: 1px solid #0078D7;
        color: #1E1E1E;
    }
    QScrollBar:vertical, QScrollBar:horizontal { 
        background: transparent; 
        border: none; 
        margin: 0;
    }
    QScrollBar::handle:vertical, QScrollBar::handle:horizontal { 
        background: #B0B0B0; 
        border-radius: 3px; 
        min-height: 30px; 
        min-width: 30px; 
    }
    QScrollBar::handle:vertical:hover, QScrollBar::handle:horizontal:hover { 
        background: #0078D7; 
    }
    QScrollBar::add-line, QScrollBar::sub-line { 
        background: none; 
        border: none; 
        height: 0px; 
        width: 0px; 
    }
    QScrollBar::add-page, QScrollBar::sub-page {
        background: transparent;
    }
    QDockWidget { 
        border: none; 
    }
    QDockWidget::title { 
        background-color: #F2F2F2; 
        border-bottom: 1px solid #D0D0D0; 
        padding: 8px 12px; 
        text-align: left; 
        font-weight: bold; 
    }
    QTabWidget::pane { 
        border: none; 
        top: -1px; 
    }
    QTabBar::tab { 
        background-color: transparent; 
        color: #808080; 
        border: none; 
        padding: 8px 16px; 
        border-bottom: 2px solid transparent; 
    }
    QTabBar::tab:selected { 
        color: #1E1E1E; 
        border-bottom: 2px solid #0078D7; 
    }
    QTabBar::tab:hover:!selected {
        color: #444444;
    }
    QStatusBar { 
        background-color: #F2F2F2; 
        border-top: 1px solid #D0D0D0; 
        color: #444444;
    }
    QStatusBar::item { border: none; }
    QMenuBar { 
        background-color: #F2F2F2; 
        color: #444444; 
        border-bottom: 1px solid #D0D0D0; 
        padding: 2px; 
    }
    QMenuBar::item { 
        background: transparent; 
        padding: 6px 12px; 
        border-radius: 6px; 
    }
    QMenuBar::item:selected { 
        background-color: #E0E0E0; 
        color: #1E1E1E; 
    }
    QMenu { 
        background-color: #FFFFFF; 
        color: #1E1E1E; 
        border: 1px solid #CCCCCC; 
        border-radius: 8px; 
        padding: 4px;
    }
    QMenu::item { 
        padding: 8px 24px 8px 16px; 
        border-radius: 4px; 
    }
    QMenu::item:selected { 
        background-color: #0078D7; 
        color: #FFFFFF; 
    }
    QMenu::separator {
        height: 1px;
        background: #D0D0D0;
        margin: 4px 8px;
    }
    QLabel#timeLabel { 
        background-color: #FFFFFF; 
        color: #0078D7; 
        font-family: "Consolas", monospace; 
        padding: 6px 12px; 
        border: 1px solid #CCCCCC; 
        border-radius: 6px; 
    }
    """
    app.setStyleSheet(qss)