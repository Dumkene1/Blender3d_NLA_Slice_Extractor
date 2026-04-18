import bpy

from ..utils.strip_utils import selected_anim_object


class NLA_PT_slice_extractor(bpy.types.Panel):
    bl_label = "NLA Slice Extractor"
    bl_idname = "NLA_PT_slice_extractor"
    bl_space_type = 'NLA_EDITOR'
    bl_region_type = 'UI'
    bl_category = 'NLA Slice Extractor'

    def draw(self, context):
        layout = self.layout
        settings = context.scene.nlase_settings
        obj = selected_anim_object(context)

        if not obj:
            layout.label(text="Select an object with NLA tracks.", icon='INFO')
            return

        top = layout.row(align=True)
        top.operator("nla_slice.refresh_strips", icon='FILE_REFRESH')

        if not settings.strips:
            layout.label(text="No NLA strips found on the relevant animated object(s).", icon='INFO')
            return

        header = layout.row(align=True)
        split = header.split(factor=0.22, align=True)
        split.label(text="Strip")
        split = split.split(factor=0.22, align=True)
        split.label(text="Owner")
        split = split.split(factor=0.22, align=True)
        split.label(text="Track")
        split = split.split(factor=0.20, align=True)
        split.label(text="Action")
        split.label(text="Range")

        layout.template_list(
            "NLA_UL_strip_list",
            "",
            settings,
            "strips",
            settings,
            "active_index",
            rows=5,
        )

        item = settings.strips[min(max(0, settings.active_index), len(settings.strips) - 1)]
        box = layout.box()
        box.label(text=f"Selected Strip: {item.name}", icon='NLA')
        box.label(text=f"Owner: {item.owner_name}")
        box.label(text=f"Track: {item.track_name}")
        box.label(text=f"Action: {item.action_name or 'None'}")

        layout.prop(settings, "slice_start")
        layout.prop(settings, "slice_end")
        layout.prop(settings, "new_action_name")

        note = layout.box()
        note.label(text="Requires one valid NLA strip.", icon='INFO')
        note.label(text="Creates a new Action, track, and strip.")
        note.label(text="End frame must be greater than start frame.")

        layout.operator("nla_slice.extract", icon='ACTION')
