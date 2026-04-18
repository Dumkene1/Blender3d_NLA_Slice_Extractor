bl_info = {
    "name": "NLA Slice Extractor",
    "author": "Dumkene",
    "version": (0, 1, 0),
    "blender": (5, 0, 0),
    "location": "NLA Editor > Sidebar > NLA Slice Extractor",
    "description": "Extract a chosen frame range from a selected NLA strip into a new independent Action.",
    "category": "Animation",
}

import bpy
from bpy.props import CollectionProperty, IntProperty, PointerProperty, StringProperty
from bpy.types import PropertyGroup

from .operators.slice_ops import NLA_OT_extract_slice, NLA_OT_refresh_strips
from .ui.panel import NLA_PT_slice_extractor
from .ui.uilist import NLA_UL_strip_list


def _active_index_update(self, context):
    if self.strips and 0 <= self.active_index < len(self.strips):
        item = self.strips[self.active_index]
        self.slice_start = item.frame_start
        self.slice_end = item.frame_end
        if not self.new_action_name.strip():
            self.new_action_name = f"{item.name}_Slice"


class NLASE_PG_strip_item(PropertyGroup):
    name: StringProperty(name="Strip Name")
    track_name: StringProperty(name="Track Name")
    owner_name: StringProperty(name="Owner Name")
    action_name: StringProperty(name="Action Name")
    frame_start: IntProperty(name="Start")
    frame_end: IntProperty(name="End")
    track_index: IntProperty(name="Track Index", default=-1)
    strip_index: IntProperty(name="Strip Index", default=-1)


class NLASE_PG_settings(PropertyGroup):
    strips: CollectionProperty(type=NLASE_PG_strip_item)
    active_index: IntProperty(name="Active Strip", default=0, update=_active_index_update)
    slice_start: IntProperty(name="Start Frame", default=1)
    slice_end: IntProperty(name="End Frame", default=10)
    new_action_name: StringProperty(name="New Action Name", default="New_Action")


CLASSES = (
    NLASE_PG_strip_item,
    NLASE_PG_settings,
    NLA_UL_strip_list,
    NLA_OT_refresh_strips,
    NLA_OT_extract_slice,
    NLA_PT_slice_extractor,
)


def register():
    for cls in CLASSES:
        bpy.utils.register_class(cls)
    bpy.types.Scene.nlase_settings = PointerProperty(type=NLASE_PG_settings)


def unregister():
    del bpy.types.Scene.nlase_settings
    for cls in reversed(CLASSES):
        bpy.utils.unregister_class(cls)


if __name__ == "__main__":
    register()
