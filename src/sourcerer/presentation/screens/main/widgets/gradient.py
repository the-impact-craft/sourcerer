from rich.text import Text
from textual.widgets import Static


def hex_to_rgb(hex_color: str):
    """
    Convert a hex color string to an RGB tuple.
    """
    hex_color = hex_color.lstrip("#")
    return tuple(int(hex_color[i : i + 2], 16) for i in (0, 2, 4))


def generate_gradient_text(text: str, start_color: str, end_color: str) -> Text:
    """
    Generate a gradient text effect by blending two colors across the text.
    """
    start_rgb = hex_to_rgb(start_color)
    end_rgb = hex_to_rgb(end_color)

    gradient_text = Text()

    for i, char in enumerate(text):
        blend = i / (len(text) - 1) if len(text) > 1 else 0

        r = int(start_rgb[0] + (end_rgb[0] - start_rgb[0]) * blend)
        g = int(start_rgb[1] + (end_rgb[1] - start_rgb[1]) * blend)
        b = int(start_rgb[2] + (end_rgb[2] - start_rgb[2]) * blend)

        color = f"#{r:02x}{g:02x}{b:02x}"
        gradient_text.append(char, style=color)

    return gradient_text


class GradientWidget(Static):

    def on_mount(self):
        """
        Generate a gradient text effect for the widget's content.
        """
        gradient = generate_gradient_text(str(self.renderable), "#9E53E0", "#FFA656")
        self.update(gradient)
