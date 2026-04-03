from aidb_locator.models import (
    WView,
    WFragment,
    WActivity,
    WFile,
    WApplication,
    SchemaInfo,
    parse_application,
)


class TestWView:
    def test_parse_minimal_view(self):
        raw = {
            "ag": "android.widget.TextView",
            "ab": "V",
            "d": 0, "e": 100, "f": 0, "g": 50,
        }
        view = WView.from_dict(raw)
        assert view.class_name == "android.widget.TextView"
        assert view.visibility == "V"
        assert view.left == 0
        assert view.right == 100
        assert view.top == 0
        assert view.bottom == 50

    def test_parse_view_with_text(self):
        raw = {
            "ag": "android.widget.TextView",
            "ab": "V",
            "ac": "title",
            "aq": "Hello World",
            "d": 0, "e": 200, "f": 0, "g": 48,
        }
        view = WView.from_dict(raw)
        assert view.id_str == "title"
        assert view.text == "Hello World"

    def test_parse_view_with_children(self):
        raw = {
            "ag": "android.widget.FrameLayout",
            "ab": "V",
            "d": 0, "e": 1080, "f": 0, "g": 2340,
            "a": [
                {"ag": "android.widget.TextView", "ab": "V", "d": 0, "e": 100, "f": 0, "g": 50},
                {"ag": "android.widget.Button", "ab": "V", "d": 0, "e": 200, "f": 50, "g": 100},
            ],
        }
        view = WView.from_dict(raw)
        assert len(view.children) == 2
        assert view.children[0].class_name == "android.widget.TextView"
        assert view.children[1].class_name == "android.widget.Button"

    def test_view_to_dict(self):
        raw = {
            "ag": "android.widget.TextView",
            "ab": "V",
            "ac": "btn",
            "aq": "Click me",
            "d": 10, "e": 200, "f": 20, "g": 80,
        }
        view = WView.from_dict(raw)
        d = view.to_dict()
        assert d["class_name"] == "android.widget.TextView"
        assert d["id"] == "btn"
        assert d["text"] == "Click me"
        assert d["bounds"] == {"left": 10, "top": 20, "right": 200, "bottom": 80}


class TestWFragment:
    def test_parse_fragment(self):
        raw = {
            "ag": "com.example.HomeFragment",
            "cd": True,
            "ce": True,
            "af": "0x1234",
        }
        frag = WFragment.from_dict(raw)
        assert frag.class_name == "com.example.HomeFragment"
        assert frag.is_visible is True
        assert frag.is_added is True

    def test_parse_nested_fragments(self):
        raw = {
            "ag": "ParentFragment",
            "cd": True,
            "ce": True,
            "a": [
                {"ag": "ChildFragment", "cd": True, "ce": True},
            ],
        }
        frag = WFragment.from_dict(raw)
        assert len(frag.children) == 1
        assert frag.children[0].class_name == "ChildFragment"


class TestWFile:
    def test_parse_file(self):
        raw = {
            "c6": "config.json",
            "c7": "/data/data/com.example/files/config.json",
            "c1": 1024,
            "c2": False,
            "c3": True,
        }
        f = WFile.from_dict(raw)
        assert f.name == "config.json"
        assert f.absolute_path == "/data/data/com.example/files/config.json"
        assert f.size == 1024
        assert f.is_directory is False

    def test_parse_directory_with_children(self):
        raw = {
            "c6": "files",
            "c7": "/data/data/com.example/files",
            "c1": 0,
            "c2": True,
            "c3": True,
            "a": [
                {"c6": "a.txt", "c7": "/data/data/com.example/files/a.txt", "c1": 100, "c2": False, "c3": True},
            ],
        }
        f = WFile.from_dict(raw)
        assert f.is_directory is True
        assert len(f.children) == 1
        assert f.children[0].name == "a.txt"


class TestWApplication:
    def test_parse_application(self):
        raw = {
            "code": 0,
            "msg": "success",
            "data": {
                "bd": "com.example.app",
                "b7": {
                    "ag": "com.example.MainActivity",
                    "cj": [
                        {
                            "ag": "android.widget.FrameLayout",
                            "ab": "V",
                            "d": 0, "e": 1080, "f": 0, "g": 2340,
                        }
                    ],
                    "ck": [
                        {"ag": "HomeFragment", "cd": True, "ce": True},
                    ],
                },
                "bc": [
                    {"db": "myapp://home", "dc": "Home page"},
                ],
            },
        }
        app = parse_application(raw)
        assert app.package_name == "com.example.app"
        assert app.activity.class_name == "com.example.MainActivity"
        assert len(app.activity.decor_views) == 1
        assert len(app.activity.fragments) == 1
        assert app.activity.fragments[0].class_name == "HomeFragment"
        assert len(app.schemas) == 1
        assert app.schemas[0].schema == "myapp://home"
