from hexlog.ui.theme import get_theme_stylesheet, toggle_theme_name


def test_light_stylesheet_contains_light_palette():
    stylesheet = get_theme_stylesheet("light")
    assert "background-color: #f4f5f7" in stylesheet
    assert "color: #1f2329" in stylesheet


def test_toggle_theme_name_flips_between_dark_and_light():
    assert toggle_theme_name("dark") == "light"
    assert toggle_theme_name("light") == "dark"
