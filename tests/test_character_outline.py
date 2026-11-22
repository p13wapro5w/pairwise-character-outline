import pytest
import render.character_outline as mod

CASES = [
    ("depth_normal_edge", (1.0, 2.0, 0.5)),
    ("screen_space_width", (3.0, 1080)),
    ("transparent_mask", ([1, 0, 1],)),
    ("temporal_stable", (1, 2)),
    ("msaa_resolve_mask", (4, 2)),
    ("world_camera_only", (1, 2)),
    ("faction_color", (1, 2)),
    ("gap_fill", ([1, 2, 3],)),
    ("width_scale", (2.0, 720, 1440)),
    ("depth_write_off", (1)),
    ("normal_threshold", (0.3, 0.9)),
    ("outline_color", (0.2, 0.4)),
    ("edge_dilate", ([0, 1, 0], 1)),
    ("stencil_mask", (2, 1)),
    ("per_object_style", (1, 2)),
]

@pytest.mark.parametrize("fn_name,args", CASES)
def test_contract(fn_name, args):
    fn = getattr(mod, fn_name)
    assert fn(*args) is not None
