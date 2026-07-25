import sys
import os
import ctypes
from PySide6.QtWidgets import QApplication, QSplashScreen
from PySide6.QtGui import QIcon, QPixmap, QPainter, QColor, QFont
from PySide6.QtCore import Qt, QTimer
from app.ui.main_window import MainWindow
from app.themes.modern_themes import apply_modern_theme

def resource_path(relative_path):
    """Get absolute path to resource, works for dev and for PyInstaller."""
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)

def create_splash_pixmap():
    """Loads a custom transparent PNG, or generates a default dark splash screen."""
    custom_img_path = resource_path(os.path.join("assets", "splash.png"))
    
    if os.path.exists(custom_img_path):
        # Load your pre-made image with baked-in transparent rounded corners
        pix = QPixmap(custom_img_path)
        # Scale it down so it doesn't cover the whole screen, but keep it crisp
        if pix.width() > 600:
            pix = pix.scaledToWidth(600, Qt.TransformationMode.SmoothTransformation)
        return pix
        
    # Fallback: Draw a programmatic dark splash screen if image isn't found
    # (This is just a backup in case the PNG is missing)
    pix = QPixmap(640, 360)
    pix.fill(QColor("#171717"))
    p = QPainter(pix)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    p.setPen(QColor("#4C8DFF"))
    p.setFont(QFont("SF Pro Display", 44, QFont.Weight.Bold))
    p.drawText(pix.rect().adjusted(0, -30, 0, 0), Qt.AlignmentFlag.AlignCenter, "OpenDailies")
    p.setPen(QColor("#A9A9A9"))
    p.setFont(QFont("SF Pro Display", 14, QFont.Weight.Medium))
    p.drawText(pix.rect().adjusted(0, 40, 0, 0), Qt.AlignmentFlag.AlignCenter, "Loading Workspace...")
    p.end()
    return pix

def main():
    if sys.platform == "win32":
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("ParitKatre.OpenDailies")

    app = QApplication(sys.argv)
    
    icon_path = resource_path(os.path.join("assets", "icons", "OpenDailies.ico"))
    if os.path.exists(icon_path):
        app.setWindowIcon(QIcon(icon_path))
        
    apply_modern_theme(app, "dark")
    
    # Create the pixmap
    splash_pixmap = create_splash_pixmap()
    
    # Create and show the static splash screen
    splash = QSplashScreen(splash_pixmap)
    splash.show()
    app.processEvents() 
    
    # Initialize the main window behind the scenes
    window = MainWindow()
    
    # Show window after 1.5 seconds for a fast, responsive feel
    def show_window():
        window.show()
        splash.finish(window) # Smoothly fades/hides splash when window is ready
        
        # NEW: Check if a video path was passed as a command-line argument (e.g., from Maya)
        if len(sys.argv) > 1:
            file_arg = sys.argv[1]
            if os.path.exists(file_arg):
                # Load the video automatically after the UI appears
                QTimer.singleShot(100, lambda: window.open_video_file(file_arg))
        
    QTimer.singleShot(1500, show_window)
    
    sys.exit(app.exec())

if __name__ == "__main__":
    main()