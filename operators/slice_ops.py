import bpy

from ..utils.strip_utils import get_active_strip_from_settings, sync_strip_items


def _sanitize_action_name(name: str) -> str:
    text = (name or "").strip()
    return text or "New_Action"


def _copy_kfp_attributes(src, dst):
    dst.interpolation = src.interpolation
    dst.easing = src.easing
    dst.handle_left_type = src.handle_left_type
    dst.handle_right_type = src.handle_right_type
    dst.amplitude = src.amplitude
    dst.back = src.back
    dst.period = src.period
    dst.type = src.type


def _find_neighbor_keys(fcurve, frame):
    left = None
    right = None
    for kp in fcurve.keyframe_points:
        x = kp.co.x
        if x < frame:
            if left is None or x > left.co.x:
                left = kp
        elif x > frame:
            if right is None or x < right.co.x:
                right = kp
    return left, right


def _channelbags_for_action(action, slot_identifier=None):
    layers = getattr(action, "layers", None)
    if not layers:
        return []
    bags = []
    for layer in layers:
        for strip in getattr(layer, "strips", []):
            for bag in getattr(strip, "channelbags", []):
                if slot_identifier is None:
                    bags.append(bag)
                else:
                    bag_slot = getattr(bag, "slot", None)
                    bag_identifier = getattr(bag_slot, "identifier", None)
                    if bag_identifier == slot_identifier:
                        bags.append(bag)
    return bags


def _fcurves_for_action(action, slot_identifier=None):
    bags = _channelbags_for_action(action, slot_identifier)
    if bags:
        return bags[0].fcurves
    legacy_fcurves = getattr(action, "fcurves", None)
    if legacy_fcurves is not None:
        return legacy_fcurves
    return []


def _evaluate_point(fcurve, frame):
    return float(fcurve.evaluate(frame))


def _insert_boundary_key(dst_fcurve, src_fcurve, frame):
    value = _evaluate_point(src_fcurve, frame)
    kp = dst_fcurve.keyframe_points.insert(frame, value, options={'FAST'})
    left, right = _find_neighbor_keys(src_fcurve, frame)
    template = left or right
    if template is not None:
        _copy_kfp_attributes(template, kp)
    else:
        kp.interpolation = 'BEZIER'
        kp.handle_left_type = 'AUTO'
        kp.handle_right_type = 'AUTO'
    return kp


def _remove_outside_range(fcurve, start_frame, end_frame):
    indices = [i for i, kp in enumerate(fcurve.keyframe_points) if kp.co.x < start_frame or kp.co.x > end_frame]
    for i in reversed(indices):
        fcurve.keyframe_points.remove(fcurve.keyframe_points[i], fast=True)


class NLA_OT_refresh_strips(bpy.types.Operator):
    bl_idname = "nla_slice.refresh_strips"
    bl_label = "Refresh"
    bl_description = "Refresh the list of available NLA strips from the active object"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        obj = sync_strip_items(context, prefer_timeline_selection=False)
        if obj is None:
            self.report({'WARNING'}, "Select an object with NLA tracks.")
            return {'CANCELLED'}
        self.report({'INFO'}, "NLA strip list refreshed.")
        return {'FINISHED'}


class NLA_OT_extract_slice(bpy.types.Operator):
    bl_idname = "nla_slice.extract"
    bl_label = "Extract Slice"
    bl_description = "Create a new Action, track, and strip from the chosen frame range of the selected NLA strip"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        settings = context.scene.nlase_settings
        obj, track, strip = get_active_strip_from_settings(context)
        if not obj:
            self.report({'ERROR'}, "Select an animated object with NLA tracks.")
            return {'CANCELLED'}
        if not strip:
            self.report({'ERROR'}, "No valid NLA strip selected.")
            return {'CANCELLED'}
        if strip.action is None:
            self.report({'ERROR'}, "The selected strip has no Action.")
            return {'CANCELLED'}
        if settings.slice_end <= settings.slice_start:
            self.report({'ERROR'}, "End frame must be greater than start frame.")
            return {'CANCELLED'}

        source_action = strip.action
        slot_identifier = getattr(getattr(strip, 'action_slot', None), 'identifier', None)
        src_fcurves = _fcurves_for_action(source_action, slot_identifier)
        if not src_fcurves:
            self.report({'ERROR'}, "Could not access animation curves for the selected strip in this Blender version.")
            return {'CANCELLED'}

        new_name = _sanitize_action_name(settings.new_action_name or f"{strip.name}_Slice")
        new_action = source_action.copy()
        new_action.name = new_name
        new_action.use_fake_user = True

        dst_fcurves = _fcurves_for_action(new_action, slot_identifier)
        if not dst_fcurves:
            bpy.data.actions.remove(new_action)
            self.report({'ERROR'}, "Could not prepare the duplicated action for slicing.")
            return {'CANCELLED'}

        src_map = {(fc.data_path, fc.array_index): fc for fc in src_fcurves}
        dst_map = {(fc.data_path, fc.array_index): fc for fc in dst_fcurves}

        any_curve = False
        for key, dst_fcurve in dst_map.items():
            src_fcurve = src_map.get(key)
            if src_fcurve is None:
                continue

            existing_inside = {round(kp.co.x, 6) for kp in dst_fcurve.keyframe_points if settings.slice_start <= kp.co.x <= settings.slice_end}
            _remove_outside_range(dst_fcurve, settings.slice_start, settings.slice_end)

            if round(float(settings.slice_start), 6) not in existing_inside:
                _insert_boundary_key(dst_fcurve, src_fcurve, settings.slice_start)
            if round(float(settings.slice_end), 6) not in existing_inside:
                _insert_boundary_key(dst_fcurve, src_fcurve, settings.slice_end)

            if dst_fcurve.keyframe_points:
                any_curve = True
                dst_fcurve.keyframe_points.sort()
                try:
                    dst_fcurve.keyframe_points.deduplicate()
                except Exception:
                    pass
                dst_fcurve.update()

        if not any_curve:
            bpy.data.actions.remove(new_action)
            self.report({'ERROR'}, "No animation data could be extracted from that frame range.")
            return {'CANCELLED'}

        new_track = obj.animation_data.nla_tracks.new()
        new_track.name = new_name
        new_strip = new_track.strips.new(new_name, int(settings.slice_start), new_action)
        new_strip.name = new_name

        try:
            sync_strip_items(context, prefer_timeline_selection=False)
        except Exception:
            pass

        self.report({'INFO'}, f"Created action and strip '{new_action.name}' from strip '{strip.name}'.")
        return {'FINISHED'}
