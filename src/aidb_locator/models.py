"""Data models for CodeLocator protocol responses.

Upstream SDK uses abbreviated JSON field names for compression.
Each model maps short keys to readable Python attributes.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class WView:
    class_name: str = ""
    visibility: str = "V"
    id_str: str | None = None
    id_int: int = 0
    mem_addr: str | None = None
    text: str | None = None
    left: int = 0
    right: int = 0
    top: int = 0
    bottom: int = 0
    left_offset: int = 0
    top_offset: int = 0
    draw_left: int = 0
    draw_right: int = 0
    draw_top: int = 0
    draw_bottom: int = 0
    padding_left: int = 0
    padding_right: int = 0
    padding_top: int = 0
    padding_bottom: int = 0
    margin_left: int = 0
    margin_right: int = 0
    margin_top: int = 0
    margin_bottom: int = 0
    layout_width: int = 0
    layout_height: int = 0
    scroll_x: int = 0
    scroll_y: int = 0
    scale_x: float = 1.0
    scale_y: float = 1.0
    translation_x: float = 0.0
    translation_y: float = 0.0
    pivot_x: float = 0.0
    pivot_y: float = 0.0
    alpha: float = 1.0
    is_clickable: bool = False
    is_enabled: bool = True
    is_focusable: bool = False
    is_selected: bool = False
    can_provide_data: bool = False
    background_color: str | None = None
    text_color: str | None = None
    text_size: float = 0.0
    click_tag: str | None = None
    touch_tag: str | None = None
    xml_tag: str | None = None
    view_holder_tag: str | None = None
    view_type: int = 0
    children: list[WView] = field(default_factory=list)

    @classmethod
    def from_dict(cls, d: dict) -> WView:
        children_raw = d.get("a", [])
        children = [WView.from_dict(c) for c in children_raw] if children_raw else []
        return cls(
            class_name=d.get("ag", ""),
            visibility=d.get("ab", "V"),
            id_str=d.get("ac"),
            id_int=d.get("ad", 0),
            mem_addr=d.get("af"),
            text=d.get("aq"),
            left=d.get("d", 0),
            right=d.get("e", 0),
            top=d.get("f", 0),
            bottom=d.get("g", 0),
            left_offset=d.get("c", 0),
            top_offset=d.get("b", 0),
            draw_left=d.get("p", 0),
            draw_right=d.get("q", 0),
            draw_top=d.get("n", 0),
            draw_bottom=d.get("o", 0),
            padding_left=d.get("t", 0),
            padding_right=d.get("u", 0),
            padding_top=d.get("r", 0),
            padding_bottom=d.get("s", 0),
            margin_left=d.get("x", 0),
            margin_right=d.get("y", 0),
            margin_top=d.get("v", 0),
            margin_bottom=d.get("w", 0),
            layout_width=d.get("z", 0),
            layout_height=d.get("a0", 0),
            scroll_x=d.get("h", 0),
            scroll_y=d.get("i", 0),
            scale_x=d.get("j", 1.0),
            scale_y=d.get("k", 1.0),
            translation_x=d.get("l", 0.0),
            translation_y=d.get("m", 0.0),
            pivot_x=d.get("df", 0.0),
            pivot_y=d.get("dg", 0.0),
            alpha=d.get("ae", 1.0),
            is_clickable=d.get("a1", False),
            is_enabled=d.get("a7", True),
            is_focusable=d.get("a3", False),
            is_selected=d.get("a5", False),
            can_provide_data=d.get("a9", False),
            background_color=d.get("ap"),
            text_color=d.get("as"),
            text_size=d.get("at", 0.0),
            click_tag=d.get("ah"),
            touch_tag=d.get("ai"),
            xml_tag=d.get("ak"),
            view_holder_tag=d.get("an"),
            view_type=d.get("aa", 0),
            children=children,
        )

    def to_dict(self) -> dict:
        d: dict = {
            "class_name": self.class_name,
            "visibility": self.visibility,
            "bounds": {
                "left": self.left,
                "top": self.top,
                "right": self.right,
                "bottom": self.bottom,
            },
        }
        if self.id_str:
            d["id"] = self.id_str
        if self.text:
            d["text"] = self.text
        if self.mem_addr:
            d["mem_addr"] = self.mem_addr
        if self.is_clickable:
            d["clickable"] = True
        if self.background_color:
            d["background_color"] = self.background_color
        if self.text_color:
            d["text_color"] = self.text_color
        if self.text_size:
            d["text_size"] = self.text_size
        if self.children:
            d["children"] = [c.to_dict() for c in self.children]
        return d


@dataclass
class WFragment:
    class_name: str = ""
    tag: str | None = None
    id: int = 0
    mem_addr: str | None = None
    view_mem_addr: str | None = None
    is_visible: bool = False
    is_added: bool = False
    user_visible_hint: bool = True
    children: list[WFragment] = field(default_factory=list)

    @classmethod
    def from_dict(cls, d: dict) -> WFragment:
        children_raw = d.get("a", [])
        children = [WFragment.from_dict(c) for c in children_raw] if children_raw else []
        return cls(
            class_name=d.get("ag", ""),
            tag=d.get("cc"),
            id=d.get("ad", 0),
            mem_addr=d.get("af"),
            view_mem_addr=d.get("cb"),
            is_visible=d.get("cd", False),
            is_added=d.get("ce", False),
            user_visible_hint=d.get("cf", True),
            children=children,
        )

    def to_dict(self) -> dict:
        d: dict = {
            "class_name": self.class_name,
            "visible": self.is_visible,
            "added": self.is_added,
        }
        if self.tag:
            d["tag"] = self.tag
        if self.children:
            d["children"] = [c.to_dict() for c in self.children]
        return d


@dataclass
class WActivity:
    class_name: str = ""
    mem_addr: str | None = None
    start_info: str | None = None
    decor_views: list[WView] = field(default_factory=list)
    fragments: list[WFragment] = field(default_factory=list)

    @classmethod
    def from_dict(cls, d: dict) -> WActivity:
        decor_raw = d.get("cj", [])
        frag_raw = d.get("ck", [])
        return cls(
            class_name=d.get("ag", ""),
            mem_addr=d.get("af"),
            start_info=d.get("cl"),
            decor_views=[WView.from_dict(v) for v in decor_raw],
            fragments=[WFragment.from_dict(f) for f in frag_raw],
        )

    def to_dict(self) -> dict:
        d: dict = {
            "class_name": self.class_name,
            "fragments": [f.to_dict() for f in self.fragments],
        }
        if self.decor_views:
            d["view_tree"] = [v.to_dict() for v in self.decor_views]
        return d


@dataclass
class WFile:
    name: str = ""
    absolute_path: str = ""
    size: int = 0
    is_directory: bool = False
    is_exists: bool = True
    in_sdcard: bool = False
    last_modified: int = 0
    custom_tag: str | None = None
    editable: bool = False
    is_json: bool = False
    children: list[WFile] = field(default_factory=list)

    @classmethod
    def from_dict(cls, d: dict) -> WFile:
        children_raw = d.get("a", [])
        children = [WFile.from_dict(c) for c in children_raw] if children_raw else []
        return cls(
            name=d.get("c6", ""),
            absolute_path=d.get("c7", ""),
            size=d.get("c1", 0),
            is_directory=d.get("c2", False),
            is_exists=d.get("c3", True),
            in_sdcard=d.get("c4", False),
            last_modified=d.get("c5", 0),
            custom_tag=d.get("c8"),
            editable=d.get("c9", False),
            is_json=d.get("ca", False),
            children=children,
        )

    def to_dict(self) -> dict:
        d: dict = {
            "name": self.name,
            "path": self.absolute_path,
            "size": self.size,
            "is_directory": self.is_directory,
        }
        if self.children:
            d["children"] = [c.to_dict() for c in self.children]
        return d


@dataclass
class SchemaInfo:
    schema: str = ""
    display_schema: str | None = None
    desc: str | None = None

    @classmethod
    def from_dict(cls, d: dict) -> SchemaInfo:
        return cls(
            schema=d.get("db", ""),
            display_schema=d.get("ds"),
            desc=d.get("dc"),
        )

    def to_dict(self) -> dict:
        d: dict = {"schema": self.schema}
        if self.desc:
            d["desc"] = self.desc
        return d


@dataclass
class WApplication:
    package_name: str = ""
    activity: WActivity = field(default_factory=WActivity)
    file: WFile | None = None
    schemas: list[SchemaInfo] = field(default_factory=list)
    is_debug: bool = False
    density: float = 0.0
    screen_width: int = 0
    screen_height: int = 0
    android_version: int = 0
    device_info: str | None = None
    sdk_version: str | None = None

    @classmethod
    def from_dict(cls, d: dict) -> WApplication:
        activity_raw = d.get("b7", {})
        file_raw = d.get("b8")
        schema_raw = d.get("bc", [])
        return cls(
            package_name=d.get("bd", ""),
            activity=WActivity.from_dict(activity_raw) if activity_raw else WActivity(),
            file=WFile.from_dict(file_raw) if file_raw else None,
            schemas=[SchemaInfo.from_dict(s) for s in schema_raw],
            is_debug=d.get("bf", False),
            density=d.get("bj", 0.0),
            screen_width=d.get("bq", 0),
            screen_height=d.get("br", 0),
            android_version=d.get("by", 0),
            device_info=d.get("bz"),
            sdk_version=d.get("bo"),
        )

    def to_dict(self) -> dict:
        d: dict = {
            "package_name": self.package_name,
            "activity": self.activity.to_dict(),
            "screen": {
                "width": self.screen_width,
                "height": self.screen_height,
                "density": self.density,
            },
        }
        if self.schemas:
            d["schemas"] = [s.to_dict() for s in self.schemas]
        if self.device_info:
            d["device_info"] = self.device_info
        return d


def parse_application(response: dict) -> WApplication:
    """Parse a full ApplicationResponse (BaseResponse<WApplication>) into WApplication."""
    data = response.get("data", {})
    return WApplication.from_dict(data)
