def from_some_distance_away(pt_origin, pt_ref, distance="5mm", angle=-90):
    return f"(${pt_origin}!{distance}!{angle}:{pt_ref}$)"
