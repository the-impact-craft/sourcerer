from textual.theme import Theme

github_dark_theme = Theme(
    name="github-dark",
    primary="#FFA656",
    secondary="#81A1C1",
    accent="#B48EAD",
    foreground="#CDD9E5",
    background="#1C2128",
    success="#A3BE8C",
    warning="#EBCB8B",
    error="#BF616A",
    surface="#22272E",
    panel="#434C5E",
    dark=True,
    variables={
        "block-cursor-text-style": "none",
        "footer-key-foreground": "#88C0D0",
        "input-selection-background": "#81a1c1 35%",
    },
)
