"""
Brush Engine for handling textured drawing, pressure mapping, and custom presets.
"""
import os
import json
import random
import glob
from typing import Optional
from PySide6.QtCore import Qt, QPoint, QPointF
from PySide6.QtGui import QPainter, QPen, QColor, QPixmap, QBrush, QImage

class BrushPreset:
    """Data class for a custom brush preset."""
    def __init__(self, name: str, texture_path: str = "", spacing: int = 1, pressure_size: bool = True, is_default: bool = False):
        self.name = name
        self.texture_path = texture_path
        self.spacing = spacing
        self.pressure_size = pressure_size
        self.is_default = is_default
        self.texture = None
        
        # Load texture if path is provided and exists
        if texture_path and os.path.exists(texture_path):
            pix = QPixmap(texture_path)
            # FIX: Force the image to have an alpha channel for proper tinting
            if not pix.hasAlphaChannel():
                img = pix.toImage().convertToFormat(QImage.Format.Format_ARGB32)
                pix = QPixmap.fromImage(img)
            self.texture = pix

class BrushEngine:
    """Handles the rendering logic for different brush types."""
    
    def __init__(self):
        self._textures = {}
        self._presets = {}  # Store all brushes (default and custom)
        self._tint_cache = {} # FIX: Initialize the tint cache dictionary here
        self._load_default_textures()

    def _find_file(self, base_dir: str, filename: str) -> Optional[str]:
        """Dynamically searches for a file anywhere inside the assets folder."""
        for root, _, files in os.walk(os.path.join(base_dir, "assets")):
            if filename in files:
                return os.path.join(root, filename)
        return None

    def _load_default_textures(self) -> None:
        """Loads default tileable textures or generates them if missing."""
        base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
        
        # FIX: Dynamically search for the file instead of guessing the folder
        pencil_path = self._find_file(base_dir, "pencil_grain.png")
        pencil_tex = None
        
        if pencil_path:
            pix = QPixmap(pencil_path)
            # FIX: If the texture is massive (e.g., 10MB 4K image), shrink it to 256x256 
            # to prevent extreme CPU lag when scaling it to 3px during mouse movement.
            if pix.width() > 256 or pix.height() > 256:
                pix = pix.scaled(256, 256, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
            if not pix.hasAlphaChannel():
                img = pix.toImage().convertToFormat(QImage.Format.Format_ARGB32)
                pix = QPixmap.fromImage(img)
            pencil_tex = pix
        else:
            # If the texture file is missing, automatically generate a grainy noise texture.
            pencil_tex = self._generate_noise_texture(128)

        self._textures["pencil"] = pencil_tex
        
        # FIX: Set spacing to 1 for maximum overlap. This prevents pixelated gaps 
        # when the brush size is very small (e.g., 3px).
        self._presets["pencil"] = BrushPreset("pencil", spacing=1, pressure_size=True, is_default=True)
        self._presets["pencil"].texture = pencil_tex

        # Load any .odbrush files found in assets/brushes/
        brushes_dir = os.path.join(base_dir, "assets", "brushes")
        if os.path.exists(brushes_dir):
            preset_files = glob.glob(os.path.join(brushes_dir, "*.odbrush"))
            for preset_file in preset_files:
                try:
                    with open(preset_file, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                    
                    name = data.get("name", os.path.basename(preset_file).replace(".odbrush", ""))
                    tex_path = data.get("texture_path")
                    spacing = data.get("spacing", 1)
                    pressure_size = data.get("pressure_size", True)
                    
                    if tex_path:
                        if not os.path.isabs(tex_path):
                            tex_path = os.path.join(base_dir, tex_path)
                            
                        if os.path.exists(tex_path):
                            preset = BrushPreset(name, tex_path, spacing, pressure_size, is_default=True)
                            self._presets[name] = preset
                except Exception as e:
                    print(f"Error loading default preset {preset_file}: {e}")

    def _generate_noise_texture(self, size: int = 128) -> QPixmap:
        """Generates a soft, grayscale noise texture in memory (anti-pixelated)."""
        img = QImage(size, size, QImage.Format.Format_ARGB32)
        img.fill(Qt.GlobalColor.transparent)
        
        painter = QPainter(img)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        
        # Draw random soft circles to simulate graphite/paper grain smoothly
        for _ in range(size * size // 4):
            x = random.uniform(0, size - 1)
            y = random.uniform(0, size - 1)
            alpha = random.randint(30, 150)
            radius = random.uniform(0.5, 1.5)
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QColor(255, 255, 255, alpha))
            painter.drawEllipse(QPointF(x, y), radius, radius)
            
        painter.end()
        return QPixmap.fromImage(img)

    def load_preset(self, json_path: str) -> Optional[str]:
        """Loads a .odbrush JSON preset file manually (via Settings menu)."""
        try:
            with open(json_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            name = data.get("name", "Custom Brush")
            tex_path = data.get("texture_path")
            spacing = data.get("spacing", 1)
            pressure_size = data.get("pressure_size", True)
            
            base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
            if tex_path:
                if not os.path.isabs(tex_path):
                    tex_path = os.path.join(base_dir, tex_path)
                    
            if tex_path and os.path.exists(tex_path):
                preset = BrushPreset(name, tex_path, spacing, pressure_size, is_default=False)
                self._presets[name] = preset
                return name
        except Exception:
            pass
        return None

    def draw_segment(self, painter: QPainter, p1: QPoint, p2: QPoint, tool_type: str, color: QColor, base_size: int, pressure: float) -> None:
        """Draws a line segment between two points."""
        width = max(1, int(base_size * pressure))
        
        # Check if a preset is being used (this now includes the default pencil)
        preset = self._presets.get(tool_type)
        
        if preset and preset.texture:
            # Use the stamping method for all textured brushes
            self._stamp_along_path(painter, p1, p2, preset, color, width)
        else:
            # Standard Smooth Brush Rendering (pen)
            pen = QPen(color, width)
            pen.setCapStyle(Qt.PenCapStyle.RoundCap)
            pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
            painter.setPen(pen)
            painter.drawLine(p1, p2)

    def draw_point(self, painter: QPainter, p: QPoint, tool_type: str, color: QColor, base_size: int, pressure: float) -> None:
        """Draws a single dot (for single clicks)."""
        width = max(1, int(base_size * pressure))
        preset = self._presets.get(tool_type)
        
        if preset and preset.texture:
            tex = preset.texture.scaled(width, width, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
            painter.drawPixmap(p.x() - width//2, p.y() - width//2, self._tint_texture(tex, color))
        else:
            pen = QPen(color, width)
            pen.setCapStyle(Qt.PenCapStyle.RoundCap)
            painter.setPen(pen)
            painter.drawPoint(p)

    def _tint_texture(self, tex: QPixmap, color: QColor) -> QPixmap:
        """Tints a grayscale texture with the specified color. Uses a cache for performance."""
        # FIX: Cache the tinted texture so we don't recreate QPixmaps constantly during mouse movement
        key = (tex.cacheKey(), color.rgb())
        if key in self._tint_cache:
            return self._tint_cache[key]
            
        tinted = QPixmap(tex.size())
        tinted.fill(Qt.GlobalColor.transparent)
        p = QPainter(tinted)
        p.drawPixmap(0, 0, tex)
        p.setCompositionMode(QPainter.CompositionMode.CompositionMode_SourceIn)
        p.fillRect(tinted.rect(), color)
        p.end()
        
        # Prevent memory leaks by clearing cache if it gets too large
        if len(self._tint_cache) > 50:
            self._tint_cache.clear()
            
        self._tint_cache[key] = tinted
        return tinted

    def _stamp_along_path(self, painter: QPainter, p1: QPoint, p2: QPoint, preset: BrushPreset, color: QColor, width: int) -> None:
        """Stamps the texture along the line path based on preset spacing."""
        import math
        
        dx = p2.x() - p1.x()
        dy = p2.y() - p1.y()
        distance = math.hypot(dx, dy)
        
        if distance == 0:
            return
            
        # Ensure at least 1 step, and scale steps based on distance and spacing
        steps = max(1, int(distance / max(1, preset.spacing)))
        tex = preset.texture.scaled(width, width, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
        tinted_tex = self._tint_texture(tex, color)
        
        # FIX: Save painter state and enable smooth pixmap transform
        old_hints = painter.renderHints()
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform, True)
        
        for i in range(steps + 1):
            t = i / steps
            x = int(p1.x() + dx * t)
            y = int(p1.y() + dy * t)
            painter.drawPixmap(x - width//2, y - width//2, tinted_tex)
            
        # Restore painter state
        painter.setRenderHints(old_hints)