class Theme:
    """Управление темами оформления приложения."""
    
    def __init__(self, is_dark_mode=False):
        self.is_dark_mode = is_dark_mode

    def get_bg_color(self):
        return "#1e1e1e" if self.is_dark_mode else "#f9f9f9"

    def get_fg_color(self):
        return "#ffffff" if self.is_dark_mode else "#000000"

    def get_button_bg(self):
        return "#3c3c3c" if self.is_dark_mode else "#d3d3d3"

    def get_button_fg(self):
        return "#ffffff" if self.is_dark_mode else "#000000"

    def get_accent_color(self):
        return "#2c2c2c" if self.is_dark_mode else "#0078d7"

    def get_result_bg(self):
        return "#2e2e2e" if self.is_dark_mode else "#ffffff"

    def get_result_fg(self):
        return "#ffffff" if self.is_dark_mode else "#000000"

    def toggle(self):
        """Переключение между светлой и темной темой."""
        self.is_dark_mode = not self.is_dark_mode