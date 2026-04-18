import bpy


class NLA_UL_strip_list(bpy.types.UIList):
    bl_idname = "NLA_UL_strip_list"

    def draw_item(self, context, layout, data, item, icon, active_data, active_propname, index=0):
        if self.layout_type in {'DEFAULT', 'COMPACT'}:
            split = layout.split(factor=0.22, align=True)
            split.label(text=item.name, icon='NLA')
            split = split.split(factor=0.22, align=True)
            split.label(text=item.owner_name or '-')
            split = split.split(factor=0.22, align=True)
            split.label(text=item.track_name or '-')
            split = split.split(factor=0.20, align=True)
            split.label(text=item.action_name or 'No Action')
            split.label(text=f'{item.frame_start}-{item.frame_end}')
        elif self.layout_type == 'GRID':
            layout.alignment = 'CENTER'
            layout.label(text="", icon='NLA')
