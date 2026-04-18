import bpy


def _candidate_anim_owners(context):
    seen = set()
    owners = []

    def add(obj):
        if not obj:
            return
        ptr = obj.as_pointer()
        if ptr in seen:
            return
        ad = getattr(obj, "animation_data", None)
        tracks = getattr(ad, "nla_tracks", None) if ad else None
        if tracks:
            seen.add(ptr)
            owners.append(obj)

    active = getattr(context, "active_object", None) or getattr(context, "object", None)
    add(active)

    for obj in getattr(context, "selected_objects", []) or []:
        add(obj)

    # Common case: mesh selected while animation lives on its armature.
    for obj in list(owners) + ([active] if active else []):
        parent = getattr(obj, "parent", None)
        if parent and getattr(parent, "type", None) == 'ARMATURE':
            add(parent)
        for mod in getattr(obj, "modifiers", []) or []:
            if getattr(mod, 'type', None) == 'ARMATURE':
                add(getattr(mod, 'object', None))

    return owners


def selected_anim_object(context):
    owners = _candidate_anim_owners(context)
    return owners[0] if owners else None


def iter_nla_strips(obj):
    if not obj or not obj.animation_data:
        return
    nla_tracks = getattr(obj.animation_data, "nla_tracks", None)
    if not nla_tracks:
        return
    for track_index, track in enumerate(nla_tracks):
        for strip_index, strip in enumerate(track.strips):
            yield track_index, track, strip_index, strip


def sync_strip_items(context, prefer_timeline_selection=False):
    scene = context.scene
    settings = scene.nlase_settings
    owners = _candidate_anim_owners(context)

    settings.strips.clear()
    if not owners:
        settings.active_index = 0
        return None

    all_items = []
    for obj in owners:
        for track_index, track, strip_index, strip in (iter_nla_strips(obj) or []):
            all_items.append((obj, track_index, track, strip_index, strip))

    active_idx = 0
    if prefer_timeline_selection:
        active_strip = getattr(context, "active_nla_strip", None)
        if active_strip:
            for idx, (_obj, _t_idx, _track, _s_idx, strip) in enumerate(all_items):
                if strip == active_strip:
                    active_idx = idx
                    break

    for idx, (obj, track_index, track, strip_index, strip) in enumerate(all_items):
        item = settings.strips.add()
        item.name = strip.name
        item.owner_name = obj.name
        item.track_name = track.name
        item.action_name = strip.action.name if getattr(strip, "action", None) else ""
        item.frame_start = int(strip.frame_start)
        item.frame_end = int(strip.frame_end)
        item.track_index = track_index
        item.strip_index = strip_index

    settings.active_index = min(max(0, active_idx), max(0, len(settings.strips) - 1)) if settings.strips else 0
    return owners[0]


def get_active_strip_from_settings(context):
    scene = context.scene
    settings = scene.nlase_settings
    owners = _candidate_anim_owners(context)
    if not owners or not settings.strips:
        return None, None, None
    idx = min(max(0, settings.active_index), len(settings.strips) - 1)
    wanted = settings.strips[idx]

    obj = next((o for o in owners if o.name == wanted.owner_name), None)
    if obj is None:
        return None, None, None

    nla_tracks = getattr(obj.animation_data, "nla_tracks", None)
    if not nla_tracks:
        return obj, None, None
    if 0 <= wanted.track_index < len(nla_tracks):
        track = nla_tracks[wanted.track_index]
        if 0 <= wanted.strip_index < len(track.strips):
            strip = track.strips[wanted.strip_index]
            return obj, track, strip
    return obj, None, None
